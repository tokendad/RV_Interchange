# Issue #47 Canonical Promotion Design

**Date:** 2026-08-28
**Status:** approved design; implementation not started
**Issue:** [#47 Public Queue and Submission](https://github.com/tokendad/RV_Interchange/issues/47)

## Goal

Add the publisher-authorized boundary that turns accepted, normalized public
evidence into one append-only canonical observation. Promotion must be
idempotent and recoverable across the quarantined intake database and canonical
observation database. It must not rebuild the graph or change public lookup
results.

This phase completes the missing portion of the approved moderation workflow:
an admin prepares an observation draft from accepted claims, marks that draft
ready, and an admin who also holds the `publisher` capability confirms and
promotes its exact canonical payload.

## Scope

This phase includes:

- normalized observation drafts and their accepted-claim and clean-artifact
  links;
- draft readiness validation and immutable audit events;
- an exact canonical-payload preview and confirmation digest;
- idempotent insertion into `observations.db`;
- a promotion receipt and `pending` integration state in `submissions.db`;
- retry reconciliation when the canonical insert succeeds before its intake
  receipt is recorded;
- private review API and UI controls for draft preparation, readiness, and
  promotion;
- a dedicated writable runtime directory containing `observations.db`, with no
  write access to `components.db`; and
- focused, full-suite, Compose-contract, and isolated recovery-drill coverage.

This phase does not include:

- resolver changes that integrate promoted evidence into components or edges;
- fixture edits, canonical graph rebuilds, or `components.db` writes;
- public contribution forms or enabling `/submission/v1/*`;
- backup and restore automation;
- a public evidence ledger; or
- automatic source fetching, scraping, acceptance, promotion, or publication.

## Authority boundary

Draft preparation and readiness require the active `admin` role. Promotion
requires the same authenticated identity to have both an active `admin` role
and the active `publisher` capability. These requirements use AND semantics;
neither an ordinary admin nor a non-admin capability holder may promote.

The current general review authorizer permits a role or capability to satisfy a
combined request. Promotion therefore uses an explicit all-of authorization
mode covered by negative tests for admin-only, publisher-only, Trusted-only,
revoked-role, and revoked-capability identities. Existing moderation behavior
is not silently reinterpreted as part of this phase.

The browser only presents controls. Every draft, readiness, preview, and
promotion request repeats server-side authorization after validating the
Cloudflare Access JWT and loading current local grants.

## Data model in `submissions.db`

The next numbered intake migration adds the following review-owned tables.
All identifiers are UUID strings and all timestamps are UTC ISO 8601 values.

### `observation_drafts`

- `id`: primary key and canonical origin identifier.
- `submission_id`: foreign key to the quarantined submission.
- `created_by_digest`: reviewer digest for the active admin.
- `source_type`: controlled canonical observation source type.
- `source_name`: required reviewer-normalized source label.
- `source_url`: optional normalized HTTP or HTTPS source URL.
- `raw_content`: required reviewer-approved evidence description or permitted
  excerpt.
- `extracted_json`: normalized canonical keys and JSON values only.
- `default_source_tier`: server-derived best permitted tier for the evidence
  kind.
- `state`: `draft`, `ready`, `promoted`, or `superseded`.
- `version`: monotonically increasing optimistic-concurrency version.
- `created_at` and `updated_at`.

A submission may have multiple drafts when it contains materially distinct
source events. A promoted draft is immutable. Revisions to promoted evidence
are new observations from new drafts; they never update an existing canonical
observation.

### `observation_draft_claims`

- Composite primary key `(draft_id, claim_id)`.
- Composite foreign-key enforcement ensures the claim belongs to the draft's
  submission.

Only accepted claims may be linked. Readiness rechecks current claim state; a
stale or invalid claim link fails closed.

### `observation_draft_artifacts`

- Composite primary key `(draft_id, artifact_id)`.
- Composite foreign-key enforcement ensures the artifact belongs to the
  draft's submission.

Only sanitized artifacts with `scan_status = 'clean'` may be linked. The joins
preserve private auditability; artifact bytes and storage keys are not copied
into canonical evidence.

### `promotion_receipts`

- `id`: promotion UUID.
- `idempotency_key`: unique client replay key.
- `observation_draft_id`: unique canonical idempotency key.
- `canonical_observation_id`: integer observation identifier.
- `canonical_payload_sha256`: digest confirmed by the publisher.
- `promoted_by_digest`: promoting identity.
- `source_tier`: final server-validated tier.
- `promoted_at`.
- `integration_state`: initially `pending`; later `integrated` or
  `not_applicable` is reserved for the graph-integration phase.

The draft identifier, not the client replay key, is the cross-database
idempotency key. A second idempotency key for the same draft returns the same
promotion receipt. Reuse of one client key for different request semantics
returns `409`.

### `promotion_events`

Append-only events record draft creation, readiness, promotion, and recovery
reconciliation. Each row records the submission, draft, optional promotion,
actor digest, action, prior state, resulting state, and timestamp. Private
notes remain private and are never copied to `observations.db`.

## Canonical representation in `observations.db`

Existing observation rows remain unchanged. The canonical schema gains an
`observation_origins` table:

- `observation_id`: primary key and foreign key to `observations.id`.
- `origin_type`: initially the constant `public_submission_draft`.
- `origin_id`: the observation draft UUID.
- `submission_id`: private trace identifier for operator reconciliation.
- `artifact_ids_json`: sorted linked artifact UUIDs, not paths or bytes.
- `canonical_payload_sha256`: digest of the promoted canonical payload.
- `created_at`.
- Unique key `(origin_type, origin_id)`.

The observation row and origin row are inserted in one canonical-database
transaction. Existing manually captured observations do not need origin rows.
The observation receives:

- the draft's confirmed `source_type`, `source_name`, `source_url`,
  `raw_content`, and normalized `extracted_json`;
- `extraction_method = 'reviewed_public_submission'`;
- `fetched_by` set to the promoting reviewer's stable HMAC digest, not their
  email address;
- a content hash computed by the canonical observation helper; and
- the final server-validated `source_tier`.

No contributor contact, abuse digest, capability, IP-derived value, private
moderation note, raw artifact path, or reviewer email enters the canonical
database.

## Normalization and source-tier policy

Draft creation runs the same strict resolver-key classification and
normalization used for trusted observations. Unknown input keys fail with a
field-level validation error. The stored `extracted_json` is the resulting
normalized canonical attribute object, not the contributor's proposed JSON and
not a graph mutation. Readiness revalidates the stored keys against the
canonical vocabulary and deterministically serializes the values. Empty
normalized attributes are allowed only when `raw_content` itself is the
accepted evidence, such as a negative finding; at least one accepted claim is
always required.

The controlled source types add `field_report` to the existing observation
types. The best permitted tier for a reviewed public submission is derived only
from evidence kind:

| Source type | Best permitted tier |
| --- | ---: |
| `manufacturer_page`, `manufacturer_pdf` | 2 |
| `manual_measurement`, `dataplate_photo`, `dealer_call` | 2 |
| `field_report`, `other` | 4 |
| `retailer_page` | 7 |
| `retailer_prose` | 8 |
| `forum_post` | 9 |

The mapping reflects manual review/extraction rather than an automated native
text capture. At promotion, the publisher may choose the mapped tier or a
numerically larger, less-trusted tier up to 9. The API rejects any numerically
smaller tier. Contributor history, Trusted endorsements, submission counts,
and reviewer confidence never improve the tier.

## Draft and promotion workflow

1. An admin selects one accepted or partially accepted submission and creates a
   draft from explicit accepted claim IDs and optional clean artifact IDs.
2. The server validates ownership of every join, normalizes extracted fields,
   derives the default source tier, stores the draft, and returns its version.
3. An admin requests readiness with the last observed version. The server
   rechecks accepted claims, clean artifacts, source fields, normalized JSON,
   and submission withdrawal state before transitioning `draft` to `ready`.
4. The review detail API exposes the exact canonical payload and its SHA-256
   digest only to an admin with publisher capability.
5. The publisher submits the last observed version, payload digest,
   idempotency key, and optional lower-trust tier. Any stale version or payload
   mismatch returns `409` without a write.
6. The server first reconciles by draft origin in `observations.db`. If no
   canonical origin exists, it inserts the observation and origin atomically.
7. The server records or reconstructs the intake promotion receipt, transitions
   the draft to `promoted`, sets the existing public submission
   `evidence_state = 'available'`, and leaves `integration_state = 'pending'`.
   The private review UI derives its explicit `promoted` label from the receipt;
   it does not overload the public evidence-state vocabulary.
8. A replay returns the same canonical observation and promotion identifiers.

Withdrawal is allowed only before promotion. A withdrawn submission cannot
create or ready a draft. A withdrawal racing with promotion is serialized by
the intake database's immediate transaction; once promotion has begun from a
locked ready draft, the evidence audit is retained.

## Two-database recovery protocol

SQLite cannot provide the required reliable atomic commit across the WAL-mode
intake database and a separate canonical file. Promotion therefore uses an
explicit recoverable sequence rather than `ATTACH` or a distributed-transaction
illusion:

1. Begin an immediate intake transaction, validate and lock the ready draft,
   then compute the immutable canonical payload and digest. Keep this
   transaction open during the bounded local canonical write so withdrawal or
   draft mutation cannot race the promotion.
2. Insert or find the canonical observation by unique draft origin in a
   canonical transaction.
3. Record the promotion receipt and promoted state, then commit the intake
   transaction.

If step 2 commits and step 3 fails or the process exits, the intake transaction
rolls back and the request returns a retryable server error without inserting
again. The next request finds the canonical origin, verifies that its stored
payload digest matches the ready draft, and creates the missing receipt. A
mismatched origin is a fail-closed integrity incident: return `409`, write no
receipt, and require operator investigation.

The implementation provides a deterministic failure-injection seam between the
canonical commit and receipt commit. Tests must demonstrate one canonical row,
one origin row, and one eventual receipt after retry.

## Private API contract

The review API adds:

- `POST /review/v1/submissions/{submission_id}/observation-drafts`
- `POST /review/v1/observation-drafts/{draft_id}/ready`
- `GET /review/v1/observation-drafts/{draft_id}/canonical-preview`
- `POST /review/v1/observation-drafts/{draft_id}/promotions`

Mutation requests contain a bounded idempotency key where applicable and the
last observed version. Draft inputs forbid canonical observation IDs, arbitrary
origin identifiers, arbitrary extraction methods, graph operations, confidence
effects, and source tiers. The promotion request may contain only the confirmed
payload digest, draft version, idempotency key, and optional final tier.

Unauthorized callers receive a generic `401` or `403` before record lookup.
Missing records return `404`; stale versions, invalid transitions, idempotency
collisions, payload mismatches, and integrity mismatches return `409`; invalid
request shapes return `422`.

Trusted responses continue to exclude normalized drafts, canonical previews,
promotion controls, receipt details, and reviewer digests. Admins without
publisher capability may see and prepare drafts but cannot obtain the exact
promotion control. Publisher-capable admins see the canonical preview and
promotion history.

## Review UI

The private submission detail adds a distinct evidence section:

- accepted claims and clean artifacts eligible for a draft;
- an admin draft editor for source metadata, approved raw description, and
  normalized extracted fields;
- readiness validation errors associated with their fields;
- an immutable ready-state canonical preview;
- publisher confirmation showing source tier, artifact references, payload
  digest, and the statement that promotion does not publish graph changes; and
- separate badges for `accepted`, `promoted`, and `integration pending`.

Controls remain keyboard accessible and preserve typed input after recoverable
errors. A success toast is not authoritative; the UI reloads the server receipt
and current draft state after promotion.

## Deployment boundary

`rvinterchange-review-api` gains `RVI_OBSERVATIONS_DB_PATH`. Production points
it at a dedicated bind-mounted directory such as
`/data/DockerConfigs/RVInterchange/canonical`, containing only
`observations.db` and its SQLite journal files. The mount target is writable by
the review API. The service receives no mount of the repository's entire
`Docs/Tools` directory and no path to `components.db`.

The catalog API continues to read only its generated `components.db`. Intake
continues to have no canonical mount. The public and review Nginx boundaries do
not change, and the public intake profile remains disabled.

Deployment must initialize the dedicated canonical database from an explicitly
verified current canonical observation snapshot. This phase documents the
copy/checksum and rollback procedure but does not automate backups; backup and
restore automation is the next operational phase.

## Testing and release gates

Tests are written before production behavior and cover:

- migration constraints, cross-submission join rejection, and append-only
  events;
- strict extracted-key normalization and every source-tier boundary;
- admin-only draft/readiness permissions and all-of promotion authorization;
- revoked authorization, optimistic concurrency, and state transitions;
- canonical preview redaction and stable payload digests;
- exact observation/origin content and absence of private fields;
- idempotent replay with the same and different client keys;
- failure injection after canonical commit followed by successful
  reconciliation;
- mismatch detection for an existing origin;
- Trusted/admin/publisher response shaping;
- Compose mounts proving only the dedicated observation directory is writable
  and `components.db` is unavailable; and
- UI accessibility and distinct acceptance/promotion/integration states.

Before publication, run the focused promotion tests, the full repository suite,
`git diff --check`, both default and tunnel Compose renders, and an isolated
two-database drill. The drill must promote a seeded accepted claim, inject the
post-canonical failure, replay successfully, verify one canonical observation,
verify one intake receipt, and confirm `components.db` and public search are
unchanged.

No production deployment, public route enablement, canonical graph rebuild, or
Issue #47 completion claim occurs in this phase.
