import sqlite3

import pytest
from fastapi.testclient import TestClient

from intake.app import create_app
from intake.config import Settings
from intake import db


class _CommitFailingConnection(sqlite3.Connection):
    def commit(self):
        raise sqlite3.OperationalError("simulated commit failure")


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "submissions.db"

    db.migrate(path)
    db.migrate(path)

    with db.connect(path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5_000
        assert [
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        ] == [1]


def test_migration_creates_only_quarantined_intake_tables(tmp_path):
    path = tmp_path / "submissions.db"

    db.migrate(path)

    with db.connect(path) as conn:
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
            )
        }
    assert {
        "schema_migrations",
        "contributors",
        "submission_sessions",
        "submissions",
        "submission_capabilities",
        "submission_claims",
        "submission_artifacts",
        "email_outbox",
        "rate_limit_events",
    } <= names
    assert "observations" not in names
    assert "components" not in names
    assert "edges" not in names


def test_transaction_rolls_back_all_writes(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)

    with db.connect(path) as conn:
        with pytest.raises(RuntimeError, match="abort"):
            with db.transaction(conn):
                conn.execute(
                    """
                    INSERT INTO contributors (
                        id, email_digest, email_ciphertext, last_activity_at, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    ("contributor-1", "digest-1", b"ciphertext", "now", "now"),
                )
                raise RuntimeError("abort")

        assert conn.execute("SELECT COUNT(*) FROM contributors").fetchone()[0] == 0


def test_transaction_rolls_back_when_commit_fails(tmp_path):
    path = tmp_path / "commit-failure.db"
    conn = sqlite3.connect(
        path,
        isolation_level=None,
        factory=_CommitFailingConnection,
    )
    conn.execute("CREATE TABLE pending_write (value TEXT NOT NULL)")

    with pytest.raises(sqlite3.OperationalError, match="simulated commit failure"):
        with db.transaction(conn):
            conn.execute("INSERT INTO pending_write (value) VALUES (?)", ("visible",))

    assert conn.in_transaction is False
    assert conn.execute("SELECT COUNT(*) FROM pending_write").fetchone()[0] == 0
    conn.close()


def test_foreign_keys_and_controlled_states_are_enforced(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)

    with db.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO submission_sessions (
                    id, contributor_id, token_digest, state, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("session-1", "missing", "token", "pending", "later", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO contributors (
                    id, email_digest, email_ciphertext, last_activity_at, created_at,
                    verified_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("contributor-1", "digest", b"ciphertext", "now", "now", None),
            )
            conn.execute(
                """
                INSERT INTO submission_sessions (
                    id, contributor_id, token_digest, state, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "session-1",
                    "contributor-1",
                    "token",
                    "uncontrolled",
                    "later",
                    "now",
                ),
            )


def test_app_lifespan_applies_migrations_without_expanding_health(tmp_path):
    settings = Settings.for_tests(tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get("/health/")

    assert response.json() == {"status": "ok"}
    with db.connect(settings.database_path) as conn:
        assert [
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        ] == [1]
