# Stage 2 Public API — Phased Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the minimal read-only Public API described in
`Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md`, scoped down to what
`PLAN-Staged_Build.md` actually calls for at v0 — no accounts, no listings, no dealer
workflow — reading directly from the already-built `Docs/Tools/interchange_store.py` SQLite
store, plus a personal-use-only Dockerized test website (a lookup form talking to the API)
so the API is actually exercisable by hand instead of only via `curl`.

**Architecture:** Thin Service Layer (`api/services.py`) wraps the existing Repository
Layer (`Docs/Tools/interchange_store.py` already fills this role per the API design doc —
it isolates SQLite from the resolver logic; it just needs three new read functions). A
FastAPI app (`api/main.py`) exposes two endpoints over that service layer. No auth, no
Dealer API, no publication-workflow gate — the canonical rebuild command writes the
published `components.db` snapshot, and the API reads that on-disk store as the de facto
"published" set. A static single-page test website (`web/`) calls the API over CORS from a
second container; both are wired into the shared `/data/DockerConfigs/docker-compose.yaml`
stack alongside the rest of the homelab, following that file's existing
build-context/container-naming/healthcheck conventions (see the `civicdenovo-*` services).
This website is explicitly not for public use — no auth is added because the ask is a
personal testing tool, not a public-facing surface; it is reachable on the same terms as
every other service already in that compose file (LAN-exposed via published ports, nothing
more).

**Tech Stack:** Python 3.14, FastAPI 0.136, Pydantic 2.13, uvicorn 0.49 (all already present
in the environment — see `api/requirements.txt` pinned versions in Task 6), pytest 9 +
httpx 0.28 for tests (via `fastapi.testclient.TestClient`). Docker: `python:3.12-slim` for
the API image (broadly available; the host's 3.14 is not yet guaranteed to exist as an
official slim image), plain `nginx:alpine` for the static test website — no JS framework,
build step, or bundler, since the site is one page with vanilla `fetch()` calls.

## Global Constraints

- Every extracted/read function must reuse `interchange_models.compute_confidence()` for
  confidence math — never reimplement Beta(α, β) arithmetic (`ARCHITECTURE-Interchange_Core.md`
  §7).
- Tiered search only, never flat (`ARCHITECTURE-Interchange_Core.md` §8). An identifier
  resolves identifier → component → group → members; results are always labeled with a tier,
  never a bare list.
- Interchange codes (`interchange_code`) stay hidden from Public API responses by default —
  only manufacturer identifiers are shown (`ARCHITECTURE-Interchange_Core.md` §2, Layer 3
  visibility rule). No dealer opt-in view exists yet, so the Public API simply never emits
  `interchange_code`.
- No new database engine, no auth, no write endpoints in this plan — those are explicitly
  out of scope for Phase 1 (see §Phases below).
- Follow the existing repo convention: flat modules imported via `sys.path` insertion
  (`Docs/Tools` is not a package), self-tests as `--self-test` CLI flags, `sqlite3.Row`
  row factory throughout.

---

## Phases (roadmap — Phase 1 is fully task-broken-down below; Phases 2-4 are scoping notes
for future plans, not yet bite-sized)

### Phase 1 — Basic Public API (this plan's scope)
Two endpoints, no auth, reading the existing store as-is: `/public/v1/resolve` and
`/public/v1/replacements`. This is the smallest slice that makes the phrase "what fits?"
answerable over HTTP. Tasks 1-6 build the API itself; Tasks 7-12 add logging/CORS, a
personal-use Docker deployment, and a minimal static test website so it can actually be
exercised by hand; Task 13 is the final regression pass.

