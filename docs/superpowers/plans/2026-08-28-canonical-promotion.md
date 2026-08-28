# Issue #47 Canonical Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a publisher-capable admin turn a ready, normalized public-evidence draft into one traceable and idempotent canonical observation without rebuilding the public graph.

**Architecture:** Extend the quarantine database with draft, join, event, and promotion-receipt tables. Keep canonical writes behind a focused `CanonicalObservationStore`, and coordinate the two SQLite files with a recoverable sequence keyed by observation-draft UUID. The review API keeps the intake transaction locked during the bounded canonical write, requires admin and publisher authority together, and exposes no canonical or promotion data to Trusted-only callers.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite, vanilla JavaScript/CSS, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-28-canonical-promotion-design.md`

## Global Constraints

- A public submission never directly supplies a canonical observation ID, source tier, extraction method, confidence effect, or graph mutation.
- Draft creation and readiness require an active `admin` role.
- Promotion requires the same identity to have both active `admin` and active `publisher` authority.
- `observation_draft_id` is the cross-database idempotency key.
- Canonical insertion and origin insertion are one transaction in `observations.db`.
- Canonical insertion is reconciled by payload digest when intake receipt recording fails.
- Promotion sets public `evidence_state = 'available'` and `integration_state = 'pending'` but never writes or rebuilds `components.db`.
- `reviewed_public_submission` source tiers come only from the controlled evidence-kind mapping; a publisher may lower trust but never raise it.
- Contributor contact, reviewer email, private notes, abuse data, capabilities, raw artifact paths, and artifact bytes never enter `observations.db`.
- The review API receives a writable directory containing only `observations.db`; intake receives no canonical mount.
- The public intake route remains closed throughout this phase.

---

### Task 1: Add the canonical observation append boundary

**Files:**
- Modify: `Docs/Tools/observations.py`
- Create: `review/canonical.py`
- Create: `tests/review/test_canonical.py`
- Modify: `review/api.Dockerfile`

**Interfaces:**
- Consumes: the current `observations` table and `Docs.Tools.observations.content_hash`.
- Produces: `CanonicalPayload`, `canonical_payload_sha256(payload)`,
  `CanonicalObservationStore.append_or_get(payload) -> int`,
  `CanonicalObservationStore.find_origin(draft_id) -> dict | None`, and
  `CanonicalObservationStore.promoting_digest(observation_id) -> str`.
- Test helper: `initialized_observation_db(tmp_path: Path) -> Path` executes
  `observations.SCHEMA`, commits, closes the connection, and returns
  `tmp_path / "observations.db"`.

- [ ] **Step 1: Write failing compatibility and canonical-store tests**

Add real temporary-database tests that initialize through the trusted CLI schema, append a public observation, and inspect both tables directly:

```python
from Docs.Tools import observations
from review.canonical import (
    CanonicalObservationStore,
    CanonicalPayload,
    canonical_payload_sha256,
)


def payload(draft_id="draft-1"):
    return CanonicalPayload(
        draft_id=draft_id,
        submission_id="submission-1",
        source_type="dataplate_photo",
        source_name="Suburban data plate",
        source_url=None,
        raw_content="Model SF-30FQ is visible on the plate.",
        extracted={"model": "SF-30FQ"},
        source_tier=2,
        reviewer_digest="reviewer-digest",
        artifact_ids=("artifact-1",),
    )


def test_canonical_append_is_compatible_and_idempotent(tmp_path):
    path = tmp_path / "observations.db"
    with observations.get_conn(path) as conn:
        conn.executescript(observations.SCHEMA)
        conn.commit()

    store = CanonicalObservationStore(path)
    first = store.append_or_get(payload())
    replay = store.append_or_get(payload())

    assert replay == first
    with observations.get_conn(path) as conn:
        row = conn.execute("SELECT * FROM observations WHERE id = ?", (first,)).fetchone()
        origin = conn.execute("SELECT * FROM observation_origins").fetchone()
    assert row["extraction_method"] == "reviewed_public_submission"
    assert row["fetched_by"] == "reviewer-digest"
    assert row["source_tier"] == 2
    assert origin["origin_id"] == "draft-1"
    assert origin["canonical_payload_sha256"] == canonical_payload_sha256(payload())


def test_existing_origin_with_different_payload_fails_closed(tmp_path):
    path = initialized_observation_db(tmp_path)
    store = CanonicalObservationStore(path)
    store.append_or_get(payload())

    with pytest.raises(CanonicalIntegrityError, match="origin payload mismatch"):
        store.append_or_get(replace(payload(), raw_content="different"))
```

The test helper `initialized_observation_db()` belongs in `tests/review/test_canonical.py` and must initialize the real schema, not mock SQLite.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m pytest tests/review/test_canonical.py -q
```

Expected: collection fails because `review.canonical` does not exist. Do not create production code until this failure is observed.

- [ ] **Step 3: Make the trusted observation helper transaction-safe**

