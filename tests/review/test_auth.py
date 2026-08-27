import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.requests import Request

from intake import db
from review.auth import AccessTokenValidator, ReviewerAuthorizer
from review.config import Settings


class Validator:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error

    def validate(self, assertion):
        if self.error:
            raise self.error
        return self.payload


def request(assertion="token"):
    return Request({"type": "http", "headers": [(b"cf-access-jwt-assertion", assertion.encode())]})


class JwksClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, _assertion):
        return SimpleNamespace(key=self.key)


def signed_token(private_key, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://access.example",
        "aud": "aud",
        "iat": now,
        "exp": now + 300,
        "email": "reviewer@example.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_access_token_validator_checks_real_rs256_claims(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator = AccessTokenValidator(
        settings, JwksClient(private_key.public_key())
    )

    assert validator.validate(signed_token(private_key))["email"] == (
        "reviewer@example.com"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": 1},
        {"iss": "https://wrong.example"},
        {"aud": "wrong-audience"},
    ],
)
def test_access_token_validator_rejects_invalid_registered_claims(
    tmp_path, overrides
):
    settings = Settings.for_tests(tmp_path / "db")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator = AccessTokenValidator(
        settings, JwksClient(private_key.public_key())
    )

    with pytest.raises(jwt.PyJWTError):
        validator.validate(signed_token(private_key, **overrides))


def test_access_token_validator_rejects_invalid_signature(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    expected_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator = AccessTokenValidator(
        settings, JwksClient(expected_key.public_key())
    )

    with pytest.raises(jwt.InvalidSignatureError):
        validator.validate(signed_token(attacker_key))


def test_missing_or_invalid_assertion_is_unauthorized(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    with db.connect(settings.database_path) as conn:
        with pytest.raises(HTTPException) as error:
            ReviewerAuthorizer(conn, settings, Validator(error=ValueError())).require(request(), {"admin"})
    assert error.value.status_code == 401


def test_roles_and_capabilities_are_loaded_from_signed_identity(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        import hashlib, hmac
        digest = hmac.new(settings.reviewer_digest_key, b"reviewer@example.com", hashlib.sha256).hexdigest()
        conn.execute("INSERT INTO reviewer_roles VALUES (?, 'admin', 1, 'now', NULL)", (digest,))
        conn.execute("INSERT INTO reviewer_capabilities VALUES (?, 'publisher', 1, 'now', NULL)", (digest,))
        identity = ReviewerAuthorizer(conn, settings, Validator({"email": "reviewer@example.com"})).require(request(), {"admin"}, "publisher")
    assert identity.email_digest == digest
    assert identity.roles == {"admin"}
    assert identity.capabilities == {"publisher"}


def test_signed_identity_without_active_local_role_is_unauthorized(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        with pytest.raises(HTTPException) as error:
            ReviewerAuthorizer(
                conn,
                settings,
                Validator({"email": "unlisted@example.com"}),
            ).require(request())

    assert error.value.status_code == 401


def test_publisher_capability_satisfies_admin_or_publisher_authorization(tmp_path):
    settings = Settings.for_tests(tmp_path / "db")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        import hashlib, hmac

        digest = hmac.new(
            settings.reviewer_digest_key,
            b"publisher@example.com",
            hashlib.sha256,
        ).hexdigest()
        conn.execute(
            "INSERT INTO reviewer_roles VALUES (?, 'trusted', 1, 'now', NULL)",
            (digest,),
        )
        conn.execute(
            "INSERT INTO reviewer_capabilities VALUES (?, 'publisher', 1, 'now', NULL)",
            (digest,),
        )

        identity = ReviewerAuthorizer(
            conn,
            settings,
            Validator({"email": "publisher@example.com"}),
        ).require(request(), {"admin"}, "publisher")

    assert identity.roles == {"trusted"}
    assert identity.capabilities == {"publisher"}