### Phase 2 — Round out the Public API surface
`/public/v1/components/{id}` (full attribute detail), `/public/v1/search` (free-text across
identifiers/attributes — needs >1 vendor's worth of data to be worth building), `/public/v1/compare`.
Add the `contains` edge tier ("Parts for this unit") once a part family with real
sub-assemblies is resolved (monitor panels are the natural first case per
`ARCHITECTURE-Interchange_Core.md` §5's KIB example).

### Phase 3 — Contributor intake (still no accounts)
A single anonymous submission endpoint (data-plate photo, PDF, or "here's what I installed")
that writes to `observations.py`'s append-only store — this is `PLAN-Staged_Build.md` §6's
"ask once, at the right moment, one tap" and the "empty result is a demand signal" capture,
not the Dealer API's authenticated resource/command model. Empty-result logging (§3 of the
staged-build plan) belongs here too: log the query, don't error.

### Phase 4 — Dealer API, auth, publication workflow
Everything in the API design doc's §5, §6, §9's Dealer half, and the review/publication
lifecycle. Deferred deliberately: `PLAN-Staged_Build.md`'s stage ordering principle is
"don't build for a role that doesn't exist with real demand yet," and there are zero dealer
users today. Building auth/roles/review now would be scope creep ahead of any contributor
existing to use it. Revisit when Phase 3's intake produces enough submissions that manual
review-and-merge (the current de facto workflow: a human reads observations, runs the
resolver, commits) stops scaling.

---

## Phase 1 File Structure

- **Modify:** `Docs/Tools/interchange_store.py` — add `get_component`,
  `get_component_by_identifier`, `get_identifiers_for_component`. These are Repository-layer
  reads; they belong next to the file's existing `get_*` functions, not in a new file.
- **Create:** `api/__init__.py` — empty, marks `api/` as a package.
- **Create:** `api/services.py` — `IdentifierService.resolve()`,
  `ReplacementService.get_replacements()`. The Service Layer named in the API design doc §7.
- **Create:** `api/schemas.py` — Pydantic response models (`ResolveResponse`,
  `ReplacementItem`, `ReplacementsResponse`).
- **Create:** `api/main.py` — FastAPI app, DB connection wiring, the two routes.
- **Create:** `api/requirements.txt` — pinned deps.
- **Create:** `tests/api/__init__.py` — empty.
- **Create:** `tests/api/test_services.py` — service-layer tests against an in-memory DB.
- **Create:** `tests/api/test_main.py` — HTTP-level tests via `TestClient`.
- **Create:** `api/Dockerfile`, `.dockerignore` (repo root) — API container image.
- **Create:** `web/index.html`, `web/app.js`, `web/Dockerfile` — static test lookup website.
- **Modify:** `/data/DockerConfigs/docker-compose.yaml` — add `rvinterchange-api` and
  `rvinterchange-web` services.
- **Modify:** `.gitignore` (repo root) — ignore the local `logs/` directory.

---

## Task 1: Repository reads — `get_component`, `get_component_by_identifier`, `get_identifiers_for_component`

**Files:**
- Modify: `Docs/Tools/interchange_store.py`
- Test: inline `self_test()` in the same file (existing convention — no separate test file
  for this module)

**Interfaces:**
- Produces: `get_component(conn, component_id) -> Component | None`,
  `get_component_by_identifier(conn, ns, value) -> Component | None`,
  `get_identifiers_for_component(conn, component_id) -> list[Identifier]`. These three are
  what `api/services.py` (Tasks 2-3) calls directly — no other repository access is needed
  for Phase 1.

- [ ] **Step 1: Add the three functions**

Add after `insert_identifier` (around line 37) in `Docs/Tools/interchange_store.py`:

```python
def get_component(conn, component_id):
    row = conn.execute(
        "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
    if row is None:
        return None
    return Component(component_id=row["component_id"], part_type_id=row["part_type_id"],
                      interchange_code=row["interchange_code"])


def get_component_by_identifier(conn, ns, value):
    row = conn.execute(
        "SELECT component_id FROM identifiers WHERE ns = ? AND value = ?",
        (ns, value)).fetchone()
    if row is None:
        return None
    return get_component(conn, row["component_id"])


def get_identifiers_for_component(conn, component_id):
    rows = conn.execute(
        "SELECT * FROM identifiers WHERE component_id = ? ORDER BY id",
        (component_id,)).fetchall()
    return [Identifier(component_id=r["component_id"], ns=r["ns"], value=r["value"],
                        visibility=r["visibility"]) for r in rows]
```

`Component` and `Identifier` are already imported at the top of the file from
`interchange_models` — no import changes needed.

- [ ] **Step 2: Add self-test coverage**

In `self_test()`, after the existing `insert_identifier(conn, Identifier("c_test_a",
"suburban", "SW6DE"))` call (around line 252), add:

```python
    fetched_component = get_component(conn, "c_test_a")
    if fetched_component is None or fetched_component.part_type_id != 412:
        failures.append(f"expected c_test_a with part_type_id 412, got {fetched_component}")

    by_identifier = get_component_by_identifier(conn, "suburban", "SW6DE")
    if by_identifier is None or by_identifier.component_id != "c_test_a":
        failures.append(f"expected SW6DE to resolve to c_test_a, got {by_identifier}")

    missing_identifier = get_component_by_identifier(conn, "suburban", "NOPE")
    if missing_identifier is not None:
        failures.append(f"expected None for unknown identifier, got {missing_identifier}")

    idents = get_identifiers_for_component(conn, "c_test_a")
    if len(idents) != 1 or idents[0].value != "SW6DE":
        failures.append(f"expected 1 identifier SW6DE for c_test_a, got {idents}")
```

- [ ] **Step 3: Run the self-test**

Run: `cd Docs/Tools && python3 interchange_store.py --self-test --verbose`
Expected: `PASS: full round trip through every insert/get function` and `self_test: PASS`

- [ ] **Step 4: Commit**

```bash
git add Docs/Tools/interchange_store.py
git commit -m "Add component/identifier reads to interchange_store for the Public API"
```

---

## Task 2: `IdentifierService.resolve()`

**Files:**
- Create: `api/__init__.py` (empty file)
- Create: `api/services.py`
- Test: `tests/api/test_services.py`

**Interfaces:**
- Consumes: `interchange_store.get_component_by_identifier(conn, ns, value)` from Task 1.
- Produces: `IdentifierService.resolve(conn, ns, value) -> dict | None`, returning
  `{"component_id": str, "identifiers": [{"ns": str, "value": str}, ...]}` or `None` if
  unresolved. `ReplacementService` (Task 3) and `api/main.py` (Task 5) both call this.

- [ ] **Step 1: Create `api/__init__.py`**

Empty file.

- [ ] **Step 2: Write the failing test**

Create `tests/api/__init__.py` (empty), then `tests/api/test_services.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from interchange_schema import init_db
from interchange_store import insert_component, insert_identifier
from interchange_models import Component, Identifier

from api.services import IdentifierService


def _seed_basic_component(conn):
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))


def test_resolve_known_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result == {
        "component_id": "c_test_a",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
    }


def test_resolve_unknown_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "NOPE")
    assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_services.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api'` (or `api.services`)

- [ ] **Step 4: Write minimal implementation**

Create `api/services.py`:

```python
"""
api/services.py — Service Layer over the Docs/Tools interchange store, per
Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md §7.

Docs/Tools is not an installable package, so callers of this module must
insert it onto sys.path before importing this file (api/main.py does this
at process start; tests do it per-file — see tests/api/test_services.py).
"""

from interchange_store import get_component_by_identifier, get_identifiers_for_component


class IdentifierService:
    @staticmethod
    def resolve(conn, ns, value):
        component = get_component_by_identifier(conn, ns, value)
        if component is None:
            return None
        identifiers = get_identifiers_for_component(conn, component.component_id)
        return {
            "component_id": component.component_id,
            "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_services.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add api/__init__.py api/services.py tests/api/__init__.py tests/api/test_services.py
git commit -m "Add IdentifierService.resolve for the Public API"
```

---

## Task 3: `ReplacementService.get_replacements()` — tiered search

**Files:**
- Modify: `api/services.py`
- Test: `tests/api/test_services.py`

**Interfaces:**
- Consumes: `interchange_store.get_component`, `get_identifiers_for_component`,
  `get_edges_from`, `get_evidence_for_edge`, `get_caveats_for_edge` (all already exist);
  `interchange_models.compute_confidence` (already exists).
- Produces: `ReplacementService.get_replacements(conn, component_id) -> dict | None`,
  returning `{"source": str, "replacements": [{"part": str, "fit": str, "rank": int,
  "summary": str | None}, ...]}` or `None` if `component_id` doesn't exist. `api/main.py`
  (Task 5) calls this directly.

This implements `ARCHITECTURE-Interchange_Core.md` §8's tiers, restricted to `substitutes`
edges for Phase 1 (the `contains` tier, "Parts for this unit," is Phase 2 — see the Phases
section above):

| Tier | Rule | Public label |
|---|---|---|
| Exact | the resolved component itself | `"Exact Match"` |
| Drop-in (verified) | `certainty >= 8` and `confidence > 0.90` | `"Direct Fit"` |
| Fits with one check | `confidence > 0.70` (and not already Drop-in) | `"Fits With Modification"` |
| below bar | `confidence <= 0.70` or no evidence at all | excluded — not silently shown as a false positive |

- [ ] **Step 1: Write the failing test**

Append to `tests/api/test_services.py`:

```python
from datetime import datetime, timezone

from interchange_store import insert_edge, insert_evidence, insert_caveat
from interchange_models import Edge, RelationshipEvidence, EdgeCaveat

from api.services import ReplacementService


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def test_get_replacements_tiers_by_confidence():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_component(conn, Component("c_test_c", 412, "412-0001-C"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))
    insert_identifier(conn, Identifier("c_test_c", "suburban", "SW12DEL"))

    drop_in_edge = Edge(type="substitutes", from_component_id="c_test_a",
                         to_component_id="c_test_b")
    insert_edge(conn, drop_in_edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=drop_in_edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))

    modified_edge = Edge(type="substitutes", from_component_id="c_test_a",
                          to_component_id="c_test_c")
    insert_edge(conn, modified_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=modified_edge.id, event_type="attribute_prior",
        effect_alpha=3.0, effect_beta=1.0, occurred_at=_now()))
    insert_caveat(conn, EdgeCaveat(edge_id=modified_edge.id, blocking=True,
                                   text="Requires switch kit"))

    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["source"] == "SW6DE"
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2, "summary": None},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "summary": "Requires switch kit"},
    ]


def test_get_replacements_excludes_below_bar_and_unknown_component():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    weak_edge = Edge(type="substitutes", from_component_id="c_test_a",
                      to_component_id="c_test_b")
    insert_edge(conn, weak_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=weak_edge.id, event_type="unknown_incomplete",
        effect_alpha=1.0, effect_beta=1.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
    ]

    assert ReplacementService.get_replacements(conn, "c_does_not_exist") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_services.py -v`
Expected: FAIL — `ReplacementService` does not exist

- [ ] **Step 3: Write minimal implementation**

Append to `api/services.py`:

```python
from interchange_store import (
    get_component, get_edges_from, get_evidence_for_edge, get_caveats_for_edge,
)
from interchange_models import compute_confidence


def _label_for(conn, component_id):
    identifiers = get_identifiers_for_component(conn, component_id)
    return identifiers[0].value if identifiers else component_id


def _tier_for_confidence(confidence):
    if confidence["value"] is None:
        return None
    if confidence["certainty"] >= 8 and confidence["value"] > 0.90:
        return "Direct Fit"
    if confidence["value"] > 0.70:
        return "Fits With Modification"
    return None


class ReplacementService:
    @staticmethod
    def get_replacements(conn, component_id):
        component = get_component(conn, component_id)
        if component is None:
            return None

        source_label = _label_for(conn, component_id)
        replacements = [
            {"part": source_label, "fit": "Exact Match", "rank": 1, "summary": None},
        ]

        rank = 2
        for edge in get_edges_from(conn, component_id, type="substitutes"):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            summary = "; ".join(c.text for c in caveats) if caveats else None
            replacements.append({
                "part": _label_for(conn, edge["to_component_id"]),
                "fit": fit,
                "rank": rank,
                "summary": summary,
            })
            rank += 1

        return {"source": source_label, "replacements": replacements}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_services.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add api/services.py tests/api/test_services.py
git commit -m "Add ReplacementService with tiered confidence-based fit ranking"
```

---

## Task 4: Response schemas

**Files:**
- Create: `api/schemas.py`

**Interfaces:**
- Consumes: nothing (pure Pydantic models).
- Produces: `ResolveResponse`, `ReplacementItem`, `ReplacementsResponse` — used by
  `api/main.py` (Task 5) as route `response_model`s.

- [ ] **Step 1: Write the models**

Create `api/schemas.py`:

```python
"""api/schemas.py — Public API response shapes. Never includes interchange_code
(ARCHITECTURE-Interchange_Core.md §2 visibility rule) or any observation/candidate/review
internals (RV_Interchange_API_Design.md §10, "Hidden from public users")."""

from typing import Optional

from pydantic import BaseModel


class IdentifierOut(BaseModel):
    ns: str
    value: str


class ResolveResponse(BaseModel):
    component_id: str
    identifiers: list[IdentifierOut]


class ReplacementItem(BaseModel):
    part: str
    fit: str
    rank: int
    summary: Optional[str] = None


class ReplacementsResponse(BaseModel):
    source: str
    replacements: list[ReplacementItem]
```

- [ ] **Step 2: Verify import works**

Run: `cd /data/Projects/RVInterchange && python3 -c "from api.schemas import ResolveResponse, ReplacementsResponse; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add api/schemas.py
git commit -m "Add Public API response schemas"
```

---

## Task 5: FastAPI app — `/public/v1/resolve` and `/public/v1/replacements`

**Files:**
- Create: `api/main.py`
- Test: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `IdentifierService.resolve`, `ReplacementService.get_replacements` (Tasks 2-3),
  `ResolveResponse`, `ReplacementsResponse` (Task 4), `interchange_schema.init_db`.
- Produces: a FastAPI `app` object importable as `api.main:app` (used by Task 6's requirements
  file / run instructions, and by any future ASGI deployment).

Endpoints take an explicit `ns` query param alongside `identifier` — per
`ARCHITECTURE-Interchange_Core.md` §3, identifiers are namespaced, so a bare value like
`SW6DEL` is not guaranteed globally unique across vendors. The API design doc's example
(`?identifier=SW6DEL` with no namespace) is simplified for the doc; this plan resolves that
ambiguity explicitly rather than silently guessing a namespace.

- [ ] **Step 1: Write the failing test**

Create `tests/api/test_main.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from fastapi.testclient import TestClient

from interchange_schema import init_db
from interchange_store import insert_component, insert_identifier
from interchange_models import Component, Identifier

import api.main as main_module


@pytest.fixture
def client():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))

    def _get_conn_override():
        return conn

    main_module.app.dependency_overrides[main_module.get_conn] = _get_conn_override
    yield TestClient(main_module.app)
    main_module.app.dependency_overrides.clear()


def test_resolve_endpoint(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "component_id": "c_test_a",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
    }


def test_resolve_endpoint_not_found(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404


def test_replacements_endpoint(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        ],
    }


def test_replacements_endpoint_not_found(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 3: Write minimal implementation**

Create `api/main.py`:

```python
"""
api/main.py — the Public API (Docs/Inital_Design/Stage 2 (Frontend)/
RV_Interchange_API_Design.md §4). Read-only, anonymous, query-oriented.
No Dealer API, no auth, no write endpoints — see this plan's Phases section
for why those are deferred.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Docs" / "Tools"))

from fastapi import Depends, FastAPI, HTTPException
from interchange_schema import init_db

from api.services import IdentifierService, ReplacementService
from api.schemas import ReplacementsResponse, ResolveResponse

DB_PATH = str(Path(__file__).resolve().parent.parent / "Docs" / "Tools" / "components.db")

app = FastAPI(title="RV Interchange Public API", version="1")


def get_conn():
    conn = init_db(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/public/v1/resolve", response_model=ResolveResponse)
def resolve(ns: str, identifier: str, conn=Depends(get_conn)):
    result = IdentifierService.resolve(conn, ns, identifier)
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result


@app.get("/public/v1/replacements", response_model=ReplacementsResponse)
def replacements(ns: str, identifier: str, conn=Depends(get_conn)):
    resolved = IdentifierService.resolve(conn, ns, identifier)
    if resolved is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    result = ReplacementService.get_replacements(conn, resolved["component_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result
```

Note the test fixture overrides `get_conn` via FastAPI's `dependency_overrides` so tests run
against an in-memory DB rather than the real `components.db` file — this is the standard
FastAPI pattern for swapping a `Depends()`-injected resource in tests.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_main.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "Add FastAPI app with resolve and replacements Public API endpoints"
```

---

## Task 6: Pin dependencies and document how to run it

**Files:**
- Create: `api/requirements.txt`
- Modify: `README.md`

**Interfaces:** none — this task only adds packaging/documentation, no new code.

- [ ] **Step 1: Write the requirements file**

Create `api/requirements.txt`:

```text
fastapi==0.136.3
pydantic==2.13.4
uvicorn==0.49.0
```

- [ ] **Step 2: Add a run section to `README.md`**

Read `README.md` first to find a natural insertion point (e.g., after the existing Stage 1
status section), then add:

```markdown
## Running the Public API (Stage 2, Phase 1)

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload
```

Then:

```bash
curl "http://127.0.0.1:8000/public/v1/replacements?ns=suburban&identifier=SW6DE"
```

See `docs/superpowers/plans/2026-08-03-stage2-public-api.md` for scope and the phased plan
beyond this first slice.
```

- [ ] **Step 3: Verify the app actually boots**

Run: `cd /data/Projects/RVInterchange && python3 -m uvicorn api.main:app --port 8001 &`
then: `curl -s http://127.0.0.1:8001/public/v1/resolve?ns=suburban\&identifier=SW6DE`
Expected: either a real JSON result (if `Docs/Tools/components.db` already has SW6DE — it
does, per Stage 1 status) or a clean `{"detail":"identifier not found"}` 404, never a 500.
Then stop the server: `kill %1`

- [ ] **Step 4: Commit**

```bash
git add api/requirements.txt README.md
git commit -m "Document how to run the Public API and pin its dependencies"
```

---

## Task 7: Add logging, CORS, and error handling to the API

**Files:**
- Modify: `api/main.py`

**Interfaces:**
- Produces: a module-level `logger` (`logging.Logger`, name `"rvinterchange.api"`) that
  Task 9's Docker setup relies on writing to a mounted volume; no other task calls it
  directly.

This is personal/testing infrastructure requested alongside the plan, not part of the
original API design doc — logging every request/response and any unhandled exception is
the explicit ask ("will need logging to check for errors"), and CORS is needed because
Task 10's static test website calls this API from a different origin (`http://localhost:8485`
vs `http://localhost:8484`) — without it, browser `fetch()` calls silently fail with an
opaque CORS error that is much harder to debug than the thing this task is for.

- [ ] **Step 1: Add logging setup, request-logging middleware, and a catch-all exception handler**

Modify `api/main.py` — replace the top of the file (imports through `app = FastAPI(...)`)
with:

```python
"""
api/main.py — the Public API (Docs/Inital_Design/Stage 2 (Frontend)/
RV_Interchange_API_Design.md §4). Read-only, anonymous, query-oriented.
No Dealer API, no auth, no write endpoints — see this plan's Phases section
for why those are deferred.
"""

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Docs" / "Tools"))

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from interchange_schema import init_db

from api.services import IdentifierService, ReplacementService
from api.schemas import ReplacementsResponse, ResolveResponse

DB_PATH = str(Path(__file__).resolve().parent.parent / "Docs" / "Tools" / "components.db")

# Defaults to a repo-local `logs/` dir so tests and local `uvicorn api.main:app` runs
# work without root permissions; the Docker image overrides this to /app/logs, a
# mounted volume, via the RVI_LOG_DIR env var (see api/Dockerfile and docker-compose.yaml).
LOG_DIR = Path(os.environ.get(
    "RVI_LOG_DIR", str(Path(__file__).resolve().parent.parent / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("rvinterchange.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_DIR / "api.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())

app = FastAPI(title="RV Interchange Public API", version="1")

# Personal-use-only CORS: the test website (Task 10) is the one and only browser
# caller, always on this fixed local port. Not "*" — see the Docker deployment plan's
# note that this stack is not public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8485", "http://127.0.0.1:8485"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info("%s %s -> %s (%.1fms)",
                request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal error"})
```

Leave the rest of the file (`get_conn`, `resolve`, `replacements`) unchanged below this.

- [ ] **Step 2: Re-run the existing HTTP tests to confirm nothing broke**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_main.py -v`
Expected: 4 passed (same as Task 5 — this task only adds middleware/logging, no behavior
change to the two routes).

- [ ] **Step 3: Add a test for the new error-logging path**

Append to `tests/api/test_main.py`:

```python
def test_unhandled_error_is_logged_and_returns_500(client, caplog):
    import api.main as main_module

    def _boom(conn, ns, identifier):
        raise RuntimeError("simulated failure")

    original = main_module.IdentifierService.resolve
    main_module.IdentifierService.resolve = staticmethod(_boom)
    try:
        with caplog.at_level("ERROR", logger="rvinterchange.api"):
            response = client.get(
                "/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
        assert response.status_code == 500
        assert response.json() == {"detail": "internal error"}
        assert any("Unhandled exception" in record.message for record in caplog.records)
    finally:
        main_module.IdentifierService.resolve = original
```

- [ ] **Step 4: Run the new test**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/api/test_main.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "Add request logging, CORS, and unhandled-error handling to the API"
```

---

## Task 8: API Dockerfile and build-context hygiene

**Files:**
- Create: `api/Dockerfile`
- Create: `.dockerignore` (repo root)

**Interfaces:** none — packaging only.

The image bakes in `api/` (application code, rebuilt on change) but does **not** bake in
`Docs/Tools` — that directory is bind-mounted at runtime (Task 11's compose entry) because
it is the live, host-edited data/tooling directory (parser, resolver, `components.db`),
not static app code. The canonical rebuild command updates `components.db` there
atomically after validation, so rebuilding the image every time an observation gets
resolved would be backwards.

- [ ] **Step 1: Add `.dockerignore` at the repo root**

Create `/data/Projects/RVInterchange/.dockerignore`:

```text
.git
.worktrees
docs/
Docs/Data
Docs/Inital_Design
*.pdf
__pycache__
*.pyc
logs/
```

This keeps the build context small — `Docs/Data` alone holds multi-megabyte PDFs that the
API image never needs.

- [ ] **Step 2: Write the Dockerfile**

Create `api/Dockerfile`:

```dockerfile
# Build context is the repo root (see docker-compose.yaml's `build.context`).
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

COPY api /app/api

EXPOSE 8484

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8484"]
```

- [ ] **Step 3: Build the image locally to verify it builds**

Run: `cd /data/Projects/RVInterchange && docker build -f api/Dockerfile -t rvinterchange-api:latest .`
Expected: build completes with no errors.

- [ ] **Step 4: Commit**

```bash
git add api/Dockerfile .dockerignore
git commit -m "Add API Dockerfile and dockerignore"
```

---

## Task 9: Static test website — lookup form

**Files:**
- Create: `web/index.html`
- Create: `web/app.js`

**Interfaces:**
- Consumes: `GET /public/v1/resolve` and `GET /public/v1/replacements` (Task 5/7a) over
  HTTP, hardcoded to `http://localhost:8484` (this is a personal testing tool on one
  machine — no environment-based API URL config needed).

This is explicitly a testing tool, not a production frontend: one page, a namespace
dropdown (`ns`), an identifier text input, a submit button, and a results area that prints
whatever the API returned — including the raw HTTP status on failure, since the point is
to see errors, not hide them.

- [ ] **Step 1: Write the HTML**

Create `web/index.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Lookup (test)</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
    label { display: block; margin-top: 1rem; font-weight: bold; }
    input, select { font-size: 1rem; padding: 0.4rem; width: 100%; box-sizing: border-box; }
    button { margin-top: 1rem; font-size: 1rem; padding: 0.5rem 1rem; }
    pre { background: #f2f2f2; padding: 1rem; overflow-x: auto; white-space: pre-wrap; }
    .error { color: #b00020; font-weight: bold; }
  </style>
</head>
<body>
  <h1>RV Interchange — Lookup (test tool, not public)</h1>

  <label for="ns">Namespace</label>
  <select id="ns">
    <option value="suburban">suburban</option>
    <option value="coleman">coleman</option>
    <option value="icm">icm</option>
  </select>

  <label for="identifier">Identifier</label>
  <input id="identifier" type="text" placeholder="e.g. SW6DE" value="SW6DE">

  <button id="lookup">Look up replacements</button>

  <h2>Result</h2>
  <pre id="result">(nothing yet)</pre>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write the JS**

Create `web/app.js`:

```javascript
const API_BASE = "http://localhost:8484";

document.getElementById("lookup").addEventListener("click", async () => {
  const ns = document.getElementById("ns").value;
  const identifier = document.getElementById("identifier").value.trim();
  const resultEl = document.getElementById("result");
  resultEl.className = "";
  resultEl.textContent = "Loading...";

  const url = `${API_BASE}/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;

  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      resultEl.className = "error";
      resultEl.textContent = `HTTP ${response.status}\n${JSON.stringify(body, null, 2)}`;
      return;
    }
    resultEl.textContent = JSON.stringify(body, null, 2);
  } catch (err) {
    resultEl.className = "error";
    resultEl.textContent = `Request failed: ${err.message}\n(Is the API reachable at ${API_BASE}? Check the api container's logs.)`;
  }
});
```

- [ ] **Step 3: Verify it works against the API running locally (no Docker yet)**

Run the API: `cd /data/Projects/RVInterchange && python3 -m uvicorn api.main:app --port 8484 &`
Then serve the static files: `cd web && python3 -m http.server 8485 &`
Open `http://localhost:8485` in a browser, click "Look up replacements" with the default
`suburban` / `SW6DE` values.
Expected: the result box shows a JSON `replacements` array (per Stage 1 status, SW6DE
already resolves in `components.db`), not a CORS error and not a network error.
Stop both background processes: `kill %1 %2`

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/app.js
git commit -m "Add static test lookup website"
```

---

## Task 10: Web Dockerfile

**Files:**
- Create: `web/Dockerfile`

**Interfaces:** none — packaging only.

- [ ] **Step 1: Write the Dockerfile**

Create `web/Dockerfile`:

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
EXPOSE 80
```

- [ ] **Step 2: Build the image locally to verify it builds**

Run: `cd /data/Projects/RVInterchange/web && docker build -t rvinterchange-web:latest .`
Expected: build completes with no errors.

- [ ] **Step 3: Commit**

```bash
git add web/Dockerfile
git commit -m "Add web Dockerfile"
```

---

## Task 11: Wire both containers into the shared Docker stack

**Files:**
- Modify: `/data/DockerConfigs/docker-compose.yaml`
- Modify: `.gitignore` (repo root, add `/logs/`)

**Interfaces:** none — deployment config only.

Ports `8484` and `8485` are unused in the current compose file (checked against every
`"HOST:CONTAINER"` mapping already present). Named `rvinterchange-api` /
`rvinterchange-web` to match the existing container-naming convention (`civicdenovo-backend`
/ `civicdenovo-frontend`).

- [ ] **Step 1: Add `/logs/` to `.gitignore`**

Add to `/data/Projects/RVInterchange/.gitignore` (near the existing `*.log` line):

```text
/logs/
```

- [ ] **Step 2: Add the two services to the shared compose file**

In `/data/DockerConfigs/docker-compose.yaml`, insert after the `civicdenovo-frontend` block
(before the parked "SeaQuacks" comment section) — matching that section's `# ── Name ──`
header convention:

```yaml
  # ── RV Interchange (personal test tool, not public) ─────────────────────

  rvinterchange-api:
    container_name: rvinterchange-api
    build:
      context: /data/Projects/RVInterchange
      dockerfile: api/Dockerfile
    image: rvinterchange-api:latest
    restart: unless-stopped
    ports:
      - "8484:8484"
    environment:
      - TZ=America/New_York
      - RVI_LOG_DIR=/app/logs
    volumes:
      - /data/Projects/RVInterchange/Docs/Tools:/app/Docs/Tools
      - /data/DockerConfigs/RVInterchange/logs:/app/logs
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8484/docs')"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3

  rvinterchange-web:
    container_name: rvinterchange-web
    build:
      context: /data/Projects/RVInterchange/web
      dockerfile: Dockerfile
    image: rvinterchange-web:latest
    restart: unless-stopped
    ports:
      - "8485:80"
    depends_on:
      - rvinterchange-api
```

The `Docs/Tools` bind mount is why the API container always sees the live
`components.db` and the current parser/resolver code without a rebuild — this matches how
every other tool in this project already runs directly against the host filesystem.

`/data/DockerConfigs/RVInterchange/logs` needs to exist before `docker compose up` (Docker
will auto-create it as root-owned if missing, which then blocks the container's non-root
default user from writing — create it explicitly first).

- [ ] **Step 3: Create the log directory ahead of time**

Run: `mkdir -p /data/DockerConfigs/RVInterchange/logs`

- [ ] **Step 4: Commit the compose and gitignore changes**

The compose file lives outside this repo (`/data/DockerConfigs`), so this is two separate
commits in two separate repos if `/data/DockerConfigs` is its own git repo — check with
`git -C /data/DockerConfigs status` first and follow whatever that repo's convention is.

```bash
cd /data/Projects/RVInterchange
git add .gitignore
git commit -m "Ignore the local logs directory"
```

```bash
cd /data/DockerConfigs
git status
# If tracked, commit the compose change there following this repo's own commit conventions.
```

---

## Task 12: End-to-end Docker verification

**Files:** none created or modified — verification only.

- [ ] **Step 1: Bring the two new services up**

Run: `cd /data/DockerConfigs && docker compose up -d rvinterchange-api rvinterchange-web`
Expected: both containers report `Up` in `docker compose ps`.

- [ ] **Step 2: Confirm the API is reachable and logging**

Run: `curl -s "http://localhost:8484/public/v1/replacements?ns=suburban&identifier=SW6DE"`
Expected: a JSON response (not connection refused, not 500).

Run: `tail -5 /data/DockerConfigs/RVInterchange/logs/api.log`
Expected: a log line for the request just made, e.g. `GET /public/v1/replacements ->
200 (…ms)`.

- [ ] **Step 3: Confirm the website works end-to-end through Docker**

Open `http://localhost:8485` in a browser (not `127.0.0.1` — must match one of the two
allowed CORS origins from Task 7a), submit the default lookup.
Expected: same JSON result as Step 2, rendered in the page's result box.

- [ ] **Step 4: Confirm errors are visible, not swallowed**

Run: `curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8484/public/v1/replacements?ns=suburban&identifier=DOES_NOT_EXIST"`
Expected: `404`, and a corresponding line in `api.log`.

Then in the browser, look up an identifier that doesn't exist and confirm the page's
result box shows `HTTP 404` with the response body — not a blank page or a silent failure.

- [ ] **Step 5: Tear down if this was just a verification pass, or leave running**

Run: `cd /data/DockerConfigs && docker compose stop rvinterchange-api rvinterchange-web`
(leave running instead if this is meant to stay up as a standing personal tool — that's a
judgment call for whoever runs this step, not a fixed instruction).

---

## Task 13: Full-suite regression check

**Files:** none created or modified — verification only.

- [ ] **Step 1: Run every existing self-test plus the new pytest suite**

```bash
cd /data/Projects/RVInterchange/Docs/Tools
python3 resolver.py --self-test
python3 suburban_parser.py --self-test
python3 interchange_schema.py --self-test
python3 interchange_models.py --self-test
python3 interchange_store.py --self-test
python3 edge_resolver.py --self-test
python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml
cd /data/Projects/RVInterchange
python3 -m pytest tests/api/ -v
```

Expected: every self-test prints `PASS`, `--check-fixture` reports 0 mismatches, and all
`tests/api/` tests pass (9 total: 4 from Task 2-3's services tests, 5 from Task 5/7's
main-app tests). This is the same full verification sequence the Coleman-Mach memory notes
as required before every commit in this project (`interchange_store.py`'s self-test plus
the four sibling modules plus the fixture check) — Task 1 modified `interchange_store.py`,
so re-running all of them, not just the new one, is the correct bar.

- [ ] **Step 2: If anything fails, stop and fix before proceeding**

Do not commit further work in this plan on top of a failing self-test — this project's
convention (see `coleman_mach_7330_status` memory) is zero-mismatch before every commit.

---

## Self-Review Notes

- **Spec coverage:** API design doc §3 (layered architecture) → Task 1 (Repository) + Task 2-3
  (Service) + Task 5 (Public API). §4 (Public API characteristics/endpoints) → Task 5,
  scoped to the two endpoints the doc itself uses as its worked example (§4's "Example
  Request"). §10 (information exposure) → Task 4's schema docstring + the namespaced-identifier
  decision in Task 5. §5/§6/§9 Dealer half, §11 subscriptions → explicitly deferred to Phase 4,
  not silently dropped. `ARCHITECTURE-Interchange_Core.md` §7 (confidence) → Task 3 reuses
  `compute_confidence` verbatim. §8 (tiered search) → Task 3's tier table, `contains` tier
  deferred to Phase 2 with a named reason (needs a resolved sub-assembly family first).
- **Placeholder scan:** no TBD/TODO markers; every code step is complete, runnable code.
- **Type consistency:** `ReplacementService.get_replacements` and `IdentifierService.resolve`
  signatures match between their Task 2/3 definitions and Task 5's call sites. Response dict
  shapes match the Pydantic models in Task 4 field-for-field (`part`/`fit`/`rank`/`summary`,
  `component_id`/`identifiers`, `ns`/`value`).
- **User request coverage (Docker/website addendum):** "basic website that can access the
  API" → Task 9 (static lookup page). "Simple Docker stack to fit into the current stack" →
  Task 8/10/11, following `docker-compose.yaml`'s existing patterns exactly (build context +
  Dockerfile path, `container_name`, `image` tag, `restart: unless-stopped`, healthcheck
  style copied from `aft`/`civicdenovo-db`). "This will not be for the public. Me only." →
  no auth added (would be scope creep for a personal tool), called out explicitly in the
  Architecture section and in the CORS comment in Task 7 so a future reader doesn't mistake
  the absence of auth for an oversight. "Simple lookup options, that then display the
  results" → Task 9's one-page form. "Mostly for testing" → hardcoded `localhost` URLs, no
  environment-based config, matches the stack's own single-host deployment model. "Will
  need logging to check for errors" → Task 7's request-logging middleware and unhandled-
  exception handler, both verified end-to-end in Task 12 (confirms a log line actually
  appears for both a successful and a 404 request) rather than just asserted to exist.
