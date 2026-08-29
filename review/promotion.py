"""Recoverable promotion from a ready private draft to canonical evidence."""

import hashlib
import json
from pathlib import Path

from review.canonical import (
    CanonicalIntegrityError,
    CanonicalObservationStore,
    CanonicalPayload,
    canonical_payload_sha256,
)
from review.drafts import DraftConflict, DraftRepository


class PromotionConflict(RuntimeError):
    pass


class PromotionNotFound(PromotionConflict):
    pass


def promotion_request_sha256(draft_id, payload_sha256, final_source_tier):
    encoded = json.dumps(
        {
            "draft_id": draft_id,
            "canonical_payload_sha256": payload_sha256,
            "final_source_tier": final_source_tier,
        }, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PromotionService:
    def __init__(self, conn, canonical):
        self.conn = conn
        self.canonical = (
            canonical if isinstance(canonical, CanonicalObservationStore)
            else CanonicalObservationStore(Path(canonical))
        )
        self.after_canonical_write = lambda: None

    def payload_for(self, draft, final_source_tier, reviewer_digest):
        if final_source_tier < draft["default_source_tier"] or final_source_tier > 9:
            raise PromotionConflict("invalid source tier")
        return CanonicalPayload(
            draft_id=draft["id"], submission_id=draft["submission_id"],
            source_type=draft["source_type"], source_name=draft["source_name"],
            source_url=draft["source_url"], raw_content=draft["raw_content"],
            extracted=draft["extracted"], source_tier=final_source_tier,
            reviewer_digest=reviewer_digest,
            artifact_ids=tuple(sorted(draft["artifact_ids"])),
        )

    def preview(self, draft_id, *, final_source_tier):
        draft = DraftRepository(self.conn).get(draft_id)
        if draft is None:
            raise PromotionNotFound("draft not found")
        if draft["state"] != "ready":
            raise PromotionConflict("draft is not ready")
        try:
            payload = self.payload_for(draft, final_source_tier, "preview")
        except (KeyError, TypeError) as error:
            raise PromotionConflict("draft payload is invalid") from error
        evidence = {
            "draft_id": payload.draft_id,
            "submission_id": payload.submission_id,
            "source_type": payload.source_type,
            "source_name": payload.source_name,
            "source_url": payload.source_url,
            "raw_content": payload.raw_content,
            "extracted": payload.extracted,
            "source_tier": payload.source_tier,
            "artifact_ids": sorted(payload.artifact_ids),
        }
        return {
            "canonical_payload": evidence,
            "canonical_payload_sha256": canonical_payload_sha256(payload),
            "source_tier": payload.source_tier,
        }

    def promote(
        self, draft_id, *, expected_version, confirmed_payload_sha256,
        idempotency_key, final_source_tier, reviewer_digest,
    ):
        drafts = DraftRepository(self.conn)
        request_sha256 = promotion_request_sha256(
            draft_id, confirmed_payload_sha256, final_source_tier
        )
        replay = drafts.receipt_by_replay_key(idempotency_key)
        if replay:
            try:
                drafts.assert_request_replay_compatible(replay, request_sha256)
            except DraftConflict as error:
                raise PromotionConflict(str(error)) from error
            return _public_receipt(replay)
        receipt = drafts.receipt_by_draft(draft_id)
        if receipt:
            try:
                drafts.assert_replay_compatible(receipt, confirmed_payload_sha256)
                if receipt["source_tier"] != final_source_tier:
                    raise DraftConflict("promotion payload conflict")
                drafts.add_replay_key(idempotency_key, receipt["id"], request_sha256)
            except DraftConflict as error:
                raise PromotionConflict(str(error)) from error
            return _public_receipt(receipt)
        if drafts.get(draft_id) is None:
            raise PromotionNotFound("draft not found")
        try:
            draft = drafts.ready_for_promotion(draft_id, expected_version)
            payload = self.payload_for(draft, final_source_tier, reviewer_digest)
            if canonical_payload_sha256(payload) != confirmed_payload_sha256:
                raise PromotionConflict("canonical payload changed")
            prior_origin = self.canonical.find_origin(draft_id)
            observation_id = self.canonical.append_or_get(payload)
            self.after_canonical_write()
            receipt = drafts.record_promotion(
                draft=draft, observation_id=observation_id,
                payload_sha256=confirmed_payload_sha256,
                idempotency_key=idempotency_key,
                promoted_by_digest=self.canonical.promoting_digest(observation_id),
                reconciled_by_digest=reviewer_digest,
                source_tier=final_source_tier, reconciled=prior_origin is not None,
            )
            return _public_receipt(receipt)
        except (DraftConflict, CanonicalIntegrityError) as error:
            raise PromotionConflict(str(error)) from error


def _public_receipt(receipt):
    return {key: value for key, value in receipt.items() if not key.startswith("_")}
