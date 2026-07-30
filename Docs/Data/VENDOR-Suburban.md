# VENDOR — Suburban Manufacturing

**Project:** RV Interchange
**Status:** research in progress
**Date:** 2026-07-29
**Adapter priority:** 1 of 7 (first vendor)
**Part families covered here:** water heaters (SW series, tank-style). A first data point
also now exists for the `IW` on-demand/tankless line (§4) — not yet its own research thread.
Furnaces, ranges/cooktops: preliminary structure only — see
`VENDOR-Suburban-Furnace_Cooktop.md`, low confidence, not yet fixture-ready.

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

`C` suffix, **confirmed 2026-07-29** from the SW12DELC product page (5331A), which carries
the same "Model Name Breakdown" text found on the image-only grammar page — this vendor
repeats the grammar in plain text on at least some individual product pages, not only as
the screenshot at `/model-number-breakdown/`:

```
C = 120V Corded
```

> **Methodology note.** This means the grammar may not require hand-transcribing the
> screenshot at all — it may already be scrapeable, page by page, wherever a product
> listing includes its own "Model Name Breakdown" block. Worth checking a sample of
> pages across capacities before assuming the image transcription is still required.

Observed capacities: 4, 6, 10, 12, 16.
Observed suffix combinations: `D`, `DE`, `DEC`, `DEL`, `DELC`, `DEM`, and a separate
combined code `VE` seen on the 16-gallon line (`SW16VE`, SKU 5082A) — **confirmed
2026-07-29** from that page's own "Model Name Breakdown" text:

```
VE = 120 Volt AC Direct Spark Ignition Gas Heating and 120 Volt AC Heating Element
```

**This is not a synonym for `D`+`E`.** The `D` line's ignition draws **12V DC** — coach
battery power. `VE`'s ignition draws **120V AC** — shore/generator power, the same circuit
as the heating element. That's not a cosmetic suffix difference; it's a different
electrical requirement at the install location. A coach wired for a 12V-ignition unit does
not necessarily have 120V AC run to that cavity.

**Compat consequence:** do not fold `SW16VE` into the same `substitutes` group as the
`D`-line units on capacity/cutout match alone, even if the cutout turns out identical. This
is exactly the kind of case `compat_mode` exists for — cutout match is necessary but not
sufficient here. At minimum this wants a caveat: *"Requires 120V AC wiring at the water
heater location."* Whether it's the same `part_type_id` (412) or a distinct one is worth
deciding once more of the line is captured — `attribute_schema` for 412 currently doesn't
have an ignition-power-source field, and probably should.

**Also worth flagging:** the SW16VE page describes a **non-portable** unit with a
**flush-mount radius door**, "without access door," and an adjustable gas control valve —
language that doesn't appear on the DE/DEL/DELC pages at all. That's a different door/access
family, not just a different ignition source. Possible this capacity tier is a genuinely
separate physical platform under the same `SW` + capacity naming convention, not a
same-platform variant. Don't assume shared cutout geometry with a same-capacity `D`-line
unit until one exists to check against — **it's not clear a `SW16D`/`SW16DE`/`SW16DEL`
counterpart exists at all**, which would make the comparison moot anyway.

> **CORRECTION — logged.** An earlier working assumption held that `L` meant *longer body*,
> and that SW6DE and SW6DEL therefore had different cutout depths. **This is wrong.**
> `L` is the 12-volt relay. Confirmed by the vendor's own decoding text and by direct
> dimensional comparison (§4). This is exactly the class of error the ground-truth fixture
> exists to catch.

### 3.1 SKU numbering

| Model | SKU |
|---|---|
| SW4D | 5135A |
| SW6D | 5238A |
| SW6DE | 5239A |
| SW6DEL | 5240A |
| SW10DE | 5243A |
| SW10DEL | 5244A |
| SW10DELC | 5230A |
| SW12D | 5146A |
| SW12DE | 5247A |
| SW12DEL | 5248A |
| SW12DELC | 5331A |
| SW16VE | 5082A |

