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

- `Docs/Data/Atwood/Atwood-Water-Heaters.pdf` — Atwood Mobile Products, LLC's own service
  manual (50 pages; earliest page dated 2004, revision pages through 2019). Covers Pilot
  models, Electronic Ignition & XT models, general water heater information, and parts
  breakdowns/replacement-part cross-reference tables (pp. 21-36) for both families.
  `www.atwoodmobile.com`, support line 866-869-3118 (both named in-document).

Not yet captured: any Atwood retailer pages, Wayback Machine history, an in-hand unit's
rear-label/data-plate photographs, or the manual's later "Replacement Part Reference"
tables (pp. 21-36, 30-36) — those are shared-parts-by-model-group tables (which universal
repair part fits which model bracket), not old-model-to-new-model supersession charts, and
are a different, not-yet-built kind of relationship. See §4.

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

## 6. Resolver status and next milestone

First wave complete: 19 exact endpoint components, no supersession/substitution edges yet
(none stated in the manual's catalog table itself — that evidence, if it exists, lives in
the separate parts-breakdown/cross-reference tables, not yet parsed).

Ready-to-do next work, in rough priority order:

1. Parse the manual's "Replacement Part Reference" tables (pp. 21-24, 30-36) — these are
   shared-repair-part-by-model-group charts (which universal part number fits which
   bracket of models), a genuinely different relationship than Coleman's old-model ->
   new-model supersession edges. Needs its own edge/relationship shape decision before
   building, not a direct reuse of `resolve_coleman_supersessions()`'s pattern.
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
