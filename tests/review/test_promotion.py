import pytest

from review.promotion import PromotionConflict, PromotionService

from .promotion_helpers import PromotionHarness


@pytest.fixture
def promotion_harness(tmp_path):
    return PromotionHarness(tmp_path)


def test_ready_draft_promotes_once(promotion_harness):
    draft = promotion_harness.ready_draft()
    preview = promotion_harness.service.preview(draft["id"], final_source_tier=2)
    receipt = promotion_harness.service.promote(
        draft["id"], expected_version=draft["version"],
        confirmed_payload_sha256=preview["canonical_payload_sha256"],
        idempotency_key="promotion-1", final_source_tier=2,
        reviewer_digest="publisher-digest",
    )
    assert receipt["integration_state"] == "pending"
    assert promotion_harness.observation_count() == 1
    assert promotion_harness.origin_count() == 1
    assert promotion_harness.receipt_count() == 1
    assert promotion_harness.submission()["evidence_state"] == "available"
    assert promotion_harness.submission()["integration_state"] == "pending"
    assert promotion_harness.linked_artifact()["retention_class"] == "accepted_evidence"
    assert promotion_harness.linked_artifact()["purge_after"] is None


def test_retry_reconciles_canonical_commit_without_receipt(promotion_harness):
    draft = promotion_harness.ready_draft()
    preview = promotion_harness.preview(draft)
    promotion_harness.service.after_canonical_write = lambda: (_ for _ in ()).throw(
        InjectedFailure("after canonical")
    )
    with pytest.raises(InjectedFailure):
        promotion_harness.promote(draft, preview, key="promotion-1")
    assert promotion_harness.observation_count() == 1
    assert promotion_harness.receipt_count() == 0
    promotion_harness.service.after_canonical_write = lambda: None
    receipt = promotion_harness.promote(draft, preview, key="promotion-2")
    assert receipt["reconciled"] is True
    assert promotion_harness.observation_count() == 1
    assert promotion_harness.receipt_count() == 1


def test_same_and_alternate_keys_replay_the_same_receipt(promotion_harness):
    draft = promotion_harness.ready_draft()
    preview = promotion_harness.preview(draft)
    first = promotion_harness.promote(draft, preview, key="promotion-1")
    assert promotion_harness.promote(draft, preview, key="promotion-1") == first
    assert promotion_harness.promote(draft, preview, key="promotion-2") == first
    assert promotion_harness.receipt_count() == 1


def test_key_collision_and_payload_mismatch_are_conflicts(promotion_harness):
    first_draft = promotion_harness.ready_draft()
    first_preview = promotion_harness.preview(first_draft)
    promotion_harness.promote(first_draft, first_preview, key="promotion-1")
    second_draft = promotion_harness.ready_draft()
    second_preview = promotion_harness.preview(second_draft)
    with pytest.raises(PromotionConflict):
        promotion_harness.promote(second_draft, second_preview, key="promotion-1")
    with pytest.raises(PromotionConflict):
        promotion_harness.promote(first_draft, {**first_preview, "canonical_payload_sha256": "0" * 64}, key="promotion-3")


def test_preview_enforces_source_tier_and_promotion_requires_ready(promotion_harness):
    draft = promotion_harness.draft()
    with pytest.raises(PromotionConflict):
        promotion_harness.service.preview(draft["id"], final_source_tier=1)
    with pytest.raises(PromotionConflict):
        promotion_harness.service.promote(draft["id"], expected_version=draft["version"], confirmed_payload_sha256="0" * 64, idempotency_key="x", final_source_tier=2, reviewer_digest="publisher")


class InjectedFailure(RuntimeError):
    pass
