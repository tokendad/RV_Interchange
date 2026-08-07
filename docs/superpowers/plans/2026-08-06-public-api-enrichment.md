# Public API Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `/public/v1/search`, `/public/v1/resolve`, and `/public/v1/replacements` with manufacturer display name, part-type display name, component attributes, required parts, and structured caveats — per `docs/superpowers/specs/2026-08-06-public-api-enrichment-design.md`.

**Architecture:** Two new canonical registries (`Docs/Tools/part_types.py`, `Docs/Tools/manufacturers.py`) mirroring the existing `edge_types.py` single-source-of-truth pattern. `interchange_schema.py` gains two DB tables seeded from those registries inside `init_db`. `api/services.py` reads the registries directly (not through the DB) to enrich responses; two required store helpers (`get_component_attributes`, `get_required_parts_for_edge`) already exist and just need wiring in. `api/schemas.py` gains new response models; `ReplacementItem.summary` (a flattened string) is replaced by structured `caveats`. `web/app.js` is updated to match the new contract — it is the only caller of this API today.

**Tech Stack:** Python 3, FastAPI, Pydantic, sqlite3, pytest, vanilla JS (no build step).

## Global Constraints

- Never expose `component_attributes.provenance` or `component_attributes.source_observation_id` in any public API response (spec §D, API design doc §10 "hidden from public users").
- The real `ns` value for Coleman-Mach parts is `"coleman"`, never `"coleman_mach"` (verified against `edge_resolver.py` and `ground-truth.yaml`).
- No Dealer API, no auth, no new write endpoints — out of scope (spec, "Explicitly out of scope for this round").
- No `categories.py` grouping layer over `part_types.py` — explicitly cut during design.
- `part_types.py` / `manufacturers.py` live in `Docs/Tools/`, importable the same way `edge_types.py` is (that directory is already on `sys.path` for every consumer — `api/main.py`, and every test file via `sys.path.insert(0, str(Path(__file__).resolve().parents[N] / "Docs" / "Tools"))`).

---

### Task 1: `part_types.py` registry

**Files:**
- Create: `Docs/Tools/part_types.py`
- Test: `tests/tools/test_part_types.py`

**Interfaces:**
- Produces: `PartType` (frozen dataclass: `id: int`, `display_name: str`, `description: str = ""`), the 8 bare int constants (`WATER_HEATER_PART_TYPE`, `ATWOOD_PART_TYPE`, `THERMOSTAT_PART_TYPE`, `SUBURBAN_FURNACE_PART_TYPE`, `SUBURBAN_FURNACE_REPAIR_PART_TYPE`, `SUBURBAN_COOKTOP_PART_TYPE`, `NORCOLD_REFRIGERATOR_PART_TYPE`, `NORCOLD_REPAIR_PART_TYPE`), `PART_TYPES: tuple[PartType, ...]`, `PART_TYPE_NAMES: dict[int, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_part_types.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from part_types import (
    PART_TYPES,
    PART_TYPE_NAMES,
    ATWOOD_PART_TYPE,
    NORCOLD_REFRIGERATOR_PART_TYPE,
    NORCOLD_REPAIR_PART_TYPE,
    SUBURBAN_COOKTOP_PART_TYPE,
    SUBURBAN_FURNACE_PART_TYPE,
    SUBURBAN_FURNACE_REPAIR_PART_TYPE,
    THERMOSTAT_PART_TYPE,
    WATER_HEATER_PART_TYPE,
)


def test_part_types_cover_every_exported_constant():
    exported_ids = {
        WATER_HEATER_PART_TYPE, ATWOOD_PART_TYPE, THERMOSTAT_PART_TYPE,
        SUBURBAN_FURNACE_PART_TYPE, SUBURBAN_FURNACE_REPAIR_PART_TYPE,
        SUBURBAN_COOKTOP_PART_TYPE, NORCOLD_REFRIGERATOR_PART_TYPE,
        NORCOLD_REPAIR_PART_TYPE,
    }
    registry_ids = {pt.id for pt in PART_TYPES}
    assert registry_ids == exported_ids
    assert len(PART_TYPES) == len(exported_ids)  # no duplicate ids


def test_part_type_names_is_derived_from_registry():
    assert PART_TYPE_NAMES == {pt.id: pt.display_name for pt in PART_TYPES}


def test_known_part_type_display_names():
    assert PART_TYPE_NAMES[WATER_HEATER_PART_TYPE] == "Water Heater"
    assert PART_TYPE_NAMES[THERMOSTAT_PART_TYPE] == "Wall Thermostat"
    assert PART_TYPE_NAMES[NORCOLD_REFRIGERATOR_PART_TYPE] == "Refrigerator"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_part_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'part_types'`

- [ ] **Step 3: Write the registry**

