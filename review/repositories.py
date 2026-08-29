"""Transactional persistence for the private moderation queue."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from intake import db

# Draft persistence lives in its own module, but remains part of the review
# repository surface for callers that own the complete moderation workflow.
from review.drafts import DraftRepository


class ReviewConflict(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


class ReviewRepository:
    def __init__(self, conn):
        self.conn = conn

    def queue(self, *, status=None, priority=None, cursor=None, limit=50):
        clauses = ["s.status NOT IN ('withdrawn', 'accepted', 'rejected', 'duplicate', 'partially_accepted')"]
        args: list[Any] = []
        priority_rank = "CASE s.priority WHEN 'safety' THEN 0 WHEN 'high' THEN 1 ELSE 2 END"
        if status:
            clauses.append("s.status = ?")
            args.append(status)
        if priority:
            clauses.append("s.priority = ?")
            args.append(priority)
        if cursor:
            parts = cursor.split("|")
            if len(parts) == 3:
                rank, created_at, item_id = parts
                if rank not in {"0", "1", "2"}:
                    raise ValueError("invalid cursor")
                clauses.append(
                    f"({priority_rank} > ? OR ({priority_rank} = ? AND (s.created_at, s.id) > (?, ?)))"
                )
                args.extend((int(rank), int(rank), created_at, item_id))
            elif len(parts) == 2:
                created_at, item_id = parts
                clauses.append("(s.created_at, s.id) > (?, ?)")
                args.extend((created_at, item_id))
            else:
                raise ValueError("invalid cursor")
        limit = min(max(int(limit), 1), 100)
        rows = self.conn.execute(
            f"""
            SELECT s.id, s.intent, s.status, s.priority, s.summary, s.created_at,
                   COUNT(c.id) AS claim_count,
                   SUM(CASE WHEN c.status = 'pending' THEN 1 ELSE 0 END) AS pending_claim_count
            FROM submissions s LEFT JOIN submission_claims c ON c.submission_id = s.id
            WHERE {' AND '.join(clauses)}
            GROUP BY s.id ORDER BY CASE s.priority WHEN 'safety' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,
                     s.created_at, s.id LIMIT ?
            """,
            (*args, limit + 1),
        ).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            f"{({'safety': 0, 'high': 1}.get(rows[-1]['priority'], 2))}|{rows[-1]['created_at']}|{rows[-1]['id']}"
            if has_more and rows
            else None
        )
        return {"items": [dict(row) for row in rows], "next_cursor": next_cursor}

    def detail(self, submission_id: str, *, include_drafts: bool = False):
        row = self.conn.execute(
            """SELECT id, intent, status, target_component_id, target_edge_key_json,
                      target_namespace, target_identifier, summary, priority,
                      evidence_state, integration_state, created_at, updated_at
               FROM submissions WHERE id = ?""", (submission_id,)
        ).fetchone()
        if row is None:
            return None
        claims = self.conn.execute(
            """SELECT id, claim_type, proposed_json, status, decision_reason_code,
                      created_at, decided_at FROM submission_claims
               WHERE submission_id = ? ORDER BY created_at, id""", (submission_id,)
        ).fetchall()
        artifacts = self.conn.execute(
            """SELECT id, original_name, declared_media_type, detected_media_type,
                      size_bytes, width, height, scan_status, retention_class, created_at
               FROM submission_artifacts WHERE submission_id = ? ORDER BY created_at, id""", (submission_id,)
        ).fetchall()
        decisions = self.conn.execute(
            """SELECT claim_id, action, reason_code, prior_status,
                      resulting_status, created_at FROM review_decisions
               WHERE submission_id = ? ORDER BY created_at, id""", (submission_id,)
        ).fetchall()
        assessments = self.conn.execute(
            """SELECT claim_id, assessment, reason, created_at FROM review_assessments
               WHERE submission_id = ? ORDER BY created_at, id""", (submission_id,)
        ).fetchall()
        audit = [dict(row, type="decision") for row in decisions]
        audit.extend(dict(row, type="assessment") for row in assessments)
        audit.sort(key=lambda entry: entry["created_at"])
        result = {"submission": dict(row), "claims": [self._json_claim(c) for c in claims],
                  "artifacts": [dict(a) for a in artifacts], "audit": audit}
        if include_drafts:
            from review.drafts import DraftRepository
            result["drafts"] = [
                {key: draft[key] for key in (
                    "id", "submission_id", "source_type", "source_name", "source_url",
                    "extracted", "default_source_tier", "state", "version", "created_at", "updated_at",
                    "claim_ids", "artifact_ids")}
                for draft in DraftRepository(self.conn).list_for_submission(submission_id)
            ]
        return result

    @staticmethod
    def _json_claim(row):
        value = dict(row)
        value["proposed_json"] = json.loads(value["proposed_json"])
        return value

    def decide_claim(self, submission_id, claim_id, *, action, reason_code, note, reviewer_digest, idempotency_key):
        existing = self.conn.execute("SELECT * FROM review_decisions WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if existing:
            if (
                existing["action"] != "decision"
                or existing["submission_id"] != submission_id
                or existing["claim_id"] != claim_id
                or existing["reviewer_digest"] != reviewer_digest
                or existing["reason_code"] != reason_code
                or existing["note"] != note
            ):
                raise ReviewConflict("idempotency key conflict")
            claim_status = self.conn.execute(
                "SELECT status FROM submission_claims WHERE id = ? AND submission_id = ?",
                (existing["claim_id"], existing["submission_id"]),
            ).fetchone()["status"]
            if claim_status != action:
                raise ReviewConflict("idempotency key conflict")
            return {
                "submission_id": existing["submission_id"],
                "claim_id": existing["claim_id"],
                "status": claim_status,
                "submission_status": existing["resulting_status"],
            }
        submission = self.conn.execute(
            "SELECT status FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        if submission is None or submission["status"] not in (
            "received",
            "held",
            "under_review",
        ):
            raise ReviewConflict("submission is not reviewable")
        claim = self.conn.execute("SELECT status FROM submission_claims WHERE id = ? AND submission_id = ?", (claim_id, submission_id)).fetchone()
        if claim is None or claim["status"] != "pending":
            raise ReviewConflict("claim is not pending")
        result = {"accepted": "accepted", "rejected": "rejected", "duplicate": "duplicate"}.get(action)
        if result is None:
            raise ReviewConflict("invalid claim decision")
        now = _now()
        self.conn.execute("UPDATE submission_claims SET status = ?, decision_reason_code = ?, decided_at = ? WHERE id = ? AND status = 'pending'", (result, reason_code, now, claim_id))
        remaining = self.conn.execute("SELECT COUNT(*) FROM submission_claims WHERE submission_id = ? AND status = 'pending'", (submission_id,)).fetchone()[0]
        accepted = self.conn.execute("SELECT COUNT(*) FROM submission_claims WHERE submission_id = ? AND status = 'accepted'", (submission_id,)).fetchone()[0]
        duplicate = self.conn.execute("SELECT COUNT(*) FROM submission_claims WHERE submission_id = ? AND status = 'duplicate'", (submission_id,)).fetchone()[0]
        rejected = self.conn.execute("SELECT COUNT(*) FROM submission_claims WHERE submission_id = ? AND status = 'rejected'", (submission_id,)).fetchone()[0]
        if remaining:
            resulting = "under_review"
        elif accepted and (rejected or duplicate):
            resulting = "partially_accepted"
        elif accepted:
            resulting = "accepted"
        elif duplicate and not rejected:
            resulting = "duplicate"
        else:
            resulting = "rejected"
        prior = self.conn.execute("SELECT status FROM submissions WHERE id = ?", (submission_id,)).fetchone()[0]
        self.conn.execute("UPDATE submissions SET status = ?, updated_at = ? WHERE id = ?", (resulting, now, submission_id))
        self.conn.execute("INSERT INTO review_decisions VALUES (?, ?, ?, ?, ?, 'decision', ?, ?, ?, ?, ?)", (_id(), idempotency_key, submission_id, claim_id, reviewer_digest, reason_code, note, prior, resulting, now))
        return {"submission_id": submission_id, "claim_id": claim_id, "status": result, "submission_status": resulting}

    def request_information(
        self,
        submission_id,
        *,
        reason,
        reviewer_digest,
        idempotency_key,
    ):
        existing = self.conn.execute(
            "SELECT * FROM review_decisions WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            if (
                existing["action"] != "request_information"
                or existing["submission_id"] != submission_id
                or existing["reviewer_digest"] != reviewer_digest
                or existing["reason_code"] != reason
            ):
                raise ReviewConflict("idempotency key conflict")
            return {
                "submission_id": existing["submission_id"],
                "status": existing["resulting_status"],
            }
        row = self.conn.execute(
            "SELECT status FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        if row is None:
            raise ReviewConflict("submission not found")
        if row["status"] not in ("received", "held", "under_review"):
            raise ReviewConflict("submission cannot request information")
        now = _now()
        self.conn.execute(
            "UPDATE submissions SET status = 'needs_information', public_reason = ?, updated_at = ? WHERE id = ?",
            (reason, now, submission_id),
        )
        self.conn.execute(
            "INSERT INTO review_decisions VALUES (?, ?, ?, NULL, ?, 'request_information', ?, ?, ?, 'needs_information', ?)",
            (
                _id(),
                idempotency_key,
                submission_id,
                reviewer_digest,
                reason,
                reason,
                row["status"],
                now,
            ),
        )
        return {"submission_id": submission_id, "status": "needs_information"}

    def add_assessment(self, submission_id, claim_id, *, assessment, reason, reviewer_digest, idempotency_key):
        existing = self.conn.execute("SELECT * FROM review_assessments WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if existing:
            if (
                existing["submission_id"] != submission_id
                or existing["claim_id"] != claim_id
                or existing["reviewer_digest"] != reviewer_digest
                or existing["assessment"] != assessment
                or existing["reason"] != reason
            ):
                raise ReviewConflict("idempotency key conflict")
            return {
                "submission_id": existing["submission_id"],
                "claim_id": existing["claim_id"],
                "assessment": existing["assessment"],
            }
        if assessment == 'spam' and claim_id is not None:
            raise ReviewConflict("spam assessment targets submission")
        if assessment != 'spam' and claim_id is None:
            raise ReviewConflict("claim assessment requires claim")
        if self.conn.execute("SELECT 1 FROM submissions WHERE id = ?", (submission_id,)).fetchone() is None:
            raise ReviewConflict("submission not found")
        if claim_id and self.conn.execute("SELECT 1 FROM submission_claims WHERE id = ? AND submission_id = ?", (claim_id, submission_id)).fetchone() is None:
            raise ReviewConflict("claim not found")
        self.conn.execute("INSERT INTO review_assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (_id(), idempotency_key, submission_id, claim_id, reviewer_digest, assessment, reason, _now()))
        return {"submission_id": submission_id, "claim_id": claim_id, "assessment": assessment}
