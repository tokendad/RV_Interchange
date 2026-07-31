# VENDOR — Suburban Manufacturing

**Project:** RV Interchange
**Status:** research in progress
**Date:** 2026-07-29
**Adapter priority:** 1 of 7 (first vendor)
**Part families covered here:** water heaters — `SW` (tank-style, the main body of this
document), plus first data points for `SAW` ("Advantage", §4) and `IW` ("Nautilus"
on-demand/tankless, §4). Neither of the latter two is its own research thread yet.
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
| `suburbanrvparts.com` product pages | retailer (BigCommerce) | dimensions, aliases — **publishes an invalid 3rd "cutout" figure, see §6.5** | medium |
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
`D`-line units on capacity/opening match alone, even though the opening IS identical
(obs #19 puts 10/12/16 in one family). This is exactly the kind of case `compat_mode`
exists for — opening match is necessary but not
sufficient here. At minimum this wants a caveat: *"Requires 120V AC wiring at the water
heater location."* Whether it's the same `part_type_id` (412) or a distinct one is worth
deciding once more of the line is captured — `attribute_schema` for 412 currently doesn't
have an ignition-power-source field, and probably should.

**Also worth flagging:** the SW16VE page describes a **non-portable** unit with a
**flush-mount radius door**, "without access door," and an adjustable gas control valve —
language that doesn't appear on the DE/DEL/DELC pages at all. That's a different door/access
family, not just a different ignition source. Possible this capacity tier is a genuinely
separate physical platform under the same `SW` + capacity naming convention, not a
same-platform variant. Its opening is shared per obs #19, but don't assume shared
platform/door hardware with a same-capacity `D`-line
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

**Non-`SW` families** (same vendor, different product line — kept separate so they never
get mistaken for `SW` grammar members):

| Model | SKU | Family |
|---|---|---|
| SAW6DE | 5321A | Advantage (tank) |
| IW60RL | 5280A | Nautilus (tankless) |

**Models known from the factory spec sheet with no SKU captured** (obs #17, §4.2). The sheet
gives dimensions and weights but no catalog numbers, so these are model-only until a SKU
turns up:

`SW3P` · `SW6P` · `SW6PR` · `SW6PE` · `SW6PER` · `SW6DEM` ·
`SW10P` · `SW10PR` · `SW10PE` · `SW10PER` · `SW10D` · `SW10DEM`

Note `SW10D` and `SW6DEM` appear here for the first time; `SW6D` and `SW10DE` corroborate
SKUs already captured from retailer pages.

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

**There's a whole `Pilot` family (`P`/`PR`/`PE`/`PER`).** Standing-pilot ignition is a
materially different, and likely older, system than either Direct Spark family (`D` or `V`) —
no spark electrode, no direct-spark control board, possibly a different gas valve entirely.

> **REVISED 2026-07-30 by the factory spec sheet (§4.2).** This paragraph originally warned
> against assuming a Pilot unit shares an interchange group with a Direct Spark unit on
> opening match alone. The spec sheet shows that **at 6 and 10 gallons, every P/PR/PE/PER/
> D/DE/DEM variant is dimensionally identical** — one envelope per capacity. The families
> do share geometry.
>
> The caution was aimed at the right risk but misattributed it. What differs is the
> **electrical supply required at the install location** (`P` needs none, `D` needs 12V DC,
> `E` adds 120V AC), which produces *blocking caveats on a matching group*, not separate
> groups. `ignition_system` and `ignition_power_source` belong in the 412
> `attribute_schema` as **caveat-generating, not group-splitting** fields. See §4.2.

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
of 12-11/16"h × 12-11/16"w × 19-3/16"d — the same **product envelope** as `SW6DE`/`SW6DEL`
(12.69 × 12.69 × 19.19, same rounding).

`SW12D` = **5146A** likewise, alt text 16-7/32"h × 16-7/32"w × 22-1/4"d, matching the known
`SW12DE`/`SW12DEL` **product envelope**.

> **CORRECTION — logged 2026-07-30 (caught by Walter).** Both paragraphs above originally
> read these alt-text matches as *"the first direct confirmation that `D`, `DE`, and `DEL`
> share one **cutout** family"* and *"second confirmation at a different capacity."*
>
> **That was a category error, and it violated this document's own §4.1 rule.** `12-11/16"`
> and `16-7/32"` are **product-size** figures — obs #17 confirms the factory sheet reports
> envelope dimensions with no opening column at all. Matching envelopes are *consistent with*
> a shared opening; they do not establish one. Two units can share an envelope and be framed
> differently, and the whole reason §4.1 exists is that sources rarely label which quantity
> they're publishing. Calling this "confirmation of a cutout family" promoted an inference to
> a fact on evidence that couldn't carry it.
>
> **The claim itself survives — on entirely different evidence.** Suburban's Master Service
> and Training Manual (obs #19, Figure 1) states the opening families directly: all **4 and 6
> gallon** models share `12 3/4" × 12 3/4" (+1/8, −0)`, and all **10, 12 and 16 gallon** share
> `16 3/8" × 16 3/8" (± 1/16)`. `SW6D`/`SW6DE`/`SW6DEL` and `SW12D`/`SW12DE`/`SW12DEL` are
> therefore same-opening by **manufacturer statement**, not by envelope inference.
>
> So this is two separate fixes, and it's worth keeping them distinct: **the cited evidence
> was wrong** (product size ≠ opening, downgrade it), and **the conclusion is nonetheless
> confirmed** (by a source that arrived later). Fixing only one of those would leave the
> document either overclaiming or underclaiming. See §6.5.
>
> Residual value of the alt-text observation: it still corroborates that these models share a
> *physical envelope*, which matters for `unit_depth` and cavity clearance even though it says
> nothing about the opening.

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

**~~New open thread, not yet investigated:~~ partly resolved — see the SAW6DE section
immediately below.** A `SAW` series (`SAW6D`, `SAW6DE` — "Suburban Advantage Water heater")
exists as a naming line distinct from `SW`. One model now captured (obs #12); the line as a
whole is still unresearched. Keep it visually distinct in any parser or documentation —
easy for a human to conflate "SAW" and "SW" even though they don't collide as a
string-prefix match.

**New open thread:** `SW10DM` (Motor Aid Heat Exchanger, **without** the electric element)
turned up in a cross-vendor listing. The confirmed grammar chart (§3.2) only documents
`DEM` (WITH the element) — a bare `DM` isn't on it. Either the chart is incomplete, or `DM`
is a distinct, older designation that predates `DEM`. Needs its own product-page check.

### SAW6DE (SKU 5321A) — "Advantage" line, a third `SW`-adjacent family

Observation #12. Not an `SW`-series unit: `SAW` = Suburban **A**dvantage **W**ater heater.
Third distinct water-heater family found on this vendor, after `SW` (tank) and `IW`
(Nautilus tankless).

| Field | Value | Source |
|---|---|---|
| Capacity | 6 gal | retailer spec block |
| Ignition | 12V DC direct spark | retailer prose |
| Heating element | 120V AC (listed as *optional*) | retailer prose |
| Tank | Steel, porcelain-lined | retailer prose |
| Dimensions | 16.125"w × 12.5"h × 17.625"d | retailer spec block |
| Warranty | 2 year unit / **3 year tank** | retailer prose |
| Required access door | 6279APW (Polar White) | retailer "required items" |
| Required power switch | 234589 (White) | retailer "required items" |

**The suffix grammar carries across the prefix boundary.** `SAW6DE` decomposes the same way
an `SW` model does — capacity `6`, `D` = 12V DC direct spark, `E` = 120V AC element — and the
page's own prose confirms both. So the §3.2 ignition-suffix table is **not `SW`-specific**;
it's a Suburban-wide convention that survives a product-line change. Worth testing against
`IW` and the furnace lines before generalizing further, but this is one confirmed crossing.

**The envelope is completely different, and that's the important part.** 16.125 × 12.5 ×
17.625 against `SW6DE`'s 12.69 × 12.69 × 19.19 — wider, shorter, shallower. Same brand, same
capacity, same ignition suffix, **not the same hole.** This is the cleanest counterexample yet
to "capacity + ignition implies interchange," and a good regression case for the clusterer:
if `SAW6DE` ever lands in group `412-0087` with the `SW6` units, something is matching on
model-name similarity instead of geometry.

> **Gap:** the page doesn't say whether those numbers are product size or opening. Every
> `SW`-series page labels both explicitly (§4.1); this one gives one unlabeled triple.
> Recorded as-is, unlabeled — do **not** silently file it as `opening_*`. Needs a second
> source or the install manual before it's fixture-ready.

**Different switch part number — likely a different interface.** Requires switch **234589**,
where the whole `SW` DEL line uses the 232882/233111/232881 colour trio (§5.2). A new part
number for the same nominal function usually means the connector, the voltage, or the
mounting changed. Do not assume the `SW` switch trio substitutes here. This is its own
`controls` edge to its own component, and the colour-axis grouping established for the `SW`
switches has to be re-derived for this one rather than inherited.

**"Replaces Aluminum Tank RV Water Heaters" — a manufacturer assertion, not a documented
retrofit.** Porcelain-lined steel is Suburban's signature; aluminum tank is Atwood's. So this
is a competitor-replacement claim aimed squarely at the Atwood installed base — the same
*intent* as the Nautilus retrofit table, but a completely different evidence class:

| | Nautilus retrofit (§4, obs #14) | This claim |
|---|---|---|
| Artifact | Four stocked panel PNs, per brand and capacity | None |
| Procedure | Documented, with vent-hole spec | None |
| Target named | Atwood 6-gal, Atwood 10-gal, explicitly | "aluminum tank" generically |
| Evidence tier | `manufacturer_documented` (α+4/+5) | `manufacturer_assertion` (α+2, capped) |

Per `ARCHITECTURE-Interchange_Core.md` §7, marketing copy asserting broad replaceability with
no part number behind it caps at α+2 and does not repeat. **Do not create Atwood edges from
this line.** If Suburban publishes a SAW installation manual with an adapter or panel PN the
way it did for the Nautilus, that promotes; a brochure sentence doesn't.



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

**No cutout dimensions were on the retailer page — resolved, not a gap.** The manufacturer's
own service manual (Suburban/Airxcel, "Nautilus (IW60) Service and Training Manual" —
[myrvworks.com PDF](https://myrvworks.com/wp-content/uploads/2020/04/Suburban-Nautilus-Service-Manual.pdf),
captured as observation #14) confirms this platform genuinely has **no tank cutout at all.**
It's not a missing attribute, it's a different attribute shape entirely — this platform needs
its own schema, not `part_type_id: 412`'s cutout fields:

- **New install:** the only opening required is a **3.750" diameter vent hole**. Vent cap is
  ordered separately (Table 1: PNs 260616/260617/260618/260638, selected by wall thickness /
  vent-cap-length, 0–1" through 5–6").
- **Retrofit install (replacing an existing tank unit):** a **replacement panel** — sized to
  the *old* unit's cutout — gets caulked into the existing opening, covering it. Only the
  3.750" vent hole is newly cut; the tank cutout itself is reused, not resized. Panel part
  number is selected by the outgoing unit's brand and capacity:

  | Outgoing unit | Capacities | Replacement panel PN |
  |---|---|---|
  | Suburban | 6 gal | 6276APW (Polar White) |
  | Suburban | 10, 12, 16 gal | 6277APW (Polar White) |
  | Atwood | 6 gal | 521147 (Polar White) |
  | Atwood | 10 gal | 521150 (Polar White) |

**Interchange consequence — this is a cross-vendor `substitutes` candidate, not just a
same-vendor one.** The manual explicitly documents the IW60(RL) as a drop-in retrofit target
for five different cutout families across **two manufacturers** (Suburban 6-gal, Suburban
10/12/16-gal, Atwood 6-gal, Atwood 10-gal), via the panel adapter rather than a matching
cutout. That's a `basis: manufacturer_documented` edge, stronger evidence than the single
buyer-confirmed review in §5.4, and it's the first confirmed Atwood cross-reference anywhere
in this document. Each of those five edges would need `verdict: fits_with_modification` (new
vent hole + panel required) and a `requires_part` reference to the correct panel PN — this
is not a caveat-free drop-in.

Dimensions from the manual match the retailer page exactly (12.5"h × 12.5"w × 20"d) —
independent corroboration between manufacturer and retailer sources.

Cross-sell on the retailer page surfaces companion parts under different SKUs — a module
board (521212) and a recirculating pump (233390 / 521299) — worth noting these are
accessory/repair parts for the IW60RL, not alternate models of it.

**New open thread:** the `IW` prefix ("Nautilus") is now a second product family, alongside
the already-flagged `SAW` line (§4, SW16VE section), that exists outside the `SW` grammar
entirely. Two different non-`SW` water-heater families have surfaced from casual browsing
without deliberately searching for them — worth a pass through the vendor's full water-heater
category page to check for a third.

### 4.1 Opening vs product size — the rule

**Only the framed opening is the interchange key, and it is two-dimensional.** Product size
(envelope) is never the key. This distinction is the single most error-prone thing in this
vendor's data and has now caused three separate mistakes in this document — see §6.5 and the
correction logged in §4.

Three quantities are in play, and sources routinely publish one while labelling it as
another:

| Quantity | What it answers | Source of truth |
|---|---|---|
| **`opening_h` × `opening_w`** | *Does it fit the hole?* | Manufacturer installation figure (obs #19) |
| **`unit_depth`** | *Is the cavity deep enough?* | Spec chart / spec sheet (obs #17, #20) |
| product H × W (envelope) | neither, on its own | Spec sheets and retailer alt text |

Unit-normalization warning: the same measurement appears three ways on a single page —
`12.69"`, `12-11/16"`, and `12.75"` — where the first two are the *product* width and only
the third is the *opening*. **Fraction → decimal normalization is a day-one requirement**,
not a later cleanup, and it is what makes the product/opening confusion visible at all.

The factory spec sheet (§4.2) reports `12 11/16"` = 12.6875" — product size — with **no
opening column at all**. Manufacturer spec sheets and retailer pages do not necessarily
publish the same quantity, and neither reliably labels which one it is.

> **Working rule: never infer the kind from the source type or from a numeric match.**
> Read the label, or leave the value unlabeled. Two records sharing an envelope are
> *consistent with* sharing an opening; they do not establish it. Only a stated opening
> — ideally a manufacturer installation figure — confirms one.

### 4.2 Factory spec sheet — Pilot family captured, envelope shared across ignition families

Observation #17. A spec-sheet table extracted from a Suburban service manual, covering 15
models across the `P`/`PR`/`PE`/`PER`/`D`/`DE`/`DEM` suffixes at 3, 6, and 10 gallons.

**These are product-size dimensions, not cutouts.** `12 11/16" = 12.6875"`, which matches
the retailer's *product size* of 12.69" — the retailer's cutout for the same unit is 12.75".
There is no cutout column on this sheet at all. Do not file these as `cutout_*`.

| Capacity | Envelope (H × W × D) | Models sharing it |
|---|---|---|
| 3 gal | 12.6875 × 12.6875 × **16.125** | SW3P |
| 6 gal | 12.6875 × 12.6875 × **19.1875** | SW6P, SW6PR, SW6PE, SW6PER, SW6D, SW6DE, SW6DEM |
| 10 gal | 16.21875 × 16.21875 × **20.5** | SW10P, SW10PR, SW10PE, SW10PER, SW10D, SW10DE, SW10DEM |

#### The headline: ignition family does not change the envelope

Every 6-gallon model on this sheet is dimensionally identical — **pilot and direct-spark
alike.** Same for every 10-gallon. Seven suffix variants per capacity, one envelope each.

This **revises the caution in §3.2**, which said not to assume a Pilot-family unit shares an
interchange group with a Direct Spark unit on cutout match alone. On geometry, they do share
it. But the caution was directed at the right risk, just misattributed — the difference
between these families isn't dimensional, it's **what has to be present at the install
location**:

- `D`-line units need **12V DC** run to the cavity for the spark board.
- `P`-line units need **no electrical supply at all** for the gas side.
- `E`-bearing units additionally need **120V AC**.

So `SW6P` → `SW6D` is a same-group, same-envelope substitution that **still requires a
blocking check** ("is there 12V DC at the heater?"), and `SW6D` → `SW6P` is the reverse: it
fits, and any 12V feed simply goes unused. That's an asymmetric caveat pair on a
geometrically clean match — the same shape as the SW6DE↔SW6DEL edge in §5.1, one layer up.

**Consequence for `attribute_schema` (part type 412):** `ignition_system` and
`ignition_power_source` are confirmed as **caveat-generating attributes, not
group-splitting ones**. They belong in the schema, but the clusterer should not fork a group
on them. Previously flagged as possibly group-splitting in §3.2 — this sheet settles it.

#### Resolved: `DEM` does not change the envelope

`SW6DEM` is dimensionally identical to `SW6DE` and `SW6D`; `SW10DEM` likewise. The Motor Aid
heat exchanger adds **weight** — +2 lb at 6 gal, +10 lb at 10 gal — but not size. Closes the
open item asking whether the heat-exchanger hardware changes the cutout. It does not.

The chassis-type constraint from §3.2 still stands and is unaffected: `DEM` remains
motorhome-only because it needs an engine coolant loop, which is a *system* requirement, not
a dimensional one.

#### Surprise: a 3-gallon model exists

`SW3P`, 9,000 BTU — and **3 gallons is not on the confirmed capacity list.** The
cross-validated grammar chart (§3.2) states capacity sizes of 4, 6, 10, 12, 16 only.

This is the first counterexample to anything in a section marked *confirmed*. Two readings,
both plausible, not yet distinguishable:

1. The chart documents the **then-current** lineup and `SW3P` predates or postdates it.
2. The chart is simply incomplete.

Either way the rule is the same: **the chart is authoritative for decoding suffixes, not for
enumerating what exists.** Treat "capacity sizes" as a sample, not a closed set — the parser
should decode `SW3P` and `SW8xx` fine on grammar alone without a membership check.

`SW3P` also shares its **height and width** exactly with the 6-gallon line, differing only in
depth (3.0625" shallower). A 3-gallon dropping into a 6-gallon opening is therefore a
plausible fit-with-gap; the reverse is a hard no. Neither is confirmed — no cutout figures
here — but it's a strong candidate edge worth checking.

#### `BTU` is capacity-dependent, not line-constant

Every model on this sheet is 12,000 BTU **except** `SW3P` at 9,000. Prior captures were all
12,000 and could have been read as a line constant. They aren't.

#### A third weight quantity

This sheet reports **shipping weight**, distinct from both the *net empty* and *net full*
figures on retailer pages (§6.3). Three different quantities now wear the word "weight" in
this vendor's data. The `full − empty` validity rule in §6.3 applies only to the net pair;
shipping weight must not be substituted into it.

---

## 5. Interchange findings

### 5.1 First real edge: SW6DE ↔ SW6DEL — ASYMMETRIC

Same opening, same capacity, same BTU, same ignition type. Same group, different variant.

The opening is **manufacturer-stated**, not inferred from matching retailer figures: obs #19
Figure 1 places every 4- and 6-gallon model in one `12 3/4" × 12 3/4" (+1/8, −0)` family.
That is the evidence this edge rests on. (The two units' matching *product envelopes*
are consistent with it but would not on their own establish it — see the §4 correction.)

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

### 5.5 Accessory part numbers that are actually interchange edges

From the factory spec sheet's accessory table (obs #17). Three of these are `substitutes`
evidence wearing an accessory-catalog disguise:

| PN | Description | Why it's an edge |
|---|---|---|
| 520781 | Kit to adapt **old style 6 gal door** to SW6 | manufacturer-documented backward compat, stocked PN |
| 520771 | Kit to adapt **old style flush mount door** to SW6 | same |
| 520787 / 520818 | **Door Kit (6 Gallon Aluminum Tank Replacement Kit)** — Colonial White / Polar White | see below |

#### The aluminum-tank kit, and what it does and doesn't license

Suburban tanks are porcelain-lined steel; **aluminum tank** is Atwood's signature
construction. So 520787/520818 look like a stocked, manufacturer-documented path for
replacing an Atwood 6-gallon with a Suburban SW6 — structurally the same pattern as the
Nautilus retrofit panels (§4, obs #14), and exactly the artifact that
`ARCHITECTURE-Interchange_Core.md` §7 says separates *manufacturer-documented retrofit* from
mere *assertion*.

**But this sheet never says Atwood.** It says "aluminum tank." The inference is strong and
probably right, and it is still an inference. Recording it accordingly:

- The **kit exists and is stocked** — confirmed, `manufacturer_documented`.
- The kit's **target is an aluminum-tank 6-gallon unit** — confirmed, that's the literal text.
- The target **is Atwood** — *inferred from construction type*, not stated. Provenance
  `inferred_from_construction`, not `vendor_confirmed`.

Practical effect: this is enough to create an edge to the existing
`c_placeholder_wh_atwood_6gal` family placeholder, with `requires_part: 520787/520818` and an
explicit note that the brand identification is inferential. It is **not** enough to retroactively
promote the SAW6DE marketing line (§4) — that's a different product with no PN behind it, and
it stays at `manufacturer_assertion`. A stocked kit for the SW6 says nothing about the SAW6.

> Worth noting the pattern now visible across three independent documents: when Suburban
> wants you to replace a competitor's unit with theirs, it sells you **a door or panel** —
> the tank goes in the hole, the *trim* is what's brand-specific. That's a reusable
> structural insight for the whole category, not a Suburban quirk. Expect `requires_part`
> on cross-brand edges to resolve to trim/door/panel SKUs far more often than to adapters.

#### `V` is overloaded — namespace collision, flag before it bites

The same accessory table lists doors for a **"V Model"** line in 3, 6, 8, and 10 gallon.

> **CORRECTED 2026-07-30.** An earlier draft read the "8 Gallon" here as a second
> counterexample to the §3.2 capacity list, alongside `SW3P`. **Withdrawn — Suburban did
> not make an 8-gallon water heater.** Nothing in any capture supports one: no SKU, no
> model number, no spec-sheet row, no product page, across 18 observations. The §3.2
> capacity list stands unchallenged except by `SW3P`.
>
> **What the "8" actually is remains unresolved.** Three candidate readings, none confirmed:
>
> 1. **An error in the accessory table.** Simplest explanation; accessory catalogs are
>    lower-care copy than spec tables.
> 2. **A model-revision digit misread as a capacity.** Atwood model numbers carry a
>    revision suffix (`G6A-8E` and similar), so an "8" appearing near capacity figures in
>    a cross-brand door list is plausibly a revision marker. *Reservation:* the source text
>    reads "3, 6 and 8 Gallon" — the word "Gallon" is right there, applied to all three
>    numbers, which strains this reading unless the catalog itself made the mistake.
> 3. **A capacity belonging to whatever "V Model" actually is** — see below. If the V line
>    isn't Suburban's own, its capacity range needn't match Suburban's.
>
> Note that the 8 appears **only** on V-Model door rows (697205, 690578), never on an
> SW-Model row (6261ACW, 6255ACW, 6259ACW are 3/6/10 only). Whatever it refers to, it is
> not an `SW` capacity.
>
> **Operationally this changes nothing about how the parser should behave** — it still
> decodes capacity from the model string rather than validating against a list (the `SW3P`
> lesson). It only removes a bad data point from this document.

Separately, `V` genuinely means two unrelated things in this vendor's data:

1. **`V` as an ignition suffix** — 120V AC direct spark, confirmed in the §3.2 grammar
   (`SW16VE`).
2. **"V Model" as a product line** — a distinct tank family with its own door catalog.

These do not collide as string prefixes (`SW16VE` vs. a V-Model part number), but they
collide badly in prose, in category names, and in anything a human types into a search box.
**Do not let a parser or a human treat "V Model" as evidence about the `V` ignition suffix,
or vice versa.** Namespaced identifiers (`ARCHITECTURE-Interchange_Core.md` §3) handle this
correctly if the line is recorded as its own namespace rather than as a suffix reading.

Unresearched: the V-Model line entirely — including **whether it is even Suburban's own
product.** Suburban demonstrably sells trim for other manufacturers' units (the aluminum-tank
kits above; the Nautilus retrofit panels in §4), so a "V Model" door catalog inside a
Suburban accessory table does not establish that Suburban built the V Model. Door PNs
697205 / 690578 / 697221 / 6257ACW / 697213 are the only trace captured so far, and their
`697xxx` numbering sits well outside the `62xxACW` block used for the SW doors — which is
itself weak evidence of a different origin.

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

### 6.2 Wattage — **resolved 2026-07-30: 1440 W**

Spec block says **1400 W**. Prose header says **1440 W**. Reproduced identically across
SW6DEL, SW6DE, and SW12DELC pages — a template-level error, not a transcription slip.

**Resolved by the manufacturer.** Suburban's own 2002 spec chart (obs #20, rvcomfort.com via
Internet Archive) lists the input column as **`12000/1440`** for every electric-equipped
model — SW6PE, SW6PER, SW6DE, SW6DEM, SW10PE, SW10PER, SW10DE, SW10DEM. Fifteen rows, no
1400 anywhere.

**1440 W is correct. The 1400 W figure in suburbanrvparts' spec block is wrong on every page
it appears.** This is a single systematic error with a single correction, exactly as
predicted — one rule fixes the whole catalog.

Same chart also settles two smaller conflicts in the same column:

| Field | suburbanrvparts | PPL | **Manufacturer** |
|---|---|---|---|
| Element | 1400 W | — | **1440 W** |
| Recovery, gas | 10.1 gal/hr | 10.2 | **10.2** |
| Recovery, electric | 6.1 gal/hr | 6 | **6.0** |

PPL was right on both recovery figures; suburbanrvparts was off by 0.1 on each.

### 6.3 Weight — a derivable consistency check, **recalibrated 2026-07-30**

> **CORRECTION.** This rule originally assumed `(full − empty) / 8.34 ≈ nominal capacity`
> and, on that basis, declared the SW6DE record suspect for computing 5.42 instead of 6.
> **The rule's calibration was wrong.** It was fitted to a single retailer datapoint
> (SW6DEL, 36 / 86.04) that happens to give exactly 1.000. Suburban's own spec chart
> (obs #20) supplies fifteen rows, and they are emphatic:

| Model | Empty | Full | Water | Implied gal | **Ratio to nominal** |
|---|---|---|---|---|---|
| SW3P | 28.3 | 52.6 | 24.3 | 2.91 | 0.971 |
| SW6P | 34.7 | 83.3 | 48.6 | 5.83 | 0.971 |
| SW10P | 44.6 | 125.6 | 81.0 | 9.71 | 0.971 |
| SW6D | 33.3 | 81.9 | 48.6 | 5.83 | 0.971 |
| SW6DE | **34.3** | 82.6 | 48.3 | 5.79 | 0.965 |
| SW10DE | 45.5 | 126.5 | 81.0 | 9.71 | 0.971 |
| SW6DEM | 35.0 | 83.6 | 48.6 | 5.83 | 0.971 |
| *(15 rows total)* | | | | | **13 of 15 at exactly 0.971** |

A tank does not fill to nominal — there's air space at the top. **The fill ratio is a design
constant of ≈ 0.971**, not 1.000.

**Corrected rule:**

```
(weight_full − weight_empty) / 8.34 / nominal_gal  ≈  0.971 ± 0.01
```

Re-running the retailer records against the corrected rule inverts the original verdict:

| Record | Ratio | Verdict |
|---|---|---|
| suburbanrvparts SW6DE (37.4 / 82.6) | 0.903 | **fails** — and the manufacturer says empty is 34.3, not 37.4. The *full* weight (82.6) matches exactly; only the empty figure is wrong. |
| suburbanrvparts SW6DEL (36 / 86.04) | 1.000 | **fails** — too clean. No manufacturer row reaches 1.000. SW6DEL isn't in the 2002 chart, so this can't be checked directly, but 1.000 against a design constant of 0.971 is an outlier, not a pass. |

So **both** retailer weight records are suspect, in opposite directions — and the original
conclusion ("DEL passes, DE fails") was an artifact of calibrating on the very record that
should have been under suspicion.

**Lesson worth keeping:** a validity rule fitted to one datapoint isn't a rule, it's a
restatement of that datapoint. This one only became useful once fifteen manufacturer rows
were available to fit against.

Separately: the cart "Weight: 35.00 LBS" field is identical across models and matches neither
net figure. It is a **shipping default, not a measurement.** And the factory spec sheet
(obs #17) reports a third quantity again — *shipping weight* — distinct from both net
figures. Three quantities wear the word "weight" in this vendor's data; the rule above
applies only to the net pair.

### 6.4 Warranty conflict — **resolved 2026-07-30**

SW6DEL: limited 2 year. SW6DE: limited 90 day. Same family, no stated reason.

**Resolved by an independent source.** PPL Motor Homes' SW6D page (obs #18) states the
warranty as **2 years on components, 3 years on the tank** — matching Suburban's general
terms and the SW6DEL page, and matching the SAW6DE page's separate 2yr/3yr split (§4).

Three sources now agree on 2yr + 3yr tank; one page says 90 days. **The 90-day figure on
the SW6DE page is an error.** Recorded as a correction, not a value change — the erroneous
observation stays in the table.

Note the shape of the resolution: the winning evidence came from a *different retailer*,
not from Suburban. Cross-vendor corroboration settled a conflict that no amount of
re-reading the original source could have.

---

### 6.5 Cutout depth — **RESOLVED 2026-07-30: there is no such dimension**

Both retailers were wrong, in different ways, and the error was categorical rather than
numerical.

Suburban's own **Master Service and Training Manual** (obs #19, 44 pages, fully text-bearing)
specifies the installation opening in Figure 1 as **two dimensions only**:

```
Provide an opening flush with floor in outer wall of coach.
Wall of coach should be framed as shown in Figure 1.
Maintain inside dimensions listed below.

  4 & 6 Gallons          10, 12 & 16 Gallons
  A = 12 3/4" +1/8 -0    A = 16 3/8" ± 1/16
  B = 12 3/4" +1/8 -0    B = 16 3/8" ± 1/16
```

**There is no C. No depth.** The opening is a framed rectangle in the sidewall. Depth is a
property of the *unit*, and separately a question of whether the cavity behind the wall is
deep enough — governed by the manual's clearance rule, not by an opening dimension.

| Source | Claimed "cutout depth" | Verdict |
|---|---|---|
| suburbanrvparts.com | 19.19" | Copied its own product-size depth into a cutout row. No such dimension exists. |
| pplmotorhomes.com | 19.75" | Stated a depth as a "cut-out dimension." Also not an opening dimension; may be a real cavity-clearance figure, but it is mislabeled. |
| **Suburban master manual** | **— (none)** | **Opening is 2D: A × B.** |

#### What replaces it in the schema

`cutout_d` is not a valid attribute for part type 412. It should be:

- **`opening_h`, `opening_w`** — the framed opening. **This is the interchange key.**
- **`unit_depth`** — the unit's own depth, a separate constraint answering "is the cavity
  deep enough," not "does it fit the hole."

Applied to `fixtures/ground-truth.yaml`: `cutout_d` removed from the 412
`critical_attributes` list, and the contested `cutout_d` values on both 6-gallon components
retired with a note pointing here.

#### The much larger finding: there are only TWO opening families

The manual's own grouping is the headline:

| Opening | Tolerance | Capacities |
|---|---|---|
| 12 3/4" × 12 3/4" | +1/8, −0 | **4 and 6 gallon** |
| 16 3/8" × 16 3/8" | ± 1/16 | **10, 12 and 16 gallon** |

Suburban states directly that **10, 12, and 16 gallon all share one framed opening.**
Capacity does not imply a distinct opening — which is the single most useful interchange
fact captured in this project so far, and it comes from the manufacturer rather than being
inferred.

This **corrects a fixture assumption.** `c_placeholder_wh_6del` (412-0087) and
`c_placeholder_wh_12del` (412-0088) were placed in different groups partly on differing
cutouts. The 6-gal/12-gal split is still correct — 12 3/4 vs 16 3/8 are genuinely different
openings — but any future 10- or 16-gallon component belongs in the **same opening group as
the 12**, not its own. The `contains`-style reasoning "different capacity ⇒ different group"
is wrong here.

Corroborating detail from the same manual's door list: *"Colonial White, SW Model, Flush
Mount, **10, 12 & 16 Gallon**"* — one door part number spans all three capacities, exactly as
a shared opening would require.

#### Manufacturer-specified tolerances — new, and directly usable

This is the first tolerance data in the project:

- **4 & 6 gal: `+1/8, −0`** — asymmetric. The opening may be up to 1/8" oversize but must
  **never** be undersize.
- **10/12/16 gal: `± 1/16`** — symmetric.

`ARCHITECTURE-Interchange_Core.md` §11 lists "tolerance bands per attribute type" as an open
question. For this part type it is now answered by the manufacturer, and the asymmetry
matters: a matcher that treats tolerance as symmetric would accept an opening 1/8" *under*
nominal on a 6-gallon, which Suburban explicitly does not.

---

## 7. Coverage — what's captured, what's dark

*Rebuilt 2026-07-30 at 20 observations. Regenerate from the db rather than trusting this
table's age.*

**35 `SW` models are named across all sources.** The useful framing has changed: the earlier
version of this table asked *"which suffixes have we seen?"* — that question is now closed.
The grammar is confirmed (§3.2) and every model's opening is known (§6.5). What remains is a
**specs** gap, and it splits cleanly along generational lines.

### The interchange key: complete

| | Coverage |
|---|---|
| **Opening (`opening_h` × `opening_w`)** | **35 of 35 — 100%** |

Not because 35 models were measured, but because the master manual (obs #19) states two
opening families covering every capacity. 4/6 gal → 12¾"; 10/12/16 gal → 16⅜". A single
document closed the entire dimension.

*(`SW3P` is inferred into the small family — the manual postdates it and starts at 4 gal.)*

### Unit specs: 15 of 35, and all on one side of a line

| Source | Models | Generation |
|---|---|---|
| Manufacturer spec chart (obs #20) + factory sheet (obs #17) | 15 | 3/6/10 gal · `P` `PR` `PE` `PER` `D` `DE` `DEM` |
| Retailer pages (obs #1, 2, 4, 5, 8, 11, 18) | 6 | 6/12/16 gal · `D` `DE` `DEL` `DELC` `VE` |
| **Both** | **2** | `SW6D`, `SW6DE` |
| **Neither — named only** | **~16** | mostly 12/16 gal and the `DEL`/`DELC` line |

**The sharp finding: there is zero manufacturer data for the `DEL`/`DELC`/`V` generation.**
Every `DEL`, `DELC`, and `V`-family figure in this project traces to a retailer — and
suburbanrvparts is the source with three confirmed systematic errors (§6.1, §6.2, §6.5).
The two documents that resolved those errors both predate the models that need resolving.

Symmetrically: **no Pilot-family model has a retailer page**, so nothing corroborates the
2002 chart from the other direction.

### Suffix status, then vs. now

| Suffix | At 11 observations | At 20 observations |
|---|---|---|
| `P` `PR` `PE` `PER` | completely dark | **fully spec'd** — 8 models, mfr dims + weights |
| `D` | SKU only | spec'd (mfr) + retailer page |
| `DE` | one page | spec'd (mfr) + retailer page |
| `DEL` | two pages | retailer only — **no mfr specs** |
| `DELC` | one page | retailer only — **no mfr specs** |
| `DEC` | not found | **still not found** — inferred from grammar only |
| `DEM` | zero pages | **fully spec'd** at 6 and 10 gal |
| `DM` | zero pages | named (`SW10DM`) — still no specs |
| `V` standalone | zero pages | named (`SW16V`, obs #19) — no specs |
| `VE` | one page | retailer only — **no mfr specs** |
| `SAW` | completely dark | one model captured (§4) |
| `IW` (Nautilus) | not known to exist | manual + retrofit table (§4) |

### Caveat on the model count

Bare `SW6`, `SW12`, `SW16` appear in the extraction but are almost certainly regex artifacts
— fragments of longer model strings broken across PDF line wraps. Treat 32, not 35, as the
real count until confirmed.

---

## 8. Definition of done — Stage 1, Suburban



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

## 9. Open items

- ~~Determine whether `C` suffix affects cutout.~~ **Resolved 2026-07-29:** `C` = 120V
  Corded, confirmed directly from vendor page text (SW12DELC / 5331A). Whether it changes
  cutout specifically (vs. just adding a cord) is still unconfirmed — flagging the label
  is resolved, the dimensional consequence is not.
- ~~Decode remaining suffixes (`M`, full grammar table).~~ **Resolved 2026-07-30,
  cross-validated** — see §3.2. Full `P`/`PR`/`PE`/`PER`/`D`/`DE`/`DEL`/`DEM`/`V`/`VE` table
  confirmed by two independent transcriptions.
- ~~An entire `Pilot` ignition family (`P`/`PR`/`PE`/`PER`) exists and nothing about it has
  been fetched.~~ **Resolved 2026-07-30** by the factory spec sheet (obs #17, §4.2). All
  eight Pilot models at 6 and 10 gal captured with dimensions and weights. Key result: the
  Pilot family **shares its envelope** with the Direct Spark family at the same capacity —
  the difference is electrical supply at the install location, not geometry. **Still open:**
  no Pilot-family *cutout* figures (this sheet is product-size only), and no Pilot product
  page or SKU has been captured.
- ~~Confirm whether `DEM` shares cutout with its non-`M` `DE`/`DEL` counterpart, or whether
  the heat-exchanger hardware changes the envelope.~~ **Resolved 2026-07-30** (obs #17,
  §4.2): `SW6DEM` and `SW10DEM` are dimensionally identical to their `DE` siblings. Motor
  Aid adds weight (+2 lb / +10 lb), not size. The motorhome-only *system* constraint from
  §3.2 is unaffected and still stands.
- **Still open (separated out from the resolved `DEM` item above):** how should a resolver
  encode "physically impossible for this chassis type"? `DEM`'s motorhome-only constraint is
  stronger than a caveat — it's knowable in advance from the coach type and can never be
  satisfied by a travel trailer. Closer to a hard filter than a warning. Unresolved.
- ~~`SW3P` (3 gal, 9,000 BTU) exists, but 3 gallons is not on the confirmed capacity list in
  §3.2. Determine whether it is older, newer, or an omission.~~ **Resolved 2026-07-30:
  older.** `SW3P` was discontinued around 2005. The §3.2 chart and the master manual (obs
  #19) both postdate it, which is why neither lists a 3-gallon — the manual's opening figure
  starts at "4 & 6 Gallons". The lesson stands unchanged and is the part that matters:
  **capacity lists in vendor documents enumerate a current lineup, not a closed set.** The
  parser decodes capacity from the model string; it must never validate against a list.
- **New (and worth keeping despite the discontinuation):** `SW3P`'s unit height and width
  match the 6-gallon line exactly (12-11/16"), differing only in depth (3.0625" shallower).
  Since the manual assigns 4- and 6-gallon to one 12 3/4" opening family, `SW3P` **very
  likely shares that opening** — but the manual postdates it and doesn't say so, making this
  an inference rather than a confirmation.

  If it holds, the useful direction is **`SW3P` → `SW6*`**: someone with a dead 3-gallon can
  put a 6-gallon in the same hole and gain capacity, needing only ~3" more cavity depth. That
  is exactly the kind of upgrade path a salvage-parts index exists to surface, and
  discontinued-in-2005 makes it *more* relevant, not less — the coaches that shipped with
  these are precisely the ones being parted out now. Confirm the opening before creating the
  edge.
- ~~an **8-gallon** capacity appears in the V-Model door listings.~~ **Withdrawn
  2026-07-30.** Suburban did not make an 8-gallon water heater — no SKU, model, spec row, or
  product page across 18 observations. See §5.5. What the "8" refers to is still unknown but
  it is not an `SW` capacity, and it does not change parser behaviour.
- ~~HIGH PRIORITY — cutout depth conflict (§6.5).~~ **RESOLVED 2026-07-30** (obs #19):
  **there is no cutout depth.** The framed opening is 2D (A x B). Both retailer figures were
  category errors. `cutout_d` retired from the fixture; replaced by `opening_h`/`opening_w`
  plus a separate `unit_depth`.
- ~~Recovery rate 10.2 vs 10.1.~~ **Resolved 2026-07-30** (obs #20): manufacturer says
  **10.2 gas / 6.0 electric**. PPL correct; suburbanrvparts off by 0.1 on both.
- ~~First **manufacturer-vs-manufacturer** conflict: `SW3P` depth is 16-3/16" (obs #20) vs
  16-1/8" (obs #17), 0.0625" apart.~~ **PARKED 2026-07-30 — won't fix.** Two reasons, the
  second stronger than the first:
  1. `SW3P` was discontinued around 2005.
  2. **Depth is no longer a `critical_attribute`.** Since §6.5 established the opening is 2D,
     `unit_depth` is a secondary constraint. A 1/16" discrepancy on a non-key attribute is
     below the threshold worth resolving.

  Both values stay recorded in their observations. Revisit only if a real fitment case turns
  on 3-gallon depth — which would require an unusually shallow cavity.

  *The fact that two manufacturer documents can disagree at all is the finding worth keeping;
  this particular instance of it isn't.*
- **New:** `SW6DM` exists — bare Motor Aid *without* the electric element, at 6 gallons.
  Seen in a service-manual model list alongside `SW6DEM`. Confirms `DM` is real at more than
  one capacity (`SW10DM` already flagged) and that the §3.2 chart, which lists only `DEM`,
  is incomplete on this point.
- **New:** `SW6P` SKU is **5117A** (single retailer source, uncorroborated).
- **New fitment constraint:** 6-gallon models accept flush **or** surface mount doors;
  **all 10-gallon models require flush mount.** A hard door-compatibility rule, relevant to
  any `requires_part` edge resolving to a door SKU.
- **New:** door PNs appear with and without a `22-` prefix (`6255ACW` on the factory sheet
  vs `22-6255ACW` as a retailer MFR#). Determine whether that's a Suburban packaging
  distinction or a retailer artifact before treating them as distinct identifiers.
- **New:** doors follow the §5.2 colour-axis pattern — `6261ACW` (Colonial White) and
  `6261APW` (Polar White) are one component in two colours.
- **New:** "Dynatrail" appears as a product/marketing name for the SW series. Establish
  whether it's a brand overlay, a sub-line, or retailer copy before recording it as an
  identifier namespace.
- **New:** `V` is **overloaded** — it's both an ignition suffix (120V AC DSI, §3.2) and a
  product line ("V Model", §5.5) with its own door catalog and capacity range. Record the
  line as its own namespace before a parser or a person conflates the two.
- **New:** the V-Model line is entirely unresearched. Only trace so far is five door PNs
  (697205 / 690578 / 697221 / 6257ACW / 697213).
- **New:** aluminum-tank replacement door kits **520787 / 520818** are stocked PNs for
  retrofitting a Suburban SW6 into a 6-gallon aluminum-tank opening (§5.5). Confirm whether
  the target is specifically Atwood — the sheet says "aluminum tank," not the brand. Also
  find the 10-gallon equivalent if one exists.
- **New:** door-adapter kits **520781** and **520771** ("old style" → SW6) imply a
  *pre-SW* Suburban door generation with its own dimensions. Identify what "old style"
  refers to; it's likely the V-Model line, but that's unconfirmed.
- **New:** `SW16VE`'s ignition runs on **120V AC**, not the 12V DC used by every `D`-line
  unit. Confirmed as a real electrical-architecture difference, not a labeling quirk —
  see §3 and the compat-consequence note there. `attribute_schema` for part type 412
  probably needs an `ignition_power_source` field before this line goes through the
  clusterer, or it risks getting grouped with `D`-line units on cutout match alone.
- ~~Confirm whether a `D`/`DE`/`DEL`-grammar 16-gallon unit exists at all.~~ **Resolved
  2026-07-30** (obs #19): **`SW16D`, `SW16DE`, `SW16DEL`, `SW16DEM` all exist** and are named
  in the master service manual's installation figure. `SW16VE` is not the only 16-gallon
  offering. `SW4P` and `SW4D` are confirmed too, closing the 4-gallon question.
- **New:** `SW16VE`'s captured record has no depth, no BTU, no wattage, no weight. Thinnest
  capture so far — needs a second source before it's usable in the fixture.
- ~~Check whether the "Model Name Breakdown" text block appears on product pages across
  the rest of the line.~~ **Confirmed 2026-07-30** — present on SW12DELC and SW16VE pages
  too, not just SW6DEL/SW6DE. Three-for-three on water heaters. Still unconfirmed for
  furnaces and cooktops specifically; check before assuming the image transcription at
  `/model-number-breakdown/` is fully redundant.
- **New (SAW line, §4):** `SAW6DE`'s single dimension triple is **unlabeled** — the page
  doesn't say product size or cutout, unlike every `SW` page. Needs a second source before
  it can be filed as either. Do not guess.
- **New (SAW line):** `SAW6DE` requires switch **234589**, not the `SW` DEL colour trio
  (232882/233111/232881). Confirm whether that's a different electrical interface or just a
  different colour/branding SKU for the same switch — this decides whether the `SW` switch
  group extends here or a second group is needed.
- **New (SAW line):** find a SAW installation or service manual. The "Replaces Aluminum
  Tank RV Water Heaters" claim is currently `manufacturer_assertion` tier only (§4). A
  documented adapter/panel PN would promote it to `manufacturer_documented` and create real
  Atwood edges — the Nautilus manual (obs #14) is the precedent for what that looks like.
- **New (SAW line):** capture `SAW6D` (the non-`E` sibling, seen referenced but not fetched)
  to confirm the `D`/`DE` progression shares one envelope within SAW the way it does within
  SW (§4, SW16VE section).
- Pull `/sw-series-water-heater-parts-diagram/` — expected `shares_subassembly` source
  across SW6DEL / SW10DEL / SW12DEL / SW16DEL.
- ~~Resolve the 1400/1440 W conflict.~~ **Resolved 2026-07-30** (obs #20): **1440 W**,
  confirmed on all 15 manufacturer rows. suburbanrvparts' 1400 is wrong catalog-wide.
- ~~Resolve the 90-day/2-year warranty conflict.~~ **Resolved 2026-07-30** (obs #18, §6.4):
  2 years components + 3 years tank, corroborated by an independent retailer. The SW6DE
  page's 90-day figure is an error.
- Identify what occupies SKUs 5241A, 5242A, 5245A, 5246A — likely moot now that the
  catalog is confirmed non-sequential across capacities (§3.1); may simply not predict
  anything.
- Confirm SW4, SW12 and SW16 *unit* dimensions — the 2002 chart (obs #20) predates them and
  covers only 3/6/10 gal. Openings for all of them are already known from obs #19.
- **New:** capture the SW12/SW16 generation's own spec chart. Obs #20 is the 2002 lineup
  (P/PR/PE/PER/D/DE/DEM at 3/6/10 gal only); the DEL/DELC/V models and the 12- and 16-gallon
  capacities came later and have no manufacturer weight/recovery figures captured yet.
- Determine whether `C` and `M` suffixes affect cutout specifically (⟵ `C` label resolved
  above; `M` label now resolved too — see §3.2 — but neither's *dimensional* consequence
  is confirmed).
- ~~`IW60RL` (5280A, "Nautilus" on-demand/tankless line): no cutout data, unclear if
  `part_type_id: 412` applies.~~ **Resolved 2026-07-30** via the manufacturer service
  manual (obs #14) — see §4. Confirmed: no tank cutout on this platform at all, just a
  3.750" vent hole, plus a manufacturer-documented cross-vendor retrofit path (replacement
  panels for Suburban 6/10/12/16-gal and Atwood 6/10-gal cutouts). **Still open:** this
  platform needs its own `attribute_schema` (vent hole, not cutout h/w/d) before it goes in
  the fixture — not a slot in the existing 412 schema.

---

## 10. Adapter order (cross-vendor)

1. **Suburban** — owns one, clean grammar, small line, public manuals ← *here*
2. **Coleman-Mach / Airxcel** — hits multi-namespace identity early via the thermostat
3. **KIB** — assembly decomposition
4. Furnaces, roof vents — after

Findings consolidate into `VENDOR-Reference_RV_Components.md`, mirroring the structure of
the existing `VENDOR-Reference_Election_Tech.md`.
