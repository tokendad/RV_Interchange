# VENDOR — D&W International (dwincorp.com)

## 1. Why this vendor, why now

Fills `PLAN-Staged_Build.md` §9 item 9: the ceiling register / round AC grille in
`ground-truth.yaml` (`c_placeholder_register`, part_type 418) carried
`duct_diameter: TODO_measure` since day one — it's the flagship "identity is pure
geometry, no markings anywhere" case the fixture was written to anchor. This is that
measurement, plus a manufacturer/model identification built entirely from geometry
and feature match (no marking on the part itself to search against).

## 2. The part

In-hand round plastic AC grille, white, rotatable louvers that stay open (not a
damper — no fully-closed position), screw-mounted through a flanged trim ring into a
round duct spud. **No markings anywhere** — no part number, no brand, no molded text
on any visible or interior surface photographed. Photos: `Docs/Data/DWIN/Images/20260731_134004.jpg`,
`..._134019.jpg`, `..._134030.jpg`, `..._134103.jpg`. Measurement observation: obs #36
(corrected by obs #39).

## 3. In-hand measurements

| Attribute | Value | Source |
|---|---|---|
| Duct spud diameter | ~5 in | obs #36, photo `134004.jpg` — tape across the inner duct tube |
| Flange (trim ring) outer diameter | ~7 in | obs #36/#39, photo `134019.jpg` — tape across the outer white ring |
| Shape | round | in-hand |
| Actuation | rotatable louvers, always open (no closed/damper position) | in-hand |
| Colour | white | in-hand (display axis only, not interchange key) |

Depth (duct spud protrusion) was **not** independently re-measured to a confident
precision from the in-hand photos — carried from the corroborating catalog spec below
(1-7/8 in) and flagged in `ground-truth.yaml` as pending direct confirmation.

## 4. Identification: D&W International RO-9850

**Manufacturer match:** dwincorp.com (D&W International) — "100% Made in the USA"
AC vents for the RV market. Their vents product listing (obs #38) names a round
plastic grille model **RO-9850** among a family of AC vent SKUs (RO-8950, RO-8841,
RO-8840, RO-5840, RO-8850, RO-6840, RO-9850). The listing page itself publishes no
dimensions — model names only.

**Retailer corroboration:** suremarineservice.com sells the RO-9850 as "9850-White"
(obs #37), and publishes the dimensions the manufacturer page omits:

| Spec (obs #37, retailer) | Published value | In-hand match |
|---|---|---|
| Nominal grille diameter | 5 in | matches ~5 in duct spud reading |
| Duct diameter | slightly over 5 in (5-1/8 in) | consistent — in-hand read is within tape precision on a curved/molded edge |
| Exterior mounting flange diameter | 7 in | matches ~7 in flange reading essentially exactly |
| Duct spud depth | 1-7/8 in | not independently re-measured; carried as-is |
| Feature | "always open with rotatable louvers" | matches in-hand actuation exactly |

Two of three geometry checks land almost exactly on the retailer's published numbers,
and the distinctive "always-open rotatable louver" feature (as opposed to a fully-
closing damper vent, which is the more common style) matches too. That's enough to
treat **RO-9850** as the working identification — but see the confidence caveat below.

## 5. Confidence — this is a geometry match, not a marking read

Unlike the Suburban SW-series work, there is **no data plate, no molded part number,
no marking of any kind** on this part to corroborate against. The identification
rests entirely on:

1. Two measured dimensions matching a retailer's spec block, and
2. One matching qualitative feature (always-open rotatable louvers).

That is real evidence, not a guess, but it is a single retailer's spec block, not a
manufacturer spec sheet with dimensions (D&W's own page names the model but publishes
no numbers), and not a marking read off the unit. In `ground-truth.yaml` this is
recorded as `visibility: unmarked_geometry_match` on the identifier, and the
identification itself is flagged CANDIDATE tier — while `duct_diameter` and
`flange_diameter`, the two `critical_attributes` for part_type 418, are recorded as
`in_hand_measured` and stand on their own regardless of whether the RO-9850 call
turns out to be right.

## 6. Sources

- obs #36 — manual measurement, 4 photos, in-hand
- obs #37 — suremarineservice.com, 9850-White product page (retailer spec block)
- obs #38 — dwincorp.com/products/vents (manufacturer listing page, no dimensions)
- obs #39 — correction to obs #36's flange-diameter reading (6.75in → 7in)

## 7. Open items

- Confirm duct spud depth (1-7/8 in) with a direct in-hand measurement rather than
  carrying it from the retailer spec.
- No teardown of the interior/back side has been photographed — unlike the roof vent
  case (`c_placeholder_vent`), where part numbers are known to hide on interior mold
  faces, this unit hasn't been fully disassembled to rule that out.
- If a second unit or a manufacturer spec sheet with dimensions ever turns up,
  upgrade the identifier off CANDIDATE.