In `Docs/Tools/observations.py`, add `field_report` to `SOURCE_TYPES`, include `observation_origins` in `SCHEMA`, and split insertion into a non-committing primitive plus the existing committing wrapper:

```python
def append_observation(conn, *, source_type, source_name, url, raw_content,
                       extracted, extraction_method, fetched_by,
                       source_tier=None):
    h = content_hash(raw_content)
    cursor = conn.execute(
        """INSERT INTO observations
           (source_type, source_name, url, fetched_at, fetched_by,
            content_hash, raw_content, extracted, extraction_method, source_tier)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_type, source_name, url, now_iso(), fetched_by, h, raw_content,
         json.dumps(extracted) if extracted is not None else None,
         extraction_method, source_tier),
    )
    return cursor.lastrowid


def insert_observation(conn, **values):
    observation_id = append_observation(conn, **values)
    conn.commit()
    return observation_id
```

Keep all current CLI calls valid by retaining their existing keyword defaults. Add this table to `SCHEMA`:

```sql
CREATE TABLE IF NOT EXISTS observation_origins (
    observation_id INTEGER PRIMARY KEY REFERENCES observations(id),
    origin_type TEXT NOT NULL CHECK (origin_type = 'public_submission_draft'),
    origin_id TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    artifact_ids_json TEXT NOT NULL CHECK (json_valid(artifact_ids_json)),
    canonical_payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(origin_type, origin_id)
);
```

- [ ] **Step 4: Implement the canonical store and digest**

Create immutable `CanonicalPayload` fields exactly as used by the test. Serialize
this evidence-only digest input with sorted JSON keys and compact separators:

```python
def canonical_payload_sha256(payload):
    confirmed = {
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
    encoded = json.dumps(
        confirmed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

The reviewer digest is intentionally absent from `confirmed` but remains on the
observation row as action metadata. `append_or_get()` must:

```python
with observations.get_conn(self.path) as conn:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(observations.SCHEMA)
    existing = conn.execute(
        """SELECT observation_id, canonical_payload_sha256
           FROM observation_origins
           WHERE origin_type = 'public_submission_draft' AND origin_id = ?""",
        (payload.draft_id,),
    ).fetchone()
    if existing:
        if existing["canonical_payload_sha256"] != digest:
            raise CanonicalIntegrityError("origin payload mismatch")
        return existing["observation_id"]
    conn.execute("BEGIN IMMEDIATE")
    observation_id = observations.append_observation(
        conn,
        source_type=payload.source_type,
        source_name=payload.source_name,
        url=payload.source_url,
        raw_content=payload.raw_content,
        extracted=payload.extracted,
        extraction_method="reviewed_public_submission",
        fetched_by=payload.reviewer_digest,
        source_tier=payload.source_tier,
    )
    conn.execute(
        """INSERT INTO observation_origins
           (observation_id, origin_type, origin_id, submission_id,
            artifact_ids_json, canonical_payload_sha256, created_at)
           VALUES (?, 'public_submission_draft', ?, ?, ?, ?, ?)""",
        (observation_id, payload.draft_id, payload.submission_id,
         json.dumps(sorted(payload.artifact_ids)), digest, observations.now_iso()),
    )
    conn.commit()
    return observation_id
```

Catch `sqlite3.IntegrityError` from a competing origin insert, roll back, reload by origin, compare the digest, and return the existing ID only on an exact match.

- [ ] **Step 5: Copy only the canonical helper dependencies into the review image**

Add these lines to `review/api.Dockerfile`:

```dockerfile
COPY Docs/Tools/observations.py /app/Docs/Tools/observations.py
COPY Docs/Tools/resolver.py /app/Docs/Tools/resolver.py
```

Do not copy either database file or the whole `Docs/Tools` directory.

- [ ] **Step 6: Verify GREEN and existing CLI compatibility**

Run:

```bash
python3 -m pytest tests/review/test_canonical.py Docs/Tools/test_edge_resolver.py -q
python3 Docs/Tools/observations.py --help >/dev/null
```

Expected: all selected tests pass and the CLI exits zero.

- [ ] **Step 7: Commit Task 1**

```bash
git add Docs/Tools/observations.py review/canonical.py review/api.Dockerfile tests/review/test_canonical.py
git diff --cached --check
git commit -m "feat: add canonical observation append boundary"
```

### Task 2: Add normalized observation-draft persistence

**Files:**
- Create: `intake/migrations/003_promotion.sql`
- Create: `review/drafts.py`
- Create: `tests/review/test_drafts.py`
- Create: `tests/review/promotion_helpers.py`
- Modify: `review/repositories.py`

**Interfaces:**
- Consumes: accepted claims, clean artifacts, `Docs.Tools.resolver.normalize_extracted`, and the existing intake transaction boundary.
- Produces: `DraftRepository.create()`, `DraftRepository.mark_ready()`, `DraftRepository.get()`, `DraftRepository.list_for_submission()`, and `DraftConflict`.
- Test helper: `seed_accepted_evidence(conn) -> AcceptedEvidence` creates one
  accepted submission, accepted claim, and clean artifact and returns their IDs;
  `seed_submission(conn) -> str` and `seed_accepted_claim(conn, submission_id) -> str`
  create the cross-submission negative fixtures.

- [ ] **Step 1: Write failing migration and repository tests**

Cover accepted-claim enforcement, cross-submission claim and artifact rejection, clean-artifact enforcement, normalization, state/version transitions, withdrawn submissions, and append-only events:

```python
def test_create_and_ready_draft_normalizes_and_links_evidence(seeded_accepted):
    conn, submission_id, claim_id, artifact_id = seeded_accepted
    drafts = DraftRepository(conn)
    draft = drafts.create(
        submission_id,
        source_type="dataplate_photo",
        source_name="Suburban data plate",
        source_url=None,
        raw_content="Model SF-30FQ is visible.",
        extracted={"model_number": "SF-30FQ"},
        claim_ids=[claim_id],
        artifact_ids=[artifact_id],
        reviewer_digest="admin-digest",
        idempotency_key="draft-1",
    )
    ready = drafts.mark_ready(
        draft["id"], expected_version=1, reviewer_digest="admin-digest"
    )

    assert draft["extracted"] == {"model": "SF-30FQ"}
    assert draft["default_source_tier"] == 2
    assert ready["state"] == "ready"
    assert ready["version"] == 2
    assert [event["action"] for event in drafts.events(draft["id"])] == [
        "draft_created", "draft_ready"
    ]


