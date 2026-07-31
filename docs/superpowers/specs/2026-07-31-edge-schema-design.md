# Edge schema design — RV Interchange Stage 1

**Status:** approved, ready for implementation planning
**Date:** 2026-07-31
**Scope:** the edge (relationship) side of the observations→components/edges resolver.
`components` and `identifiers` are assumed to exist roughly as
`Docs/Inital_Design/ground-truth.yaml` already implies (`component_id`, `part_type_id`,
`interchange_code`, `identifiers{ns,value,visibility}`, `attributes{value,provenance,...}`) —
not redesigned here.

Related: `Docs/Inital_Design/ARCHITECTURE-Interchange_Core.md` §4 (edge vocabulary), §7
(confidence scoring), §9 (two-table persistence, rebuildable-from-source).

---

## 1. Storage target

Persisted as SQLite tables (same engine/style as `Docs/Tools/observations.db`), with Python
dataclasses as the resolver's in-memory working model before serialization.

**Why:** the project's stated end-state (`PLAN-Staged_Build.md`) is hundreds to thousands of
components plus a Stage 3 marketplace consuming this data directly. Tiered search (EXACT →
DROP-IN → FITS WITH ONE CHECK → PARTS FOR THIS UNIT) needs indexed, queryable lookups by
identifier/namespace — a JSON-file rebuild-and-scan approach doesn't hold up past a few
hundred components. Dataclasses stay valuable as the resolver's testable intermediate
representation (same pattern `suburban_parser.py` already uses), diffable directly against
`ground-truth.yaml` in tests, before a thin serializer writes them to SQLite. SQLite can
migrate to Postgres later without a schema rethink if concurrent writes or scale demand it.

## 2. Table list

```
edges                            -- shared core, one row per directed relationship
edge_substitution_detail         -- substitutes: confidence-bearing, directional
edge_caveat                      -- child of edge_substitution_detail
edge_required_part               -- child of edge_substitution_detail
edge_contains_detail             -- contains: parent component -> child part (ns/value/role)
edge_supersession_detail         -- supersedes: replacement chains
edge_controls_detail             -- controls: switch/thermostat -> appliance
edge_requires_system_detail      -- requires_system: needs matching harness/sensor
edge_shared_subassembly_detail   -- shares_subassembly: partial overlap
edge_aftermarket_replaces_detail -- lower-trust directional
relationship_evidence            -- append-only, drives confidence for edges
identifier_equivalence_candidate -- pre-merge "these might be the same part"
identifier_equivalence_evidence  -- same evidence pattern, scoped to the candidate above
```

## 3. Why shared-core-plus-typed-detail, not one wide table or one JSON blob

The edge vocabulary (ARCHITECTURE §4) has eight types with genuinely different required
fields — `substitutes` needs confidence, basis, and directional verdict/caveats;
`contains` needs an assembly role; `controls` needs almost nothing; `alias` links
identifiers, not components. A single wide table drowns most rows in nulls. A single JSON
detail column keeps required compatibility semantics outside SQL's reach (no indexing, no
`WHERE` on confidence without JSON1 extension functions) — JSON is fine for uncommon
vendor-specific extensions, not for load-bearing fields like confidence or verdict.

