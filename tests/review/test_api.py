import hashlib
import hmac
import time
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from intake import db, repositories
from review.app import create_app
from review.auth import AccessTokenValidator
from review.config import Settings
from review.repositories import ReviewRepository


class JwksClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, _assertion):
        return SimpleNamespace(key=self.key)


def _auth(settings, email):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": settings.access_issuer,
            "aud": settings.access_audience,
            "iat": now,
            "exp": now + 300,
            "email": email,
        },
        private_key,
        algorithm="RS256",
    )
    validator = AccessTokenValidator(
        settings, JwksClient(private_key.public_key())
    )
    return validator, {"Cf-Access-Jwt-Assertion": assertion}


def _seed(settings, email="admin@example.com", role="admin"):
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        digest = hmac.new(
            settings.reviewer_digest_key, email.encode(), hashlib.sha256
        ).hexdigest()
        conn.execute(
            "INSERT INTO reviewer_roles VALUES (?, ?, 1, 'now', NULL)",
            (digest, role),
        )
        contributor = repositories.ContributorRepository(conn).create("contact", b"cipher", "now")
        sid = repositories.SubmissionRepository(conn).create_with_children({"contributor_id": contributor, "intent": "data_correction", "status": "received", "summary": "Correction", "context_json": {}, "priority": "high", "abuse_digest": "a", "terms_version": "v1", "evidence_license_version": "v1", "consented_at": "now", "created_at": "now", "updated_at": "now"}, [{"claim_type": "correction", "proposed_json": {"correct": True}, "created_at": "now"}], [], [], [])
        claim_id = ReviewRepository(conn).detail(sid)["claims"][0]["id"]
    return sid, claim_id


def test_review_api_requires_assertion_and_supports_queue_and_decision(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, claim_id = _seed(settings)
    validator, headers = _auth(settings, "admin@example.com")
    with TestClient(create_app(settings, validator)) as client:
        assert client.get("/review/v1/queue").status_code == 401
        assert client.get("/review/v1/queue", headers=headers).json()["items"][0]["id"] == sid
        response = client.post(f"/review/v1/submissions/{sid}/claims/{claim_id}/decision", headers=headers, json={"action": "accepted", "reason_code": "verified", "idempotency_key": "decision-1"})
        assert response.status_code == 200
        assert response.json()["submission_status"] == "accepted"
        replay = client.post(f"/review/v1/submissions/{sid}/claims/{claim_id}/decision", headers=headers, json={"action": "accepted", "reason_code": "verified", "idempotency_key": "decision-1"})
        assert replay.status_code == 200
        assert replay.json() == response.json()
        collision = client.post(f"/review/v1/submissions/{sid}/claims/{claim_id}/decision", headers=headers, json={"action": "rejected", "reason_code": "different", "idempotency_key": "decision-1"})
        assert collision.status_code == 409
        assert client.get("/review/v1/queue?cursor=bad", headers=headers).status_code == 422


def test_request_information_replay_is_stable_and_redacted(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, _claim_id = _seed(settings)
    validator, headers = _auth(settings, "admin@example.com")
    payload = {
        "reason": "Please provide the model label photo.",
        "idempotency_key": "information-1",
    }

    with TestClient(create_app(settings, validator)) as client:
        first = client.post(
            f"/review/v1/submissions/{sid}/request-information",
            headers=headers,
            json=payload,
        )
        replay = client.post(
            f"/review/v1/submissions/{sid}/request-information",
            headers=headers,
            json=payload,
        )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json() == {
        "submission_id": sid,
        "status": "needs_information",
    }


def test_trusted_assessment_replay_is_stable_without_internal_identity(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, claim_id = _seed(
        settings, email="trusted@example.com", role="trusted"
    )
    validator, headers = _auth(settings, "trusted@example.com")
    payload = {
        "assessment": "endorse",
        "reason": "The evidence supports this claim.",
        "idempotency_key": "assessment-1",
    }

    with TestClient(create_app(settings, validator)) as client:
        denied = client.post(
            f"/review/v1/submissions/{sid}/claims/{claim_id}/decision",
            headers=headers,
            json={
                "action": "accepted",
                "reason_code": "verified",
                "idempotency_key": "trusted-decision-1",
            },
        )
        first = client.post(
            f"/review/v1/submissions/{sid}/claims/{claim_id}/assessment",
            headers=headers,
            json=payload,
        )
        replay = client.post(
            f"/review/v1/submissions/{sid}/claims/{claim_id}/assessment",
            headers=headers,
            json=payload,
        )

    assert denied.status_code == 403
    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json() == {
        "submission_id": sid,
        "claim_id": claim_id,
        "assessment": "endorse",
    }


def test_detail_exposes_redacted_advisory_audit(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, claim_id = _seed(
        settings, email="trusted@example.com", role="trusted"
    )
    validator, headers = _auth(settings, "trusted@example.com")
    with TestClient(create_app(settings, validator)) as client:
        response = client.post(
            f"/review/v1/submissions/{sid}/claims/{claim_id}/assessment",
            headers=headers,
            json={
                "assessment": "dispute",
                "reason": "The source is ambiguous.",
                "idempotency_key": "audit-1",
            },
        )
        detail = client.get(
            f"/review/v1/submissions/{sid}", headers=headers
        )

    assert response.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["audit"][0]["assessment"] == "dispute"
    assert "reviewer_digest" not in detail.json()["audit"][0]
