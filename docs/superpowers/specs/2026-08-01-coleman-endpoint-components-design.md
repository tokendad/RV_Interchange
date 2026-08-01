# Coleman Thermostat Endpoint Components Design

**Status:** approved for implementation
**Date:** 2026-08-01
**Scope:** resolve the three exact Coleman-Mach thermostat components named by the
manufacturer's current product page and 2025 aftermarket catalog, persist the two cataloged
supersession relationships, and preserve the retailer/manual visual match as candidate-only
research.

## 1. Goal

Extend the Coleman thermostat fixture from one in-hand component to the three independently
identified endpoints of the manufacturer's replacement statement:

| Component | Manufacturer description | Evidence boundary |
|---|---|---|
| `7330G3351` | analog, single-stage, heat/cool, white | exact manufacturer endpoint; distinct from photographed `7330G335` |
| `7330F3852` | analog, single-stage, heat/cool, black | exact manufacturer endpoint; distinct from retailer-only `7330F3858` |
| `9420-351` | analog, heat/cool, 12 VDC, black | current replacement named by the 2025 catalog |

The resolver will persist two directed `supersedes` edges:

```text
7330G3351 -> 9420-351
7330F3852 -> 9420-351
```

Direction follows the repository's replacement-chain convention: the retired component is
the `from_component_id`, and the current replacement is the `to_component_id`.

This milestone does not merge any of these components with the in-hand `AP7862` /
`7330G335` thermostat and does not create the older service manual's broader
interchangeability edges.

## 2. Evidence and trust boundaries

### Existing manufacturer observations

- Observation #40, the official Coleman-Mach analog thermostat page, independently names
  `7330G3351` and `7330F3852` and supplies their function and color under the analog
  single-stage product family.
- Observation #41, the official 2025 aftermarket catalog, independently names `9420-351`,
  describes it as analog Heat/Cool, 12 VDC, black, and states that it replaces
  `7330G3351` and `7330F3852`.
- Observation #42, the older RVP/Coleman catalog, supplies additional manufacturer catalog
  context for `7330G3351`, including 12 VDC and single-stage Heat/Cool.

These observations are sufficient to create the three endpoint components and two
manufacturer-supported supersession edges.

### New retailer observations

Append, without modifying existing observations:

1. The RV Products Shop `7330G3351` product page. Preserve its replacement narrative that
   `9420-351` retains function, wiring, mounting, and compatibility. Also preserve the
   internal conflict between the Heat/Cool title and the `Gas Furnace` specification row.
2. The RV Products Shop `7330F3852` product page. Preserve the equivalent replacement
   narrative and the conflict between the Heat/Cool title and the `Heat Pump,
   Heat Strip/Element` specification row.
3. The RV Products Shop `8330-3362` page and photograph as a visual-match candidate for the
   service manual's third, electronic-digital illustration.

All three remain `retailer_page` / Tier 7 evidence. Conflicting retailer specification
fields must not overwrite manufacturer attributes. The two replacement narratives may be
stored as lower-weight corroborating relationship evidence because each agrees with the
manufacturer's exact old-to-new endpoint pair.

### Visual candidate

The `8330-3362` product photograph closely matches the manual's third illustration: the
`RVComfort.HC` face, left display, adjacent up/down controls, and three lower slide controls
are all present. The manual does not print a model number next to the illustration, so this
is not exact identity evidence.

Persist the comparison only in `observations.db` using a classified
`visual_match_candidate` field with:

- candidate identifier `coleman:8330-3362`;
- comparison source observation #45;
- manual figure `electronic_digital_display_thermostat`;
- status `open`;
- an explicit note that visual similarity does not prove model identity.

Do not insert it into `identifier_equivalence_candidate`, because that table represents a
claim that two identifiers name the same physical component. Do not create a component or
edge from this visual candidate in this milestone.

## 3. Component representation

Create three independent fixture components with part type `415` and one exact `coleman`
identifier each:

| Fixture component ID | Identifier | Attributes persisted |
|---|---|---|
| `c_placeholder_tstat_7330g3351` | `7330G3351` | function `heat_cool`, color `white`, interface `analog`, stages `single`, voltage `12VDC` |
| `c_placeholder_tstat_7330f3852` | `7330F3852` | function `heat_cool`, color `black`, interface `analog`, stages `single` |
| `c_placeholder_tstat_9420_351` | `9420-351` | function `heat_cool`, color `black`, interface `analog`, voltage `12VDC` |

