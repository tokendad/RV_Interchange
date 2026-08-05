# Suburban Furnace & Cooktop Extension Design

**Status:** approved, not yet implemented
**Date:** 2026-08-05
**Scope:** extend the existing Suburban vendor arc with two new part types (furnace,
cooktop/range) and three components, sourced from in-hand data-plate photographs of the
owner's current coach plus one corroborating page from the 2025 Suburban catalog.

## 1. Goal

The owner's current RV (a 2013(?) SPREE 322BHS) carries a Suburban furnace and a Suburban
cooktop/range, photographed in-hand on 2026-08-05 alongside the Norcold refrigerator that
opens the 4th Stage 1 vendor arc (separate design). This document covers only the Suburban
side: extending the existing vendor arc (Suburban is already Stage 1 vendor #1, via the
SW-series water heaters) with two part types it has never covered before.

| Component | Identity source | Evidence boundary |
|---|---|---|
| `SF-30FQ` furnace | in-hand data plate photo | exact, high trust (dataplate_photo tier) |
| `2608A` furnace core replacement module | 2025 Suburban catalog (`Catalogue_2025.pdf`) | exact, manufacturer catalog; states it fits both `SF-25FQ` and `SF-30FQ` |
| `SRNA3SBBM` cooktop/range | in-hand data plate photo | exact, high trust (dataplate_photo tier) |

The resolver will persist one `fits` edge:

```text
2608A -> SF-30FQ
```

`SF-25FQ` is named by the same catalog row but is not itself being built as a component in
this milestone (no in-hand unit, no other evidence) — the `2608A` component's `fits_bracket`
shape allows a second `fits` edge to be added later without rework if `SF-25FQ` is ever
independently evidenced.

## 2. Evidence and trust boundaries

### New in-hand observations

