# VENDOR — Coleman-Mach / RV Products / Airxcel

**Status:** exact endpoint and supersession fixture complete; broader adapter research in progress
**Updated:** 2026-08-01 (obs #58/#59: a manufacturer wildcard-family manual and an
independent retailer's own replacement chart together unblock the `7330E336`/`7330-336`
"electronic generation" lead that eBay/manuals.plus previously blocked — see §6.2. Obs
#60/#61 add two third-party aftermarket thermostats claiming compatibility with the 7330
wildcard family, one of which (FARAMZ) confusingly reuses Coleman's own `7330F3852` number
for a physically different digital product — see §6.4/§6.5. Obs #62 resolves §6.3's initial
`9420-351`-vs-`8330-3362` replacement conflict as two coexisting OEM-analog and
digital-upgrade paths rather than a real contradiction. **2026-08-02:** built
`7330F3361`/`7330-3861`/`7330B3441` as exact endpoint components (§6.1); obs #64/#65
narrow the `7330-E336`/`7330-E385` "electronic generation" question — image evidence now
identifies the manual's "Electronic Thermostats" generation as the `7330*335*/*385*/*336*`
family itself, though `7330-E336`/`7330-E385`'s own exact identity stays observation-only
(§6.2). Decided `8330-3362`/`8330-3862` will not be built as components — the
manufacturer's own current document library names its digital line only `9420-*` and has
no entry for either, and a retailer independently reports `8330-3362` itself discontinued
(§6.6, obs #66/#67))

## 1. Why this adapter

Coleman-Mach is the second Stage 1 vendor after Suburban. The in-hand analog wall
thermostat is the first fixture case where identity crosses namespaces: its rear label
carries both an ICM part number and an RVP/Coleman number, while its circuit board carries
two additional manufacturing markings. Unlike water heaters, its compatibility key is the
electrical terminal interface rather than physical dimensions.

## 2. In-hand thermostat teardown

Observation #44 and four photographs record the exact physical unit:

| Namespace | Identifier | Location |
|---|---|---|
| ICM | `AP7862` | rear label, behind faceplate |
| Coleman/RVP | `7330G335` | rear label, behind faceplate |
| board silkscreen | `PCB1060` | reverse of circuit board |
| board silkscreen | `SPCB-2` | reverse of circuit board |

The rear label also gives date code `1203`. The photographs do **not** show the earlier
fixture variants `AP7862-3` or `PCB1060-4A`; those have therefore been removed from the
confirmed component. They may be related variants, but there is no evidence here that
allows suffixes to be discarded.

Photographs:

- `Thermostat Images/20260801_103947.jpg` — rear labels and installed harness
- `Thermostat Images/20260801_104000.jpg` — terminal labels, board positions, and colors
- `Thermostat Images/20260801_104039.jpg` — reverse-board `PCB1060` / `SPCB-2` markings
- `Thermostat Images/20260801_104050.jpg` — housing/date-wheel context

## 3. Terminal interface

The board photograph establishes the physical order, board positions, and installed wire
colors. The RV Products service manual `1976-376 (4-02)` (observation #45) establishes the
electrical function:

| Order | Terminal | Board position | Installed color | Manual function |
|---:|---|---|---|---|
| 1 | `R` | `W1` | red | +12 VDC supply |
| 2 | `Y` | `W5` | yellow | compressor control |
| 3 | `W` | `W6` | white | furnace/heat control |
| 4 | `GL` | `W3` | gray | low-fan control |
| 5 | `GH` | `W4` | green | high-fan control |
| 6 | `B` | `W2` | blue | 12 VDC negative/ground |

The installed colors agree with the manual's conventional colors, but color is supporting
evidence only. The manual explicitly warns that vehicle-manufacturer or installer wiring
may not follow those colors. Terminal label and function—not conductor color—form the
portable compatibility contract.

A second manufacturer document, RV Products/Airxcel installation instructions `1976F190
(1-04)` (observation #58, covering the `7330*335*`/`7330*385*`/`7330*336*` wildcard
family), independently corroborates the same six-terminal order and colors via its own
"Wire Cross Reference Chart," and adds one new fact: the `7330*336*` "Cool Only" variant
physically omits the `W` (heat) wire entirely, with a wire nut required over any unused
thermostat wire. That same chart also cross-references Coleman's `R`/`Y`/`W`/`GH`/`GL`/`B`
labels to unnamed "other manufacturers'" terminal designations (e.g. `RH`/`RC`-style
names for `R`) — the columns are not attributed to specific manufacturers, so this does
not on its own confirm or deny the obs #54 White-Rodgers question in §5, but it is worth
noting that Coleman's own manual acknowledges generic-HVAC terminal equivalents exist.

## 4. What the service manual proves

The manual covers 12 VDC Coleman/RV Products wall-thermostat control for rooftop systems.
It depicts mechanical/bimetal, electronic, and electronic-digital thermostats in
chronological order and says all three are completely interchangeable. It also documents
the operating connections:

- low cool connects `R` to `Y` and `GL`;
- high cool connects `R` to `Y` and `GH`;
- heat connects `R` to `W`;
- fan-only connects `R` to `GH`.

This is strong manufacturer evidence for compatibility among the depicted generations.
It is **not** proof that every catalog, builder, board, or retailer number found near those
products is a pure alias.

Local source: `Docs/Data/Coleman_Mach/Coleman-Wall-Thermostat.pdf`<br>
Mirror URL: <https://myrvworks.com/wp-content/uploads/2019/04/Coleman-Wall-Thermostat.pdf>

## 5. Identifier crosswalk boundaries

Confirmed on one physical unit:

```text
ICM AP7862 = Coleman/RVP 7330G335 = board PCB1060 / SPCB-2
```

Here `=` means the identifiers coexist on this one component, not that their namespaces
or numbering systems are generally interchangeable.

Still candidate-only:

- Observation #43: a used-parts retailer presents ICM `AR7815` and Coleman `7330F3858`
  as the same thermostat. Neither appears on the in-hand unit.
- `AR7816`, `AP7862-3`, and `PCB1060-4A` currently lack captured evidence sufficient to
  attach them to the in-hand component.
- Observation #40 lists the current manufacturer model `7330G3351`; the extra trailing
  digit must not be normalized away from the photographed legacy `7330G335` without an
  explicit cross-reference.
- Observation #41 says current `9420-351` replaces `7330G3351` and `7330F3852`. These are
  now represented as supersession edges, not alias claims.
- Observation #50 presents `8330-3362` as a close visual match for the service manual's
  unnamed electronic-digital illustration. The face, left display, up/down controls, and
  three lower slide controls agree, but visual similarity does not establish identity.
  `8330-3362` therefore remains observation-only: it is not an identifier, equivalence
  candidate, component, or graph edge.
- Observation #52 identifies `1C26-10` / `153-6616` as a real, distinct Coleman analog
  thermostat model (retailer listing, dimensions 3.1 x 3.75 x 1.75in, condition/pricing
  only — no compatibility claim on that page). It is a real candidate for one of the
  service manual's three unnamed generations (the manual's own "mechanical," "electronic,"
  and "electronic-digital" categories are broader than "analog" vs "digital," so which
  generation `1C26-10` maps to is still unconfirmed).
- Observation #53 (a forum Q&A on a separate `8330-3362` listing) asked whether `8330-3362`
  is compatible with `1C26-10`. Manufacturer support "could not pull up thermostat type
  1C26-10" at all; a later staff reply calls `1C26-10` "obsolete with no direct
  replacements," and relays an HVAC technician's **hedged, unconfirmed** suggestion of
  `7330G3351` as a "possible alternative," explicitly recommending the buyer verify
  connections with a dealer first. This is the weakest evidence tier captured for Coleman
  so far — not a manufacturer-documented or retailer-cross-reference claim, and not
  strong enough to justify a `substitutes`/`supersedes` edge. `1C26-10` therefore remains
  observation-only, same treatment as `8330-3362`.
- Observation #54 is an installation manual for **White-Rodgers (Emerson Electric)**
  models `1C20`/`1C26` — a mechanical, snap-action heat/cool thermostat with an adjustable
  heat anticipator, PN `37-6335B`. This is a **different manufacturer than Coleman-Mach /
  RV Products / Airxcel entirely**. The "1C26" number match with the retailer's "1C26-10"
  (obs #52) is suggestive of an OEM/private-label relationship — RV suppliers commonly
  rebadge generic HVAC hardware — but the document itself does not name "Coleman" or
  "1C26-10" anywhere, and its terminal scheme (`RH`/`RC`/`G`/`W`/`Y`/`O`/`B`/`A`, standard
  residential HVAC) is unrelated to the RV wall thermostat's terminal scheme documented in
  §3 (`R`/`Y`/`W`/`GL`/`GH`/`B`). **This does not confirm that `1C26-10` is the unit
  depicted in the service manual's unnamed "mechanical/bimetal" illustration** — that
  remains a visual/contextual hypothesis, not an established identity, and is tracked the
  same way as the `8330-3362` candidate: not an identifier, equivalence candidate,
  component, or graph edge.

## 6. Exact catalog endpoints and supersession edges

Manufacturer observations #40-#42 establish three components independently from the
in-hand `7330G335` thermostat:

| Exact component | Manufacturer-backed attributes |
|---|---|
| `7330G3351` | analog, single-stage Heat/Cool, white, 12 VDC |
| `7330F3852` | analog, single-stage Heat/Cool, black |
| `9420-351` | analog Heat/Cool, black, 12 VDC |

Each component has a null interchange code. No terminal map is inferred from the in-hand
unit. The 2025 manufacturer catalog and the two matching retailer replacement narratives
support exactly these candidate edges:

```text
7330G3351 -> 9420-351
7330F3852 -> 9420-351
```

Observation #48 corroborates the first pair while internally conflicting between its
Heat/Cool title and `Gas Furnace` specification. Observation #49 corroborates the second
while conflicting between its Heat/Cool title and `Heat Pump, Heat Strip/Element`
specification. Those retailer conflicts remain preserved in the evidence store and do not
override the manufacturer attributes. Each edge carries an incomplete-attribute prior,
the manufacturer assertion from observation #41, and its corresponding retailer
cross-reference, producing Beta(4,1), confidence 0.8 with certainty 5.

### 6.1 Wider 7330-family: real numbers, not yet built into components

Observation #40's own manufacturer model table already lists `7330F3361` and `7330-3861`
(and `7330B3441`) as real analog single-stage thermostats alongside `7330G3351`/`7330F3852`
— they were simply never built into their own components by the resolver yet.
Observations #55-#57 (rvacguys.com) now independently corroborate all three:

| Model | Function | Color | Stages | Readout |
|---|---|---|---|---|
| `7330F3361` | cool_only | white (obs #40) | single | mechanical |
| `7330-3861` | cool_only | black | single | mechanical |
| `7330F3852` | heat_cool | black | single | mechanical (2nd retailer, corroborates obs #48/#49) |

Obs #55/#56 also cross-sell `7330B3441`, `8330-3362`, `8330-3862`, `9430A3543`, and
`9630A3351` on the same pages — a merchandising widget, **not a stated compatibility or
replacement claim**. This is the first independent-retailer confirmation that `8330-3862`
and `9430A3543` are real catalog numbers (as opposed to only appearing in a single visual
candidate or a user's own reverse-image search), but their relationship to anything else
in this fixture remains unestablished.

**Built 2026-08-02:** `7330F3361`/`7330-3861`/`7330B3441` are now exact endpoint
components (`coleman_second_wave_endpoint_components()` in `edge_resolver.py`, resolver
version `coleman_endpoint_v2`), same shape as §6's three, no supersession edges (no
replacement target is stated in evidence for any of the three — a targeted evidence pass
through obs #59's MakariosRV replacement chart found `7330F3361` named as the *current
replacement* for legacy identifiers `7330D337`/`7330-E336`/`8330-339(2)`, but none of
those are built as components, and promoting them is separate, larger-scope work — see
§6.2/§8 item 2). `7330F3361` and `7330-3861` carry two-source evidence (obs #40 +
obs #55/#56 respectively); `7330B3441` stays single-source (obs #40 only, provenance
`manufacturer_page_single_source` on its `interface_type` attribute) since obs #55/#56
only cross-sell it without stating attributes. `edge_resolver.py --check-fixture`
confirms 0 mismatches for all three.

### 6.2 The "electronic" generation candidate: narrowed, still not fully resolved

The eBay listing for a candidate `7330E336`/`7330-336` electronic-generation model was
never independently fetchable (eBay blocks automated retrieval), and an earlier attempt to
reach a `manuals.plus` mirror of the closest manual (for `7330G3351`) also 403'd. Several
new sources (obs #58/#59, and #64/#65 this session) progressively unblock this lead
without fully resolving unit-level identity:

- Observation #58 is the manufacturer installation manual `1976F190 (1-04)` for
  `7330*335*`, `7330*385*`, **and `7330*336*`**. It independently establishes `7330*336*`
  as a real, current, manufacturer-documented wildcard family member — a "Cool Only"
  physical variant of the same thermostat body, differing only by the omitted `W` wire and
  disabled heat/furnace switch positions (see §3). It does **not** mention `7330E336` or
  `7330-336` specifically.
- Observation #59, an independent retailer's ("MakariosRV.com") own model-lookup and
  replacement chart, lists `7330-E336` directly (current replacement: `7330F3361`) and
  `7330-E385` directly (current replacement: `8330-3482`, a model number not otherwise seen
  in this fixture). This is the first time `7330-E336`/`7330-E385` have been read from a
  fetchable, citable source — the eBay dead end is no longer the only lead — but it is
  retailer cross-reference tier, not manufacturer-documented, and it does not itself
  describe the `7330-E336` unit's physical characteristics.
- Observation #64 (trvparts.com) independently names `7330F3361` as the replacement for
  `7330-E336` — a third, independent corroboration of that specific replacement pairing
  (after obs #40's implicit family membership and obs #59's chart).
- **Observation #65, this session:** obs #58's own installation-manual PDF (`1976F190`,
  fetched a second time via a different mirror — rvupgradestore.com — specifically to
  render its Figure 2 to an image, since the manuals.plus text-only capture couldn't) shows
  the physical control layout for the `7330*335*/*385*/*336*` family: a `COOL/FAN/OFF/HEAT`
  slide switch, an `AUTO/HIGH/LOW`+`LOW/HIGH/ON` fan-speed switch, and a vertical
  thermometer-style gauge (55–90°) with a slider. This is **visually identical** to obs
  #45's Coleman-Wall-Thermostat.pdf page 3, which depicts (unlabeled by part number) three
  chronological generations — "1. Mechanical/By-Metal" (a round dial with a heating
  anticipator), "2. Electronic Thermostats" (this same switch-and-gauge layout), and
  "3. Electronic Digital Display Thermostats" (the `RVComfort.HC` LED-readout unit already
  linked to `8330-3362` as a visual candidate, obs #50). Two independent manufacturer
  documents showing the identical control layout is direct evidence, not part-number
  pattern-matching: **the service manual's "Electronic Thermostats" generation is the
  `7330*335*/*385*/*336*` family** — already built as fixture components
  (`7330G3351`/`7330F3852`/`7330F3361`/`7330-3861`/`7330B3441`, superseded-to `9420-351`).

Net effect: the "which of the three manual generations" question is now answered for the
*family* — `7330*335*/*385*/*336*` (and therefore `7330F3361`, its already-built current
member) is the "Electronic" generation, not "Mechanical/By-Metal" or "Electronic Digital
Display." This makes it a reasonable hypothesis that `7330-E336`/`7330-E385` were earlier
product codes within this same "Electronic" generation lineage (the `E` plausibly standing
for "Electronic") — but this remains a hypothesis, not a manufacturer-confirmed identity:
no source shows a photo or manufacturer statement of `7330-E336`/`7330-E385` themselves, so
their exact relationship to `7330F3361`/`7330-3861` (same physical unit under an older SKU
scheme, vs. a genuinely distinct predecessor unit later replaced by it) is still open — same
evidentiary gap as `8330-3362` and `1C26-10` elsewhere in this document. They remain
observation-only, not promoted to components or graph edges.

### 6.3 Two coexisting replacement paths, not a real conflict: OEM analog vs. digital upgrade

Observation #59's replacement chart also lists a current replacement for the fixture's own
exact endpoints and the in-hand unit's own identifier:

| Old model (obs #59) | Retailer's stated current replacement |
|---|---|
| `7330G335` (in-hand unit, §2) | White digital: `8330-3362` / Black digital: `8330-3862` |
| `7330G3351` (exact endpoint, §6) | White digital: `8330-3362` / Black digital: `8330-3862` |
| `7330F3852` (exact endpoint, §6) | White digital: `8330-3362` / Black digital: `8330-3862` |

This initially looked like a conflict with the manufacturer-documented supersession already
in this fixture (`7330G3351 -> 9420-351` and `7330F3852 -> 9420-351`, §6, obs #40-42/48/49).
Two further sources resolve the framing rather than the tension itself:

- Observation #48's own raw content (already captured, not previously quoted this
  precisely) includes the retailer's rendered, non-template product text: *"Model
  7330G3351 is no longer produced. Your order will include the latest OEM replacement (Part
  9420-351). Function, wiring and compatibility remain the same, but the housing and display
  style are different."* Combined with the 2025 manufacturer catalog (obs #41), `9420-351`
  is the manufacturer's own, singular, official supersession target — not one retailer's
  preference among several.
- Observation #62 (rvupgradestore.com's `8330-3362` product page) shows Coleman-Mach itself
  (via this retailer) marketing `8330-3362` as a direct replacement for a *cluster* of older
  analog models (`7330G335`, `7330E335`, `7330D335`, `7330F3858`, `7330A335`) — and, on the
  same page, separately offering `7330G3351` itself as a named "Alternative Analog
  Thermostat" option for customers who don't want to switch to digital.

Read together, these are **two coexisting, non-contradictory replacement paths**, not
competing claims about one correct answer: `9420-351` is the official OEM analog
supersession for the exact discontinued analog part, while `8330-3362`/`8330-3862` is a
widely-marketed digital upgrade path that most customers now choose instead — which is
almost certainly why MakariosRV's own chart (obs #59) defaults to recommending the digital
part. This is still retailer/aftermarket-tier reasoning about customer preference, not a
manufacturer statement that `8330-3362` supersedes `7330G3351`/`7330F3852`, so no additional
graph edge is added here; the existing `-> 9420-351` edges remain the fixture's only
supersession claim, and `8330-3362`/`8330-3862` remain observation-only alternatives.

Observation #59 also independently corroborates two previously weaker leads:

- `7330F3858` (obs #43's `AR7815`/`7330F3858` used-parts-retailer claim) appears in the
  MakariosRV chart as its own old-model row, confirming it is a real Coleman model number
  from a second, independent retailer — still not enough to confirm the `AR7815` alias
  itself, which remains an open `identifier_equivalence_candidate`.
- `8330-3862` (previously seen only in obs #55/#56 cross-sell widgets) appears repeatedly
  in the chart as the named black-digital sibling of `8330-3362` in an explicit replacement
  role, not merchandising placement — stronger evidence that it is a real, distinct catalog
  number, though still not tied to any specific old model in this fixture as a confirmed
  supersession.

Observation #59 also includes a photograph of a *second*, independently-owned physical
thermostat with rear label `Part No: AP7862`, `Date Code: C15`, `RVP No: 7330G335` — the
same `AP7862 = 7330G335` identity pair as the in-hand unit (§2), but a different date code.
This corroborates that pairing as a stable identity across at least two physical units,
not a single label fluke.

### 6.4 Third-party product reusing the `7330F3852` name: not the same device

Observation #60 is a FARAMZ-brand instruction manual for a "7330F3852" thermostat.
**FARAMZ is a third-party aftermarket brand, not Coleman-Mach/RV Products/Airxcel**, and
this unit is a **touchscreen digital** thermostat (`Controller Type: Touch Control`,
`Display Type: Touchscreen`) — a fundamentally different device from the
manufacturer-documented `7330F3852` exact endpoint in §6, which is analog/mechanical
(obs #40/#41). FARAMZ markets its own product under Coleman's OEM number, presumably
because it is wired as an electrical drop-in replacement: its terminal labels, functions,
and wire colors (`R`/`Y`/`W`/`GH`/`GL`/`B`, same colors) exactly match the RV Products
scheme in §3/obs #58. This is the same treatment already applied to obs #54
(White-Rodgers): a different manufacturer's product that overlaps an existing identifier
is evidence about *that manufacturer's marketing*, not about the identifier's own
referent. `FARAMZ`/its touchscreen unit is not an identifier, equivalence candidate,
component, or graph edge in this fixture.

A second aftermarket product, observation #61 (Briidea RV Thermostat, model `MK-101`, via
manuals.plus), avoids that overlap: it markets itself under its own model number, not a
Coleman number, while explicitly claiming OEM-replacement compatibility with the
`7330*335*`/`7330*385*`/`7330*336*` wildcard family using the manufacturer's own notation
from obs #58. It also independently corroborates the 3-minute compressor short-cycle delay
(obs #45/#47/#58) and the cool-only fuse difference (obs #58), though its own suggested
fuse rating (1A) differs from the OEM manual's stated 2A — different products, not a
contradiction of the OEM spec. Like the FARAMZ manual, this is aftermarket
compatibility-claim evidence, not manufacturer-documented, and does not by itself justify
a graph edge.

### 6.5 Reference only: the 8330-33X digital-family manual

Observation #63 is the manufacturer manual `1976-333 (9-04)` for `8330-336`/`337`/`338`/`339`
— a four-model digital-display wildcard family (heat/cool for `336`/`337`, cool-only for
`338`/`339`) with the same `R`/`Y`/`W`/`GH`/`GL`/`B` terminal scheme and colors, the same 2A
fuse, and the same 3-minute anti-short-cycle delay as the analog family (obs #45/#58). The
retailer links this exact PDF from the Q&A section of their `8330-3362` product page
(obs #62's page), which is suggestive that it is the closest manual they have for that
digital product — but the manual's own title and content only name `336`/`337`/`338`/`339`,
a different digit count than `8330-3362`, and the manual **does not name `8330-3362`
anywhere**. Captured for reference at the user's request; not built into a component and
not tied to the fixture's `8330-3362`/`8330-3862` exact endpoints without a more direct
identity confirmation.

### 6.6 Decision, 2026-08-02: `8330-3362`/`8330-3862` stay observation-only

Closing §8's former item 2. Two new checks this session tip the evidence from "not yet
confirmed" to "actively against":

- Observation #66 (rvproductsshop.com, the same RVPS retailer chain already trusted for
  the obs #48/#49 "no longer produced" quotes) states `8330-3362` **is itself now
  discontinued**, replaced by `9420A382` — a *third* distinct `9420-*` SKU alongside
  `9420-351` (§6, the analog supersession target) and `9420-391` (see next bullet).
- Observation #67, a direct check of Coleman-Mach's own current official document library
  (`library.coleman-mach.com`) — the highest-trust source available, distinct from every
  retailer mirror used elsewhere in this document — names its digital wall-thermostat line
  exclusively by `9420-*` numbers (`9420-381`, `9420-382`, `9420-391`) and lists **no
  document for `8330-3362` or `8330-3862` anywhere**.

Four retailers (obs #50/#55/#62/#66) independently describe `8330-3362` with consistent
attributes, and it is a real, purchasable product — this is not a case of doubting the
part exists. But the project's bar for an *exact endpoint component* has consistently been
a manufacturer-primary or -secondary source naming the specific SKU (every §6/§6.1
component has one), and `1C26-10`/`7330-E336`/`7330-E385` already established that retailer
volume alone doesn't clear that bar. Here the negative check goes further: the
manufacturer's own current library confirms its digital line under a *different* numbering
scheme and omits `8330-3362`/`8330-3862` entirely, and a retailer independently says
`8330-3362` is itself discontinued. The likeliest explanation is that `8330-3362`/`8330-3862`
were never Coleman-Mach's own catalog numbers with independent manufacturer documentation —
possibly a reseller/private designation, or an older SKU retired before the current library
was assembled.

**Decision: do not build `8330-3362`/`8330-3862` as exact endpoint components or add a
`supersedes` edge from them.** They stay observation-only, same treatment as `1C26-10` and
`7330-E336`/`7330-E385`. Revisit only if a manufacturer-primary source (a catalog page, a
model-specific install manual, a manufacturer email) surfaces that names `8330-3362`/
`8330-3862` directly.

## 7. Sources

- obs #40 — Coleman-Mach current analog thermostat product page
- obs #41 — Coleman-Mach 2025 aftermarket catalog
- obs #42 — 2013 RVP/Coleman product catalog via MyRVWorks
- obs #43 — used-parts retailer `AR7815` / `7330F3858` claim
- obs #44 — in-hand rear-label, terminal, wiring, and circuit-board photographs
- obs #45 — RV Products/Airxcel service manual `1976-376 (4-02)`
- obs #46 — structured PCB-position transcription supplement to obs #44
- obs #47 — structured voltage/stage extraction supplement to obs #45
- obs #48 — RV Products Shop `7330G3351` replacement page; exact `9420-351` pair plus
  conflicting `Gas Furnace` specification
- obs #49 — RV Products Shop `7330F3852` replacement page; exact `9420-351` pair plus
  conflicting `Heat Pump, Heat Strip/Element` specification
- obs #50 — RV Products Shop `8330-3362` page and photograph; open visual match candidate
  for the manual's unnamed electronic-digital illustration
- obs #52 — rvpartshop.ca used `1C26-10`/`153-6616` listing; identity only, no
  compatibility claim
- obs #53 — answers.rvupgradestore.com Q&A; manufacturer could not identify `1C26-10`,
  hedged unconfirmed third-party suggestion of `7330G3351` as a possible alternative
- obs #54 — White-Rodgers (Emerson) `1C20`/`1C26` installation manual, PN `37-6335B`; a
  **different, residential-HVAC manufacturer** — the "1C26" number match with obs #52's
  "1C26-10" is suggestive but unconfirmed, not established identity
- obs #55 — rvacguys.com `7330F3361` product page (cool_only, single, mechanical, 12VDC,
  white); cross-sells `7330B3441`/`8330-3362`/`8330-3862`/`9430A3543` (not a compatibility
  claim)
- obs #56 — rvacguys.com `7330-3861` product page (cool_only, single, mechanical, 12VDC,
  black); cross-sells `9630A3351`/`7330G3351`/`7330F3361`/`7330B3441`/`7330F3852` (not a
  compatibility claim)
- obs #57 — rvacguys.com `7330F3852` product page; second independent retailer
  corroborating black/single-stage/heat-cool (obs #40/#41/#49); first note of Coleman-Mach's
  current ownership by Dometic
- obs #58 — RV Products/Airxcel installation instructions `1976F190 (1-04)` for
  `7330*335*`/`7330*385*`/`7330*336*`, via manuals.plus mirror; manufacturer confirmation
  of the `7330*336*` "Cool Only" wildcard family member and its wiring difference
- obs #59 — MakariosRV.com's Guide to Coleman Thermostats (replacement chart), via
  manuals.plus mirror (makariosrv.com now 403s); first fetchable source for
  `7330-E336`/`7330-E385`, a new conflict with the `-> 9420-351` supersession edges, and a
  second physical-unit corroboration of `AP7862 = 7330G335`
- obs #60 — FARAMZ 7330F3852 RV Thermostat Instruction Manual, via manuals.plus (exact URL
  not captured); a **third-party, non-Coleman brand's** digital touchscreen thermostat
  marketed under Coleman's own `7330F3852` model number — a different physical product, not
  evidence about Coleman's own `7330F3852`
- obs #61 — Briidea RV Thermostat User Manual, model `MK-101`, via manuals.plus; a
  **third-party** OEM-replacement product (own model number, no identifier overlap) that
  independently corroborates the `7330*335*`/`7330*385*`/`7330*336*` wildcard family
  grouping, the 3-minute compressor short-cycle delay, and the cool-only fuse difference
- obs #62 — rvupgradestore.com `8330-3362` digital thermostat product page; shows
  Coleman-Mach's own retailer marketing `8330-3362` as a direct digital-upgrade replacement
  for a cluster of older analog models while separately offering `7330G3351` itself as a
  named "Alternative Analog Thermostat" — resolves the §6.3 framing as two coexisting
  replacement paths, not a conflict
- obs #63 — RV Products/Airxcel installation/operating instructions `1976-333 (9-04)` for
  `8330-336`/`337`/`338`/`339`, via rvupgradestore.com (linked from the obs #62 product
  page's Q&A section); the digital-family counterpart to obs #45/#58's analog manual,
  captured for reference only per the user's request — does not itself name `8330-3362`
- obs #64 — trvparts.com `7330F3361` product page; third independent retailer naming
  `7330F3361` as the replacement for `7330-E336` (see §6.2)
- obs #65 — obs #58's own installation-manual PDF (`1976F190`), refetched via a second
  mirror (rvupgradestore.com) specifically to render Figure 2 to an image; visually
  identical to obs #45's unlabeled "Electronic Thermostats" generation illustration,
  identifying the `7330*335*/*385*/*336*` family as that generation (see §6.2)
- obs #66 — rvproductsshop.com `8330-3362` product page; states `8330-3362` is itself
  discontinued, replaced by `9420A382` (see §6.6)
- obs #67 — `library.coleman-mach.com`, the manufacturer's own current document library;
  negative check confirming it names its digital thermostat line only by `9420-*` numbers
  and lists no `8330-3362`/`8330-3862` document (see §6.6)

## 8. Resolver status and next milestone

The fixture resolver now builds the thermostat component from observations #44-#47,
persists 26 qualified attributes, and stores the retailer-only `AR7815`/`7330F3858` claim
as a separate open identifier-equivalence candidate sourced to observation #43.

It also builds the three exact catalog endpoints from manufacturer observations #40-#42
and persists the two directed, candidate `supersedes` edges above with observation #48/#49
corroboration. Fixture validation checks identifiers, null interchange codes, attribute
provenance, direction, detail, evidence, confidence, and the prohibited graph promotions.

**2026-08-02:** a second wave of three exact endpoint components —
`7330F3361`/`7330-3861`/`7330B3441` — is now built from observations #40/#55/#56, with no
supersession edges (see §6.1). Same validation coverage as the first three, minus edge
checks (none apply).

Next, independently identify the service manual's unnamed mechanical, electronic, and
electronic-digital generations. The manual's compatibility statement remains a research
boundary, not a source of graph edges, until those exact identities are established. The
resolver must continue to keep compatibility, supersession, identity, and candidate
equivalence separate.

Ready-to-do next work, in rough priority order:

1. **Partially resolved 2026-08-02 (§6.2, obs #64/#65):** which manual generation
   `7330-E336`/`7330-E385` belong to is now narrowed to "Electronic" (image-matched to the
   already-built `7330*335*/*385*/*336*` family), but their own exact unit-level identity
   is still unconfirmed — no photo or manufacturer statement of `7330-E336`/`7330-E385`
   themselves exists in any source found so far (eBay remains unfetchable; no forum photo
   turned up). Revisit only if a new fetchable source surfaces (a manual, a forum post with
   a rear-label photo, or a retailer page that itself shows the unit rather than only
   naming it in a replacement chart).
2. **Resolved 2026-08-02 (§6.6, obs #66/#67):** `8330-3362`/`8330-3862` will **not** be
   built as exact endpoint components. A direct check of Coleman-Mach's own current
   document library shows its digital line is named exclusively `9420-*`, with no
   `8330-3362`/`8330-3862` document anywhere, and a retailer independently reports
   `8330-3362` itself discontinued (replaced by `9420A382`). No further action unless a
   manufacturer-primary source naming these SKUs directly turns up.
3. If item 1 gets a confirming source, revisit whether `7330F3361` (already built, see
   §6.1) should get a `supersedes` edge from `7330D337`/`7330-E336`/`8330-339(2)` once one
   of those legacy identifiers is itself promoted to a component.