Odd wrinkle: `SW12D` (5146A) sits in the "51xx" number range alongside `SW6DEL`'s alternate
number 5140A, while `SW12DE`/`SW12DEL` sit in "52xx." Possibly two SKU eras or catalog
generations coexisting. Not confirmed — flagged as a pattern, not a conclusion.

Sequential *within* a capacity's DE/DEL pair (5239/5240, 5243/5244, 5247/5248), but **not
sequential across the whole line** — 5230A (SW10DELC), 5331A (SW12DELC), 5082A (SW16VE),
and 5135A (SW4D) all fall outside that neat run. Read the earlier "gaps predict unseen
models" idea as true only within a capacity's core pair, not as a single global sequence.

Known alias chain for the in-hand unit: `SW6DEL = 5240A = 5140A`.

### 3.2 Full ignition-suffix grammar — confirmed 2026-07-30, cross-validated

Walter independently transcribed the same water-heater chart with his own tool. The result
matched Claude's earlier visual read **exactly**, down to a shared run-together typo
("GasHeating") in the `VE` line — two independent extractions agreeing, including an error,
is real corroboration rather than coincidence. This section is now **confirmed**, not
image-inferred-lowest-trust; it supersedes the equivalent entry in
`VENDOR-Suburban-Furnace_Cooktop.md` §1's trust caveat for the water-heater chart
specifically (that caveat still applies in full to the furnace and cooktop charts).

| Code | Meaning |
|---|---|
| `P` | Pilot Gas Heating Only |
| `PR` | Pilot Gas Heating with 12V DC Pilot Re-igniter |
| `PE` | Pilot Gas Heating with 120V AC Heating Element |
| `PER` | Pilot Gas Heating with 12V DC Pilot Re-igniter and 120V AC Heating Element |
| `D` | 12V DC Direct Spark Ignition Gas Heating Only |
| `DE` | 12V DC Direct Spark Ignition Gas Heating + 120V AC Heating Element |
| `DEL` | `DE` + 12V Relay for Interior Operation of Electric Heating System |
| `DEM` | `DE` + Motor Aid Heat Exchanger — **Motor Home Only** |
| `V` | 120V AC Direct Spark Ignition Gas Heating Only |
| `VE` | `V` + 120V AC Heating Element |

Two genuinely new findings here, not just confirmation of what was already known:

**There's a whole `Pilot` family (`P`/`PR`/`PE`/`PER`) that hasn't appeared in anything
fetched so far.** Standing-pilot ignition is a materially different, and likely older,
system than either Direct Spark family (`D` or `V`) — no spark electrode, no direct-spark
control board, possibly a different gas valve entirely. Treat `compat_mode` the same way as
the `VE` finding: do not assume a `Pilot`-family unit shares an interchange group with a
`Direct Spark`-family unit on cutout match alone. This is a strong candidate for its own
`ignition_system` field in the 412 `attribute_schema` — categorical, not derived from
dimensions — alongside the ignition-power-source field already flagged for `V`/`VE`.

