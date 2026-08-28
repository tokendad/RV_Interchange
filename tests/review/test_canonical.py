import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from Docs.Tools import observations
from review.canonical import (
    CanonicalIntegrityError,
    CanonicalObservationStore,
    CanonicalPayload,
    canonical_payload_sha256,
)


def initialized_observation_db(tmp_path: Path) -> Path:
    path = tmp_path / "observations.db"
    with observations.get_conn(path) as conn:
        conn.executescript(observations.SCHEMA)
        conn.commit()
    return path


def payload(draft_id="draft-1"):
    return CanonicalPayload(
        draft_id=draft_id,
        submission_id="submission-1",
        source_type="dataplate_photo",
        source_name="Suburban data plate",
        source_url=None,
        raw_content="Model SF-30FQ is visible on the plate.",
        extracted={"model": "SF-30FQ"},
        source_tier=2,
        reviewer_digest="reviewer-digest",
        artifact_ids=("artifact-1",),
    )


def test_canonical_append_is_compatible_and_idempotent(tmp_path):
    path = initialized_observation_db(tmp_path)

    store = CanonicalObservationStore(path)
    first = store.append_or_get(payload())
    replay = store.append_or_get(payload())

    assert replay == first
    with observations.get_conn(path) as conn:
        row = conn.execute("SELECT * FROM observations WHERE id = ?", (first,)).fetchone()
        origin = conn.execute("SELECT * FROM observation_origins").fetchone()
    assert row["extraction_method"] == "reviewed_public_submission"
    assert row["fetched_by"] == "reviewer-digest"
    assert row["source_tier"] == 2
    assert origin["origin_id"] == "draft-1"
    assert origin["canonical_payload_sha256"] == canonical_payload_sha256(payload())


def test_existing_origin_with_different_payload_fails_closed(tmp_path):
    path = initialized_observation_db(tmp_path)
    store = CanonicalObservationStore(path)
    store.append_or_get(payload())

    with pytest.raises(CanonicalIntegrityError, match="origin payload mismatch"):
        store.append_or_get(replace(payload(), raw_content="different"))


def test_store_rejects_a_missing_database_file(tmp_path):
    with pytest.raises(CanonicalIntegrityError, match="initialized observations database"):
        CanonicalObservationStore(tmp_path / "missing.db")


def test_store_rejects_an_uninitialized_database_file(tmp_path):
    path = tmp_path / "uninitialized.db"
    sqlite3.connect(path).close()

    with pytest.raises(CanonicalIntegrityError, match="initialized observations database"):
        CanonicalObservationStore(path)
