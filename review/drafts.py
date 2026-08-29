"""Normalized, quarantined observation drafts."""

import json
import uuid
from datetime import datetime, timezone

from Docs.Tools import resolver


BEST_SOURCE_TIERS = {
    "manufacturer_page": 2, "manufacturer_pdf": 2, "manual_measurement": 2,
    "dataplate_photo": 2, "dealer_call": 2, "field_report": 4, "other": 4,
    "retailer_page": 7, "retailer_prose": 8, "forum_post": 9,
}


class DraftConflict(RuntimeError):
    pass


def normalize_draft_extracted(extracted: dict) -> dict:
    return resolver.normalize_extracted("draft", extracted, strict=True)["attributes"]


def _now():
    return datetime.now(timezone.utc).isoformat()


class DraftRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, submission_id, *, source_type, source_name, source_url, raw_content,
               extracted, claim_ids, artifact_ids, reviewer_digest, idempotency_key):
        claim_ids = list(claim_ids or [])
        artifact_ids = list(artifact_ids or [])
        if len(claim_ids) != len(set(claim_ids)) or len(artifact_ids) != len(set(artifact_ids)):
            raise DraftConflict("claim and artifact IDs must be unique")
        claim_ids.sort()
        artifact_ids.sort()
        if not claim_ids:
            raise DraftConflict("at least one accepted claim is required")
        normalized = normalize_draft_extracted(extracted)
        existing = self.conn.execute("SELECT * FROM observation_drafts WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if existing:
            old_claims = [r[0] for r in self.conn.execute("SELECT claim_id FROM observation_draft_claims WHERE draft_id = ? ORDER BY claim_id", (existing["id"],))]
            old_artifacts = [r[0] for r in self.conn.execute("SELECT artifact_id FROM observation_draft_artifacts WHERE draft_id = ? ORDER BY artifact_id", (existing["id"],))]
            if (existing["submission_id"], existing["source_type"], existing["source_name"], existing["source_url"], existing["raw_content"], json.loads(existing["extracted_json"]), old_claims, old_artifacts, existing["created_by_digest"]) != (submission_id, source_type, source_name, source_url, raw_content, normalized, claim_ids, artifact_ids, reviewer_digest):
                raise DraftConflict("idempotency key conflict")
            return self._row(existing)
        submission = self.conn.execute("SELECT status FROM submissions WHERE id = ?", (submission_id,)).fetchone()
        if submission is None or submission["status"] == "withdrawn":
            raise DraftConflict("submission is withdrawn or missing")
        if submission["status"] not in ("accepted", "partially_accepted"):
            raise DraftConflict("submission is not accepted")
        self._validate_evidence(submission_id, claim_ids, artifact_ids)
        now, draft_id = _now(), str(uuid.uuid4())
        try:
            tier = BEST_SOURCE_TIERS[source_type]
        except KeyError:
            raise DraftConflict("invalid source type") from None
        self.conn.execute("INSERT INTO observation_drafts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?)", (draft_id, idempotency_key, submission_id, reviewer_digest, source_type, source_name, source_url, raw_content, json.dumps(normalized, sort_keys=True), tier, now, now))
        for claim_id in claim_ids:
            self.conn.execute("INSERT INTO observation_draft_claims VALUES (?, ?, ?)", (submission_id, draft_id, claim_id))
        for artifact_id in artifact_ids:
            self.conn.execute("INSERT INTO observation_draft_artifacts VALUES (?, ?, ?)", (submission_id, draft_id, artifact_id))
        self.conn.execute("INSERT INTO promotion_events VALUES (?, ?, ?, NULL, ?, 'draft_created', NULL, 'draft', ?)", (str(uuid.uuid4()), submission_id, draft_id, reviewer_digest, now))
        return self._row(self.conn.execute("SELECT * FROM observation_drafts WHERE id = ?", (draft_id,)).fetchone())

    def mark_ready(self, draft_id, *, expected_version, reviewer_digest):
        row = self.conn.execute("SELECT * FROM observation_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise DraftConflict("draft not found")
        self._validate_evidence(row["submission_id"], self._ids(draft_id, "claim_id"), self._ids(draft_id, "artifact_id"))
        submission = self.conn.execute("SELECT status FROM submissions WHERE id = ?", (row["submission_id"],)).fetchone()
        if submission is None or submission["status"] == "withdrawn":
            raise DraftConflict("submission is withdrawn or missing")
        now = _now()
        changed = self.conn.execute("UPDATE observation_drafts SET state = 'ready', version = version + 1, updated_at = ? WHERE id = ? AND state = 'draft' AND version = ?", (now, draft_id, expected_version)).rowcount
        if changed != 1:
            raise DraftConflict("draft version conflict")
        self.conn.execute("INSERT INTO promotion_events VALUES (?, ?, ?, NULL, ?, 'draft_ready', 'draft', 'ready', ?)", (str(uuid.uuid4()), row["submission_id"], draft_id, reviewer_digest, now))
        return self._row(self.conn.execute("SELECT * FROM observation_drafts WHERE id = ?", (draft_id,)).fetchone())

    def get(self, draft_id):
        row = self.conn.execute("SELECT * FROM observation_drafts WHERE id = ?", (draft_id,)).fetchone()
        return self._row(row) if row else None

    def list_for_submission(self, submission_id):
        return [self._row(row) for row in self.conn.execute("SELECT * FROM observation_drafts WHERE submission_id = ? ORDER BY created_at, id", (submission_id,))]

    def events(self, draft_id):
        return [dict(row) for row in self.conn.execute("SELECT id, submission_id, observation_draft_id, promotion_id, action, prior_state, resulting_state, created_at FROM promotion_events WHERE observation_draft_id = ? ORDER BY created_at, id", (draft_id,))]

    def receipt_by_draft(self, draft_id):
        row = self.conn.execute(
            "SELECT * FROM promotion_receipts WHERE observation_draft_id = ?",
            (draft_id,),
        ).fetchone()
        return self._receipt(row) if row else None

    def receipt_by_replay_key(self, idempotency_key):
        row = self.conn.execute(
            """SELECT r.*, k.request_sha256 AS _request_sha256 FROM promotion_receipts r
               JOIN promotion_replay_keys k ON k.promotion_id = r.id
               WHERE k.idempotency_key = ?""",
            (idempotency_key,),
        ).fetchone()
        return self._receipt(row) if row else None

    def assert_replay_compatible(self, receipt, payload_sha256):
        if receipt["canonical_payload_sha256"] != payload_sha256:
            raise DraftConflict("promotion payload conflict")

    def assert_request_replay_compatible(self, receipt, request_sha256):
        if receipt.get("_request_sha256") != request_sha256:
            raise DraftConflict("idempotency key conflict")

    def add_replay_key(self, idempotency_key, promotion_id, request_sha256):
        existing = self.conn.execute(
            "SELECT promotion_id, request_sha256 FROM promotion_replay_keys WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            if existing["promotion_id"] != promotion_id or existing["request_sha256"] != request_sha256:
                raise DraftConflict("idempotency key conflict")
            return
        try:
            self.conn.execute(
                "INSERT INTO promotion_replay_keys VALUES (?, ?, ?, ?)",
                (idempotency_key, promotion_id, request_sha256, _now()),
            )
        except Exception as error:
            raise DraftConflict("idempotency key conflict") from error

    def ready_for_promotion(self, draft_id, expected_version):
        row = self.conn.execute(
            "SELECT * FROM observation_drafts WHERE id = ? AND state = 'ready' AND version = ?",
            (draft_id, expected_version),
        ).fetchone()
        if row is None:
            raise DraftConflict("draft is not ready or version conflict")
        self._validate_evidence(
            row["submission_id"], self._ids(draft_id, "claim_id"),
            self._ids(draft_id, "artifact_id"),
        )
        submission = self.conn.execute(
            "SELECT status FROM submissions WHERE id = ?", (row["submission_id"],)
        ).fetchone()
        if submission is None or submission["status"] == "withdrawn":
            raise DraftConflict("submission is withdrawn or missing")
        return self._row(row)

    def record_promotion(
        self, *, draft, observation_id, payload_sha256, idempotency_key,
        promoted_by_digest, reconciled_by_digest, source_tier, reconciled,
    ):
        promotion_id = str(uuid.uuid4())
        now = _now()
        self.conn.execute(
            """INSERT INTO promotion_receipts
               (id, idempotency_key, observation_draft_id,
                canonical_observation_id, canonical_payload_sha256,
                promoted_by_digest, source_tier, promoted_at, integration_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (promotion_id, idempotency_key, draft["id"], observation_id,
             payload_sha256, promoted_by_digest, source_tier, now),
        )
        self.add_replay_key(
            idempotency_key, promotion_id,
            _request_digest(draft["id"], payload_sha256, source_tier),
        )
        changed = self.conn.execute(
            """UPDATE observation_drafts
               SET state = 'promoted', version = version + 1, updated_at = ?
               WHERE id = ? AND state = 'ready' AND version = ?""",
            (now, draft["id"], draft["version"]),
        ).rowcount
        if changed != 1:
            raise DraftConflict("draft is not ready or version conflict")
        self.conn.execute(
            """UPDATE submissions SET evidence_state = 'available',
                      integration_state = 'pending', updated_at = ?
               WHERE id = ?""",
            (now, draft["submission_id"]),
        )
        self.conn.execute(
            """UPDATE submission_artifacts SET retention_class = 'accepted_evidence',
                      purge_after = NULL
               WHERE submission_id = ? AND scan_status = 'clean'
                 AND id IN (SELECT artifact_id FROM observation_draft_artifacts WHERE draft_id = ?)""",
            (draft["submission_id"], draft["id"]),
        )
        action = "promotion_reconciled" if reconciled else "promoted"
        actor = reconciled_by_digest if reconciled else promoted_by_digest
        self.conn.execute(
            """INSERT INTO promotion_events
               VALUES (?, ?, ?, ?, ?, ?, 'ready', 'promoted', ?)""",
            (str(uuid.uuid4()), draft["submission_id"], draft["id"],
             promotion_id, actor, action, now),
        )
        return self._receipt(
            self.conn.execute(
                "SELECT * FROM promotion_receipts WHERE id = ?", (promotion_id,)
            ).fetchone(), reconciled=reconciled,
        )

    def _receipt(self, row, *, reconciled=None):
        value = dict(row)
        if reconciled is None:
            reconciled = self.conn.execute(
                "SELECT 1 FROM promotion_events WHERE promotion_id = ? AND action = 'promotion_reconciled'",
                (row["id"],),
            ).fetchone() is not None
        value["reconciled"] = bool(reconciled)
        return value

    def _row(self, row):
        value = dict(row)
        value["extracted"] = json.loads(value.pop("extracted_json"))
        value["claim_ids"] = [r[0] for r in self.conn.execute("SELECT claim_id FROM observation_draft_claims WHERE draft_id = ? ORDER BY claim_id", (row["id"],))]
        value["artifact_ids"] = [r[0] for r in self.conn.execute("SELECT artifact_id FROM observation_draft_artifacts WHERE draft_id = ? ORDER BY artifact_id", (row["id"],))]
        return value

    def _ids(self, draft_id, column):
        table = "observation_draft_claims" if column == "claim_id" else "observation_draft_artifacts"
        return [r[0] for r in self.conn.execute(f"SELECT {column} FROM {table} WHERE draft_id = ?", (draft_id,))]

    def _validate_evidence(self, submission_id, claim_ids, artifact_ids):
        placeholders = ",".join("?" * len(claim_ids))
        claims = self.conn.execute(
            f"SELECT id, status FROM submission_claims WHERE submission_id = ? AND id IN ({placeholders})",
            (submission_id, *claim_ids),
        ).fetchall()
        if len(claims) != len(claim_ids):
            raise DraftConflict("accepted claim does not belong to submission")
        if any(row["status"] != "accepted" for row in claims):
            raise DraftConflict("claim is not accepted")
        if not artifact_ids:
            return
        placeholders = ",".join("?" * len(artifact_ids))
        artifacts = self.conn.execute(
            f"SELECT id, scan_status FROM submission_artifacts WHERE submission_id = ? AND id IN ({placeholders})",
            (submission_id, *artifact_ids),
        ).fetchall()
        if len(artifacts) != len(artifact_ids):
            raise DraftConflict("artifact does not belong to submission")
        if any(row["scan_status"] != "clean" for row in artifacts):
            raise DraftConflict("artifact must have clean scan status")


def _request_digest(draft_id, payload_sha256, source_tier):
    import hashlib
    encoded = json.dumps({
        "draft_id": draft_id,
        "canonical_payload_sha256": payload_sha256,
        "final_source_tier": source_tier,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
