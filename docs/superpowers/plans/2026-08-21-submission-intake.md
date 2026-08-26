# Submission Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the quarantined public-submission backend behind the existing closed `/submission/v1/*` boundary, including verified-email sessions, Turnstile, rate limits, sanitized image storage, owner capabilities, and a transactional email outbox.

**Architecture:** Add a separate `intake` FastAPI service with write access only to `submissions.db`, a private artifact root, and intake secrets. Keep the catalog API read-only and public Nginx on its controlled `503`; run intake only under an `intake` Compose profile until mail, backup, moderation, privacy, and public-UX release gates pass.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLite, `cryptography` AES-GCM, Pillow, HTTPX, Docker Compose, pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-public-submission-queue-design.md`

## Global Constraints

- Execute after PR #58, including `c53d1de` and `515a106`, is merged to `main`; branch `feat/issue-47-submission-intake` from that updated `main`.
- Public input never writes to `observations.db`, `components.db`, components, identifiers, edges, source tiers, or confidence.
- Public Nginx continues returning its controlled `503` throughout this plan.
- The intake container receives no canonical-database or `Docs/Tools` mount.
- Raw email, tokens, submission text, filenames, artifacts, and Turnstile payloads never enter logs.
- Browser identifiers are UUIDs. Raw row numbers and raw capability/session secrets are never stored.
- Cookie-authenticated mutations require the session cookie and `X-CSRF-Token`.
- URLs are validated and stored but never fetched.
- Image limits: five files, 10 MiB each, 25 MiB total, 12,000 × 12,000 decoded pixels.
- Rate limits: five verification requests/IP digest/hour, five submissions/session, twenty submissions/email/day.
- Cloudflare Email Sending stays disabled until Workers Paid and arbitrary-recipient delivery are authorized.
- Use red-green-refactor and stage only each task's named paths. Preserve unrelated untracked work.

---

### Task 1: Isolated intake service and configuration boundary

**Files:**
- Create: `intake/__init__.py`
- Create: `intake/app.py`
- Create: `intake/config.py`
- Create: `intake/Dockerfile`
- Create: `intake/requirements.txt`
- Create: `tests/intake/__init__.py`
- Create: `tests/intake/test_app.py`
- Modify: `deploy/docker-compose.yaml`
- Modify: `tests/deploy/test_compose_contract.py`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings`, `Settings.for_tests(root) -> Settings`, `create_app(settings) -> FastAPI`, and `GET /health/`.
- Consumes: file-mounted 32-byte contact, token, session, IP-HMAC, and Turnstile secrets.

- [ ] **Step 1: Write failing app and Compose tests**

```python
def test_intake_health_uses_coarse_shape(tmp_path):
    settings = Settings.for_tests(tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Extend the Compose test with literal assertions: profile `intake` adds only `rvinterchange-intake`; it has no `ports`; writable mounts target `/app/data` and `/app/artifacts`; no mount targets `/app/Docs/Tools`.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_app.py tests/deploy/test_compose_contract.py -q`

Expected: import failure for `intake.app` and missing Compose service.

- [ ] **Step 3: Add minimal service**

```python
import os


def _required_file(name: str) -> Path:
    path = Path(os.environ[name])
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError(f"{name} must name an existing absolute file")
    return path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    artifact_root: Path
    contact_key_path: Path
    token_key_path: Path
    session_key_path: Path
    ip_key_path: Path
    turnstile_secret_path: Path
    trust_cf_connecting_ip: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=Path(os.environ["RVI_INTAKE_DB_PATH"]),
            artifact_root=Path(os.environ["RVI_ARTIFACT_ROOT"]),
            contact_key_path=_required_file("RVI_CONTACT_KEY_FILE"),
            token_key_path=_required_file("RVI_TOKEN_KEY_FILE"),
            session_key_path=_required_file("RVI_SESSION_KEY_FILE"),
            ip_key_path=_required_file("RVI_IP_KEY_FILE"),
            turnstile_secret_path=_required_file("RVI_TURNSTILE_SECRET_FILE"),
            trust_cf_connecting_ip=os.environ.get("RVI_TRUST_CF_CONNECTING_IP") == "true",
        )

    @classmethod
    def for_tests(cls, root: Path) -> "Settings":
        root.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, value in {
            "contact": b"c" * 32, "token": b"t" * 32,
            "session": b"s" * 32, "ip": b"i" * 32,
            "turnstile": b"test-secret",
        }.items():
            paths[name] = root / name
            paths[name].write_bytes(value)
        return cls(root / "submissions.db", root / "artifacts",
                   paths["contact"], paths["token"], paths["session"],
                   paths["ip"], paths["turnstile"])
```

