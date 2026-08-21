"""Atomic creation route for quarantined public submissions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError

from intake import db
from intake.artifacts import (
    MAX_UPLOAD_BYTES,
    ArtifactRejected,
    ArtifactStorageError,
    ArtifactStore,
    StoredArtifact,
)
from intake.rate_limits import (
    RateLimitExceeded,
    RateLimiter,
    canonical_ip,
    daily_ip_digest,
)
from intake.repositories import (
    SessionRepository,
    SubmissionLimitExceeded,
    SubmissionRepository,
)
from intake.schemas import SubmissionMetadata, SubmissionReceipt
from intake.security import TokenCodec
from intake.turnstile import TurnstileRejected, TurnstileUnavailable


router = APIRouter(prefix="/submission/v1")

_SESSION_COOKIE = "rvi_contribution_session"
_MAX_ARTIFACTS = 5
_MAX_TOTAL_UPLOAD_BYTES = 25 * 1024 * 1024
_EMAIL_DAILY_LIMIT = 20
_CAPABILITY_LIFETIME = timedelta(days=30)
_UNVERIFIED_RETENTION = timedelta(days=7)
_CAPABILITY_PURPOSES = ("status", "follow_up", "withdrawal")


class _InactiveSession(RuntimeError):
    pass


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


def _parse_metadata(raw: str) -> SubmissionMetadata:
    try:
        return SubmissionMetadata.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid submission metadata",
        ) from None


def _authenticate(
    request: Request, now: datetime
) -> tuple[str, str, object, TokenCodec]:
    settings = request.app.state.settings
    signed_session = request.cookies.get(_SESSION_COOKIE)
    session_codec = TokenCodec(settings.read_key("session"))
    try:
        raw_session = session_codec.verify_session(signed_session, int(now.timestamp()))
    except ValueError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "active contribution session required"
        ) from None
    session_digest = session_codec.digest(raw_session)
    with db.connect(settings.database_path) as conn:
        session = SessionRepository(conn).authenticate(session_digest, now.isoformat())
    if session is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "active contribution session required"
        )
    if not session_codec.verify_csrf(
        request.headers.get("X-CSRF-Token"), session["csrf_digest"]
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid CSRF token")
    return raw_session, session_digest, session, session_codec


def _upload_size(upload: UploadFile) -> int:
    if isinstance(upload.size, int):
        return upload.size
    try:
        position = upload.file.tell()
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(position)
    except (AttributeError, OSError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected") from None
    if not isinstance(size, int) or size < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected")
    return size


def _check_upload_limits(artifacts: list[UploadFile]) -> None:
    if len(artifacts) > _MAX_ARTIFACTS:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "artifact limits exceeded"
        )
    sizes = [_upload_size(upload) for upload in artifacts]
    if any(size > MAX_UPLOAD_BYTES for size in sizes) or sum(sizes) > (
        _MAX_TOTAL_UPLOAD_BYTES
    ):
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "artifact limits exceeded"
        )


def _artifact_values(artifact: StoredArtifact, now: datetime) -> dict[str, object]:
    return {
        "storage_key": artifact.storage_key,
        "original_name": artifact.original_name,
        "declared_media_type": artifact.declared_media_type,
        "detected_media_type": artifact.detected_media_type,
        "raw_sha256": artifact.raw_sha256,
        "stored_sha256": artifact.stored_sha256,
        "size_bytes": artifact.size_bytes,
        "width": artifact.width,
        "height": artifact.height,
        "scan_status": "clean",
        "retention_class": "unverified",
        "created_at": now.isoformat(),
        "purge_after": (now + _UNVERIFIED_RETENTION).isoformat(),
    }


def _discard(store: ArtifactStore, stored: list[StoredArtifact]) -> None:
    store.discard(artifact.storage_key for artifact in stored)


@router.post(
    "/submissions",
    status_code=status.HTTP_201_CREATED,
    response_model=SubmissionReceipt,
)
def create_submission(
    request: Request,
    metadata: Annotated[str, Form()],
    artifacts: Annotated[list[UploadFile], File()] = [],
):
    payload = _parse_metadata(metadata)
    settings = request.app.state.settings
    now = _now(request)
    _, session_digest, initial_session, _ = _authenticate(request, now)
    _check_upload_limits(artifacts)
    remote_ip = _remote_ip(request)
    try:
        request.app.state.turnstile_verifier.verify(payload.turnstile_token, remote_ip)
    except TurnstileRejected:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "turnstile verification failed"
        ) from None
    except TurnstileUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "turnstile unavailable"
        ) from None

    submission_id = str(uuid.uuid4())
    artifact_store = ArtifactStore(settings.artifact_root)
    stored_artifacts: list[StoredArtifact] = []
    try:
        for upload in artifacts:
            stored_artifacts.append(artifact_store.sanitize(upload, submission_id))
    except ArtifactRejected:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "artifact rejected") from None
    except ArtifactStorageError:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "artifact storage unavailable"
        ) from None

    token_codec = TokenCodec(settings.read_key("token"))
    raw_capabilities = {
        purpose: request.app.state.secret_factory() for purpose in _CAPABILITY_PURPOSES
    }
    expires_at = (now + _CAPABILITY_LIFETIME).isoformat()
    now_text = now.isoformat()

    try:
        with db.connect(settings.database_path) as conn:
            with db.transaction(conn):
                sessions = SessionRepository(conn)
                active_session = sessions.authenticate(session_digest, now_text)
                if (
                    active_session is None
                    or active_session["id"] != initial_session["id"]
                ):
                    raise _InactiveSession("active contribution session required")
                sessions.reserve_submission(active_session["id"])
                contributor = conn.execute(
                    "SELECT * FROM contributors WHERE id = ?",
                    (active_session["contributor_id"],),
                ).fetchone()
                if contributor is None:
                    raise _InactiveSession("active contribution session required")
                RateLimiter(conn).check_and_record(
                    "submission_email",
                    contributor["email_digest"],
                    _EMAIL_DAILY_LIMIT,
                    24 * 60 * 60,
                    now,
                )
                SubmissionRepository(conn).create_with_children(
                    {
                        "id": submission_id,
                        "contributor_id": contributor["id"],
                        "intent": payload.intent,
                        "target_component_id": payload.target_component_id,
                        "target_edge_key_json": (
                            None
                            if payload.target_edge is None
                            else payload.target_edge.model_dump(
                                mode="json", exclude_none=True
                            )
                        ),
                        "target_namespace": payload.target_namespace,
                        "target_identifier": payload.target_identifier,
                        "summary": payload.summary,
                        "context_json": payload.context.model_dump(mode="json"),
                        "priority": payload.priority,
                        "abuse_digest": daily_ip_digest(
                            settings.read_key("ip"), remote_ip, now
                        ),
                        "terms_version": payload.terms_version,
                        "evidence_license_version": (payload.evidence_license_version),
                        "consented_at": now_text,
                        "created_at": now_text,
                        "updated_at": now_text,
                    },
                    [
                        {
                            "claim_type": claim.claim_type,
                            "proposed_json": claim.proposed,
                            "created_at": now_text,
                        }
                        for claim in payload.claims
                    ],
                    [_artifact_values(artifact, now) for artifact in stored_artifacts],
                    [
                        {
                            "purpose": purpose,
                            "token_digest": token_codec.digest(raw_secret),
                            "expires_at": expires_at,
                            "created_at": now_text,
                        }
                        for purpose, raw_secret in raw_capabilities.items()
                    ],
                    [
                        {
                            "template": "submission_received",
                            "recipient_ciphertext": contributor["email_ciphertext"],
                            "template_data_json": {
                                "submission_id": submission_id,
                                "status": "received",
                            },
                            "next_attempt_at": now_text,
                            "created_at": now_text,
                        }
                    ],
                )
    except (SubmissionLimitExceeded, RateLimitExceeded):
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "submission limit exceeded"
        ) from None
    except _InactiveSession:
        _discard(artifact_store, stored_artifacts)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "active contribution session required"
        ) from None
    except BaseException:
        _discard(artifact_store, stored_artifacts)
        raise

    return {
        "submission_id": submission_id,
        "status": "received",
        "capabilities": raw_capabilities,
    }
