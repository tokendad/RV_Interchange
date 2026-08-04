# VENDOR — JR Products (assembly) / American Technology Components (switch)

**Status:** exact assembly SKU confirmed; underlying ATC switch identity narrowed to
`AH-SWI-P09` family via ATC's own wire-color documentation, correcting the initial
`AP-SWI-019` candidate, which ATC's own datasheet rules out. Lippert independently
confirms `AH-SWI-P09` as a live, cataloged ATC part family (its own "Manufacturer
Reference Number") — the JR-to-ATC cross-reference itself is still not source-named, but
the underlying identifier is no longer resting on Wayback research alone.
**Updated:** 2026-08-03 (revised twice same day after new sources).

## 1. Why this adapter

JR Products is the third Stage 1 vendor. The in-hand part (a slide-room IN/OUT rocker
switch with bezel) turned out to be a two-namespace case like Coleman-Mach: the retail
product is sold and boxed as a JR Products part, but the switch itself carries no JR
Products marking at all — it's stamped with a different manufacturer's name. Resolving
this cleanly matters because getting the vendor wrong here would misfile every future
JR Products slide-out switch observation under the wrong namespace.

## 2. In-hand teardown (obs #76)

Six photographs record the physical assembly:

| Location | Marking |
|---|---|
| Faceplate | `SLIDE ROOM IN / OUT`, left/right gold arrows — no brand printed |
| Switch body (molded) | `American Technology Components, Incorporated` |
| Switch body (molded) | `40A. 12VDC` |
| Terminal block, pole 1 | `1b` `1` `1a` |
| Terminal block, pole 2 | `2a` `2` `2b`, also marked `CW` |

The switch is a DPDT rocker, momentary in both directions with a center-off spring
return (mom-off-mom) — consistent with a reversing-motor application: one pole switches
the motor's positive lead, the other its negative, so a single rocker throw reverses
polarity to drive the slide motor in or out. No ATC-style stamped part number (no
`AP-SWI-xxx` / `AH-SWI-xxx` string) appears anywhere on the physical unit.

Photographs:

- `Images/Slide Out Switch/20260801_104335.jpg` — faceplate, no brand marking
- `Images/Slide Out Switch/20260801_104434.jpg` — rear label, "American Technology... 12VDC"
- `Images/Slide Out Switch/20260801_104640.jpg` — side profile, terminal pins
- `Images/Slide Out Switch/20260801_104649.jpg` — rear label, "40A. 12VDC / American Technology Components Incorporated"
- `Images/Slide Out Switch/20260801_104702.jpg` — full rear label with `1b 1 1a` pin labels
- `Images/Slide Out Switch/20260801_104706.jpg` — pole 2 side, `2a 2 2b` and `CW` marking

## 3. Two-namespace identity

### 3.1 JR Products — the assembly/retail identity (confirmed exact)

`jrproducts.net` product 12075 (obs #77): **"Single Slide-Out Switch Assembly w/Bezel,
White"**, SKU `12075`, black variant `12285`. Switch type "Mom-On/Off/Mom-On", 12V, 40A
continuous, cutout 1.85in x 1.20in. This matches the in-hand unit's rating (40A/12V),
switch action (mom-off-mom), and physical form (bezel + rocker) exactly. **This is a
confirmed exact match for the complete assembly as sold.**

JR Products, Clarence Center, NY — a parts distributor/private-labeler, not a switch
manufacturer. Nothing in JR's own listing claims they manufacture the switch mechanism
itself.

### 3.2 American Technology Components (ATC) — the switch manufacturer

The switch body's own marking is the ground truth for who made the mechanism: American
Technology Components, Inc., Elkhart, IN. Two ATC part-number families were investigated;
one is now ruled out and one is now well-supported.

**`AP-SWI-019` — ruled out.** obs #80 (ATC's 2006 site, via Wayback) found this SKU under
*Recreational Vehicle > Switch Controls > Rocker Switches > AP Series Reversing Motor
Switches*, with matching top-line specs (40A DC, slide-room application). But **obs #83**,
ATC's own datasheet PDF, and **obs #85**, ATC's own `AP-INSTR-03` wiring-replacement
document, both show `AP-SWI-019` is a **5-pin switch using harness `AP-HRN-136`, wired
GRN / WHT / BLK / WHT / RED — no yellow wire.** The in-hand unit's physically observed
wiring (obs #76, user-confirmed against the harness) is black-yellow-green-black-red,
which does not match. Matching specs and application aren't enough when the wiring
disagrees — `AP-SWI-019` is a sibling product in the same family, not this part.

**`AH-SWI-P09` (variants `-1`/`-5`/`-8`) — current best match.** The same ATC document,
`AP-INSTR-03` (obs #85), directly compares `AP-SWI-019/086` against `AH-SWI-P09-1/5/8` as
a top/bottom switch-replacement pair, and gives the P09 switch's harness (`AP-HRN-401`) as
**BLK-GROUND / YEL-MOTOR OUT / GRN-MOTOR IN / BLK-GROUND / RED-POWER — an exact wire-color
match** to the in-hand unit. The same document gives a wall opening of 1.800in x 1.100in
for the P09 switch, closely matching the bare-switch dimension JR Products' own
distributor catalog lists for its slide-out switch (1.85in x 1.2in, obs #84). This is
still an ATC "Home Series"-prefixed SKU (`AH-`, not `AP-`) despite the RV-slide-room
application and RV-compatible wall-opening size — ATC's own naming convention does not
cleanly separate by application the way its catalog copy implies.

**obs #78/#79** (RecPro `RP-1146W`, affordablervparts "4 Prong") are both retailer-assigned
numbers, not ATC's own; obs #79's 4-prong claim is unconfirmed and now looks like simple
retailer-listing error given the 5-wire harness confirmed in obs #85.

### 3.3 JR Products' own manufacturer part numbers (obs #84)

A Coast Distribution wholesale electrical catalog (pages 172-177) gives JR Products' own
part numbers for both the bare switch and the bezel assembly:

| JRP # | Description | Color | Coast # |
|---|---|---|---|
| `12095` | Replacement Slide-Out High Current Motor Switch (bare, no bezel), 40A @ 14VDC peak, 1.85in x 1.2in | White | 14602 |
| `12295` | Same, bare switch | Black | 15146 |
| `12075` | Slide-Out Switch Assembly w/Bezel, cutout 1.85in x 1.20in | White | 14595 |
| `12285` | Same, w/Bezel | Black | 15143 |

The catalog also lists a 2-row wiring harness (JRP `13061`) explicitly compatible with
"5-pin straight row switches," Mfr# `12095, 12295, 12075, 12285, 12085, 12345, 12355` —
naming three more JRP numbers (`12085`, `12345`, `12355`) not otherwise documented here.

**obs #77/#87 — user-confirmed exact match.** The user directly compared the in-hand part
against `jrproducts.net/product/12075/` and its companion harness page
`jrproducts.net/product/13065/`, and confirms wiring, wire colors, and bezel shape all
match exactly. JR's own `13065` harness page (obs #87) states the wire configuration as
BLACK-Ground / YELLOW-Motor Out / GREEN-Motor In / BLACK-Ground / RED-Power — the same
five colors as ATC's `AH-SWI-P09` harness (obs #85) — and explicitly lists `12075` as one
of the harness's compatible switch models, alongside `12085`, `12095`, `12285`, `12295`,
`12345`, `12355`. This is JR's own documentation confirming the whole `12xxx` switch
family shares one wiring scheme, which is the same scheme as ATC's `AH-SWI-P09` — a much
stronger (though still not name-to-name) convergence than before.

**Working model:** JR Products' `12075` (assembly, user-confirmed exact) and `12095`
(bare switch) are very likely JR's own private-label SKUs for ATC's `AH-SWI-P09` switch —
same rating, same application, matching dimensions, and now matching wire colors across
JR's entire compatible-switch family — but no single source yet states the JR-to-ATC
cross-reference directly by naming both part numbers together.

### 3.4 Distributor/jobber cross-reference: `J4512095` / `NT-J4512095` (obs #88)

Several retailers (Young Farts RV Parts, Tractor Supply) list this part under
`J4512095` or `NT-J4512095` rather than JR's own `12075`/`12095`. Young Farts' page names
"JR Products" as manufacturer in structured data, gives GTIN `756815120951`, and its
description text is copied verbatim from JR's own `12075` assembly listing. This looks
like a distributor/jobber cross-reference number layered on top of JR's numbering, not a
JR or ATC part number itself — consistent with the user's read that `J4512095` is "the
generic version" SKU. One ambiguity: Tractor Supply's URL slug pairs this SKU with `12095`
(JR's *bare-switch* number per §3.3) while describing a bezel-included assembly (JR's
`12075` product) — so which JR SKU this cross-reference number actually maps to is not
fully disambiguated between retailers.

## 4. Lippert `AH-SWI-P09` — confirmed, not just a resemblance (obs #86, #89-91)

The user's original lead (obs #86, transcribed as `AH-SWI-009-8`) turned out to be
`AH-SWI-P09-8` — the exact same ATC part family already identified in §3.2, not a
similarly-numbered coincidence. **Lippert's own catalog states it directly:** Lippert
sells this switch under its own SKUs, with a field literally labeled "Manufacturer
Reference Number":

| Lippert SKU | Color | Manufacturer Reference Number |
|---|---|---|
| `131777` | Almond | `AH-SWI-P09-8` (obs #89) |
| `117426` | Black | `AH-SWI-P09-5` (obs #90) |
| `117461` | White | not directly confirmed; `AH-SWI-P09-1` expected by elimination (obs #91) |

Both confirmed listings describe a "5-terminal"/"5-pin" replacement switch for
Above-Floor and Through-Frame RV slide-outs, "new"-style, installed in Lippert slide-out
mechanisms after May 2006 — consistent with everything already gathered about `AH-SWI-P09`
from ATC's own `AP-INSTR-03` document (§3.2).

**This is significant beyond just closing the Lippert question.** It's the first source
anywhere in this research that names an `AH-SWI-P09` suffix as a *manufacturer reference
number* on a live commercial retail listing, from a completely independent major RV OEM
(Lippert, not a small retailer). That doesn't yet name JR Products specifically, but it
substantially de-risks the working model in §3.3: `AH-SWI-P09` is a real, current,
actively-cataloged ATC switch family used in mainstream RV slide-out systems by more than
one OEM, not an obscure Wayback-only identifier this research pieced together in
isolation. JR Products and Lippert both privately labeling the same ATC switch is exactly
the kind of shared-OEM-supplier pattern already seen in Coleman-Mach and Suburban.

## 5. What would close the remaining gap

- A source that names JR Products `12075`/`12095` and ATC `AH-SWI-P09` together by number
  (a JR spec sheet, invoice, or ATC OEM customer list) — wiring/dimensions/application now
  converge strongly (§3.3), and `AH-SWI-P09` itself is now Lippert-confirmed (§4), but no
  source states the JR-to-ATC cross-reference by part number.
- Confirming `AH-SWI-P09-1` as the white suffix. Black (`-5`) and almond (`-8`) are now
  pinned by Lippert's own catalog (§4); white (`117461`) is listed without its suffix, so
  `-1` is inferred by elimination, not directly confirmed — and the in-hand unit is white,
  so this is the one remaining disambiguation that matters for this specific part.

## 6. Not yet built

No components or edges have been resolved into `edge_resolver.py`/`components.db` yet.
The JR Products assembly (SKU 12075/12285) and bare switch (12095/12295) are safe to build
as exact components now, backed by JR's own catalog. Lippert's `131777`/`117426`/`117461`
family is now similarly safe to build, each backed by Lippert's own catalog. The
underlying ATC `AH-SWI-P09` identity is Lippert-confirmed as a real part family; what's
still missing is a source naming the *JR* cross-reference specifically (§5), so keep JR's
SKUs linked to `AH-SWI-P09` as observation-only until then.

## 7. Observation log

| # | Type | Source | Contributes |
|---|---|---|---|
| 76 | dataplate_photo | in-hand teardown, 6 photos | physical markings, terminal layout |
| 77 | retailer_page | jrproducts.net product 12075 | exact assembly SKU + specs |
| 78 | retailer_page | recpro.com RP-1146W | retailer SKU naming ATC as manufacturer |
| 79 | retailer_page | affordablervparts.com | conflicting pin-count claim (low confidence, now looks like listing error) |
| 80 | manufacturer_page | atcomp.com 2006 (Wayback) | AP-SWI-019, AP Series family, RV/slide-room application |
| 81 | manufacturer_pdf | atcomp.com AT-RLM-044 | current-day relay module + switch panel context |
| 82 | other | Wayback CDX API, full atcomp.com history | rules out AH-SWI-P10/AH-ASY-P1-5-001 as attested; confirms AH-SWI-0x (01-07) is Home Series, not RV |
| 83 | manufacturer_pdf | atcomp.com AP-SWI-019 datasheet | 5-pin harness AP-HRN-136, wiring GRN/WHT/BLK/WHT/RED — rules out AP-SWI-019 |
| 84 | retailer_page | Coast Distribution wholesale catalog pp.172-177 | JR's own SKUs: 12095/12295 (bare switch), 12075/12285 (assembly), dimensions |
| 85 | manufacturer_pdf | atcomp.com AP-INSTR-03, via techsupport.pdxrvwholesale.com | AH-SWI-P09-1/5/8 harness AP-HRN-401, wiring BLK/YEL/GRN/BLK/RED — matches in-hand unit exactly |
| 86 | other | user lead, Lippert AH-SWI-009-8 | open, unconfirmed sibling/private-label question |
| 87 | manufacturer_page | jrproducts.net product 13065 (harness) | JR's own wire colors match ATC AH-SWI-P09; lists 12075 in compatible-switch family |
| 88 | retailer_page | youngfartsrvparts.com, NT-J4512095 | distributor/jobber cross-reference SKU, manufacturer confirmed JR Products |
| 89 | retailer_page | lippert.com, 131777 Almond | Lippert's own "Manufacturer Reference Number" field states AH-SWI-P09-8 |
| 90 | retailer_page | lippert.com, 117426 Black | Lippert's own "Manufacturer Reference Number" field states AH-SWI-P09-5 |
| 91 | retailer_page | lippert.com / amazon.com, 117461 White / ELE-SWTCH-SLID-OUT | confirms white colorway exists in the same Lippert family; suffix not directly stated |
