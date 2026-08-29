"""Append-only boundary for public-submission observations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from Docs.Tools import observations


_ORIGIN_TYPE = "public_submission_draft"
_ORIGIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS observation_origins (
    observation_id INTEGER PRIMARY KEY REFERENCES observations(id),
    origin_type TEXT NOT NULL CHECK (origin_type = 'public_submission_draft'),
    origin_id TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    artifact_ids_json TEXT NOT NULL CHECK (json_valid(artifact_ids_json)),
    canonical_payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(origin_type, origin_id)
);
"""


class CanonicalIntegrityError(RuntimeError):
    """The canonical store cannot safely satisfy a promotion request."""


@dataclass(frozen=True)
class CanonicalPayload:
    draft_id: str
    submission_id: str
    source_type: str
    source_name: str
    source_url: str | None
    raw_content: str
    extracted: dict | None
    source_tier: int
    reviewer_digest: str
    artifact_ids: tuple[str, ...]


def canonical_payload_sha256(payload: CanonicalPayload) -> str:
    confirmed = {
        "draft_id": payload.draft_id,
        "submission_id": payload.submission_id,
        "source_type": payload.source_type,
        "source_name": payload.source_name,
        "source_url": payload.source_url,
        "raw_content": payload.raw_content,
        "extracted": payload.extracted,
        "source_tier": payload.source_tier,
        "artifact_ids": sorted(payload.artifact_ids),
    }
    encoded = json.dumps(
        confirmed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CanonicalObservationStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._ensure_initialized_store()

    def _ensure_initialized_store(self) -> None:
        if not self.path.is_file():
            raise CanonicalIntegrityError("initialized observations database is required")
        with observations.get_conn(self.path) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'observations'"
            ).fetchone()
            if row is None:
                raise CanonicalIntegrityError("initialized observations database is required")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(_ORIGIN_SCHEMA)
            conn.commit()

    def append_or_get(self, payload: CanonicalPayload) -> int:
        digest = canonical_payload_sha256(payload)
        with observations.get_conn(self.path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN IMMEDIATE")
            existing = self._origin_for_draft(conn, payload.draft_id)
            if existing is not None:
                return self._matching_origin_id(existing, digest)
            try:
                observation_id = observations.append_observation(
                    conn,
                    source_type=payload.source_type,
                    source_name=payload.source_name,
                    url=payload.source_url,
                    raw_content=payload.raw_content,
                    extracted=payload.extracted,
                    extraction_method="reviewed_public_submission",
                    fetched_by=payload.reviewer_digest,
                    source_tier=payload.source_tier,
                )
                conn.execute(
                    """INSERT INTO observation_origins
                       (observation_id, origin_type, origin_id, submission_id,
                        artifact_ids_json, canonical_payload_sha256, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        observation_id,
                        _ORIGIN_TYPE,
                        payload.draft_id,
                        payload.submission_id,
                        json.dumps(sorted(payload.artifact_ids)),
                        digest,
                        observations.now_iso(),
                    ),
                )
                conn.commit()
                return observation_id
            except sqlite3.IntegrityError as error:
                conn.rollback()

        with observations.get_conn(self.path) as conn:
            existing = self._origin_for_draft(conn, payload.draft_id)
            if existing is None:
                raise error
            return self._matching_origin_id(existing, digest)

    def find_origin(self, draft_id: str) -> dict | None:
        with observations.get_conn(self.path) as conn:
            row = self._origin_for_draft(conn, draft_id)
        return dict(row) if row is not None else None

    def promoting_digest(self, observation_id: int) -> str:
        with observations.get_conn(self.path) as conn:
            row = conn.execute(
                "SELECT fetched_by FROM observations WHERE id = ?", (observation_id,)
            ).fetchone()
        if row is None:
            raise CanonicalIntegrityError("canonical observation does not exist")
        return row["fetched_by"]

    @staticmethod
    def _origin_for_draft(conn, draft_id: str):
        return conn.execute(
            """SELECT observation_id, canonical_payload_sha256
               FROM observation_origins
               WHERE origin_type = ? AND origin_id = ?""",
            (_ORIGIN_TYPE, draft_id),
        ).fetchone()

    @staticmethod
    def _matching_origin_id(origin, digest: str) -> int:
        if origin["canonical_payload_sha256"] != digest:
            raise CanonicalIntegrityError("origin payload mismatch")
        return origin["observation_id"]
