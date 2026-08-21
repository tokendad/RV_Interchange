import base64
import json
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from intake import db
from intake.app import create_app
from intake.config import Settings
from intake.rate_limits import daily_ip_digest
from intake.security import ContactCipher, TokenCodec, VerificationTokenCipher
from intake.turnstile import TurnstileRejected, TurnstileUnavailable


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
VERIFICATION_TOKEN = "v" * 43
SESSION_TOKEN = "s" * 43
CSRF_TOKEN = "c" * 43


class AcceptingTurnstile:
    def verify(self, token: str, remote_ip: str) -> None:
        return None


class RejectingTurnstile:
    def verify(self, token: str, remote_ip: str) -> None:
        raise TurnstileRejected("turnstile verification failed")


class UnavailableTurnstile:
    def verify(self, token: str, remote_ip: str) -> None:
        raise TurnstileUnavailable("turnstile unavailable")


class MutableClock:
    def __init__(self, value: datetime):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def _secrets(*values):
    secrets = iter(values)
    return lambda: next(secrets)


def _client(
    settings: Settings,
    *,
    verifier=None,
    clock=None,
    secret_factory=None,
):
    return TestClient(
        create_app(
            settings,
            turnstile_verifier=verifier or AcceptingTurnstile(),
            clock=clock or MutableClock(NOW),
            secret_factory=secret_factory
            or _secrets(*(f"token-{i:02d}" * 5 for i in range(30))),
        ),
        client=("2001:db8::1", 50000),
    )


@pytest.fixture
def settings(tmp_path):
    return Settings.for_tests(tmp_path)


def test_daily_ip_digest_canonicalizes_and_rotates_each_utc_date():
    key = b"i" * 32

    compressed = daily_ip_digest(key, "2001:0db8:0:0:0:0:0:1", NOW)

    assert compressed == "ad9aa2dec7ddc84ed8ac8ec5ce3b11a9795a9d7c8dbd113f9e1c380277b52c20"
    assert daily_ip_digest(key, "2001:db8::1", NOW) == compressed
    assert daily_ip_digest(key, "2001:db8::1", NOW + timedelta(days=1)) == (
        "0e4871a993babd412a8622a7a0d6fca37c880d73711c29dca800c7d80d7b2d9e"
    )


def test_verification_request_has_constant_response_and_protects_persisted_data(
    settings,
):
    with _client(
        settings,
        secret_factory=_secrets(VERIFICATION_TOKEN),
    ) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            json={"email": "Person@Example.com", "turnstile_token": "ok"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "verification_requested"}

    token_codec = TokenCodec(settings.read_key("token"))
    with db.connect(settings.database_path) as conn:
        contributor = conn.execute("SELECT * FROM contributors").fetchone()
        session = conn.execute("SELECT * FROM submission_sessions").fetchone()
        outbox = conn.execute("SELECT * FROM email_outbox").fetchone()

    assert contributor["email_digest"] == token_codec.digest("person@example.com")
    assert ContactCipher(settings.read_key("contact")).decrypt(
        contributor["email_ciphertext"]
    ) == "person@example.com"
    assert session["token_digest"] == token_codec.digest(VERIFICATION_TOKEN)
    assert session["token_digest"] != VERIFICATION_TOKEN
    assert session["state"] == "pending"
    assert session["expires_at"] == "2026-08-21T12:15:00+00:00"
    assert outbox["template"] == "verify_email"
    assert outbox["recipient_ciphertext"] == contributor["email_ciphertext"]
    outbox_data = json.loads(outbox["template_data_json"])
    assert set(outbox_data) == {"expires_at", "verification_token_ciphertext"}
    assert outbox_data["expires_at"] == "2026-08-21T12:15:00+00:00"
    assert VERIFICATION_TOKEN not in outbox["template_data_json"]
    encrypted_token = base64.b64decode(
        outbox_data["verification_token_ciphertext"], validate=True
    )
    assert VerificationTokenCipher(settings.read_key("contact")).decrypt(
        encrypted_token
    ) == VERIFICATION_TOKEN


