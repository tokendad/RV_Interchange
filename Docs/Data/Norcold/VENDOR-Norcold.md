# VENDOR — Norcold (Thetford)

**Status:** exact endpoint component built (`c_placeholder_refrigerator_n811`,
part_type_id `602`, resolver version `norcold_endpoint_v1`); base/power board `fits` edge
and optical-control `supersedes` chain built (`norcold_parts_v1`); drain-hose and
AC-heater `fits`/`supersedes` pairs built 2026-08-10 (`norcold_drain_hose_heater_v1`,
obs #118) — see §4.2
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

## 4.1 `630762`/`1172-321` — confirmed alias, deliberately unconnected

A follow-up research pass (`Docs/Data/Norcold/630762-Research.md`, obs #110) upgraded
`630762` from the earlier "unverified single marketplace claim" status: three
independent named dealers (Dads Marine, RV Yard, Young Farts RV Parts) confirm it as a
genuine, discontinued Norcold optical/"eyebrow" control board, and a board photograph
(Tim's RV/eBay, corroborated by a second listing) shows an additional printed marking,
`1172-321`, on the same physical board — the same "photo confirms co-location"
evidence standard that resolved Coleman-Mach's `AR7815`/`7330F3858` case. Built as
`c_placeholder_norcold_part_630762` with both identifiers merged onto one component.

**Deliberately given zero edges.** `630762` is absent from the official parts catalog
(obs #109) entirely, and the research pass itself calls its relationship to that
catalog's optical-control lineage (`621988`/`628979`/`636105`/`629079`) *unresolved*,
not merely under-evidenced — "fits all N611/N811" and "replaces 621988/628979/637775"
claims appear only in aftermarket listings, explicitly called out as unsupported. So
unlike `628674`/`628979`→`637775` (§4), this component gets no `fits`/`supersedes`
edge to anything. `--check-fixture` asserts this directly (fails if any edge is ever
attached to it), so a future change can't silently promote the connection without
updating this reasoning first.

**Thetford email reply, 2026-08-12** (issue #28, obs #120): user emailed Thetford's
parts-fulfillment contact (Dave Carter & Associates) asking specifically about the
630762-to-catalog-lineage question. Reply confirmed 630762 is the front optical board
but did not address the catalog relationship at all — it redirected to the unrelated
main/base-power board and noted Thetford no longer sells parts directly to customers.
Same non-identification outcome as the Coleman-Mach `1C26-10` precedent (issue #37).
No new information; zero-edge status above stands unchanged.

**Correction 2026-08-10** (research-pass check, not a logged observation — same "not yet
promoted to obs" convention as §5's recall-status line): the catalog's other
optical-control pairs were column-checked with `pdftotext -bbox` (same coordinate-precise
method as VENDOR-Atwood.md §7.1) rather than left as an open question. Result: none of
them apply to the in-hand N811. `636105`→
`637776` is scoped to the `N611v`/`N811v` columns only (the in-hand unit is plain `N811`,
confirmed non-`v` per obs #108's own family statement); `629079`→`637777` is the *brown*
board and scoped to `N610`/`N810` only (wrong color and wrong model family). `621988`→
`637774` does cover `N811`, but at the "serial 9056491 and below" bracket — the in-hand
refrigerator serial (15605897) is well above that, same reasoning that already excluded
`618186` from the base board in §4. A fourth number, `624207` ("brown, serial 9056491 and
below, USE 621988"), was found chained ahead of `621988`'s own bracket — also `N610`/
`N810`-only, also not applicable. So this isn't "not yet matched cleanly"; none of the
four numbers apply to a plain black N811 above that serial breakpoint.

## 4.2 Drain hose and AC heater (obs #118) — built 2026-08-10

Same official parts catalog (623421), read fresh with the coordinate-precise method
(`pdftotext -bbox`) rather than reusing obs #109's narrower extraction. Both pairs are
fully determined by data already photographed on the in-hand unit (obs #105), unlike the
optical-control board pair in §4 (whose installed color/serial was never photographed) —
so both get `fits` edges to `c_placeholder_refrigerator_n811`, same bar as the base board
(`628674`).

- **Drain hose:** `622391` ("Drain Hose Assy - N8 Series") → `639101`, cleanly scoped to
  the N8 column group (N811 included) with no serial variants. The N6-series sibling
  (`622390`→`639100`) is out of scope for this unit, not built.
- **AC heater:** `630811` ("Heater-AC/Backer, CU Serial# 11232008 & Above") → `638374`.
  The in-hand unit's own cooling-unit serial (`15597729`, obs #105, tag `8W1006`) is
  above that breakpoint, so this is the applicable generation — same "which generation
  matches this specific unit" resolution already used for the base board. The
  below-serial sibling (`621702`→`638365`) is out of scope, not built.

**Table-layout quirk worth recording:** this table prints each part number's anchor
CENTERED between its two column-group description lines (N6-group line above, N8-group
line below), not above both the way VENDOR-Atwood.md §7.1 describes as "the standard
method." A naive anchor-to-next-anchor row window only captures the line *below* the
anchor. That happened to be exactly the line needed here (N8-group, matching N811), but a
future extraction against the N6-group lines from this same table needs row boundaries
built from the midpoint between adjacent anchors, not anchor-to-anchor.

4 new repair-part components (`part_type_id: 603`), 4 `fits` edges, 2 `supersedes`
edges — `norcold_drain_hose_and_heater_fits()` in `edge_resolver.py`, resolver version
`norcold_drain_hose_heater_v1`. `edge_resolver.py --check-fixture`: 0 mismatches.
`--self-test`: PASS. `pytest`: 53/53.

## 5. Not yet done

- `N8X`/`N8DC` (vague line names, not verified exact catalog model numbers) remain
  observation-only. Same bar this project has applied elsewhere (Coleman-Mach's
  `8330-3362`/`1C26-10`): no edge without either a manufacturer statement or a second
  independent source.
- **Gas valve bracket** (p.5): a third serial-scoped table exists (`624681`/`628993`
  brackets, `621334`/`640182` and `633726`/`637540` kits, breakpoint `9185698`/`9185699`)
  but this document's own rows don't label which serial the breakpoint refers to (unlike
  "SERIAL #" for the base board/optical control, or "CU SERIAL#" for the heater) —
  plausibly the refrigerator serial, given the numeric adjacency to the `9056491`/
  `9056492` breakpoint elsewhere in this same document, but that's an inference, not a
  labeled fact. **If confirmed as refrigerator serial**, the in-hand unit's serial
  (15605897) puts it in the ABOVE bracket (`628993`, `633726`→`637540`), making this
  buildable; deferred until that's confirmed rather than assumed.
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
- obs #110 — `630762`/`1172-321` board-photo research pass (Dads Marine, RV Yard,
  Young Farts RV Parts, Tim's RV/eBay), `Docs/Data/Norcold/630762-Research.md`
- obs #118 — fresh coordinate-precise (`pdftotext -bbox`) read of the same 623421 parts
  catalog as obs #109, drain hose (p.6) and AC heater (p.6-7) tables
- `Docs/Data/Norcold/Norcold N811RT Research Report.md` — broader online research pass
  (manuals, parts catalog, recall status, near-match interchange leads), not yet
  individually logged as observations
