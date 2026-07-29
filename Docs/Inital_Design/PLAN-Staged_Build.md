# Staged Build Plan

**Project:** RV Interchange
**Status:** design, pre-implementation
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

1. Build the `observations` table. Source-agnostic, append-only. **Before fetching anything.**
2. Hand-pull ~12 Suburban SW-series documents (SW4D through SW16DEL).
3. Transcribe the three model-number grammar charts from
   `suburbanrvparts.com/model-number-breakdown/` — they are images, not text.
4. Hand-write ground-truth records for the five in-hand parts
   (`fixtures/ground-truth.yaml`).
5. *Then* design the component/edge schema — as "what shape holds these records."
   An hour of work that will be right, rather than a week that is theoretical.
