# VENDOR — JR Products (assembly) / American Technology Components (switch)

**Status:** CLOSED — research exhausted via public sources. Exact assembly SKU
confirmed; underlying ATC switch family identity confirmed as `AH-SWI-P09`, both by
ATC's own wire-color documentation and independently by Lippert naming `AH-SWI-P09-5`
(black, `117426`)/`AH-SWI-P09-8` (almond, `131777`) as their own "Manufacturer Reference
Number." The JR-to-ATC white cross-reference and the `AH-SWI-P09-1` suffix itself remain
formally unconfirmed; working theory (§4a) is that JR's white switch was a private,
dealer-specific ATC order never given a public SKU, meaning no further public-source
search is likely to close it. Only a direct manufacturer/dealer reply would move this
forward from here.
**Updated:** 2026-08-04 (closed after exhausting public-source research).

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

## 4. Lippert `AH-SWI-P09` — confirmed for black/almond; white is a different family (obs #86, #89-95)

The user's original lead (obs #86, transcribed as `AH-SWI-009-8`) turned out to be
`AH-SWI-P09-8` — the exact same ATC part family already identified in §3.2, not a
similarly-numbered coincidence. **Lippert's own catalog states it directly:** Lippert
sells this switch under its own SKUs, with a field literally labeled "Manufacturer
Reference Number":

