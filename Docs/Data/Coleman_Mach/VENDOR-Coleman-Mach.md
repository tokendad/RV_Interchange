# VENDOR — Coleman-Mach / RV Products / Airxcel

**Status:** exact endpoint and supersession fixture complete; broader adapter research in progress
**Updated:** 2026-08-09 — built the owner's in-hand rooftop AC (Mach 3 Plus, model `48253B866`,
serial `051218899`) as an exact endpoint component (part type 604), split out from the
`8330A733` ceiling plenum (issue #23) which turned out to be a separate physical part — see
GitHub issue #36. Identity comes from photographed rating-plate + product-label evidence
(obs #111), independently corroborated by Coleman-Mach's own online model-number-replacement
lookup tool (`48253B866` → "MACH 3+ EZ A/C WHT OEM", current replacement `38203-066`, the
exact SKU the 2025 dealer catalog already in this fixture lists as "MACH 3 Plus, 13,500 BTU
A/C - Textured White"). Also built all 28 repair parts from Young Farts RV Parts' illustrated
parts-breakdown page for this exact product ID (obs #112, retailer tier 7 — no manufacturer
parts-catalog PDF was found for this legacy SKU) as `fits` edges (part type 605), plus a
`supersedes` edge for the fan motor pair (`1468-3069` → `1468A3069`, the table's own "USE
1468A3069" wording). Resolver functions `coleman_ac_48253b866_component()` and
`coleman_ac_repair_parts_and_fits()`, resolver versions `coleman_ac_endpoint_v1`/
`coleman_ac_parts_v1`. `edge_resolver.py --check-fixture` confirms 0 mismatches. See §9 below.

**Updated:** 2026-08-04 — the user supplied Airxcel's own current (May 2025) dealer catalog
(`CM-4040.02_2025 AMCAT.pdf`, `Docs/Data/Coleman_Mach/`), the highest-currency
manufacturer-primary source found for this vendor yet. Its own "NEW SINGLE STAGE
THERMOSTATS" THIS#/REPLACES/DESCRIPTION table (obs #93) directly names `9420-352` as the
current replacement for `7330F3361` — revising that component's earlier
"current/unsuperseded" framing from the second wave (§6.1) below, which was accurate only
because no replacement had been found in evidence *at that time*. `9420-352` built as an
exact endpoint component plus the `7330F3361 -> 9420-352` supersession edge
(`coleman_9420_352_component_and_supersession()`, resolver version `coleman_endpoint_v4`).
See §6.8. The same catalog page also names `9420A382` (digital, multi-target universal
replacement across three separate old-part groups) and `9420-391` (WiFi) — logged but not
yet built; see §6.8/§8 for scope notes.

**Updated:** 2026-08-04 — `7330E335`/`7330E385`/`7330E336` built as exact endpoint
components (`coleman_third_wave_endpoint_components()`, resolver version
`coleman_endpoint_v3`), plus the `7330E336 -> 7330F3361` supersession edge
(`resolve_coleman_third_wave_supersession()`), closing §8 items 1 and 3. No manufacturer
reply on color/date detail had arrived; the user asked to proceed with the build using the
evidence already in hand rather than continue waiting. `edge_resolver.py --check-fixture`
confirms 0 mismatches; the canonical rebuild command
(`python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db`)
has repopulated `components.db`. See §6.7/§8 below for the updated evidence-and-decision
record.

**Updated:** 2026-08-02 — `7330E335`/`7330E385`/`7330E336` confirmed as real,
manufacturer-catalogued RV Products SKUs via `rvcomfort.com` (RVP/Airxcel's own historical
site, found by the user on the Wayback Machine): the site's own catalog page names them
verbatim, linking to the same "Electronic"-generation document already in this fixture
(obs #71–#75, §6.7). Production window bounded to roughly Dec 2005–Jul 2008, between a
`D`-suffix family (named through Aug 2003) and the `G`/`F`-suffix family already built as
components. This resolves the identity question that had been open since the original,
never-fetchable eBay listing; whether to build the `E`-suffix trio as components is now
the open decision (§8 item 1). Along the way, a sixth retailer (`colemanmachac.com`, also
via Wayback) corrected an earlier evidentiary gap for `8330-3862` without changing the
decision to keep it observation-only (§6.6, obs #68–#70).

**2026-08-01/02, earlier this arc:** obs #58/#59 first unblocked the `7330E336`/`7330-336`
lead that eBay/manuals.plus had blocked (§6.2). Obs #60/#61 documented two third-party
aftermarket thermostats claiming compatibility with the 7330 wildcard family, one of which
(FARAMZ) confusingly reuses Coleman's own `7330F3852` number for a physically different
digital product (§6.4/§6.5). Obs #62 resolved §6.3's initial `9420-351`-vs-`8330-3362`
replacement conflict as two coexisting OEM-analog and digital-upgrade paths, not a
contradiction. Built `7330F3361`/`7330-3861`/`7330B3441` as exact endpoint components
(§6.1). Decided `8330-3362`/`8330-3862` will not be built as components — Coleman-Mach's
own current document library names its digital line only `9420-*` and has no entry for
either, and a retailer independently reports `8330-3362` itself discontinued (§6.6).

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

**Also confirmed, on a separate physical unit** (2026-08-06, observation #104): a
product-label photograph posted to a Forest River Forums thread
(`img_9829-jpg.1338016`, saved locally as
`Docs/Data/Coleman_Mach/Thermostat/IMG_9829.jpg`, research notes in
`AR7815_Research.md` in the same folder) shows both identifiers printed on the same
label:

```text
Part No: AR7815
Date Code: L16
RVP No: 7330F3858
L02745806316
```

This resolves the `AR7815`/`7330F3858` `identifier_equivalence_candidate` (previously
obs #43-only, GitHub issue #18) to a **confirmed alias**:

```text
ICM AR7815 = Coleman/RVP 7330F3858 (date code L16)
```

The bar here is stronger than the usual "second independent source" standard — this is a
direct photograph of the manufacturer's own physical label carrying both numbers on one
unit, not two separate sources describing the part in prose. Obs #43's used-parts-retailer
claim is now corroborated rather than standing alone. This is a distinct physical unit
from the `AP7862`/`7330G335` unit above — the two aliases are not shown to be the same
generation of thermostat.

Still candidate-only:

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
Display." At the time this section was first written, whether `7330-E336`/`7330-E385`
were themselves genuine predecessor codes within that lineage was still a hypothesis, not
a confirmed identity — **see §6.7, which resolves it** using a newly-found manufacturer
source (`rvcomfort.com`, RV Products/Airxcel's own historical site, via the Wayback
Machine).

### 6.7 Resolved, 2026-08-02: `7330E335`/`7330E385`/`7330E336` confirmed as real RVP SKUs

The user found `rvcomfort.com` archived on the Wayback Machine — RV Products/Airxcel's own
official site from the 2000s (footer: *"Copyright 2003 RV Products a Division of Airxcel,
Inc.,"* `webmaster@airxcel.com`), distinct from every retailer source used elsewhere in
this document. Digging through its archived catalog pages and PDFs (obs #71–#75) resolves
the identity question directly, using manufacturer-primary evidence rather than inference:

- **Obs #71/#72:** as of January 2003 (page's own "last modified" date, confirmed live
  through at least August 2003), RVP's own wall-thermostat catalog page names the family
  as `7330D3351` (Heat/Cool) and `7330D3361` (Cool Only) — a `D`-suffix generation, not yet
  the `G`/`F`-suffix family already built as components. The linked installation PDF
  (`1976-190.pdf`, internal title `1976B190.PDF`, created 2001-05-09) is the same document
  template, same physical control layout (Figure 2: `COOL/FAN/OFF/HEAT` slide,
  `AUTO/HIGH/LOW`+`LOW/HIGH/ON` fan switch, 55–90° vertical gauge, "Coleman-Mach" wordmark)
  already identified as the "Electronic" generation — just two revision letters earlier.
- **Obs #75:** by April and August 2005, the same catalog page lists **no** 7330-series
  wall thermostat entry at all — neither `D` nor anything else. A gap.
- **Obs #74, the key finding:** by December 2005 (confirmed unchanged through at least
  July 2008), the catalog page lists *"Installation Instructions For `7330E335*`,
  `7330E385*`, `7330E336*` Wall Thermostat"* — naming all three verbatim — linking to
  `pdf_documents/1976190.pdf`, the **same document number**, now at internal revision
  `1976F190` (created 2004-01-13, already in the fixture as obs #58/#65's wildcard-notation
  document). The PDF itself uses wildcard notation (`7330*335*/*385*/*336*`) to cover
  multiple suffix letters generically, but the manufacturer's own catalog link text names
  the specific letter in production at that time. Per obs #58's family statement
  (`*335*`/`*385*` = Heat/Cool, `*336*` = Cool Only): `7330E335` = Heat/Cool, `7330E385` =
  Heat/Cool (a second color/trim variant, unconfirmed which), `7330E336` = Cool Only — the
  same functional split as the already-built `7330G3351`/`7330F3852`/`7330F3361` family.

**This directly confirms `7330E335`/`7330E385`/`7330E336` as real, manufacturer-catalogued
RV Products SKUs** — not a retailer inference, not a coincidental part-number pattern
match — sold as the "Electronic"-generation family's current instantiation for a bounded
window, sitting between the `D`-suffix family (named through Aug 2003) and the `G`/`F`-suffix
family already built as components (current by the 2013 catalog, obs #42, still current
through 2025). The production timeline for this one physical body design is now:

| Suffix letter | Confirmed window |
|---|---|
| `D` (`7330D3351`/`7330D3361`) | Named Jan–Aug 2003 |
| *(gap in the catalog)* | Apr–Aug 2005 |
| `E` (`7330E335`/`7330E385`/`7330E336`) | Named Dec 2005 – Jul 2008 |
| `G`/`F` (`7330G3351`/`7330F3852`/`7330F3361`/`7330-3861`/`7330B3441`) | Current by 2013, still current 2025 |

Not yet confirmed: exact color for `7330E335` vs. `7330E385` individually (both are
Heat/Cool per the shared document, but which is white vs. black is not stated on this
catalog page), and the precise D→E and E→G/F transition dates (no `rvcomfort.com` capture
was found covering 2004 or 2009–2012 specifically). The user has separately emailed
Coleman-Mach directly requesting datasheets on the `E` variant — a parallel, possibly
faster path to the remaining color/date detail than further Wayback searching.

**This resolves the identity question that has been open since the original,
never-fetchable eBay listing.** Whether to now build `7330E335`/`7330E385`/`7330E336` as
exact endpoint components (the evidentiary bar that blocked `8330-3362`/`8330-3862` in
§6.6 is now met here) is a separate decision, tracked in §8.

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
  from a second, independent retailer. The `AR7815` alias itself was later confirmed
  directly by obs #104's product-label photograph — see §5.
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

**Correction, same day:** the paragraph above originally treated `8330-3862`'s evidentiary
tier as roughly equal to `8330-3362`'s. On re-checking every observation that mentions
`8330-3862` specifically (prompted by the user), that wasn't accurate — before obs #68,
`8330-3862` had **no dedicated product listing anywhere**, only a merchandising cross-sell
mention (obs #55) and a named-but-undescribed "black digital" sibling role in obs #59's
chart. Obs #68 (`colemanmachac.com`, via the Wayback Machine, a source the user supplied)
closes that specific gap: a dedicated, independently-priced listing (MSRP $99.99, sale
$85.22) with its own attributes, stating it too is discontinued and "superseded to part
number `9420-381`." Obs #69, the same retailer's `8330-3362` page, adds a fifth retailer
source for that SKU and independently corroborates the fixture's existing
`7330G3351 -> 9420-351` edge — but also states `8330-3362`'s replacement as `9420-381`,
a *third* distinct successor number after `9420-351` and obs #66's `9420A382`. This
retailer disagreement across sources on the exact 9420-series successor is itself
consistent with the §6.6 read (`8330-3362`/`8330-3862` predate a numbering-scheme change
and were never given one stable, manufacturer-documented replacement) rather than
undermining it. `colemanmachac.com`'s own footer identifies it as "an independent retailer
of Coleman®-Mach® by Airxcel, ... Seek Adventure LLC, Operating out of Florida, USA" — a
sixth retailer, not a manufacturer, despite the manufacturer-suggestive domain name. **The
decision above is unchanged**, but `8330-3862` should now be read as an independently
confirmed, once-current retail product (same as `8330-3362`), not a merely-inferred sibling.

Obs #70 additionally records a negative search: `colemanmachac.com`'s full recorded
history (695 unique URLs, Wayback captures 2017-06-30 through 2025-05-13, including a
direct check of its earliest known inventory listing) never lists `7330-E336`, `7330-E385`,
or any product described as an "electronic" (as opposed to analog/digital) generation
thermostat — this domain doesn't help resolve §6.2's open item, but is logged so a future
session doesn't repeat the search. It does independently confirm `9420-381` as a real,
current Coleman-Mach digital SKU (a third `9420-*` number now seen in this document).

### 6.8 Built 2026-08-04: `9420-352`, and `7330F3361`'s status revised

The user supplied Airxcel's own current dealer catalog, `CM-4040.02_2025 AMCAT.pdf`
(printed May 2025, document number CM-4040.02, `Docs/Data/Coleman_Mach/`) — a live, dated,
dealer-facing print catalog, a higher-currency manufacturer-primary tier than every
retailer/Wayback source used elsewhere in this document. Its Thermostats page (p.8) has a
"NEW SINGLE STAGE THERMOSTATS" table in the same `THIS#`/`REPLACES`/`DESCRIPTION` shape as
the original obs #41 replacement sheet that established the `-> 9420-351` edges (§6):

| THIS # | REPLACES | DESCRIPTION |
|---|---|---|
| `9420-351` | `7330G3351`, `7330F3852` | Analog, Heat/Cool, 12VDC - Black |
| `9420-352` | `7330F3361` | Analog, Cool Only, 12VDC - Black |
| `9420A382` | `7330F3361`, `9430-3392`, `9430A3392` | Digital, Cool Only, 12VDC - Black |
| `9420A382` | `9630A3351`, `9630A3361` | Digital, Heat Pump, 12VDC - Black |
| `9420A382` | `9630A3371`, `9430A3372` | Digital, Heat/Cool, 12VDC - Black |
| `9420-391` | *(none — new product)* | WiFi Accessible Digital Thermostat - Black |

The `9420-351` row corroborates the fixture's existing edges exactly (obs #41's own
successor, still current). The `9420-352` row is new: **obs #93, this session**, captured
by rendering the page to a PNG and reading it directly (`pdftotext -layout` interleaves
this table's two side-by-side blocks unreadably). It directly names `9420-352` as the
current replacement for `7330F3361` — the same model built in the second wave (§6.1) and
described there as current/unsuperseded, because no replacement had been found in evidence
at that time. This is that evidence, found later — **an honest revision, not a
contradiction**: §6.1's language reflected the evidentiary state as of 2026-08-02, not a
permanent claim.

**Built:** `9420-352` as an exact endpoint component (`function: cool_only, color: black,
interface_type: analog, voltage: 12VDC`, all from obs #93) plus the `7330F3361 ->
9420-352` `supersedes` edge, both via `coleman_9420_352_component_and_supersession()`,
resolver version `coleman_endpoint_v4`. Manufacturer-primary, single-source (no independent
retailer corroboration yet, unlike the obs #41 edges' retailer cross-references) —
confidence 0.75/n=4, same tier as the third-wave `7330E336 -> 7330F3361` edge (§6.2) for a
different underlying reason (single manufacturer source there vs. two retailer sources
here).

`7330F3361` now sits in the middle of a two-hop supersession chain:
`7330E336 -> 7330F3361 -> 9420-352` — not a contradiction; `7330F3361` was itself current
when it superseded `7330E336`; it has since itself been superseded.

**Not built this pass:** `9420-391` (WiFi, a new product with no REPLACES entry — nothing
to build a supersession edge from). `9420A382` was scoped and built separately — see §6.9.

### 6.9 Built 2026-08-04: `9420A382`, scoped to its one independently-evidenced edge

Decision on the `9420A382` item logged in §6.8/obs #93: **build the component, build only
the edge its evidence actually supports.**

The same catalog page's `9420A382` row lists three separate `REPLACES` groups under one
SKU — captured as a new observation, obs #94 (same page, same visual-read method as obs
#93), since obs #93 itself only logged this narratively (`other_replacements_noted_not_built`,
deliberately IGNORED_KEYS-classified, not usable as build evidence):

| REPLACES group | Description |
|---|---|
| `7330F3361`, `9430-3392`, `9430A3392` | Digital, Cool Only, 12VDC - Black |
| `9630A3351`, `9630A3361` | Digital, Heat Pump, 12VDC - Black, used with Single Stage Heat Pump Control Package & Gas Furnace |
| `9630A3371`, `9430A3372` | Digital, Heat/Cool, 12VDC - Black |

One SKU replacing three functionally distinct old-part groups is evidence that `9420A382`
is itself one multi-configuration digital thermostat (parallel to the already-catalogued
`9420A330` multizone unit, "fully programmable for cooling and heating... third party
heater"), not three different products sharing a number — so `9420A382` is built as a
**single** component with three `configurable_mode` attributes (`cool_only`, `heat_pump`,
`heat_cool`), rather than asserting one `function` value that would misrepresent the
evidence.

**Edge scoping:** of the six old part numbers named across the three groups, only
`7330F3361` already exists as an independently-evidenced component in this fixture. The
other five (`9430-3392`, `9430A3392`, `9630A3351`, `9630A3361`, `9630A3371`, `9430A3372`)
appear **only** as bare `REPLACES` targets on this one catalog row — no dedicated product
page, spec table, or description anywhere else in this fixture's evidence. That is the same
evidentiary gap that already keeps `7330D337`/`8330-339(2)` unbuilt (§6.2) despite also
being named in a `REPLACES`-style chart (obs #59). Consistent with that precedent: **only
the `7330F3361 -> 9420A382` edge is built.** The other five part numbers are logged in obs
#94's structured `sku_relationship.groups` field (real, citable evidence if a future session
finds independent confirmation for any of them) but are not identifiers, components, or
graph edges yet.

This makes `9420A382` `7330F3361`'s **second** coexisting replacement path, alongside the
analog `7330F3361 -> 9420-352` edge (§6.8) — the same "two coexisting, non-contradictory
paths" framing §6.3 already established for the original `7330G3351`/`7330F3852` pair. The
one difference from §6.3: there, the digital alternatives (`8330-3362`/`8330-3862`) never
cleared the manufacturer-primary-component bar (§6.6 decided against building them at all),
so only the analog path got a real graph edge. Here, `9420A382` clears that bar directly —
this catalog names it, with real attributes — so **both** paths get real edges. Not an
inconsistency with §6.3; the evidentiary bar was simply met this time.

Built via `coleman_9420a382_component_and_supersession()`, resolver version
`coleman_endpoint_v5`. Confidence 0.75/n=4 (manufacturer-primary single-source, same tier
as the `9420-352` edge). `edge_resolver.py --check-fixture`: 0 mismatches.

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
- obs #68/#69 — `colemanmachac.com` (Seek Adventure LLC), via the Wayback Machine
  (user-supplied snapshot URLs); dedicated retailer listings for `8330-3862`/`8330-3362`,
  correcting `8330-3862`'s prior evidentiary gap and adding a fifth/sixth retailer source
  overall (see §6.6 correction)
- obs #70 — `colemanmachac.com`'s full site history (695 URLs, Wayback captures
  2017-2025), searched for `7330-E336`/`7330-E385`/"electronic" — negative result, logged
  for future reference (see §6.2/§6.6)
- obs #71/#72 — `rvcomfort.com` (RV Products/Airxcel's own site, via Wayback Machine,
  user-supplied lead): Jan–Aug 2003 catalog page and installation PDF naming
  `7330D3351`/`7330D3361` (see §6.7)
- obs #73 — `rvcomfort.com`, Dec 2005 capture of the same installation PDF (by then
  revision `1976F190`, the wildcard-notation document already in the fixture) (see §6.7)
- obs #74 — `rvcomfort.com`, Dec 2005–Jul 2008 catalog page naming `7330E335`/`7330E385`/
  `7330E336` verbatim — the key finding resolving the electronic-generation identity
  question (see §6.7)
- obs #75 — `rvcomfort.com`, Apr/Aug 2005 catalog page showing no 7330-series listing at
  all, narrowing the D→E transition window (see §6.7)
- obs #93 — Airxcel's own current (May 2025) dealer catalog, `CM-4040.02_2025 AMCAT.pdf`
  p.8, "NEW SINGLE STAGE THERMOSTATS" table naming `9420-352` as the replacement for
  `7330F3361` (see §6.8)
- obs #94 — same catalog page, the `9420A382` `REPLACES` rows (three groups: cool-only,
  heat pump, heat/cool) (see §6.9)
- obs #104 — Forest River Forums thread attachment, physical label photograph confirming
  `AR7815`/`7330F3858` (see §5)

## 8. Resolver status and next milestone

The fixture resolver now builds the thermostat component from observations #44-#47,
persists 26 qualified attributes, and stores the `AR7815`/`7330F3858` claim as a separate
identifier-equivalence candidate sourced to observation #43 (retailer claim) and
observation #104 (physical label photo, 2026-08-06 — see §5). The candidate stays
`status: open` rather than `merged`, because neither identifier attaches to any
component_id in this fixture (a different physical thermostat than the in-hand
`AP7862`/`7330G335` unit) — `open` here means "identity confirmed, no component of ours to
merge into," not "unconfirmed."

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

1. **Resolved 2026-08-02 (§6.7, obs #71–#75), built 2026-08-04:** `7330E335`/`7330E385`/
   `7330E336` are confirmed real, manufacturer-catalogued RV Products SKUs — RVP's own
   historical site (`rvcomfort.com`, via Wayback Machine) names them verbatim, linking to
   the same "Electronic"-generation document already in the fixture. Production window
   bounded to roughly Dec 2005–Jul 2008, between the `D`-suffix family (named through Aug
   2003) and the `G`/`F`-suffix family already built as components. **Built 2026-08-04:**
   now exact endpoint components (`coleman_third_wave_endpoint_components()` in
   `edge_resolver.py`, resolver version `coleman_endpoint_v3`), from obs #74 (naming) +
   obs #58 (the wildcard family's functional split). No manufacturer reply on the `E`-variant
   datasheets had arrived by build time — the user decided to proceed on the evidence
   already in hand rather than continue waiting. Because color is unstated for all three in
   every captured source (unlike the `G`/`F`/`F3361`/`-3861` siblings), **no color attribute
   is asserted** on any of the three components — function (`heat_cool`/`heat_cool`/
   `cool_only`) and `interface_type`/`stages` (inferred, single-source) are. If the pending
   manufacturer reply ever arrives, fold in color and revisit the D→E/E→G transition dates.
2. **Resolved 2026-08-02 (§6.6, obs #66/#67):** `8330-3362`/`8330-3862` will **not** be
   built as exact endpoint components. A direct check of Coleman-Mach's own current
   document library shows its digital line is named exclusively `9420-*`, with no
   `8330-3362`/`8330-3862` document anywhere, and a retailer independently reports
   `8330-3362` itself discontinued (replaced by `9420A382`). No further action unless a
   manufacturer-primary source naming these SKUs directly turns up.
3. **Built 2026-08-04:** `7330E336 -> 7330F3361` `supersedes` edge
   (`resolve_coleman_third_wave_supersession()`), evidenced by two independent retailers
   (obs #59 MakariosRV's chart, obs #64 trvparts.com) — retailer-cross-reference tier only,
   no manufacturer-primary statement of this specific pairing, so confidence is 0.75/n=4
   (weaker than the manufacturer-backed `-> 9420-351` edges' 0.8/n=5). `7330D337` and
   `8330-339(2)` remain unbuilt identifiers (obs #59's chart also names `7330F3361` as their
   replacement) — out of scope here, a separate future decision.
4. **Built 2026-08-04 (§6.8, obs #93):** `9420-352` as an exact endpoint component plus the
   `7330F3361 -> 9420-352` `supersedes` edge, from Airxcel's own current (May 2025) dealer
   catalog. This revised `7330F3361`'s status from "current/unsuperseded" (§6.1) to
   superseded — an honest evidence-driven revision.
5. **Built 2026-08-04 (§6.9, obs #94):** `9420A382` as an exact endpoint component
   (`coleman_9420a382_component_and_supersession()`, resolver version `coleman_endpoint_v5`)
   plus the `7330F3361 -> 9420A382` `supersedes` edge — scoped to just the one
   independently-evidenced REPLACES group. The other two groups' old part numbers
   (`9630A3351`/`9630A3361`, `9630A3371`/`9430A3372`, heat-pump-line parts not otherwise in
   this fixture) remain unbuilt, same evidentiary treatment as `7330D337`/`8330-339(2)`.
   `9420-391` (WiFi, new product, no replacement target) remains unbuilt — nothing to anchor
   a supersession edge to.
6. The `2026 Attwood Catalog.pdf` the user also supplied this session is a **marine**
   products catalog (Atwood/marine items overlapping RV items only incidentally) — out of
   scope for this vendor, and out of scope for RV Interchange generally per the Atwood
   vendor's own marine-exclusion decision (`VENDOR-Atwood.md` §4). Not reviewed further.

## 9. Rooftop AC unit — `48253B866` (separate part type from the plenum)

Issue #23 was originally opened for "the Coleman-Mach rooftop AC" using the model number
visible on the owner's coach data plates (`8330A733`), but that number turned out to
identify the **room plenum** (interior ceiling assembly), not the rooftop AC head itself —
confirmed via Airxcel's own installation manual and catalog listings (research doc attached
to issue #23; plenum not yet built as a component in this fixture, remains open). The
rooftop AC's own model number is not visible without disassembly and was illegible on the
pink factory "build sheet" transcription (`Coleman 4853B866`-ish handwriting, too uncertain
to trust). Issue #36 tracks the AC unit itself, separately from #23's plenum.

**Identity (obs #111, 2026-08-09):** photographs of the physical unit's rating plate
(riveted inside the base/shroud ring: `MODEL NO. 48253B866  SERIAL NO. 051218899`) and a
separate "MACH 3 PLUS A/C" manufacturer label on the same unit. Independently corroborated
by Coleman-Mach's own online model-number-replacement lookup tool
(coleman-mach.com/search-model-number-replacement/), which returns `48253B866` as
"MACH 3+ EZ A/C WHT OEM" with current replacement `38203-066` — exactly the SKU the 2025
dealer catalog (already in this fixture, §"Why this adapter" catalog evidence) lists as
"MACH 3 Plus, 13,500 BTU A/C - Textured White." The `48253B866 -> 38203-066` replacement is
**not** built as a `supersedes` edge: `38203-066` itself is not in-hand or independently
built as a component here, so it stays a description-level note (same caution as the
compressor's unbuilt `14504209` variant below).

Built as component `c_placeholder_coleman_ac_48253b866` (part type 604,
`coleman_ac_48253b866_component()`, resolver version `coleman_ac_endpoint_v1`).

**Repair parts (obs #112, 2026-08-09):** Young Farts RV Parts' illustrated parts-breakdown
page for this exact product ID (`48253B866`) is the only parts-level source found — no
manufacturer repair-parts catalog PDF exists for this legacy SKU (Coleman-Mach's current
document library and 2025 catalog only cover the current `38203-066` replacement's sales
listing, not a service breakdown for either SKU). Retailer-only sourcing (tier 7) means
these `fits` edges carry weaker evidence than the manufacturer-catalog-sourced Atwood/
Norcold repair-part edges elsewhere in this project — `attribute_prior` + one
`retailer_cross_reference` event each, no `manufacturer_assertion`.

All 28 listed parts (26 numbered reference positions + 2 "NS"/not-shown-on-diagram items)
are built as repair-part components (part type 605) with `fits` edges to the host AC,
via `coleman_ac_repair_parts_and_fits()` (resolver version `coleman_ac_parts_v1`). One pair
names each other directly in the source table — `1468-3069` ("FAN MOTOR (FASCO D1092) USE
1468A3069") and `1468A3069` ("MOTOR") — the same explicit "(USE X)" supersession wording
already used for the Suburban/Coleman-Mach thermostats and Norcold's optical control board
elsewhere in this project; built as both a `fits` edge (each is still a real, orderable
part) and a `supersedes` edge (`coleman_ac_48253b866_fan_motor` group). The compressor row's
own "USE 14504209" note is **not** built the same way — `14504209` doesn't otherwise appear
in the table and isn't independently confirmed, so it stays a caveat inside the compressor
component's description rather than an invented component, consistent with this project's
standing rule against building identifiers from a single unconfirmed mention.

`edge_resolver.py --check-fixture` confirms 0 mismatches for both the endpoint and the
repair-parts/fits build.
