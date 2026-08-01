# Edge Schema & Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SQLite-backed components/edges store described in
`docs/superpowers/specs/2026-07-31-edge-schema-design.md`, and a resolver that reads
`Docs/Tools/observations.db` through `resolver.py`'s vocabulary layer and
`suburban_parser.py`'s model comparison into that store — proven against the fixture's
canonical edge case (SW6DE/SW6DEL).

**Architecture:** Four new files under `Docs/Tools/`, following the existing project
convention (`observations.py`, `resolver.py`, `suburban_parser.py`) of one file per
responsibility, an inline `self_test()` function per module instead of pytest, and a
`--check-fixture` CLI flag that cross-checks against `Docs/Inital_Design/ground-truth.yaml`.
No new dependencies — stdlib `sqlite3`/`dataclasses` plus the already-used `pyyaml` for
fixture checks.

**Tech Stack:** Python 3, stdlib `sqlite3`, stdlib `dataclasses`, `pyyaml` (already a
project dependency per `suburban_parser.py`'s `check_fixture`).

**Status:** Completed 2026-07-31. All tasks below are implemented on `main`; the full
self-test suite and canonical fixture check pass.

## Global Constraints

- Follow the spec exactly: shared `edges` core + typed detail tables, one row per
  substitution direction, append-only `relationship_evidence` (never a mutable
  alpha/beta counter), `identifier_equivalence_candidate` instead of an `alias` edge type,
  `edge_required_part` and `edge_caveat` as child tables of `edge_substitution_detail`.
- No pytest — this codebase uses inline `self_test(verbose=False) -> int` functions
  (0 = pass) invoked via a `--self-test` CLI flag, exactly like `suburban_parser.py` and
  `resolver.py` already do. Match that convention exactly.
- `component_id` values are opaque per `ARCHITECTURE-Interchange_Core.md` §2, but *opaque ID
  generation is explicitly out of scope* for this plan (not yet designed anywhere in the
  project). Use the fixture's own placeholder strings (e.g. `c_placeholder_wh_6del`) as the
  literal `component_id` for the two anchor components this plan builds — this keeps
  `--check-fixture` a direct join against `ground-truth.yaml` without inventing ID
  generation as a side effect of this plan.
- Scope is the two in-hand, best-documented anchor components (SW6DE, SW6DEL) and the
  canonical asymmetric substitution edge between them — the fixture's own "THE CANONICAL
  EDGE TEST" comment marks this as the case the whole schema must reproduce first. Full
  reproduction of all ten fixture components/edges is explicitly follow-on work, not part
  of this plan.
- Every new table gets a `CREATE INDEX` on any column it will be looked up by (mirrors
  `observations.py`'s `idx_obs_url` etc.) — don't skip indexes "for now."

---

## File Structure

- Create: `Docs/Tools/interchange_schema.py` — DDL constants + `init_db(path) -> sqlite3.Connection`.
- Create: `Docs/Tools/interchange_models.py` — dataclasses for every row type + confidence math.
- Create: `Docs/Tools/interchange_store.py` — sqlite insert/query functions operating on those dataclasses.
- Create: `Docs/Tools/edge_resolver.py` — reads `observations.db`, builds components + the
  anchor substitution edge, writes them via `interchange_store.py`, and the
  `--check-fixture` validation CLI.

---

### Task 1: Schema DDL and `init_db`

**Files:**
- Create: `Docs/Tools/interchange_schema.py`
- Test: inline `self_test()` in the same file (project convention — see Global Constraints)

**Interfaces:**
- Produces: `SCHEMA: str` (the full DDL), `init_db(path: str) -> sqlite3.Connection` — creates
  all tables if they don't exist and returns an open connection with `row_factory =
  sqlite3.Row`.

- [x] **Step 1: Write `interchange_schema.py` with the full DDL**

```python
#!/usr/bin/env python3
"""
interchange_schema.py — DDL for the derived components/edges store.

Per ARCHITECTURE-Interchange_Core.md §9: this store is REBUILDABLE from
observations.db, never hand-edited. See
docs/superpowers/specs/2026-07-31-edge-schema-design.md for the design
rationale (shared edges core + typed detail tables, one row per
substitution direction, append-only relationship_evidence).
"""

import sqlite3
import sys

DEFAULT_DB = "components.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS components (
    component_id      TEXT PRIMARY KEY,
    part_type_id      INTEGER NOT NULL,
    interchange_code  TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identifiers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id  TEXT NOT NULL REFERENCES components(component_id),
    ns            TEXT NOT NULL,
    value         TEXT NOT NULL,
    visibility    TEXT
);
CREATE INDEX IF NOT EXISTS idx_identifiers_ns_value ON identifiers(ns, value);
CREATE INDEX IF NOT EXISTS idx_identifiers_component ON identifiers(component_id);

CREATE TABLE IF NOT EXISTS edges (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    type                TEXT NOT NULL,
    from_component_id   TEXT NOT NULL REFERENCES components(component_id),
    to_component_id     TEXT REFERENCES components(component_id),
    group_key           TEXT,
    status              TEXT NOT NULL DEFAULT 'candidate',
    resolver_version    TEXT,
    created_at          TEXT NOT NULL,
    retired_at          TEXT,
    notes               TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_component_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_component_id);
CREATE INDEX IF NOT EXISTS idx_edges_group ON edges(group_key);

CREATE TABLE IF NOT EXISTS edge_substitution_detail (
    edge_id      INTEGER PRIMARY KEY REFERENCES edges(id),
    basis        TEXT NOT NULL,
    verdict      TEXT NOT NULL,
    source_text  TEXT
);

CREATE TABLE IF NOT EXISTS edge_caveat (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id        INTEGER NOT NULL REFERENCES edges(id),
    blocking       INTEGER NOT NULL,
    text           TEXT NOT NULL,
    becomes_input  TEXT
);
CREATE INDEX IF NOT EXISTS idx_caveat_edge ON edge_caveat(edge_id);

CREATE TABLE IF NOT EXISTS edge_required_part (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id  INTEGER NOT NULL REFERENCES edges(id),
    ns       TEXT NOT NULL,
    value    TEXT NOT NULL,
    role     TEXT
);
CREATE INDEX IF NOT EXISTS idx_required_part_edge ON edge_required_part(edge_id);

CREATE TABLE IF NOT EXISTS edge_contains_detail (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id         INTEGER NOT NULL REFERENCES edges(id),
    child_ns        TEXT NOT NULL,
    child_value     TEXT NOT NULL,
    role            TEXT,
    assembly_level  TEXT
);

CREATE TABLE IF NOT EXISTS edge_controls_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_requires_system_detail (
    edge_id      INTEGER PRIMARY KEY REFERENCES edges(id),
    system_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_supersession_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_shared_subassembly_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_aftermarket_replaces_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS relationship_evidence (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id                 INTEGER NOT NULL REFERENCES edges(id),
    event_type              TEXT NOT NULL,
    effect_alpha            REAL NOT NULL,
    effect_beta             REAL NOT NULL,
    source_observation_id   INTEGER,
    actor_id                TEXT,
    occurred_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_edge ON relationship_evidence(edge_id);

CREATE TABLE IF NOT EXISTS identifier_equivalence_candidate (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    ns_a                  TEXT NOT NULL,
    value_a               TEXT NOT NULL,
    ns_b                  TEXT NOT NULL,
    value_b               TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'open',
    merged_component_id   TEXT REFERENCES components(component_id)
);

CREATE TABLE IF NOT EXISTS identifier_equivalence_evidence (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id            INTEGER NOT NULL
                            REFERENCES identifier_equivalence_candidate(id),
    event_type              TEXT NOT NULL,
    effect_alpha            REAL NOT NULL,
    effect_beta             REAL NOT NULL,
    source_observation_id   INTEGER,
    actor_id                TEXT,
    occurred_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ident_equiv_evidence_candidate
    ON identifier_equivalence_evidence(candidate_id);
"""


def init_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def self_test(verbose=False):
    conn = init_db(":memory:")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "components", "identifiers", "edges", "edge_substitution_detail",
        "edge_caveat", "edge_required_part", "edge_contains_detail",
        "edge_controls_detail", "edge_requires_system_detail",
        "edge_supersession_detail", "edge_shared_subassembly_detail",
        "edge_aftermarket_replaces_detail", "relationship_evidence",
        "identifier_equivalence_candidate", "identifier_equivalence_evidence",
    }
    missing = expected - tables
    if missing:
        print(f"FAIL: missing tables {missing}")
        return 1
    # calling init_db twice on the same file must not raise (IF NOT EXISTS)
    init_db(":memory:")
    if verbose:
        print(f"PASS: {len(expected)} tables created")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))
    sys.exit(init_db(DEFAULT_DB) and 0)


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run it to verify the self-test passes**

Run: `cd Docs/Tools && python3 interchange_schema.py --self-test --verbose`
Expected: `PASS: 15 tables created` then `self_test: PASS`, exit code 0.

- [x] **Step 3: Commit**

```bash
git add Docs/Tools/interchange_schema.py
git commit -m "Add components/edges store schema (interchange_schema.py)"
```

---

### Task 2: Dataclasses and confidence math

**Files:**
- Create: `Docs/Tools/interchange_models.py`

**Interfaces:**
- Consumes: nothing (pure data definitions).
- Produces: `Component`, `Identifier`, `Edge`, `EdgeSubstitutionDetail`, `EdgeCaveat`,
  `EdgeRequiredPart`, `RelationshipEvidence` dataclasses; `PRIOR_BY_MATCH_QUALITY: dict`;
  `prior_for_basis(basis: str) -> tuple[float, float]`; `compute_confidence(evidence_rows:
  list[RelationshipEvidence]) -> dict` with keys `alpha`, `beta`, `value`, `certainty`.

- [x] **Step 1: Write `interchange_models.py`**

```python
#!/usr/bin/env python3
"""
interchange_models.py — dataclasses mirroring interchange_schema.py's tables,
plus the confidence math from ARCHITECTURE-Interchange_Core.md §7.

Confidence is never stored as a mutable field (see the edge schema design
doc, §7) — compute_confidence() sums relationship_evidence rows on demand.
"""

import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Component:
    component_id: str
    part_type_id: int
    interchange_code: Optional[str] = None


@dataclass
class Identifier:
    component_id: str
    ns: str
    value: str
    visibility: Optional[str] = None


@dataclass
class Edge:
    type: str
    from_component_id: str
    to_component_id: Optional[str] = None
    group_key: Optional[str] = None
    status: str = "candidate"
    resolver_version: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[int] = None


@dataclass
class EdgeSubstitutionDetail:
    edge_id: int
    basis: str
    verdict: str
    source_text: Optional[str] = None


@dataclass
class EdgeCaveat:
    edge_id: int
    blocking: bool
    text: str
    becomes_input: Optional[str] = None
    id: Optional[int] = None


@dataclass
class EdgeRequiredPart:
    edge_id: int
    ns: str
    value: str
    role: Optional[str] = None
    id: Optional[int] = None


@dataclass
class RelationshipEvidence:
    edge_id: int
    event_type: str
    effect_alpha: float
    effect_beta: float
    occurred_at: str
    source_observation_id: Optional[int] = None
    actor_id: Optional[str] = None
    id: Optional[int] = None


# ARCHITECTURE-Interchange_Core.md §7, "Prior, from attribute match" table.
PRIOR_BY_MATCH_QUALITY = {
    "all_critical_exact": (3.0, 1.0),
    "within_tolerance": (2.0, 1.0),
    "unknown_incomplete": (1.0, 1.0),
}

# Maps edge_substitution_detail.basis values to the match-quality prior.
# attribute_match_exact is the only basis that has actually exercised "all
# critical attributes exact" so far (the SW6DE/SW6DEL case) - every other
# basis starts from the honest "unknown/incomplete" prior per §7, then
# accumulates real evidence on top (buyer_confirmed_install,
# manufacturer_documented, etc. are EVENT types, not priors - see
# relationship_evidence event_type, not this table).
_BASIS_TO_PRIOR = {
    "attribute_match_exact": "all_critical_exact",
}


def prior_for_basis(basis):
    quality = _BASIS_TO_PRIOR.get(basis, "unknown_incomplete")
    return PRIOR_BY_MATCH_QUALITY[quality]


def compute_confidence(evidence_rows):
    alpha = sum(r.effect_alpha for r in evidence_rows)
    beta = sum(r.effect_beta for r in evidence_rows)
    if alpha + beta == 0:
        return {"alpha": 0.0, "beta": 0.0, "value": None, "certainty": 0.0}
    return {
        "alpha": alpha,
        "beta": beta,
        "value": alpha / (alpha + beta),
        "certainty": alpha + beta,
    }


def self_test(verbose=False):
    failures = []

    if prior_for_basis("attribute_match_exact") != (3.0, 1.0):
        failures.append("attribute_match_exact prior should be (3, 1)")
    if prior_for_basis("buyer_confirmed_install") != (1.0, 1.0):
        failures.append("unrecognized basis should fall back to (1, 1)")

    # Ground-truth.yaml's canonical edge: prior only, Beta(3,1) -> 0.75, n=4.
    ev = [RelationshipEvidence(edge_id=1, event_type="attribute_prior",
                                effect_alpha=3.0, effect_beta=1.0,
                                occurred_at="2026-07-31T00:00:00+00:00")]
    result = compute_confidence(ev)
    if result["value"] != 0.75 or result["certainty"] != 4.0:
        failures.append(f"expected value=0.75 certainty=4.0, got {result}")

    empty_result = compute_confidence([])
    if empty_result["value"] is not None:
        failures.append("confidence with no evidence should be None, not a number")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: prior lookup and confidence math both correct")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run the self-test**

Run: `cd Docs/Tools && python3 interchange_models.py --self-test --verbose`
Expected: `PASS: prior lookup and confidence math both correct`, `self_test: PASS`, exit 0.

- [x] **Step 3: Commit**

```bash
git add Docs/Tools/interchange_models.py
git commit -m "Add interchange dataclasses and confidence math"
```

---

### Task 3: Store layer — components, identifiers, edges + all detail tables

**Files:**
- Create: `Docs/Tools/interchange_store.py`

**Interfaces:**
- Consumes: `interchange_schema.init_db`; every dataclass from `interchange_models`.
- Produces:
  - `insert_component(conn, component: Component) -> None`
  - `insert_identifier(conn, identifier: Identifier) -> int` (returns new row id)
  - `insert_edge(conn, edge: Edge) -> int` (returns new edge id, sets `edge.id`)
  - `insert_substitution_detail(conn, detail: EdgeSubstitutionDetail) -> None`
  - `insert_caveat(conn, caveat: EdgeCaveat) -> int`
  - `insert_required_part(conn, part: EdgeRequiredPart) -> int`
  - `insert_evidence(conn, evidence: RelationshipEvidence) -> int`
  - `get_edges_from(conn, component_id: str, type: str = None) -> list[sqlite3.Row]`
  - `get_evidence_for_edge(conn, edge_id: int) -> list[RelationshipEvidence]`
  - `get_caveats_for_edge(conn, edge_id: int) -> list[EdgeCaveat]`

- [x] **Step 1: Write `interchange_store.py`**

```python
#!/usr/bin/env python3
"""
interchange_store.py — sqlite persistence for the dataclasses in
interchange_models.py, against the schema in interchange_schema.py.
"""

import sys
from datetime import datetime, timezone

from interchange_models import (
    Component, Identifier, Edge, EdgeSubstitutionDetail, EdgeCaveat,
    EdgeRequiredPart, RelationshipEvidence,
)
from interchange_schema import init_db


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_component(conn, component):
    conn.execute(
        "INSERT INTO components (component_id, part_type_id, interchange_code, created_at) "
        "VALUES (?, ?, ?, ?)",
        (component.component_id, component.part_type_id, component.interchange_code,
         now_iso()))
    conn.commit()


def insert_identifier(conn, identifier):
    cur = conn.execute(
        "INSERT INTO identifiers (component_id, ns, value, visibility) VALUES (?, ?, ?, ?)",
        (identifier.component_id, identifier.ns, identifier.value, identifier.visibility))
    conn.commit()
    return cur.lastrowid


def insert_edge(conn, edge):
    cur = conn.execute(
        "INSERT INTO edges (type, from_component_id, to_component_id, group_key, "
        "status, resolver_version, created_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (edge.type, edge.from_component_id, edge.to_component_id, edge.group_key,
         edge.status, edge.resolver_version, now_iso(), edge.notes))
    conn.commit()
    edge.id = cur.lastrowid
    return edge.id


def insert_substitution_detail(conn, detail):
    conn.execute(
        "INSERT INTO edge_substitution_detail (edge_id, basis, verdict, source_text) "
        "VALUES (?, ?, ?, ?)",
        (detail.edge_id, detail.basis, detail.verdict, detail.source_text))
    conn.commit()


def insert_caveat(conn, caveat):
    cur = conn.execute(
        "INSERT INTO edge_caveat (edge_id, blocking, text, becomes_input) VALUES (?, ?, ?, ?)",
        (caveat.edge_id, int(caveat.blocking), caveat.text, caveat.becomes_input))
    conn.commit()
    caveat.id = cur.lastrowid
    return caveat.id


def insert_required_part(conn, part):
    cur = conn.execute(
        "INSERT INTO edge_required_part (edge_id, ns, value, role) VALUES (?, ?, ?, ?)",
        (part.edge_id, part.ns, part.value, part.role))
    conn.commit()
    part.id = cur.lastrowid
    return part.id


def insert_evidence(conn, evidence):
    cur = conn.execute(
        "INSERT INTO relationship_evidence (edge_id, event_type, effect_alpha, effect_beta, "
        "source_observation_id, actor_id, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evidence.edge_id, evidence.event_type, evidence.effect_alpha, evidence.effect_beta,
         evidence.source_observation_id, evidence.actor_id, evidence.occurred_at))
    conn.commit()
    evidence.id = cur.lastrowid
    return evidence.id


def get_edges_from(conn, component_id, type=None):
    if type:
        return conn.execute(
            "SELECT * FROM edges WHERE from_component_id = ? AND type = ?",
            (component_id, type)).fetchall()
    return conn.execute(
        "SELECT * FROM edges WHERE from_component_id = ?", (component_id,)).fetchall()


def get_evidence_for_edge(conn, edge_id):
    rows = conn.execute(
        "SELECT * FROM relationship_evidence WHERE edge_id = ?", (edge_id,)).fetchall()
    return [RelationshipEvidence(
        id=r["id"], edge_id=r["edge_id"], event_type=r["event_type"],
        effect_alpha=r["effect_alpha"], effect_beta=r["effect_beta"],
        source_observation_id=r["source_observation_id"], actor_id=r["actor_id"],
        occurred_at=r["occurred_at"]) for r in rows]


def get_caveats_for_edge(conn, edge_id):
    rows = conn.execute(
        "SELECT * FROM edge_caveat WHERE edge_id = ?", (edge_id,)).fetchall()
    return [EdgeCaveat(id=r["id"], edge_id=r["edge_id"], blocking=bool(r["blocking"]),
                        text=r["text"], becomes_input=r["becomes_input"]) for r in rows]


def self_test(verbose=False):
    conn = init_db(":memory:")
    failures = []

    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))

    edge = Edge(type="substitutes", from_component_id="c_test_a",
                to_component_id="c_test_b", group_key="412-0001")
    insert_edge(conn, edge)
    if edge.id is None:
        failures.append("insert_edge did not set edge.id")

    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge.id, basis="attribute_match_exact", verdict="drop_in"))
    insert_caveat(conn, EdgeCaveat(edge_id=edge.id, blocking=True, text="test caveat"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="attribute_prior", effect_alpha=3.0, effect_beta=1.0,
        occurred_at=now_iso()))

    fetched = get_edges_from(conn, "c_test_a", type="substitutes")
    if len(fetched) != 1:
        failures.append(f"expected 1 edge from c_test_a, got {len(fetched)}")

    ev = get_evidence_for_edge(conn, edge.id)
    if len(ev) != 1 or ev[0].effect_alpha != 3.0:
        failures.append(f"expected 1 evidence row with alpha=3.0, got {ev}")

    caveats = get_caveats_for_edge(conn, edge.id)
    if len(caveats) != 1 or caveats[0].text != "test caveat":
        failures.append(f"expected 1 caveat, got {caveats}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: full round trip through every insert/get function")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run the self-test**

Run: `cd Docs/Tools && python3 interchange_store.py --self-test --verbose`
Expected: `PASS: full round trip through every insert/get function`, `self_test: PASS`, exit 0.

- [x] **Step 3: Commit**

```bash
git add Docs/Tools/interchange_store.py
git commit -m "Add interchange_store.py: CRUD for components/edges/evidence"
```

---

### Task 4: `edge_resolver.py` — build the two anchor components from observations

**Files:**
- Create: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: `resolver.normalize_extracted(obs_id, extracted, strict=True) -> dict` (returns
  `{"attributes": {...}}`); `suburban_parser.parse_model(raw: str) -> dict`;
  `interchange_models.Component`, `interchange_models.Identifier`;
  `interchange_store.insert_component`, `interchange_store.insert_identifier`.
- Produces: `component_from_observation(obs_row: sqlite3.Row, component_id: str,
  part_type_id: int) -> tuple[Component, list[Identifier]]` — does not write to the DB,
  returns the objects for the caller to persist (keeps this function unit-testable without
  a live store).

- [x] **Step 1: Write the observation-loading half of `edge_resolver.py`**

```python
#!/usr/bin/env python3
"""
edge_resolver.py — observations.db -> components/edges, proven against the
fixture's canonical edge case (SW6DE/SW6DEL). See
docs/superpowers/plans/2026-07-31-edge-schema-resolver.md for scope: this
resolves the two best-documented anchor components and the asymmetric
substitution edge between them, not the full ten-component fixture.
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from resolver import normalize_extracted
from suburban_parser import parse_model, compare_models
from interchange_models import (
    Component, Identifier, Edge, EdgeSubstitutionDetail, EdgeCaveat,
    EdgeRequiredPart, RelationshipEvidence, prior_for_basis,
)
from interchange_schema import init_db
from interchange_store import (
    insert_component, insert_identifier, insert_edge, insert_substitution_detail,
    insert_caveat, insert_evidence, now_iso,
)

WATER_HEATER_PART_TYPE = 412


def component_from_observation(obs_row, component_id, part_type_id):
    """
    Build a Component + its Identifier rows from one observations.db row
    whose `extracted` blob has a `model` and `sku` field (the two anchor
    observations, #1 and #2, both do).
    """
    extracted = json.loads(obs_row["extracted"])
    normalized = normalize_extracted(obs_row["id"], extracted, strict=True)
    attrs = normalized["attributes"]

    model_raw = attrs.get("model")
    if not model_raw:
        raise ValueError(f"observation #{obs_row['id']} has no 'model' attribute")

    component = Component(component_id=component_id, part_type_id=part_type_id)
    identifiers = [Identifier(component_id, "suburban", model_raw, "exterior_plate")]

    # normalize_extracted accumulates same-canonical-key values into a list
    # when more than one raw key maps to `sku` (e.g. obs #1's `sku` field
    # PLUS its `aliases_mentioned` list both canonicalize to `sku`, giving
    # attrs["sku"] == ['5240A', '5140A']) - a plain string otherwise (obs #2
    # has only `sku`, giving attrs["sku"] == '5239A'). Confirmed by running
    # normalize_extracted directly against observations.db during plan
    # verification - do not assume it is always a scalar.
    sku = attrs.get("sku")
    sku_values = sku if isinstance(sku, list) else ([sku] if sku else [])
    for value in sku_values:
        identifiers.append(Identifier(component_id, "suburban", str(value), "none_marked"))
    return component, identifiers


def load_observation(obs_db_path, obs_id):
    conn = sqlite3.connect(obs_db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM observations WHERE id = ?", (obs_id,)).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"no observation #{obs_id} in {obs_db_path}")
    return row


def self_test(verbose=False):
    obs_db = str(Path(__file__).parent / "observations.db")
    failures = []

    obs1 = load_observation(obs_db, 1)  # SW6DEL
    obs2 = load_observation(obs_db, 2)  # SW6DE

    comp_6del, ids_6del = component_from_observation(
        obs1, "c_placeholder_wh_6del", WATER_HEATER_PART_TYPE)
    comp_6de, ids_6de = component_from_observation(
        obs2, "c_placeholder_wh_6de", WATER_HEATER_PART_TYPE)

    if comp_6del.component_id != "c_placeholder_wh_6del":
        failures.append("SW6DEL component_id mismatch")
    if not any(i.value == "SW6DEL" for i in ids_6del):
        failures.append(f"expected SW6DEL identifier, got {ids_6del}")
    if not any(i.value == "5240A" for i in ids_6del):
        failures.append(f"expected 5240A sku identifier, got {ids_6del}")
    if not any(i.value == "5140A" for i in ids_6del):
        failures.append(f"expected 5140A legacy-sku identifier (from aliases_mentioned "
                         f"canonicalizing into sku), got {ids_6del}")
    if not any(i.value == "SW6DE" for i in ids_6de):
        failures.append(f"expected SW6DE identifier, got {ids_6de}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: both anchor components built from observations #1 and #2")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run the self-test**

Run: `cd Docs/Tools && python3 edge_resolver.py --self-test --verbose`
Expected: `PASS: both anchor components built from observations #1 and #2`,
`self_test: PASS`, exit 0.

- [x] **Step 3: Commit**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "Add edge_resolver.py: build anchor components from observations #1/#2"
```

---

### Task 5: Derive the canonical substitution edge pair

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: `suburban_parser.compare_models(model_a: str, model_b: str) -> dict` (verdict,
  `a_to_b`/`b_to_a` dicts with `verdict` and optional `blocking_caveats: list[str]`);
  everything from Task 4.
- Produces: `resolve_substitution_pair(conn, model_a_id, model_a_raw, model_b_id,
  model_b_raw, group_key) -> tuple[int, int]` — writes two `Edge` rows (one per direction)
  plus their `edge_substitution_detail`, `edge_caveat`, and prior `relationship_evidence`
  rows, returns `(edge_a_to_b_id, edge_b_to_a_id)`.

- [x] **Step 1: Write the edge-derivation function and its test, appended to `edge_resolver.py`**

```python
def resolve_substitution_pair(conn, from_id, from_model, to_id, to_model, group_key):
    """
    Derive the two directed substitutes edges between from_id and to_id
    using suburban_parser.compare_models, and persist them (edges,
    edge_substitution_detail, edge_caveat, prior relationship_evidence).

    Returns (edge_from_to_id, edge_to_from_id).
    """
    cmp = compare_models(from_model, to_model)
    if cmp["verdict"] not in ("symmetric", "asymmetric"):
        raise ValueError(f"{from_model}/{to_model}: not a substitutable pair "
                          f"(verdict={cmp['verdict']}, reasons={cmp.get('reasons')})")

    basis = "attribute_match_exact"
    edge_ids = []
    for direction, src_id, dst_id, cmp_key in (
        ("a_to_b", from_id, to_id, "a_to_b"), ("b_to_a", to_id, from_id, "b_to_a"),
    ):
        verdict_info = cmp[cmp_key]
        edge = Edge(type="substitutes", from_component_id=src_id, to_component_id=dst_id,
                    group_key=group_key)
        insert_edge(conn, edge)

        insert_substitution_detail(conn, EdgeSubstitutionDetail(
            edge_id=edge.id, basis=basis, verdict=verdict_info["verdict"]))

        for caveat_text in verdict_info.get("blocking_caveats", []):
            insert_caveat(conn, EdgeCaveat(edge_id=edge.id, blocking=True, text=caveat_text))

        alpha, beta = prior_for_basis(basis)
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type="attribute_prior", effect_alpha=alpha,
            effect_beta=beta, occurred_at=now_iso()))

        edge_ids.append(edge.id)

    return tuple(edge_ids)
```

- [x] **Step 2: Extend `self_test()` to cover the edge derivation**

Add to `self_test()`, before the final `if failures:` block:

```python
    store_conn = init_db(":memory:")
    insert_component(store_conn, comp_6de)
    for ident in ids_6de:
        insert_identifier(store_conn, ident)
    insert_component(store_conn, comp_6del)
    for ident in ids_6del:
        insert_identifier(store_conn, ident)

    edge_de_to_del, edge_del_to_de = resolve_substitution_pair(
        store_conn, "c_placeholder_wh_6de", "SW6DE",
        "c_placeholder_wh_6del", "SW6DEL", "412-0087")

    de_to_del_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_de_to_del,)).fetchone()
    if de_to_del_detail["verdict"] != "drop_in":
        failures.append(f"SW6DE->SW6DEL should be drop_in, got {de_to_del_detail['verdict']}")

    del_to_de_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_del_to_de,)).fetchone()
    if del_to_de_detail["verdict"] != "fits_with_caveat":
        failures.append(
            f"SW6DEL->SW6DE should be fits_with_caveat, got {del_to_de_detail['verdict']}")

    del_to_de_caveats = get_caveats_for_edge(store_conn, edge_del_to_de)
    if len(del_to_de_caveats) != 1:
        failures.append(f"expected exactly 1 caveat SW6DEL->SW6DE, got {del_to_de_caveats}")

    evidence = get_evidence_for_edge(store_conn, edge_de_to_del)
    confidence = compute_confidence(evidence)
    if confidence["value"] != 0.75 or confidence["certainty"] != 4.0:
        failures.append(f"expected prior confidence 0.75/n=4, got {confidence}")
