# Staged Build Plan

**Project:** RV Interchange
**Status:** Stage 1 implementation in progress
**Date:** 2026-07-29

> **Note:** Stages 1–2 below (the database and the free lookup tool) constitute the
> **RV Interchange** project. Stage 3 (listings) and Stage 4 (dealers) describe a
> **separate marketplace project**, to be started later, that consumes RV Interchange as
> its data layer. They're kept in this plan for sequencing context, not as scope of the
> current project.

---

## 1. Ordering principle

**The marketplace grows out of the database, not the other way around.**

Why not listings first:

- A listing's free text tells you *that a part exists*. It does not tell you what that part
  *substitutes for*.
- Grouping comes from normalizing published specs — work that can be done alone, in advance,
  with no users.
- Launching listings without interchange produces Facebook Marketplace with less inventory.

---

## 2. The four stages

### Stage 1 — Interchange core

Vendor adapters: Suburban, Coleman-Mach / Airxcel, KIB, Dometic, Lippert, Furrion,
Atwood (legacy).

- **Zero users required.**
- This is the same grind as the CivicMirror state adapters: HAR/source capture →
  identify platform → document endpoints → produce per-vendor research markdown.
- **This is the only uncopyable part of the product.**

### Stage 2 — Free lookup tool

No accounts. No listings. No payments.

Answers two questions: *what is this?* and *what fits it?*

- **Works on day one with zero supply.** This is the point.
- Each data-plate photo submitted is a fitment observation.
- Each empty result is a demand signal.
- Useful as a standalone product even if the marketplace never ships.

### Stage 3 — Listings

Now nearly free to build. A listing is *identification + price*, bound to a `component_id`.
The hard part — identification — already exists from Stage 2.

### Stage 4 — Dealers

Last. Only when demand volume is worth selling to them.

---

## 3. v0 scope — the bet

**Five part families:**

1. Water heaters
2. Furnaces
3. Thermostats
4. Monitor panels
5. Roof vents

**Ship:** tiered lookup. **Do not ship:** any marketplace.

