import json

from intake import db, repositories
from review.repositories import ReviewConflict, ReviewRepository


def _submission(conn, status="received", priority="normal"):
    contributor = repositories.ContributorRepository(conn).create("digest", b"cipher", "2026-01-01T00:00:00Z")
    sid = repositories.SubmissionRepository(conn).create_with_children({
        "contributor_id": contributor, "intent": "installation_result", "status": status,
        "summary": "Observed fit", "context_json": {"private": "omit"}, "priority": priority,
        "abuse_digest": "abuse", "terms_version": "v1", "evidence_license_version": "v1",
        "consented_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
    }, [{"claim_type": "correction", "proposed_json": {"value": "yes"}, "created_at": "2026-01-01T00:00:00Z"}], [], [], [])
    return sid


def test_queue_detail_decision_and_advisory_are_redacted_and_idempotent(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        sid = _submission(conn, priority="safety")
        review = ReviewRepository(conn)
        page = review.queue(limit=10)
        assert page["items"][0]["priority"] == "safety"
        assert "contributor_id" not in page["items"][0]
        detail = review.detail(sid)
        assert detail["submission"]["context_json"] == json.dumps({"private": "omit"}, separators=(",", ":"), sort_keys=True)
        claim_id = detail["claims"][0]["id"]
        decision = review.decide_claim(sid, claim_id, action="accepted", reason_code="source_verified", note=None, reviewer_digest="reviewer", idempotency_key="k1")
        assert decision["submission_status"] == "accepted"
        assert review.decide_claim(sid, claim_id, action="accepted", reason_code="source_verified", note=None, reviewer_digest="reviewer", idempotency_key="k1")["submission_id"] == sid
        with __import__('pytest').raises(ReviewConflict):
            review.decide_claim(sid, claim_id, action="accepted", reason_code="source_verified", note=None, reviewer_digest="reviewer", idempotency_key="k2")


def test_assessment_never_changes_claim_state(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        sid = _submission(conn)
        review = ReviewRepository(conn)
        claim_id = review.detail(sid)["claims"][0]["id"]
        review.add_assessment(sid, claim_id, assessment="endorse", reason="clear photo", reviewer_digest="r", idempotency_key="a1")
        assert review.detail(sid)["claims"][0]["status"] == "pending"
