import hashlib
import hmac

from fastapi.testclient import TestClient

from intake import db, repositories
from review.app import create_app
from review.config import Settings
from review.repositories import ReviewRepository


class Validator:
    def validate(self, assertion):
        return {"email": "admin@example.com"}


def _seed(settings):
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        digest = hmac.new(settings.reviewer_digest_key, b"admin@example.com", hashlib.sha256).hexdigest()
        conn.execute("INSERT INTO reviewer_roles VALUES (?, 'admin', 1, 'now', NULL)", (digest,))
        contributor = repositories.ContributorRepository(conn).create("contact", b"cipher", "now")
        sid = repositories.SubmissionRepository(conn).create_with_children({"contributor_id": contributor, "intent": "data_correction", "status": "received", "summary": "Correction", "context_json": {}, "priority": "high", "abuse_digest": "a", "terms_version": "v1", "evidence_license_version": "v1", "consented_at": "now", "created_at": "now", "updated_at": "now"}, [{"claim_type": "correction", "proposed_json": {"correct": True}, "created_at": "now"}], [], [], [])
        claim_id = ReviewRepository(conn).detail(sid)["claims"][0]["id"]
    return sid, claim_id


def test_review_api_requires_assertion_and_supports_queue_and_decision(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, claim_id = _seed(settings)
    with TestClient(create_app(settings, Validator())) as client:
        assert client.get("/review/v1/queue").status_code == 401
        headers = {"Cf-Access-Jwt-Assertion": "signed"}
        assert client.get("/review/v1/queue", headers=headers).json()["items"][0]["id"] == sid
        response = client.post(f"/review/v1/submissions/{sid}/claims/{claim_id}/decision", headers=headers, json={"action": "accepted", "reason_code": "verified", "idempotency_key": "decision-1"})
        assert response.status_code == 200
        assert response.json()["submission_status"] == "accepted"
        replay = client.post(f"/review/v1/submissions/{sid}/claims/{claim_id}/decision", headers=headers, json={"action": "accepted", "reason_code": "verified", "idempotency_key": "decision-1"})
        assert replay.status_code == 200
