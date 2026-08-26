import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from intake import db
from review.auth import ReviewerAuthorizer
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
