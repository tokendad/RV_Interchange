# Suburban Furnace & Cooktop Extension Design

**Status:** approved, not yet implemented
**Date:** 2026-08-05 (revised same day: furnace and cooktop manufacturer manuals located,
confirmed by the owner as matching the in-hand units, resolving issue #25's cutout/clearance
dimension gap)
**Scope:** extend the existing Suburban vendor arc with two new part types (furnace,
cooktop/range) and three components, sourced from in-hand data-plate photographs of the
owner's current coach, matching manufacturer installation manuals for both appliances, and
one corroborating page from the 2025 Suburban catalog.

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

### New manufacturer manual observations (resolve issue #25)

5. `Docs/Data/Suburban/Furnace/installation-manual - Matches Current Owner.pdf` — "SUBURBAN GAS FURNACES INSTALLATION INSTRUCTIONS FOR SF-20FQ • SF-25FQ • SF-30FQ • SF-35FQ • SF-42FQ", Part Number 205170 — a manufacturer installation manual naming `SF-30FQ` explicitly, confirmed by the owner as matching the in-hand unit. `source_type: manufacturer_pdf`, `pdftotext -layout` → tier 1. Two dimensional facts, both model-row-specific to `SF-30FQ`:
   - **Table 2 (clearance to combustible construction), `SF-30FQ` row:** Front 1", Left Side 0", Right Side 0", Top 0", Bottom 0", Back 0", Exhaust and Intake Tube 3/8".
   - **Cabinet/inner-wall cutout** (installation method A — furnace installed directly against the outer skin, "X" dimension 0"–1-1/2"): "Cut an opening through the inner wall 17-3/4 x 8"." This dimension is stated once for the SF-FQ family in the manual text (not broken out per model the way Table 2 is) — record it as family-level, not confirmed `SF-30FQ`-specific beyond the family membership itself, and note it applies to installation method A specifically; method B (not against outer skin) uses a charted "X"-dependent tube length instead of a fixed cabinet cutout.
6. `Docs/Data/Suburban/Cooktop/Suburban Range.pdf` — "RECREATIONAL VEHICLE RANGE AND COOKTOPS INSTALLATION, OPERATION AND SERVICE MANUAL for All SRNA3 and SRSA3 Model Variations (Short and Long Oven)...", confirmed by the owner as matching the in-hand unit. Same tier. Two dimensional facts, both from the `SRNA3S`/`SRSA3S` ("Short" oven) row, which matches `SRNA3SBBM`'s `SRNA3S` prefix:
   - **Clearance table**, `SRNA3`/`SRSA3` row: Below Counter 0", Right Sidewall 6", Left Sidewall 6", Backwall 9" — matches the in-hand plate photo (observation 3) exactly, corroborating both sources.
   - **Cut-out dimensions (Figure 2), `SRNA3S`/`SRSA3S` row:** A 18-5/8", B 16", C 2", D 20-5/8", E 7/8" (the manual's Figure 2 labels these letters against a diagram not extracted here — recorded as five labeled dimensions, not further interpreted).
   - Minimum vertical clearance to combustible material above the cooktop: 24" (also matches the in-hand plate), reducible to 19-1/2" with a range hood installed 1/4" off the construction.

### New retailer observation (corroborates the `2608A` fits edge, resolves issue #26)

7. `unitedrvparts.com`'s `SF-30FQ` product page: OEM numbers `2518A`/`2391A`/`2558A` — `2391A`
   matches the in-hand unit's own `Stock No. 2391` exactly, confirming this retailer's listing
   covers our specific unit. Its own crossover chart independently states `SF-30FQ | 2391 |
   Stock# 2608A, Model# RP-30FQ` — a second, independent source for the `2608A` fits edge
   (previously sourced only to the manufacturer catalog), plus the core module's own model
   designation, `RP-30FQ`, not present in the catalog. `source_type: retailer_page` → tier 7;
   does not upgrade the edge's primary manufacturer-assertion evidence, but adds a
   `retailer_cross_reference` corroborating event, same pattern as the Coleman endpoint
   design's retailer corroboration (§2 "New retailer observations" of that design).
