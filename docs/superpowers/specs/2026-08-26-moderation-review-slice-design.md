# Issue #47 Moderation Review Slice Design

**Date:** 2026-08-26  
**Status:** approved scope; implementation pending spec review  
**Issue:** [#47 Public Queue and Submission](https://github.com/tokendad/RV_Interchange/issues/47)

## Goal

Replace the legacy private admin/debug page with the first functional moderation
slice: authenticated queue access, sanitized submission detail, claim-level
decisions, and advisory Trusted assessments. Promotion into canonical evidence
remains a later, separately authorized slice.

## Boundaries

The review service is a separate FastAPI application and static build. It may read
and update the quarantined `submissions.db`, read sanitized artifacts, and append
review audit events. It must not write `components.db`, and it must not expose
review routes through the public web container. The review Nginx proxy permits only
the explicit `/review/v1/` API allowlist and static assets.

## Authentication and authorization

Every review API request requires a valid Cloudflare Access JWT in
`Cf-Access-Jwt-Assertion`. Validation checks issuer, audience, signature, and
expiration using the configured Access JWKS endpoint. The JWT email is then matched
against a local reviewer allowlist with an active role and optional publisher
capability. The browser may hide controls based on the returned role, but the API
performs all authorization checks.

The first slice uses these permissions:

| Action | trusted | admin | publisher |
| --- | ---: | ---: | ---: |
| Read sanitized queue/detail | yes | yes | yes |
| Endorse/dispute a claim | yes | yes | yes |
| Flag submission as spam | yes | yes | yes |
| Decide a claim | no | yes | yes |
| Request information / mark duplicate | no | yes | yes |
| Promote or integrate evidence | no | no | later slice |
| Manage roles | no | yes, subject to authority rules | later slice |

## API contract

The review API exposes:

- `GET /health/` — private service health.
- `GET /review/v1/session` — validated reviewer identity, roles, and capabilities.
- `GET /review/v1/queue?status=&priority=&cursor=` — paginated queue summaries,
  ordered by priority then creation time, with no email, raw artifact path, or
  reviewer notes.
- `GET /review/v1/submissions/{id}` — sanitized submission detail, claims,
  artifact metadata, target resolver context, and audit summary.
- `POST /review/v1/submissions/{id}/claims/{claim_id}/decision` — idempotent
  admin-only decision with `accepted`, `rejected`, or `duplicate` plus a required
  reason code and optional note.
- `POST /review/v1/submissions/{id}/request-information` — admin-only transition
  to `needs_information` with a required public reason.
- `POST /review/v1/submissions/{id}/spam` — Trusted-or-admin advisory spam
  assessment with a required reason; it does not accept or reject claims.
- `POST /review/v1/submissions/{id}/claims/{claim_id}/assessment` — Trusted-or-admin
  endorse/dispute assessment with a required reason; it does not change claim state.

Mutations use an idempotency key and append an immutable audit event containing the
reviewer identity, action, prior state, resulting state, reason, and timestamp.
Invalid transitions return `409`; missing or unauthorized identities return `401`
or `403` without revealing whether a submission exists.

## Data model

The intake migration gains review-owned tables rather than overloading contributor
or public capability records:

- `reviewer_roles(email_digest, role, active, granted_at, revoked_at)`
- `reviewer_capabilities(email_digest, capability, active, granted_at, revoked_at)`
- `review_decisions(idempotency_key, submission_id, claim_id, reviewer_digest,
  action, reason_code, note, prior_status, resulting_status, created_at)`
- `review_assessments(idempotency_key, submission_id, claim_id, reviewer_digest,
  assessment, reason, created_at)`

The existing submission and claim status checks remain the source of truth for
workflow state. A submission reaches `accepted` or `partially_accepted` only from
claim decisions; Trusted assessments never alter those fields. Responses redact
encrypted contact data, internal digests, storage keys, and unreviewed raw content.

## UI

The review static app adopts the approved Nocturne visual system: dark surfaces,
lavender accent, dense split-view queue, evidence cards, resolver context, and
keyboard-accessible navigation. The left pane filters and lists queue items; the
right pane shows sanitized details and claim cards. Admin decision controls are
absent for Trusted users, while advisory controls remain available with required
reasons. The page displays acceptance, promotion, and integration as distinct
states even though promotion/integration controls are deferred.

The old raw Search/Resolve/Replacements/Logs forms are removed from the review
build. Public assets and public navigation remain unchanged except that the public
Contribute destination must not expose review controls without Access.

## Testing and release gates

- Unit tests cover JWT validation, role/capability authorization, redaction,
  idempotency, valid transitions, invalid transitions, and advisory isolation.
- API tests use a temporary persisted intake database and signed test JWTs; no
  test trusts a header without signature validation.
- Static tests verify the old debug controls are absent and the Nocturne queue
  contract is present.
- Compose tests verify review API wiring, the private `/review/v1/` allowlist, and
  unchanged public denial of review routes.
- The full repository suite and an isolated review-container health/UI drill must
  pass before deployment.

Promotion, canonical observation writes, graph integration, backup/restore, and
public contribution forms are explicitly out of scope for this slice.