`from_env()` requires absolute paths and readable secret files; `for_tests()` creates deterministic keys below the pytest directory.

```python
def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="RV Interchange Submission Intake",
                  docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health/")
    def health():
        return {"status": "ok"}

    return app
```

Pin FastAPI, Uvicorn, Pydantic, HTTPX, Pillow, cryptography, and python-multipart. Add profile-gated `rvinterchange-intake` with no host port, private writable data/artifact binds, and read-only Compose secrets.

- [ ] **Step 4: Verify GREEN and commit**

Run focused tests, then `python3 -m pytest tests/ Docs/Tools -q`.

```bash
git add -- intake tests/intake deploy/docker-compose.yaml tests/deploy/test_compose_contract.py
git commit -m "feat: add isolated submission intake service"
```

### Task 2: SQLite migrations and repositories

**Files:**
- Create: `intake/db.py`
- Create: `intake/migrations/001_intake.sql`
- Create: `intake/repositories.py`
- Create: `tests/intake/test_db.py`
- Create: `tests/intake/test_repositories.py`
- Modify: `intake/app.py`

**Interfaces:**
- Produces: `connect(path)`, `migrate(path)`, `transaction(conn)`, and repositories for contributors, sessions, submissions, capabilities, artifacts, outbox, and rate limits.
- Consumes: `Settings.database_path`.

- [ ] **Step 1: Write failing tests**

Test migration idempotency, `foreign_keys=1`, WAL, 5,000 ms busy timeout, UUID creation, unique token digests, five-submission reservation, and full rollback of submission/claims/artifacts/capabilities/outbox.

```python
def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "submissions.db"
    migrate(path)
    migrate(path)
    with connect(path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("SELECT version FROM schema_migrations").fetchall() == [(1,)]
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_db.py tests/intake/test_repositories.py -q`

- [ ] **Step 3: Implement migration and schema**

`connect()` uses `sqlite3.Row`, foreign keys, WAL, busy timeout, and explicit transactions. `migrate()` uses `BEGIN IMMEDIATE` and records a numbered migration only after success.

Create spec-aligned tables: `contributors`, `submission_sessions`, `submissions`, `submission_capabilities`, `submission_claims`, `submission_artifacts`, `email_outbox`, and `rate_limit_events`. Enforce controlled states with CHECK constraints, unique token digests, `UNIQUE(submission_id,id)` on claims, and one live capability per submission/purpose.

Implement these exact repository signatures: `SessionRepository.create_pending(contributor_id, token_digest, expires_at, now) -> str`, `activate(verification_digest, session_digest, csrf_digest, expires_at, now) -> sqlite3.Row`, `authenticate(session_digest, now) -> sqlite3.Row | None`, and `reserve_submission(session_id) -> None`; plus `SubmissionRepository.create_with_children(submission, claims, artifacts, capabilities, outbox) -> str`, `public_status(submission_id) -> dict | None`, `append_follow_up(submission_id, context_json, now) -> None`, and `withdraw(submission_id, now) -> None`.

Use parameterized SQL and compact, sorted JSON. Accept existing connections so service operations own atomic transactions.

- [ ] **Step 4: Initialize migration in lifespan, verify, and commit**

```bash
python3 -m pytest tests/intake/test_db.py tests/intake/test_repositories.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/app.py intake/db.py intake/migrations/001_intake.sql intake/repositories.py tests/intake/test_db.py tests/intake/test_repositories.py
git commit -m "feat: add submission intake persistence"
```

### Task 3: Contact encryption, token hashing, sessions, and CSRF

**Files:**
- Create: `intake/security.py`
- Create: `tests/intake/test_security.py`
- Modify: `intake/config.py`

**Interfaces:**
- Produces: `ContactCipher`, `TokenCodec`, `normalize_email`, `new_secret`, and CSRF verification.
- Consumes: Task 1 keys.