**Distribute:** RV subreddits; the RV equivalent of the existing Plex/*arr Facebook group.

**Read the result:** if the empty-result log fills up, that log *is* the demand map and the
build order for what comes next.

### The test for whether Stage 1 is the right first step

> Is the lookup tool worth shipping even if the marketplace never happens?

If yes, the ordering is right.

### Secondary benefit

Sidesteps disputes, fraud, and trust & safety at the moment of maximum vulnerability —
which matters given the concurrent CivicMirror-API live ENR capture window.

---

## 4. Roles — three roles, one engine

**Not three interfaces.**

Buyer and seller are **the same identification engine pointed in opposite directions**:

- Buyer: *what do I need* → identify → find
- Seller: *what is this* → identify → list

Build identification once.

**Do not make users pick a role at signup.** Role is a *mode*. The same person buys and
sells in a single session.

### Fourth role: contributor

Identifies without transacting. No account required.

This is data intake disguised as a free tool. Useful on day one with zero supply.

### Dealer is not an interface — it's an integration problem

Yards already have working systems: phone, email, eBay storefronts. A data-entry form is
an unacceptable behaviour change for a small family business.

**Approach:** index their CSV exports and public eBay stores → send them phone-call leads on
matches. Zero change on their end. Public eBay stores (e.g. Colaw) can be indexed with no
partnership at all.

**Note for the business model:** yards ship (liquid nationally). Individuals mostly do local
pickup only. This should be a **filter** before it is a business model.

---

## 5. Known risks

| Risk | Notes |
|---|---|
| Two-sided cold start | Mitigated by Stage 2 being useful with zero supply |
| Freight fragmentation | Large parts are local-pickup-only; fridges and doors don't ship |
| Leakage | Used-parts deals happen by phone, bypassing any take rate |
| Data provenance / legal | See §7 |

**Where the economics do work:** a 6-gallon water heater is ~35 lbs and ships UPS ground.
The used route is unusually viable for this size class — which is part of why water heaters
are a good v0 family.

---

## 6. The retention problem

**Most people will never come back.** This is a once-every-few-years purchase with no reason
to build a habit. Plan for single-digit response rates, then build so single digits suffice.

In order of leverage:

### 6.1 Ask once, at the right moment, one tap

One email at ~10 days. Three buttons: **Fit** / **Fit with modification** / **Didn't fit**.

- No login gate.
- Ask "what happened" *only* on the negative taps.
- One question, no account, is the difference between 4% and 15%.

### 6.2 Then stop asking

An edge with 30 confirmations does not need a 31st. Route asks only to edges that are
uncertain, high-variance, or stale-and-high-traffic.

Most buyers get no email at all — which is also why the ones who do respond better.

### 6.3 Harvest silence as weak evidence

No return, no dispute, no re-search within 60 days → **α + 0.5**.

Genuinely weaker than a confirmation; weight it that way. But it applies to *everyone*,
making it the highest-volume input by a wide margin.

### 6.4 Mine free negative signals

Returns citing fitment. Disputes. A buyer re-searching the same component two weeks later.

These arrive without asking — and since failures already carry heavier weight, **the
passively-captured evidence is precisely the evidence that moves confidence most.**
Fortunate alignment: the expensive signal to collect is the one you need least of.

### 6.5 Two structural points that outweigh all of the above

**Sellers are the better data source.** A yard listing parts is on the platform weekly —
a repeat user by nature, where a buyer never is. A yard that has pulled forty water heaters
knows things no buyer does. And teardown co-occurrence is self-reporting: a coach that
shipped with an Acme in a cutout originally spec'd for a Suburban is a fitment observation
with no human confirmation step at all.

**The highest-intent moment is mid-install, not post-install.** Someone with the old unit out
and the new one in their hands is on their phone *right then*, looking up specs. If the
identification tool is useful at that moment, they are already on the site — and that is when
to ask.

> A tool that is useful during the job earns return visits on its own merits.
> A marketplace has to beg for them.

This is an independent argument for shipping Stage 2 before Stage 3.

---

## 7. Legal / ethical position

- Manufacturer manuals are meant to be read. Reading them is uncontroversial.
- **Bulk-scraping retailer catalogs is a different thing.**
- The underlying *facts* — that two part numbers denote one part — are not copyrightable.
  Presentation and site terms are real constraints.

**Practice:**

- Rate-limit.
- Cache raw responses (which the `observations` table does anyway).
- Prefer manufacturer sources wherever both a manufacturer and a retailer carry the fact.

---

## 8. Market context

RV *rental* was modernized (RVshare, Outdoorsy, Camping World P2P).
RV *parts* never was.

Current state of the art: salvage-yard phone/email intake, eBay storefronts, Facebook groups,
alphabetical directory listings. Competition is weak — which is a signal about difficulty as
much as opportunity. See §5.

---

## 9. Immediate next actions

*Updated 2026-07-30 at 35 observations. The original list is preserved struck-through —
four of five items are done, and the work has moved past what that list anticipated.*

### Done

1. ~~Build the `observations` table.~~ **Done** — `tools/observations.py`, append-only,
   HTML + PDF capture with scan detection, 35 observations live.
2. ~~Hand-pull ~12 Suburban SW-series documents.~~ **Superseded.** The count was set before
   the sources were known. Actual capture spans manufacturer brochures, two service manuals,
   an OEM parts portal, a 2002 archived spec chart, and a direct reply from Suburban support
   — a better spread than twelve retailer pages would have given.
3. ~~Transcribe the three model-number grammar charts.~~ **Done for water heaters**
   (cross-validated, `VENDOR-Suburban.md` §3.2). Furnace and cooktop charts remain
   image-only and low-trust — see `VENDOR-Suburban-Furnace_Cooktop.md`.
4. ~~Hand-write ground-truth records for the five in-hand parts.~~ **Done** —
   `fixtures/ground-truth.yaml`, now also carrying vendor-researched components that anchor
   real edges.

### Also done, since 35 observations

5. ~~Build the SW-series model parser.~~ **Done** — `Docs/Tools/suburban_parser.py`. Decodes
   model strings to structured attributes, resolves substitution edges (install-side-supply-
   aware, not just feature-count), and implements the `full − empty` weight validity rule.
   Self-tested, cross-checked against `ground-truth.yaml` with 0 mismatches.
6. ~~Enforce source-trust ranking.~~ **Done** — `Docs/Tools/resolver.py` adds a
   machine-readable `source_tier` column on `observations`, backfilled for all 35 rows.
7. **Prerequisite for the resolver, found by measuring the input.** 35 observations had
   accumulated 175 distinct `extracted` keys, 132 seen exactly once — the no-schema-on-insert
   design working as intended, but it meant no resolver could be written against raw field
   names yet. `resolver.py` now classifies every key (alias, compound, or explicitly-reviewed
   ignore) and makes the `cutout_*` → `opening_h`/`opening_w` correction (§6.5) mechanical
   instead of re-litigated per record. Unclassified keys raise instead of dropping silently.

### Completed since the last update

8. ~~Design the component/edge schema, then build the observations→components/edges
   resolver itself.~~ **Done 2026-07-31** — `Docs/Tools/interchange_schema.py`,
   `interchange_models.py`, `interchange_store.py`, and `edge_resolver.py` now build the two
   anchor components from observations and persist the canonical directed SW6DE/SW6DEL
   substitution edge pair. The full inline self-test suite passes, and `--check-fixture`
   reports 0 mismatches against the fixture's canonical edge.

### Added since

9. ~~Fill the in-hand measurement gaps.~~ **Done 2026-07-31.** The two parts where geometry
   *is* the identity are both recorded in `Docs/Inital_Design/ground-truth.yaml`.
   **Ceiling register: done 2026-07-31** — `duct_diameter` (~5in) and `flange_diameter`
   (~7in) measured in-hand (obs #36, corrected by obs #39) and matched to D&W International's
   RO-9850 round plastic grille (obs #37/#38); see `Docs/Data/DWIN/VENDOR-DWIN.md`. Identifier
   is CANDIDATE tier — a geometry/feature match against one retailer's spec block, not a
   marking read off the part. **Roof vent:** `opening_size: 14x14 in` was already recorded
   with `in_hand_measured` provenance. Its measurement is complete; only the separate
   teardown capture and hidden molded-identifier classification remain open.
10. **Second vendor adapter.** Suburban is deep enough to prove the pattern. Coleman-Mach /
    Airxcel is next (§ `VENDOR-Suburban.md` §10) and hits multi-namespace identity early via
    the in-hand thermostat.
11. **Resolve the SKU channel-split model.** Suburban confirmed 5148A/5248A are the same unit
    sold to different channels (`VENDOR-Suburban.md` §7.2) — that part is done. Identifiers
    still need a channel qualifier in the schema itself, not just a namespace — that's an
    `ARCHITECTURE-Interchange_Core.md` §3 change, not just a vendor note, and it isn't made yet.

> **Updated 2026-07-31.** The scoped edge resolver is now built and tested: it walks the two
> best-documented anchor observations through the vocabulary into components and the canonical
> directed substitution edge pair. The next adapter is Coleman-Mach / Airxcel. Expanding the
> resolver to the rest of the fixture remains follow-on work.
>
> The §8 definition-of-done in `VENDOR-Suburban.md` now has 8 of 9 boxes checked. The remaining
> partial item is full-fixture reproduction; the scoped SW6DE/SW6DEL resolver milestone is done.
