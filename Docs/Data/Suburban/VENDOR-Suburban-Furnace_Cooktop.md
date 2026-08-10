# VENDOR — Suburban Manufacturing: Furnace & Cooktop (preliminary)

**Project:** RV Interchange
**Status:** furnace/cooktop endpoints + SRNA3SBBM repair-parts cross-reference built and
fixture-ready (§0, §5); the general cooktop model-number grammar (§3) is still preliminary
**Date:** 2026-07-30
**Source:** `suburbanrvparts.com/model-number-breakdown/` — three screenshot charts (furnace,
two cooktop eras). No text version found yet for these two families.

---

## 0. Update 2026-08-05 — exact endpoint components built

The owner's in-hand furnace (`SF-30FQ`) and cooktop/range (`SRNA3SBBM`) are now built as
exact fixture components, sourced from in-hand data-plate photographs and matching
manufacturer installation manuals the owner confirmed match their units — see
`docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md`. The furnace also has
a `fits` edge to its `2608A` core replacement module (catalog + retailer corroborated).

This is identity/dimension data for these two specific in-hand models, built independently
of the letter-by-letter grammar question below, which remains open. Do not treat this
section as resolving anything in sections 1–4.

---

## 1. Trust level — read this before using anything below

Everything in this document comes from **OCR/visual transcription of a compressed
screenshot**, not from vendor page text. Per the source-trust ranking established for the
SW-series (`VENDOR-Suburban.md` §6.1): spec block > prose > alt text > **this**.

Do not promote anything here to a `component`/`attribute` record, and do not use it in the
ground-truth fixture, until it's cross-checked against either a manual or a product page
with the same "Model Name Breakdown" text block the SW-series pages carry (confirmed
present on 3 of 3 water-heater pages checked so far — same trick likely works here).

---

## 2. Furnace — structure confirmed, letter meanings not yet confirmed

Same "grammar, not labels" pattern as the water heaters:

```
[series prefix] [BTU rating ÷ 1000] [suffix letters]
```

- **Series prefixes observed on the chart:** `NT`, `SF`, `SFV`, `P`.
- **Suffix letters** appear to mark sail-switch/spark-ignition variant and ducted/blower
  configuration — legible as a pattern, not confidently legible letter-by-letter at this
  resolution.

**Action before trusting this:** find one furnace product page and check whether it repeats
the breakdown as text, the way `suburbanrvparts.com/suburban-water-heater-sw12delc-.../`
did for water heaters. If the same authoring pattern holds, this whole section becomes
unnecessary — confirmed text beats re-squinting at a screenshot.

### 2.1 Manufacturer-confirmed: `F`, `V`, `H`, `Q` (2026-08-06)

Highest-trust source yet — a direct reply from Suburban's own support (see
`Gmail-FVHQ-code.pdf` in this folder; also recorded in GitHub issue #26, closed):

- **`F`** = front gas — gas inlet is on the front of the unit.
- **`V`** = vertical mounting.
- **`H`** = horizontal mounting — combined with `V` (i.e. `VH`), means the unit can be
  mounted either way.
- **`Q`** = quiet.

This confirms (and outranks) the informal `irv2.com` forum theory and the
`suburbanrvparts.com` SFQ-series page grammar mentioned in issue #26. Still unconfirmed by
this manufacturer reply: the sail-switch/spark-ignition/ducted-blower letters noted above,
and the two cooktop-era grammars in §3 — this only resolves the furnace `F`/`V`/`H`/`Q`
suffix letters.

---

## 3. Cooktops — two charts, likely two grammars

The breakdown page carries **two separate screenshots**, dated by filename to roughly 2018
and 2021. Two independent charts implies **the naming convention changed between
generations** — not a resolution problem, a real vendor change.

**Consequence for the schema:** cooktop model-number parsing may need to be
**date-gated**, not a single static grammar. A model number from a 2019 unit and one from
a 2023 unit could use the same-looking letters to mean different things. Don't assume
backward compatibility of the grammar itself.

**Not yet captured:** which specific letters/numbers changed meaning between the two
charts. Needs the same product-page-text check as the furnace line, ideally against
cooktops from both eras.

---

## 4. Open items

- Find a cooktop or furnace product page with an embedded text "Model Name Breakdown" —
  same method that resolved the water heater `C` and `VE` codes with high confidence.
- If no text version exists for these families, the screenshot needs a higher-resolution
  source (PDF manual, or a request to the vendor) before any letter-level claim goes into
  the fixture.
