# RV Interchange — Design Set

**Project name:** RV Interchange (retired name: "rvpartsmarketplace" — see naming note
below).

Started 2026-07-29 from a design session, with two external design reviews incorporated
the same day. **Stage 1 implementation is now in progress:** the append-only evidence
store, canonical observation vocabulary, Suburban model parser, SQLite component/edge
store, and the first observation-derived interchange edge are implemented and tested.

| Document | What's in it |
|---|---|
| `Docs/Inital_Design/ARCHITECTURE-Interchange_Core.md` | The schema. Three-layer identity, namespaced identifiers, edge vocabulary, compat modes, part-type taxonomy, confidence model, tiered search, persistence, number stability rules. |
| `Docs/Inital_Design/PLAN-Staged_Build.md` | Four-stage build order, v0 scope and bet, roles architecture, the retention problem, legal position, next actions. |
| `Docs/Data/Suburban/VENDOR-Suburban.md` | First vendor adapter research. Model grammar, captured specs, first real interchange edge, data-quality findings, definition of done. |
| `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md` | Second adapter research. In-hand thermostat identity, terminal map, manufacturer compatibility evidence, and candidate crosswalk boundaries. |
| `Docs/Inital_Design/ground-truth.yaml` | Hand-written expected records for the in-hand parts and the acceptance fixture for the resolver. |

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

## Current Stage 1 status

- `Docs/Tools/observations.db` contains 47 append-only evidence observations.
- `Docs/Tools/resolver.py` classifies every captured field into a canonical vocabulary
  and assigns source-trust tiers.
- `Docs/Tools/suburban_parser.py` decodes SW-series models and resolves their directional
  compatibility constraints.
- `Docs/Tools/interchange_*.py` and `edge_resolver.py` persist components, typed edges,
  caveats, required parts, and evidence. The canonical SW6DE/SW6DEL fixture case resolves
  with zero mismatches.
- The Coleman-Mach thermostat resolver now persists the in-hand `AP7862` / `7330G335`
  identity, its queryable `R/Y/W/GL/GH/B` interface, and the separate open
  `AR7815` / `7330F3858` identifier-equivalence candidate.

The next Coleman milestone is resolving the exact endpoint components named by the
compatibility and supersession evidence before creating those edges. The wider Stage 1 roadmap is in
`Docs/Inital_Design/PLAN-Staged_Build.md`.

## Known corrections logged

- **`L` in SW6DEL means 12-volt relay, not "longer."** SW6DE and SW6DEL share an identical
  cutout. An earlier assumption to the contrary was wrong. See `VENDOR-Suburban.md` §3.
