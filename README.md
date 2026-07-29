# RV Interchange — Design Set

**Project name:** RV Interchange (retired name: "rvpartsmarketplace" — see naming note
below).

Captured 2026-07-29 from a design session, plus two external design reviews incorporated
the same day. Pre-implementation. No code written yet.

| Document | What's in it |
|---|---|
| `ARCHITECTURE-Interchange_Core.md` | The schema. Three-layer identity, namespaced identifiers, edge vocabulary, compat modes, part-type taxonomy, confidence model, tiered search, persistence, number stability rules. |
| `PLAN-Staged_Build.md` | Four-stage build order, v0 scope and bet, roles architecture, the retention problem, legal position, next actions. |
| `VENDOR-Suburban.md` | First vendor adapter research. Model grammar, captured specs, first real interchange edge, four data-quality findings, definition of done. |
| `fixtures/ground-truth.yaml` | Hand-written expected records for the five in-hand parts. Write this before the schema. |

## Naming

The project is **RV Interchange**. The database — component identity, aliases,
attributes, directional substitution edges, evidence — is the product and the moat.

A marketplace (listings, transactions, dealer leads) may be built later as a **separate,
standalone project** that references RV Interchange as its data layer. It is not part of
this project's scope, and the original working name ("rvpartsmarketplace") is retired
because it implied otherwise.

## External design reviews (incorporated 2026-07-29)

Two design reviews were submitted for comparison against the working design and merged in:

- **Design Review #002 (numbering system):** confirmed the existing three-layer identity
  and number format. Three additions adopted: group merges preserve redirects, variant
  letters are never recycled, and numbers have a candidate/published distinction (internal
  clusters churn freely; published numbers are stable). One conflict resolved: interchange
  numbers are hidden from general consumers by default, and shown as an opt-in secondary
  line for dealer/salvage-yard accounts.
- **Design Review #003 (knowledge graph framing):** confirmed the system is already
  graph-shaped (typed nodes and directed, evidence-backed edges) and recommended naming it
  as such, without adopting a dedicated graph database — Postgres with explicit edge tables
  is sufficient for now. The confidence-scoring example in that review (flat percentage per
  candidate) was **not** adopted; the Beta(α, β) confidence/certainty model in
  `ARCHITECTURE-Interchange_Core.md` §7 remains authoritative.

## The one-paragraph version

The defensible asset is a cross-brand fitment/interchange database, not a marketplace.
Index components, not coaches. Identity is three layers changing at three rates: an opaque
immutable `component_id`, attributes carrying per-attribute provenance, and a re-clusterable
`interchange_code` that points at an equivalence class rather than containing one. Confidence
accumulates from field evidence over an attribute-derived prior, climbing slowly and falling
hard. Build the interchange core first with no users, ship a free lookup tool that works with
zero supply, and only then add listings.

## Where to start

1. `observations` table — append-only, source-agnostic. Before fetching anything.
2. Transcribe the three grammar charts (they're images) at
   `suburbanrvparts.com/model-number-breakdown/`.
3. Fill in the `TODO` measurements in `fixtures/ground-truth.yaml`.
4. Then design the component/edge schema as "what shape holds these records."

## Known corrections logged

- **`L` in SW6DEL means 12-volt relay, not "longer."** SW6DE and SW6DEL share an identical
  cutout. An earlier assumption to the contrary was wrong. See `VENDOR-Suburban.md` §3.