Every attribute is a typed `component_attributes` row with its exact source observation and
provenance. Do not infer `7330F3852` voltage from the replacement's voltage, and do not copy
the photographed in-hand terminal map onto any suffix-bearing model.

All three `interchange_code` values remain null. A manufacturer replacement statement is
enough to create a directed edge, but it is not by itself a reason to publish or allocate a
stable interchange number. Opaque production component IDs also remain outside this
fixture milestone.

## 4. Supersession representation

Add an `EdgeSupersessionDetail` model and store round-trip operations for the existing
`edge_supersession_detail` table. Each edge has:

- type `supersedes`;
- status `candidate`;
- group key `coleman_analog_heat_cool_12v`;
- a detail note quoting the relationship in paraphrase, not copying catalog prose;
- resolver version identifying this Coleman endpoint milestone.

Each edge begins with two evidence rows:

1. `attribute_prior`, Beta(1, 1), because critical terminal-level attributes are incomplete
   for the catalog endpoints;
2. `manufacturer_assertion`, effect alpha `+2`, beta `+0`, sourced to observation #41.

The corresponding retailer page may add one `retailer_cross_reference` evidence event with
effect alpha `+1`, beta `+0`. Retailer metadata conflicts remain recorded on the source
observation, but do not negate its exact replacement narrative. Confidence remains computed
from evidence rows and is never stored as a mutable score.

## 5. Resolver boundaries

Add two focused builders to `Docs/Tools/edge_resolver.py`:

```python
coleman_endpoint_components(product_row, replacement_row, legacy_row, component_ids)
    -> list[tuple[Component, list[Identifier], list[ComponentAttribute]]]

resolve_coleman_supersessions(conn, replacement_row, retailer_rows, component_ids)
    -> tuple[int, int]
```

The component builder validates the exact three-model set and rejects:

- normalization between `7330G335` and `7330G3351`;
- normalization between `7330F3852` and `7330F3858`;
- attributes sourced only from conflicting retailer specification blocks;
- a terminal map copied from observation #44/#45.

The edge builder validates the manufacturer relation exactly as
`[7330G3351, 7330F3852] -> 9420-351`, checks that all endpoint components already exist,
and rejects missing, extra, reversed, or self-referential endpoints.

## 6. Fixture and documentation changes

Extend `Docs/Inital_Design/ground-truth.yaml` with the three components, their qualified
attributes, and two directional supersession edges. Fixture comparison must verify:

- all three exact component identifiers and attribute provenance;
- exactly two Coleman thermostat supersession edges;
- old-to-current direction;
- detail rows and evidence sources/effects;
- no edge connecting any endpoint to `c_placeholder_tstat`;
- no `substitutes` edge generated from the service manual's unnamed illustrations;
- no component or edge generated from `8330-3362`.

Refresh the Coleman vendor status, staged-build plan, tool inventory, and README observation
count and milestone summary. The new source URLs are recorded without their transient
`srsltid` tracking query.

## 7. Testing and acceptance

Use the repository's inline red-green convention:

1. Vocabulary tests fail until retailer conflict and visual-candidate fields classify.
2. Model/store tests fail until supersession detail round trips.
3. Resolver tests fail until the three exact endpoints and both directed edges resolve.
4. Negative tests reject suffix normalization, reversed relations, and visual candidates
   promoted into the graph.
5. Fixture validation retains zero Suburban and in-hand thermostat mismatches and reaches
   zero endpoint/supersession mismatches.
6. Observation validation reports every key classified, no null source tiers, and database
   integrity `ok`.

Acceptance requires the derived graph to contain the three exact endpoint components and
two candidate supersession edges while the broader manual compatibility claim and
`8330-3362` visual match remain explicitly unresolved.

## 8. Out of scope

- Assigning exact model numbers to the manual's mechanical or electronic illustrations.
- Treating `8330-3362` as the proven digital illustration model.
- Importing the retailer's complete 31-product catalog.
- Resolving `AR7815` / `7330F3858` beyond their existing open identifier candidate.
- Merging `7330G3351` with photographed `7330G335`.
- Publishing interchange numbers or edge status.
- Building Stage 2 lookup or frontend functionality.