- [ ] **Step 1: Write failing tests**

Cover normalized email, randomized authenticated ciphertext, tamper rejection, token tampering/expiry, digest comparison, and CSRF mismatch. Assert errors contain no email or token.

```python
def test_contact_cipher_round_trip_uses_random_nonce():
    cipher = ContactCipher(b"c" * 32)
    first = cipher.encrypt("person@example.com")
    second = cipher.encrypt("person@example.com")
    assert first != second
    assert cipher.decrypt(first) == "person@example.com"
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_security.py -q`

- [ ] **Step 3: Implement primitives**

Use AES-256-GCM, random 12-byte nonce, and associated data `b"rvi-contact-v1"`. Use HMAC-SHA-256, `secrets.token_urlsafe(32)`, and `hmac.compare_digest`. Signed sessions use `v1.<expires>.<raw>.<signature>`. Normalize with NFKC, trim, lowercase ASCII local/domain, reject controls, and enforce 254 characters.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_security.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/config.py intake/security.py tests/intake/test_security.py
git commit -m "feat: secure intake contact and session tokens"
```

### Task 4: Turnstile, rotating abuse digests, and verification routes

**Files:**
- Create: `intake/turnstile.py`
- Create: `intake/rate_limits.py`
- Create: `intake/schemas.py`
- Create: `intake/routers/verification.py`
- Create: `tests/intake/test_turnstile.py`
- Create: `tests/intake/test_verification_api.py`
- Modify: `intake/app.py`

**Interfaces:**
- Produces: `TurnstileVerifier.verify(token, remote_ip)`, `RateLimiter.check_and_record(scope, subject_digest, limit, window_seconds, now)`, verification request and exchange endpoints.
- Consumes: Tasks 2-3.

- [ ] **Step 1: Write failing tests**

Cover Turnstile success/rejection/timeout/malformed/unavailable; generic `202`; five/hour; encrypted email; hashed token; outbox row; replay; 15-minute verification expiry; 24-hour session; secure cookie flags; returned CSRF stored only as digest.

```python
def test_verification_request_has_constant_response(client):
    response = client.post("/submission/v1/verification-requests", json={
        "email": "Person@Example.com", "turnstile_token": "ok"
    })
    assert response.status_code == 202
    assert response.json() == {"status": "verification_requested"}
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_turnstile.py tests/intake/test_verification_api.py -q`

- [ ] **Step 3: Implement boundaries and routes**

Post only `secret`, `response`, and `remoteip` to Cloudflare with a five-second timeout. Map invalid to 400, rate limit to 429, provider unavailable to 503. Derive daily IP digest as HMAC of date, NUL, and canonical IP. Trust `CF-Connecting-IP` only when configured.

```python
class VerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    turnstile_token: str = Field(min_length=1, max_length=4096)

class VerificationExchange(BaseModel):
    token: str = Field(min_length=32, max_length=512)
```

Request flow verifies Turnstile/rate limit, normalizes/digests/encrypts contact, upserts contributor, revokes prior pending tokens, stores a digest, and enqueues `verify_email` atomically. Exchange consumes once, marks verified, installs session/CSRF digests, and sets `rvi_contribution_session` with `HttpOnly; Secure; SameSite=Lax; Path=/submission/v1/`.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_turnstile.py tests/intake/test_verification_api.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/app.py intake/turnstile.py intake/rate_limits.py intake/schemas.py intake/routers/verification.py tests/intake/test_turnstile.py tests/intake/test_verification_api.py
git commit -m "feat: add verified contribution sessions"
```

### Task 5: Private artifact quarantine

**Files:**
- Create: `intake/artifacts.py`
- Create: `tests/intake/test_artifacts.py`
- Modify: `intake/requirements.txt`

**Interfaces:**
- Produces: `ArtifactStore.sanitize(upload, submission_id) -> StoredArtifact`, `resolve(storage_key)`, and `discard(storage_keys)`.

- [ ] **Step 1: Write failing tests**

Generate fixtures for JPEG/PNG/WebP, traversal filename, MIME mismatch, corruption, per-file/batch/dimension limits, decompression bomb, EXIF/GPS removal, random keys, derivative hash, database-failure cleanup, and fixed-root resolution.

