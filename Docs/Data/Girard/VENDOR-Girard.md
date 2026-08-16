# VENDOR — Girard

**Status:** exact endpoint component built (`c_placeholder_wh_girard_gswh2`,
part_type_id `419`, resolver version `girard_endpoint_v1`) plus three cross-vendor
`substitutes` retrofit edges into existing Atwood/Suburban tank-unit components.
`edge_resolver.py --check-fixture` confirms 0 mismatches.
**Vendor position:** 6th Stage 1 vendor (after Suburban, Coleman-Mach, Atwood, Norcold,
Furrion)
**Updated:** 2026-08-16 — pass 2, built from four manufacturer PDFs (sell sheet,
troubleshooting/service manual, owner's manual, aftermarket conversion-door addendum)
linked in a GitHub issue #53 comment, on top of pass 1's in-hand teardown photographs.

## 1. In-hand unit

A Girard tankless propane water heater, photographed 2026-08-16 (issue #53, 2
photographs). Photos saved locally in `Docs/Data/Girard/GSWH-2 Images/`; the GitHub
comment attachment URLs are the observations' citable `url` field.

| Field | Value | Source |
|---|---|---|
| Model | `GSWH-2` | obs #135, interior rating/compliance label |
| Lippert PN | `2022107534` | obs #138, service manual title page ("MODEL (LIPPERT PN) GSWH-2 (2022107534)") |
| Manufacturer | Girard Products, LLC — 1361 Calle Avanzado, San Clemente, CA 92673 — www.greenrvproducts.com | obs #135 |
| Serial number | `2GWH0303465` | obs #135 (rating label) and obs #136 (exterior back-panel barcode) — same value on both, confirming one physical unit |
| Product type | Tankless water heater, induced draft, direct vent | obs #135 |
| Fuel | Propane (LP gas) | obs #136 |
| Ignition | No pilot — automatic ignition device | obs #135 |
| Compliance | ANSI Z21.10.3-2019 / CSA 4.3-2019, ETL listed (Intertek) | obs #135 |
| Input | 42,000 BTU/h | obs #137, obs #138 |
| Power | 12VDC, <3A | obs #136, obs #137, obs #138 |
| Inlet gas pressure | 11in WC min – 14in WC max | obs #136 (14in max), obs #138 (11–14in range) |
| Manifold pressure | 1.5–7.8in WC | obs #138 |
| Max water operating pressure | 125 PSI | obs #138 |
| Physical unit size (W×H×D) | 12.5 × 12.5 × 15.5in | obs #138 |
| Shipping weight | 22lb | obs #138 |
| Unit weight | 23lb | obs #137 |
| ECO cutoff | 140°F | obs #138 |
| Rough opening (fresh install) | 13in × 13in, right-angle corners | obs #139, corroborated by obs #140 |

**Manufacturer note:** the in-hand unit's own label reads "Girard Products, LLC," and
its own printed website is `www.greenrvproducts.com` — not `girardrv.com`. Namespace
built as `girard` (the label's own company name). Pass 1 found no Lippert mark
anywhere on the physical unit and left the Lippert-ownership fact as issue-label/prose
context only; **pass 2 supersedes that** — the service manual's own title page names a
Lippert-issued part number (`2022107534`) for this exact model, so a second identifier
(`lippert`/`2022107534`) is now built on the component, sourced to that document.

## 2. Two numbering families — don't conflate

The sell sheet (obs #137) and service manual (obs #138) reveal two structurally
distinct part-number families on this one product line:

- **`2GWH*`-prefixed numbers** (`2GWHDAS10`, `2GWHDA6`, `2GWHD`, `2GWHDTR-B`, ...) are
  Girard-native **aftermarket conversion door/flange kits** — accessories sold
  separately to retrofit a GSWH-2 into an existing tank water heater's cutout. Built
  under namespace `girard`.
- **`2022107xxx`-prefixed numbers** are the unit's **own internal replaceable parts**
  (control board, gas valve, burner, etc. — service manual's Replaceable Parts List,
  ~44 rows) plus the unit's own Lippert PN (`2022107534`) itself. These read as a
  Lippert-issued numbering scheme, not Girard-native — see §5's deferred scope.

These are never the same part number appearing twice; they simply share a similar
`20221xxxxx`-shaped numeric range by coincidence of Lippert's corporate numbering, not
because they're related components.

## 3. Retrofit edges — GSWH-2 replacing existing Atwood/Suburban tank units

The aftermarket conversion-door addendum (obs #140, Girard's own installation manual
addendum) documents three retrofit paths, each built as a `substitutes` edge (existing
tank unit → GSWH-2), `basis: manufacturer_documented`, `verdict: fits_with_modification`,
with a `requires_part` conversion kit and blocking caveats:

| Edge group | Target | Existing cutout | Kit | Confidence |
|---|---|---|---|---|
| `girard_retrofit_atwood_6gal` | `c_placeholder_wh_atwood_6gal` (family placeholder) | 16.25 × 12.625in | `2GWHDA6` | 0.80 |
| `girard_retrofit_atwood_10gal` | `c_placeholder_wh_atwood_10gal` (family placeholder) | 16.25 × 15.75in | `2GWHDAS10` | 0.80 |
| `girard_retrofit_suburban_10_12gal` | `c_placeholder_wh_12del` (real SW12DEL component) | 16.25 × 16.25in (addendum) vs. 16.38 × 16.38in (SW12DEL's own retailer-spec cutout) | `2GWHDAS10` | 0.80 |

This is the **opposite shape** from Suburban's own IW60RL retrofit edges
(`resolve_iw60rl_retrofit_edge`, `VENDOR-Suburban.md`): IW60RL's replacement panels
*cover* a larger existing tank cutout without resizing it. Girard's GSWH-2 opening
(13in × 13in) is *smaller* than every target cutout, so the conversion kit instead
**reframes the opening down** — the flange must be supported on all sides by a new
wooden frame, mounted with #8 ¾in flat head screws, plus one or two 2×2in vertical
braces depending on the gap. Both Atwood targets also carry a blocking caveat that the
kit doesn't cover the corners of an Atwood *flush mount* door — the installer must
fabricate a corner cover; this issue does not apply to a Suburban flush mount door
(stated explicitly, verbatim, on both addendum pages).

The Suburban target is the real `c_placeholder_wh_12del` (SW12DEL) component rather
than a family placeholder, but its confidence is docked to 0.80 (matching the Atwood
edges, not IW60RL's higher 0.833 Suburban tier) — the addendum's own worked example is
titled "10 GA. SUBURBAN," not SW12DEL specifically, and its 16.25in cutout figure is
within ⅛in of SW12DEL's own 16.38in retailer-spec-block cutout. The sell sheet's kit
table description ("REPLACES 10-12 GALLON SUBURBAN AND ATWOOD") is what bridges the gap
between "10 GA" and the 12-gallon SW12DEL, treating the ⅛in difference as ordinary
rounding between two documents rather than a distinct physical opening — a reasonable
inference, not a certain one, hence the lower tier.

No dimensional retrofit edge was built for the 6-gallon Suburban target (`2GWHD` /
`2GWHDB` kit) — it's named in the sell sheet's part table but no addendum page
supplying its cutout dimensions was found this pass.

## 4. Thin-evidence framing from pass 1 is now superseded

Pass 1 (obs #135/#136, in-hand photos only) found no spec table on either physical
label and described this as a thinner first pass than Furrion's. Pass 2's four
manufacturer PDFs supply the full spec table (§1) that was missing — the "no BTU
input, no GPM capacity, no rough-opening dimensions" framing from pass 1 no longer
describes this component's evidence base, only what was visible in the two original
photographs.

## 5. Deliberately not built this pass

- **The ~44-row Replaceable Parts List** (service manual obs #138, callouts A–AS,
  part numbers `2022107535`–`2022107598`) — mechanical bulk on the scale of Atwood's
  87-part repair-parts cross-reference. Logged in obs #138's note for citation only.
  Deferred to a follow-up pass so this commit stays reviewable; issue #53 stays open
  for it.
- **Namespace for the `2022107xxx` internal parts** — plausibly `lippert` given the
  service manual's own Lippert-PN framing for the host unit, but not yet decided; will
  be settled when the parts list is actually built.
- **General Troubleshooting / error-code table** (service manual) — logged in obs
  #138's note for citation only, not built as component data.
- **6-gallon Suburban retrofit edge** — no cutout-dimension source found this pass
  (§3).
- **Lippert's own corporate product page**
  (`corporate.lippert.com/about/brands/girard/tankless-water-heater`) — fetch attempt
  returned no usable content (likely a JS-rendered page); not cited as a source.

## 6. Sources

- obs #135 — interior rating/compliance label photograph (model, manufacturer,
  serial, compliance standards, no-pilot/ignition statement)
- obs #136 — exterior back-panel photograph (serial barcode corroboration, 12VDC
  power legend, 14in WC max LP gas pressure, HOT/COLD fitting labels)
- obs #137 — sell sheet PDF (2022111638-RA): BTU/power/weight bullets, 8-row
  conversion-kit part table
- obs #138 — Troubleshooting and Service Manual PDF (CCD-0009390): Lippert PN, full
  Technical Specifications table, Replaceable Parts List (not built), error-code table
  (not built)
- obs #139 — Owner's Manual PDF (CCD-0006120): 13in × 13in rough opening for a fresh
  install
- obs #140 — Installation Manual Addendum for after Market Installations PDF: per-kit
  existing-cutout dimensions, bracing requirements, Atwood flush-mount-door corner
  caveat

## 7. Resolver status

`girard_gswh2_component()` builds the endpoint from obs #135/#136/#137/#138/#139,
cross-checking the rating-plate/back-panel serial match and each pass-2 document's
model/Lippert-PN claim before persisting. `girard_gswh2_retrofit_edge()` builds the
three retrofit edges from obs #140, one call per target family. Both wired into
`edge_resolver.py`'s `check_fixture()`/`build_database()`.
`part_types.GIRARD_PART_TYPE = 419`; `manufacturers.py` adds `ns="girard"` and
`ns="lippert"`. `resolver.py` gains eleven new canonical fields
(`max_gas_pressure_in_wc`, `manufacturer_address`, `manifold_pressure_min_in_wc`,
`manifold_pressure_max_in_wc`, `eco_max_temp_f`, `unit_weight_lb`,
`shipping_weight_lb`, `lippert_part_number`, `product_size_h`, `product_size_w`,
`product_size_d`) plus a `conversion_kits` alias onto the existing `accessory_data`
catch-all — `python3 resolver.py --self-test`
and `--validate` both pass, with obs #135–#140 fully mapped (no unmapped keys).
`edge_resolver.py --self-test` and `--check-fixture` both pass at 0 mismatches;
`components.db` rebuilt via the canonical `--build` command.
