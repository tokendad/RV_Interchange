# Issue #47 Moderation Review Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the legacy private debug page with an authenticated moderation queue that supports sanitized reads, admin claim decisions, and Trusted advisory assessments.

**Architecture:** Add a separate `review` FastAPI application backed by the existing isolated intake database and a review-owned migration. Validate Cloudflare Access JWTs before looking up local roles, expose a narrow `/review/v1/` contract through the review Nginx service, and serve a Nocturne static UI that consumes only sanitized API responses. Promotion and canonical integration remain outside this plan.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pydantic v2, PyJWT/JWKS validation, Nginx, vanilla JavaScript, CSS, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-26-moderation-review-slice-design.md`

## Global Constraints

- Review service is private and separate from the public catalog and intake services.
- Every review request validates Cloudflare Access JWT issuer, audience, signature, and expiration.
- Trusted assessments are advisory and never change submission or claim workflow state.
- Review responses redact contributor contact data, internal digests, storage keys, and raw unreviewed content.
- Review API never writes `components.db`; public `/review/v1/` remains denied.
- Promotion, canonical evidence writes, graph integration, backup/restore, and public contribution forms are out of scope.

### Task 1: Add review persistence migration and repository

**Files:**
- Create: `review/migrations/002_review.sql`
- Create: `review/repositories.py`
- Modify: `intake/db.py` to support the review migration directory
- Test: `tests/review/test_repositories.py`

**Interfaces:**
- `ReviewRepository.queue(status: str | None, priority: str | None, cursor: str | None, limit: int) -> dict`
- `ReviewRepository.detail(submission_id: str) -> dict | None`
- `ReviewRepository.decide_claim(...) -> dict`
- `ReviewRepository.request_information(...) -> dict`
- `ReviewRepository.add_assessment(...) -> dict`

- [ ] Write failing tests for queue ordering/redaction, legal transitions, idempotent decisions, and advisory isolation.
- [ ] Run `pytest tests/review/test_repositories.py -q` and verify failures identify missing review tables/repository methods.
- [ ] Add reviewer roles/capabilities, immutable decisions, and advisory assessments tables with unique idempotency keys and foreign keys to intake submissions/claims.
- [ ] Implement transactional repository methods using `BEGIN IMMEDIATE`, explicit prior-state checks, and immutable audit rows.
- [ ] Run the focused repository tests until all pass.
- [ ] Commit with `feat: add moderation review persistence`.

### Task 2: Implement signed Access JWT and role authorization

**Files:**
- Create: `review/auth.py`
- Create: `review/config.py`
- Create: `review/schemas.py`
- Test: `tests/review/test_auth.py`

**Interfaces:**
- `AccessTokenValidator.validate(assertion: str) -> ReviewerIdentity`
- `ReviewerAuthorizer.require(request: Request, roles: set[str], capability: str | None = None) -> ReviewerIdentity`
- `ReviewerIdentity(email_digest: str, email: str, roles: frozenset[str], capabilities: frozenset[str])`

- [ ] Write failing tests for missing, malformed, expired, wrong-issuer, wrong-audience, and invalid-signature JWTs plus role/capability failures.
- [ ] Run `pytest tests/review/test_auth.py -q` and verify all security cases fail before implementation.
- [ ] Implement JWKS retrieval with bounded HTTP timeouts and cached keys, PyJWT signature/issuer/audience/expiration validation, and local active-role lookup by normalized email digest.
- [ ] Return generic `401`/`403` errors that do not reveal submission existence or reviewer membership.
- [ ] Run focused auth tests and add settings for issuer, audience, JWKS URL, and digest key file.
- [ ] Commit with `feat: validate review access identities`.

### Task 3: Add review FastAPI service and narrow API contract

**Files:**
- Create: `review/app.py`
- Create: `review/routers.py`
- Create: `review/api.Dockerfile` for the Python review service image
- Modify: `deploy/docker-compose.yaml` to add the profile-gated review API and shared intake DB mount
- Modify: `review/nginx.conf` to proxy only explicit review endpoints
- Test: `tests/review/test_api.py`, `tests/deploy/test_compose_contract.py`

**Interfaces:**
- `GET /health/`
- `GET /review/v1/session`
- `GET /review/v1/queue`
- `GET /review/v1/submissions/{submission_id}`
- `POST /review/v1/submissions/{submission_id}/claims/{claim_id}/decision`
- `POST /review/v1/submissions/{submission_id}/request-information`
- `POST /review/v1/submissions/{submission_id}/spam`
- `POST /review/v1/submissions/{submission_id}/claims/{claim_id}/assessment`

- [ ] Write failing API tests using a temporary persisted intake database and signed test JWTs.
- [ ] Run the focused API tests and confirm the service/routes are absent or return the expected failures.
- [ ] Implement dependency-injected settings, auth, repository transactions, Pydantic request/response models, and status-code mapping (`401`, `403`, `404`, `409`, `422`).
- [ ] Ensure every mutation requires an idempotency key and reason; ensure Trusted cannot decide claims or change workflow state.
- [ ] Add review API Compose wiring without exposing its port publicly; mount only intake data and required logs.
- [ ] Configure review Nginx to proxy the explicit API paths and deny `/submission/v1/`, docs, and arbitrary routes.
- [ ] Run API and Compose tests.
- [ ] Commit with `feat: add authenticated review API`.

### Task 4: Replace legacy debug UI with Nocturne queue UI

**Files:**
- Replace: `review/index.html`
- Replace: `review/admin.js`
- Modify: `review/Dockerfile` to include the new static assets and the review API runtime image definition
- Modify: `review/nginx.conf` to proxy the Task 3 review paths instead of returning the placeholder moderation `503`
- Test: `tests/review/test_ui_contract.py`

**Interfaces:**
- Browser calls only the review API paths from Task 3.
- Queue cards expose priority, intent, summary, claim counts, and workflow state.
- Detail view exposes sanitized claims/artifact metadata and distinct acceptance/promotion/integration states.

- [ ] Write failing static contract tests asserting legacy Search/Resolve/Replacements/Logs controls are absent and queue/detail/action hooks exist.
- [ ] Run the UI contract tests to verify the old page fails the new contract.
- [ ] Implement keyboard-accessible split-view queue, filters, claim cards, role-aware controls, required-reason dialogs, optimistic-safe idempotency keys, and visible error states using the Nocturne palette.
- [ ] Keep Trusted controls limited to endorse/dispute/spam; hide admin decisions for Trusted while retaining server enforcement.
- [ ] Run UI contract tests and a local browser/API drill against seeded review data.
- [ ] Commit with `feat: replace review debug page with moderation queue`.

### Task 5: Verify, deploy, and document operations

**Files:**
- Modify: `Docs/Operations/` review deployment/runbook document
- Test: full repository suite and isolated Compose drill

- [ ] Run `python3 -m pytest tests/ Docs/Tools -q` and `git diff --check`.
- [ ] Build an isolated review stack with a temporary database and signed test identity; verify health, queue read, decision, idempotency replay, and Trusted authorization.
- [ ] Verify public Nginx still returns `404` for `/review/v1/` and review Nginx returns `401` without a valid Access assertion.
- [ ] Rebuild the local stack from the exact deployment worktree, preserving the generated `components.db` artifact in the mounted `Docs/Tools` directory.
- [ ] Verify local and public review health plus a sanitized queue response through the tunnel.
- [ ] Record the deployed commit, test counts, and any intentionally disabled promotion/intake boundaries.
- [ ] Commit with `docs: add review moderation operations runbook`.
