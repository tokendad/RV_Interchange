# PARKED — myrvworks.com service manual library

**Project:** RV Interchange
**Status:** parked 2026-07-30, not being worked
**Why parked:** deliberately set aside to finish Suburban-line documentation first.

---

## What it is

`https://myrvworks.com/manuals/` — a mobile RV repair business (Darren Koepp, My RV Works
Inc., Port Angeles WA) hosts a curated library of manufacturer service manuals as PDFs.

**431 unique PDFs, 37 categories, 40 manufacturers.** Covers every family in the v0 scope
(`PLAN-Staged_Build.md` §3) plus three of the five in-hand fixture parts.

Manufacturers by volume: Dometic (97), Norcold (33), Atwood (30), Lippert (29),
Suburban (26), AquaHot (21), Splendide (20), Xantrex (14), HWH (12), Intellitec (12),
Equalizer Systems (12), AirXcel-Coleman (9), KIB Enterprises (5), Alde (5).

---

## What was done before parking

- `tools/manual_index.py` written — scrapes the index once, dedupes by URL, scores each
  row against v0 scope + interchange-content signals, writes `data/manual_queue.json`.
  **Downloads nothing.** 127 of 431 rows scored in-scope.
- `tools/observations.py` gained **PDF support** (see below) — this was a real blocker,
  not a nicety.
- Two PDFs captured as observations #15 and #16. Both stay in the append-only table.

---

## The blocker that got fixed (keep this even if the library is never used)

`observations.py`'s `fetch` stored `resp.text` for every response. On a PDF that is the
raw bytes decoded as text — `'%PDF-1.6\r%\xe2\x80\xa1...'`. It hashed clean, inserted
clean, and looked fine in `list`. Every PDF fetched before 2026-07-30 would have been
silently unusable.

Fixed: content-type detection → `pdfplumber` extraction → per-page text, with a
`_pdf_pages` report stored in `extracted` recording `pages_total`, `pages_text`,
`pages_image_only`, `needs_ocr`.

**This applies to any PDF source, not just this library** — including manufacturer
manuals fetched directly from Suburban, Atwood, Dometic, etc.

---

## The finding that matters most

**This library is roughly half scans.** Sampled:

| Document | Pages | Text-bearing | Image-only |
|---|---|---|---|
| Atwood Furnace Dimensions 2015 Revised | 23 | 23 | 0 |
| Suburban Water Heater Service Manual | 24 | **1** | **23** |
| Coleman Cross Reference Model Numbers | 3 | **1** | **2** |
| Vent Hinge Chart | 2 | 1 | 1 (the chart itself) |

The single most on-topic document in the library — Suburban's own water heater service
manual — is a stack of pictures with a text cover sheet. Anything derived from it is
OCR-tier evidence and needs the two-independent-transcription treatment that promoted the
water-heater grammar to *confirmed* (`VENDOR-Suburban.md` §3.2).

**Do not equate "downloaded" with "captured" for this source.**

---

## The prize, if this gets picked up again

`Atwood-Furnace-Dimensions-2015-Revised.pdf` — 23/23 pages text, fully extracted, already
in the db as **observation #15**. Contains:

1. **A positional model-number grammar for Atwood furnaces.**
   `AFSD12121` = Atwood Furnace / Small cabinet / DC / 12,000 BTU / LP / single-stage /
   outside-LD. Same shape as the Suburban `SW` grammar, different vendor.
2. **Four old→new supersession tables.** `8012-II → AFSAD12111 → AFSAD12121`,
   `7912-II → AFSD12111`, `8516-IV → AFMD16111`, `8535DCLP → AFLD35111`, and more.
3. **Old-vs-new cutout dimensions with explicit deltas** — `+7/8"`, `−1-1/8"`, `−4-3/8"`.

That third item is a manufacturer publishing quantified `fits_with_modification` edges.
Same evidence class as the Nautilus retrofit table (obs #14), for the Atwood side that
currently exists in the fixture only as `interchange_code: null` placeholders.

---

## If resumed — suggested order

The five highest-scoring rows in `data/manual_queue.json`:

1. Suburban Water Heater Identification
2. Suburban Furnace Model_Serial Number Identification
3. Suburban Nautilus Parts List
4. Suburban Furnace Troubleshooting Flowchart
5. Atwood Furnace Dimensions 2015 Revised ✅ *(already captured, obs #15)*

Items 1–2 may close the furnace-grammar gap that
`VENDOR-Suburban-Furnace_Cooktop.md` §1 is currently holding open at lowest-trust.

---

## Conduct note

This is one person's WordPress site, not a corporate CDN. `PLAN-Staged_Build.md` §7
already governs: rate-limit, cache raw responses, prefer manufacturer sources where both
carry the same fact. The manuals themselves are manufacturer copyright; the site states
they are believed released for distribution or public domain, which is the host's
assessment, not a license. Pull selectively, not exhaustively.
