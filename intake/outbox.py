"""Transactional outbox worker without a production delivery adapter."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from intake import db
from intake.mailer import (
    PermanentMailError,
    TemporaryMailError,
    TransactionalMailer,
    TransactionalMessage,
)
from intake.repositories import OutboxRepository
from intake.security import ContactCipher


_RETRY_DELAYS = (60, 300, 1_800, 7_200, 7_200)
_STALE_AFTER = timedelta(minutes=10)


class OutboxWorker:
    """Claim, deliver, and record at most one ready outbox message."""

    def __init__(
        self,
        database_path: str | Path,
        contact_key: bytes,
        mailer: TransactionalMailer,
        *,
        logger: logging.Logger | None = None,
    ):
        self._database_path = Path(database_path)
        self._contact_cipher = ContactCipher(contact_key)
        self._mailer = mailer
        self._logger = logger or logging.getLogger(__name__)

    def run_once(self, now: datetime) -> bool:
        """Process one ready row, returning false when no work can be claimed."""
        now = _utc(now)
        now_text = now.isoformat()
        stale_before = (now - _STALE_AFTER).isoformat()
        with db.connect(self._database_path) as conn:
            with db.transaction(conn):
                repository = OutboxRepository(conn)
                exhausted_count = repository.fail_stale_exhausted(
                    now_text, stale_before
                )
                row = repository.claim_next(now_text, stale_before)
        if row is None:
            if exhausted_count:
                self._logger.warning("stale outbox message reached retry limit")
            return bool(exhausted_count)

        try:
            message = self._message(row)
        except (TypeError, ValueError, json.JSONDecodeError):
            self._mark_failed(row["id"], "invalid_outbox_payload", now_text)
            self._logger.warning("outbox message payload rejected")
            return True

        try:
            provider_reference = self._mailer.send(message)
        except TemporaryMailError:
            if row["attempt_count"] >= 6:
                self._mark_failed(row["id"], "attempt_limit_reached", now_text)
                self._logger.warning("outbox message reached retry limit")
            else:
                delay = _RETRY_DELAYS[row["attempt_count"] - 1]
                retry_at = (now + timedelta(seconds=delay)).isoformat()
                self._mark_retry(
                    row["id"], retry_at, "temporary_mail_error", now_text
                )
                self._logger.info("outbox message scheduled for retry")
            return True
        except PermanentMailError:
            self._mark_failed(row["id"], "permanent_mail_error", now_text)
            self._logger.warning("outbox message permanently rejected")
            return True

        if provider_reference is not None and not isinstance(
            provider_reference, str
        ):
            self._mark_failed(row["id"], "invalid_provider_reference", now_text)
            self._logger.warning("outbox provider returned an invalid reference")
            return True
        with db.connect(self._database_path) as conn:
            with db.transaction(conn):
                OutboxRepository(conn).mark_sent(
                    row["id"], provider_reference, now_text
                )
        self._logger.info("outbox message sent")
        return True

    def _message(self, row: Any) -> TransactionalMessage:
        recipient = self._contact_cipher.decrypt(row["recipient_ciphertext"])
        template_data = json.loads(row["template_data_json"])
        if not isinstance(template_data, dict):
            raise ValueError("invalid template data")
        return TransactionalMessage(
            message_id=row["id"],
            recipient=recipient,
            template=row["template"],
            template_data=template_data,
            submission_id=row["submission_id"],
        )

    def _mark_retry(
        self, message_id: str, retry_at: str, error_code: str, now: str
    ) -> None:
        with db.connect(self._database_path) as conn:
            with db.transaction(conn):
                OutboxRepository(conn).mark_retry(
                    message_id, retry_at, error_code, now
                )

    def _mark_failed(self, message_id: str, error_code: str, now: str) -> None:
        with db.connect(self._database_path) as conn:
            with db.transaction(conn):
                OutboxRepository(conn).mark_failed(message_id, error_code, now)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("outbox time must be timezone-aware")
    return value.astimezone(timezone.utc)