8. `unitedrvparts.com`'s `SF-30VHFQ` and `SF-30VHQ` product pages: neither contains a
   supersession statement toward `SF-30FQ`. This is meaningful rather than merely an absence
   of data: the same retailer explicitly uses "Superseded from 2563A" language elsewhere (the
   `SF-35VHFQ` `2587A` listing) when a real supersession exists, so its absence on both
   `SF-30FQ`'s stated successors-in-name is evidence the manufacturer has not declared one.
   This does not become an edge or attribute — it's the basis for continuing to *not* build a
   `supersedes` edge, closing issue #26 with a "no" rather than leaving it open as "unknown."

These eight observations are sufficient to create three components, populate cutout/clearance
attributes on both endpoints, one `fits` edge with two independent corroborating sources, and
a second identifier on the core-module component.

### Explicitly not asserted

- No `supersedes` edge from `SF-30FQ` to `SF-30VHFQ`/`SF-30VHQ` — see observation 8 above
  (issue #26, closed as resolved "no").
- No interpretation of the cooktop manual's Figure 2 dimension letters (A–E) beyond recording
  their values — the diagram itself isn't extracted, so which letter is width vs. depth vs.
  offset isn't asserted here.
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
  critical_attributes: [btu_rating, ignition_type, clearance_front_in, clearance_left_in,
                         clearance_right_in, clearance_top_in, clearance_bottom_in,
                         clearance_back_in]
  secondary_attributes: [cabinet_cutout_h_in, cabinet_cutout_w_in]
  tags: [climate, lp_gas, appliance]
  pcdb_term_id: null
  # Clearance-to-combustible values are per-model rows in the installation manual
  # (Table 2) -- high trust. cabinet_cutout_h/w is filed as SECONDARY, not
  # critical: the manual states it once for the whole SF-FQ family tied to one
  # installation method (against the outer skin), not confirmed SF-30FQ-specific
  # the way Table 2's clearances are, and a different install method uses a
  # charted/variable tube length instead of a fixed cutout.

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
  critical_attributes: [burner_count, btu_rating, cutout_a_in, cutout_b_in, cutout_c_in,
                         cutout_d_in, cutout_e_in]
  secondary_attributes: [oven_btu_rating, manifold_pressure_wc, clearance_below_counter_in,
                          clearance_right_sidewall_in, clearance_left_sidewall_in,
                          clearance_backwall_in, clearance_vertical_in]
  tags: [appliance, lp_gas]
  pcdb_term_id: null
  # cutout_a..e_in are the manual's own Figure 2 dimension labels, recorded
  # without further interpretation (see "Explicitly not asserted" above).
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
    clearance_front_in: 1
    clearance_left_in: 0
    clearance_right_in: 0
    clearance_top_in: 0
    clearance_bottom_in: 0
    clearance_back_in: 0     # exhaust/intake tube clearance (3/8") not modeled as a
                              # separate attribute in this pass -- same six-field shape
                              # as the other clearance fields, tube clearance differs in
                              # kind (a duct penetration, not a wall/ceiling clearance)
    cabinet_cutout_h_in: 8       # from "17-3/4 x 8" -- family-level, method-A-specific;
    cabinet_cutout_w_in: 17.75   # see part-type note above and source 5 above
    stock_no: "2391"         # secondary, not critical_attributes
    serial: "122103492"

- component_id: c_placeholder_furnace_part_2608a
  part_type_id: 417
  identifiers:
    - {ns: suburban, value: "2608A", visibility: catalog}
    - {ns: suburban, value: "RP-30FQ", visibility: retailer_page}   # obs 7, corroborating
                                                                      # model designation,
                                                                      # not the catalog's own
                                                                      # order-number identifier
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
    clearance_below_counter_in: 0
    clearance_right_sidewall_in: 6
    clearance_left_sidewall_in: 6
    clearance_backwall_in: 9
    clearance_vertical_in: 24   # 19.5" reducible variant (with range hood) not
                                 # separately modeled in this pass
    cutout_a_in: 18.625   # 18 5/8" -- SRNA3S/SRSA3S row, Figure 2, unlabeled dimension
    cutout_b_in: 16
    cutout_c_in: 2
    cutout_d_in: 20.625   # 20 5/8"
    cutout_e_in: 0.875    # 7/8"
    stock_no: "2863"
    serial: "122109479"
```

Both endpoints' clearance-table values are corroborated twice — once by the in-hand plate
photo, once by the matching manual page — which is stronger evidence than either source
alone. The furnace's cabinet-cutout dimension and the cooktop's five Figure-2 dimensions are
each single-sourced (manual only), so they're recorded with plain `manufacturer_pdf`
provenance rather than a corroborated/cross-checked marker.

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
- evidence: `attribute_prior` Beta(1,1); `manufacturer_assertion` effect alpha `+2` beta `+0`
  sourced to the catalog observation; `retailer_cross_reference` effect alpha `+1` beta `+0`
  sourced to the `unitedrvparts.com` observation (obs 7) — same three-event shape as the
  Coleman endpoint design's supersession edges (§4 of that design)

## 6. Resolver boundaries

Add one focused builder to `Docs/Tools/edge_resolver.py`, mirroring
`atwood_repair_parts_and_fits()`'s shape but scoped to a single part (no bulk table):

```python
suburban_furnace_and_core_module(conn, furnace_dataplate_row, furnace_manual_row,
                                  cooktop_dataplate_row, cooktop_clearance_row,
                                  cooktop_manual_row, catalog_row) \
    -> list[tuple[Component, list[Identifier], list[ComponentAttribute], list[edge_id]]]
```

Validates:

- the furnace/cooktop dataplate observations carry `source_type: dataplate_photo`;
- the furnace/cooktop manual observations carry `source_type: manufacturer_pdf` and each
  names the exact model (`SF-30FQ`, `SRNA3S`/`SRSA3S`) on the row the dimensions are read
  from;
- the catalog observation's `manufacturer_pdf` text explicitly names both `SF-25FQ` and
  `SF-30FQ` on the `2608A` row (reject if only one model or a different module number
  appears — protects against a future catalog edition silently changing this);
- the furnace's `cabinet_cutout_h_in`/`cabinet_cutout_w_in` are written as `secondary`, never
  `critical`, attributes (guards the method-A-only caveat from §2/§3);
- no `supersedes` edge is created toward `SF-30VHFQ` (guards issue #26's boundary the same
  way the Coleman endpoint resolver rejects an unnamed supersession).

## 7. Fixture and documentation changes

Extend `Docs/Inital_Design/ground-truth.yaml` with the three components, their attributes,
and the one `fits` edge. Fixture comparison must verify:

- both exact component identifiers and the repair-part identifier;
- exactly one `fits` edge, correct direction (`2608A -> SF-30FQ`);
- the furnace's `btu_rating` attribute carries `inferred_from_model_family` provenance, not
  `dataplate_photo`;
- the furnace's clearance attributes and the cooktop's clearance + cutout attributes are all
  present, sourced to the correct manual/plate observations, with the furnace's cabinet
  cutout filed as `secondary_attributes`, not `critical_attributes`;
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

- Any `supersedes` claim toward `SF-30VHFQ` (issue #26).
- Interpreting the cooktop manual's Figure 2 dimension diagram (which letter is width vs.
  depth vs. offset) — values are recorded, not interpreted.
- Confirming the furnace cabinet cutout against this specific coach's actual installation
  method (A vs. B) — recorded as family-level, method-A evidence only.
- Resolving the furnace/cooktop model-number grammar letter-by-letter (existing open item in
  `VENDOR-Suburban-Furnace_Cooktop.md`).
- The Coleman-Mach `8330A733` rooftop AC and the High Pointe `EM925RCW` microwave found in
  the same photo pass (issues #23, #24) — separate vendor-research items, not part of this
  extension.
- The Norcold `N811RT` 4th-vendor arc — separate design, next after this one.
