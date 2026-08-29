import pytest

from intake import db
from review.drafts import DraftConflict, DraftRepository
from .promotion_helpers import seed_accepted_claim, seed_accepted_evidence, seed_submission


@pytest.fixture
def seeded_accepted(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        yield seed_accepted_evidence(conn)


def test_create_and_ready_draft_normalizes_and_links_evidence(seeded_accepted):
    conn, submission_id, claim_id, artifact_id = seeded_accepted
    drafts = DraftRepository(conn)
    draft = drafts.create(
        submission_id, source_type="dataplate_photo", source_name="Suburban data plate",
        source_url=None, raw_content="Model SF-30FQ is visible.",
        extracted={"model": "SF-30FQ"}, claim_ids=[claim_id], artifact_ids=[artifact_id],
        reviewer_digest="admin-digest", idempotency_key="draft-1",
    )
    ready = drafts.mark_ready(draft["id"], expected_version=1, reviewer_digest="admin-digest")
    assert draft["extracted"] == {"model": "SF-30FQ"}
    assert draft["default_source_tier"] == 2
    assert ready["state"] == "ready"
    assert ready["version"] == 2
    assert [event["action"] for event in drafts.events(draft["id"])] == ["draft_created", "draft_ready"]


def test_draft_rejects_claim_from_another_submission(seeded_accepted):
    conn, submission_id, _claim_id, artifact_id = seeded_accepted
    other_claim = seed_accepted_claim(conn, seed_submission(conn))
    with pytest.raises(DraftConflict, match="accepted claim does not belong"):
        DraftRepository(conn).create(
            submission_id, source_type="field_report", source_name="Owner field report",
            source_url=None, raw_content="Observed installation.", extracted={"model": "SW6DE"},
            claim_ids=[other_claim], artifact_ids=[artifact_id], reviewer_digest="admin-digest",
            idempotency_key="wrong-submission",
        )


def test_draft_idempotency_conflict_is_rejected(seeded_accepted):
    conn, submission_id, claim_id, artifact_id = seeded_accepted
    drafts = DraftRepository(conn)
    drafts.create(submission_id, source_type="field_report", source_name="Field", source_url=None,
                  raw_content="Observed.", extracted={"model": "SF-30FQ"}, claim_ids=[claim_id],
                  artifact_ids=[artifact_id], reviewer_digest="r", idempotency_key="same")
    with pytest.raises(DraftConflict, match="idempotency key conflict"):
        drafts.create(submission_id, source_type="field_report", source_name="Changed", source_url=None,
                      raw_content="Observed.", extracted={"model": "SF-30FQ"}, claim_ids=[claim_id],
                      artifact_ids=[artifact_id], reviewer_digest="r", idempotency_key="same")


def test_draft_requires_clean_artifact_and_accepted_claim(seeded_accepted):
    conn, submission_id, claim_id, artifact_id = seeded_accepted
    conn.execute("UPDATE submission_artifacts SET scan_status = 'pending' WHERE id = ?", (artifact_id,))
    with pytest.raises(DraftConflict, match="clean scan status"):
        DraftRepository(conn).create(submission_id, source_type="other", source_name="x", source_url=None,
                                     raw_content="x", extracted={"model": "SF-30FQ"}, claim_ids=[claim_id],
                                     artifact_ids=[artifact_id], reviewer_digest="r", idempotency_key="bad")