```

Add the two new imports at the top of `edge_resolver.py`:
```python
from interchange_models import compute_confidence
from interchange_store import get_caveats_for_edge, get_evidence_for_edge
```

- [x] **Step 3: Run the self-test**

Run: `cd Docs/Tools && python3 edge_resolver.py --self-test --verbose`
Expected: `PASS: both anchor components built from observations #1 and #2`,
`self_test: PASS`, exit 0. (The printed message stays the same; if you want a distinct
message for this expanded coverage, update the `if verbose:` print — either is fine as
long as it stays truthful about what was checked.)

- [x] **Step 4: Commit**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "Derive the canonical SW6DE/SW6DEL substitution edge pair"
```

---

### Task 6: `--check-fixture` — validate against `ground-truth.yaml`

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: `yaml.safe_load_all` (already a project dependency, see
  `suburban_parser.check_fixture`); everything from Tasks 4–5.
- Produces: `check_fixture(ground_truth_path: str, obs_db_path: str) -> int` (0 = match,
  1 = mismatch, printed diagnostics either way) and wires it into `main()` via
  `--check-fixture <path>`.

- [x] **Step 1: Write `check_fixture`, appended to `edge_resolver.py`**

```python
def _find_fixture_edge(edges_doc, a_id, b_id):
    for e in edges_doc:
        if e.get("type") == "substitutes" and e.get("a") == a_id and e.get("b") == b_id:
            return e
    return None