**`DEM` is now decoded, and it carries a hard installation constraint, not just a feature
flag:** *Motor Home Only.* A travel trailer or fifth wheel has no engine to draw heat
exchange from — this variant **cannot physically exist** outside a motorized chassis. That's
a fitment fact worth encoding structurally (e.g. a `requires_system` edge to "engine coolant
loop" or a `chassis_type` gate), not just a caveat string, since it's not a "check before
you buy" situation — it's a "this cannot apply to you" situation, knowable in advance from
the coach type alone.

**`DEC` remains uncomfirmed but is now inferable, not just observed.** The chart doesn't
list `DEC` directly, but combined with the confirmed `C = 120V Corded` (§3, from the
SW12DELC page) the grammar is compositional: `DEC` = `DE` + corded, **without** the interior
relay `DEL` adds. That's a reasonable inference from two confirmed facts, not a new
confirmed fact itself — flag it as such if it goes in the fixture (`provenance:
inferred_from_grammar`, not `provenance: vendor_confirmed`).

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
Confirmed independently: SW12DEL's own alt text on the SW12DELC page correctly reads
"With 12 Volt Relay" — **the swapped-alt-text bug (§6.1) is specific to the 6-gallon pair
and does not recur here.**

### SW12DELC (SKU 5331A) — second full spec capture, corded variant

| Field | Value | Source |
|---|---|---|
| Capacity | 12 gal | retailer spec block |
| Input | 12,000 BTU/h | retailer spec block |
| Element | 1440 W (spec header) / 1400 W (features table) | **same conflict, same page — §6.2** |
| Recovery, gas | 10.1 gal/hr | retailer spec block |
| Recovery, electric | 6.1 gal/hr | retailer spec block |
| Product size | 16.22"h × 16.22"w × 22.25"d | retailer spec block |
| **Cutout** | **16.38"h × 16.38"w × 22.25"d** | retailer spec block |
| Net weight, empty | 48.0 lb | retailer spec block |
| Net weight, full | 148.08 lb | retailer spec block |
| Warranty | Limited 2 year | retailer features list |

`(148.08 − 48.0) / 8.34 = 12.00` — **passes** the validity rule exactly. Second data point
supporting the pattern that relay-equipped (`L`) variants have internally consistent
records; the one failure seen so far (SW6DE) was the one variant *without* a relay. Not
enough data to call this causal — flagging the correlation, not concluding it.

### SW16VE (SKU 5082A) — different platform, not just a suffix

| Field | Value | Source |
|---|---|---|
| Capacity | 16 gal | retailer spec block |
| Product size | 16-7/32"h × 16-7/32"w × **depth not given** | retailer spec block |
| Cutout | 16-3/8"h × 16-3/8"w × **depth not given** | retailer spec block |
| Ignition power | 120V AC (not 12V DC) | grammar text — see §3 |
| Door style | flush mount radius door, sold "without access door" | retailer prose |
| Portability | non-portable | retailer prose |
| Gas control valve | adjustable | retailer prose |
| Anode | "full anode protection" (unspecified detail) | retailer prose |

**No BTU, wattage, recovery rate, or net weight anywhere on this page — confirmed on a
full fetch, not just a partial read.** The one weight figure present, "Weight: 50.00 LBS,"
is the same cart/shipping-default field flagged in §6.3 for the SW6 pair — not a real
measurement, don't ingest it as mass. This record is genuinely thin, not under-captured;
the vendor simply didn't publish those numbers for this model.

**Gaps closed 2026-07-30 via cross-vendor corroboration** (Amazon listing, RecPro/Young
Farts search snippets — none of these are the manufacturer's own retail site, so rank
below suburbanrvparts.com per the trust hierarchy, but they're the only sources that have
these figures at all):

| Field | Value | Source |
|---|---|---|
| Depth | 27" | Amazon listing |
| BTU | 12,000 | Amazon listing, cross-vendor |
| Element wattage | 1440 W | cross-vendor (consistent with the 1400/1440 pattern seen everywhere else) |
| Weight, dry | ~53 lb (approximate) | third-party estimate, not a spec block — lowest confidence figure in this whole document, treat as provisional |

**New sibling SKU confirmed:** `SW6D` = **5238A** — the plain gas-only base model,
sequential right before `SW6DE` (5239A) and `SW6DEL` (5240A). Its alt text gives dimensions
of 12-11/16"h × 12-11/16"w × 19-3/16"d — same envelope as `SW6DE`/`SW6DEL` (12.69 × 12.69 ×
19.19, same rounding). **This is the first direct confirmation that `D`, `DE`, and `DEL`
share one cutout family**, not just an inference from the DE↔DEL pair alone.