```python
# Docs/Tools/part_types.py
"""Canonical part-type registry for the interchange graph.

Mirrors edge_types.py's single-source-of-truth pattern: the resolver, the
service layer, and the seeded `part_types` table (interchange_schema.py)
all derive from PART_TYPES below instead of each keeping their own copy.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PartType:
    id: int
    display_name: str
    description: str = ""


WATER_HEATER_PART_TYPE = 412
ATWOOD_PART_TYPE = 413
THERMOSTAT_PART_TYPE = 415
SUBURBAN_FURNACE_PART_TYPE = 416
SUBURBAN_FURNACE_REPAIR_PART_TYPE = 417
SUBURBAN_COOKTOP_PART_TYPE = 601
NORCOLD_REFRIGERATOR_PART_TYPE = 602
NORCOLD_REPAIR_PART_TYPE = 603

PART_TYPES = (
    PartType(id=WATER_HEATER_PART_TYPE, display_name="Water Heater"),
    PartType(id=ATWOOD_PART_TYPE, display_name="Water Heater"),
    PartType(id=THERMOSTAT_PART_TYPE, display_name="Wall Thermostat"),
    PartType(id=SUBURBAN_FURNACE_PART_TYPE, display_name="Furnace"),
    PartType(id=SUBURBAN_FURNACE_REPAIR_PART_TYPE, display_name="Furnace Repair Part"),
    PartType(id=SUBURBAN_COOKTOP_PART_TYPE, display_name="Cooktop"),
    PartType(id=NORCOLD_REFRIGERATOR_PART_TYPE, display_name="Refrigerator"),
    PartType(id=NORCOLD_REPAIR_PART_TYPE, display_name="Refrigerator Repair Part"),
)

PART_TYPE_NAMES = {pt.id: pt.display_name for pt in PART_TYPES}
```

Note: `ATWOOD_PART_TYPE` (413) is used in `edge_resolver.py` for both Atwood water
heater endpoints and Atwood repair parts (e.g. `c_placeholder_wh_atwood_epart_91230` —
see `edge_resolver.py:1220`) — there is no separate Atwood repair-part type, unlike
Suburban (416/417) and Norcold (602/603). This is an existing data-model asymmetry, not
something this task changes; both get the display name `"Water Heater"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_part_types.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add Docs/Tools/part_types.py tests/tools/test_part_types.py
git commit -m "feat: add part_types.py canonical registry"
```

---

### Task 2: `manufacturers.py` registry

**Files:**
- Create: `Docs/Tools/manufacturers.py`
- Test: `tests/tools/test_manufacturers.py`

**Interfaces:**
- Produces: `Manufacturer` (frozen dataclass: `ns: str`, `display_name: str`), `MANUFACTURERS: tuple[Manufacturer, ...]`, `MANUFACTURER_NAMES: dict[str, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_manufacturers.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manufacturers import MANUFACTURERS, MANUFACTURER_NAMES


def test_manufacturers_cover_the_four_shipped_vendors():
    assert {m.ns for m in MANUFACTURERS} == {"suburban", "coleman", "atwood", "norcold"}


def test_manufacturer_names_is_derived_from_registry():
    assert MANUFACTURER_NAMES == {m.ns: m.display_name for m in MANUFACTURERS}


def test_known_manufacturer_display_names():
    assert MANUFACTURER_NAMES["coleman"] == "Coleman-Mach"
    assert MANUFACTURER_NAMES["suburban"] == "Suburban"
    assert MANUFACTURER_NAMES["atwood"] == "Atwood"
    assert MANUFACTURER_NAMES["norcold"] == "Norcold"


def test_non_manufacturer_namespaces_are_absent():
    # icm/dwin/kib (sub-component namespaces) and silkscreen (a physical-marking
    # identifier type) are real ns values in ground-truth.yaml but are not
    # manufacturers - callers must .get() and handle a miss, not assume coverage.
    for ns in ("icm", "dwin", "kib", "silkscreen"):
        assert ns not in MANUFACTURER_NAMES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_manufacturers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'manufacturers'`

- [ ] **Step 3: Write the registry**

```python
# Docs/Tools/manufacturers.py
"""Canonical manufacturer registry for the interchange graph.

Mirrors edge_types.py's single-source-of-truth pattern. Keyed on the same
`ns` values used in identifiers.ns - not every ns is a manufacturer (some
are sub-component namespaces or physical-marking identifier types), so
callers look up MANUFACTURER_NAMES.get(ns) and treat a miss as "no
manufacturer name to show," not an error.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Manufacturer:
    ns: str
    display_name: str


MANUFACTURERS = (
    Manufacturer(ns="suburban", display_name="Suburban"),
    Manufacturer(ns="coleman", display_name="Coleman-Mach"),
    Manufacturer(ns="atwood", display_name="Atwood"),
    Manufacturer(ns="norcold", display_name="Norcold"),
)

MANUFACTURER_NAMES = {m.ns: m.display_name for m in MANUFACTURERS}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_manufacturers.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add Docs/Tools/manufacturers.py tests/tools/test_manufacturers.py
git commit -m "feat: add manufacturers.py canonical registry"
```

---

### Task 3: Seed `part_types` and `manufacturers` tables in `interchange_schema.py`

**Files:**
- Modify: `Docs/Tools/interchange_schema.py`

**Interfaces:**
- Consumes: `PART_TYPES` from `part_types.py` (Task 1), `MANUFACTURERS` from `manufacturers.py` (Task 2).
- Produces: two new tables (`part_types`, `manufacturers`), auto-seeded by every `init_db()` call.

- [ ] **Step 1: Write the failing test**

Add to the bottom of `Docs/Tools/interchange_schema.py`'s existing `self_test()` function
(this file has no separate pytest file today — its own `self_test()`/`--self-test` is the
established convention for this module, matching `part_type`'s and `edge_types`' pytest
files being the exception because they're small, pure-Python registries; this file is
schema DDL, so it stays in its existing self-test).

