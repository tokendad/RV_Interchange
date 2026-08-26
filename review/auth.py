"""Cloudflare Access JWT validation and local role authorization."""

import hashlib
import hmac
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, Request, status

from review.config import Settings


@dataclass(frozen=True)
class ReviewerIdentity:
    email: str
    email_digest: str
    roles: frozenset[str]
    capabilities: frozenset[str]


class AccessTokenValidator:
    def __init__(self, settings: Settings, jwks_client=None):
        self.settings = settings
        self.jwks_client = jwks_client or jwt.PyJWKClient(settings.access_jwks_url, cache_jwk_set=True)

    def validate(self, assertion: str) -> dict:
        if not assertion:
            raise ValueError("missing access assertion")
        signing_key = self.jwks_client.get_signing_key_from_jwt(assertion).key
        return jwt.decode(assertion, signing_key, algorithms=["RS256"], issuer=self.settings.access_issuer, audience=self.settings.access_audience, options={"require": ["exp", "iat", "iss", "aud"]})


class ReviewerAuthorizer:
    def __init__(self, conn, settings: Settings, validator=None):
        self.conn = conn
        self.settings = settings
        self.validator = validator or AccessTokenValidator(settings)

    def require(self, request: Request, roles: set[str] | frozenset[str] = frozenset(), capability: str | None = None) -> ReviewerIdentity:
        assertion = request.headers.get("Cf-Access-Jwt-Assertion")
        try:
            if not assertion:
                raise ValueError("missing access assertion")
            payload = self.validator.validate(assertion)
            email = payload.get("email")
            if not isinstance(email, str) or not email:
                raise ValueError("missing email")
            digest = hmac.new(self.settings.reviewer_digest_key, email.strip().lower().encode(), hashlib.sha256).hexdigest()
            role_rows = self.conn.execute("SELECT role FROM reviewer_roles WHERE email_digest = ? AND active = 1 AND revoked_at IS NULL", (digest,)).fetchall()
            roles_found = frozenset(row[0] for row in role_rows)
            cap_rows = self.conn.execute("SELECT capability FROM reviewer_capabilities WHERE email_digest = ? AND active = 1 AND revoked_at IS NULL", (digest,)).fetchall()
            capabilities = frozenset(row[0] for row in cap_rows)
        except Exception:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "valid review identity required") from None
        if roles and not roles_found.intersection(roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "review role required")
        if capability and capability not in capabilities:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "review capability required")
        return ReviewerIdentity(email, digest, roles_found, capabilities)
