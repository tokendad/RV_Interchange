"""Cryptographic primitives for quarantined public-submission intake."""

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_CONTACT_AAD = b"rvi-contact-v1"
_NONCE_BYTES = 12
_LOCAL_PART = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", re.ASCII)
_DOMAIN_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", re.ASCII)


def _require_key(key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("cryptographic key must contain exactly 32 bytes")
    return key


def normalize_email(email: str) -> str:
    """Return the supported canonical form of an ASCII email address."""
    if not isinstance(email, str):
        raise ValueError("invalid email address")
    normalized = unicodedata.normalize("NFKC", email)
    if any(
        unicodedata.category(character).startswith("C")
        for character in normalized
    ):
        raise ValueError("invalid email address")
    normalized = normalized.strip()
    if len(normalized) > 254 or normalized.count("@") != 1:
        raise ValueError("invalid email address")
    try:
        normalized.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("invalid email address") from None

    local, domain = normalized.lower().split("@", 1)
    if (
        not local
        or not domain
        or _LOCAL_PART.fullmatch(local) is None
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        raise ValueError("invalid email address")
    labels = domain.split(".")
    if any(
        len(label) > 63 or _DOMAIN_LABEL.fullmatch(label) is None
        for label in labels
    ):
        raise ValueError("invalid email address")
    return f"{local}@{domain}"


class ContactCipher:
    """Encrypt normalized contributor contact using AES-256-GCM."""

    def __init__(self, key: bytes):
        self._cipher = AESGCM(_require_key(key))

    def encrypt(self, email: str) -> bytes:
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ciphertext = self._cipher.encrypt(nonce, email.encode("utf-8"), _CONTACT_AAD)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> str:
        if not isinstance(ciphertext, bytes) or len(ciphertext) < _NONCE_BYTES + 16:
            raise ValueError("invalid contact ciphertext")
        nonce = ciphertext[:_NONCE_BYTES]
        encrypted = ciphertext[_NONCE_BYTES:]
        try:
            plaintext = self._cipher.decrypt(nonce, encrypted, _CONTACT_AAD)
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError):
            raise ValueError("invalid contact ciphertext") from None


def new_secret() -> str:
    """Generate a URL-safe secret containing 32 random bytes of entropy."""
    return secrets.token_urlsafe(32)


class TokenCodec:
    """Hash opaque tokens and sign short-lived contribution sessions."""

    def __init__(self, key: bytes):
        self._key = _require_key(key)

    def digest(self, raw: str) -> str:
        if not isinstance(raw, str):
            raise ValueError("invalid token")
        return hmac.new(self._key, raw.encode("utf-8"), hashlib.sha256).hexdigest()

    def matches(self, raw: str | None, expected_digest: str | None) -> bool:
        if not isinstance(raw, str) or not isinstance(expected_digest, str):
            return False
        actual_digest = hmac.new(
            self._key, raw.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        try:
            return hmac.compare_digest(actual_digest, expected_digest)
        except TypeError:
            return False

    def sign_session(self, raw: str, expires: int) -> str:
        if not isinstance(raw, str) or not raw or "." in raw:
            raise ValueError("invalid session token")
        if not isinstance(expires, int) or expires < 0:
            raise ValueError("invalid session token")
        payload = f"v1.{expires}.{raw}"
        signature = _urlsafe_signature(
            hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).digest()
        )
        return f"{payload}.{signature}"

    def verify_session(self, signed: str, now: int) -> str:
        if not isinstance(signed, str) or not isinstance(now, int):
            raise ValueError("invalid session token")
        try:
            version, expires_text, raw, signature = signed.split(".")
            expires = int(expires_text)
        except (TypeError, ValueError):
            raise ValueError("invalid session token") from None
        if version != "v1" or not raw or expires < 0:
            raise ValueError("invalid session token")
        payload = f"{version}.{expires_text}.{raw}"
        expected_signature = _urlsafe_signature(
            hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).digest()
        )
        try:
            signature_matches = hmac.compare_digest(signature, expected_signature)
        except TypeError:
            raise ValueError("invalid session token") from None
        if not signature_matches:
            raise ValueError("invalid session token")
        if now >= expires:
            raise ValueError("expired session token")
        return raw

    def verify_csrf(
        self, presented_token: str | None, expected_digest: str | None
    ) -> bool:
        if not presented_token:
            return False
        return self.matches(presented_token, expected_digest)


def verify_csrf(
    codec: TokenCodec,
    presented_token: str | None,
    expected_digest: str | None,
) -> bool:
    """Fail closed unless a presented CSRF secret matches its keyed digest."""
    if not isinstance(codec, TokenCodec):
        return False
    return codec.verify_csrf(presented_token, expected_digest)


def _urlsafe_signature(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