First, run the current self-test to see today's baseline (no failure expected yet, this
just confirms the harness runs before you touch it):

Run: `python Docs/Tools/interchange_schema.py --self-test --verbose`
Expected: `PASS: 16 tables created` then `self_test: PASS`

- [ ] **Step 2: Add the tables to `SCHEMA` and seed them in `init_db`**

In `Docs/Tools/interchange_schema.py`, add two `CREATE TABLE` statements to the `SCHEMA`
string (insert right after the closing `);` of the `identifier_equivalence_evidence`
table, i.e. right before the closing `"""`):

```python
CREATE TABLE IF NOT EXISTS part_types (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS manufacturers (
    ns            TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL
);
"""
```
(replacing the file's existing closing `"""` on its own line).

Add imports near the top of the file, right after `import sys`:

```python
from manufacturers import MANUFACTURERS
from part_types import PART_TYPES
```

No `sys.path` change is needed here: every caller of `interchange_schema.py` already
puts `Docs/Tools` on `sys.path` before importing it (every test file does this; so does
`edge_resolver.py` at its own `sys.path.insert(0, str(Path(__file__).parent))`), and
running this file directly (`python Docs/Tools/interchange_schema.py --self-test`)
automatically puts its own directory on `sys.path[0]`. `manufacturers.py` and
`part_types.py` live in that same directory (Tasks 1-2), so the plain import resolves in
both cases.

Then change `init_db` from:

```python
def init_db(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
```

to:

```python
def init_db(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT OR IGNORE INTO part_types (id, display_name, description) VALUES (?, ?, ?)",
        [(pt.id, pt.display_name, pt.description or None) for pt in PART_TYPES])
    conn.executemany(
        "INSERT OR IGNORE INTO manufacturers (ns, display_name) VALUES (?, ?)",
        [(m.ns, m.display_name) for m in MANUFACTURERS])
    conn.commit()
    return conn
```

`INSERT OR IGNORE` makes this safe to run every time `init_db` is called against an
already-populated file (same idempotency guarantee the file's own self-test already
requires — "calling init_db twice on the same file must not raise").

- [ ] **Step 3: Update `self_test()` to assert the new tables exist and are seeded**

In `self_test()`, change:

```python
    expected = {
        "components", "component_attributes", "identifiers", "edges", "edge_substitution_detail",
        "edge_caveat", "edge_required_part", "edge_contains_detail",
        "edge_controls_detail", "edge_requires_system_detail",
        "edge_supersession_detail", "edge_shared_subassembly_detail",
        "edge_aftermarket_replaces_detail", "relationship_evidence",
        "identifier_equivalence_candidate", "identifier_equivalence_evidence",
    }
```

to:

```python
    expected = {
        "components", "component_attributes", "identifiers", "edges", "edge_substitution_detail",
        "edge_caveat", "edge_required_part", "edge_contains_detail",
        "edge_controls_detail", "edge_requires_system_detail",
        "edge_supersession_detail", "edge_shared_subassembly_detail",
        "edge_aftermarket_replaces_detail", "relationship_evidence",
        "identifier_equivalence_candidate", "identifier_equivalence_evidence",
        "part_types", "manufacturers",
    }
```

Then, right after the existing `if "component_attributes" in tables:` block (the
value-check insert/rollback block), add:

```python
    seeded_part_types = {r["id"]: r["display_name"] for r in conn.execute(
        "SELECT id, display_name FROM part_types")}
    if seeded_part_types != {pt.id: pt.display_name for pt in PART_TYPES}:
        print(f"FAIL: seeded part_types table does not match PART_TYPES registry: "
              f"{seeded_part_types}")
        missing.add("part_types_seed_mismatch")

    seeded_manufacturers = {r["ns"]: r["display_name"] for r in conn.execute(
        "SELECT ns, display_name FROM manufacturers")}
    if seeded_manufacturers != {m.ns: m.display_name for m in MANUFACTURERS}:
        print(f"FAIL: seeded manufacturers table does not match MANUFACTURERS registry: "
              f"{seeded_manufacturers}")
        missing.add("manufacturers_seed_mismatch")
```

Finally, update the print at the end of a passing run — it currently reads
`print(f"PASS: {len(expected)} tables created")`, which will now automatically print
`PASS: 18 tables created` (no code change needed, just confirming the number moves from
16 to 18 in Step 4 below).

- [ ] **Step 4: Run the self-test to verify it passes**

Run: `python Docs/Tools/interchange_schema.py --self-test --verbose`
Expected: `PASS: 18 tables created` then `self_test: PASS`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add Docs/Tools/interchange_schema.py
git commit -m "feat: seed part_types and manufacturers tables from their registries"
```

---

### Task 4: Point `edge_resolver.py`'s part-type constants at the new registry

**Files:**
- Modify: `Docs/Tools/edge_resolver.py:19-70` (imports and constant block)

**Interfaces:**
- Consumes: the 8 constants from `part_types.py` (Task 1).
- Produces: no change to any other symbol — every existing call site
  (`Component(component_id, WATER_HEATER_PART_TYPE)`, etc.) is untouched.

- [ ] **Step 1: Establish the regression baseline**

Run: `python Docs/Tools/edge_resolver.py --check-fixture Docs/Inital_Design/ground-truth.yaml`
Expected: ends with `0 total mismatches against ground-truth.yaml`, exit code 0. Keep this
output — you'll compare against it after the change.

- [ ] **Step 2: Add the import**

In `Docs/Tools/edge_resolver.py`, after the existing import block that ends with:

```python
from interchange_store import (
    insert_component, insert_identifier, insert_edge, insert_substitution_detail,
    insert_supersession_detail,
    insert_caveat, insert_evidence, now_iso, get_caveats_for_edge, get_evidence_for_edge,
    insert_component_attribute, get_component_attributes,
    insert_identifier_equivalence_candidate, insert_identifier_equivalence_evidence,
    get_identifier_equivalence_candidates, get_identifier_equivalence_evidence,
    get_supersession_detail, insert_required_part, get_required_parts_for_edge,
    insert_controls_detail, get_controls_detail,
)
```

add:

```python
from part_types import (
    ATWOOD_PART_TYPE, NORCOLD_REFRIGERATOR_PART_TYPE, NORCOLD_REPAIR_PART_TYPE,
    SUBURBAN_COOKTOP_PART_TYPE, SUBURBAN_FURNACE_PART_TYPE,
    SUBURBAN_FURNACE_REPAIR_PART_TYPE, THERMOSTAT_PART_TYPE, WATER_HEATER_PART_TYPE,
)
```

- [ ] **Step 3: Remove the local constant definitions**

Delete these 8 lines from the constant block that follows the imports (they are scattered
among other, unrelated constants — e.g. `THERMOSTAT_CODE`, `COLEMAN_ENDPOINT_MODELS` —
which must stay; delete only these exact lines):

```python
WATER_HEATER_PART_TYPE = 412
```
```python
THERMOSTAT_PART_TYPE = 415
```
```python
ATWOOD_PART_TYPE = 413
```
```python
SUBURBAN_FURNACE_PART_TYPE = 416
```
```python
SUBURBAN_FURNACE_REPAIR_PART_TYPE = 417
```
```python
SUBURBAN_COOKTOP_PART_TYPE = 601
```
```python
NORCOLD_REFRIGERATOR_PART_TYPE = 602
```
```python
NORCOLD_REPAIR_PART_TYPE = 603
```

Every other line currently interspersed with these (`THERMOSTAT_CODE = "415-0012-A"`,
`COLEMAN_ENDPOINT_MODELS = (...)`, `SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION = ...`,
`NORCOLD_ENDPOINT_RESOLVER_VERSION = ...`, etc.) stays exactly as-is.

- [ ] **Step 4: Re-run the regression baseline**

Run: `python Docs/Tools/edge_resolver.py --check-fixture Docs/Inital_Design/ground-truth.yaml`
Expected: identical output to Step 1 — `0 total mismatches against ground-truth.yaml`,
exit code 0. If anything changed, a constant was deleted or mistyped; diff against Step 1's
output before proceeding.

Also run: `python Docs/Tools/edge_resolver.py --self-test --verbose`
Expected: exits 0 (no printed `FAIL` lines).

- [ ] **Step 5: Commit**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "refactor: import part-type constants from part_types.py instead of redefining them"
```

---

### Task 5: New response models in `api/schemas.py`

**Files:**
- Modify: `Docs/Tools` is not touched here; modify `api/schemas.py` (full-file rewrite, see below)

**Interfaces:**
- Produces: `AttributeOut(name, qualifier, value, unit)`, `RequiredPartOut(ns, value, role, manufacturer)`, `CaveatOut(text, blocking)`; `SearchResultItem` and `ResolveResponse` gain `manufacturer`, `part_type`, `attributes`; `ReplacementItem` gains `required_parts`, `caveats` and **loses** `summary`.
- Consumes (Task 6/7 will produce dicts matching these shapes): nothing new from earlier
  tasks — this task only defines the contract those tasks must satisfy.

- [ ] **Step 1: Replace `api/schemas.py`**

This is a full-file rewrite (the existing file is 47 lines; shown in full for clarity —
no step in this task is a partial edit):

```python
"""api/schemas.py — Public API response shapes. Never includes interchange_code
(ARCHITECTURE-Interchange_Core.md §2 visibility rule) or any observation/candidate/review
internals (RV_Interchange_API_Design.md §10, "Hidden from public users"). Component
attributes are exposed via AttributeOut, which deliberately omits `provenance` and
`source_observation_id` — those stay internal even though the underlying
component_attributes row carries them."""

from typing import Optional

from pydantic import BaseModel


class IdentifierOut(BaseModel):
    ns: str
    value: str


class AttributeOut(BaseModel):
    name: str
    qualifier: str = ""
    value: str | float | bool
    unit: Optional[str] = None


class SearchResultItem(BaseModel):
    component_id: str
    label: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


class ResolveResponse(BaseModel):
    component_id: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []


class RequiredPartOut(BaseModel):
    ns: str
    value: str
    role: Optional[str] = None
    manufacturer: Optional[str] = None


class CaveatOut(BaseModel):
    text: str
    blocking: bool


class ReplacementItem(BaseModel):
    part: str
    fit: str
    rank: int
    required_parts: list[RequiredPartOut] = []
    caveats: list[CaveatOut] = []


class SupersessionItem(BaseModel):
    part: str
    note: Optional[str] = None


class ReplacementsResponse(BaseModel):
    source: str
    replacements: list[ReplacementItem]
    supersessions: list[SupersessionItem] = []
```

- [ ] **Step 2: Confirm the app still imports cleanly**

Run: `python -c "import api.main"`
Expected: no output, exit code 0. (This will actually still succeed even before Task 6/7
update `api/services.py`, because FastAPI only validates response shapes against these
models at request time, not at import time — Tasks 6/7 are what make the running
responses actually match. This step just catches typos in the schema file itself.)

- [ ] **Step 3: Commit**

```bash
git add api/schemas.py
git commit -m "feat: add manufacturer/part_type/attributes/required_parts/caveats response fields"
```

Note: this commit temporarily breaks `api/services.py`'s contract with these models
(`ReplacementItem` no longer has `summary`, which `services.py` still returns) — Tasks
6 and 7 fix this in the same work session. If you're pausing between tasks, don't deploy
between Task 5 and Task 7.

---

### Task 6: Wire `manufacturer` / `part_type` / `attributes` into `IdentifierService` and `SearchService`

**Files:**
- Modify: `api/services.py:1-44` (imports, `IdentifierService`, `SearchService`)
- Modify: `tests/api/test_services.py` (existing tests broken by the new fields)

**Interfaces:**
- Consumes: `PART_TYPE_NAMES` (Task 1), `MANUFACTURER_NAMES` (Task 2),
  `get_component_attributes(conn, component_id, name=None)` (already exists,
  `interchange_store.py:111`).
- Produces: `_format_attributes(conn, component_id) -> list[dict]`, used again by Task 7.

- [ ] **Step 1: Write the failing tests**

In `tests/api/test_services.py`, replace the existing
`test_resolve_known_identifier` with:

```python
def test_resolve_known_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result == {
        "component_id": "c_test_a",
        "manufacturer": "Suburban",
        "part_type": "Water Heater",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
        "attributes": [],
    }
```

Add a new test right after it:

```python
def test_resolve_includes_component_attributes():
    from interchange_store import insert_component_attribute
    from interchange_models import ComponentAttribute

    conn = init_db(":memory:")
    _seed_basic_component(conn)
    insert_component_attribute(conn, ComponentAttribute(
        component_id="c_test_a", name="capacity", provenance="manufacturer_pdf",
        source_observation_id=1, value_number=6.0, unit="gal"))

    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result["attributes"] == [
        {"name": "capacity", "qualifier": "", "value": 6.0, "unit": "gal"},
    ]
    # provenance/source_observation_id must never leak into the response
    assert "provenance" not in result["attributes"][0]
    assert "source_observation_id" not in result["attributes"][0]
```

Update `test_search_ranks_exact_match_first` — add two lines at the end of the existing
function body (don't remove any existing assertions):

```python
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
    assert result["results"][0]["manufacturer"] == "Suburban"
    assert result["results"][0]["part_type"] == "Water Heater"
```

Add a new test for the "unknown ns" degrade-gracefully case:

```python
def test_search_result_manufacturer_is_none_for_unmapped_namespace():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 415, "415-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "icm", "PCB1060"))

    result = SearchService.search(conn, "PCB1060")
    assert result["results"][0]["manufacturer"] is None
    assert result["results"][0]["part_type"] == "Wall Thermostat"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_services.py -v -k "resolve_known_identifier or resolve_includes_component_attributes or search_ranks_exact_match_first or search_result_manufacturer_is_none"`
Expected: FAIL — `KeyError: 'manufacturer'` (or similar) since `IdentifierService`/
`SearchService` don't produce these keys yet.

- [ ] **Step 3: Implement**

In `api/services.py`, change the import block from:

```python
from interchange_store import (
    get_component, get_component_by_identifier, get_edges_from,
    get_caveats_for_edge, get_evidence_for_edge, get_identifiers_for_component,
    get_supersession_detail, search_identifiers,
)
from interchange_models import compute_confidence
from edge_types import EDGE_TYPE_SUBSTITUTES, EDGE_TYPE_SUPERSEDES
```

to:

```python
from interchange_store import (
    get_component, get_component_attributes, get_component_by_identifier,
    get_edges_from, get_caveats_for_edge, get_evidence_for_edge,
    get_identifiers_for_component, get_required_parts_for_edge,
    get_supersession_detail, search_identifiers,
)
from interchange_models import compute_confidence
from edge_types import EDGE_TYPE_SUBSTITUTES, EDGE_TYPE_SUPERSEDES
from manufacturers import MANUFACTURER_NAMES
from part_types import PART_TYPE_NAMES
```

Add a new helper function after the imports (used by both this task and Task 7):

```python
def _attribute_value(attribute):
    if attribute.value_text is not None:
        return attribute.value_text
    if attribute.value_number is not None:
        return attribute.value_number
    return attribute.value_boolean


def _format_attributes(conn, component_id):
    return [
        {
            "name": attribute.name,
            "qualifier": attribute.qualifier,
            "value": _attribute_value(attribute),
            "unit": attribute.unit,
        }
        for attribute in get_component_attributes(conn, component_id)
    ]


def _ns_for_label(identifiers, label):
    for identifier in identifiers:
        if identifier.value == label:
            return identifier.ns
    return identifiers[0].ns if identifiers else None
```

Change `IdentifierService.resolve` from:

```python
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

to:

```python
class IdentifierService:
    @staticmethod
    def resolve(conn, ns, value):
        component = get_component_by_identifier(conn, ns, value)
        if component is None:
            return None
        identifiers = get_identifiers_for_component(conn, component.component_id)
        return {
            "component_id": component.component_id,
            "manufacturer": MANUFACTURER_NAMES.get(ns),
            "part_type": PART_TYPE_NAMES.get(component.part_type_id),
            "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
            "attributes": _format_attributes(conn, component.component_id),
        }
```

Change `SearchService.search` from:

```python
class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        matches = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id, matched_value in matches:
            identifiers = get_identifiers_for_component(conn, component_id)
            results.append({
                "component_id": component_id,
                "label": matched_value,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
            })
        return {"query": query, "results": results}
```

to:

```python
class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        matches = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id, matched_value in matches:
            identifiers = get_identifiers_for_component(conn, component_id)
            component = get_component(conn, component_id)
            matched_ns = _ns_for_label(identifiers, matched_value)
            results.append({
                "component_id": component_id,
                "label": matched_value,
                "manufacturer": MANUFACTURER_NAMES.get(matched_ns),
                "part_type": PART_TYPE_NAMES.get(component.part_type_id) if component else None,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
                "attributes": _format_attributes(conn, component_id),
            })
        return {"query": query, "results": results}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_services.py -v`
Expected: all pass. (Some other tests in this file will still fail — the
`get_replacements` ones, which reference `summary` — that's expected; Task 7 fixes those.)

- [ ] **Step 5: Commit**

```bash
git add api/services.py tests/api/test_services.py
git commit -m "feat: enrich resolve/search results with manufacturer, part_type, attributes"
```

---

### Task 7: Wire `required_parts` / structured `caveats` into `ReplacementService`, remove `summary`

**Files:**
- Modify: `api/services.py` (`ReplacementService.get_replacements`)
- Modify: `tests/api/test_services.py` (existing tests broken by removing `summary`)

**Interfaces:**
- Consumes: `get_required_parts_for_edge(conn, edge_id)` (already exists,
  `interchange_store.py:258`), `MANUFACTURER_NAMES` (Task 2), `_format_attributes`'s
  sibling pattern from Task 6 (not reused directly — a new `_format_required_parts` and
  `_format_caveats` are added here).
- Produces: each `ReplacementItem` dict now has `required_parts: list[dict]` and
  `caveats: list[dict]`; `summary` is gone.

- [ ] **Step 1: Write the failing tests**

Replace `test_get_replacements_tiers_by_confidence`'s final assertion block — change:

```python
    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["source"] == "SW6DE"
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2, "summary": None},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "summary": "Requires switch kit"},
    ]
