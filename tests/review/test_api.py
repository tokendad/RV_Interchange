import hashlib
import hmac
import time
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from Docs.Tools import observations
from intake import db, repositories
from review.app import create_app
from review.auth import AccessTokenValidator
from review.config import Settings
from review.repositories import ReviewRepository
from tests.review.promotion_helpers import seed_accepted_evidence


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


def test_trusted_detail_does_not_expose_admin_notes(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    sid, claim_id = _seed(settings)
    admin_validator, admin_headers = _auth(settings, "admin@example.com")
    with db.connect(settings.database_path) as conn:
        digest = hmac.new(settings.reviewer_digest_key, b"trusted@example.com", hashlib.sha256).hexdigest()
        conn.execute("INSERT INTO reviewer_roles VALUES (?, 'trusted', 1, 'now', NULL)", (digest,))
    trusted_validator, trusted_headers = _auth(settings, "trusted@example.com")
    with TestClient(create_app(settings, admin_validator)) as client:
        response = client.post(
            f"/review/v1/submissions/{sid}/claims/{claim_id}/decision",
            headers=admin_headers,
            json={"action": "accepted", "reason_code": "verified", "note": "internal-only", "idempotency_key": "note-1"},
        )
    with TestClient(create_app(settings, trusted_validator)) as client:
        detail = client.get(f"/review/v1/submissions/{sid}", headers=trusted_headers)

    assert response.status_code == 200
    assert detail.status_code == 200
    assert "note" not in detail.json()["audit"][0]
    assert "internal-only" not in detail.text


def test_admin_creates_and_readies_draft_while_trusted_detail_hides_it(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        _conn, submission_id, claim_id, artifact_id = seed_accepted_evidence(conn)
        admin_digest = hmac.new(
            settings.reviewer_digest_key, b"admin@example.com", hashlib.sha256
        ).hexdigest()
        trusted_digest = hmac.new(
            settings.reviewer_digest_key, b"trusted@example.com", hashlib.sha256
        ).hexdigest()
        conn.execute(
            "INSERT INTO reviewer_roles VALUES (?, 'admin', 1, 'now', NULL)",
            (admin_digest,),
        )
        conn.execute(
            "INSERT INTO reviewer_roles VALUES (?, 'trusted', 1, 'now', NULL)",
            (trusted_digest,),
        )
    admin_validator, admin_headers = _auth(settings, "admin@example.com")
    trusted_validator, trusted_headers = _auth(settings, "trusted@example.com")
    payload = {
        "source_type": "dataplate_photo",
        "source_name": "Suburban data plate",
        "source_url": None,
        "raw_content": "Model SF-30FQ is visible.",
        "extracted": {"model": "SF-30FQ"},
        "claim_ids": [claim_id],
        "artifact_ids": [artifact_id],
        "idempotency_key": "draft-1",
    }

    with TestClient(create_app(settings, admin_validator)) as client:
        created = client.post(
            f"/review/v1/submissions/{submission_id}/observation-drafts",
            headers=admin_headers,
            json=payload,
        )
        assert created.status_code == 201
        draft = created.json()
        ready = client.post(
            f"/review/v1/observation-drafts/{draft['id']}/ready",
            headers=admin_headers,
            json={"expected_version": draft["version"]},
        )
        detail = client.get(
            f"/review/v1/submissions/{submission_id}", headers=admin_headers
        )

    assert ready.status_code == 200
    assert ready.json()["state"] == "ready"
    assert detail.status_code == 200
    assert detail.json()["drafts"] == [
        {
            "id": draft["id"],
            "submission_id": submission_id,
            "source_type": "dataplate_photo",
            "source_name": "Suburban data plate",
            "source_url": None,
            "extracted": {"model": "SF-30FQ"},
            "default_source_tier": 2,
            "state": "ready",
            "version": 2,
            "created_at": draft["created_at"],
            "updated_at": ready.json()["updated_at"],
            "claim_ids": [claim_id],
            "artifact_ids": [artifact_id],
        }
    ]
    assert "raw_content" not in detail.text
    assert "created_by_digest" not in detail.text
    assert "idempotency_key" not in detail.text

    with TestClient(create_app(settings, trusted_validator)) as client:
        denied = client.post(
            f"/review/v1/submissions/{submission_id}/observation-drafts",
            headers=trusted_headers,
            json=payload,
        )
        trusted_detail = client.get(
            f"/review/v1/submissions/{submission_id}", headers=trusted_headers
        )

    assert denied.status_code == 403
    assert trusted_detail.status_code == 200
    assert "drafts" not in trusted_detail.json()


def test_draft_routes_reject_unexpected_request_fields(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        _conn, submission_id, claim_id, artifact_id = seed_accepted_evidence(conn)
        digest = hmac.new(
            settings.reviewer_digest_key, b"admin@example.com", hashlib.sha256
        ).hexdigest()
        conn.execute(
            "INSERT INTO reviewer_roles VALUES (?, 'admin', 1, 'now', NULL)", (digest,)
        )
    validator, headers = _auth(settings, "admin@example.com")
    draft_payload = {
        "source_type": "manufacturer_pdf",
        "source_name": "Manufacturer sheet",
        "source_url": None,
        "raw_content": "Model SF-30FQ is visible.",
        "extracted": {"model": "SF-30FQ"},
        "claim_ids": [claim_id],
        "artifact_ids": [artifact_id],
        "idempotency_key": "draft-extra",
        "unexpected": "value",
    }

    with TestClient(create_app(settings, validator)) as client:
        rejected_create = client.post(
            f"/review/v1/submissions/{submission_id}/observation-drafts",
            headers=headers,
            json=draft_payload,
        )
        rejected_extracted = client.post(
            f"/review/v1/submissions/{submission_id}/observation-drafts",
            headers=headers,
            json={
                key: value
                for key, value in draft_payload.items()
                if key != "unexpected"
            }
            | {
                "extracted": {"model_number": "SF-30FQ"},
            },
        )
        rejected_ready = client.post(
            "/review/v1/observation-drafts/not-a-draft/ready",
            headers=headers,
            json={"expected_version": 1, "unexpected": "value"},
        )

    assert rejected_create.status_code == 422
    assert rejected_extracted.status_code == 422
    assert rejected_ready.status_code == 422


def test_publisher_preview_and_promotion_require_all_authorization(tmp_path):
    settings = Settings.for_tests(tmp_path / "review")
    db.migrate(settings.database_path)
    with db.connect(settings.database_path) as conn:
        _conn, submission_id, claim_id, artifact_id = seed_accepted_evidence(conn)
        admin_digest = hmac.new(settings.reviewer_digest_key, b"admin@example.com", hashlib.sha256).hexdigest()
        publisher_digest = hmac.new(settings.reviewer_digest_key, b"publisher@example.com", hashlib.sha256).hexdigest()
        conn.execute("INSERT INTO reviewer_roles VALUES (?, 'admin', 1, 'now', NULL)", (admin_digest,))
        conn.execute("INSERT INTO reviewer_capabilities VALUES (?, 'publisher', 1, 'now', NULL)", (admin_digest,))
        conn.execute("INSERT INTO reviewer_roles VALUES (?, 'trusted', 1, 'now', NULL)", (publisher_digest,))
        conn.execute("INSERT INTO reviewer_capabilities VALUES (?, 'publisher', 1, 'now', NULL)", (publisher_digest,))
    with observations.get_conn(settings.observations_database_path) as conn:
        conn.executescript(observations.SCHEMA)
        conn.commit()
    admin_validator, admin_headers = _auth(settings, "admin@example.com")
    publisher_validator, publisher_headers = _auth(settings, "publisher@example.com")
    draft_payload = {
        "source_type": "manufacturer_pdf", "source_name": "Install sheet",
        "source_url": None, "raw_content": "Model SF-30FQ.",
        "extracted": {"model": "SF-30FQ"}, "claim_ids": [claim_id],
        "artifact_ids": [artifact_id], "idempotency_key": "draft-promotion",
    }
    with TestClient(create_app(settings, admin_validator)) as client:
        created = client.post(f"/review/v1/submissions/{submission_id}/observation-drafts", headers=admin_headers, json=draft_payload)
        draft = created.json()
        ready = client.post(f"/review/v1/observation-drafts/{draft['id']}/ready", headers=admin_headers, json={"expected_version": 1})
        preview = client.get(f"/review/v1/observation-drafts/{draft['id']}/canonical-preview?final_source_tier=2", headers=admin_headers)
        promoted = client.post(f"/review/v1/observation-drafts/{draft['id']}/promotions", headers=admin_headers, json={
            "expected_version": 2,
            "canonical_payload_sha256": preview.json()["canonical_payload_sha256"],
            "idempotency_key": "promotion-api-1", "final_source_tier": 2,
        })
    with TestClient(create_app(settings, publisher_validator)) as client:
        denied = client.get(f"/review/v1/observation-drafts/{draft['id']}/canonical-preview?final_source_tier=2", headers=publisher_headers)
    assert created.status_code == 201
    assert ready.status_code == 200
    assert preview.status_code == 200
    assert promoted.status_code == 200
    assert denied.status_code == 403