def test_draft_rejects_claim_from_another_submission(seeded_accepted):
    conn, submission_id, _claim_id, artifact_id = seeded_accepted
    other_claim = seed_accepted_claim(conn, seed_submission(conn))
    with pytest.raises(DraftConflict, match="accepted claim does not belong"):
        DraftRepository(conn).create(
            submission_id,
            source_type="field_report",
            source_name="Owner field report",
            source_url=None,
            raw_content="Observed installation.",
            extracted={"model": "SW6DE"},
            claim_ids=[other_claim],
            artifact_ids=[artifact_id],
            reviewer_digest="admin-digest",
            idempotency_key="wrong-submission",
        )
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m pytest tests/review/test_drafts.py -q
```

Expected: collection fails because `review.drafts` and migration 003 do not exist.

- [ ] **Step 3: Add migration 003 with enforced composite ownership**

Create `observation_drafts`, `observation_draft_claims`,
`observation_draft_artifacts`, `promotion_receipts`,
`promotion_replay_keys`, and `promotion_events`. Use these checks and keys:

```sql
CREATE UNIQUE INDEX submission_artifacts_submission_id_id_uq
    ON submission_artifacts(submission_id, id);

CREATE TABLE observation_drafts (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    created_by_digest TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'manufacturer_page', 'manufacturer_pdf', 'manual_measurement',
        'dataplate_photo', 'dealer_call', 'field_report', 'other',
        'retailer_page', 'retailer_prose', 'forum_post'
    )),
    source_name TEXT NOT NULL CHECK (length(source_name) BETWEEN 1 AND 300),
    source_url TEXT,
    raw_content TEXT NOT NULL CHECK (length(raw_content) BETWEEN 1 AND 12000),
    extracted_json TEXT NOT NULL CHECK (json_valid(extracted_json)),
    default_source_tier INTEGER NOT NULL CHECK (default_source_tier BETWEEN 1 AND 9),
    state TEXT NOT NULL CHECK (state IN ('draft', 'ready', 'promoted', 'superseded')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(submission_id, id)
);
```

Each join table stores `submission_id` and uses composite foreign keys to both its draft and child record. `promotion_receipts.observation_draft_id`, `promotion_receipts.idempotency_key`, and `(origin_type, origin_id)` on the canonical side are unique. `promotion_events.action` is restricted to `draft_created`, `draft_ready`, `promoted`, and `promotion_reconciled`.

Use these exact remaining table contracts:

```sql
CREATE TABLE observation_draft_claims (
    submission_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (draft_id, claim_id),
    FOREIGN KEY (submission_id, draft_id)
        REFERENCES observation_drafts(submission_id, id),
    FOREIGN KEY (submission_id, claim_id)
        REFERENCES submission_claims(submission_id, id)
);

CREATE TABLE observation_draft_artifacts (
    submission_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    PRIMARY KEY (draft_id, artifact_id),
    FOREIGN KEY (submission_id, draft_id)
        REFERENCES observation_drafts(submission_id, id),
    FOREIGN KEY (submission_id, artifact_id)
        REFERENCES submission_artifacts(submission_id, id)
);

CREATE TABLE promotion_receipts (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    observation_draft_id TEXT NOT NULL UNIQUE REFERENCES observation_drafts(id),
    canonical_observation_id INTEGER NOT NULL,
    canonical_payload_sha256 TEXT NOT NULL CHECK (length(canonical_payload_sha256) = 64),
    promoted_by_digest TEXT NOT NULL,
    source_tier INTEGER NOT NULL CHECK (source_tier BETWEEN 1 AND 9),
    promoted_at TEXT NOT NULL,
    integration_state TEXT NOT NULL DEFAULT 'pending'
        CHECK (integration_state IN ('pending', 'integrated', 'not_applicable'))
);