def check_fixture(ground_truth_path, obs_db_path):
    import yaml

    docs = [d for d in yaml.safe_load_all(open(ground_truth_path)) if d]
    edges_doc = next((d["edges"] for d in docs if isinstance(d, dict) and "edges" in d), [])
    fixture_edge = _find_fixture_edge(edges_doc, "c_placeholder_wh_6de",
                                       "c_placeholder_wh_6del")
    if fixture_edge is None:
        print("FAIL: ground-truth.yaml has no c_placeholder_wh_6de -> "
              "c_placeholder_wh_6del substitutes edge")
        return 1

    obs1 = load_observation(obs_db_path, 1)
    obs2 = load_observation(obs_db_path, 2)
    comp_6del, ids_6del = component_from_observation(
        obs1, "c_placeholder_wh_6del", WATER_HEATER_PART_TYPE)
    comp_6de, ids_6de = component_from_observation(
        obs2, "c_placeholder_wh_6de", WATER_HEATER_PART_TYPE)

    conn = init_db(":memory:")
    insert_component(conn, comp_6de)
    for ident in ids_6de:
        insert_identifier(conn, ident)
    insert_component(conn, comp_6del)
    for ident in ids_6del:
        insert_identifier(conn, ident)

    edge_de_to_del, edge_del_to_de = resolve_substitution_pair(
        conn, "c_placeholder_wh_6de", "SW6DE",
        "c_placeholder_wh_6del", "SW6DEL", "412-0087")

    mismatches = 0

    fixture_group = fixture_edge.get("group")
    resolved_group = conn.execute(
        "SELECT group_key FROM edges WHERE id = ?", (edge_de_to_del,)).fetchone()["group_key"]
    if fixture_group != resolved_group:
        print(f"MISMATCH group_key: fixture={fixture_group} resolved={resolved_group}")
        mismatches += 1

    for label, edge_id, fixture_key in (
        ("a_to_b", edge_de_to_del, "a_to_b"), ("b_to_a", edge_del_to_de, "b_to_a"),
    ):
        fixture_verdict = fixture_edge[fixture_key]["verdict"]
        resolved_verdict = conn.execute(
            "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
            (edge_id,)).fetchone()["verdict"]
        if fixture_verdict != resolved_verdict:
            print(f"MISMATCH {label} verdict: fixture={fixture_verdict} "
                  f"resolved={resolved_verdict}")
            mismatches += 1
        print(f"  {label}: verdict={resolved_verdict} (fixture={fixture_verdict})")

    fixture_conf = fixture_edge["confidence"]
    evidence = get_evidence_for_edge(conn, edge_de_to_del)
    resolved_conf = compute_confidence(evidence)
    if (resolved_conf["value"], resolved_conf["certainty"]) != \
            (fixture_conf["value"], fixture_conf["certainty"]):
        print(f"MISMATCH confidence: fixture={fixture_conf} resolved={resolved_conf}")
        mismatches += 1

    print(f"\n{mismatches} mismatches against ground-truth.yaml's canonical edge")
    return 1 if mismatches else 0