def test_supported_but_invalid_email_keeps_generic_response_without_persistence(
    settings,
):
    with _client(settings, secret_factory=_secrets(VERIFICATION_TOKEN)) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            json={"email": "not-an-email", "turnstile_token": "ok"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "verification_requested"}
    with db.connect(settings.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM contributors").fetchone()[0] == 0
        assert (
            conn.execute("SELECT COUNT(*) FROM submission_sessions").fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM email_outbox").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("verifier", "expected_status"),
    [(RejectingTurnstile(), 400), (UnavailableTurnstile(), 503)],
)
def test_verification_request_maps_turnstile_failures(
    settings, verifier, expected_status
):
    with _client(settings, verifier=verifier) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            json={"email": "person@example.com", "turnstile_token": "sensitive"},
        )

    assert response.status_code == expected_status


def test_verification_requests_are_limited_to_five_per_rotating_ip_hour(settings):
    raw_tokens = [f"verification-token-{index:02d}" * 2 for index in range(6)]
    with _client(settings, secret_factory=_secrets(*raw_tokens)) as client:
        responses = [
            client.post(
                "/submission/v1/verification-requests",
                json={"email": "person@example.com", "turnstile_token": "ok"},
            )
            for _ in range(6)
        ]

    assert [response.status_code for response in responses] == [202] * 5 + [429]
    with db.connect(settings.database_path) as conn:
        rate_rows = conn.execute(
            "SELECT subject_digest FROM rate_limit_events ORDER BY occurred_at"
        ).fetchall()
    assert [row["subject_digest"] for row in rate_rows] == [
        "ad9aa2dec7ddc84ed8ac8ec5ce3b11a9795a9d7c8dbd113f9e1c380277b52c20"
    ] * 5


def test_cf_connecting_ip_is_used_only_when_explicitly_trusted(settings):
    forwarded = "198.51.100.7"
    expected_socket = "ad9aa2dec7ddc84ed8ac8ec5ce3b11a9795a9d7c8dbd113f9e1c380277b52c20"
    expected_forwarded = "3f608f685933636cb050f9af4bdd28158b9078314a855e60866fdb9f4303e7aa"

    with _client(settings, secret_factory=_secrets(VERIFICATION_TOKEN)) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            headers={"CF-Connecting-IP": forwarded},
            json={"email": "person@example.com", "turnstile_token": "ok"},
        )
    assert response.status_code == 202
    with db.connect(settings.database_path) as conn:
        assert conn.execute(
            "SELECT subject_digest FROM rate_limit_events"
        ).fetchone()[0] == expected_socket

    trusted_settings = replace(
        Settings.for_tests(settings.database_path.parent / "trusted"),
        trust_cf_connecting_ip=True,
    )
    with _client(
        trusted_settings, secret_factory=_secrets(VERIFICATION_TOKEN)
    ) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            headers={"CF-Connecting-IP": forwarded},
            json={"email": "person@example.com", "turnstile_token": "ok"},
        )
    assert response.status_code == 202
    with db.connect(trusted_settings.database_path) as conn:
        assert conn.execute(
            "SELECT subject_digest FROM rate_limit_events"
        ).fetchone()[0] == expected_forwarded


