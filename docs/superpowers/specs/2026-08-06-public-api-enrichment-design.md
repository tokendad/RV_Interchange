# Public API enrichment (interchange doc's "Phase 2") — design

**Date:** 2026-08-06
**Status:** approved, not yet implemented

## Context

`Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md` (§4) and the
companion `RV_Interchange_Public_Lookup_Recommendations.md` (§9, Phase 2) both call for
richer `/public/v1/search` and `/public/v1/replacements` responses than what shipped in
the phase-1 backend: manufacturer display name, part type, component attributes,
compatibility caveats, required additional parts, description, evidence summary, and
source references.

**Priority change (2026-08-06):** no Dealer API / Marketplace work is needed yet. The
near-term goal is a richer public-facing lookup site to start collecting public feedback,
so this enrichment work is promoted ahead of the Dealer API track. Both design docs were
updated in place to record this (`RV_Interchange_API_Design.md` new §0; the
recommendations doc's §18 and manufacturer-coverage copy).

This is unrelated to `2026-08-04-stage2-frontend-phase2-design.md` (the internal
admin/debug page work, already shipped) despite the "Phase 2" name collision — that spec
covers frontend tooling; this one covers the *Public API's* Phase 2 field additions named
in the architecture doc's own phasing.

## Scope for this round

In scope — real, already-modeled data with no query path today:
- Manufacturer display name (`identifiers.ns` → human name)
- Part type display name (`components.part_type_id` → human name)
- Component attributes (`component_attributes` table)
- Required additional parts (`edge_required_part` table)
- Structured caveats (`edge_caveat`, currently flattened into `ReplacementItem.summary`
  as a joined string — upgrade to a structured list)

Explicitly deferred — no backing data exists yet, or exposing it risks the "hidden from
public users" boundary (`RV_Interchange_API_Design.md` §10):
- Free-text component **description** — no such field exists in `components.db`.
- **Evidence summary** — `relationship_evidence` has only structured rows (`event_type`,
  `occurred_at`, `actor_id`, `source_observation_id`); no narrative text. A public-facing
  summary would have to be synthesized, and raw rows must never be exposed directly.
- **Source references** — provenance text lives in `observations.db`, not the derived
  `components.db` store; out of scope for this round.

## A. New registries (`Docs/Tools/`)

Both mirror the existing single-source-of-truth pattern in `edge_types.py` (a module the
resolver, serializers, and API all import from instead of each defining its own copy).

### `part_types.py`

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PartType:
    id: int
    display_name: str
    description: str = ""

# Bare int constants — moved here from edge_resolver.py. Existing call sites
# (Component(component_id, WATER_HEATER_PART_TYPE)) are unchanged, just re-imported.
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
    PartType(id=ATWOOD_PART_TYPE, display_name="Atwood Water Heater"),
    PartType(id=THERMOSTAT_PART_TYPE, display_name="Wall Thermostat"),
    PartType(id=SUBURBAN_FURNACE_PART_TYPE, display_name="Furnace"),
    PartType(id=SUBURBAN_FURNACE_REPAIR_PART_TYPE, display_name="Furnace Repair Part"),
    PartType(id=SUBURBAN_COOKTOP_PART_TYPE, display_name="Cooktop"),
    PartType(id=NORCOLD_REFRIGERATOR_PART_TYPE, display_name="Refrigerator"),
    PartType(id=NORCOLD_REPAIR_PART_TYPE, display_name="Refrigerator Repair Part"),
)

PART_TYPE_NAMES = {pt.id: pt.display_name for pt in PART_TYPES}
```

(Exact display-name wording TBD at implementation time — placeholders above convey shape,
not final copy.)

`edge_resolver.py` deletes its local `*_PART_TYPE` constant definitions and imports them
from `part_types.py` instead. Every other reference (`Component(component_id,
WATER_HEATER_PART_TYPE)`, etc.) is unchanged.

### `manufacturers.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Manufacturer:
    ns: str
    display_name: str

MANUFACTURERS = (
    Manufacturer(ns="suburban", display_name="Suburban"),
    Manufacturer(ns="coleman_mach", display_name="Coleman-Mach"),
    Manufacturer(ns="atwood", display_name="Atwood"),
    Manufacturer(ns="norcold", display_name="Norcold"),
)

