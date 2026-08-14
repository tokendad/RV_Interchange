# VENDOR — Atwood / Atwood Mobile Products

**Status:** endpoint components + repair-parts cross-reference built, plus one in-hand
teardown anchor (GH6-6E) and its gas-valve supersession chain
**Updated:** 2026-08-14 — closed all six remaining #35 children (issues #40/#41/#43/#44/
#45/#46) by re-reading the Electronic table's GH6-6E column in both the Jan 2014 and Jan
2007 editions (obs #128/#129). 5 parts confirmed and linked to GH6-6E with new `fits`
edges (0 new components — all already existed from other models); `91470`'s disputed
120°/130° thermostat calibration resolved as a genuine spec revision between editions,
both values kept; `91580` electric element confirmed inapplicable to the gas-only GH6-6E;
3 parts confirmed to have zero current applicability in either edition and are not built;
4 numbers from the attached research report were searched for and not found anywhere.
See §11.
**Updated:** 2026-08-09 — GH6-6E gas-valve chain built (issue #42, split from #35): `91605
-> 93870 -> 93844`, with `93870`/`93844` `fits` GH6-6E. See §9. Totals now: 20 endpoint +
91 repair-part components, 370 `fits` + 2 `supersedes` edges.
**Updated:** 2026-08-07 — In-hand teardown anchor GH6-6E built (obs #111 data plate, obs
#112 Winnebago OEM catalog), resolving the "no in-hand teardown anchor yet" gap noted
above (issue #13) and issue #33. See §8. Totals now: 20 endpoint components + 88
repair-part components + 368 `fits` edges.

## 1. Why this adapter

Atwood is the third Stage 1 vendor, after Suburban (water heaters) and Coleman-Mach
(thermostats). It is itself a water heater vendor, giving the fixture its first
cross-manufacturer water-heater comparison — Suburban's own manual already documents
Atwood retrofit-panel dimensions as a competing option (`c_placeholder_wh_atwood_6gal`/
`_10gal`, the generic family-placeholder components built during the Suburban IW60RL
retrofit work — see `edge_resolver.py`'s `resolve_atwood_family_components()`). Those two
components are **not** the same thing as the real, model-specific components built here:
they're manufacturer-asserted stand-ins for "an Atwood 6/10-gallon tank, whichever one,"
used only as a retrofit target in the Suburban fixture, with no real Atwood model
identifiers. This document and its components are Atwood's own first-class vendor arc.

No physical Atwood unit is in hand yet, so unlike Coleman-Mach's thermostat teardown or
Suburban's own in-hand water heaters, this wave has no photographed anchor fixture. It
starts catalog-only, from Atwood's own service manual — the same evidentiary tier as
Coleman-Mach's later catalog-only waves (second/third), just as the *first* wave here
rather than a later one.

## 2. Source material

Three editions of the same underlying Atwood service manual are now in hand, each with a
different "Replacement Part Reference" table revision date printed on the table itself
(the manual's own cover/title date does not track this — all three are titled "2004 Water
Heater" or equivalent):

- `Docs/Data/Atwood/Atwood-Water-Heaters.pdf` — **January 2014** table revision. A rescanned
  PDF (CreationDate 2017, ModDate 2019) with an OCR-derived text layer that is real but
  demonstrably incomplete (word-extraction gaps found around watermarked/obscured regions,
  and one row's ✗ marks merged into the wrong adjacent row during extraction) — usable for
  spot-checks, not treated as a primary structured-extraction source.
- `Docs/Data/Atwood/Atwood-Water-Heater-Service-Manual.pdf` (user-supplied, myrvworks.com
  mirror) — **September 2003** table revision. Native/born-digital PDF (Acrobat Distiller
  4.05, 2003), full reliable text layer.
- `Docs/Data/Atwood/Atwood-Water-Heater-Service-Manual-2007.pdf` (user-supplied URL,
  manuals.heartlandowners.org mirror) — **January 2007** table revision. Native/born-digital
  PDF (QuarkXPress/Distiller 7.0.5, Feb 2007), full reliable text layer. Used as the primary
  source for §7 below: the most current of the two reliably-extractable editions.

All three cover Pilot models, Electronic Ignition & XT models, general water heater
information, and parts breakdowns/replacement-part cross-reference tables. `www.atwoodmobile.com`,
support line 866-869-3118 or 1-800-825-4328 (named in-document).

Not yet captured: any Atwood retailer pages, Wayback Machine history, an in-hand unit's
rear-label/data-plate photographs, or the Electronic Ignition table's own repair-parts
cross-reference (only the Pilot table is built so far — see §7).

## 3. Model-number grammar

The manual gives two explicit legends, for two different physical/electrical families that
share one document:

**Pilot models** (p.4): `G [C] [H] {6|10} A[A] - # [P]`
- `G` — Propane Gas (constant prefix)
- `C` — Combination gas and 110VAC electric (absent = gas-only)
- `H` — Engine Heat Exchange option
- `6`/`10` — gallon capacity
- trailing `P` — Pilot Relight version

**Electronic Ignition models** (p.14): `G [C] [H] {6|10} AA - # E`
- Same `G`/`C`/`H`/capacity letters as the Pilot legend
- trailing `E` — Electronic Ignition (DSI)

**XT/exothermal models** (p.14, its own legend line: `G E H 9/16 - E XT`) use a
**different** letter for the gas/electric combo flag — `E` immediately after `G`, not `C`
— and the `-EXT` suffix. This is a real inconsistency in the manufacturer's own numbering,
not a transcription error: confirmed by `GC10A-4E`/`GCH10A-4E` in the main catalog table,
which are exothermal (per their own description text) but do **not** carry the `-EXT`
suffix or the XT-family's `E`-after-`G` combo letter — they use the regular
Pilot/Electronic-family `C` combo letter instead. Because of this, `exothermal` is treated
as a single-presentation (description-text-only) attribute for all 19 models, not
cross-validated against the model number the way `power_type`/`heat_exchanger`/
`ignition_type` are (see `atwood_endpoint_components()` in `edge_resolver.py` for the exact
cross-check logic and its documented exception).

Not decoded here: the `A`/`AA` letter (manual only says "type of heating element" and
warns bolt-on vs. screw-in elements are physically different and must be checked on the
unit — no per-model enumeration given, so no attribute is asserted for it), or the trailing
numeral after the dash (an opaque revision/version number, not decoded).

## 4. First wave: 19 exact endpoint components (obs #92)

Built from obs #92 — the manual's own "Atwood LP Gas Water Heaters" catalog table (p.2:
PART#/MODEL#/DESCRIPTION for the RV product line) cross-checked against the two
model-number legends above, both presentations from the same manufacturer-primary
document. `atwood_endpoint_components()` in `edge_resolver.py`, resolver version
`atwood_endpoint_v1`; each component asserts `capacity_gal` (6 or 10), `power_type`
(`gas_only`/`gas_electric`), `ignition_type` (`pilot`/`electronic`), `heat_exchanger`
(bool), and `exothermal` (bool); three of the 19 carry an extra attribute the description
column states but the model number doesn't encode: `G6A-7P` is `pilot_relight: true` and
`status: discontinued` ("NLA" in the table); `GC6AA-10E` is `availability: oem_only`.

| Model | Capacity | Power | Ignition | Heat exch. | Exothermal | Notes |
|---|---:|---|---|:---:|:---:|---|
| `G6A-7` | 6 | gas_only | pilot | | | |
| `G6A-7P` | 6 | gas_only | pilot | | | pilot_relight; **discontinued (NLA)** |
| `GC6AA-8` | 6 | gas_electric | pilot | | | |
| `GC6AA-10E` | 6 | gas_electric | electronic | | | OEM only |
| `GCH6A-10E` | 6 | gas_electric | electronic | ✓ | | |
| `G6A-8E` | 6 | gas_only | electronic | | | |
| `GH6-8E` | 6 | gas_only | electronic | ✓ | | |
| `G9-EXT` | 6 | gas_only | electronic | | ✓ | |
| `GE9-EXT` | 6 | gas_electric | electronic | | ✓ | |
| `GEH9-EXT` | 6 | gas_electric | electronic | ✓ | ✓ | |
| `G10-2` | 10 | gas_only | pilot | | | |
| `GC10A-2` | 10 | gas_electric | pilot | | | |
| `G10-3E` | 10 | gas_only | electronic | | | |
| `GH10-3E` | 10 | gas_only | electronic | ✓ | | |
| `GC10A-4E` | 10 | gas_electric | electronic | | ✓ | exothermal, no `-EXT`/`E`-combo — see §3 |
| `GCH10A-4E` | 10 | gas_electric | electronic | ✓ | ✓ | exothermal, no `-EXT`/`E`-combo — see §3 |
| `G16-EXT` | 10 | gas_only | electronic | | ✓ | |
| `GE16-EXT` | 10 | gas_electric | electronic | | ✓ | |
| `GEH16-EXT` | 10 | gas_electric | electronic | ✓ | ✓ | |

Marine/220V-CE water heaters in the same manual (pp.2 addenda: `EHM4-SM`, `EH20`,
international `EHM6-FHX` family, etc.) are explicitly **not** RV parts and are out of scope
— not built, not tracked as observation-only candidates, since this project is RV parts
interchange, not marine.

`edge_resolver.py --check-fixture`: 0 mismatches for all 19. `pytest`: 25/25 green.

## 5. Sources

- obs #92 — Atwood Mobile Products, LLC's own service manual: the "Atwood LP Gas Water
  Heaters" catalog table (p.2) cross-checked against the Pilot (p.4) and Electronic
  Ignition (p.14) model-number-explanation legends. `Docs/Data/Atwood/Atwood-Water-Heaters.pdf`.
- obs #95 — the January 2007 edition's Pilot "Replacement Part Reference" table (pp.31-32),
  scoped to the 5 already-built Pilot models. `Docs/Data/Atwood/Atwood-Water-Heater-Service-Manual-2007.pdf`.
  See §7.
- obs #96 — the January 2007 edition's Electronic Ignition "Replacement Part Reference"
  table (pp.35-36), scoped to the 8 already-built Electronic models. Same source PDF. See §7.

## 6. Resolver status and next milestone

First wave complete: 19 exact endpoint components. Second wave (§7) adds shared
repair-parts cross-references for all 13 of the 19 models that have a Pilot or Electronic
Ignition parts table (5 Pilot + 8 Electronic) — **87 repair-part components, 367 `fits`
edges** total across both tables.

Ready-to-do next work, in rough priority order:

1. If/when a physical Atwood unit becomes available, add an in-hand teardown observation
   (rear label, data plate, model number) as a real anchor fixture, same role as the
   Coleman-Mach thermostat teardown (obs #44) — the two existing generic
   `c_placeholder_wh_atwood_6gal`/`_10gal` family-placeholder components (Suburban-arc,
   §1 above) are not a substitute for this.
2. Retailer/Wayback Machine research to corroborate or extend the 19-model catalog (e.g.
   confirm current-vs-discontinued status beyond the one `NLA` flag the manual itself
   states, or find later/earlier manual revisions for a production-window timeline like
   Coleman-Mach's D→E→G/F letter progression).
3. `capacity_gal`/`opening_h`/`opening_w` cross-comparison against the existing Suburban
   `opening_families` fixture data (§4's `part_types` block, `Docs/Inital_Design/
   ground-truth.yaml`) — resolved. The Atwood brochure cutout spec gives the two family
   openings directly, so all 19 endpoint components now carry `opening_h`/`opening_w`
   assertions in the resolver and fixture.
4. ~~The 6 remaining EXT-family models...~~ Done — see §10.

## 7. Second wave: Pilot repair-parts cross-reference (obs #95)

The manual's "Replacement Part Reference" tables are a genuinely different relationship
shape than §4/§6.1's supersession-style evidence: each row is one generic internal service
part (a thermostat valve, burner, orifice, door, gasket kit...) and each column a *bracket*
of many distinct end-product models it fits — many-to-many, not old-model-to-new-model.
Modeled as a new edge type, `fits` (`edges.type` is free-text, so this needed no schema
migration — same mechanism as how `controls` was added), from a new `part_type_id: 413`
("water heater repair/service part") component to each host water-heater model it fits.
This also resolves, for Atwood, the same "single-fixture-encounter" TODO the Suburban
switch component (`c_placeholder_wh_switch`, filed under `part_type_id: 412` with a
"likely wants its own type on second encounter" comment) flagged — this is that second
encounter, for a different vendor.

### 7.1 Extraction method: coordinate-precise, not eyeballed

The first attempt at this table (against the January 2014 edition, a rescanned PDF) was
done by rendering pages to PNG and reading X-mark positions by eye — a real risk of
column-misalignment error across a 12-column table, flagged to the user before building
anything from it. The user then supplied two better sources: the September 2003 edition
(native PDF, real text layer) and, after a further exchange, the January 2007 edition
(also native, from a different mirror) — three dated revisions of the same table, "a very
good source to cross-check everything" (user, 2026-08-04).

All three turned out to have **real, word-level text layers**, including the 2014 scan
(OCR-derived, real "X" tokens in its text layer, previously overlooked). This let every
table be parsed with `pdftotext -bbox`, which gives exact `(xMin, yMin, xMax, yMax)`
bounding boxes per word — column membership becomes a nearest-neighbor match against the
header words' own x-positions, not a pixel guess. Each part-number "anchor" (a 5-digit
token at the row's left margin) defines a row segment running to the next anchor's y
position, so multi-line entries (two-line descriptions, wrapped column headers) are
captured correctly. This is unambiguously more reliable than the original visual read, and
is now the standard method for any future Atwood table extraction.

Cross-checking the three editions surfaced genuine historical evolution, not extraction
noise: `91603 Jade Pilot` fit only the `G6A`/`GC6AA-7`/`GC6AA-8` family in the September
2003 edition, gaining the `G10B`/`GC10A-2`/`GC10-1`/`GC10-2`/`G10-2` columns by January
2007 (i.e. it became compatible with more models over time — read as a real product
change, not a data conflict). `93801`/`93803` (Ignition Module/Piezo Wiring Harness)
similarly gained the `GC6AA-8` column between 2003 and 2007. The January 2007 edition was
used as primary since it's the more current of the two reliably-extractable (native-text)
editions; the 2014 scan's OCR text layer, while real, has demonstrated gaps (a watermark
overlapping two drain-plug rows, one row's marks merged into an adjacent row) and is not
treated as authoritative.

### 7.2 What was built (Pilot table)

Scoped to the 5 Pilot models already built as exact endpoint components: `G6A-7`,
`G6A-7P`, `GC6AA-8`, `GC10A-2`, `G10-2` (the Electronic Ignition table's own repair-parts
cross-reference, for the 8 built Electronic models, is covered separately in §7.3).

**40 repair-part components, 119 `fits` edges** — `atwood_repair_parts_and_fits()` in
`edge_resolver.py`, resolver version `atwood_fits_v1`. Each component carries one
`description` attribute (manufacturer_pdf, obs #95); each `fits` edge carries
`attribute_prior` + `manufacturer_assertion` evidence (0.75/n=4, single-source
manufacturer-primary, same tier as Coleman-Mach's `9420-352`/`9420A382` edges). Given the
~40-row scale, validation is **structural** (required fields present, `applies_to` is a
non-empty subset of the 5 known host models) rather than per-row hardcoded expected
values — the "bulk catalog ingestion" trade-off discussed and deferred earlier in this
project's history, scoped tight to just this one table rather than built as a general
ingestion pipeline. `ground-truth.yaml`'s own fixture entry for this data is correspondingly
light: total counts (40/119) plus three spot-checks, not an itemized entry per part —
see `atwood_pilot_repair_parts_fixture` in that file.

Examples: `92610` (Gas Line Grommet), `90960` (Flue Box & Gasket), `91602`/`91601`
(Robertshaw/White Rodgers thermostats), and `91928` (corner brackets) fit all 5 models.
`93914` (10-gallon main burner orifice) fits only `GC10A-2`. `91591`/`91596` (110VAC
conversion kits) are capacity-specific: 6-gallon fits `G6A-7`/`G6A-7P`, 10-gallon fits
`G10-2`. Two rows (`91857` Drain Plug, `92698` Petcock Drain Valve) have no `X` marks in
any edition captured so far — genuinely no fitment data given via this table (the manual
handles them with a "measure drain coupling" instruction instead), not a gap in extraction.

`edge_resolver.py --check-fixture`: 0 mismatches (40 parts, 119 edges, all 3 spot-checks
pass). `pytest`: 25/25 green.

### 7.3 Third wave: Electronic Ignition repair-parts cross-reference (obs #96)

Same manual, same edition (January 2007), same extraction method (§7.1) applied to the
Electronic Ignition table (pp.35-36, 15 model-group columns instead of the Pilot table's
12), scoped to the 8 already-built Electronic models: `GH6-8E`, `G6A-8E`, `G10-3E`,
`GH10-3E`, `GCH6A-10E`, `GC6AA-10E`, `GC10A-4E`, `GCH10A-4E`.

**47 repair-part components, 248 `fits` edges** — `atwood_electronic_repair_parts_and_fits()`
in `edge_resolver.py`, resolver version `atwood_fits_v2`. Same evidence tier and validation
approach as §7.2. `ground-truth.yaml`'s fixture entry is the same shape: total counts
(47/248) plus four spot-checks, in `atwood_electronic_repair_parts_fixture`.

The coordinate-based extraction method held up on a larger, denser table and gave an
internal consistency check for free: part `91802` ("Drawn Pan (Electronic 6 Gallon)")
resolved to exactly the four 6-gallon models among the 8 (`GH6-8E`, `G6A-8E`, `GCH6A-10E`,
`GC6AA-10E`), and its 10-gallon sibling `93871` to three of the four 10-gallon ones
(`G10-3E`, `GC10A-4E`, `GCH10A-4E` — not `GH10-3E`, plausibly because that model's heat
exchanger needs a different drawn pan; not investigated further). A part's own
gallon-capacity-specific description landing on exactly the capacity-matching model subset,
independently for two different rows, is a strong sanity check that column alignment
extraction is correct, not a coincidence.

Two columns in this table's own header (`GCH6A-10E`/`GC6AA-10E` share one column;
`GC10A-4E`/`GCH10A-4E` share another) mean several rows apply to pairs of our built models
at once rather than being separable — e.g. `91230` ("Switch 12 VDC - White Combo") fits both
`GCH6A-10E` and `GC6AA-10E`, with no way to tell from this table alone whether it fits one,
the other, or genuinely both; the manual's own bracket says both, so both get the edge.

`edge_resolver.py --check-fixture`: 0 mismatches (47 parts, 248 edges, all 4 spot-checks
pass). `pytest`: 25/25 green. Combined Atwood repair-parts total across both tables: **87
components, 367 `fits` edges.**

## 8. Fourth wave: GH6-6E in-hand teardown anchor (obs #111, #112) — issue #33

The first Atwood component built from an owner-photographed physical unit rather than
catalog text alone — the gap explicitly called out in the header above and in issue #13.

**Identity settled only after two rounds of independent verification.** The GitHub issue
was opened as "GH6-GE" and an attached AI-generated research report (`GH6-6E-Research.md`)
claimed the true reading was `GH6-6E`, flagging `GH6-GE` as a probable
misreading. `GH6-GE` doesn't fit Atwood's own Pilot/Electronic model-number grammar (§3 —
no digit precedes the terminal `E`), and a web search found zero independent hits for the
literal string. The owner re-examined the physical data-plate photo directly and confirmed
`GH6-6E` is correct — matching the attached report, not the issue title. The report's Spec
number (`260038`) was also independently re-verified against the photo and corrected to
`266038`. Settled plate values: **model `GH6-6E`, spec `266038`, serial `96266000345`**,
6 gal, 8,800 BTU/h input, 7.40 gal/h recovery, 11 in wc min gas pressure, 10 in wc manifold
pressure, 150 psi max working pressure, 300 psi test pressure — all obs #111
(`dataplate_photo`, tier 2).

**Corroborating evidence came from a primary source, not the attached report's secondhand
quotes.** The report cited a 1994 Winnebago WF424RC parts catalog; rather than trust that
citation, the actual PDF was located and read directly (obs #112, `manufacturer_pdf`, tier
2 — a genuinely independent third-party OEM catalog, not Atwood's own literature). It
confirms Winnebago part `051393-01-000` = "WATER HEATER-W/MOTOR AID-PILOTLESS
IGNITION(GH6-3E,GH6-4E OR GH6-6E)" (corroborating the report's model-family claim) and
names Atwood part `91642` as the front-mount inner tank for "GH6-4E & 6E" (Winnebago part
`051391-04-704`).

**Built now:** the GH6-6E endpoint component (`atwood_gh6_6e_component()`, resolver version
`atwood_gh6_6e_v1`) and tank `91642` as a repair-part `fits` edge
(`atwood_gh6_6e_tank_91642_fits()`, resolver version `atwood_gh6_6e_parts_v1`) — **1
endpoint component, 1 repair-part component, 1 `fits` edge.**

**Deliberately NOT built now** (scoped out — anchor + high-confidence parts only, per an
explicit scope decision): the report's remaining ~15 Atwood part numbers under the same
catalog heading, several with supersession-chain or disputed claims that are single-source
or internally contradictory in the report itself — circuit board (`91420` →
`93867`/`93865` → `91367`), electrode (`91606` → `93868`), gas valve (`91605` → `93870` →
`93844`+`94787`), orifice (`92742` → `92743`), drain plug (`91561` → `91857`), a disputed
thermostat (`91470`) calibration claim (120°F vs 130°F), and a contradictory electric-element
(`91580`) listing. Spun off to a follow-up GitHub issue for dedicated research rather than
built on this pass's evidence.

`edge_resolver.py --check-fixture`: 0 mismatches. `pytest`: all green.

## 9. Fifth wave: GH6-6E gas-valve supersession chain (obs #115, #116) — issue #42

Issue #35's deferred gas-valve item ("91605 -> 93870 -> 93844 + 94787") was split into
issue #42 for dedicated research. The attached AI research report (`91605-Research.md`,
issue #42) was reviewed against the three local Atwood service manuals rather than taken
on trust — the project's established standard (§7.1, §8). That review is posted as a
comment on issue #42; the summary:

**Buildable, primary-verified:** `93870 -> 93844` for GH6-6E. Atwood's own January 2014
"Replacement Part Reference" table (obs #116, direct `pdftotext -f`/`pdftoppm` page read,
not OCR guesswork) combines both part numbers into one row — `"93870/93844 White Rodgers
Valve (6&10 Gal.)"` — with GH6-6E checked. Cross-checked against the January 2007 edition,
whose native-text table lists only `93870` (also checked for GH6-6E) and does not yet name
`93844`, confirming the combined listing is a later factory revision rather than an
extraction artifact from the 2014 scan's known OCR gaps (§2).

**Buildable, secondary-tier:** `91605 -> 93870`. No Atwood factory document names `91605`
at all (grepped all three local manuals; zero hits). Built instead from obs #115: Leisure
Vehicle Services' 2012 Atwood spares list ("91605 Replaced by 93870"), cross-checked
against a direct `pdftotext` read of the 1995 Winnebago ICF23RC Parts Catalog PDF — not
secondhand from the attached report. That catalog lists `91605` as "VALVE-GAS" under its
"WATER HEATER W/ELECTRIC IGNITION" (G6A-7E) section and `93870` as "SOLENOID VALVE AND
BRACKET" under its "WATER HEATER W/MOTOR AID" (GH6-7E) section, both at the identical
Winnebago-internal key part number `051393-01-726` — corroborating without independently
proving chronological supersession (two adjacent model sections, not one model's revision
history), so this edge is built at retailer-tier evidence (`atwood_91605_93870_supersession()`
in `edge_resolver.py`), one notch below the manufacturer-sourced `93870 -> 93844` step.

**Not built:** the report's `93243 -> 94787` bracket claim for GH6-6E. Column-by-column
verification of all three local manuals (2003, 2007, Jan 2014 — including a rendered-page
visual check, not just `pdftotext` column-position guessing) shows `94787` is never
checked for GH6-6E in any edition. `93243` is checked for GH6-6E in the 2003 edition,
marked "No Longer Available" by the Jan 2007 edition, and labeled OBSOLETE in Jan 2014 —
with no GH6-6E successor marked in any edition. The report's bracket chain comes from
other models' parts lists (G6A-2E, GC6A-7E), over-generalized to GH6-6E. Left as an open
question on issue #42 rather than built.

3 new repair-part components (`91605`, `93870`, `93844`, `part_type_id: 413`), 2 `fits`
edges (`93870`/`93844` -> GH6-6E), 2 `supersedes` edges (`91605`->`93870`, `93870`->`93844`)
— `atwood_gh6_6e_gas_valve_chain()` and `atwood_91605_93870_supersession()` in
`edge_resolver.py`, resolver version `atwood_gh6_6e_valve_v1`.

`edge_resolver.py --check-fixture`: 0 mismatches. `edge_resolver.py --self-test`: PASS.
`pytest`: 52/53 (the one failure, `test_part_types_cover_every_exported_constant`, predates
this work — a gap from the Coleman AC 48253B866 build (commit `9063edd`) never adding
`COLEMAN_AC_PART_TYPE`/`COLEMAN_AC_REPAIR_PART_TYPE` to that test's registry check).

## 10. Sixth wave: XT repair-parts cross-reference (obs #119) — closes issue #14

The gap §6 item 4 called out: the 6 EXT-family models (`G9-EXT`, `GE9-EXT`, `GEH9-EXT`,
`G16-EXT`, `GE16-EXT`, `GEH16-EXT`) don't appear in either Pilot or Electronic Ignition
"Replacement Part Reference" table — the same January 2007 manual covers them separately,
under its own "XT Water Heater Part Identification" table (p.38), extracted with the same
coordinate-precise `pdftotext -bbox` method as §7.1.

**Shape differs from the Pilot/Electronic tables.** Those bracket by individual model (one
column per model). This table brackets by tank size only (a "6 GALLON"/"10 GALLON" column
pair), under three section headers — Spark Ignition, Heat Exchange, Combination
Gas/Electric — that turned out to describe the assembly diagram each part is drawn in, not
a power-type restriction. Confirmed against p.37 (the same manual's `92690` valve-kit
install instructions, which name only "10 GALLON XT" with no power-type qualifier) and
against the table itself, where three Combination Gas/Electric items (`90029` Mixing
Valve, `90030` Ball Valve, `90034` Elbow) print the identical part number in both size
columns. Only the section's two `NS` (not-shown-in-diagram) rows — `92249` Heating Element
& Gasket, `93849` Relay — are genuinely electric-only components and stay restricted to
the four gas_electric EXT models (`GE9-EXT`, `GEH9-EXT`, `GE16-EXT`, `GEH16-EXT`); every
other part on the page applies to all 6 EXT models (Spark Ignition section) or every model
of the matching tank size (the rest of the Combination Gas/Electric section).

**One row deliberately left unbuilt.** Item 21A ("9" Hose (6 Gallon)") prints the same
part number, `90032`, as item 20's 10-gallon Tee — a real duplicate in the manual's own
table, coordinate-verified, not an extraction error. A Tee and a hose sharing one SKU is
physically implausible, so `90032` is only built as the Tee; the 6-gallon-hose row is
unasserted pending manufacturer clarification.

**14 of the 22 XT part numbers already existed as components from the Pilot and/or
Electronic tables** — the XT family's spark-ignition hardware (switches, circuit board,
wiring harness, thermal cut-off, spark probe, relief valves, flue box, drain plug, solenoid
valve) is largely the same generic service stock as the Electronic-ignition family's, just
described slightly differently table-to-table (e.g. `91230` is obs #96's "Switch 12 VDC -
White Combo" and this table's "Dual Switch" — same part). `atwood_ext_repair_parts_and_fits()`
looks up each part number first and, on a hit, adds this table's description as a second
attribute observation and its edges onto the existing component instead of minting a
duplicate `atwood` identifier. Checking this surfaced a **pre-existing, separate gap**:
the Pilot and Electronic tables don't cross-check each other the same way, and 17
`(ns, value)` pairs between them already resolve to two different components (e.g. `90960`
Flue Box & Gasket exists as both `..._part_90960` and `..._epart_90960`). That predates
this change, is out of scope for issue #14, and is now surfaced as a non-blocking `NOTE` by
a new `check_fixture()` invariant rather than silently left — see issue #48.

**8 new repair-part components, 116 `fits` edges** (of which 10 land on the reused `91230`
component, joining its existing 4) — resolver version `atwood_fits_v3`. Same structural
validation approach as §7.2/§7.3; `ground-truth.yaml`'s fixture entry
(`atwood_ext_repair_parts_fixture`) follows the same total-counts-plus-spot-checks shape.

`edge_resolver.py --check-fixture`: 0 mismatches (22 parts, 116 edges, all 4 spot-checks
pass; 17-pair pre-existing-duplicate NOTE is informational). `edge_resolver.py --self-test`:
PASS. `pytest`: 46/46 green (one snapshot test, `test_atwood_repair_part_is_served_from_the_
persisted_database`, updated to reflect `91230`'s now-merged description/edge count — a
real data change, not a test patch). Atwood repair-parts total across all three tables:
**95 components, 483 `fits` edges** (87 + 8 new; 367 + 116 new, minus double-counting
none — the merged edges are additive on the existing `91230` component, not a separate
total).

## 11. Seventh wave: GH6-6E electronic-table parts (obs #128, #129) — closes #35's remaining children

Issue #35's deferred low-confidence items — split into #40 (circuit board), #41
(electrode), #43 (orifice), #44 (drain plug), #45 (thermostat calibration), and #46
(electric element), with the gas-valve item already closed via #42 (§9) — are resolved by
re-reading the same Electronic Water Heaters Replacement Part Reference table already used
for the endpoint/valve builds (obs #96/#116), this time at GH6-6E's own column. Neither
earlier read had captured it: obs #96 (Jan 2007) was scoped to the 8 Electronic models
built before GH6-6E existed as a component; obs #116 (Jan 2014) was read only for its
combined valve row. Two fresh observations — #128 (Jan 2014) and #129 (Jan 2007) — read
both editions' full disputed-row set via the same coordinate-precise `pdftotext -bbox`
column matching as §7.1, independently corroborating or refuting the AI research report
attached to #35's children per the "second document family" standard.

**Confirmed GH6-6E-applicable in both editions:** `93865` (circuit board, spade electrode
connection), `93868` (electrode, local sense), `92742` (6-gallon main-burner orifice),
`91857` (drain plug kit 1/2") — closing #41, #43, #44, and half of #40. `91857`'s 2014 row
has no extractable text label in the source PDF (a text-layer gap specific to that one
row); confirmed via direct visual read and corroborated by the adjacent "92698 Petcock
Drain Valve" row directly below it, which checks exactly the single column 91857 skips —
the two rows partition the model set with no overlap, confirming the bbox row/column
alignment. All 5 parts already existed as components (built by the Pilot/Electronic
batches, §7/§9) for other models — looked up by identifier rather than re-minted (same
pattern as §10's XT table), and given a new `fits` edge to GH6-6E, double-sourced against
both editions.

**`91470` (front-mount thermostat) — #45 resolved as a genuine specification revision, not
a contradiction.** obs #129 (Jan 2007) states "130°"; obs #128 (Jan 2014) states "120°" for
the identical part number and model. A plain-text grep of the undated (2003) edition
independently confirms 130° there too, so the value was stable from at least 2003 through
2007 and was revised down to 120° by January 2014. Both values are kept — the existing
"description" attribute from obs #96 (130°, 2007) is left as-is, and a new
`thermostat_setpoint_f` attribute (120°, source obs #128) is added alongside it, since
ground-truth.yaml's per-component attributes are name-keyed and can't hold two values
under the same "description" key.

**Confirmed inapplicable to GH6-6E in both editions, closing #46:** `91580` (110VAC
bolt-on electric element) is checked only for the combination gas/electric `GCH6-6E` model
and the `G10-2E`/`G10-3E` family — not `GH6-6E`, whose own in-hand dataplate (obs #111,
already in this fixture) records `power_type: gas_only`. The report's apparent confusion
was almost certainly `GCH6-6E` (checked) vs. `GH6-6E` (gas-only, not checked) — visually
similar model numbers one letter apart. Not built as a component or edge for GH6-6E.

**Zero applicability in either edition, closing the other half of #40 and all of #41's
"chain" framing:** `91420` (circuit board, post-electrode-connection), `91504` (a bundle
SKU, "Includes 93865 & 93868"), and `91606` (remote-sense electrode) each show zero
checked models across both tables — not GH6-6E-specific rejections, genuinely inapplicable
to every current model either edition lists. None carries the explicit "(USE X)"/"OBSOLETE"
wording the fan-motor or gas-valve rows use, so none is built as a `supersedes` edge —
there is no multi-hop chain in either manufacturer document, only a real current part
(`93865`/`93868`) and a real but currently-unavailable old one, with no stated relationship
between them.

**Four numbers named in the attached research report do not appear anywhere:** `93867`/
`91367` (#40's claimed further chain hops) and `92743`/`91561` (#43/#44's claimed
successor/predecessor) — grep-verified against obs #128, obs #129, and all three other
locally held Atwood PDFs, zero hits for all four. None is built.

0 new components (all 5 parts already existed), 5 new `fits` edges, 1 new attribute —
`atwood_gh6_6e_electronic_table_parts()` in `edge_resolver.py`, resolver version
`atwood_gh6_6e_electronic_table_v1`. `ground-truth.yaml`'s fixture entry
(`atwood_gh6_6e_electronic_table_fixture`) follows the same total-counts-plus-spot-checks
shape as §7/§9/§10.

`edge_resolver.py --check-fixture`: 0 mismatches. `edge_resolver.py --self-test`: PASS.
`pytest`: 46/46 green. Issues #35, #40, #41, #43, #44, #45, #46 all closed.
