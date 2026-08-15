# VENDOR — Furrion

**Status:** exact endpoint component built (`c_placeholder_wh_furrion_fwh09afa_am`,
part_type_id `418`, resolver version `furrion_endpoint_v1`); one repair-part `fits` edge
built (`c_placeholder_furrion_part_jsq6075fdf1cz`, `furrion_parts_v1`). `edge_resolver.py
--check-fixture` confirms 0 mismatches.
**Vendor position:** 5th Stage 1 vendor (after Suburban, Coleman-Mach, Atwood, Norcold)
**Updated:** 2026-08-15 — first pass, built from the owner's in-hand teardown photographs
attached to GitHub issue #34.

## 1. In-hand unit

A Furrion tankless propane water heater, photographed 2026-08-15 (issue #34, 5
photographs). Photos saved locally in `Docs/Data/Furrion/FWH09AFA-AM Images/`; the
GitHub comment attachment URLs are the observations' citable `url` field.

| Field | Value | Source |
|---|---|---|
| Exterior rating-plate model | `FWH09AFA-AM` | obs #130, exterior panel nameplate |
| Internal chassis-label model | `FWH09A-AM` | obs #134, label on the burner/blower assembly itself, behind the exterior plate |
| Serial number | `10001121985122100056` | obs #134 |
| Gas code | `FA` | obs #134, adjacent PARAMETERLIST sticker |
| Capacity | 2.4 GPM, tankless | obs #130 |
| Fuel | Propane | obs #130 |
| Input | 60,000 BTU/h | obs #130 |
| Max working pressure | 65 PSI | obs #130 |
| Max outlet water temp | 124°F | obs #130 |
| Power | 12VDC, <3A | obs #130 |
| Rough opening | 12⅝ × 12¾ × 23½ in (321 × 324 × 597 mm) | obs #131, safety/installation label |
| Required flue damper | `JSQ6075FDF1(CZ)` | obs #131 |

## 2. `FWH09AFA-AM` vs `FWH09A-AM` — coexisting, not normalized together