```python
def test_sanitized_derivative_removes_exif(store, jpeg_with_gps):
    result = store.sanitize(jpeg_with_gps, submission_id="sub-1")
    assert result.storage_key.startswith("sub-1/")
    with Image.open(store.resolve(result.storage_key)) as image:
        assert image.getexif() == {}
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_artifacts.py -q`

- [ ] **Step 3: Implement sanitation**

Read a bounded spool; hash raw bytes; decode/verify/load with Pillow; reject unsupported format/mode/dimensions; re-encode with no metadata into a same-directory temporary file; fsync and `os.replace()` to `<submission UUID>/<artifact UUID>.<ext>`. Record derivative MIME, size, dimensions, and SHA-256. Resolve only paths whose real path remains beneath the fixed root.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_artifacts.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/artifacts.py intake/requirements.txt tests/intake/test_artifacts.py
git commit -m "feat: add private submission artifact quarantine"
```

### Task 6: Intent validation and atomic submission creation

**Files:**
- Create: `intake/intents.py`
- Create: `intake/routers/submissions.py`
- Create: `tests/intake/test_submission_api.py`
- Modify: `intake/app.py`
- Modify: `intake/schemas.py`

**Interfaces:**
- Produces: `POST /submission/v1/submissions`.
- Consumes: active session/CSRF, Turnstile, rate limits, repositories, artifact store.

- [ ] **Step 1: Write failing tests**

Cover three intents; consent; HTTPS/userinfo/2,048-byte URL rules; stable edge locator; file limits; session expiry; CSRF; Turnstile; session/email limits; SQL rollback plus artifact cleanup; successful redacted receipt/capabilities.

```python
def test_submission_requires_matching_csrf(client, active_cookie):
    response = client.post(
        "/submission/v1/submissions",
        cookies=active_cookie,
        files={"metadata": (None, VALID_INSTALLATION_JSON, "application/json")},
        headers={"X-CSRF-Token": "wrong"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_submission_api.py -q`

- [ ] **Step 3: Define contracts and implement**

```python
class SubmissionMetadata(BaseModel):
    intent: Literal["installation_result", "documentation_citation", "data_correction"]
    summary: str = Field(min_length=20, max_length=4000)
    target_component_id: str | None = Field(default=None, max_length=128)
    target_edge: EdgeLocator | None = None
    target_namespace: str | None = Field(default=None, max_length=64)
    target_identifier: str | None = Field(default=None, max_length=256)
    priority: Literal["normal", "high", "safety"] = "normal"
    context: dict
    claims: list[ClaimInput] = Field(min_length=1, max_length=50)
    terms_version: str = Field(min_length=1, max_length=64)
    evidence_license_version: str = Field(min_length=1, max_length=64)
    consented: Literal[True]
    turnstile_token: str = Field(min_length=1, max_length=4096)
```

Use discriminated context models. Reject canonical IDs, tiers, confidence, and graph mutations. Authenticate, verify Turnstile/rates, sanitize artifacts, then atomically reserve session count, insert submission/claims/artifact metadata, issue purpose-specific capability digests, and enqueue `submission_received`. On SQL failure, delete derivatives. Return raw capability secrets once in a 201 response.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_submission_api.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/app.py intake/intents.py intake/routers/submissions.py intake/schemas.py tests/intake/test_submission_api.py
git commit -m "feat: accept quarantined public submissions"
```

### Task 7: Owner status, follow-up, and withdrawal capabilities

**Files:**
- Create: `intake/routers/capabilities.py`
- Create: `tests/intake/test_capability_api.py`
- Modify: `intake/app.py`
- Modify: `intake/schemas.py`
- Modify: `intake/repositories.py`

**Interfaces:**
- Produces: status-query, follow-up, and withdrawal endpoints.
- Consumes: purpose-scoped capability secrets.

- [ ] **Step 1: Write failing tests**

Cover wrong submission/purpose, expiry, revocation, single-use replay, reusable status, replacement revocation, contributor isolation, additions-only follow-up, pre-promotion withdrawal, and public redaction.

```python
def test_status_response_is_redacted(client, status_secret, submission_id):
    response = client.post("/submission/v1/status-queries", json={
        "submission_id": submission_id, "capability": status_secret
    })
    assert set(response.json()) == {
        "submission_id", "status", "public_reason",
        "evidence_state", "integration_state", "updated_at"
    }
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_capability_api.py -q`

- [ ] **Step 3: Implement constant-shape authorization**

All missing/expired/revoked/consumed/wrong-purpose/wrong-submission secrets return the same 404. Status remains reusable. Follow-up/withdrawal consume inside `BEGIN IMMEDIATE`; retry returns generic 404. Follow-up only appends bounded text and sanitized images.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_capability_api.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/app.py intake/routers/capabilities.py intake/schemas.py intake/repositories.py tests/intake/test_capability_api.py
git commit -m "feat: add submission owner capabilities"
```

### Task 8: Transactional outbox without production delivery

**Files:**
- Create: `intake/mailer.py`
- Create: `intake/outbox.py`
- Create: `tests/intake/test_outbox.py`
- Modify: `intake/repositories.py`

**Interfaces:**
- Produces: `TransactionalMailer.send(message)`, `OutboxWorker.run_once(now)`, `TemporaryMailError`, `PermanentMailError`.

- [ ] **Step 1: Write failing tests**

Cover success, temporary retry delays 60/300/1,800/7,200 seconds, permanent failure, six-attempt ceiling, stale-sending recovery, just-in-time recipient decryption, and redacted logs.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/intake/test_outbox.py -q`

- [ ] **Step 3: Implement worker contract**

Claim one row in a short `BEGIN IMMEDIATE`, commit `sending`, decrypt/send outside the transaction, then record sent/retry/failed. Put `FakeMailer` only in tests. Do not add a real provider, credentials, Compose worker, or log-mailer fallback.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m pytest tests/intake/test_outbox.py -q
python3 -m pytest tests/ Docs/Tools -q
git add -- intake/mailer.py intake/outbox.py intake/repositories.py tests/intake/test_outbox.py
git commit -m "feat: add transactional submission outbox"
```

### Task 9: Closed-deployment verification and operations handoff

**Files:**
- Create: `docs/operations/rvinterchange-submission-intake.md`
- Modify: `tests/web/test_hosting_boundary.py`
- Modify: `tests/deploy/test_compose_contract.py`

**Interfaces:**
- Produces: tested profile-gated intake service and exact release-gate handoff.

- [ ] **Step 1: Add deployment assertions**

Assert public Nginx remains a non-proxied 503; default/tunnel omit intake; intake profile includes it with no host port; mounts contain no repository/canonical DB; docs/OpenAPI stay disabled.

- [ ] **Step 2: Run deployment tests**

Run: `python3 -m pytest tests/web/test_hosting_boundary.py tests/deploy/test_compose_contract.py -q`

Expected: PASS if earlier tasks preserved the boundary; otherwise correct the named invariant before documentation.

- [ ] **Step 3: Write operations handoff**

Document profile startup, health, migrations, ownership, secret generation, database/artifact locations, and shutdown. List unresolved gates: live mail authorization; encrypted/off-host backup and restore drill; privacy/terms/license; Access JWT plus reviewer grants; moderation/promotion; public UI/accessibility; explicit Nginx proxy launch.

- [ ] **Step 4: Final verification**

```bash
git diff --check
python3 -m pytest tests/ Docs/Tools -q
docker compose -f deploy/docker-compose.yaml --profile intake config --quiet
docker compose -f deploy/docker-compose.yaml --profile tunnel config --quiet
```

Start the intake profile in an isolated Compose project with temporary host directories and test secrets. Verify internal health is 200. Verify live `https://rvinterchange.com/submission/v1/status-queries` remains 503 and public search remains healthy. Do not deploy intake to production.

- [ ] **Step 5: Commit**

```bash
git add -- docs/operations/rvinterchange-submission-intake.md tests/web/test_hosting_boundary.py tests/deploy/test_compose_contract.py
git commit -m "docs: record submission intake operations"
```

## Plan self-review

- Covers quarantine persistence, verified contact, Turnstile, abuse controls, sanitation, owner capabilities, and outbox.
- Leaves moderation, Trusted/admin auth, promotion, public UI, provider activation, backup, and launch as explicit later gates.
- Uses consistent cross-task interfaces and capability purposes.
- Never opens public intake, mounts canonical data writable, or adds a production mail sender.
- Makes implementation and error behavior explicit for every task.
