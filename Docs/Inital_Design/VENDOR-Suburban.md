# VENDOR — Suburban Manufacturing

**Project:** RV Interchange
**Status:** research in progress
**Date:** 2026-07-29
**Adapter priority:** 1 of 7 (first vendor)
**Part families covered here:** water heaters (SW series). Furnaces, ranges/cooktops: not yet started.

---

## 1. Why Suburban first

- Unit physically in hand (SW6DEL) — measurable ground truth.
- Clean, positional model-number grammar.
- Small product line.
- Public manuals and public spec pages.
- Good v0 economics: ~35 lb unit ships UPS ground, unlike fridges or doors.

---

## 2. Sources

| Source | Type | Holds | Trust |
|---|---|---|---|
| Suburban product manuals (PDF) | manufacturer | parts breakdowns, specs | high |
| `suburbanrvparts.com` product pages | retailer (BigCommerce) | **dimensions, cutouts, aliases** | medium |
| `suburbanrvparts.com/model-number-breakdown/` | retailer | **grammar charts — IMAGES ONLY** | high (once transcribed) |
| `suburbanrvparts.com/sw-series-water-heater-parts-diagram/` | retailer | shared-subassembly source | not yet pulled |
| Product page image `alt` / `title` attributes | retailer | sibling specs | **LOW — see §6.1** |

### 2.1 The division of labour between source types

**Manufacturers publish specs. They do not publish aliases or supersessions.**

Those live in **retailer copy**:
- `5240A = 5140A = SW6DEL` came from a product blurb.
- An element "replaces 520789" came from a parts-diagram page.

> The messiest source is the most valuable one. Manufacturer data seeds the catalog;
> retailer copy builds the crosswalk.

### 2.2 Adapter note: the grammar is not text

`/model-number-breakdown/` carries the canonical decoding charts for water heaters,
furnaces, **and** cooktops — all three as screenshots. No parseable text.

**Action:** transcribe by hand, once. Cheap. That transcription is the parser spec for the
entire vendor.

---

## 3. Model-number grammar (SW series)

Model numbers are a **grammar, not labels**. Parse once and you get capacity, ignition, and
power for the whole line — plus you can predict unseen models as gaps.

```
SW  6  D  E  L
|   |  |  |  |
|   |  |  |  +-- L = 12V relay for interior operation of the electric element
|   |  |  +----- E = 120V AC heating element
|   |  +-------- D = 12V DC direct spark ignition gas system
|   +----------- capacity in gallons
+--------------- Suburban Water heater
```

Observed capacities: 4, 6, 10, 12, 16.
Observed suffix combinations: `D`, `DE`, `DEC`, `DEL`, `DELC`, `DEM`.

> **CORRECTION — logged.** An earlier working assumption held that `L` meant *longer body*,
> and that SW6DE and SW6DEL therefore had different cutout depths. **This is wrong.**
> `L` is the 12-volt relay. Confirmed by the vendor's own decoding text and by direct
> dimensional comparison (§4). This is exactly the class of error the ground-truth fixture
> exists to catch.

### 3.1 SKU numbering

| Model | SKU |
|---|---|
| SW6DE | 5239A |
| SW6DEL | 5240A |
| SW10DE | 5243A |
| SW10DEL | 5244A |
| SW12DE | 5247A |
| SW12DEL | 5248A |

Sequential with gaps (5241, 5242, 5245, 5246 unaccounted — likely LP-only or P-series
variants). **The gaps predict models not yet seen** — same trick as the grammar itself.

Known alias chain for the in-hand unit: `SW6DEL = 5240A = 5140A`.

---

## 4. Captured specifications

### SW6DEL (SKU 5240A) — the in-hand unit

| Field | Value | Source |
|---|---|---|
| Capacity | 6 gal | retailer spec block |
| Input | 12,000 BTU/h | retailer spec block |
| Element | 1440 W Incoloy | prose (**conflicts with spec block — §6.2**) |
| Recovery, gas | 10.1 gal/hr | retailer spec block |
| Recovery, electric | 6.1 gal/hr | retailer spec block |
| Recovery, both | 16.2 gal/hr | prose |
| **Product size** | 12.69"h × 12.69"w × 19.19"d | retailer spec block |
| **Cutout** | **12.75"h × 12.75"w × 19.19"d** | retailer spec block |
| Net weight, empty | 36 lb | retailer spec block |
| Net weight, full | 86.04 lb | retailer spec block |
| Shipping weight | 35.00 lb | retailer cart field |
| Warranty | Limited 2 year | retailer features list |
| Orifice | 61 | data plate (in-hand) |
| Serial | 122106544 | data plate (in-hand) |

### SW6DE (SKU 5239A)

| Field | Value |
|---|---|
| Product size | 12.69"h × 12.69"w × 19.19"d |
| **Cutout** | **12.75"h × 12.75"w × 19.19"d** |
| Net weight, empty | 37.4 lb |
| Net weight, full | 82.6 lb |
| Warranty | Limited 90 day (**conflicts — §6.4**) |

### Sibling dimensions (from `alt` text — verify before trusting)

| Model | Dimensions |
|---|---|
| SW10DE / SW10DEL | 16-7/32" × 16-7/32" × 20-1/2" |
| SW12DE / SW12DEL | 16-7/32" × 16-7/32" × 22-1/4" |

Note that within each capacity, DE and DEL share dimensions. Consistent with §3's correction.

### 4.1 Cutout vs product size

**Only cutout is the interchange key.** This vendor gives both, which is unusually generous;
most sources give one and don't say which.

Unit-normalization warning: the same number appears three ways on a single page —
`12.69"`, `12-11/16"`, and (for cutout) `12.75"`. **Fraction → decimal normalization is a
day-one requirement**, not a later cleanup.

