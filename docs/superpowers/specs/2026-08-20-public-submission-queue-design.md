# Public submission queue and local-first hosting — design

**Date:** 2026-08-20
**Status:** approved 2026-08-20, including Cloudflare-only email revision
**Issues:** [#47 Public Queue and Submission](https://github.com/tokendad/RV_Interchange/issues/47), [#32 Hosting - DNS - Google Cloud](https://github.com/tokendad/RV_Interchange/issues/32)

## Decision summary

RV Interchange will accept public evidence through a quarantined submission system. A
public submission is never itself a canonical observation and never writes directly to
components, identifiers, edges, confidence records, or the published `components.db`.
A reviewer must normalize and accept the evidence before an idempotent promotion step
appends it to `observations.db`. Graph integration remains a separate, fixture-validated
research step.

The first deployment remains on the local Docker host. `rvinterchange.com` will use
Cloudflare DNS, Cloudflare Tunnel, Turnstile, and edge protections. The public site and
public endpoints share one origin. The moderation interface uses
`review.rvinterchange.com`, protected by Cloudflare Access and application-level token
validation. No inbound router ports are required.

Human correspondence uses Cloudflare Email Routing at `contact@rvinterchange.com`,
forwarded to an account-level verified personal inbox whose address is never stored in
Git. This first hosting release is inbound-only: replies originate from the personal
inbox unless a branded outbound service is added later. Transactional messages will use
Cloudflare Email Sending from `notifications@rvinterchange.com` only after the submission
intake plan explicitly authorizes Workers Paid and verifies arbitrary-recipient delivery.
Email delivery is asynchronous and cannot determine whether a submission transaction
succeeds.

The local implementation uses a separate SQLite intake database and private filesystem
artifact store behind narrow repository interfaces. Those interfaces allow a later move
to Cloud SQL PostgreSQL and Google Cloud Storage without changing the public workflow,
review state machine, or canonical promotion contract.

## Context

The existing system has two deliberately different persistence layers:

1. `Docs/Tools/observations.db` is the append-only evidence source of truth.
2. `Docs/Tools/components.db` is a derived, rebuildable read model produced by
   `edge_resolver.py` and protected by fixture validation and atomic replacement.

The public FastAPI application currently opens `components.db` read-only and exposes
only anonymous `GET` endpoints. The current static site calls that API on a hard-coded
host port. The Docker Compose deployment labels RV Interchange a personal test tool and
publishes host ports `8484` and `8485`.

The existing observation tool assumes a trusted researcher. It accepts raw content and
hand-authored extracted JSON, assigns source trust tiers, and has no submission state,
review identity, abuse handling, artifact quarantine, or promotion receipt. It must not
be exposed as a public write API.

The resolver is curated rather than fully generic. Adding an accepted observation does
not automatically change the graph. Researchers still decide how that evidence maps to
components, identifiers, attributes, candidates, and edges, then run the canonical build
and fixture checks. Public-facing status and reviewer copy must make this distinction
clear.

## Goals

- Let a member of the public submit direct observations, documentation citations,
  photos, measurements, successful installations, failed installations, and corrections.
- Require a verified email address without requiring a conventional user account.
- Preserve untrusted input outside the canonical evidence and derived graph stores.
- Let a reviewer accept, reject, request information, or mark individual claims as
  duplicates.
- Preserve an append-only audit trail for review decisions and canonical promotion.
- Make promotion idempotent and traceable from a public submission to a canonical
  observation.
- Keep reviewer notes, contributor identity, internal confidence, candidates, and raw
  moderation data private.
- Keep the current public lookup available when intake, email, or moderation is degraded.
- Support safe local hosting through Cloudflare without opening inbound network ports.
- Preserve a low-friction migration path to Google Cloud.

## Non-goals

- Public editing of components, identifiers, attributes, edges, source tiers, confidence,
  or publication status.
- Automatic acceptance, graph integration, confidence changes, or publication based on
  contributor reputation.
- A public wiki, discussion forum, marketplace, or general-purpose account system.
- Automatic fetching or scraping of submitted URLs in the first release.
- Public PDF upload in the first release. Submitters provide a URL and page, table, or
  figure citation instead.
- Automatic OCR conclusions. OCR may later assist a reviewer, but extracted text remains
  untrusted until a reviewer verifies it against the artifact.
- Publishing raw submissions, reviewer notes, contributor email addresses, or uploaded
  photos.
- Moving the workload to Google Cloud during the first release.

## Delivery decomposition

This design is implemented through four separately reviewable plans. Each plan must leave
the system working and independently testable.

1. **Hosting foundation (#32):** same-origin reverse proxy, Cloudflare Tunnel, public and
   review hostnames, Cloudflare Access, removal of direct public host-port exposure, health
   checks, and operational documentation.
2. **Submission intake:** intake schema, state transitions, verified-email session,
   Turnstile verification, rate limits, photo quarantine, receipt/status capability, and
   transactional outbox.
3. **Moderation and promotion:** reviewer API/UI, claim-level decisions, audit events,
   normalized observation draft, idempotent canonical promotion, and integration status.
4. **Public contribution experience:** the three guided submission flows, email templates,
   needs-information follow-up, contact page, accessibility, and end-to-end validation.

Google Cloud migration is a later plan, not a fifth task hidden inside the local launch.

## System boundaries

### Public web container

The public Nginx container serves only public static assets. It proxies these paths over
the private Docker network:

- `/public/v1/*` to the read-only catalog API.
- `/submission/v1/*` to the intake API.
- `/health/` to a public-safe aggregate health response.

The browser uses relative same-origin URLs. `web/api-client.js` no longer constructs an
API origin with port `8484`. Nginx does not proxy `/debug/v1`, `/review/v1`, FastAPI
documentation, or arbitrary API paths.

The public image does not contain `admin.html`, `admin.js`, or future moderation assets.
Those assets move to the review application. This prevents an Access configuration error
from turning an accidentally shipped moderation page into a public page.

### Catalog API

The catalog API retains read-only access to `components.db`. It receives no write access
to `submissions.db`, the artifact directory, or `observations.db`. Existing public lookup
behavior remains available independently of the intake system.

### Intake API

The intake API can write only to `submissions.db`, the artifact quarantine directory,
and its own logs. It cannot open `observations.db` or `components.db` for writing. It can
read the public catalog through the same read-only service interfaces used by the catalog
API when validating an optional target identifier.

### Review application

The review application consists of a private static UI and a review API. The review API
can read and update the intake database, read quarantined artifacts, and append accepted
evidence to `observations.db`. It cannot mutate `components.db`; publication continues
through the canonical resolver build.

Every review request validates the Cloudflare Access JWT in
`Cf-Access-Jwt-Assertion`, including issuer, audience, signature, and expiration. The
validated email must also appear in a local reviewer allowlist with an explicit role.
The API never trusts the presence of an Access header without cryptographic validation.
The `reviewer` role may triage submissions, decide claims, and prepare observation drafts.
The narrower `publisher` capability is additionally required to promote a ready draft or
record graph integration. Reviewer membership alone never grants publication authority.

### Cloudflare Tunnel

`cloudflared` runs as a managed Docker service on the same private network as the public
and review proxies. It uses outbound connections only.

- `rvinterchange.com` routes to the public web container.
- `www.rvinterchange.com` redirects permanently to `https://rvinterchange.com`.
- `review.rvinterchange.com` routes to the review web container and is covered by a
  deny-by-default Cloudflare Access application.

The production Compose configuration does not bind catalog, intake, review, or database
ports to all host interfaces. A development-only override may bind loopback ports for
local testing.

## Public contribution flows

The site presents three explicit intents. It does not ask contributors to author generic
graph conclusions.

### Installation result

Prompt for:

- Original manufacturer and identifier.
- Attempted replacement manufacturer and identifier.
- Outcome: installed successfully, installed with modification, or did not fit/work.
- Modifications and required additional parts.
- Relevant appliance, coach, model-year, and installation context.
- Up to five supporting photos.

Copy asks what happened rather than whether the parts are interchangeable. A failed
installation is prioritized in the reviewer queue, but it is not automatically applied
as negative confidence evidence.

### Documentation citation

Prompt for:

- Source category: manufacturer page, manufacturer document, retailer page, service
  manual, owner manual, dealer communication, or other.
- HTTPS URL.
- Document title and revision/date when visible.
- Page, table, figure, or section locator.
- A short description of what the source explicitly states.
- The identifiers to which the statement appears to apply.

The service stores the URL and contributor description but does not fetch the URL.
Reviewers independently validate the source. Public PDF uploads are deferred; a PDF must
be cited by URL in the first release.

### Incorrect or missing result

This flow can be launched from a search result or replacement card and pre-populates the
target component or edge reference. Prompt for:

- Whether the information is missing, misleading, or contradicted.
- What was directly observed.
- A conflicting source or supporting photo when available.
- Safety impact, including electrical, fuel, dimensional, or installation concerns.

These submissions receive a high-priority queue flag. Priority changes review order only.

Every flow ends with an unchecked consent step covering the current contribution terms,
privacy notice, and a non-exclusive license permitting RV Interchange to retain, analyze,
and use the submitted evidence. The contributor also confirms that uploaded photos are
theirs to submit and do not intentionally contain people, addresses, license plates, or
other unnecessary personal information. Consent versions and timestamp are stored with
the submission.

## Verified-email session

No conventional account or password is required.

1. The contributor submits an email address and a Turnstile token.
2. The intake API validates Turnstile server-side and rate limits the request.
3. It stores only a hashed single-use verification token and queues a verification email.
4. The link opens the public site with the raw token in the URL fragment, so web server,
   proxy, and analytics logs do not receive it.
5. Browser JavaScript exchanges the token for a signed, `HttpOnly`, `Secure`,
   `SameSite=Lax` contribution session cookie.
6. The session expires after 24 hours and may create up to five submissions.

Email comparison uses a normalized keyed digest. The address itself is encrypted at rest
with an application key stored outside the repository. Reviewer screens show a masked
address except when a reviewer explicitly requests contact for a needs-information action.

## Submission data model

The intake store is a separate SQLite database using foreign keys, WAL mode, a busy
timeout, and schema migrations. Identifiers exposed to browsers are random UUIDs; database
row numbers are never public identifiers.

### `contributors`

- `id`: UUID primary key.
- `email_digest`: keyed digest, unique.
- `email_ciphertext`: encrypted normalized address.
- `verified_at`, `last_activity_at`, `blocked_at`.
- `created_at`.

There is no public profile and no truth or confidence weight.

### `submission_sessions`

- `id`: UUID primary key.
- `contributor_id`.
- `token_digest`: digest of the verification token before exchange or session token after
  exchange.
- `state`: `pending`, `active`, `consumed`, `expired`, or `revoked`.
- `submission_count`.
- `expires_at`, `created_at`, `consumed_at`.

### `submissions`

- `id`: UUID primary key.
- `contributor_id`.
- `intent`: `installation_result`, `documentation_citation`, or `data_correction`.
- `status`: current workflow status.
- `target_component_id`, `target_edge_key_json`, `target_namespace`, and
  `target_identifier`, all nullable because genuinely new parts may not resolve.
- `target_edge_key_json` stores a stable logical locator (`type`, from-component ID,
  to-component ID or group key), never the rebuildable `edges.id` row number.
- `summary`: plain text, never rendered as HTML.
- `context_json`: validated intent-specific input.
- `priority`: `normal`, `high`, or `safety`.
- `abuse_digest`: rotating keyed digest used for rate-limit correlation, not a raw IP.
- `terms_version`, `evidence_license_version`, and `consented_at`.
- `created_at`, `updated_at`, `withdrawn_at`.

### `submission_capabilities`

- `id`: UUID primary key.
- `submission_id`.
- `purpose`: `status`, `follow_up`, or `withdrawal`.
- `token_digest`: digest of a random capability secret; raw secrets are never stored.
- `expires_at`, `consumed_at`, `revoked_at`, and `created_at`.

Status capabilities are reusable until expiry or revocation. Follow-up and withdrawal
capabilities are single-use. Issuing a replacement revokes the earlier capability for the
same purpose.

### `submission_claims`

- `id`: UUID primary key.
- `submission_id`.
- `claim_type`: controlled vocabulary describing an observed identifier, attribute,
  installation outcome, document assertion, supersession assertion, or correction.
- `proposed_json`: validated but untrusted structured value.
- `status`: `pending`, `accepted`, `rejected`, or `duplicate`.
- `decision_reason_code`.
- `created_at`, `decided_at`.

The public form may propose claims, but only the review API can change claim status or
create normalized accepted content.

### `submission_artifacts`

- `id`: UUID primary key.
- `submission_id`.
- `storage_key`: random server-generated relative key.
- `original_name`: sanitized display-only filename.
- `declared_media_type`, `detected_media_type`.
- `raw_sha256`, `stored_sha256`, `size_bytes`, `width`, and `height`.
- `scan_status`: `pending`, `clean`, `rejected`, or `failed`.
- `retention_class`: `unverified`, `rejected`, or `accepted_evidence`.
- `created_at`, `purge_after`, `purged_at`.

### `review_events`

- `id`: UUID primary key.
- `submission_id` and optional `claim_id`.
- `reviewer_id`.
- `action`: controlled workflow action.
- `reason_code` and private `note`.
- `created_at`.

Rows are append-only. A current status column is a query optimization; review events are
the audit record.

### `observation_drafts`

- `id`: UUID primary key.
- `submission_id`.
- `reviewer_id`.
- `source_type`, `source_name`, `source_url`.
- `raw_content`: reviewer-approved evidence description or document excerpt within the
  project's quotation policy.
- `extracted_json`: normalized canonical keys only.
- `state`: `draft`, `ready`, `promoted`, or `superseded`.
- `created_at`, `updated_at`.

One draft may combine multiple accepted claims from the same source event. A submission
with materially different sources uses separate drafts.

### `observation_draft_claims` and `observation_draft_artifacts`

These join tables map each observation draft to the accepted claims and sanitized
artifacts it incorporates. Both use composite unique keys. A draft cannot transition to
`ready` if it references a pending/rejected claim or a non-clean artifact. Explicit joins
preserve the audit trail without hiding relationships inside JSON.

### `promotions`

- `id`: UUID primary key.
- `observation_draft_id`: unique idempotency key.
- `canonical_observation_id`.
- `reviewer_id`.
- `promoted_at`.
- `integration_state`: `pending`, `integrated`, or `not_applicable`.
- `integrated_at` and `integration_reference`.

`integration_reference` records the repository commit or research artifact that integrates
the evidence. It is metadata, not permission to commit automatically.

### `email_outbox`

- `id`: UUID primary key.
- `template`, encrypted recipient, and JSON template data.
- `state`: `pending`, `sending`, `sent`, `retry`, or `failed`.
- `attempt_count`, `next_attempt_at`, `provider_reference`, `last_error`.
- `created_at`, `sent_at`.

No table stores a provider API token.

## Submission workflow states

The submission status state machine is:

```text
received ──> under_review ──> accepted
    │              │              └──> integration pending/integrated is tracked separately
    │              ├──> partially_accepted
    │              ├──> needs_information ──> under_review
    │              ├──> rejected
    │              └──> duplicate
    ├──> held
    └──> withdrawn
```

- `received`: email is verified, validation passed, and every artifact is clean.
- `held`: automated checks require operator attention; it never appears in the normal
  review queue.
- `under_review`: a reviewer has claimed the item.
- `needs_information`: contributor response is required; a signed follow-up link permits
  only additions, never edits to earlier evidence.
- `accepted`: all material claims were accepted and at least one observation draft is
  ready or promoted.
- `partially_accepted`: at least one material claim was accepted and at least one was
  rejected or marked duplicate.
- `rejected`: no material claim was accepted.
- `duplicate`: all material claims duplicate existing evidence or another submission.
- `withdrawn`: contributor requested withdrawal before promotion.

Review decisions never delete or rewrite an earlier review event. Corrections append a new
event and, when required, a new observation draft.

## Artifact quarantine

The first release accepts JPEG, PNG, and WebP images only, with these limits:

- At most five files per submission.
- At most 10 MiB per file.
- At most 25 MiB total per submission.
- Maximum decoded dimensions of 12,000 by 12,000 pixels.

Validation uses magic bytes and full image decoding rather than filename or browser MIME
type. Accepted images are decoded and re-encoded to remove EXIF, GPS, embedded profiles,
and active or malformed metadata. The raw upload is hashed for duplicate and abuse
analysis, then deleted after a safe derivative is created. The derivative receives a new
hash and is the artifact reviewers inspect.

Artifacts are stored outside the repository and outside every static web root. Download
requires a short-lived review-API authorization check; filenames never become paths.
The public API never returns an artifact URL.

Retention is explicit:

- Unverified and abandoned upload staging is purged after 7 days.
- Rejected and duplicate artifacts are purged 30 days after final decision.
- Accepted evidence artifacts are retained while referenced by a canonical observation.
- Contributor contact ciphertext is purged 24 months after last activity unless an active
  accepted-evidence audit or legal requirement requires retention.

## Review queue

The default queue orders safety corrections first, then fitment failures, then oldest
received submission. Filters include intent, status, source category, target manufacturer,
unresolved identifier, duplicate hash, and assigned reviewer.

The review detail screen shows:

- Submitted facts and context as escaped plain text.
- Sanitized artifact previews.
- Target catalog component, identifiers, attributes, and affected edge when resolvable.
- Potential duplicate submissions, observation hashes, and source URLs.
- Each proposed claim with independent accept, reject, and duplicate actions.
- Controlled reason code and private-note fields.
- A normalized observation draft preview.
- The exact canonical observation payload before promotion.
- Review and promotion history.

Reviewer actions are optimistic-concurrency protected. Updating a stale version returns a
conflict and reloads the current decision history instead of overwriting another reviewer.

## Canonical promotion

Promotion has these invariants:

1. Only a `ready` observation draft with at least one accepted claim can be promoted.
2. The reviewer must reconfirm the source type, source name, raw description, normalized
   extracted JSON, and artifact references.
3. `observation_draft_id` is the idempotency key. Repeating a successful promotion returns
   the existing canonical observation ID.
4. `observations.db` gains an origin reference that is unique for promoted public evidence.
   Existing observations remain valid and unchanged.
5. The promoted observation uses extraction method `reviewed_public_submission` and records
   the reviewer identity in `fetched_by`. The existing source-tier rules remain authoritative;
   contributor history never raises the tier.
6. A promotion receipt is recorded in the intake database. If receipt recording is
   interrupted after canonical insertion, retry reconciles by the unique origin reference
   and creates the missing receipt without inserting another observation.
7. Promotion marks graph integration `pending`. It does not run or modify the resolver and
   does not change public results.
8. A researcher integrates accepted evidence through normal resolver code, fixture updates,
   review, and the atomic canonical rebuild. Only then is the promotion marked `integrated`.

The public status distinguishes “accepted as evidence” from “included in published lookup
results.” It never promises that accepted evidence supports the contributor's proposed
conclusion.

Promotion adds `field_report` to the controlled observation source types. Reviewed
manufacturer pages/documents, data-plate photos, and manual measurements retain the trust
tier assigned to that evidence kind under the existing policy. A `field_report` defaults
to tier 4. `reviewed_public_submission` receives explicit source-tier mappings so it never
falls through to the current tier-9 unknown-source default. A reviewer may lower a tier
when the artifact is incomplete or ambiguous, but cannot raise it because of contributor
history.

## Public and review API surface

Exact request and response schemas belong in the implementation plans, but the stable
resource boundaries are:

### Public intake

- `POST /submission/v1/verification-requests`
- `POST /submission/v1/verification-exchanges`
- `POST /submission/v1/submissions`
- `POST /submission/v1/submissions/{id}/follow-ups`
- `POST /submission/v1/status-queries`
- `POST /submission/v1/submissions/{id}/withdrawals`

Submission creation uses multipart form data containing one JSON metadata part and optional
image parts. Status and follow-up capabilities use random secrets delivered in email. Raw
capability secrets remain in browser URL fragments and are posted in request bodies, not
path or query parameters.

### Review

- `GET /review/v1/queue`
- `GET /review/v1/submissions/{id}`
- `POST /review/v1/submissions/{id}/claim`
- `POST /review/v1/claims/{id}/decisions`
- `POST /review/v1/submissions/{id}/information-requests`
- `POST /review/v1/submissions/{id}/observation-drafts`
- `POST /review/v1/observation-drafts/{id}/ready`
- `POST /review/v1/observation-drafts/{id}/promotions`
- `POST /review/v1/promotions/{id}/integration-records`

Mutation requests include the last observed record version. Review APIs never accept an
arbitrary canonical observation ID, source tier, confidence effect, or graph mutation from
the public payload.

## Email

### Human contact

`contact@rvinterchange.com` is a Cloudflare Email Routing address forwarded to an existing
verified personal inbox. The destination address is operational account data and is not
recorded in the repository. The routing rule is for support, privacy, security, and general
correspondence. Email sent there does not automatically become a submission because
unstructured email cannot satisfy the queue's validation, consent, or claim boundaries. A
reviewer may send the writer a link to the appropriate contribution flow. The public
contact page provides the address and routes data reports toward the structured
contribution flows; it does not add a second unstructured web contact form.

The initial routing-only release does not promise branded replies from `contact@`. Replies
may expose the personal destination address. A branded two-way mailbox is a later product
choice, separate from the public submission workflow.

### Transactional delivery

The submission-intake release may call Cloudflare Email Sending through its REST API after
Workers Paid is explicitly authorized and the sending domain is onboarded. The API token
is stored in a Docker secret or root-readable environment file outside the repository.
Transactional templates then cover:

- Verify your email.
- Submission received.
- More information requested.
- Submission accepted as evidence.
- Submission partially accepted.
- Submission rejected or marked duplicate.
- Evidence integrated into published data.

Every message includes plain text and HTML, the submission receipt, and a reply-to address
at `contact@rvinterchange.com`. Provider calls run from an outbox worker. Only rate-limit and
temporary provider failures are retried, using bounded exponential backoff. Permanent
validation errors and hard bounces move the outbox item to `failed` and suppress repeated
sends to that address until reviewed.

Cloudflare Email Routing owns the root-domain MX, routing SPF, and routing DKIM records.
Cloudflare Email Sending will configure separate sending SPF/DKIM records on its bounce
subdomain when the later intake plan onboards outbound delivery. A DMARC policy begins in
reporting mode and moves to quarantine only after every active sender passes alignment in
reports.

## Abuse, privacy, and security controls

- Cloudflare Turnstile is required for verification requests and submission creation.
- Cloudflare edge rate limits are supplemented by application limits of five verification
  requests per hour per rotating IP digest, five submissions per verified session, and
  twenty submissions per verified email per day.
- The application trusts `CF-Connecting-IP` only because the origin is reachable solely
  through the Tunnel. Development traffic uses the socket peer address.
- Submitted text is stored and rendered as plain text. No contributor HTML or Markdown is
  rendered.
- URLs must use HTTPS, have a bounded length, and pass structural validation. The first
  release never fetches them server-side, eliminating SSRF from intake.
- Reviewer link clicks are marked as external and open with `noopener` and `noreferrer`.
- Artifact paths are generated server-side and resolved beneath one fixed root.
- CSRF protection is required on cookie-authenticated public and review mutations.
- Security headers include a restrictive Content Security Policy, frame denial, MIME
  sniffing denial, strict referrer policy, and HSTS after HTTPS operation is verified.
- Logs exclude email addresses, raw tokens, submission text, filenames, and artifact data.
- Public status responses contain workflow state and public reason copy only. They never
  contain reviewer names, private notes, abuse flags, other submissions, internal source
  tiers, or confidence calculations.
- Secrets, intake databases, uploaded files, and backups are excluded from Git and Docker
  build contexts.

## Contributor history and reputation

The system records operational history such as accepted, rejected, duplicate, and safety
submission counts. In the first release, history can affect rate-limit review and queue
priority only.

Contributor history cannot:

- Change a source tier.
- Add confidence effects.
- Auto-accept a claim.
- Auto-promote an observation.
- Auto-integrate or publish graph data.
- Reduce the independent-source requirement.

This maintains the existing rule that evidence is evaluated by source and event, capped per
actor/source, rather than treating a person as an authority.

## Operations and recovery

The local production data directory lives outside the repository under
`/data/DockerConfigs/RVInterchange/` and contains separate subdirectories for logs, intake
database, artifacts, and backups.

- SQLite backups use the online backup API or `VACUUM INTO`; copying a live WAL database as
  unrelated files is not a backup procedure.
- A daily encrypted backup includes `submissions.db`, `observations.db`, accepted artifacts,
  and configuration metadata but excludes provider tokens.
- At least one encrypted backup copy is stored off the local host.
- Restore testing occurs before public launch and quarterly afterward.
- Health checks separately report public catalog readiness, intake readiness, outbox backlog,
  artifact storage writability, and review-service readiness. Public health output is coarse;
  detailed health requires reviewer access.
- If intake is unhealthy, the contribution page displays a maintenance state while public
  search remains available.
- If email is unhealthy, verified active sessions may still submit and receive an on-screen
  receipt; new verification requests report delayed delivery without losing the outbox item.

## Google Cloud migration seam

Application code depends on these interfaces rather than directly importing provider SDKs
throughout the feature:

- `SubmissionRepository`: SQLite implementation first; Cloud SQL PostgreSQL later.
- `ArtifactStore`: private filesystem implementation first; Google Cloud Storage later.
- `TransactionalMailer`: Cloudflare REST implementation added only after Workers Paid and
  arbitrary-recipient sending are approved; it may remain unchanged after migration.
- `HumanMailbox`: Cloudflare Email Routing configuration, not an application dependency.
- `ReviewIdentity`: Cloudflare Access JWT validation, with email one-time PIN delivered
  through the routed `contact@` address for the first release.

A future Cloud Run deployment replaces local containers and persistent SQLite/filesystem
adapters. It does not change public endpoint paths, workflow states, claim semantics,
promotion idempotency, or the separation between accepted evidence and published graph
data.

## Testing strategy

### Domain and persistence tests

- Schema initialization and migration on a temporary on-disk SQLite database.
- Every allowed and forbidden workflow transition.
- Append-only review history.
- Optimistic concurrency conflict behavior.
- Idempotent promotion and interrupted-receipt reconciliation.
- Retention selection without deleting accepted referenced artifacts.
- Repository interface contract tests shared by local and future cloud adapters.

### API tests

- Verification token hashing, expiry, replay rejection, and session limits.
- Turnstile success, failure, timeout, and provider-unavailable behavior through a fake
  verifier.
- Multipart limits, MIME mismatches, corrupt images, oversized decoded images, path
  traversal names, and duplicate hashes.
- Intent-specific request validation.
- Capability-token status and follow-up authorization.
- Review Access JWT validation, audience mismatch, expiration, unlisted reviewer, and role
  enforcement.
- Escaping and information-exposure assertions for public and review responses.
- Email outbox retry and permanent-failure behavior through a fake mailer.

### Canonical integration tests

- Promotion into a temporary copy of `observations.db` adds one append-only observation with
  the expected origin reference and reviewer attribution.
- Retrying promotion returns the original observation ID.
- Intake API tests prove it cannot open canonical databases for writing.
- Promotion alone leaves a temporary `components.db` unchanged.
- A deliberately integrated fixture change still passes the canonical atomic build and
  persisted API end-to-end tests.

### Deployment tests

- Public hostname serves the site and only the intended public/intake paths.
- Public requests to debug, review, documentation, and artifact paths are denied.
- Review hostname requires Cloudflare Access and the API independently validates its JWT.
- Containers expose no unintended host interfaces.
- Search stays available while intake is stopped.
- Intake enters maintenance mode when storage is unwritable.
- Backup restoration produces a working queue and valid promotion references.

### Experience and accessibility tests

- Keyboard-only completion of verification and all three submission flows.
- Screen-reader announcements for validation, upload progress, receipt, and error states.
- Clear recovery after email delay, expired session, duplicate submission, and needs-info
  follow-up.
- Mobile layouts preserve 44-pixel touch targets and do not require horizontal scrolling.

## Release gates

The submission form is not made public until all of these are true:

- `rvinterchange.com` reaches the local site only through Cloudflare Tunnel.
- Public search uses same-origin API requests and no longer depends on exposed port `8484`.
- Public routing denies debug, review, API documentation, and artifact endpoints.
- `review.rvinterchange.com` has deny-by-default Cloudflare Access and application JWT
  validation.
- Cloudflare Email Routing forwards `contact@rvinterchange.com` and
  `dmarc-reports@rvinterchange.com` to the verified destination while catch-all routing
  remains disabled.
- Root MX, routing SPF/DKIM, and reporting-only DMARC are verified. Transactional sending
  from `notifications@rvinterchange.com` and bounce handling remain gates for the later
  submission-intake release, not this hosting release.
- A backup has been restored successfully on a clean temporary environment.
- Promotion idempotency and canonical rebuild tests pass.
- A reviewer can process representative successful-install, failed-install, documentation,
  and correction submissions end to end.
- Unverified, rejected, and accepted artifact retention behavior has been exercised.
- The public privacy and contribution terms explain email use, artifact retention, evidence
  licensing, and the difference between acceptance and publication.

## Issue structure after approval

Issue #47 should remain the product/design epic. Its child issues should cover:

1. Intake schema and repositories.
2. Verification sessions, Turnstile, and application rate limits.
3. Photo quarantine and retention.
4. Submission API and status capabilities.
5. Email outbox and Cloudflare transactional mail.
6. Reviewer identity and authorization.
7. Review queue and claim decisions.
8. Observation drafts and idempotent promotion.
9. Public contribution flows and follow-up experience.
10. Privacy, security, backup, and operational launch checks.

Issue #32 should remain the hosting epic. Its child issues should cover:

1. Same-origin Nginx routing and public-image separation.
2. Production Compose network and port isolation.
3. Cloudflare Tunnel hostnames and DNS.
4. Cloudflare Access for the review hostname.
5. Cloudflare Email Routing for contact and DMARC reports, with catch-all disabled.
6. Cloudflare transactional sending domain and arbitrary-recipient delivery validation in
   the later submission-intake plan.
7. Health checks, backup, restore, and operating guide.

The implementation plans will reference these boundaries after this design is approved.