```

to:

```python
    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["source"] == "SW6DE"
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2,
         "required_parts": [], "caveats": []},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "required_parts": [],
         "caveats": [{"text": "Requires switch kit", "blocking": True}]},
    ]
```

Apply the identical replacement to `test_get_replacements_rank_reflects_tier_not_insertion_order`
(it ends with the exact same assertion block).

In `test_get_replacements_excludes_below_bar_and_unknown_component`, change:

```python
    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
    ]
```

to:

```python
    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
    ]
```

Add a new test after `test_get_replacements_omits_supersession_with_no_evidence` (end of
file) covering `required_parts`:

```python
def test_get_replacements_includes_required_parts():
    from interchange_store import insert_required_part
    from interchange_models import EdgeRequiredPart

    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))

    edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                to_component_id="c_test_b")
    insert_edge(conn, edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))
    insert_required_part(conn, EdgeRequiredPart(
        edge_id=edge.id, ns="suburban", value="6276APW", role="replacement_panel"))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    match = next(r for r in result["replacements"] if r["part"] == "SW6DEL")
    assert match["required_parts"] == [
        {"ns": "suburban", "value": "6276APW", "role": "replacement_panel",
         "manufacturer": "Suburban"},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_services.py -v -k "get_replacements"`
Expected: FAIL — `AssertionError` on the updated equality checks (actual dicts still
contain `summary` instead of `required_parts`/`caveats`), and `KeyError`/`AttributeError`
on `test_get_replacements_includes_required_parts` since nothing produces
`required_parts` yet.

- [ ] **Step 3: Implement**

In `api/services.py`, add two more helpers next to `_format_attributes` (from Task 6):

```python
def _format_required_parts(conn, edge_id):
    return [
        {
            "ns": part.ns,
            "value": part.value,
            "role": part.role,
            "manufacturer": MANUFACTURER_NAMES.get(part.ns),
        }
        for part in get_required_parts_for_edge(conn, edge_id)
    ]


def _format_caveats(caveats):
    return [{"text": c.text, "blocking": c.blocking} for c in caveats]
```

Change `ReplacementService.get_replacements` from:

```python
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
        for edge in get_edges_from(conn, component_id, type=EDGE_TYPE_SUBSTITUTES):
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
```

to:

```python
class ReplacementService:
    @staticmethod
    def get_replacements(conn, component_id, ns=None):
        component = get_component(conn, component_id)
        if component is None:
            return None

        source_label = _label_for(conn, component_id, ns)
        replacements = [
            {"part": source_label, "fit": "Exact Match", "rank": 1,
             "required_parts": [], "caveats": []},
        ]

        _TIER_PRIORITY = {"Direct Fit": 0, "Fits With Modification": 1}

        candidates = []
        for edge in get_edges_from(conn, component_id, type=EDGE_TYPE_SUBSTITUTES):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            candidates.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "fit": fit,
                "required_parts": _format_required_parts(conn, edge["id"]),
                "caveats": _format_caveats(caveats),
                "_confidence_value": confidence["value"],
            })