def test_malformed_trusted_cf_connecting_ip_is_rejected_without_writes(settings):
    trusted_settings = replace(settings, trust_cf_connecting_ip=True)

    with _client(trusted_settings) as client:
        response = client.post(
            "/submission/v1/verification-requests",
            headers={"CF-Connecting-IP": "not-an-ip"},
            json={"email": "person@example.com", "turnstile_token": "ok"},
        )

    assert response.status_code == 400
    with db.connect(settings.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM rate_limit_events").fetchone()[0] == 0


def test_new_request_revokes_prior_pending_verification_token(settings):
    first = "first-verification-token" * 2
    second = "second-verification-token" * 2
    with _client(settings, secret_factory=_secrets(first, second)) as client:
        for _ in range(2):
            assert client.post(
                "/submission/v1/verification-requests",
                json={"email": "person@example.com", "turnstile_token": "ok"},
            ).status_code == 202

    with db.connect(settings.database_path) as conn:
        rows = conn.execute(
            "SELECT state, token_digest FROM submission_sessions ORDER BY created_at, id"
        ).fetchall()
    assert sorted(row["state"] for row in rows) == ["pending", "revoked"]
    assert {row["token_digest"] for row in rows} == {
        TokenCodec(settings.read_key("token")).digest(first),
        TokenCodec(settings.read_key("token")).digest(second),
    }


def test_exchange_is_single_use_and_installs_24_hour_session_and_csrf_digest(
    settings,
):
    session_codec = TokenCodec(settings.read_key("session"))
    with _client(
        settings,
        secret_factory=_secrets(VERIFICATION_TOKEN, SESSION_TOKEN, CSRF_TOKEN),
    ) as client:
        assert client.post(
            "/submission/v1/verification-requests",
            json={"email": "person@example.com", "turnstile_token": "ok"},
        ).status_code == 202
        response = client.post(
            "/submission/v1/verification-exchanges",
            json={"token": VERIFICATION_TOKEN},
        )
        replay = client.post(
            "/submission/v1/verification-exchanges",
            json={"token": VERIFICATION_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"csrf_token": CSRF_TOKEN}
    assert replay.status_code == 400
    cookie = response.cookies.get("rvi_contribution_session")
    assert cookie is not None
    assert session_codec.verify_session(cookie, int(NOW.timestamp())) == SESSION_TOKEN
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/submission/v1/" in set_cookie

    with db.connect(settings.database_path) as conn:
        contributor = conn.execute("SELECT * FROM contributors").fetchone()
        session = conn.execute("SELECT * FROM submission_sessions").fetchone()
    assert contributor["verified_at"] == "2026-08-21T12:00:00+00:00"
    assert session["state"] == "active"
    assert session["expires_at"] == "2026-08-22T12:00:00+00:00"
    assert session["token_digest"] == session_codec.digest(SESSION_TOKEN)
    assert session["csrf_digest"] == session_codec.digest(CSRF_TOKEN)
    assert SESSION_TOKEN not in (session["token_digest"], session["csrf_digest"])
    assert CSRF_TOKEN not in (session["token_digest"], session["csrf_digest"])


def test_verification_token_expires_after_fifteen_minutes(settings):
    clock = MutableClock(NOW)
    with _client(
        settings,
        clock=clock,
        secret_factory=_secrets(VERIFICATION_TOKEN, SESSION_TOKEN, CSRF_TOKEN),
    ) as client:
        assert client.post(
            "/submission/v1/verification-requests",
            json={"email": "person@example.com", "turnstile_token": "ok"},
        ).status_code == 202
        clock.value = NOW + timedelta(minutes=15)
        response = client.post(
            "/submission/v1/verification-exchanges",
            json={"token": VERIFICATION_TOKEN},
        )

    assert response.status_code == 400
    with db.connect(settings.database_path) as conn:
        assert conn.execute(
            "SELECT state FROM submission_sessions"
        ).fetchone()[0] == "pending"


def test_verification_request_rolls_back_every_write_when_outbox_insert_fails(
    settings,
):
    with _client(settings, secret_factory=_secrets(VERIFICATION_TOKEN)) as client:
        with db.connect(settings.database_path) as conn:
            conn.execute(
                """
                CREATE TRIGGER fail_verification_outbox
                BEFORE INSERT ON email_outbox
                BEGIN
                    SELECT RAISE(ABORT, 'simulated outbox failure');
                END
                """
            )
        with pytest.raises(sqlite3.IntegrityError, match="simulated outbox failure"):
            client.post(
                "/submission/v1/verification-requests",
                json={"email": "person@example.com", "turnstile_token": "ok"},
            )

    with db.connect(settings.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM contributors").fetchone()[0] == 0
        assert (
            conn.execute("SELECT COUNT(*) FROM submission_sessions").fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM email_outbox").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM rate_limit_events").fetchone()[0] == 0
