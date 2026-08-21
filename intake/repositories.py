"""Repositories for the isolated public-submission quarantine."""

import json
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from typing import Any


class RepositoryConflict(RuntimeError):
    """A requested state transition is not currently valid."""


class InvalidVerificationToken(RepositoryConflict):
    """A verification token is missing, expired, or already consumed."""


class SubmissionLimitExceeded(RepositoryConflict):
    """A verified session has reserved all five submissions."""


def _new_id() -> str:
    return str(uuid.uuid4())


def _canonical_uuid(value: Any) -> str:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid submission id") from None
    if not isinstance(value, str) or str(parsed) != value:
        raise ValueError("invalid submission id")
    return value


def _compact_json(value: Any) -> str:
    if isinstance(value, str):
        value = json.loads(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _insert(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    values: Mapping[str, Any],
) -> None:
    selected = [column for column in columns if column in values]
    placeholders = ", ".join("?" for _ in selected)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(selected)}) VALUES ({placeholders})",
        tuple(values[column] for column in selected),
    )


class ContributorRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        email_digest: str,
        email_ciphertext: bytes,
        now: str,
    ) -> str:
        contributor_id = _new_id()
        self.conn.execute(
            """
            INSERT INTO contributors (
                id, email_digest, email_ciphertext, last_activity_at, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (contributor_id, email_digest, email_ciphertext, now, now),
        )
        return contributor_id

    def upsert(
        self,
        email_digest: str,
        email_ciphertext: bytes,
        now: str,
    ) -> sqlite3.Row:
        row = self.find_by_digest(email_digest)
        if row is None:
            contributor_id = self.create(email_digest, email_ciphertext, now)
        else:
            contributor_id = row["id"]
            self.conn.execute(
                """
                UPDATE contributors
                SET email_ciphertext = ?, last_activity_at = ?
                WHERE id = ?
                """,
                (email_ciphertext, now, contributor_id),
            )
        return self.conn.execute(
            "SELECT * FROM contributors WHERE id = ?", (contributor_id,)
        ).fetchone()

    def find_by_digest(self, email_digest: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM contributors WHERE email_digest = ?", (email_digest,)
        ).fetchone()


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_pending(
        self,
        contributor_id: str,
        token_digest: str,
        expires_at: str,
        now: str,
    ) -> str:
        session_id = _new_id()
        self.conn.execute(
            """
            INSERT INTO submission_sessions (
                id, contributor_id, token_digest, state, submission_count,
                expires_at, created_at
            ) VALUES (?, ?, ?, 'pending', 0, ?, ?)
            """,
            (session_id, contributor_id, token_digest, expires_at, now),
        )
        return session_id

    def activate(
        self,
        verification_digest: str,
        session_digest: str,
        csrf_digest: str,
        expires_at: str,
        now: str,
    ) -> sqlite3.Row:
        row = self.conn.execute(
            """
            UPDATE submission_sessions
            SET token_digest = ?, csrf_digest = ?, state = 'active',
                expires_at = ?, consumed_at = ?
            WHERE token_digest = ? AND state = 'pending' AND expires_at > ?
            RETURNING *
            """,
            (
                session_digest,
                csrf_digest,
                expires_at,
                now,
                verification_digest,
                now,
            ),
        ).fetchone()
        if row is None:
            raise InvalidVerificationToken("verification token is not active")
        self.conn.execute(
            """
            UPDATE contributors
            SET verified_at = COALESCE(verified_at, ?), last_activity_at = ?
            WHERE id = ?
            """,
            (now, now, row["contributor_id"]),
        )
        return row

    def authenticate(self, session_digest: str, now: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            SELECT submission_sessions.*
            FROM submission_sessions
            JOIN contributors
              ON contributors.id = submission_sessions.contributor_id
            WHERE submission_sessions.token_digest = ?
              AND submission_sessions.state = 'active'
              AND submission_sessions.expires_at > ?
              AND contributors.blocked_at IS NULL
            """,
            (session_digest, now),
        ).fetchone()

    def reserve_submission(self, session_id: str) -> None:
        cursor = self.conn.execute(
            """
            UPDATE submission_sessions
            SET submission_count = submission_count + 1
            WHERE id = ? AND state = 'active' AND submission_count < 5
            """,
            (session_id,),
        )
        if cursor.rowcount != 1:
            raise SubmissionLimitExceeded("verified session submission limit reached")