1. Furnace data plate photograph (`Docs/Data/Current RV - DO NOT COMMIT THIS FOLDER/Furnace/20260805_124128.jpg` — gitignored, not committed): `Model No. SF-30FQ`, `Stock No. 2391`, `Serial No. 122103492`. `source_type: dataplate_photo`, `extraction_method: hand_typed` → tier 2.
2. Cooktop data plate photograph (`.../Stove/20260805_124807.jpg`): `Model No. SRNA3SBBM`, `Serial No. 122109479`, `Stock No. 2863`, full burner-rate spec block (Front 9,000 BTU, Left Rear 6,500 BTU, Right Rear 6,500 BTU, Oven 7,100 BTU, Manifold Pressure 10.0" W.C.). Same tier.
3. Cooktop shutdown/lighting/clearance plate photograph (`.../Stove/20260805_124815.jpg`): clearance-to-combustible dimensions (0" below counter, 6"/6"/9" sides/left/back, 24" vertical over cooktop), `AIRXCEL` logo confirming current corporate parent, UL listing `82E7`. Same tier — a second photo of the same physical unit, not independent corroboration.

### Existing manufacturer observation (catalog)

4. `Docs/Data/Suburban/Catalogue_2025.pdf`, "FURNACE CORE REPLACEMENT MODULES" section: `FOR SF-25FQ / SF-30FQ ORDER 2608A`. `source_type: manufacturer_pdf`, extracted via `pdftotext -layout` (real text layer, not OCR) → tier 1.

These four observations are sufficient to create three components and one `fits` edge.

### Explicitly not asserted (see issues #25, #26)

- No cutout/cabinet dimensions for either the furnace or the cooktop — not published in the
  2025 catalog, and cooktops are absent from the current catalog's lineup entirely. Tracked
  as issue #25.
- No `supersedes` edge from `SF-30FQ` to the current-catalog `SF-30VHFQ`. The catalog shows
  `SF-30FQ` is absent from the current lineup and still serviceable via `2608A`, but does not
  state a direct replacement relationship the way the Coleman-Mach catalog does for
  thermostats (e.g. obs #94's explicit `REPLACES` table). Tracked as issue #26.
- No letter-by-letter grammar claims for either model number, consistent with the existing
  `VENDOR-Suburban-Furnace_Cooktop.md` preliminary research, which flagged the furnace/cooktop
  breakdown charts as screenshot-transcribed and not fixture-ready. This milestone does not
  change that document's trust boundary — it adds two components identified by their own
  in-hand markings, independent of the grammar question.

## 3. Part-type taxonomy additions

Following the existing loose block convention (`ARCHITECTURE-Interchange_Core.md` §6) and the
`412`/`413` water-heater/repair-part pairing precedent:

```yaml
- id: 416
  label: furnace
  compat_mode: attribute
  critical_attributes: [btu_rating, ignition_type]
  secondary_attributes: []
  tags: [climate, lp_gas, appliance]
  pcdb_term_id: null
  # No cutout/cabinet dimensions yet -- see issue #25. critical_attributes
  # intentionally excludes them until a source exists; do not backfill guesses.

- id: 417
  label: furnace repair/service part
  compat_mode: fits_bracket
  critical_attributes: [description]
  tags: [climate, lp_gas, appliance, repair_part]
  pcdb_term_id: null
  # Mirrors 413 (water heater repair/service part) for the furnace host category.

- id: 601
  label: cooktop/range
  compat_mode: attribute
  critical_attributes: [burner_count, btu_rating]
  secondary_attributes: [oven_btu_rating, manifold_pressure_wc]
  tags: [appliance, lp_gas]
  pcdb_term_id: null
  # No cutout dimensions yet -- see issue #25.
```

`416`/`417` land in the existing "climate" block (`400s`) alongside `412`/`413`/`415`. `601`
opens the "appliances" block (`600s`), the first part type assigned there.

## 4. Component representation

```yaml
- component_id: c_placeholder_furnace_sf30fq
  part_type_id: 416
  identifiers:
    - {ns: suburban, value: SF-30FQ, visibility: dataplate}
  attributes:
    btu_rating: 30000       # from model number "30" and catalog family naming; not
                             # independently confirmed by a printed BTU figure on this
                             # unit's plate -- flag provenance as inferred, not read.
    stock_no: "2391"         # secondary, not critical_attributes
    serial: "122103492"

- component_id: c_placeholder_furnace_part_2608a
  part_type_id: 417
  identifiers:
    - {ns: suburban, value: "2608A", visibility: catalog}
  attributes:
    description: "Furnace Core Replacement Module"
  edges:
    - {type: fits, to: c_placeholder_furnace_sf30fq, group_key: suburban_furnace_core_module}

- component_id: c_placeholder_cooktop_srna3sbbm
  part_type_id: 601
  identifiers:
    - {ns: suburban, value: SRNA3SBBM, visibility: dataplate}
  attributes:
    burner_count: 3
    btu_rating: 9000          # front burner, the highest-rated of the three
    oven_btu_rating: 7100
    manifold_pressure_wc: 10.0
    stock_no: "2863"
    serial: "122109479"
```

The furnace's `btu_rating: 30000` is a judgment call worth flagging explicitly in the
resolver docstring: the model number's `30` and the catalog's parallel `SF-30VHFQ,
30,000 BTU/h` listing both support it, but this unit's own plate does not print a BTU figure
the way the cooktop's plate does. Store it with `source_type: inferred_from_model_family`,
not `dataplate_photo`, so its provenance is honest.

`ignition_type` is listed in `416`'s `critical_attributes` (it matters for the type generally
— e.g. distinguishing pilot from direct-spark furnaces) but is deliberately left unpopulated
on `SF-30FQ` in this milestone: the catalog describes the *current* `VH`-series as direct
spark ignition, but does not state that the legacy pre-`VH` `SF-30FQ` shares it, and no other
source does either. Do not infer it from the current series the way `btu_rating` was
inferred from the model number — BTU rating is encoded directly in the number itself
(`SF-30...` / `30,000 BTU/h` is the same pattern across both eras), ignition method is not.

`interchange_code` stays null for all three, consistent with the Coleman endpoint
precedent (§3 of that design): a real component identity does not by itself justify
allocating a stable interchange number.

## 5. Edge representation

One `fits` edge, built the same way as `atwood_repair_parts_and_fits()`
(`Docs/Tools/edge_resolver.py:1102`) — generic `edges` row plus `relationship_evidence`,
no dedicated detail table:

- type `fits`
- `from_component_id`: `2608A`, `to_component_id`: `SF-30FQ`
- group key `suburban_furnace_core_module`
- status `candidate`
- evidence: `attribute_prior` Beta(1,1), then `manufacturer_assertion` effect alpha `+2`
  beta `+0`, sourced to the catalog observation

## 6. Resolver boundaries

Add one focused builder to `Docs/Tools/edge_resolver.py`, mirroring
`atwood_repair_parts_and_fits()`'s shape but scoped to a single part (no bulk table):

```python
suburban_furnace_and_core_module(conn, furnace_dataplate_row, cooktop_dataplate_row,
                                  cooktop_clearance_row, catalog_row) \
    -> list[tuple[Component, list[Identifier], list[ComponentAttribute], list[edge_id]]]
```

Validates:

- the furnace/cooktop dataplate observations carry `source_type: dataplate_photo`;
- the catalog observation's `manufacturer_pdf` text explicitly names both `SF-25FQ` and
  `SF-30FQ` on the `2608A` row (reject if only one model or a different module number
  appears — protects against a future catalog edition silently changing this);
- no cutout/cabinet dimension attributes are written for either endpoint (guards issue #25's
  boundary — this should raise, not silently omit, if someone tries to add one without
  updating this design);
- no `supersedes` edge is created toward `SF-30VHFQ` (guards issue #26's boundary the same
  way the Coleman endpoint resolver rejects an unnamed supersession).

## 7. Fixture and documentation changes

Extend `Docs/Inital_Design/ground-truth.yaml` with the three components, their attributes,
and the one `fits` edge. Fixture comparison must verify:

- both exact component identifiers and the repair-part identifier;
- exactly one `fits` edge, correct direction (`2608A -> SF-30FQ`);
- the furnace's `btu_rating` attribute carries `inferred_from_model_family` provenance, not
  `dataplate_photo`;
- no cutout/cabinet dimension attributes present on either endpoint;
- no edge of type `supersedes` touching `SF-30FQ`.

Update `Docs/Data/Suburban/VENDOR-Suburban-Furnace_Cooktop.md` to record that the furnace and
cooktop now each have one exact in-hand endpoint component, while explicitly keeping its
existing "NOT fixture-ready" grammar-decoding sections unchanged (this milestone adds
identity, not grammar). Update `Docs/Data/Suburban/VENDOR-Suburban.md`'s status summary and
the README's Suburban status bullet.

## 8. Testing and acceptance

1. Resolver tests reject a catalog row missing either `SF-25FQ` or `SF-30FQ` from the
   `2608A` line.
2. Resolver tests reject any attempt to attach a cutout/cabinet dimension or a `supersedes`
   edge from this builder.
3. Fixture validation reaches zero mismatches for the two new endpoints and the one `fits`
   edge, with existing Suburban/Coleman/Atwood mismatch counts unchanged.
4. `python3 -m pytest tests/ Docs/Tools` stays green.

Acceptance requires the derived graph to contain `SF-30FQ`, `SRNA3SBBM`, and `2608A` with
their in-hand attributes, one `fits` edge, and no dimensional or supersession claims beyond
what's evidenced.

## 9. Out of scope

- Cutout/cabinet dimensions for either part type (issue #25).
- Any `supersedes` claim toward `SF-30VHFQ` (issue #26).
- Resolving the furnace/cooktop model-number grammar letter-by-letter (existing open item in
  `VENDOR-Suburban-Furnace_Cooktop.md`).
- The Coleman-Mach `8330A733` rooftop AC and the High Pointe `EM925RCW` microwave found in
  the same photo pass (issues #23, #24) — separate vendor-research items, not part of this
  extension.
- The Norcold `N811RT` 4th-vendor arc — separate design, next after this one.
