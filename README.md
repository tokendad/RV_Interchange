# RV Parts Interchange — Design Set

Captured 2026-07-29 from a design session. Pre-implementation. No code written yet.

| Document | What's in it |
|---|---|
| `ARCHITECTURE-Interchange_Core.md` | The schema. Three-layer identity, namespaced identifiers, edge vocabulary, compat modes, part-type taxonomy, confidence model, tiered search, persistence. |
| `PLAN-Staged_Build.md` | Four-stage build order, v0 scope and bet, roles architecture, the retention problem, legal position, next actions. |
| `VENDOR-Suburban.md` | First vendor adapter research. Model grammar, captured specs, first real interchange edge, four data-quality findings, definition of done. |
| `fixtures/ground-truth.yaml` | Hand-written expected records for the five in-hand parts. Write this before the schema. |

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