class SubmissionRepository:
    _COLUMNS = (
        "id",
        "contributor_id",
        "intent",
        "status",
        "target_component_id",
        "target_edge_key_json",
        "target_namespace",
        "target_identifier",
        "summary",
        "context_json",
        "priority",
        "abuse_digest",
        "terms_version",
        "evidence_license_version",
        "consented_at",
        "public_reason",
        "evidence_state",
        "integration_state",
        "created_at",
        "updated_at",
        "withdrawn_at",
    )
    _CLAIM_COLUMNS = (
        "id",
        "submission_id",
        "claim_type",
        "proposed_json",
        "status",
        "decision_reason_code",
        "created_at",
        "decided_at",
    )

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_with_children(
        self,
        submission: Mapping[str, Any],
        claims: Sequence[Mapping[str, Any]],
        artifacts: Sequence[Mapping[str, Any]],
        capabilities: Sequence[Mapping[str, Any]],
        outbox: Sequence[Mapping[str, Any]],
    ) -> str:
        values = dict(submission)
        submission_id = _canonical_uuid(values["id"]) if "id" in values else _new_id()
        values["id"] = submission_id
        values.setdefault("status", "received")
        values.setdefault("priority", "normal")
        values.setdefault("evidence_state", "pending")
        values.setdefault("integration_state", "not_applicable")
        values["context_json"] = _compact_json(values.get("context_json", {}))
        if values.get("target_edge_key_json") is not None:
            values["target_edge_key_json"] = _compact_json(
                values["target_edge_key_json"]
            )
        _insert(self.conn, "submissions", self._COLUMNS, values)

        for claim in claims:
            claim_values = dict(claim)
            claim_values.update(id=_new_id(), submission_id=submission_id)
            claim_values.setdefault("status", "pending")
            claim_values["proposed_json"] = _compact_json(
                claim_values.get("proposed_json", {})
            )
            _insert(
                self.conn,
                "submission_claims",
                self._CLAIM_COLUMNS,
                claim_values,
            )
        artifact_repository = ArtifactRepository(self.conn)
        for artifact in artifacts:
            artifact_repository.create(submission_id, artifact)
        capability_repository = CapabilityRepository(self.conn)
        for capability in capabilities:
            capability_repository.create(
                submission_id,
                capability["purpose"],
                capability["token_digest"],
                capability["expires_at"],
                capability["created_at"],
            )
        outbox_repository = OutboxRepository(self.conn)
        for message in outbox:
            values = dict(message)
            values["submission_id"] = submission_id
            outbox_repository.enqueue(values)
        return submission_id

    def public_status(self, submission_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, status, public_reason, evidence_state,
                   integration_state, updated_at
            FROM submissions
            WHERE id = ?
            """,
            (submission_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "submission_id": row["id"],
            "status": row["status"],
            "public_reason": row["public_reason"],
            "evidence_state": row["evidence_state"],
            "integration_state": row["integration_state"],
            "updated_at": row["updated_at"],
        }

    def append_follow_up(
        self,
        submission_id: str,
        context_json: Any,
        now: str,
    ) -> None:
        row = self.conn.execute(
            "SELECT status, context_json FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        if row is None or row["status"] != "needs_information":
            raise RepositoryConflict("submission does not accept follow-up evidence")
        context = json.loads(row["context_json"])
        if not isinstance(context, dict):
            raise RepositoryConflict("submission context is not appendable")
        follow_ups = context.setdefault("follow_ups", [])
        if not isinstance(follow_ups, list):
            raise RepositoryConflict("submission follow-up history is not appendable")
        if isinstance(context_json, str):
            context_json = json.loads(context_json)
        follow_ups.append(context_json)
        cursor = self.conn.execute(
            """
            UPDATE submissions
            SET context_json = ?, status = 'under_review', updated_at = ?
            WHERE id = ? AND status = 'needs_information'
            """,
            (_compact_json(context), now, submission_id),
        )
        if cursor.rowcount != 1:
            raise RepositoryConflict("submission does not accept follow-up evidence")

    def withdraw(self, submission_id: str, now: str) -> None:
        cursor = self.conn.execute(
            """
            UPDATE submissions
            SET status = 'withdrawn', withdrawn_at = ?, updated_at = ?
            WHERE id = ?
              AND status IN ('received', 'held', 'under_review', 'needs_information')
              AND integration_state = 'not_applicable'
            """,
            (now, now, submission_id),
        )
        if cursor.rowcount != 1:
            raise RepositoryConflict("submission cannot be withdrawn")


class CapabilityRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        submission_id: str,
        purpose: str,
        token_digest: str,
        expires_at: str,
        now: str,
    ) -> str:
        capability_id = _new_id()
        self.conn.execute(
            """
            INSERT INTO submission_capabilities (
                id, submission_id, purpose, token_digest, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                capability_id,
                submission_id,
                purpose,
                token_digest,
                expires_at,
                now,
            ),
        )
        return capability_id

    def replace(
        self,
        submission_id: str,
        purpose: str,
        token_digest: str,
        expires_at: str,
        now: str,
    ) -> str:
        self.conn.execute(
            """
            UPDATE submission_capabilities
            SET revoked_at = ?
            WHERE submission_id = ? AND purpose = ?
              AND consumed_at IS NULL AND revoked_at IS NULL
            """,
            (now, submission_id, purpose),
        )
        return self.create(submission_id, purpose, token_digest, expires_at, now)

    def authorize(
        self,
        submission_id: str,
        purpose: str,
        token_digest: str,
        now: str,
        *,
        consume: bool = False,
    ) -> sqlite3.Row | None:
        if consume:
            return self.conn.execute(
                """
                UPDATE submission_capabilities
                SET consumed_at = ?
                WHERE submission_id = ? AND purpose = ? AND token_digest = ?
                  AND expires_at > ?
                  AND consumed_at IS NULL AND revoked_at IS NULL
                RETURNING *
                """,
                (now, submission_id, purpose, token_digest, now),
            ).fetchone()
        return self.conn.execute(
            """
            SELECT * FROM submission_capabilities
            WHERE submission_id = ? AND purpose = ? AND token_digest = ?
              AND expires_at > ? AND consumed_at IS NULL AND revoked_at IS NULL
            """,
            (submission_id, purpose, token_digest, now),
        ).fetchone()