CREATE TABLE promotion_replay_keys (
    idempotency_key TEXT PRIMARY KEY,
    promotion_id TEXT NOT NULL REFERENCES promotion_receipts(id),
    request_sha256 TEXT NOT NULL CHECK (length(request_sha256) = 64),
    created_at TEXT NOT NULL
);

CREATE TABLE promotion_events (
    id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL,
    observation_draft_id TEXT NOT NULL,
    promotion_id TEXT REFERENCES promotion_receipts(id),
    actor_digest TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN (
        'draft_created', 'draft_ready', 'promoted', 'promotion_reconciled'
    )),
    prior_state TEXT,
    resulting_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (submission_id, observation_draft_id)
        REFERENCES observation_drafts(submission_id, id)
);

CREATE INDEX promotion_events_draft_idx
    ON promotion_events(observation_draft_id, created_at, id);
```

- [ ] **Step 4: Implement strict normalization and tier mapping**

In `review/drafts.py`, define:

```python
BEST_SOURCE_TIERS = {
    "manufacturer_page": 2,
    "manufacturer_pdf": 2,
    "manual_measurement": 2,
    "dataplate_photo": 2,
    "dealer_call": 2,
    "field_report": 4,
    "other": 4,
    "retailer_page": 7,
    "retailer_prose": 8,
    "forum_post": 9,
}


def normalize_draft_extracted(extracted: dict) -> dict:
    result = resolver.normalize_extracted("draft", extracted, strict=True)
    return result["attributes"]
```

Require a nonempty list of unique accepted claim IDs. Require every artifact to
belong to the same submission and have `scan_status = 'clean'`. Sort claim and
artifact IDs before insertion and response serialization. On draft-creation
idempotency replay, compare the submission, normalized source fields, sorted
claim IDs, sorted artifact IDs, and actor digest; return the existing draft only
when all match and otherwise raise `DraftConflict("idempotency key conflict")`.

- [ ] **Step 5: Implement optimistic draft transitions and redacted detail**

`mark_ready()` must update with `WHERE id = ? AND state = 'draft' AND version = ?`, require exactly one changed row, recheck joins, append the event, and return version 2. Extend `ReviewRepository.detail()` so it can include sanitized draft summaries for admins without returning `created_by_digest`, reviewer digests, or canonical receipts to Trusted callers.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 -m pytest tests/review/test_drafts.py tests/review/test_repositories.py tests/intake/test_db.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add intake/migrations/003_promotion.sql review/drafts.py review/repositories.py tests/review/test_drafts.py tests/review/promotion_helpers.py
git diff --cached --check
git commit -m "feat: add normalized observation drafts"
```

### Task 3: Add all-of authorization and draft API contracts

**Files:**
- Modify: `review/auth.py`
- Modify: `review/schemas.py`
- Modify: `review/routers.py`
- Modify: `tests/review/test_auth.py`
- Modify: `tests/review/test_api.py`

**Interfaces:**
- Consumes: Task 2 draft repository and current Access identity loading.
- Produces: `ReviewerAuthorizer.require_all()`, draft creation/readiness routes, and role-shaped detail responses.
- Test helper: `AuthorizationHarness.grant(roles: set[str], capabilities:
  set[str])` replaces active rows for `reviewer@example.com`, and exposes the
  real `ReviewerAuthorizer`, signed request, migrated connection, and test settings.

- [ ] **Step 1: Write failing all-of authorization tests**

Add four real local-grant cases:

```python
@pytest.mark.parametrize(
    ("roles", "capabilities"),
    [
        ({"admin"}, set()),
        ({"trusted"}, {"publisher"}),
        ({"trusted"}, set()),
        (set(), {"publisher"}),
    ],
)
def test_require_all_rejects_partial_authority(auth_harness, roles, capabilities):
    auth_harness.grant(roles=roles, capabilities=capabilities)
    with pytest.raises(HTTPException) as error:
        auth_harness.authorizer.require_all(
            auth_harness.request, roles={"admin"}, capabilities={"publisher"}
        )
    assert error.value.status_code in {401, 403}


def test_require_all_accepts_admin_with_publisher(auth_harness):
    auth_harness.grant(roles={"admin"}, capabilities={"publisher"})
    identity = auth_harness.authorizer.require_all(
        auth_harness.request, roles={"admin"}, capabilities={"publisher"}
    )
    assert identity.roles == {"admin"}
    assert identity.capabilities == {"publisher"}
```

- [ ] **Step 2: Write failing draft API and response-shaping tests**

Test the exact routes from the specification. Assert admin can create/ready,
Trusted receives `403`, Trusted detail contains no `drafts`, admin detail has a
sanitized draft summary, and every unexpected request field returns `422`:

```python
response = client.post(
    f"/review/v1/submissions/{submission_id}/observation-drafts",
    headers=admin_headers,
    json={
        "source_type": "dataplate_photo",
        "source_name": "Suburban data plate",
        "source_url": None,
        "raw_content": "Model SF-30FQ is visible.",
        "extracted": {"model_number": "SF-30FQ"},
        "claim_ids": [claim_id],
        "artifact_ids": [artifact_id],
        "idempotency_key": "draft-1",
    },
)
assert response.status_code == 201
draft = response.json()
ready = client.post(
    f"/review/v1/observation-drafts/{draft['id']}/ready",
    headers=admin_headers,
    json={"expected_version": draft["version"]},
)
assert ready.json()["state"] == "ready"
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest tests/review/test_auth.py tests/review/test_api.py -q
```

Expected: failures identify the missing `require_all` method and draft routes.

- [ ] **Step 4: Implement `require_all` without changing existing OR behavior**

Refactor identity loading into one private method, then implement:

```python
def require_all(self, request, *, roles=frozenset(), capabilities=frozenset()):
    identity = self._load_identity(request)
    if not roles.issubset(identity.roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "review role required")
    if not capabilities.issubset(identity.capabilities):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "review capability required")
    return identity
```

Preserve `require()` for current moderation endpoints and their existing tests.

- [ ] **Step 5: Add strict Pydantic schemas and draft routes**

Set `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)` on new inputs. Bound source name to 300 characters, raw content to 12,000 characters, each ID list to 1–100 unique strings, extracted JSON to an object, and URL to HTTP/HTTPS. Add:

```python
class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_type: Literal[
        "manufacturer_page", "manufacturer_pdf", "manual_measurement",
        "dataplate_photo", "dealer_call", "field_report", "other",
        "retailer_page", "retailer_prose", "forum_post",
    ]
    source_name: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl | None = None
    raw_content: str = Field(min_length=1, max_length=12_000)
    extracted: dict[str, Any]
    claim_ids: list[str] = Field(min_length=1, max_length=100)
    artifact_ids: list[str] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=200)


class DraftReady(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
```

Authorize both mutations with active admin role, wrap each repository call in `db.transaction`, and map `DraftConflict` to `409`.

- [ ] **Step 6: Verify GREEN and authorization regressions**

Run:

```bash
python3 -m pytest tests/review/test_auth.py tests/review/test_api.py tests/review/test_drafts.py -q
```

Expected: all selected tests pass, including the legacy decision/assessment cases.

- [ ] **Step 7: Commit Task 3**

```bash
git add review/auth.py review/schemas.py review/routers.py tests/review/test_auth.py tests/review/test_api.py
git diff --cached --check
git commit -m "feat: add authorized observation draft API"
```

### Task 4: Implement recoverable publisher promotion

**Files:**
- Create: `review/promotion.py`
- Modify: `review/config.py`
- Modify: `review/schemas.py`
- Modify: `review/routers.py`
- Modify: `review/repositories.py`
- Create: `tests/review/test_promotion.py`
- Modify: `tests/review/promotion_helpers.py`
- Modify: `tests/review/test_api.py`

**Interfaces:**
- Consumes: Task 1 canonical store, Task 2 ready drafts, Task 3 all-of authorization.
- Produces: `PromotionService.payload_for()`, `PromotionService.preview()`,
  `PromotionService.promote()`, `promotion_request_sha256()`,
  `DraftRepository.receipt_by_draft()`,
  `DraftRepository.receipt_by_replay_key()`,
  `DraftRepository.assert_replay_compatible()`,
  `DraftRepository.assert_request_replay_compatible()`,
  `DraftRepository.add_replay_key()`,
  `DraftRepository.ready_for_promotion()`,
  `DraftRepository.record_promotion()`, canonical-preview route, and promotion route.
- Test helper: `PromotionHarness.ready_draft() -> dict`, `preview(draft) -> dict`,
  `promote(draft, preview, key) -> dict`, `observation_count() -> int`,
  `origin_count() -> int`, `receipt_count() -> int`, and `submission() -> dict`
  plus `linked_artifact() -> dict` operate on distinct temporary real SQLite
  files. `InjectedFailure` is a test-local `RuntimeError` subclass.

- [ ] **Step 1: Write failing service tests for the complete happy path**

Use real temporary intake and canonical databases:

```python
def test_ready_draft_promotes_once(promotion_harness):
    draft = promotion_harness.ready_draft()
    preview = promotion_harness.service.preview(draft["id"], final_source_tier=2)
    receipt = promotion_harness.service.promote(
        draft["id"],
        expected_version=draft["version"],
        confirmed_payload_sha256=preview["canonical_payload_sha256"],
        idempotency_key="promotion-1",
        final_source_tier=2,
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
```

- [ ] **Step 2: Add failing replay, failure-injection, and mismatch tests**

