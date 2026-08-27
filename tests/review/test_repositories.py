import json

from intake import db, repositories
from review.repositories import ReviewConflict, ReviewRepository


def _submission(conn, status="received", priority="normal"):
    contributor = repositories.ContributorRepository(conn).create(
        f"digest-{status}-{priority}", b"cipher", "2026-01-01T00:00:00Z"
    )
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


def test_claim_decision_rejects_submission_outside_reviewable_states(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        sid = _submission(conn, status="needs_information")
        review = ReviewRepository(conn)
        claim_id = review.detail(sid)["claims"][0]["id"]

        with __import__("pytest").raises(ReviewConflict):
            review.decide_claim(
                sid,
                claim_id,
                action="accepted",
                reason_code="source_verified",
                note=None,
                reviewer_digest="reviewer",
                idempotency_key="blocked-state",
            )


def test_mixed_terminal_claim_results_make_submission_partially_accepted(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        sid = _submission(conn)
        conn.execute(
            """INSERT INTO submission_claims
               (id, submission_id, claim_type, proposed_json, created_at)
               VALUES ('second-claim', ?, 'correction', '{"value":"no"}',
                       '2026-01-01T00:00:01Z')""",
            (sid,),
        )
        review = ReviewRepository(conn)
        first_claim = review.detail(sid)["claims"][0]["id"]

        review.decide_claim(
            sid,
            first_claim,
            action="accepted",
            reason_code="source_verified",
            note=None,
            reviewer_digest="reviewer",
            idempotency_key="first",
        )
        result = review.decide_claim(
            sid,
            "second-claim",
            action="rejected",
            reason_code="not_supported",
            note=None,
            reviewer_digest="reviewer",
            idempotency_key="second",
        )

    assert result["submission_status"] == "partially_accepted"


def test_all_duplicate_claims_make_submission_duplicate(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        sid = _submission(conn)
        review = ReviewRepository(conn)
        claim_id = review.detail(sid)["claims"][0]["id"]
        result = review.decide_claim(
            sid,
            claim_id,
            action="duplicate",
            reason_code="existing_submission",
            note=None,
            reviewer_digest="reviewer",
            idempotency_key="duplicate",
        )

    assert result["submission_status"] == "duplicate"


def test_queue_cursor_preserves_priority_order_across_pages(tmp_path):
    path = tmp_path / "submissions.db"
    db.migrate(path)
    with db.connect(path) as conn:
        high_id = _submission(conn, priority="high")
        safety_id = _submission(conn, priority="safety")
        conn.execute(
            "UPDATE submissions SET created_at = '2026-01-03T00:00:00Z' WHERE id = ?",
            (safety_id,),
        )
        review = ReviewRepository(conn)

        first = review.queue(limit=1)
        second = review.queue(cursor=first["next_cursor"], limit=1)

    assert first["items"][0]["id"] == safety_id
    assert second["items"][0]["id"] == high_id
