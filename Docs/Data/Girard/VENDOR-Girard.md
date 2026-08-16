# VENDOR — Girard

**Status:** exact endpoint component built (`c_placeholder_wh_girard_gswh2`,
part_type_id `419`, resolver version `girard_endpoint_v1`). `edge_resolver.py
--check-fixture` confirms 0 mismatches.
**Vendor position:** 6th Stage 1 vendor (after Suburban, Coleman-Mach, Atwood, Norcold,
Furrion)
**Updated:** 2026-08-16 — first pass, built from the owner's in-hand teardown photographs
attached to GitHub issue #53.

## 1. In-hand unit

A Girard tankless propane water heater, photographed 2026-08-16 (issue #53, 2
photographs). Photos saved locally in `Docs/Data/Girard/GSWH-2 Images/`; the GitHub
comment attachment URLs are the observations' citable `url` field.

| Field | Value | Source |
|---|---|---|
| Model | `GSWH-2` | obs #135, interior rating/compliance label |
| Manufacturer | Girard Products, LLC — 1361 Calle Avanzado, San Clemente, CA 92673 — www.greenrvproducts.com | obs #135 |
| Serial number | `2GWH0303465` | obs #135 (rating label) and obs #136 (exterior back-panel barcode) — same value on both, confirming one physical unit |
| Product type | Tankless water heater, induced draft, direct vent | obs #135 |
| Fuel | Propane (LP gas) | obs #136 |
| Ignition | No pilot — automatic ignition device | obs #135 |
| Compliance | ANSI Z21.10.3-2019 / CSA 4.3-2019, ETL listed (Intertek) | obs #135 |
| Power | 12VDC (RED/ROUGE +12VDC, BLACK/NOIR −12VDC, REMOTE/TÉLÉCOMMANDE blue) | obs #136 |
| Max LP gas inlet pressure | 14in WC | obs #136 |

**Manufacturer note:** the label reads "Girard Products, LLC," and its own printed
website is `www.greenrvproducts.com` — not `girardrv.com`. Namespace built as `girard`
(the label's own company name), matching this project's convention of naming the
namespace from the unit's own marking rather than from a parent/holding brand. Issue
#53 tags this as `Vendor - Lippert` (Girard's current corporate owner per public
industry knowledge) — that ownership fact is issue-label/prose context only; no Lippert
identifier or namespace is asserted on this component, since nothing on the unit itself
carries a Lippert mark. Same restraint as Furrion/Norcold: don't assert what the
evidence doesn't show.

## 2. Single identifier — no coexisting-pair finding this time

Unlike Norcold's `N811`/`N811RT`, Coleman-Mach's `AP7862`/`7330G335` and
`AR7815`/`7330F3858`, and Furrion's `FWH09AFA-AM`/`FWH09A-AM`, this unit carries only
one model number anywhere legible in the two photographs: `GSWH-2`, printed on the
interior rating/compliance label (obs #135). No second internal chassis label was
photographed this pass. Built with a single identifier
(`girard`/`GSWH-2`, visibility `rating_plate`).

## 3. Thin evidence this pass — no spec table

The interior rating/compliance label (obs #135) that names the model and compliance
standards carries no printed spec table at all — no BTU input, no GPM capacity, no
rough-opening dimensions, no gas-pressure figures. It is warning/compliance text only
(installation-code citations, pilot/ignition statement, pressure-relief-valve warning,
WARNING/FOR YOUR SAFETY/WHAT TO DO IF YOU SMELL GAS blocks). The only two numeric specs
available this pass — 12VDC power and 14in WC maximum LP gas inlet pressure — come from
a second label on the exterior back panel (obs #136), which is otherwise a wiring/
plumbing-connection panel (HOT/COLD fitting call-outs, a MAX/MIN temperature-adjustment
knob on the cold side, POWER/POUVOIR wire-color legend), not a rating plate.

This is a thinner first pass than Furrion's (which had a full altitude/BTU/orifice
table) — same shape as Norcold's initial `N811` build before its parts-catalog work.
No BTU input, no GPM capacity rating, and no rough-opening dimensions are recorded
because none were legible in either photograph.

A separate wire tag visible in obs #136 ("+12VDC Power / 240 VOLTS AC... THESE
CONNECTIONS ARE FOR LOW-VOLTAGE-BATTERY OR DIRECT CURRENT ONLY. DO NOT CONNECT TO 120 OR
240 VOLTS AC") is a generic wiring-safety warning printed on the wire itself, not a unit
spec — logged in the observation's note for citation only, not built as a component
attribute.

## 4. Deliberately not built this pass

- **No `fits`/repair-part edges.** Neither label names a required accessory part the
  way Furrion's safety label named its flue damper — a zero-edge endpoint is fine here,
  same as Norcold's deliberately edge-free first pass. Don't manufacture an edge to
  have one.
- **No BTU input, GPM capacity, or rough-opening dimensions** — not legible in either
  photograph (see §3).
- **No catalog/retailer corroboration, no Lippert-brand cross-reference, no second
  Girard water-heater model.** From-scratch vendor arc with a single in-hand unit and
  no catalog research pass yet. Issue #53 left open for a pass 2 (full spec sheet from
  `greenrvproducts.com` or a Girard/Lippert install manual, once available).

## 5. Sources

- obs #135 — interior rating/compliance label photograph (model, manufacturer,
  serial, compliance standards, no-pilot/ignition statement)
- obs #136 — exterior back-panel photograph (serial barcode corroboration, 12VDC
  power legend, 14in WC max LP gas pressure, HOT/COLD fitting labels)

## 6. Resolver status

`girard_gswh2_component()` builds the endpoint from obs #135/#136, cross-checking that
both labels' serial numbers match before persisting. Wired into `edge_resolver.py`'s
`check_fixture()`/`build_database()`. `part_types.GIRARD_PART_TYPE = 419`;
`manufacturers.py` adds `ns="girard"`. `resolver.py` gains two new canonical fields
(`max_gas_pressure_in_wc`, `manufacturer_address`) — `python3 resolver.py --self-test`
and `--validate` both pass. `edge_resolver.py --self-test` and `--check-fixture` both
pass at 0 mismatches; `components.db` rebuilt via the canonical `--build` command.