- Determine the actual cutover point between the two cooktop-era grammars.
- No part-type IDs, compat_mode, or attribute_schema assigned yet for furnace/cooktop —
  intentionally deferred until the grammar itself is trustworthy (see `ARCHITECTURE-
  Interchange_Core.md` §6: don't design the taxonomy on shaky ground). **Update 2026-08-09:**
  this still holds for the general cooktop-model grammar (§3 above); the SRNA3SBBM repair
  parts built in §5 below use a new dedicated type, `part_type_id: 606`, scoped to the one
  exact model already anchored in the fixture — not a resolution of the broader grammar
  question.

---

## 5. SRNA3SBBM repair-parts cross-reference (obs #117) — issue #37

Same "fits" many-to-many relationship as `atwood_repair_parts_and_fits()` (see
`VENDOR-Atwood.md` §7), sourced to Airxcel/Suburban's own "Replacement Parts List and
Parts Illustrations for Cook Top & Range Models" (doc `203705XP`, 03-13-2018,
`Docs/Data/Suburban/Cooktop/203705XP_RANGE.pdf`) rather than secondhand from the attached
AI research report (`SRNA3SBBM-Research.md`, issue #37).

**Model-number decoder verified directly:** the report's decode of `SRNA3SBBM` (S=Suburban,
R=Range, N=Conventional burner, A=Mercury Free, 3=3-Burner, S=17" short oven, B=Black
porcelain top, B=Black painted door, M=Match ignition) was cross-checked against the
manufacturer PDF's own "MODEL NUMBER POSITIONS" chart (p.1) and matches exactly.

**Three real parts the report's own table missed**, found by reading the PDF's parts list
(pp.8-9) directly rather than trusting the report's summary: `011008`/`011009`/`011010`,
the match-ignition top-burner assemblies themselves (center/right-rear/left-rear). The
report's parts table (its §8) named only the oven burner (`010994`) and no top-burner
part numbers at all. Also added after direct PDF read, not present in the report at all:
`521102`/`521103`, the BSI/Copreci manifold assemblies with black thermostat knobs — the
service-critical part per the report's own §7 discussion of manifold generations.

**Filtering:** the shared SRNA3S/SRSA3S table in `203705XP` covers many finish/ignition/
manifold variants across several sibling models at once (Piezo and Spark ignition,
stainless and glass-door finishes, long-oven, sealed-burner). Obs #117's extraction starts
from the attached report's own §8 parts table, corrected and pruned against a direct read
of the PDF — **not** the full config-filtered table. Excludes: long-oven-only, Piezo/
Spark-only, sealed-burner, stainless/glass, and sealed/nickel-manifold rows; the optional
deluxe grate (`031302`, not established as original per the report's own caution); and,
deliberately out of scope for this pass rather than excluded on evidentiary grounds, the
generic structural/hardware rows (clips, cover plates, brackets, screws, cabinet panels,
insulation, fittings) that are config-applicable but not repair-critical the way the
valve/burner/knob/manifold rows are.

**Manifold generation (Sabaf/BSI/Copreci) is not modeled as a caveat.** Each part's
`description` keeps the PDF's own `(BSI)`/`(Copreci)`/`(BSI/COPRECI)` qualifiers verbatim —
the same convention as Atwood's bracket rows (`VENDOR-Atwood.md` §9) — since manifold
generation is a property of the physical unit's build date, not of the SRNA3SBBM model
itself. This 2018 document also does not cover Sabaf-era units (2004-2006 production per
Suburban's Jan 2008 bulletin) at all — a real coverage gap, not an extraction error.

**In-hand unit cross-check, free from data already in `observations.db`:** obs #98's
serial for the owner's own SRNA3SBBM is `122109479` — well outside NHTSA recall 07E-022's
affected range (`063809986`-`063810173`, all manufactured September 2006), so **this
stove is not part of that recall.** The serial's `12`-prefix also lines up with Copreci's
January 2012 general release (vs. Sabaf's `04`-prefixed and BSI's `06`-prefixed production
starts per the 2008 bulletin) — a reasonable inference that the in-hand unit carries a
Copreci manifold, though this is not asserted as a component attribute, only noted here.

**Not built:** the `2863A -> 3108A` stock-number lead. The report itself found no
manufacturer document proving supersession — only a later retailer listing under the same
model description — so this stays unbuilt per this project's evidence bar. Cutout
dimensions from the report's lettered Figure-2 values are also not asserted; the letters
have no meaning without the installation drawing itself.

28 new repair-part components (`part_type_id: 606`), 28 `fits` edges —
`suburban_srna3sbbm_repair_parts_and_fits()` in `edge_resolver.py`, resolver version
`suburban_cooktop_parts_v1`. `ground-truth.yaml`'s fixture entry is counts + 3 spot-checks
(`suburban_srna3sbbm_repair_parts_fixture`), same shape as the Atwood tables' fixture
entries, not itemized per-part.

`edge_resolver.py --check-fixture`: 0 mismatches. `edge_resolver.py --self-test`: PASS.
`pytest`: 53/53 (fixed the pre-existing `test_part_types_cover_every_exported_constant`
gap from the Coleman AC build while adding the new `SUBURBAN_COOKTOP_REPAIR_PART_TYPE`
constant it required).
