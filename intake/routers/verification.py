"""Verified-email session routes for quarantined submission intake."""

import base64
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status

from intake import db
from intake.rate_limits import (
    RateLimitExceeded,
    RateLimiter,
    canonical_ip,
    daily_ip_digest,
)
from intake.repositories import (
    ContributorRepository,
    InvalidVerificationToken,
    OutboxRepository,
    SessionRepository,
)
from intake.schemas import (
    VerificationExchange,
    VerificationRequest,
    VerificationRequested,
    VerificationSession,
)
from intake.security import (
    ContactCipher,
    TokenCodec,
    VerificationTokenCipher,
    normalize_email,
)
from intake.turnstile import TurnstileRejected, TurnstileUnavailable


router = APIRouter(prefix="/submission/v1")
_GENERIC_REQUEST_RESPONSE = {"status": "verification_requested"}
_VERIFICATION_LIFETIME = timedelta(minutes=15)
_SESSION_LIFETIME = timedelta(hours=24)


def _now(request: Request) -> datetime:
    value = request.app.state.clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RuntimeError("application clock must return an aware datetime")
    return value.astimezone(timezone.utc)


def _remote_ip(request: Request) -> str:
    settings = request.app.state.settings
    if settings.trust_cf_connecting_ip:
        forwarded = request.headers.get("CF-Connecting-IP")
        if forwarded:
            try:
                return canonical_ip(forwarded)
            except ValueError:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "invalid client address"
                ) from None
    if request.client is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid client address")
    try:
        return canonical_ip(request.client.host)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "invalid client address"
        ) from None


@router.post(
    "/verification-requests",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VerificationRequested,
)
def request_verification(payload: VerificationRequest, request: Request):
    settings = request.app.state.settings
    now = _now(request)
    remote_ip = _remote_ip(request)
    try:
        request.app.state.turnstile_verifier.verify(
            payload.turnstile_token, remote_ip
        )
    except TurnstileRejected:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "turnstile verification failed"
        ) from None
    except TurnstileUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "turnstile unavailable"
        ) from None

    abuse_digest = daily_ip_digest(settings.read_key("ip"), remote_ip, now)
    try:
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                RateLimiter(conn).check_and_record(
                    "verification", abuse_digest, 5, 60 * 60, now
                )
                try:
                    email = normalize_email(payload.email)
                except ValueError:
                    return _GENERIC_REQUEST_RESPONSE

                token_codec = TokenCodec(settings.read_key("token"))
                contact_key = settings.read_key("contact")
                contact_ciphertext = ContactCipher(contact_key).encrypt(email)
                contributor = ContributorRepository(conn).upsert(
                    token_codec.digest(email),
                    contact_ciphertext,
                    now.isoformat(),
                )
                conn.execute(
                    """
                    UPDATE submission_sessions
                    SET state = 'revoked'
                    WHERE contributor_id = ? AND state = 'pending'
                    """,
                    (contributor["id"],),
                )

                raw_token = request.app.state.secret_factory()
                expires_at = (now + _VERIFICATION_LIFETIME).isoformat()
                encrypted_token = VerificationTokenCipher(contact_key).encrypt(
                    raw_token
                )
                SessionRepository(conn).create_pending(
                    contributor["id"],
                    token_codec.digest(raw_token),
                    expires_at,
                    now.isoformat(),
                )
                OutboxRepository(conn).enqueue(
                    {
                        "template": "verify_email",
                        "recipient_ciphertext": contact_ciphertext,
                        "template_data_json": {
                            "expires_at": expires_at,
                            "verification_token_ciphertext": base64.b64encode(
                                encrypted_token
                            ).decode("ascii"),
                        },
                        "next_attempt_at": now.isoformat(),
                        "created_at": now.isoformat(),
                    }
                )
    except RateLimitExceeded:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "rate limit exceeded"
        ) from None

    return _GENERIC_REQUEST_RESPONSE


@router.post(
    "/verification-exchanges",
    response_model=VerificationSession,
)
def exchange_verification(
    payload: VerificationExchange,
    request: Request,
    response: Response,
):
    settings = request.app.state.settings
    now = _now(request)
    verification_codec = TokenCodec(settings.read_key("token"))
    session_codec = TokenCodec(settings.read_key("session"))
    verification_digest = verification_codec.digest(payload.token)
    expires_at = now + _SESSION_LIFETIME

    try:
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                pending = conn.execute(
                    """
                    SELECT 1 FROM submission_sessions
                    WHERE token_digest = ? AND state = 'pending' AND expires_at > ?
                    """,
                    (verification_digest, now.isoformat()),
                ).fetchone()
                if pending is None:
                    raise InvalidVerificationToken(
                        "verification token is not active"
                    )
                raw_session = request.app.state.secret_factory()
                raw_csrf = request.app.state.secret_factory()
                SessionRepository(conn).activate(
                    verification_digest,
                    session_codec.digest(raw_session),
                    session_codec.digest(raw_csrf),
                    expires_at.isoformat(),
                    now.isoformat(),
                )
    except InvalidVerificationToken:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "invalid or expired verification token",
        ) from None

    signed_session = session_codec.sign_session(
        raw_session, int(expires_at.timestamp())
    )
    response.set_cookie(
        "rvi_contribution_session",
        signed_session,
        max_age=int(_SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/submission/v1/",
    )
    return {"csrf_token": raw_csrf}
