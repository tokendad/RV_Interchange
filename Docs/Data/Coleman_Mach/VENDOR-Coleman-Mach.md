# VENDOR — Coleman-Mach / RV Products / Airxcel

**Status:** exact endpoint and supersession fixture complete; broader adapter research in progress
**Updated:** 2026-08-01 (obs #52/#53: `1C26-10` identified as a real candidate for one of
the manual's unnamed generations, but its only compatibility evidence is hedged and
unconfirmed — not yet strong enough for a graph edge)

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
in this fixture remains unestablished. Building `7330F3361`/`7330-3861`/`7330B3441` as
exact endpoint components (same shape as §6's three) is real, ready-to-do next work — the
evidence already exists across obs #40 + #55/#56.

### 6.2 Unresolved lead: the "electronic" generation candidate

An eBay listing for a candidate `7330E336`/`7330-336` electronic-generation model could
not be independently fetched (eBay blocks automated retrieval; `manuals.plus`'s mirror of
the closest manual found — for `7330G3351` — also 403s). Until one of those can be read
directly (or the user supplies the page text/screenshot), this candidate is not captured
as an observation at all — a bare identification claim with no readable source behind it
falls below even the `8330-3362`/`1C26-10` visual-candidate tier, which at least ties to a
real, fetchable page.

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

## 8. Resolver status and next milestone

The fixture resolver now builds the thermostat component from observations #44-#47,
persists 26 qualified attributes, and stores the retailer-only `AR7815`/`7330F3858` claim
as a separate open identifier-equivalence candidate sourced to observation #43.

It also builds the three exact catalog endpoints from manufacturer observations #40-#42
and persists the two directed, candidate `supersedes` edges above with observation #48/#49
corroboration. Fixture validation checks identifiers, null interchange codes, attribute
provenance, direction, detail, evidence, confidence, and the prohibited graph promotions.

Next, independently identify the service manual's unnamed mechanical, electronic, and
electronic-digital generations. The manual's compatibility statement remains a research
boundary, not a source of graph edges, until those exact identities are established. The
resolver must continue to keep compatibility, supersession, identity, and candidate
equivalence separate.