**Second confirmation at a different capacity:** `SW12D` = **5146A**, alt text gives
16-7/32"h × 16-7/32"w × 22-1/4"d — identical to the already-known `SW12DE`/`SW12DEL`
envelope. The "D/DE/DEL share one cutout" rule now holds at two capacities (6-gal and
12-gal), which is reasonable grounds to generalize it as a rule for the whole `D`-line, not
just document it per-capacity as it's confirmed.

**Weak supporting evidence (not proof) for the "SW16VE may be the only 16-gallon
model" open question:** the page's own cross-sell list surfaces `SW12DEL`, `SW10DE`,
`SW10DELC`, `SW6D`, `SW4D` — no `SW16D`/`SW16DE`/`SW16DEL` anywhere. Cross-sell lists aren't
exhaustive by design, so this doesn't close the question, but it's one more page that had
the chance to surface a 16-gallon `D`-line sibling and didn't.

**New data-quality finding: SEO meta-keywords directly contradict body copy.** This page's
`meta-keywords` tag includes both "Portable Water Heater" and "Compact Water Heater" —
while the actual product description says "**Non-portable** heater." Add meta-keywords to
the source-trust ranking, **below alt text**: it's written for search engines, not
accuracy, and this is a clean example of it being flatly wrong. Never treat meta-keywords
as an attribute source.

**New data-quality finding: a *different* vendor's copy can introduce its own errors.**
Young Farts RV Parts describes the SW16VE's ignition as "125V DC DSI w/ 125V AC Element" —
which garbles the careful 12V-DC-vs-120V-AC distinction this whole document is built on.
Cross-vendor corroboration is genuinely useful (it just closed three real gaps above), but
it is not automatically *more* reliable than the manufacturer's own retail site — treat
each new vendor's copy with the same spec-block > prose > alt-text > meta-keywords
skepticism, not as a shortcut past it.