```

- [x] **Step 2: Wire `--check-fixture` into `main()`**

Replace the existing `main()` in `edge_resolver.py`:

```python
def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))
    if "--check-fixture" in sys.argv:
        idx = sys.argv.index("--check-fixture")
        fixture_path = sys.argv[idx + 1]
        obs_db = str(Path(__file__).parent / "observations.db")
        sys.exit(check_fixture(fixture_path, obs_db))
```

- [x] **Step 3: Run it against the real fixture**

Run: `cd Docs/Tools && python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml`
Expected: two `a_to_b`/`b_to_a` lines printed (verdicts matching fixture), then
`0 mismatches against ground-truth.yaml's canonical edge`, exit code 0.

- [x] **Step 4: Run the full self-test suite one more time to confirm nothing regressed**

Run: `cd Docs/Tools && python3 edge_resolver.py --self-test --verbose && python3 interchange_store.py --self-test && python3 interchange_models.py --self-test && python3 interchange_schema.py --self-test`
Expected: all four print `self_test: PASS` with exit code 0.

- [x] **Step 5: Commit**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "Add --check-fixture: resolver reproduces the canonical SW6DE/SW6DEL edge"
```

---

## Explicitly out of scope (tracked, not forgotten)

- The other nine fixture components (thermostat, monitor panel, roof vent, ceiling
  register, the IW60RL retrofit edges, the Atwood family placeholders) — same pattern,
  future plan(s).
- Opaque `component_id` generation (ULID-style, per ARCHITECTURE §2) — this plan hardcodes
  the fixture's placeholder strings; a real ID generator is separate work.
- `identifier_equivalence_candidate` population (currently the retailer-only
  AR7815/7330F3858 thermostat case; corrected by obs #43/#44 on 2026-08-01) —
  the table exists (Task 1) but nothing writes to it yet; needs the thermostat component
  first.
- Tiered search (EXACT/DROP-IN/FITS WITH ONE CHECK/PARTS FOR THIS UNIT) query logic per
  ARCHITECTURE §8 — this plan produces the rows that tiering would query, not the tiering
  logic itself.