Cover same-key replay, new-key same-draft replay, one-key different-draft collision,
stale version, non-ready draft, final tier better than default, and this required recovery case:

```python
def test_retry_reconciles_canonical_commit_without_receipt(promotion_harness):
    draft = promotion_harness.ready_draft()
    preview = promotion_harness.preview(draft)
    promotion_harness.service.after_canonical_write = (
        lambda: (_ for _ in ()).throw(InjectedFailure("after canonical"))
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
```

- [ ] **Step 3: Run service tests and verify RED**

Run:

```bash
python3 -m pytest tests/review/test_promotion.py -q
```

Expected: collection fails because `review.promotion` does not exist.

- [ ] **Step 4: Add canonical path configuration**

Add `observations_database_path: Path` to `Settings`; load it from
`RVI_OBSERVATIONS_DB_PATH`; and make `Settings.for_tests()` default to a sibling
`observations.db` unless the test supplies a distinct path. No default production
path is allowed.

- [ ] **Step 5: Implement deterministic preview and tier enforcement**

`preview()` loads a ready draft and sorted joins, validates
`default_source_tier <= final_source_tier <= 9`, constructs `CanonicalPayload`,
and returns the exact JSON-safe evidence payload plus its digest. The digest
includes draft and submission origins, source fields, normalized extracted JSON,
sorted artifact IDs, and final tier. It excludes reviewer digest, timestamps, and
client idempotency keys so a different currently authorized publisher can
reconcile an interrupted request without changing the confirmed evidence.

- [ ] **Step 6: Implement the locked recoverable promotion sequence**

The router opens `db.transaction(intake_conn)` before calling `promote()`. Inside
that transaction, hash client-key semantics independently from the evidence
payload:

```python
def promotion_request_sha256(draft_id, payload_sha256, final_source_tier):
    encoded = json.dumps(
        {
            "draft_id": draft_id,
            "canonical_payload_sha256": payload_sha256,
            "final_source_tier": final_source_tier,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

Then `promote()` must:

```python
request_sha256 = promotion_request_sha256(
    draft_id, confirmed_payload_sha256, final_source_tier
)
replay = drafts.receipt_by_replay_key(idempotency_key)
if replay:
    drafts.assert_request_replay_compatible(replay, request_sha256)
    return replay

receipt = drafts.receipt_by_draft(draft_id)
if receipt:
    drafts.assert_replay_compatible(receipt, confirmed_payload_sha256)
    drafts.add_replay_key(
        idempotency_key, receipt["id"], request_sha256
    )
    return receipt

draft = drafts.ready_for_promotion(draft_id, expected_version)
payload = self.payload_for(draft, final_source_tier, reviewer_digest)
if canonical_payload_sha256(payload) != confirmed_payload_sha256:
    raise PromotionConflict("canonical payload changed")

prior_origin = self.canonical.find_origin(draft_id)
observation_id = self.canonical.append_or_get(payload)
self.after_canonical_write()
receipt = drafts.record_promotion(
    draft=draft,
    observation_id=observation_id,
    payload_sha256=confirmed_payload_sha256,
    idempotency_key=idempotency_key,
    promoted_by_digest=self.canonical.promoting_digest(observation_id),
    reconciled_by_digest=reviewer_digest,
    source_tier=final_source_tier,
    reconciled=prior_origin is not None,
)
return receipt
```

`record_promotion()` inserts the receipt and event, transitions the draft from
`ready` to `promoted`, increments its version, and updates the submission to
`evidence_state = 'available'`, `integration_state = 'pending'` in the same
intake transaction. It also changes every linked clean artifact to
`retention_class = 'accepted_evidence'` and clears `purge_after`; it does not
change unlinked artifacts. Receipt creation inserts the initial row in
`promotion_replay_keys`; every compatible alternate key is inserted before its
replay response is returned.

- [ ] **Step 7: Add publisher-only preview and promotion endpoints**

Add strict inputs:

```python
class PromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    canonical_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=200)
    final_source_tier: int = Field(ge=1, le=9)