```

The rest of the method (`candidates.sort(...)`, the `rank`-assignment loop, the
supersessions loop, the final `return`) is unchanged — it doesn't reference `summary`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_services.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api/services.py tests/api/test_services.py
git commit -m "feat: replace flattened caveat summary with structured caveats and required_parts"
```

---

### Task 8: Fix `tests/api/test_main.py` and `tests/api/test_e2e.py` for the new contract

**Files:**
- Modify: `tests/api/test_main.py`
- Modify: `tests/api/test_e2e.py`

**Interfaces:**
- Consumes: the response shapes finalized in Tasks 5-7. No new production code.

- [ ] **Step 1: Update `tests/api/test_main.py`**

Change `test_resolve_endpoint` from:

```python
def test_resolve_endpoint(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "component_id": "c_test_a",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
    }
```

to:

```python
def test_resolve_endpoint(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "component_id": "c_test_a",
        "manufacturer": "Suburban",
        "part_type": "Water Heater",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
        "attributes": [],
    }
```

Change `test_replacements_endpoint` from:

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

to:

```python
def test_replacements_endpoint(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
             "required_parts": [], "caveats": []},
        ],
        "supersessions": [],
    }
```

- [ ] **Step 2: Update `tests/api/test_e2e.py`**

Change `test_sw6de_and_sw6del_replacement_behavior_is_directional` from:

```python
def test_sw6de_and_sw6del_replacement_behavior_is_directional(client):
    sw6de = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert sw6de.status_code == 200
    assert sw6de.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
            {"part": "SW6DEL", "fit": "Fits With Modification", "rank": 2, "summary": None},
        ],
        "supersessions": [],
    }

    sw6del = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DEL"})
    assert sw6del.status_code == 200
    body = sw6del.json()
    assert body["source"] == "SW6DEL"
    assert body["replacements"][0] == {
        "part": "SW6DEL", "fit": "Exact Match", "rank": 1, "summary": None,
    }
    assert any(
        item["part"] == "SW6DE" and "12V relay" in (item["summary"] or "")
        for item in body["replacements"]
    )
```

to:

```python
def test_sw6de_and_sw6del_replacement_behavior_is_directional(client):
    sw6de = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert sw6de.status_code == 200
    assert sw6de.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
             "required_parts": [], "caveats": []},
            {"part": "SW6DEL", "fit": "Fits With Modification", "rank": 2,
             "required_parts": [], "caveats": []},
        ],
        "supersessions": [],
    }

    sw6del = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DEL"})
    assert sw6del.status_code == 200
    body = sw6del.json()
    assert body["source"] == "SW6DEL"
    assert body["replacements"][0] == {
        "part": "SW6DEL", "fit": "Exact Match", "rank": 1,
        "required_parts": [], "caveats": [],
    }
    assert any(
        item["part"] == "SW6DE"
        and any("12V relay" in c["text"] for c in item["caveats"])
        for item in body["replacements"]
    )
```

