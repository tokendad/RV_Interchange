import pytest

from Docs.Tools import observations
from intake import db
from review.canonical import CanonicalObservationStore
from review.drafts import DraftRepository
from review.promotion import PromotionService

from .promotion_helpers import seed_accepted_evidence


class InjectedPostCanonicalFailure(RuntimeError):
    pass


def scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_isolated_promotion_recovery_drill_reconciles_without_catalog(tmp_path):
    intake_path = tmp_path / "intake" / "submissions.db"
    canonical_path = tmp_path / "canonical" / "observations.db"
    components_path = tmp_path / "catalog" / "components.db"

    db.migrate(intake_path)
    with db.connect(intake_path) as intake:
        _conn, submission_id, claim_id, artifact_id = seed_accepted_evidence(intake)
    canonical_path.parent.mkdir()
    with observations.get_conn(canonical_path) as canonical:
        canonical.executescript(observations.SCHEMA)
        canonical.commit()

    intake = db.connect(intake_path)
    try:
        service = PromotionService(
            intake, CanonicalObservationStore(canonical_path)
        )
        with db.transaction(intake):
            draft = DraftRepository(intake).create(
                submission_id,
                source_type="dataplate_photo",
                source_name="Suburban data plate",
                source_url=None,
                raw_content="Model SF-30FQ is visible.",
                extracted={"model": "SF-30FQ"},
                claim_ids=[claim_id],
                artifact_ids=[artifact_id],
                reviewer_digest="admin-digest",
                idempotency_key="drill-draft",
            )
            ready = DraftRepository(intake).mark_ready(
                draft["id"],
                expected_version=draft["version"],
                reviewer_digest="admin-digest",
            )
        preview = service.preview(ready["id"], final_source_tier=2)

        def fail_after_canonical_write():
            raise InjectedPostCanonicalFailure("drill interruption after canonical write")

        service.after_canonical_write = fail_after_canonical_write
        with pytest.raises(InjectedPostCanonicalFailure):
            with db.transaction(intake):
                service.promote(
                    ready["id"],
                    expected_version=ready["version"],
                    confirmed_payload_sha256=preview["canonical_payload_sha256"],
                    idempotency_key="drill-first-attempt",
                    final_source_tier=preview["source_tier"],
                    reviewer_digest="publisher-digest",
                )

        service.after_canonical_write = lambda: None
        with db.transaction(intake):
            service.promote(
                ready["id"],
                expected_version=ready["version"],
                confirmed_payload_sha256=preview["canonical_payload_sha256"],
                idempotency_key="drill-retry",
                final_source_tier=preview["source_tier"],
                reviewer_digest="publisher-digest",
            )

        submission = dict(
            intake.execute(
                "SELECT * FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        )
        with observations.get_conn(canonical_path) as canonical:
            assert scalar(canonical, "SELECT COUNT(*) FROM observations") == 1
            assert scalar(canonical, "SELECT COUNT(*) FROM observation_origins") == 1
        assert scalar(intake, "SELECT COUNT(*) FROM promotion_receipts") == 1
        assert scalar(
            intake,
            "SELECT COUNT(*) FROM promotion_events WHERE action = 'promotion_reconciled'",
        ) == 1
        assert submission["evidence_state"] == "available"
        assert submission["integration_state"] == "pending"
        assert not components_path.exists()
    finally:
        intake.close()