---

## 5. Interchange findings

### 5.1 First real edge: SW6DE ↔ SW6DEL — ASYMMETRIC

Identical cutout. Identical capacity, BTU, ignition type. Same group, different variant.

The difference is functional, not dimensional: the DEL has a 12V relay allowing the electric
element to be switched from inside the coach.

```yaml
edge:
  type: substitutes
  a: SW6DE
  b: SW6DEL
  asymmetric: true
  a_to_b:
    verdict: drop_in
    note: upgrade — gains interior electric switching
  b_to_a:
    verdict: fits_with_caveat
    blocking_caveat: >
      The interior wall switch will stop functioning. The relay it
      controls is not present on the DE.
```

This is a confirmed real instance of the asymmetric-substitution case the schema was
designed for. **Use it as the fixture's canonical edge test.**

### 5.2 `controls` edge — interior switch

Sold separately from the heater. One component, three part numbers, colour-only:

| Part number | Colour |
|---|---|
| 232882 | White |
| 233111 | Black |
| 232881 | Cream |

Live confirmation of the **cosmetic-axis-off-the-interchange-key** decision
(`ARCHITECTURE-Interchange_Core.md` §5).

Also note: this is an accessory the buyer *needs* but does not know to ask for. Good
candidate for the "PARTS FOR THIS UNIT" tier.

### 5.3 Repair-domain finding (from the triggering case)

The **inner tank is not a serviceable part** on this platform. Suburban replaces the whole
unit, not the tank. This is worth encoding: a `contains` edge should not imply purchasability.

Diagnostic note carried over: a weeping anode thread (bottom-mounted, doubles as the drain)
mimics a tank leak. Check anode and T&P valve before condemning a unit.

---

## 6. Data-quality findings

These are the reason for per-attribute provenance. All four surfaced within six documents.

### 6.1 Image `alt` text is unreliable — and wrong on exactly these two products

The SW6DE image is captioned "With 12 Volt Relay." The SW6DEL image is not.
**These are backwards.**

Cross-checked against siblings: SW10DEL and SW12DEL both correctly say relay;
SW10DE and SW12DE correctly omit it. **Only the 6-gallon pair is swapped.**

> `alt`/`title` text is a real source — it carries sibling dimensions not present in body
> copy — but it must be ranked **below** the spec block. Do not let it override.

### 6.2 Wattage — systematic, not a typo

Spec block says **1400 W**. Prose header says **1440 W**. On *both* pages.

Repeating identically across pages means it is a **template-level error**, not a transcription
slip. Systematic errors are the fixable kind — one rule corrects the whole catalog.

*(1440 W is almost certainly correct; it matches the stated 6.1 gal/hr electric recovery.
Flagged, not yet resolved.)*

### 6.3 Weight — derivable consistency check

| Model | Empty | Full | Difference | Implied gallons |
|---|---|---|---|---|
| SW6DEL | 36 | 86.04 | 50.04 | ≈ 6.0 ✅ |
| SW6DE | 37.4 | 82.6 | 45.2 | ≈ 5.4 ❌ |

Same physical envelope; the DEL contains *more* hardware yet is listed lighter empty.
The DEL's figures are internally consistent. The DE's are not.

> **`full − empty ÷ 8.34 ≈ nominal capacity` is a free validity rule.**
> Run it across the whole line to find bad records without any external source.

Separately: the cart "Weight: 35.00 LBS" field is identical on both models and matches
neither net figure. It is a **shipping default, not a measurement.** Do not ingest it as mass.

### 6.4 Warranty conflict

SW6DEL: limited 2 year. SW6DE: limited 90 day. Same family, no stated reason.

Suburban's general terms elsewhere reference 2 years plus an additional 3-year tank warranty.
Likely a retailer copy error on the DE page. **Unresolved.**

---

## 7. Definition of done — Stage 1, Suburban

> Any identifier printed on any of the five in-hand parts returns the correct component
> and the correct group members.

Roughly the scope of one CivicMirror state adapter.

Concretely:

- [ ] `observations` table exists and is append-only
- [ ] Three grammar charts transcribed from images
- [ ] SW-series model parser: string → {capacity, ignition, power, relay}
- [ ] ~12 SW-series documents fetched and cached raw
- [ ] Ground-truth fixture hand-written (`fixtures/ground-truth.yaml`)
- [ ] Pipeline reproduces the fixture
- [ ] SW6DE↔SW6DEL asymmetric edge resolves correctly in both directions
- [ ] `full − empty` validity rule implemented and run across the line
- [ ] Source-trust ranking enforced (spec block > prose > alt text)

---

## 8. Open items

- Pull `/sw-series-water-heater-parts-diagram/` — expected `shares_subassembly` source
  across SW6DEL / SW10DEL / SW12DEL / SW16DEL.
- Resolve the 1400/1440 W conflict against a manufacturer document.
- Resolve the 90-day/2-year warranty conflict.
- Identify what occupies SKUs 5241A, 5242A, 5245A, 5246A.
- Confirm SW4 and SW16 dimensions (not yet captured).
- Determine whether `C` and `M` suffixes (SW*DEC, SW*DEM) affect cutout.

---

## 9. Adapter order (cross-vendor)

1. **Suburban** — owns one, clean grammar, small line, public manuals ← *here*
2. **Coleman-Mach / Airxcel** — hits multi-namespace identity early via the thermostat
3. **KIB** — assembly decomposition
4. Furnaces, roof vents — after

Findings consolidate into `VENDOR-Reference_RV_Components.md`, mirroring the structure of
the existing `VENDOR-Reference_Election_Tech.md`.
