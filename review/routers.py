from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from intake import db
from review.auth import ReviewerAuthorizer
from review.repositories import ReviewConflict, ReviewRepository
from review.schemas import Assessment, ClaimDecision, InformationRequest


def router(settings, validator=None):
    api = APIRouter(prefix="/review/v1")

    @contextmanager
    def connection():
        with db.connect(settings.database_path) as conn:
            yield conn

    def identity(request: Request, roles=frozenset(), capability=None):
        with connection() as conn:
            return ReviewerAuthorizer(conn, settings, validator).require(request, roles, capability)

    @api.get("/session")
    def session(request: Request):
        reviewer = identity(request)
        return {"email": reviewer.email, "roles": sorted(reviewer.roles), "capabilities": sorted(reviewer.capabilities)}

    @api.get("/queue")
    def queue(request: Request, status_filter: str | None = Query(None, alias="status"), priority: str | None = None, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)):
        identity(request, {"trusted", "admin"})
        with connection() as conn:
            return ReviewRepository(conn).queue(status=status_filter, priority=priority, cursor=cursor, limit=limit)

    @api.get("/submissions/{submission_id}")
    def detail(submission_id: str, request: Request):
        identity(request, {"trusted", "admin"})
        with connection() as conn:
            value = ReviewRepository(conn).detail(submission_id)
        if value is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
        return value

    @api.post("/submissions/{submission_id}/claims/{claim_id}/decision")
    def decision(submission_id: str, claim_id: str, payload: ClaimDecision, request: Request):
        reviewer = identity(request, {"admin"})
        try:
            with connection() as conn, db.transaction(conn):
                return ReviewRepository(conn).decide_claim(submission_id, claim_id, action=payload.action, reason_code=payload.reason_code, note=payload.note, reviewer_digest=reviewer.email_digest, idempotency_key=payload.idempotency_key)
        except ReviewConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    @api.post("/submissions/{submission_id}/request-information")
    def request_information(submission_id: str, payload: InformationRequest, request: Request):
        reviewer = identity(request, {"admin"})
        try:
            with connection() as conn, db.transaction(conn):
                row = conn.execute("SELECT status FROM submissions WHERE id = ?", (submission_id,)).fetchone()
                if row is None:
                    raise ReviewConflict("submission not found")
                if row["status"] not in ("received", "held", "under_review"):
                    raise ReviewConflict("submission cannot request information")
                conn.execute("UPDATE submissions SET status = 'needs_information', public_reason = ?, updated_at = datetime('now') WHERE id = ?", (payload.reason, submission_id))
                conn.execute("INSERT INTO review_decisions VALUES (lower(hex(randomblob(16))), ?, ?, NULL, ?, 'request_information', ?, ?, ?, 'needs_information', datetime('now'))", (payload.idempotency_key, submission_id, reviewer.email_digest, payload.reason, payload.reason, row["status"]))
                return {"submission_id": submission_id, "status": "needs_information"}
        except ReviewConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    @api.post("/submissions/{submission_id}/spam")
    def spam(submission_id: str, payload: Assessment, request: Request):
        reviewer = identity(request, {"trusted", "admin"})
        if payload.assessment != "spam":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "spam endpoint requires spam assessment")
        try:
            with connection() as conn, db.transaction(conn):
                return ReviewRepository(conn).add_assessment(submission_id, None, assessment="spam", reason=payload.reason, reviewer_digest=reviewer.email_digest, idempotency_key=payload.idempotency_key)
        except ReviewConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    @api.post("/submissions/{submission_id}/claims/{claim_id}/assessment")
    def assessment(submission_id: str, claim_id: str, payload: Assessment, request: Request):
        reviewer = identity(request, {"trusted", "admin"})
        if payload.assessment == "spam":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "claim assessment cannot be spam")
        try:
            with connection() as conn, db.transaction(conn):
                return ReviewRepository(conn).add_assessment(submission_id, claim_id, assessment=payload.assessment, reason=payload.reason, reviewer_digest=reviewer.email_digest, idempotency_key=payload.idempotency_key)
        except ReviewConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    return api