MANUFACTURER_NAMES = {m.ns: m.display_name for m in MANUFACTURERS}
```

Not every `ns` in `identifiers` is a manufacturer namespace (e.g. `icm` in the phase-2
frontend spec looks like a component/subassembly namespace, not a vendor) — `services.py`
looks up `MANUFACTURER_NAMES.get(ns)` and treats a miss as "no manufacturer name to show,"
not an error.

## B. Schema changes (`interchange_schema.py`)

Add two tables:

```sql
CREATE TABLE IF NOT EXISTS part_types (
    id            INTEGER PRIMARY KEY,
    display_name  TEXT NOT NULL,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS manufacturers (
    ns            TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL
);
```

Both are seeded as a straight projection of `PART_TYPES` / `MANUFACTURERS` during
`edge_resolver.py --build`'s existing temp-db-then-swap rebuild (same path used for
`components`/`edges` today — see `edge_resolver.py` `~4537-4557`), not hand-inserted.
These tables exist for self-description / future SQL consumers; `api/services.py` reads
the registries' Python dicts directly rather than querying these tables (matching how
`edge_types.py` constants are already imported directly, not read back from the DB).

## C. Sync tests

`tests/tools/test_part_types.py` and `tests/tools/test_manufacturers.py`, mirroring
`tests/tools/test_edge_types.py`: reflect over `edge_resolver.py`'s module globals for
`*_PART_TYPE` names, assert every one has a matching `PART_TYPES` entry and vice versa;
assert the seeded `part_types`/`manufacturers` tables (after a `--build` run against the
test fixture) match the registry tuples exactly.

## D. Store layer (`interchange_store.py`)

Two new read helpers, following the existing `get_caveats_for_edge` /
`get_evidence_for_edge` pattern:

```python
def get_attributes_for_component(conn, component_id):
    # SELECT name, qualifier, value_text, value_number, value_boolean, unit
    # FROM component_attributes WHERE component_id = ?
    # Never selects provenance or source_observation_id (internal-only).

def get_required_parts_for_edge(conn, edge_id):
    # SELECT ns, value, role FROM edge_required_part WHERE edge_id = ?
```

## E. Service layer (`api/services.py`)

- `IdentifierService.resolve` and `SearchService.search` add `manufacturer` (via
  `MANUFACTURER_NAMES.get(ns)` on the resolved/matched identifier's `ns`), `part_type`
  (via `PART_TYPE_NAMES.get(component.part_type_id)`), and `attributes` (via
  `get_attributes_for_component`, formatted as a list of `{name, qualifier, value, unit}`
  — `value` collapses whichever of `value_text`/`value_number`/`value_boolean` is set,
  matching the schema's existing exactly-one-set CHECK constraint).
- `ReplacementService.get_replacements`: each `ReplacementItem` gains `required_parts`
  (via `get_required_parts_for_edge`, formatted as `{ns, value, role, manufacturer}` using
  the same `MANUFACTURER_NAMES` lookup) and a structured `caveats: list[{text, blocking}]`
  replacing the current flattened `summary` string. The "Exact Match" synthetic entry
  (`rank: 1`, no backing edge) gets empty `required_parts`/`caveats`, same as its current
  `summary: None`.

## F. Response schema (`api/schemas.py`)

```python
class AttributeOut(BaseModel):
    name: str
    qualifier: str = ""
    value: str | float | bool
    unit: Optional[str] = None

class RequiredPartOut(BaseModel):
    ns: str
    value: str
    role: Optional[str] = None
    manufacturer: Optional[str] = None

class CaveatOut(BaseModel):
    text: str
    blocking: bool

class SearchResultItem(BaseModel):
    component_id: str
    label: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []

class ResolveResponse(BaseModel):
    component_id: str
    manufacturer: Optional[str] = None
    part_type: Optional[str] = None
    identifiers: list[IdentifierOut]
    attributes: list[AttributeOut] = []

class ReplacementItem(BaseModel):
    part: str
    fit: str
    rank: int
    required_parts: list[RequiredPartOut] = []
    caveats: list[CaveatOut] = []
    # `summary: Optional[str]` removed — replaced by structured `caveats`.
```

**Breaking change note:** removing `ReplacementItem.summary` in favor of `caveats` breaks
the current `web/app.js` (`renderDetail` reads `item.summary`). That frontend update rides
along with this backend change — `app.js` switches to rendering the `caveats` list — since
there is exactly one caller of this API today (the phase-1 test website) and no external
consumers to keep the old field alive for.

## Explicitly out of scope for this round

- Dealer API, authentication, Marketplace — deferred per the priority-change note above.
- Description, evidence summary, source references — no backing data (see Scope section).
- `/public/v1/compare`, `/public/v1/interchange/{code}`, `/public/v1/components/{id}` —
  still not built; not required for this enrichment.
- A `categories.py` grouping layer over `part_types.py` — raised and explicitly cut during
  design; revisit only if a real grouping need shows up.

## Testing

- `tests/tools/test_part_types.py`, `tests/tools/test_manufacturers.py` (new, per §C).
- `tests/tools/test_interchange_store.py`: coverage for the two new read helpers (§D) —
  empty case, multiple rows, correct exclusion of `provenance`/`source_observation_id`.
- `tests/api/test_services.py`: `manufacturer`/`part_type`/`attributes` present on search
  and resolve results; `required_parts`/`caveats` present and correctly structured on
  replacements; unknown `ns` (no manufacturer match) degrades to `None` rather than
  erroring.
- `tests/api/test_e2e.py`: end-to-end response-shape assertions for the new fields against
  the existing fixture data.
- `web/app.js` manual re-verification against the running Docker stack once `caveats`
  replaces `summary`, per the existing manual-verification precedent for this frontend
  (no test framework introduced for it, consistent with `2026-08-04-stage2-frontend-
  phase2-design.md`).