**New open thread, not yet investigated:** a `SAW` series (`SAW6D`, `SAW6DE` — "Suburban
Advantage Water heater") exists as a naming line distinct from `SW`. Different prefix, not
researched at all yet. Keep it visually distinct in any parser or documentation — easy for
a human to conflate "SAW" and "SW" even though they don't collide as a string-prefix match.

**New open thread:** `SW10DM` (Motor Aid Heat Exchanger, **without** the electric element)
turned up in a cross-vendor listing. The confirmed grammar chart (§3.2) only documents
`DEM` (WITH the element) — a bare `DM` isn't on it. Either the chart is incomplete, or `DM`
is a distinct, older designation that predates `DEM`. Needs its own product-page check.

### IW60RL (SKU 5280A) — Nautilus on-demand line, different platform entirely

Not an `SW`-series unit at all — a separate tankless/on-demand product line ("Nautilus"),
found via the vendor's own recirculating-loop variant listing.

| Field | Value | Source |
|---|---|---|
| Model | IW60RL | retailer spec block |
| Type | LP Gas, on-demand (tankless) | retailer spec block |
| Capacity | 0.5 gal | retailer spec block |
| Ignition | Direct Spark Ignition | retailer spec block |
| BTU | 60,000 | retailer spec block |
| Product size | 12.5"w × 12.5"h × 20"d | retailer spec block |
| With switch | No | retailer spec block |
| Marine | No | retailer spec block |
| Net weight | 36 lb | retailer spec block |
| Warranty | Limited 2 year | retailer prose |

**No cutout dimensions published on this page.** Consistent with it being tankless — a
0.5-gallon buffer tank plus heat exchanger has a materially different install profile than
the tank-style `SW` line, so "no cutout given" here is not the same data gap as SW16VE's
(§4, still-missing-depth) — it may not even be the right attribute to look for on this
platform. Needs its own attribute schema question before assuming `part_type_id: 412`
(the SW-series water-heater type) applies unmodified.

Cross-sell on this page surfaces companion parts under different SKUs — a module board
(521212) and a recirculating pump (233390 / 521299) — worth noting these are accessory/repair
parts for the IW60RL, not alternate models of it.

**New open thread:** the `IW` prefix ("Nautilus") is now a second product family, alongside
the already-flagged `SAW` line (§4, SW16VE section), that exists outside the `SW` grammar
entirely. Two different non-`SW` water-heater families have surfaced from casual browsing
without deliberately searching for them — worth a pass through the vendor's full water-heater
category page to check for a third.

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

### 5.4 First real field evidence: a customer review, found by accident

While cross-checking SW16VE facts against other retailers, the `SW12DEL` product page
turned up an actual customer review — the first piece of genuine field evidence anywhere
in this research, as opposed to spec-block attributes or inferred grammar:

> "Client wanted to replace SW6DEL with the 12. Once opening was cut to fit the 12
> connected without issues. The only change that was needed was the bypass line had to be
> longer. Propane lit on second attempt. Easy install. Product operates as described."
> — John Harmon, 2021-08-30, 4 stars

This is a **cross-capacity upgrade**, not a same-group substitution — the cutout goes from
12.75"×12.75" to 16.38"×16.38", a deliberate modification, not a match. Logged in
`fixtures/ground-truth.yaml` as a `substitutes` edge with `basis: buyer_confirmed_install`
and `verdict: fits_with_modification`, asymmetric (nobody's shrinking a 12-gallon cutout
down to 6).

**Why this matters more than the specific data point:** every edge in the fixture so far
has been prior-only — CANDIDATE tier, zero field evidence, exactly the honest day-1 state
`ARCHITECTURE-Interchange_Core.md` §7 describes. This is the first one with a real evidence
event behind it (α+3 for buyer-confirmed install), and it arrived **unsought** — found
while looking for something else entirely. That's the exact mechanism
`PLAN-Staged_Build.md` §6.4 describes for why passively-captured evidence is disproportionately
valuable: nobody had to run a retention campaign to get it, it was just sitting on a
product page.

Open question this raises: is "cut the cutout larger, buyer's install proceeds fine" a
general upgrade path across the whole `D`-line (any smaller unit → any larger one at the
same ignition family), or specific to this pair? One data point can't answer that — flag
it as a pattern to watch for, not a rule.

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

**Below that: `meta-keywords`.** Confirmed unreliable on the SW16VE page — its
meta-keywords tag includes "Portable Water Heater," while the same page's body copy says
"Non-portable heater." Meta-keywords are written for search indexing, not accuracy. Never
treat them as an attribute source; they sit at the bottom of the trust ranking, below alt
text: **spec block > prose > alt text > meta-keywords > image OCR** (image OCR added per
`VENDOR-Suburban-Furnace_Cooktop.md` §1).

### 6.2 Wattage — systematic, not a typo

Spec block says **1400 W**. Prose header says **1440 W**. On *both* pages.

Repeating identically across pages means it is a **template-level error**, not a transcription
slip. Systematic errors are the fixable kind — one rule corrects the whole catalog.

*(1440 W is almost certainly correct; it matches the stated 6.1 gal/hr electric recovery.
Flagged, not yet resolved.)*

**Confirmed a third time on SW12DELC (5331A):** identical split — "Input BTUh/Watts:
12,000/1440" in the spec header, "Wattage Rating: 1400 Watt" in the features table below
it, same page. This is now confirmed across two different capacities (6-gal and 12-gal),
which makes "template bug" close to certain rather than a per-page coincidence. Worth
resolving once, catalog-wide, rather than per-model.

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

- ~~Determine whether `C` suffix affects cutout.~~ **Resolved 2026-07-29:** `C` = 120V
  Corded, confirmed directly from vendor page text (SW12DELC / 5331A). Whether it changes
  cutout specifically (vs. just adding a cord) is still unconfirmed — flagging the label
  is resolved, the dimensional consequence is not.
- ~~Decode remaining suffixes (`M`, full grammar table).~~ **Resolved 2026-07-30,
  cross-validated** — see §3.2. Full `P`/`PR`/`PE`/`PER`/`D`/`DE`/`DEL`/`DEM`/`V`/`VE` table
  confirmed by two independent transcriptions.
- **New:** an entire `Pilot` ignition family (`P`/`PR`/`PE`/`PER`) exists and nothing about
  it has been fetched yet — no product page, no dimensions, no confirmation of whether it
  shares cutout geometry with anything in the `D`/`V` families. Treat as its own research
  thread, same priority tier as finishing the `D`-line capture.
- **New:** confirm whether `DEM` (Motor Home Only) shares cutout with its non-`M`
  `DE`/`DEL` counterpart at the same capacity, or whether the heat-exchanger hardware
  changes the envelope. Also confirm how a resolver should encode "physically impossible
  for this chassis type" — a stronger claim than a caveat, closer to a hard filter.
- **New:** `SW16VE`'s ignition runs on **120V AC**, not the 12V DC used by every `D`-line
  unit. Confirmed as a real electrical-architecture difference, not a labeling quirk —
  see §3 and the compat-consequence note there. `attribute_schema` for part type 412
  probably needs an `ignition_power_source` field before this line goes through the
  clusterer, or it risks getting grouped with `D`-line units on cutout match alone.
- **New:** confirm whether a `D`/`DE`/`DEL`-grammar 16-gallon unit exists at all. If
  `SW16VE` is the *only* 16-gallon offering, the "different platform" question in §5 may
  be moot — there'd be nothing in the `D` line to compare it against.
- **New:** `SW16VE`'s captured record has no depth, no BTU, no wattage, no weight. Thinnest
  capture so far — needs a second source before it's usable in the fixture.
- ~~Check whether the "Model Name Breakdown" text block appears on product pages across
  the rest of the line.~~ **Confirmed 2026-07-30** — present on SW12DELC and SW16VE pages
  too, not just SW6DEL/SW6DE. Three-for-three on water heaters. Still unconfirmed for
  furnaces and cooktops specifically; check before assuming the image transcription at
  `/model-number-breakdown/` is fully redundant.
- Pull `/sw-series-water-heater-parts-diagram/` — expected `shares_subassembly` source
  across SW6DEL / SW10DEL / SW12DEL / SW16DEL.
- Resolve the 1400/1440 W conflict against a manufacturer document (now confirmed on two
  separate capacity lines — see §6.2).
- Resolve the 90-day/2-year warranty conflict.
- Identify what occupies SKUs 5241A, 5242A, 5245A, 5246A — likely moot now that the
  catalog is confirmed non-sequential across capacities (§3.1); may simply not predict
  anything.
- Confirm SW4 and SW16 dimensions (not yet captured).
- Determine whether `C` and `M` suffixes affect cutout specifically (⟵ `C` label resolved
  above; `M` label now resolved too — see §3.2 — but neither's *dimensional* consequence
  is confirmed).
- **New:** `IW60RL` (5280A, "Nautilus" on-demand/tankless line) captured — see §4. No cutout
  data, and it's not clear `part_type_id: 412` even applies to a tankless unit. Needs its own
  attribute-schema pass, not just a slot in the `SW`-series fixture.

---

## 9. Adapter order (cross-vendor)

1. **Suburban** — owns one, clean grammar, small line, public manuals ← *here*
2. **Coleman-Mach / Airxcel** — hits multi-namespace identity early via the thermostat
3. **KIB** — assembly decomposition
4. Furnaces, roof vents — after

Findings consolidate into `VENDOR-Reference_RV_Components.md`, mirroring the structure of
the existing `VENDOR-Reference_Election_Tech.md`.