A generic `relationship`/`relationship_endpoint` fully-normalized join layer was considered
and rejected: every edge type here has a fixed, small number of named endpoint roles
(substitutes: from/to component; controls: controller/appliance; contains: parent
component / child identifier+role). Plain `from_component_id`/`to_component_id`-style
columns on each typed table are simpler and equally capable without the extra join — the
generic endpoint table would only pay for itself if a relationship type needed an
unbounded number of members, and none here do (see §6 on why `alias` doesn't count).

## 4. `edges` (shared core)

```
edges
  id                   -- opaque PK
  type                 -- substitutes | contains | supersedes | controls |
                          requires_system | shares_subassembly | aftermarket_replaces
  from_component_id     FK -> components
  to_component_id       FK -> components   -- nullable for contains (child may be an
                                              unresolved ns/value, not a component yet)
  group_key            -- e.g. "412-0087", "iw60_retrofit_suburban_6gal" — the
                          cross-capacity/retrofit grouping key seen in the fixture
  status               -- candidate | published | retired | merged_into:<edge_id>
  resolver_version     -- which resolver run produced this row (rebuild lineage)
  created_at, retired_at
  notes
```

`from`/`to` rather than `a`/`b`: substitution is one row per direction (§5), so "from/to"
reads correctly without a separate `direction` flag. For symmetric types
(`shares_subassembly`) `from`/`to` is an arbitrary but consistent ordering, not a claim of
directionality.

`status` mirrors ARCHITECTURE §2's candidate-vs-published distinction for the
`interchange_code` itself, applied to individual edges: an edge can sit at CANDIDATE
confidence indefinitely without being published, and publication is a separate decision
from crossing a confidence threshold.

## 5. `edge_substitution_detail` — the one with real complexity

```
edge_substitution_detail
  edge_id              FK -> edges (1:1)
  basis                -- attribute_match_exact | buyer_confirmed_install |
                          manufacturer_documented | retailer_cross_reference
  verdict              -- drop_in | fits_with_caveat | fits_with_modification | not_observed
  source_text          -- free text provenance (obs #14, review excerpt, etc.)
```

Confidence (`alpha`/`beta`) is deliberately **not** a column here — see §7. `SW6DE→SW6DEL`
and `SW6DEL→SW6DE` are two separate `edges` rows, each with its own
`edge_substitution_detail` row, each accumulating evidence independently. This reproduces
the fixture's asymmetric `a_to_b`/`b_to_a` case (the SW6DE/SW6DEL pair) without a
dual-verdict blob on one row, and generalizes cleanly to cases where evidence differs by
direction (e.g. a confirmed install one way, nothing observed the other way, as with the
IW60RL retrofit edges).

Caveats live in a child table rather than inline JSON, since they're structurally uniform
across every substitution edge and worth querying directly (e.g. "show all blocking
caveats mentioning cutout"):

```
edge_caveat
  id
  edge_id               FK -> edges
  blocking              -- bool
  text
  becomes_input         -- nullable; the follow-up question text, e.g.
                           "Do you have an interior electric switch? [yes/no]"
```

A required part (the fixture's `requires_part` field, e.g. `suburban/6276APW` for the
IW60RL retrofit) is likewise a child table rather than a nullable pair of columns on
`edge_substitution_detail` — most substitution edges require no extra part, and some
retrofits need more than one (obs #14's IW60RL case already implies a replacement panel
*and* a separately-ordered vent cap, surfaced today only as caveat text):

```
edge_required_part
  id
  edge_id               FK -> edges
  ns, value
  role                  -- e.g. replacement_panel, vent_cap, gasket_kit
```

## 6. Other typed detail tables — thin, one row each

- `edge_contains_detail`: `edge_id, child_ns, child_value, role, assembly_level`
- `edge_controls_detail`: `edge_id, note`
- `edge_requires_system_detail`: `edge_id, system_name` (e.g. `kib_sensor_protocol`)
- `edge_supersession_detail`, `edge_shared_subassembly_detail`,
  `edge_aftermarket_replaces_detail`: `edge_id, note` plus whatever narrow field each turns
  out to need. No fixture case exercises these deeply yet — keep them minimal and let real
  data grow them, per ARCHITECTURE §6's "do not design the taxonomy in advance" principle,
  applied here to edge detail rather than part-type taxonomy.

## 7. `relationship_evidence` — append-only, drives confidence

```
relationship_evidence
  id
  edge_id               FK -> edges
  event_type            -- attribute_prior | buyer_confirmed_install |
                           teardown_co_occurrence | manufacturer_assertion |
                           retailer_cross_reference | fitment_failure | return_dispute
  effect_alpha, effect_beta
  source_observation_id  FK -> observations, nullable
  actor_id              -- for the "cap per actor" rule; nullable, e.g. reviewer/forum
                           handle
  occurred_at
```

Confidence is never a stored, mutable field anywhere in the schema — it is always
`prior + Σ(effects)`, computed on read (or via a materialized view later if performance
demands it). This matches ARCHITECTURE §9's rebuildable-from-source principle applied one
level up: `components`/`edges` are rebuildable from `observations`, and confidence is
rebuildable from `relationship_evidence` the same way. It also directly supports rules that
a mutable counter can't: capping evidence per source and per actor requires seeing the full
event list, not just a running total; decay-toward-prior over time requires knowing *when*
each event happened, not just its cumulative effect.

The prior itself (`Beta(3,1)` / `Beta(2,1)` / `Beta(1,1)` per ARCHITECTURE §7's match-quality
table) is inserted as the first evidence row for an edge, `event_type = attribute_prior`,
rather than a special-cased column — so "confidence = prior + Σevents" is one uniform query
with no branching on row type. Manufacturer-assertion capping ("+2, capped, once") and
per-actor capping are enforced by the resolver at insert time, not by a DB constraint —
consistent with how `observations.py` keeps insert-side validation in application code
rather than triggers.

## 8. `identifier_equivalence_candidate` — replaces the `alias` edge type

```
identifier_equivalence_candidate
  id
  ns_a, value_a
  ns_b, value_b
  status                -- open | merged (into one component_id) | rejected
  merged_component_id    FK -> components, nullable until merged
```

Plus `identifier_equivalence_evidence`, same shape as `relationship_evidence` (§7) but
scoped to this table instead of `edges`.

**Why `alias` isn't an edge type at all:** the `identifiers` table already lets one
`component_id` carry multiple `{ns, value}` rows — that's how `SW6DEL`/`5240A`/`5140A`
coexist today as confirmed facts about one component. A separate `alias` *edge* only makes
sense for the case where two identifiers are *suspected* to be the same real part but
haven't been merged into one `component_id` yet — the thermostat case in the fixture
(`AP7862-3`/`AR7815`, a retailer selling them as two separate products at different prices).
That's pre-resolution evidence, not a post-resolution fact, so it belongs in its own
small table rather than the edge system: it starts as an open candidate with
retailer-cross-reference evidence, and only becomes plain rows in `identifiers` once (or
if) it's promoted to `merged`. This also directly answers "is a two-endpoint model enough
for every edge type" (§3) — once `alias` is out, nothing left needs more than two named
endpoint roles.

## 9. Reproducing the fixture's acceptance test

Re-deriving `SW6DEL`'s tiers (ARCHITECTURE §8) becomes:

1. **EXACT** — exact match on `identifiers`.
2. **DROP-IN / FITS WITH ONE CHECK** — `edges WHERE type='substitutes' AND
   from_component_id = <SW6DEL>`, join `edge_substitution_detail` for verdict/caveats,
   join `relationship_evidence` grouped by `edge_id` for the tier math (n≥8 & mean>0.90,
   etc.).
3. **PARTS FOR THIS UNIT** — `edges WHERE type IN ('contains','controls') AND
   to_component_id = <SW6DEL>` (or `from_component_id`, depending on the relationship's
   natural direction, e.g. the interior switch `controls` edge).

No JSON parsing appears anywhere in the query path.

## 10. Open items deferred, not designed here

- `supersedes`, `shares_subassembly`, `aftermarket_replaces` detail tables are stubbed
  minimally (§6) — no fixture case exercises them enough to design further yet.
- Tolerance-band matching, the clustering algorithm/distance function, and confidence
  decay half-life remain open per ARCHITECTURE §11 — this schema stores what those need
  (raw evidence events, timestamps) but does not implement them.
- The channel-qualifier addition to the identifier schema (5148A/5248A
  manufacturer-vs-distributor split, `PLAN-Staged_Build.md` item 11) is a separate,
  already-tracked change to `identifiers`, out of scope here.