Change `test_coleman_supersession_chain_is_visible_through_api` from:

```python
    assert body["replacements"] == [
        {"part": "7330F3361", "fit": "Exact Match", "rank": 1, "summary": None},
    ]
```

to:

```python
    assert body["replacements"] == [
        {"part": "7330F3361", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
    ]
```

Change `test_atwood_repair_part_is_served_from_the_persisted_database` from:

```python
def test_atwood_repair_part_is_served_from_the_persisted_database(client, persisted_db_path):
    search = client.get("/public/v1/search", params={"q": "91230"})
    assert search.status_code == 200
    assert search.json() == {
        "query": "91230",
        "results": [
            {
                "component_id": "c_placeholder_wh_atwood_epart_91230",
                "label": "91230",
                "identifiers": [{"ns": "atwood", "value": "91230"}],
            },
        ],
    }
```

to:

```python
def test_atwood_repair_part_is_served_from_the_persisted_database(client, persisted_db_path):
    search = client.get("/public/v1/search", params={"q": "91230"})
    assert search.status_code == 200
    assert search.json() == {
        "query": "91230",
        "results": [
            {
                "component_id": "c_placeholder_wh_atwood_epart_91230",
                "label": "91230",
                "manufacturer": "Atwood",
                "part_type": "Water Heater",
                "identifiers": [{"ns": "atwood", "value": "91230"}],
                "attributes": [
                    {"name": "description", "qualifier": "",
                     "value": "Switch 12 VDC - White Combo", "unit": None},
                ],
            },
        ],
    }
```

- [ ] **Step 3: Run the full API test suite**