Same shape of finding this project has hit three times before — Suburban's FQ/VHFQ
letters (issue #26), Coleman-Mach's `AP7862`/`7330G335` and `AR7815`/`7330F3858` label
pairs (issue #18), and Norcold's `N811`/`N811RT` (§2 of `VENDOR-Norcold.md`): two
identifiers on one physical unit that look like a conflict but are not asserted to be
generally interchangeable.

The exterior panel nameplate (obs #130) reads `FWH09AFA-AM` — the full spec table, ETL
listing, and altitude conversion data live here. A second, shorter model number,
`FWH09A-AM`, is printed on a separate internal label mounted directly on the
burner/blower chassis itself, one layer inside the exterior panel (obs #134) — alongside
this unit's own serial number and a "PARAMETERLIST" sticker (second/ignition gas
pressures, min/max fan speed, gas code).

**Unlike Norcold's `N811`/`N811RT` case, no manufacturer document found so far decodes
this pair's grammar.** It is *not* asserted here that `FWH09A-AM` is a "base model" and
`FWH09AFA-AM` an order code, or the reverse — that would be guessing a pattern from two
other vendors' unrelated numbering conventions. Both are recorded as coexisting
identifiers on the same physical unit (`furrion`/`FWH09AFA-AM` visibility
`exterior_rating_plate`, `furrion`/`FWH09A-AM` visibility `internal_chassis_label`),
same treatment `interchange_code: null` on the one component. Revisit if a Furrion
manual, catalog page, or support reply ever explains the relationship.

## 3. The flue damper `JSQ6075FDF1(CZ)` — one `fits` edge, built from the unit's own label

The safety/installation label (obs #131) directly names an "automatic flue damper
device Part No. `JSQ6075FDF1(CZ)`" in its own INSTALLATION AND SERVICE paragraph,
worded as a requirement ("must be equipped with... automatic flue damper device Part
No. JSQ6075FDF1(CZ)"), not a cross-sell or retailer note. This is stronger sourcing than
the retailer repair-parts tables that have supplied every other vendor's first `fits`
edge in this project (Atwood, Norcold, Coleman AC/plenum) — it is Furrion's own label,
physically affixed to this exact unit.

The `JSQ` prefix does not match the `FWH`-prefixed unit-model numbering, but that is not
unusual for a repair/accessory part relative to its host unit — Suburban's own interior
switch (`232881`/`232882`/`233111`) and Norcold's board/hose/heater part numbers
(`628674`, `622391`, `630811`...) are likewise numbered independently of their host
unit's model string. Built under namespace `furrion` rather than inventing a new
manufacturer namespace for a single unconfirmed-origin part number.

Built as `c_placeholder_furrion_part_jsq6075fdf1cz` (part_type `418`, same type as the
host water heater — this project's existing convention for water-heater repair parts,
see Suburban's `232881` switch and Atwood's `93870`/`90960` parts, none of which get a
dedicated repair-part part_type_id the way Norcold/Coleman-Mach AC did), with a `fits`
edge (`group: furrion_flue_damper`) to the endpoint component.

## 4. Deliberately not built this pass

- **Rough-opening dims** (§1 table) come only from the safety label's printed figure;
  no independent manufacturer install-manual PDF has been checked yet for corroboration.
- **Wiring diagram** (obs #132) and the **altitude-conversion sticker** (obs #133) are
  logged for citation only — neither contributes a component attribute in this pass.
  The wiring diagram documents a real terminal/sensor interface (ignition pin, flame
  sensor, inlet/outlet temp probes, wind pressure switch, water flow sensor,
  proportional valve, ECO thermostat) that could support a future controls/terminal-map
  build, same shape as Coleman-Mach's thermostat terminal work — not attempted here.
  The altitude sticker is blank (never field-converted) and only corroborates the
  2,000–4,500ft band of obs #130's own table.
- **No supersession, no retailer corroboration, no second Furrion water-heater model.**
  This is a from-scratch vendor arc with a single in-hand unit and no catalog research
  pass yet — same minimal-first-pass shape as Norcold's initial `N811` build before its
  parts-catalog work (§3–4 of `VENDOR-Norcold.md`), not a Coleman-Mach-scale research
  campaign. Retailer/manufacturer-catalog corroboration for the flue damper and rough
  opening, plus any wiring/terminal-map component, is future scope (see GitHub issue
  #34, left open).

## 5. Sources

- obs #130 — exterior rating-plate photograph (model, full spec table, ETL/altitude data)
- obs #131 — safety/installation instructions label photograph (compatibility
  statement, flue damper part number, rough opening)
- obs #132 — control-board wiring diagram label photograph (citation only, not built)
- obs #133 — altitude-conversion sticker / fuse / on-off switch photograph (citation
  only, corroborates obs #130's 2,000–4,500ft band)
- obs #134 — internal chassis label + PARAMETERLIST sticker photograph (second model
  number, serial, gas code)

## 6. Resolver status

`furrion_fwh09afa_am_component()` builds the endpoint from obs #130/#131/#134.
`furrion_flue_damper_fits()` builds the repair-part component and its `fits` edge from
obs #131. Both wired into `edge_resolver.py`'s `check_fixture()`/`build_database()`.
`part_types.FURRION_PART_TYPE = 418`; `manufacturers.py` adds `ns="furrion"`.
`resolver.py` gains seven new canonical fields (`capacity_gpm`, `fuel_type`,
`max_water_temp_f`, `orifice_mm`, `manifold_pressure_pa`, `gas_code`,
`flue_damper_part_number`) — `python3 resolver.py --self-test` and `--validate` both
pass. `edge_resolver.py --self-test` and `--check-fixture` both pass at 0 mismatches;
`components.db` rebuilt via the canonical `--build` command.