| Lippert SKU | Color | Manufacturer Reference Number |
|---|---|---|
| `131777` | Almond | `AH-SWI-P09-8` (obs #89) |
| `117426` | Black | `AH-SWI-P09-5` (obs #90, re-confirmed obs #95) |
| `129003` → `670704` | White | `AH-SWI-P10-8` — **different family** (obs #92-93) |

Both black/almond listings describe a "5-terminal"/"5-pin" replacement switch for
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

**Correction (obs #92-94, revised same day as first entered):** the "white suffix
expected by elimination" reasoning below (formerly citing SKU `117461`) was wrong.
`117461` is not a bare switch — user supplied Lippert's Electric Through-Frame Slide-Out
Owners Manual (`Docs/Data/Lippert/Lippert-Electric-Through-Frame-Slide-Out-Owners-Manual-0001613.pdf`,
pages 21/35/42, obs #92) showing `117461`/`117460` are full kit SKUs (switch + bezel plate
+ wire harness `178436`), with the bare switches broken out separately as `129003` (White)
and `117426` (Black). Following `129003` to Lippert's current listing (obs #93, user-supplied,
it supersedes to SKU `670704`) gives Manufacturer Reference Number **`AH-SWI-P10-8`**,
a **4-prong** connection — a different ATC family than `AH-SWI-P09`, and a prong count
that contradicts the in-hand unit's 5-wire harness outright. Meanwhile `117426` Black
independently re-confirms `AH-SWI-P09-5` on its own current product page (obs #95,
user-supplied), matching the earlier obs #90 finding.

**Net effect (confirmed by obs #96, a Lippert-issued parts complist, not just a retail
page):** Lippert's black and white switches for this kit family are genuinely two
different ATC part families, not color variants of one — and `129003`/`670704` (white,
`AH-SWI-P10-8`) is confirmed as the actual, current, non-superseded-in-substance switch
shipped inside kit `117461` (the complist explicitly notes `129003` is "OBSOLETE - Use
670704," i.e. same part, renumbered, not a redesign). The "5-terminal" wording on
`117461`'s own retail page (obs #94) appears to be either boilerplate/marketing-copy
inaccuracy or refers to the harness rather than the switch itself — the complist and the
`670704` product page both independently say 4-prong/`AH-SWI-P10-8`.

**This closes off the Lippert-white avenue definitively, not just provisionally:**
Lippert does not sell an `AH-SWI-P09` white switch at all; their white offering is a
different, 4-prong ATC family that doesn't match the in-hand unit's 5-wire harness. The
`AH-SWI-P09-1` white-suffix question (§5) needs a source outside Lippert.

## 5. What would close the remaining gap — CLOSED, research exhausted (2026-08-04)

- A source that names JR Products `12075`/`12095` and ATC `AH-SWI-P09` together by number
  would still close this cleanly (a JR spec sheet, invoice, or ATC OEM customer list) —
  wiring/dimensions/application converge strongly (§3.3), and `AH-SWI-P09` itself is
  Lippert-confirmed for black/almond (§4). But per the working theory in §4a, this
  cross-reference is likely an internal JR↔ATC record that was never published, so no
  amount of further public-source searching is expected to surface it. Only a direct
  reply from JR Products or ATC would resolve it from here.
- ~~Confirming `AH-SWI-P09-1` as the white suffix~~ — **closed, obs #97-99, see §4a.**
  Concluded that `AH-SWI-P09-1` most likely was never an actual stocked/sold part, based
  on its total absence from every live source checked (WESCO distributor catalog, ATC's
  current shop, general web search), despite ATC's `-1`/`-5`/`-8` = White/Black/Almond
  suffix convention being independently well-attested across several *other* ATC product
  lines. The in-hand unit's specific white-suffix number remains formally unconfirmed,
  but this line of research is exhausted, not just paused.

**Research on this adapter is closed for now.** Nothing left to chase via public sources;
next movement requires either a direct manufacturer/dealer reply or new physical evidence.

## 4a. `AH-SWI-P09-1` white suffix — concluded likely never existed (obs #97-99)

User research (`Docs/Data/American Technology Components/ATC_Sku_Research.md`) surveyed
WESCO's distributor catalog (obs #97, several `AH-SWI-0x`/`AH-SWI-P07` listings) and
ATC's naming pattern across other product lines (obs #98: `AH-SLD-5-HS01`/`AH-SLD-1-HS01`,
`AT-RLD-1/5/8-LS01`, etc.) and found no listing anywhere for `AH-SWI-P09-1`, despite the
`-1`/`-5`/`-8` = White/Black/Almond suffix convention being solid and repeated across
several ATC lines. Independently re-verified (obs #99): a general web search turns up
nothing for `AH-SWI-P09-1`, and ATC's current shop (`shop.atcomp.com/controls/switch-panels/`)
doesn't carry `AH-SWI-P09` at all anymore (consistent with it being a discontinued/older
line surviving only in the archival `AP-INSTR-03` instructional PDF, obs #85).

**Conclusion:** `AH-SWI-P09-1` most likely was never an actual manufactured/stocked part
— it appears to be a pattern-completing placeholder in one instructional document rather
than a real catalog entry. This closes the white-suffix sub-question as *exhausted*
rather than *resolved*: there's no more research path left to pursue on it specifically.
The `AH-SWI-P09` family identity itself (§3.2, §4) is unaffected — only the white variant
number is in question.

**Working theory (user, 2026-08-04): private, dealer-specific ATC order, not a public
SKU.** Given `AH-SWI-P09-1` is completely absent from every public source (WESCO, ATC's
own current shop, general web search) while ATC's `-1`/`-5`/`-8` color-suffix convention
is otherwise solid, the most likely explanation is that JR Products ordered a white
variant directly from ATC for its own private-label line, and ATC either assigned it the
pattern-consistent `-1` suffix or some other designation informally, without ever
publishing it — because no third party would ever need to look it up. This is standard
practice for private-label OEM arrangements: the cross-reference exists only as an
internal record between JR Products and ATC (a purchase order, a mold/tooling spec, an
internal parts database), not as public-facing documentation. If that's correct, the
JR-to-ATC white cross-reference (§5) is not just hard to find — it may not exist in any
form a public search could ever surface. Closing this research thread on that basis;
revisit only if JR Products or ATC responds directly to a manufacturer inquiry with
something that names it.

## 5a. Reference material (not part identity, keep for troubleshooting)

`Docs/Data/Lippert/ccd-0001613-through-frame-electric-slide-out-manual.pdf`
(manuals.plus copy of the same CCD-0001613 manual as §4/obs #92, but with the
Slide-Out Switch Wiring Diagram page intact) contains the full switch-to-motor-to-
controller-to-battery wiring sequence with wire colors. Not yet mined for this
identity question, but flagged as a useful troubleshooting reference for future
slide-out electrical work generally.

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
| 92 | manufacturer_pdf | Lippert Electric Through-Frame Slide-Out Owners Manual (0001613), pp.21/35/42, user-supplied local copy | kit BOM: `117461`/`117460` are switch+plate+harness kits; bare switches broken out as `129003` (White) / `117426` (Black) |
| 93 | retailer_page | lippert.com, 129003 → superseded to 670704 White | Manufacturer Reference Number `AH-SWI-P10-8`, 4-prong — different ATC family than P09, contradicts in-hand unit's 5-wire harness |
| 94 | retailer_page | lippert.com, 117461 White kit (current listing) | describes itself as "5-terminal switch assembly," inconsistent with 4-prong `129003`/`670704` BOM component — likely a parts revision, current kit's actual switch not identified |
| 95 | retailer_page | lippert.com, 117426 Black (user-supplied direct link) | re-confirms Manufacturer Reference Number `AH-SWI-P09-5`, matching obs #90 |
| 96 | manufacturer_pdf | lci-support-doc.s3.amazonaws.com CCD-0002560 parts complist, user-supplied | authoritative BOM: kit 117460 (Black)→switch 117426; kit 117461 (White)→switch 129003 (OBSOLETE, use 670704) — confirms 670704/AH-SWI-P10-8 as current white switch, not a stale generation |
| 97 | retailer_page | buy.wesco.com, several AH-SWI-0x/AH-SWI-P07 listings, user research | no `AH-SWI-P09-1` listing found; establishes WESCO carries other AH-SWI lines but not this suffix |
| 98 | manufacturer_page | shop.atcomp.com/controls/switch-panels/, user research + agent re-check | confirms `-1`/`-5`/`-8` = White/Black/Almond suffix convention across other ATC lines (AH-SLD, AT-RLD); `AH-SWI-P09` itself absent from current shop entirely |
| 99 | other | general web search, agent re-check | no result anywhere for `AH-SWI-P09-1`; corroborates user's conclusion that it likely was never a stocked part |
