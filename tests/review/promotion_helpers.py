import json
from pathlib import Path

from Docs.Tools import observations
from intake import repositories
from intake import db
from review.canonical import CanonicalObservationStore
from review.drafts import DraftRepository
from review.promotion import PromotionService


def seed_submission(conn, status="accepted"):
    contributor = repositories.ContributorRepository(conn).create(
        "promotion-contributor-" + status + str(conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]), b"cipher", "2026-01-01T00:00:00Z"
    )
    return repositories.SubmissionRepository(conn).create_with_children(
        {
            "contributor_id": contributor,
            "intent": "installation_result",
            "status": status,
            "summary": "Observed fit",
            "context_json": {},
            "priority": "normal",
            "abuse_digest": "abuse",
            "terms_version": "v1",
            "evidence_license_version": "v1",
            "consented_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        [],
        [],
        [],
        [],
    )


def seed_accepted_claim(conn, submission_id):
    claim_id = "claim-" + submission_id
    conn.execute(
        """INSERT INTO submission_claims
           (id, submission_id, claim_type, proposed_json, status, created_at, decided_at)
           VALUES (?, ?, 'attribute', ?, 'accepted', ?, ?)""",
        (claim_id, submission_id, json.dumps({"model": "SF-30FQ"}),
         "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z"),
    )
    return claim_id


def seed_accepted_evidence(conn):
    submission_id = seed_submission(conn)
    claim_id = seed_accepted_claim(conn, submission_id)
    artifact_id = "artifact-" + submission_id
    conn.execute(
        """INSERT INTO submission_artifacts
           (id, submission_id, storage_key, original_name, declared_media_type,
            detected_media_type, raw_sha256, stored_sha256, size_bytes, width,
            height, scan_status, retention_class, created_at)
           VALUES (?, ?, ?, 'plate.jpg', 'image/jpeg', 'image/jpeg', ?, ?,
                   10, 1, 1, 'clean', 'accepted_evidence', ?)""",
        (artifact_id, submission_id, "storage/" + artifact_id, "a" * 64,
         "b" * 64, "2026-01-01T00:00:00Z"),
    )
    return conn, submission_id, claim_id, artifact_id


class PromotionHarness:
    """Two real SQLite stores for service-level promotion tests."""

    def __init__(self, tmp_path: Path):
        self.intake_path = tmp_path / "submissions.db"
        self.canonical_path = tmp_path / "observations.db"
        db.migrate(self.intake_path)
        with db.connect(self.intake_path) as conn:
            _conn, submission_id, claim_id, artifact_id = seed_accepted_evidence(conn)
            self.submission_id = submission_id
            self.claim_id = claim_id
            self.artifact_id = artifact_id
        with observations.get_conn(self.canonical_path) as conn:
            conn.executescript(observations.SCHEMA)
            conn.commit()
        self.intake_conn = db.connect(self.intake_path)
        self.service = PromotionService(
            self.intake_conn, CanonicalObservationStore(self.canonical_path)
        )

    def __del__(self):
        conn = getattr(self, "intake_conn", None)
        if conn is not None:
            conn.close()

    def draft(self):
        with db.transaction(self.intake_conn):
            return DraftRepository(self.intake_conn).create(
                self.submission_id,
                source_type="dataplate_photo", source_name="Suburban data plate",
                source_url=None, raw_content="Model SF-30FQ is visible.",
                extracted={"model": "SF-30FQ"}, claim_ids=[self.claim_id],
                artifact_ids=[self.artifact_id], reviewer_digest="admin-digest",
                idempotency_key="draft-" + str(self.observation_count() + self.receipt_count()),
            )

    def ready_draft(self):
        draft = self.draft()
        with db.transaction(self.intake_conn):
            return DraftRepository(self.intake_conn).mark_ready(
                draft["id"], expected_version=draft["version"], reviewer_digest="admin-digest"
            )

    def preview(self, draft):
        return self.service.preview(draft["id"], final_source_tier=draft["default_source_tier"])

    def promote(self, draft, preview, *, key):
        with db.transaction(self.intake_conn):
            return self.service.promote(
                draft["id"], expected_version=draft["version"],
                confirmed_payload_sha256=preview["canonical_payload_sha256"],
                idempotency_key=key, final_source_tier=preview["source_tier"],
                reviewer_digest="publisher-digest",
            )

    def observation_count(self):
        with observations.get_conn(self.canonical_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

    def origin_count(self):
        with observations.get_conn(self.canonical_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM observation_origins").fetchone()[0]

    def receipt_count(self):
        return self.intake_conn.execute("SELECT COUNT(*) FROM promotion_receipts").fetchone()[0]

    def submission(self):
        return dict(self.intake_conn.execute("SELECT * FROM submissions WHERE id = ?", (self.submission_id,)).fetchone())

    def linked_artifact(self):
        return dict(self.intake_conn.execute("SELECT * FROM submission_artifacts WHERE id = ?", (self.artifact_id,)).fetchone())
