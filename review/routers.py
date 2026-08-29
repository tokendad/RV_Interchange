from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from intake import db
from review.auth import ReviewerAuthorizer
from review.canonical import CanonicalIntegrityError
from review.drafts import DraftConflict, DraftRepository
from review.promotion import PromotionConflict, PromotionNotFound, PromotionService
from review.repositories import ReviewConflict, ReviewRepository
from review.schemas import Assessment, ClaimDecision, DraftCreate, DraftReady, InformationRequest, PromotionRequest


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
        try:
            with connection() as conn:
                return ReviewRepository(conn).queue(status=status_filter, priority=priority, cursor=cursor, limit=limit)
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid cursor") from None

    @api.get("/submissions/{submission_id}")
    def detail(submission_id: str, request: Request):
        reviewer = identity(request, {"trusted", "admin"})
        with connection() as conn:
            value = ReviewRepository(conn).detail(submission_id, include_drafts="admin" in reviewer.roles)
        if value is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "submission not found")
        return value

    @api.post(
        "/submissions/{submission_id}/observation-drafts",
        status_code=status.HTTP_201_CREATED,
    )
    def create_draft(submission_id: str, payload: DraftCreate, request: Request):
        reviewer = identity(request, {"admin"})
        try:
            with connection() as conn, db.transaction(conn):
                return DraftRepository(conn).create(
                    submission_id,
                    source_type=payload.source_type,
                    source_name=payload.source_name,
                    source_url=str(payload.source_url) if payload.source_url else None,
                    raw_content=payload.raw_content,
                    extracted=payload.extracted,
                    claim_ids=payload.claim_ids,
                    artifact_ids=payload.artifact_ids,
                    reviewer_digest=reviewer.email_digest,
                    idempotency_key=payload.idempotency_key,
                )
        except DraftConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None

    @api.post("/observation-drafts/{draft_id}/ready")
    def ready_draft(draft_id: str, payload: DraftReady, request: Request):
        reviewer = identity(request, {"admin"})
        try:
            with connection() as conn, db.transaction(conn):
                return DraftRepository(conn).mark_ready(
                    draft_id,
                    expected_version=payload.expected_version,
                    reviewer_digest=reviewer.email_digest,
                )
        except DraftConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    @api.get("/observation-drafts/{draft_id}/canonical-preview")
    def canonical_preview(
        draft_id: str, request: Request,
        final_source_tier: int = Query(..., ge=1, le=9),
    ):
        with connection() as conn:
            ReviewerAuthorizer(conn, settings, validator).require_all(
                request, roles={"admin"}, capabilities={"publisher"}
            )
            try:
                return PromotionService(
                    conn, settings.observations_database_path
                ).preview(draft_id, final_source_tier=final_source_tier)
            except PromotionNotFound:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "draft not found") from None
            except (PromotionConflict, CanonicalIntegrityError):
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "promotion cannot be previewed"
                ) from None

    @api.post("/observation-drafts/{draft_id}/promotions")
    def promote(draft_id: str, payload: PromotionRequest, request: Request):
        with connection() as conn:
            reviewer = ReviewerAuthorizer(conn, settings, validator).require_all(
                request, roles={"admin"}, capabilities={"publisher"}
            )
            try:
                with db.transaction(conn):
                    return PromotionService(
                        conn, settings.observations_database_path
                    ).promote(
                        draft_id,
                        expected_version=payload.expected_version,
                        confirmed_payload_sha256=payload.canonical_payload_sha256,
                        idempotency_key=payload.idempotency_key,
                        final_source_tier=payload.final_source_tier,
                        reviewer_digest=reviewer.email_digest,
                    )
            except PromotionNotFound:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "draft not found") from None
            except (PromotionConflict, CanonicalIntegrityError, DraftConflict):
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "promotion cannot be completed"
                ) from None

    @api.post("/submissions/{submission_id}/claims/{claim_id}/decision")
    def decision(submission_id: str, claim_id: str, payload: ClaimDecision, request: Request):
        reviewer = identity(request, {"admin"}, "publisher")
        try:
            with connection() as conn, db.transaction(conn):
                return ReviewRepository(conn).decide_claim(submission_id, claim_id, action=payload.action, reason_code=payload.reason_code, note=payload.note, reviewer_digest=reviewer.email_digest, idempotency_key=payload.idempotency_key)
        except ReviewConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    @api.post("/submissions/{submission_id}/request-information")
    def request_information(submission_id: str, payload: InformationRequest, request: Request):
        reviewer = identity(request, {"admin"}, "publisher")
        try:
            with connection() as conn, db.transaction(conn):
                return ReviewRepository(conn).request_information(
                    submission_id,
                    reason=payload.reason,
                    reviewer_digest=reviewer.email_digest,
                    idempotency_key=payload.idempotency_key,
                )
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
