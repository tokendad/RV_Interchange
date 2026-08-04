# Stage 2 Backend Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a search endpoint and close the four items deferred from the 2026-08-03
Stage 2 Public API ship, so the backend can answer "what fits?" without the caller
already knowing the exact namespace + identifier, and so `supersedes` edges (the
Coleman-Mach dataset's strongest use case) are actually visible via the API.

**Architecture:** No new services or files beyond what already exists — this extends
`api/services.py` (business logic), `api/schemas.py` (response shapes), `api/main.py`
(routes + DB connection handling), and `Docs/Tools/interchange_store.py` (a new
store-layer query function). Everything stays inside the existing Public
API/Service/Repository layering from `RV_Interchange_API_Design.md` §7-8.

**Tech Stack:** Python 3, FastAPI, Pydantic, sqlite3 (stdlib), pytest. No new
dependencies.

## Global Constraints

- Follow the existing test-framework split in this repo exactly: `Docs/Tools/*.py` use
  the hand-rolled `self_test(verbose=False)` / `--self-test` CLI convention (see
  `interchange_store.py`'s existing `self_test` function) — there is no pytest coverage
  for that layer. `api/*.py` use pytest under `tests/api/`.
- The Public API never returns `interchange_code` or any observation/candidate/review
  internals (`api/schemas.py`'s module docstring, `RV_Interchange_API_Design.md` §10).
  None of these tasks add any such field — confirm this stays true when writing new
  schema classes.
- No new third-party dependencies. `sqlite3` and `logging.handlers` are stdlib.
- Every task must leave `python3 -m pytest tests/ -q` fully green and
  `python3 Docs/Tools/interchange_store.py --self-test --verbose` printing `PASS`
  before it's considered done.

---

### Task 1: `search_identifiers` store function

**Files:**
- Modify: `Docs/Tools/interchange_store.py`

**Interfaces:**
- Produces: `search_identifiers(conn, query, limit=20) -> list[str]` — ranked, deduped
  `component_id` values whose identifiers' `value` contains `query`
  (case-insensitive), exact matches first, ties broken by shorter/then alphabetical
  `value`. Empty `query` returns `[]`. Later tasks (Task 2) call this directly.

- [ ] **Step 1: Add the function**

Add this function to `Docs/Tools/interchange_store.py`, directly below
`get_identifiers_for_component` (around line 63):

```python
def search_identifiers(conn, query, limit=20):
    """Ranked, deduped component_ids whose identifiers.value matches `query`.

    Exact matches (case-insensitive) rank first; ties break by shorter value,
    then alphabetically. A component can carry several matching identifiers
    across namespaces — it appears once in the result, not once per match.
    """
    if not query:
        return []
    like_pattern = f"%{query}%"
    rows = conn.execute(
        "SELECT component_id, value FROM identifiers "
        "WHERE value LIKE ? COLLATE NOCASE "
        "ORDER BY (LOWER(value) = LOWER(?)) DESC, LENGTH(value), value",
        (like_pattern, query)).fetchall()
    component_ids = []
    seen = set()
    for row in rows:
        if row["component_id"] in seen:
            continue
        seen.add(row["component_id"])
        component_ids.append(row["component_id"])
        if len(component_ids) >= limit:
            break
    return component_ids
```

- [ ] **Step 2: Add self_test coverage**

In `Docs/Tools/interchange_store.py`, inside `self_test()`, insert this block right
before the existing `if failures:` line near the end of the function (this runs after
`c_test_a` has already been given identifier `"suburban"/"SW6DE"` earlier in the same
function — check that assignment is still there before adding a second identifier for
`c_test_b`):

```python
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    exact_match = search_identifiers(conn, "SW6DE")
    if exact_match != ["c_test_a"]:
        failures.append(f"expected exact match search to return only c_test_a, got {exact_match}")

    substring_match = search_identifiers(conn, "SW")
    if substring_match != ["c_test_a", "c_test_b"]:
        failures.append(
            f"expected substring search ranked shortest-value-first, got {substring_match}")

    limited = search_identifiers(conn, "SW", limit=1)
    if limited != ["c_test_a"]:
        failures.append(f"expected limit=1 to return only the best match, got {limited}")

    no_match = search_identifiers(conn, "NOPE")
    if no_match != []:
        failures.append(f"expected no match for unknown query, got {no_match}")

    empty_query = search_identifiers(conn, "")
    if empty_query != []:
        failures.append(f"expected empty query to return [], got {empty_query}")
```

- [ ] **Step 3: Run self_test to verify it passes**

Run: `python3 Docs/Tools/interchange_store.py --self-test --verbose`
Expected: `PASS: full round trip through every insert/get function` then `self_test: PASS`
(exit code 0). If any of the four new checks fail, the printed `FAIL: ...` line tells
you which assertion and what it actually returned — fix `search_identifiers` (not the
test) unless you find the expected values above are wrong.

- [ ] **Step 4: Commit**

```bash
git add Docs/Tools/interchange_store.py
git commit -m "feat: add search_identifiers store-layer query function"
```

---

### Task 2: `/public/v1/search` endpoint

**Files:**
- Modify: `api/schemas.py`
- Modify: `api/services.py`
- Modify: `api/main.py`
- Modify: `tests/api/test_services.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `search_identifiers(conn, query, limit=20) -> list[str]` from Task 1.
  `get_identifiers_for_component(conn, component_id) -> list[Identifier]` (already
  exists, already imported in `api/services.py`).
- Produces: `SearchService.search(conn, query, limit=20) -> dict` with shape
  `{"query": str, "results": [{"component_id": str, "label": str, "identifiers": [{"ns": str, "value": str}, ...]}, ...]}`.
  `SearchResponse` / `SearchResultItem` Pydantic models in `api/schemas.py`. Route
  `GET /public/v1/search?q=<query>&limit=<n>` in `api/main.py`.

- [ ] **Step 1: Write the failing service-layer tests**

Add to `tests/api/test_services.py` (append at the end of the file):

```python
from api.services import SearchService


def test_search_ranks_exact_match_first():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    result = SearchService.search(conn, "SW")

    assert result["query"] == "SW"
    assert [r["component_id"] for r in result["results"]] == ["c_test_a", "c_test_b"]
    assert result["results"][0]["label"] == "SW6DE"
    assert result["results"][0]["identifiers"] == [{"ns": "suburban", "value": "SW6DE"}]


def test_search_no_match_returns_empty_results():
    conn = init_db(":memory:")
    result = SearchService.search(conn, "NOPE")
    assert result == {"query": "NOPE", "results": []}


def test_search_respects_limit():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    result = SearchService.search(conn, "SW", limit=1)
    assert [r["component_id"] for r in result["results"]] == ["c_test_a"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/api/test_services.py -k search -v`
Expected: FAIL with `ImportError: cannot import name 'SearchService'`

- [ ] **Step 3: Implement `SearchService`**

In `api/services.py`, add this import alongside the existing top-of-file import (do
not touch the mid-file imports yet — that's Task 3):

```python
from interchange_store import (
    get_component_by_identifier, get_identifiers_for_component, search_identifiers,
)
```

(Replace the existing single-line `from interchange_store import
get_component_by_identifier, get_identifiers_for_component` with the block above.)

Then add this class anywhere after `IdentifierService` (e.g. right below it):

```python
class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        component_ids = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id in component_ids:
            identifiers = get_identifiers_for_component(conn, component_id)
            results.append({
                "component_id": component_id,
                "label": identifiers[0].value if identifiers else component_id,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
            })
        return {"query": query, "results": results}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/api/test_services.py -k search -v`
Expected: 3 passed

- [ ] **Step 5: Add schemas**

In `api/schemas.py`, add these classes after `IdentifierOut`:

```python
class SearchResultItem(BaseModel):
    component_id: str
    label: str
    identifiers: list[IdentifierOut]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
```

- [ ] **Step 6: Write the failing route test**

Add to `tests/api/test_main.py` (append at the end of the file):

```python
def test_search_endpoint(client):
    response = client.get("/public/v1/search", params={"q": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "query": "SW6DE",
        "results": [
            {"component_id": "c_test_a", "label": "SW6DE",
             "identifiers": [{"ns": "suburban", "value": "SW6DE"}]},
        ],
    }


def test_search_endpoint_no_match_returns_200_with_empty_results(client):
    response = client.get("/public/v1/search", params={"q": "NOPE"})
    assert response.status_code == 200
    assert response.json() == {"query": "NOPE", "results": []}
```

- [ ] **Step 7: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_main.py -k search -v`
Expected: FAIL with a 404/500 (route doesn't exist yet)

- [ ] **Step 8: Add the route**

In `api/main.py`, change the import line:

```python
from api.services import IdentifierService, ReplacementService
from api.schemas import ReplacementsResponse, ResolveResponse
```

to:

```python
from api.services import IdentifierService, ReplacementService, SearchService
from api.schemas import ReplacementsResponse, ResolveResponse, SearchResponse
```

Then add this route after the existing `replacements` route:

```python
@app.get("/public/v1/search", response_model=SearchResponse)
def search(q: str, limit: int = 20, conn=Depends(get_conn)):
    return SearchService.search(conn, q, limit=limit)
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `python3 -m pytest tests/api/test_main.py -k search -v`
Expected: 2 passed

- [ ] **Step 10: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass, no regressions

- [ ] **Step 11: Commit**

```bash
git add api/schemas.py api/services.py api/main.py tests/api/test_services.py tests/api/test_main.py
git commit -m "feat: add /public/v1/search endpoint"
```

---

### Task 3: Namespace-correct labels + surface `supersedes` edges

**Files:**
- Modify: `api/services.py`
- Modify: `api/schemas.py`
- Modify: `api/main.py`
- Modify: `tests/api/test_services.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Consumes: `get_supersession_detail(conn, edge_id) -> EdgeSupersessionDetail | None`
  (already exists in `interchange_store.py`, not yet imported into `api/services.py`).
  `get_edges_from(conn, component_id, type=...)`, `compute_confidence(evidence_rows)`
  (already used by this file).
- Produces: `_label_for(conn, component_id, ns=None) -> str` (signature changes — now
  takes an optional `ns`). `ReplacementService.get_replacements(conn, component_id,
  ns=None) -> dict` (signature changes — now takes an optional `ns`; return dict gains a
  `"supersessions"` key: `list[{"part": str, "note": str | None}]`).

This task also consolidates `api/services.py`'s two scattered mid-file import blocks
into the single top-of-file import block, since this task is already editing every
function those imports serve.

- [ ] **Step 1: Write the failing tests**

Add to `tests/api/test_services.py` (append at the end; note the new imports needed at
the top of the file — add `insert_supersession_detail` to the existing `from
interchange_store import insert_edge, insert_evidence, insert_caveat` line, making it
`from interchange_store import insert_edge, insert_evidence, insert_caveat,
insert_supersession_detail`, and add `EdgeSupersessionDetail` to the existing
`from interchange_models import Edge, RelationshipEvidence, EdgeCaveat` line):

```python
def test_label_for_prefers_querying_namespace():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_a", "icm", "PCB1060"))

    assert ReplacementService.get_replacements(conn, "c_test_a", ns="icm")["source"] == "PCB1060"
    assert ReplacementService.get_replacements(conn, "c_test_a", ns="coleman")["source"] == "7330G3351"
    # No ns given: falls back to the first identifier (insertion order).
    assert ReplacementService.get_replacements(conn, "c_test_a")["source"] == "7330G3351"


def test_get_replacements_includes_supersessions():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_b", "coleman", "9420-351"))

    edge = Edge(type="supersedes", from_component_id="c_test_a", to_component_id="c_test_b")
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id, note="Coleman catalog names 9420-351 as the replacement"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="manufacturer_assertion", effect_alpha=2.0,
        effect_beta=0.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["supersessions"] == [
        {"part": "9420-351", "note": "Coleman catalog names 9420-351 as the replacement"},
    ]


def test_get_replacements_omits_supersession_with_no_evidence():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_b", "coleman", "9420-351"))

    edge = Edge(type="supersedes", from_component_id="c_test_a", to_component_id="c_test_b")
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(edge_id=edge.id, note="no evidence yet"))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["supersessions"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/api/test_services.py -k "label_for or supersession" -v`
Expected: FAIL — `test_label_for_prefers_querying_namespace` fails because
`get_replacements()` doesn't accept `ns=`; the two supersession tests fail on
`KeyError: 'supersessions'`.

- [ ] **Step 3: Rewrite `api/services.py`**

Replace the entire contents of `api/services.py` with:

```python
"""
api/services.py — Service Layer over the Docs/Tools interchange store, per
Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md §7.

Docs/Tools is not an installable package, so callers of this module must
insert it onto sys.path before importing this file (api/main.py does this
at process start; tests do it per-file — see tests/api/test_services.py).
"""

from interchange_store import (
    get_component, get_component_by_identifier, get_edges_from,
    get_caveats_for_edge, get_evidence_for_edge, get_identifiers_for_component,
    get_supersession_detail, search_identifiers,
)
from interchange_models import compute_confidence


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


class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        component_ids = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id in component_ids:
            identifiers = get_identifiers_for_component(conn, component_id)
            results.append({
                "component_id": component_id,
                "label": identifiers[0].value if identifiers else component_id,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
            })
        return {"query": query, "results": results}


def _label_for(conn, component_id, ns=None):
    identifiers = get_identifiers_for_component(conn, component_id)
    if not identifiers:
        return component_id
    if ns is not None:
        for identifier in identifiers:
            if identifier.ns == ns:
                return identifier.value
    return identifiers[0].value


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
    def get_replacements(conn, component_id, ns=None):
        component = get_component(conn, component_id)
        if component is None:
            return None

        source_label = _label_for(conn, component_id, ns)
        replacements = [
            {"part": source_label, "fit": "Exact Match", "rank": 1, "summary": None},
        ]

        _TIER_PRIORITY = {"Direct Fit": 0, "Fits With Modification": 1}

        candidates = []
        for edge in get_edges_from(conn, component_id, type="substitutes"):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            summary = "; ".join(c.text for c in caveats) if caveats else None
            candidates.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "fit": fit,
                "summary": summary,
                "_confidence_value": confidence["value"],
            })

        candidates.sort(
            key=lambda c: (_TIER_PRIORITY[c["fit"]], -c["_confidence_value"])
        )

        rank = 2
        for candidate in candidates:
            del candidate["_confidence_value"]
            candidate["rank"] = rank
            replacements.append(candidate)
            rank += 1

        supersessions = []
        for edge in get_edges_from(conn, component_id, type="supersedes"):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            if confidence["value"] is None:
                continue
            detail = get_supersession_detail(conn, edge["id"])
            supersessions.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "note": detail.note if detail else None,
            })

        return {
            "source": source_label,
            "replacements": replacements,
            "supersessions": supersessions,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/api/test_services.py -v`
Expected: all tests in the file pass, including the three new ones and every
pre-existing `test_get_replacements_*` test (they only assert on `result["source"]`
and `result["replacements"]`, not full-dict equality, so the new `"supersessions"` key
doesn't break them).

- [ ] **Step 5: Update schemas**

In `api/schemas.py`, add a new class after `ReplacementItem` and update
`ReplacementsResponse`:

```python
class SupersessionItem(BaseModel):
    part: str
    note: Optional[str] = None


class ReplacementsResponse(BaseModel):
    source: str
    replacements: list[ReplacementItem]
    supersessions: list[SupersessionItem] = []
```

- [ ] **Step 6: Thread `ns` through the route and update the route test**

In `api/main.py`, change the `replacements` route to pass `ns` through:

```python
@app.get("/public/v1/replacements", response_model=ReplacementsResponse)
def replacements(ns: str, identifier: str, conn=Depends(get_conn)):
    resolved = IdentifierService.resolve(conn, ns, identifier)
    if resolved is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    result = ReplacementService.get_replacements(conn, resolved["component_id"], ns)
    if result is None:
        raise HTTPException(status_code=404, detail="identifier not found")
    return result
```

In `tests/api/test_main.py`, update `test_replacements_endpoint`'s expected JSON to
include the new key:

```python
def test_replacements_endpoint(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        ],
        "supersessions": [],
    }
```

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass, no regressions

- [ ] **Step 8: Commit**

```bash
git add api/services.py api/schemas.py api/main.py tests/api/test_services.py tests/api/test_main.py
git commit -m "feat: namespace-correct labels and surface supersedes edges in replacements"
```

---

### Task 4: Read-only DB connections for the request path

**Files:**
- Modify: `api/main.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Produces: `_readonly_connection(path) -> sqlite3.Connection` (module-level helper in
  `api/main.py`). `get_conn()` now yields a read-only connection instead of calling
  `init_db()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/api/test_main.py`. First add `import sqlite3` near the top of the file
(alongside the existing `import pytest`), then append these two tests at the end of
the file:

```python
def test_readonly_connection_rejects_writes(tmp_path):
    db_path = str(tmp_path / "ro_test.db")
    init_db(db_path).close()

    conn = main_module._readonly_connection(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO components (component_id, part_type_id, created_at) "
                "VALUES ('x', 1, 'now')")
    finally:
        conn.close()


def test_get_conn_yields_working_readonly_connection(tmp_path, monkeypatch):
    db_path = str(tmp_path / "get_conn_test.db")
    seed_conn = init_db(db_path)
    insert_component(seed_conn, Component("c_test_ro", 412, "412-0001-A"))
    seed_conn.close()

    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    conn = next(main_module.get_conn())
    try:
        row = conn.execute(
            "SELECT component_id FROM components WHERE component_id = ?",
            ("c_test_ro",)).fetchone()
        assert row["component_id"] == "c_test_ro"
    finally:
        conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/api/test_main.py -k readonly -v`
Expected: FAIL — `AttributeError: module 'api.main' has no attribute '_readonly_connection'`

- [ ] **Step 3: Implement the read-only connection**

In `api/main.py`, add `import sqlite3` to the imports at the top of the file. Then
replace the existing `get_conn()` function:

```python
def get_conn():
    conn = init_db(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

with:

```python
def _readonly_connection(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_conn():
    conn = _readonly_connection(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

`init_db()` (still imported from `interchange_schema`) is no longer called by the
request path at all — it remains used only by `edge_resolver.py --build` (unaffected
by this change) and by the tests, which build their own `:memory:`/temp-file databases
before overriding or monkeypatching this function.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/api/test_main.py -v`
Expected: all tests pass, including the two new ones. Note that every other existing
test in this file uses the `client` fixture, which overrides
`main_module.app.dependency_overrides[main_module.get_conn]` directly and therefore
never actually calls `_readonly_connection` — they're unaffected by this change.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass, no regressions

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "feat: use read-only sqlite connections for the API request path"
```

---

### Task 5: Log rotation for `api.log`

**Files:**
- Modify: `api/main.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Produces: `logger` (module-level in `api/main.py`) now has a
  `logging.handlers.RotatingFileHandler` instead of a plain `logging.FileHandler`.

- [ ] **Step 1: Write the failing test**

Add to `tests/api/test_main.py`. Add `from logging.handlers import
RotatingFileHandler` to the imports, then append:

```python
def test_api_log_uses_rotating_file_handler():
    rotating_handlers = [
        h for h in main_module.logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) == 1
    assert rotating_handlers[0].maxBytes == 1_000_000
    assert rotating_handlers[0].backupCount == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/api/test_main.py -k rotating -v`
Expected: FAIL — `assert 0 == 1` (no `RotatingFileHandler` configured yet)

- [ ] **Step 3: Switch to `RotatingFileHandler`**

In `api/main.py`, add this import near the top:

```python
from logging.handlers import RotatingFileHandler
```

Then replace:

```python
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_DIR / "api.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())
```

with:

```python
if not logger.handlers:
    file_handler = RotatingFileHandler(
        LOG_DIR / "api.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/api/test_main.py -k rotating -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass, no regressions

- [ ] **Step 6: Also verify the store-layer self_test is still clean**

Run: `python3 Docs/Tools/interchange_store.py --self-test --verbose`
Expected: `self_test: PASS`

- [ ] **Step 7: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "feat: rotate api.log instead of letting it grow unbounded"
```

---

## Definition of done

- [ ] `GET /public/v1/search?q=...` returns ranked, deduped results; empty results is a
  200, not a 404.
- [ ] `GET /public/v1/replacements` no longer echoes a wrong-namespace label for
  multi-namespace components.
- [ ] `GET /public/v1/replacements` includes a `supersessions` field surfacing
  `supersedes` edges with evidence.
- [ ] The API request path never runs schema DDL or opens a writable connection.
- [ ] `api.log` rotates instead of growing unbounded.
- [ ] `python3 -m pytest tests/ -q` and
  `python3 Docs/Tools/interchange_store.py --self-test --verbose` are both green.
- [ ] `/public/v1/compare`, `/public/v1/interchange/{code}`, any frontend work, and any
  public-deployment changes remain explicitly out of scope (separate future phases).
