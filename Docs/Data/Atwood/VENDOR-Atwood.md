# VENDOR — Atwood / Atwood Mobile Products

**Status:** first vendor wave built (catalog-only, no in-hand teardown anchor yet)
**Updated:** 2026-08-04 — 19 RV Pilot/Electronic-Ignition water heater models built as exact
endpoint components from Atwood's own service manual.

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

## 6. Resolver status and next milestone

First wave complete: 19 exact endpoint components. Second wave (§7) adds a shared
repair-parts cross-reference for the 5 Pilot models among them.

Ready-to-do next work, in rough priority order:

1. Extend §7's repair-parts cross-reference to the Electronic Ignition table (same manual,
   pp.33-36 in the 2007 edition) for our 8 built Electronic models (`GH6-8E`, `G6A-8E`,
   `G10-3E`, `GH10-3E`, `GCH6A-10E`, `GC6AA-10E`, `GC10A-4E`, `GCH10A-4E`) — larger table
   (15 columns vs. Pilot's 12), not yet attempted.
2. If/when a physical Atwood unit becomes available, add an in-hand teardown observation
   (rear label, data plate, model number) as a real anchor fixture, same role as the
   Coleman-Mach thermostat teardown (obs #44) — the two existing generic
   `c_placeholder_wh_atwood_6gal`/`_10gal` family-placeholder components (Suburban-arc,
   §1 above) are not a substitute for this.
3. Retailer/Wayback Machine research to corroborate or extend the 19-model catalog (e.g.
   confirm current-vs-discontinued status beyond the one `NLA` flag the manual itself
   states, or find later/earlier manual revisions for a production-window timeline like
   Coleman-Mach's D→E→G/F letter progression).
4. `capacity_gal`/`opening_h`/`opening_w` cross-comparison against the existing Suburban
   `opening_families` fixture data (§4's `part_types` block, `Docs/Inital_Design/
   ground-truth.yaml`) — none of these 19 components assert cutout/opening dimensions yet,
   since the manual's catalog table doesn't give them; that would need either the manual's
   own dimensional pages (not yet captured) or a separate retailer spec source.

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

### 7.2 What was built

Scoped to the 5 Pilot models already built as exact endpoint components: `G6A-7`,
`G6A-7P`, `GC6AA-8`, `GC10A-2`, `G10-2` (the Electronic Ignition table's own repair-parts
cross-reference, for the 8 built Electronic models, is not yet attempted — see §6 item 1).

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
