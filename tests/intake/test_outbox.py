import base64
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

from intake import db
from intake.mailer import (
    PermanentMailError,
    TemporaryMailError,
)
from intake.outbox import OutboxWorker
from intake.repositories import OutboxRepository
from intake.security import ContactCipher, VerificationTokenCipher


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
CONTACT_KEY = b"c" * 32
RECIPIENT = "person@example.com"
SECRET_TEMPLATE_VALUE = "private-verification-token"


class FakeMailer:
    def __init__(self, *, outcome=None, database_path=None):
        self.outcome = outcome
        self.database_path = database_path
        self.messages = []
        self.state_during_send = None

    def send(self, message):
        self.messages.append(message)
        if self.database_path is not None:
            with db.connect(self.database_path) as conn:
                self.state_during_send = conn.execute(
                    "SELECT state FROM email_outbox"
                ).fetchone()[0]
                with db.transaction(conn):
                    conn.execute(
                        "INSERT INTO rate_limit_events "
                        "(id, scope, subject_digest, occurred_at) "
                        "VALUES ('probe', 'outbox-test', 'probe', ?)",
                        (NOW.isoformat(),),
                    )
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def outbox_path(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    return path


def _enqueue(path, *, now=NOW, ciphertext=None):
    ciphertext = ciphertext or ContactCipher(CONTACT_KEY).encrypt(RECIPIENT)
    encrypted_token = VerificationTokenCipher(CONTACT_KEY).encrypt(
        SECRET_TEMPLATE_VALUE
    )
    with db.connect(path) as conn:
        with db.transaction(conn):
            return OutboxRepository(conn).enqueue(
                {
                    "template": "verify_email",
                    "recipient_ciphertext": ciphertext,
                    "template_data_json": {
                        "expires_at": "2026-08-21T12:15:00+00:00",
                        "verification_token_ciphertext": base64.b64encode(
                            encrypted_token
                        ).decode("ascii"),
                    },
                    "next_attempt_at": now.isoformat(),
                    "created_at": now.isoformat(),
                }
            )


def _row(path):
    with db.connect(path) as conn:
        return dict(conn.execute("SELECT * FROM email_outbox").fetchone())


def test_success_claims_commits_sends_and_records_provider_reference(outbox_path):
    _enqueue(outbox_path)
    mailer = FakeMailer(outcome="provider-reference", database_path=outbox_path)
    worker = OutboxWorker(outbox_path, CONTACT_KEY, mailer)

    assert worker.run_once(NOW) is True

    assert mailer.state_during_send == "sending"
    assert len(mailer.messages) == 1
    message = mailer.messages[0]
    assert message.recipient == RECIPIENT
    assert message.template == "verify_email"
    assert message.template_data == {
        "expires_at": "2026-08-21T12:15:00+00:00",
        "verification_token": SECRET_TEMPLATE_VALUE,
    }
    row = _row(outbox_path)
    assert row["state"] == "sent"
    assert row["attempt_count"] == 1
    assert row["provider_reference"] == "provider-reference"
    assert row["sent_at"] == NOW.isoformat()


def test_run_once_returns_false_when_no_message_is_ready(outbox_path):
    mailer = FakeMailer()

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is False
    assert mailer.messages == []


@pytest.mark.parametrize(
    ("prior_attempts", "delay_seconds"),
    [(0, 60), (1, 300), (2, 1_800), (3, 7_200)],
)
def test_temporary_failure_uses_bounded_retry_delays(
    outbox_path, prior_attempts, delay_seconds
):
    _enqueue(outbox_path)
    with db.connect(outbox_path) as conn:
        conn.execute(
            "UPDATE email_outbox SET attempt_count = ?", (prior_attempts,)
        )
    mailer = FakeMailer(outcome=TemporaryMailError("provider unavailable"))

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is True

    row = _row(outbox_path)
    assert row["state"] == "retry"
    assert row["attempt_count"] == prior_attempts + 1
    assert row["next_attempt_at"] == (
        NOW + timedelta(seconds=delay_seconds)
    ).isoformat()
    assert row["last_error"] == "temporary_mail_error"


def test_sixth_temporary_failure_reaches_attempt_ceiling(outbox_path):
    _enqueue(outbox_path)
    with db.connect(outbox_path) as conn:
        conn.execute("UPDATE email_outbox SET attempt_count = 5")

    worker = OutboxWorker(
        outbox_path,
        CONTACT_KEY,
        FakeMailer(outcome=TemporaryMailError("still unavailable")),
    )

    assert worker.run_once(NOW) is True
    row = _row(outbox_path)
    assert row["state"] == "failed"
    assert row["attempt_count"] == 6
    assert row["last_error"] == "attempt_limit_reached"


def test_permanent_failure_is_not_retried(outbox_path):
    _enqueue(outbox_path)
    worker = OutboxWorker(
        outbox_path,
        CONTACT_KEY,
        FakeMailer(outcome=PermanentMailError("hard bounce")),
    )

    assert worker.run_once(NOW) is True

    row = _row(outbox_path)
    assert row["state"] == "failed"
    assert row["attempt_count"] == 1
    assert row["last_error"] == "permanent_mail_error"


def test_stale_sending_message_is_recovered(outbox_path):
    _enqueue(outbox_path)
    stale_claim = NOW - timedelta(minutes=11)
    with db.connect(outbox_path) as conn:
        conn.execute(
            "UPDATE email_outbox "
            "SET state = 'sending', attempt_count = 1, claimed_at = ?",
            (stale_claim.isoformat(),),
        )
    mailer = FakeMailer(outcome="recovered-reference")

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is True

    row = _row(outbox_path)
    assert row["state"] == "sent"
    assert row["attempt_count"] == 2
    assert row["provider_reference"] == "recovered-reference"


def test_recent_sending_message_is_not_reclaimed(outbox_path):
    _enqueue(outbox_path)
    with db.connect(outbox_path) as conn:
        conn.execute(
            "UPDATE email_outbox "
            "SET state = 'sending', attempt_count = 1, claimed_at = ?",
            ((NOW - timedelta(minutes=9)).isoformat(),),
        )
    mailer = FakeMailer()

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is False
    assert mailer.messages == []


def test_stale_sixth_attempt_fails_without_a_seventh_delivery(outbox_path):
    _enqueue(outbox_path)
    with db.connect(outbox_path) as conn:
        conn.execute(
            "UPDATE email_outbox "
            "SET state = 'sending', attempt_count = 6, claimed_at = ?",
            ((NOW - timedelta(minutes=11)).isoformat(),),
        )
    mailer = FakeMailer()

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is True

    assert mailer.messages == []
    row = _row(outbox_path)
    assert row["state"] == "failed"
    assert row["attempt_count"] == 6
    assert row["last_error"] == "attempt_limit_reached"


def test_invalid_encrypted_recipient_fails_without_calling_mailer(outbox_path):
    _enqueue(outbox_path, ciphertext=b"invalid-ciphertext")
    mailer = FakeMailer()

    assert OutboxWorker(outbox_path, CONTACT_KEY, mailer).run_once(NOW) is True

    assert mailer.messages == []
    row = _row(outbox_path)
    assert row["state"] == "failed"
    assert row["last_error"] == "invalid_outbox_payload"


def test_logs_and_persisted_errors_do_not_reflect_mail_secrets(
    outbox_path, caplog
):
    _enqueue(outbox_path)
    provider_detail = f"failed for {RECIPIENT}: {SECRET_TEMPLATE_VALUE}"
    logger = logging.getLogger("tests.intake.outbox")
    mailer = FakeMailer(outcome=TemporaryMailError(provider_detail))

    with caplog.at_level(logging.INFO, logger=logger.name):
        assert OutboxWorker(
            outbox_path, CONTACT_KEY, mailer, logger=logger
        ).run_once(NOW) is True

    persisted_error = json.dumps(_row(outbox_path)["last_error"])
    combined = caplog.text + persisted_error
    assert RECIPIENT not in combined
    assert SECRET_TEMPLATE_VALUE not in combined
    assert provider_detail not in combined