```

Expose:

```text
GET  /review/v1/observation-drafts/{draft_id}/canonical-preview?final_source_tier=N
POST /review/v1/observation-drafts/{draft_id}/promotions
```

Call `require_all(roles={"admin"}, capabilities={"publisher"})` before draft lookup.
Map canonical integrity and promotion conflicts to `409` without returning paths,
SQL text, digests from other records, or exception internals.

- [ ] **Step 8: Verify service and API GREEN**

Run:

```bash
python3 -m pytest tests/review/test_promotion.py tests/review/test_api.py tests/review/test_auth.py -q
```

Expected: all selected tests pass, including admin-only and publisher-only `403`
cases and the post-canonical recovery test.

- [ ] **Step 9: Commit Task 4**

```bash
git add review/promotion.py review/config.py review/schemas.py review/routers.py review/repositories.py tests/review/test_promotion.py tests/review/promotion_helpers.py tests/review/test_api.py
git diff --cached --check
git commit -m "feat: add recoverable canonical promotion"
```

### Task 5: Add the private draft and promotion experience

**Files:**
- Modify: `review/index.html`
- Modify: `review/admin.js`
- Modify: `review/style.css`
- Modify: `tests/review/test_ui_contract.py`

**Interfaces:**
- Consumes: Task 3 draft routes and Task 4 preview/promotion routes.
- Produces: accessible draft editor, ready-state preview, publisher confirmation, and distinct workflow states.

- [ ] **Step 1: Write failing behavior-oriented UI contract tests**

Extend the existing static contract test to require semantic hooks and API paths:

```python
def test_review_ui_exposes_distinct_draft_and_promotion_actions():
    html = read("review/index.html")
    script = read("review/admin.js")
    assert 'id="evidence-workflow"' in html
    assert "/observation-drafts" in script
    assert "/canonical-preview" in script
    assert "/promotions" in script
    assert "canPromote" in script
    assert 'roles.includes("admin")' in script
    assert 'capabilities.includes("publisher")' in script
    assert "integration pending" in script.lower()
```

Add browser-independent unit coverage only for pure serialization helpers. Do not
test by asserting hidden controls alone; API authorization tests remain authoritative.

- [ ] **Step 2: Run UI tests and verify RED**

Run:

```bash
python3 -m pytest tests/review/test_ui_contract.py -q
```

Expected: failure because draft/promotion hooks are absent.

- [ ] **Step 3: Add semantic evidence-workflow markup**

Add an `aria-labelledby` evidence section, an `aria-live="polite"` result region,
and real labeled controls for source type, source name, URL, raw description,
extracted JSON, accepted-claim selection, clean-artifact selection, final tier,
and publisher confirmation. Keep every action reachable without keyboard
shortcuts.

- [ ] **Step 4: Implement role-aware draft and promotion behavior**

Replace the current `canDecide()` helper with separate permissions:

```javascript
function canAdminister() {
  return reviewer.roles.includes("admin");
}

function canPromote() {
  return reviewer.roles.includes("admin") &&
    reviewer.capabilities.includes("publisher");
}
```

Render the draft editor only for admins, the exact preview and confirmation only
for `canPromote()`, and no draft or receipt data for Trusted-only detail responses.
After each mutation, reload detail from the server. Preserve editor values after
`409`, `422`, or network failure and show the returned safe message in the live
region rather than relying on `window.alert`.

- [ ] **Step 5: Render distinct authoritative states**

Acceptance comes from submission status, promotion comes from a promotion receipt
or promoted draft, and integration comes from `submission.integration_state`.
Display `integration pending` after promotion and include copy stating that public
lookup has not changed.

- [ ] **Step 6: Verify UI GREEN**

Run:

```bash
python3 -m pytest tests/review/test_ui_contract.py tests/review/test_api.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 5**

```bash
git add review/index.html review/admin.js review/style.css tests/review/test_ui_contract.py
git diff --cached --check
git commit -m "feat: add canonical promotion review workflow"
```

### Task 6: Enforce deployment isolation and document recovery operations

**Files:**
- Modify: `deploy/docker-compose.yaml`
- Modify: `tests/deploy/test_compose_contract.py`
- Modify: `docs/operations/rvinterchange-moderation-review.md`
- Create: `tests/review/test_promotion_drill.py`

**Interfaces:**
- Consumes: `RVI_OBSERVATIONS_DB_PATH`, the review API image, and the two-database promotion service.
- Produces: dedicated canonical-directory mount contract, operator initialization/rollback procedure, and deterministic isolated recovery drill.

- [ ] **Step 1: Write failing Compose isolation tests**

Require a dedicated canonical source directory and reject broad tool mounts:

```python
def test_review_api_mounts_only_dedicated_canonical_directory():
    config = rendered_compose(
        environment={"RVI_CANONICAL_DATA_DIR": "/tmp/rvi-canonical"}
    )
    service = config["services"]["rvinterchange-review-api"]
    writable = {
        mount["target"]: mount["source"]
        for mount in service["volumes"]
        if not mount.get("read_only", False)
    }
    assert writable["/app/canonical"] == "/tmp/rvi-canonical"
    assert service["environment"]["RVI_OBSERVATIONS_DB_PATH"] == (
        "/app/canonical/observations.db"
    )
    assert "/app/Docs/Tools" not in {
        mount["target"] for mount in service["volumes"]
    }
    assert all("components.db" not in mount["source"] for mount in service["volumes"])
```

- [ ] **Step 2: Run Compose tests and verify RED**

Run:

```bash
python3 -m pytest tests/deploy/test_compose_contract.py -q
```

Expected: the canonical mount and environment assertions fail.

- [ ] **Step 3: Add the narrow canonical mount**

Set:

```yaml
environment:
  RVI_OBSERVATIONS_DB_PATH: /app/canonical/observations.db
volumes:
  - ${RVI_INTAKE_DATA_DIR:-/data/DockerConfigs/RVInterchange/intake/data}:/app/data
  - ${RVI_CANONICAL_DATA_DIR:-/data/DockerConfigs/RVInterchange/canonical}:/app/canonical
```