class ArtifactRepository:
    _COLUMNS = (
        "id",
        "submission_id",
        "storage_key",
        "original_name",
        "declared_media_type",
        "detected_media_type",
        "raw_sha256",
        "stored_sha256",
        "size_bytes",
        "width",
        "height",
        "scan_status",
        "retention_class",
        "created_at",
        "purge_after",
        "purged_at",
    )

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, submission_id: str, artifact: Mapping[str, Any]) -> str:
        artifact_id = _new_id()
        values = dict(artifact)
        values.update(id=artifact_id, submission_id=submission_id)
        _insert(self.conn, "submission_artifacts", self._COLUMNS, values)
        return artifact_id


class OutboxRepository:
    _COLUMNS = (
        "id",
        "submission_id",
        "template",
        "recipient_ciphertext",
        "template_data_json",
        "state",
        "attempt_count",
        "next_attempt_at",
        "claimed_at",
        "provider_reference",
        "last_error",
        "created_at",
        "updated_at",
        "sent_at",
    )

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def enqueue(self, message: Mapping[str, Any]) -> str:
        message_id = _new_id()
        values = dict(message)
        values["id"] = message_id
        values.setdefault("state", "pending")
        values.setdefault("attempt_count", 0)
        values.setdefault("updated_at", values["created_at"])
        values["template_data_json"] = _compact_json(
            values.get("template_data_json", {})
        )
        _insert(self.conn, "email_outbox", self._COLUMNS, values)
        return message_id


class RateLimitRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def record(self, scope: str, subject_digest: str, now: str) -> str:
        event_id = _new_id()
        self.conn.execute(
            """
            INSERT INTO rate_limit_events (id, scope, subject_digest, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (event_id, scope, subject_digest, now),
        )
        return event_id

    def count_since(self, scope: str, subject_digest: str, since: str) -> int:
        return self.conn.execute(
            """
            SELECT COUNT(*)
            FROM rate_limit_events
            WHERE scope = ? AND subject_digest = ? AND occurred_at >= ?
            """,
            (scope, subject_digest, since),
        ).fetchone()[0]
