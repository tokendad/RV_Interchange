"""SQLite connection and migration boundaries for quarantined intake data."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


MIGRATIONS = Path(__file__).with_name("migrations")


def connect(path: str | Path) -> sqlite3.Connection:
    """Open an explicitly transactional SQLite connection with safe pragmas."""
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Own one immediate transaction and roll back every failed write."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


def migrate(path: str | Path) -> None:
    """Apply every numbered migration once, atomically and in order."""
    migration_files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
    with connect(path) as conn:
        with transaction(conn):
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = {
                row["version"]
                for row in conn.execute("SELECT version FROM schema_migrations")
            }
            for migration_file in migration_files:
                version = int(migration_file.name.split("_", 1)[0])
                if version in applied:
                    continue
                for statement in _sql_statements(migration_file.read_text()):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(timezone.utc).isoformat()),
                )


def _sql_statements(script: str) -> Iterator[str]:
    """Split a migration without sqlite3.executescript's implicit commit."""
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statement = pending.strip()
            pending = ""
            if statement:
                yield statement
    if pending.strip():
        raise ValueError("migration ends with an incomplete SQL statement")