Do not add the mount to intake, catalog API, public web, review Nginx, or
cloudflared. Keep `components.db` available only through the existing read-only
catalog mount.

- [ ] **Step 4: Write the executable isolated recovery drill**

Create a pytest integration test that seeds one accepted claim and ready draft in
a temporary intake database, initializes a temporary canonical database, injects
the post-canonical exception, retries, and asserts:

```python
def scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


assert scalar(canonical, "SELECT COUNT(*) FROM observations") == 1
assert scalar(canonical, "SELECT COUNT(*) FROM observation_origins") == 1
assert scalar(intake, "SELECT COUNT(*) FROM promotion_receipts") == 1
assert scalar(intake, "SELECT COUNT(*) FROM promotion_events WHERE action = 'promotion_reconciled'") == 1
assert submission["evidence_state"] == "available"
assert submission["integration_state"] == "pending"
assert not components_path.exists()
```

- [ ] **Step 5: Document initialization, checksum, recovery, and rollback**

Update the runbook with exact operator commands that:

1. stop the review API before initializing the canonical directory;
2. copy a verified current `observations.db` snapshot into the dedicated directory;
3. compare SHA-256 checksums before first start;
4. set ownership and mode without granting intake access;
5. run the isolated promotion/reconciliation drill against temporary paths;
6. leave public intake disabled; and
7. roll back the review API while retaining both databases for investigation.

The runbook must explicitly prohibit copying `components.db` into the canonical
write directory and prohibit running the recovery drill against production paths.

- [ ] **Step 6: Verify deployment and drill GREEN**

Run:

```bash
python3 -m pytest tests/deploy/test_compose_contract.py tests/review/test_promotion_drill.py -q
docker compose -f deploy/docker-compose.yaml config --quiet
docker compose -f deploy/docker-compose.yaml --profile tunnel config --quiet
```

Expected: tests pass and both Compose renders exit zero.

- [ ] **Step 7: Commit Task 6**

```bash
git add deploy/docker-compose.yaml tests/deploy/test_compose_contract.py docs/operations/rvinterchange-moderation-review.md tests/review/test_promotion_drill.py
git diff --cached --check
git commit -m "docs: add canonical promotion operations"
```

### Task 7: Run the phase release gate and prepare review handoff

**Files:**
- Modify only files needed to fix verified failures from the commands below.
- Create during subagent-driven execution only: `.superpowers/sdd/2026-08-28-canonical-promotion/progress.md`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: fresh verification evidence and a reviewable branch; no production deployment.

- [ ] **Step 1: Run every focused promotion boundary test together**

```bash
python3 -m pytest \
  tests/review/test_canonical.py \
  tests/review/test_drafts.py \
  tests/review/test_auth.py \
  tests/review/test_api.py \
  tests/review/test_promotion.py \
  tests/review/test_promotion_drill.py \
  tests/review/test_ui_contract.py \
  tests/deploy/test_compose_contract.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run the full repository suite**

```bash
python3 -m pytest tests/ Docs/Tools -q
```

Expected: zero failures.

- [ ] **Step 3: Run source and configuration checks**

```bash
git diff --check origin/main...HEAD
docker compose -f deploy/docker-compose.yaml config --quiet
docker compose -f deploy/docker-compose.yaml --profile tunnel config --quiet
```

Expected: every command exits zero.

- [ ] **Step 4: Verify the phase invariants directly**

Run the isolated recovery drill once with verbose output and inspect the temporary
database assertions:

```bash
python3 -m pytest tests/review/test_promotion_drill.py -vv
```

Confirm one observation, one origin, one receipt, `available` evidence,
`pending` integration, no `components.db`, and no public route change.

- [ ] **Step 5: Request independent code review**

Provide the reviewer with:

```text
DESCRIPTION: Issue #47 canonical promotion from accepted drafts into observations.db
REQUIREMENTS: docs/superpowers/specs/2026-08-28-canonical-promotion-design.md
BASE_SHA: origin/main
HEAD_SHA: current branch HEAD
FOCUS: authority AND semantics, cross-database idempotency/recovery, canonical privacy, source-tier bounds, mount isolation
```

Fix every Critical or Important finding with a failing regression test first, rerun
the affected focused tests, and request re-review. Do not advance with an unresolved
Critical or Important finding.

- [ ] **Step 6: Re-run the complete verification gate after review fixes**

Repeat Steps 1–4 from the final reviewed commit. Record exact test counts and
commit IDs in the execution ledger or handoff notes.

- [ ] **Step 7: Prepare the GitHub handoff without deploying**

Prepare a PR summary that states canonical promotion is implemented but graph
integration, backup/restore automation, public contribution forms, and public
evidence ledger remain separate Issue #47 phases. Do not deploy, enable intake,
push, create a PR, or update Issue #47 unless the user authorizes those external
changes.
