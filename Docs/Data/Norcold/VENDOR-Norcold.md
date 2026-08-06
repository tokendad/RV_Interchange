# VENDOR — Norcold (Thetford)

**Status:** exact endpoint component built (`c_placeholder_refrigerator_n811`,
part_type_id `602`, resolver version `norcold_endpoint_v1`); one `fits` repair-part edge
and one `supersedes` repair-part chain built (part_type_id `603`, resolver version
`norcold_parts_v1`)
**Vendor position:** 4th Stage 1 vendor (after Suburban, Coleman-Mach, Atwood)

## 1. In-hand unit

The owner's current RV (2013(?) SPREE 322BHS) carries a Norcold two-way absorption
refrigerator, photographed 2026-08-05 alongside the Suburban furnace/cooktop
(`Docs/Data/Current RV - DO NOT COMMIT THIS FOLDER/Fridge/`, gitignored — personal-coach
evidence, same treatment as other in-hand photo folders; hand-transcribed into
`observations.db` instead, obs #105).

| Field | Value | Source |
|---|---|---|
| Spec-plate model number | `N811` | obs #105, interior spec plate |
| Warranty-sticker model number | `N811RT` | obs #105, same door, same serial |
| Serial number | `15605897` | obs #105, both labels agree |
| Group code | `120601` | obs #105 |
| Cooling-unit tag | `8W1006`, SN `15597729` | obs #105, separate component inside cabinet |
| Refrigerant | R717, 0.66 lbs | obs #105 |
| Input | 1420 BTUH | obs #105 |
| AC supply | 120VAC 60Hz, 2.5A, 300W | obs #105 |
| DC supply | 12VDC, 0.8A, 10W | obs #105 |

## 2. The `N811` vs `N811RT` question — resolved

The permanent Norcold Inc. spec plate reads `Model #: N811`. A separate warranty/
registration sticker set on the same door reads `Model No. N811RT`, sharing the identical
serial number. Same pattern the project has already hit twice — Suburban's FQ/VHFQ
letters (GitHub issue #26) and Coleman-Mach's AR7815/7330F3858 label pair (issue #18):
two identifiers on the same physical unit that look like a conflict but are actually two
different levels of the same naming system.

**Resolution:** Norcold's own model-identification grammar (obs #106, Service Manual
p.4, "MODEL IDENTIFICATION") decodes a 12-position model-number string, including:

- Position 10 — **door swing**: `L` = left-hand, **`R` = right-hand**
- Position 12 — **packaging type**: blank = corrugated packaging, **`T` = returnable
  packaging tray**, `M6` = 6-unit multi-pack

So `N811RT` = base model `N811` + `R` (right-hand door swing, a real physical attribute)
+ `T` (returnable packaging tray, a **shipping/batch** attribute, not a permanent physical
feature of the installed unit). That plausibly explains why the permanent interior spec
plate — installed once, describing the unit itself — omits the packaging-tray letter that
a manufacturing-batch warranty sticker included. `N811` is the base/family model; `N811RT`
is the exact full order code for this specific unit as shipped.

**Corroboration:** the online research pass (`Norcold N811RT Research Report.md`)
independently found `N811RT` absent from the current official parts catalog's own
model list (which lists `N810`, `N811`, `N811C`, `N811J`, `N811F`, `N811v`, `N814F2`,
`N811VF` but not `N811RT` as its own line) — consistent with `RT` being order-code/
packaging suffixes layered on the `N811` base rather than a separate catalog SKU.

**Caveat:** the grammar table itself comes from a Service Manual scoped to the `N611v`/
`N811v` models (obs #106) — a later variant family than the in-hand unit's plain `N811`
(no `v`). Treated as applicable to the whole N6XX/N8XX platform's model-numbering
convention (same family lineage, same manufacturer, no evidence the letter-position
grammar itself changed generation to generation), not as an exact-model document for
`N811RT` specifically. Flag if a `v`-generation-specific numbering change ever surfaces.

## 3. Specifications and dimensions — built component

The component is built from obs #108 (Service Manual, **N6XX/N8XX Models**, 619394EFP,
via Bryant RV) — the plain, non-`v` family that actually matches the in-hand `N811`, not
the later `v`-variant manuals used for §2's grammar decode:

| Attribute | Value | Source |
|---|---|---|
| `serial` | `15605897` | obs #105, dataplate_photo |
| `group_code` | `120601` | obs #105, dataplate_photo |
| `input_btuh` | 1420 BTU/h | obs #105, dataplate_photo |
| `refrigerant` / `refrigerant_lbs` | R717, 0.66 lb | obs #105, dataplate_photo |
| `ac_voltage_v`/`ac_amperage_a`/`ac_watts_w` | 120V, 2.5A, 300W | obs #105, dataplate_photo |
| `dc_voltage_v`/`dc_amperage_a`/`dc_watts_w` | 12V, 0.8A, 10W | obs #105, dataplate_photo |
| `cooling_unit_model`/`cooling_unit_serial` | `8W1006` / `15597729` | obs #105, dataplate_photo |
| `door_swing` | `R` | obs #106, manufacturer_pdf_inferred (grammar decode applied to obs #105's own `N811RT` suffix) |
| `storage_volume_cu_ft` | 7.5 ft³ | obs #108, manufacturer_pdf |
| `rough_opening_h_in`/`_w_in`/`_d_in` | 59.875 × 23.5 × 24 in | obs #108, manufacturer_pdf |

**Cross-document corroboration:** obs #107 (the `v`-variant installation manual)
independently gives an enclosure-assembly tolerance of 59.88–60.01 in for the same
rough-opening height — obs #108's 59.875 (59 7/8) falls inside that band. Two
independently-fetched manuals, two different domains (Bryant RV vs. Heartland Owners
archive), two adjacent product generations, agreeing on the platform's physical
envelope — good evidence the N81X cabinet size is stable across the `N811`→`N811v`
generations, not proof, but strong enough to build on. obs #107 is corroboration-only
and not itself a build source.

`packaging_type` (`T` = returnable packaging tray, decoded alongside `door_swing` in
§2) is deliberately **not** asserted as a component attribute — it's a shipping/batch
property of how this unit was originally packed, not a lasting physical feature of the
installed refrigerator.

## 4. Fits and supersedes — official parts catalog (obs #109)

Fetched Thetford/Norcold's own official N61/N81 parts catalog (`PL_N61N81_623421`,
dated 2022-02-21) — the same tier of manufacturer-primary evidence that unlocked
Coleman-Mach's and Suburban's supersession edges. Column alignment confirmed with
`pdftotext -bbox` (same coordinate-precise method as Atwood's repair-parts tables),
not eyeballed.

**`fits` — base/power board (`c_placeholder_norcold_part_628674`):** the catalog lists
two serial-scoped board revisions for a shared bracket of models including N811 (its
own footnote: "N811 SERIES INCLUDES N814F2 AND N811 MODELS") — `618186` for
refrigerator serial 9056491 and below, `628674` for 9056492 and above. The in-hand
unit's own serial (`15605897`, obs #105) is well above that breakpoint, so only
`628674` is built as a `fits` edge to `c_placeholder_refrigerator_n811`; `618186` is
out of scope for this unit (not a supersession target — the catalog doesn't say one
replaces the other, just which one to use per serial cohort).

**`supersedes` — optical control board (`628979` → `637775`):** the same catalog
uses explicit "(USE 637775)" wording for the black optical control assembly, serial
9056492 and above — the same supersession-language convention already established
elsewhere in this project (Suburban/Coleman-Mach catalogs). Built as a **family-level**
`supersedes` edge between the two repair-part components, deliberately **not**
attached to `c_placeholder_refrigerator_n811` by any edge: the control board's own
color and internal serial were never photographed on the in-hand unit, so this
documents the catalog's real supersession fact without claiming which exact board is
currently installed. Three other serial/color-scoped pairs exist in the same catalog
table (`621988`→`637774`, `636105`→`637776`, `629079`→`637777`) — not built, since
they don't match the in-hand unit's known refrigerator-serial cohort as cleanly.

## 5. Not yet done

- The online research report's near-match leads (`N8X`/`N8DC` as dealer-claimed direct
  replacements — vague line names, not verified exact catalog model numbers; `630762`
  optical board — unverified single marketplace claim) remain observation-only. Same
  bar this project has applied elsewhere (Coleman-Mach's `8330-3362`/`1C26-10`): no
  edge without either a manufacturer statement or a second independent source.
- The catalog's other three optical-control supersession pairs (§4) and its AC-heater,
  gas-valve-bracket, and drain-hose serial-scoped tables (obs #109's `quoted_text`/the
  research report's §5) are real but not yet built — same evidentiary bar as `628674`,
  just not yet worked through column-by-column.
- Recall status checked (research report only, not a logged observation) — `N811`/
  `N811RT` absent from Thetford's current model-list pages reviewed, but that's not
  conclusive without a serial-specific check.

## 6. Sources

- obs #105 — in-hand data plate, warranty sticker, and cooling-unit tag photographs
- obs #106 — Norcold Refrigerator Service Manual, N611v/N811v Models (636355A),
  `Docs/Data/Norcold/Service_manual.pdf`, p.4 Model Identification
- obs #107 — Norcold Installation and Owner's Manual, N611v/N811v Models (636158B),
  `Docs/Data/Norcold/Norcold-N611v-N811v-Installation-Owners-Manual.pdf` (mirror:
  manuals.heartlandowners.org), p.13 Key Refrigerator Dimensions — corroboration only
- obs #108 — Norcold Refrigerator Service Manual, N6XX/N8XX Models (619394EFP),
  `Docs/Data/Norcold/Norcold-N6XX-N8XX-Service-Manual-619394E.pdf` (mirror: bryantrv.com),
  p.3–4 Specifications & Model Identification — primary build source
- obs #109 — Norcold/Thetford Official Parts List, N61/N81 Series (623421, dated
  2022-02-21), `Docs/Data/Norcold/Norcold-Thetford-N61-N81-Parts-List-623421.pdf`
  (mirror: thetford.com), p.6 Optical Control & p.9 Base/Power Board tables
- `Docs/Data/Norcold/Norcold N811RT Research Report.md` — broader online research pass
  (manuals, parts catalog, recall status, near-match interchange leads), not yet
  individually logged as observations