Run: `pytest tests/api/ -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/api/test_main.py tests/api/test_e2e.py
git commit -m "test: update API tests for enriched response contract"
```

---

### Task 9: Update `web/app.js` and `web/style.css` for the new contract

**Files:**
- Modify: `web/app.js` (`renderResults`, `renderDetail`)
- Modify: `web/style.css` (one new rule)

**Interfaces:**
- Consumes: `SearchResultItem.manufacturer`, `.part_type` (Task 6);
  `ReplacementItem.caveats` (Task 7, replaces the old `.summary`).

- [ ] **Step 1: Add manufacturer/part_type to result cards**

In `web/app.js`, inside `renderResults`, change:

```js
    const label = document.createElement("div");
    label.className = "result-label";
    label.textContent = result.label;
    li.appendChild(label);

    const idList = document.createElement("div");
```

to:

```js
    const label = document.createElement("div");
    label.className = "result-label";
    label.textContent = result.label;
    li.appendChild(label);

    if (result.manufacturer || result.part_type) {
      const meta = document.createElement("div");
      meta.className = "result-meta";
      meta.textContent = [result.manufacturer, result.part_type]
        .filter(Boolean).join(" — ");
      li.appendChild(meta);
    }

    const idList = document.createElement("div");
```

- [ ] **Step 2: Switch caveat rendering from `summary` to `caveats`**

In `web/app.js`, inside `renderDetail`'s tier-rendering loop, change:

```js
    const list = document.createElement("ul");
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item.summary ? `${item.part} — ${item.summary}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }

  if (data.supersessions && data.supersessions.length > 0) {
```

to:

```js
    const list = document.createElement("ul");
    for (const item of items) {
      const li = document.createElement("li");
      const caveatText = item.caveats && item.caveats.length
        ? item.caveats.map((c) => c.text).join("; ")
        : null;
      li.textContent = caveatText ? `${item.part} — ${caveatText}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }

  if (data.supersessions && data.supersessions.length > 0) {
```

- [ ] **Step 3: Add the `.result-meta` style**

In `web/style.css`, add after the existing `.result-label` rule:

```css
.result-label {
  font-weight: bold;
  font-size: 1.05rem;
}

.result-meta {
  color: #666;
  font-size: 0.85rem;
  margin-top: 0.15rem;
}
```

(Only the `.result-meta` block is new — `.result-label` is shown for placement context,
don't duplicate it.)

- [ ] **Step 4: Manual verification, run locally (no compose file in this repo)**

This project has no frontend test framework (consistent with
`2026-08-04-stage2-frontend-phase2-design.md`'s precedent) — verify manually. Note: there
is no `docker-compose.yaml` tracked in this repository (only `api/Dockerfile` and
`web/Dockerfile` exist here — the actual deployment compose file, if any, lives outside
this checkout). Run both pieces directly instead, matching the ports
`web/api-client.js` and `api/main.py`'s CORS config already expect:

```bash
# terminal 1 - the API, on the port api-client.js hardcodes (8484)
uvicorn api.main:app --host 0.0.0.0 --port 8484

# terminal 2 - the static frontend, on the port CORS whitelists (8485)
cd web && python3 -m http.server 8485
```

Then in a browser at `http://localhost:8485`:
1. Search `SW6DE` — confirm each result card shows a manufacturer/part-type line under
   the identifier (e.g. "Suburban — Water Heater").
2. Click the `SW6DEL` result — confirm the "Fits With Modification" tier (if present)
   shows the caveat text inline, same as before (visually indistinguishable from the old
   `summary`-based rendering — this is a refactor, not a redesign).
3. Confirm no browser console errors.

Stop both processes (Ctrl-C in each terminal) when done.

- [ ] **Step 5: Commit**

```bash
git add web/app.js web/style.css
git commit -m "feat: surface manufacturer/part_type and structured caveats in the frontend"
```

---

### Task 10: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full pytest suite**

Run: `pytest -v`
Expected: all tests pass, including everything from Tasks 1-8.

- [ ] **Step 2: Run every `Docs/Tools` self-test**

```bash
python Docs/Tools/interchange_schema.py --self-test --verbose
python Docs/Tools/interchange_store.py --self-test --verbose
python Docs/Tools/edge_resolver.py --self-test --verbose
python Docs/Tools/edge_resolver.py --check-fixture Docs/Inital_Design/ground-truth.yaml
```

Expected: every command exits 0 with no `FAIL` lines, and the last one ends with
`0 total mismatches against ground-truth.yaml`.

- [ ] **Step 3: Rebuild the real `components.db` and smoke-test the live API**

```bash
python Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db
```

Expected: exit code 0.

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8484 &
sleep 1
curl -s "http://localhost:8484/public/v1/search?q=SW6DE" | python3 -m json.tool
curl -s "http://localhost:8484/public/v1/replacements?ns=suburban&identifier=SW6DEL" | python3 -m json.tool
kill %1
```

Expected: both responses include `manufacturer`, `part_type`, `attributes` (search) and
`required_parts`, `caveats` (replacements), with no `summary` key anywhere.

- [ ] **Step 4: Final commit (if any working-tree changes remain)**

```bash
git status
```

If clean (all prior tasks already committed their own work), no action needed. Otherwise:

```bash
git add -A
git commit -m "chore: final verification pass for public API enrichment"
```
