# VENDOR — Suburban Manufacturing: Furnace & Cooktop (preliminary)

**Project:** RV Interchange
**Status:** preliminary — image-transcribed, NOT fixture-ready
**Date:** 2026-07-30
**Source:** `suburbanrvparts.com/model-number-breakdown/` — three screenshot charts (furnace,
two cooktop eras). No text version found yet for these two families.

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
  Interchange_Core.md` §6: don't design the taxonomy on shaky ground).
