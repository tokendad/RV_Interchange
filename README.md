# RV Interchange — Design Set

**Project name:** RV Interchange (retired name: "rvpartsmarketplace" — see naming note
below).

Started 2026-07-29 from a design session, with two external design reviews incorporated
the same day. **Stage 1 (the interchange database) and the first phase of Stage 2 (a
public read API and a browsable test website) are both implemented and tested.** Three
vendor arcs are built — Suburban, Coleman-Mach, and Atwood — behind a shared edge-type
registry and a single reproducible rebuild command.

| Document | What's in it |
|---|---|
| `Docs/Inital_Design/ARCHITECTURE-Interchange_Core.md` | The schema. Three-layer identity, namespaced identifiers, edge vocabulary, compat modes, part-type taxonomy, confidence model, tiered search, persistence, number stability rules. |
| `Docs/Inital_Design/PLAN-Staged_Build.md` | Four-stage build order, v0 scope and bet, roles architecture, the retention problem, legal position, next actions. |
| `Docs/Data/Suburban/VENDOR-Suburban.md` | First vendor adapter research. Model grammar, captured specs, first real interchange edge, data-quality findings, definition of done. |
| `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md` | Second adapter research. In-hand thermostat identity, terminal map, manufacturer compatibility evidence, endpoint/supersession components, and candidate crosswalk boundaries. |
| `Docs/Data/Atwood/VENDOR-Atwood.md` | Third adapter research. 19 exact endpoint water heater components plus a Pilot/Electronic Ignition repair-parts cross-reference (87 repair-part components, 367 `fits` edges). |
| `Docs/Inital_Design/ground-truth.yaml` | Hand-written expected records for the in-hand parts and the acceptance fixture for the resolver. |
| `docs/superpowers/plans/2026-08-03-stage2-public-api.md` | Stage 2 Phase 1 plan: public API design and Docker deployment. |
| `docs/superpowers/plans/2026-08-04-stage2-frontend-phase2.md` | Stage 2 Phase 2 plan: search-first frontend and admin/debug page. |

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

- `Docs/Tools/observations.db` contains the append-only evidence log backing every
  built component and edge, growing with each vendor arc.
- `Docs/Tools/resolver.py` classifies every captured field into a canonical vocabulary
  and assigns source-trust tiers.
- `Docs/Tools/suburban_parser.py` decodes SW-series models and resolves their directional
  compatibility constraints.
- `Docs/Tools/edge_types.py` is the canonical edge-type registry (`substitutes`,
  `supersedes`, `controls`, `fits`) — resolver functions, serializers, and API queries
  reference this shared vocabulary instead of ad hoc string literals.
- `Docs/Tools/interchange_*.py` and `edge_resolver.py` persist components, typed edges,
  caveats, required parts, and evidence. The current build produces 200 components and
  584 edges (563 `fits`, 12 `supersedes`, 8 `substitutes`, 1 `controls`) with zero
  mismatches against `ground-truth.yaml`.
- **Suburban** (first vendor arc): the canonical SW6DE/SW6DEL directional-replacement
  fixture case resolves with zero mismatches. Also carries two exact endpoint components
  from the owner's current coach — the `SF-30FQ` furnace (with a `fits` edge to its
  `2608A` core module) and the `SRNA3SBBM` cooktop/range, both with manual-sourced
  clearance and cutout dimensions. See `VENDOR-Suburban.md`.
- **Coleman-Mach** (second vendor arc): the in-hand `AP7862` / `7330G335` thermostat
  identity and its queryable `R/Y/W/GL/GH/B` interface, the open `AR7815` / `7330F3858`
  identifier-equivalence candidate, the `7330G3351`/`7330F3852` → `9420-351` and
  `7330F3361` → `9420-352`/`9420A382` supersession chains, and the third-wave
  `7330E335`/`E385`/`E336` endpoint components are all persisted, plus a rooftop AC head
  (`48253B866`, 28 repair parts) and its ceiling plenum (`8330A733`, 8 repair parts) as
  separate part types within the arc. See `VENDOR-Coleman-Mach.md`.
- **Atwood** (third vendor arc): 19 exact endpoint water heater components plus a
  Pilot + Electronic Ignition repair-parts cross-reference (87 repair-part components,
  367 `fits` edges), all 19 endpoints carrying `opening_h`/`opening_w` cutout
  dimensions. See `VENDOR-Atwood.md`.

The wider Stage 1 roadmap is in `Docs/Inital_Design/PLAN-Staged_Build.md`. Vendor
expansion (a 4th Stage 1 vendor) is intentionally paused pending a stabilization
checkpoint — see "Stabilization" below.

## Canonical rebuild command

From the repo root, run:

```bash
python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db
```

This is the one documented command a fresh checkout needs to get a working local stack. It
builds into a temporary database, runs the fixture validation (`--check-fixture` equivalent)
against every vendor arc, and only swaps the published `Docs/Tools/components.db` into place
after validation passes — a partially-built or invalid database is never left in place. The
file remains gitignored. Until it's built, the API below returns a clean 404 for every
identifier — that's expected behavior, not a bug.

## Running the Public API (Stage 2, Phase 1)

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload
```

Endpoints:

- `GET /health/` — container/proxy health check; returns `{"status":"ok"}`.
- `GET /public/v1/resolve?ns=<ns>&identifier=<id>` — resolve an identifier to its component.
- `GET /public/v1/replacements?ns=<ns>&identifier=<id>` — directional substitution/supersession
  results.
- `GET /public/v1/search?q=<text>&limit=<n>` — free-text identifier search.
- `GET /debug/v1/logs?lines=<n>` — tail the API request log (admin/debug use).

```bash
curl "http://127.0.0.1:8000/public/v1/replacements?ns=suburban&identifier=SW6DE"
```

See `docs/superpowers/plans/2026-08-03-stage2-public-api.md` for the Phase 1 scope and
`docs/superpowers/plans/2026-08-04-stage2-frontend-phase2.md` for the Phase 2
(search-first frontend + admin/debug page) plan.

## Public site and local hosting

The public lookup site is available at <https://rvinterchange.com>. The operational
review interface is available at <https://review.rvinterchange.com> and requires
Cloudflare Access authentication.

The repository-owned Compose project runs the API, public web frontend, protected review
frontend, and Cloudflare Tunnel connector. Start or update the complete stack with:

```bash
docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml --profile tunnel up -d --build
```

Loopback diagnostics are available at `http://127.0.0.1:8485` for the public frontend and
`http://127.0.0.1:8486` for the review frontend. The API has no host port. Browser callers
use same-origin API requests through Nginx; the FastAPI service does not enable CORS.

`Docs/Tools/components.db` is mounted read-only into the API container. Rebuild it with the
canonical command documented above before starting a fresh checkout. See
[`docs/operations/rvinterchange-local-hosting.md`](docs/operations/rvinterchange-local-hosting.md)
for deployment, verification, and rollback procedures.

## Tests

```bash
python3 -m pytest tests/ Docs/Tools
```

42 tests pass as of this writing: resolver/vendor-discovery unit tests, the edge-type
registry tests (`tests/tools/test_edge_types.py`), and end-to-end API tests that build a
temporary persisted database and exercise the public API layer directly
(`tests/api/test_e2e.py`) — covering the SW6DEL/SW6DE directional case, a Coleman-Mach
thermostat supersession chain, an Atwood repair part with multiple `fits` edges, and an
unresolved identifier-equivalence candidate. These complement the resolver-level fixture
checks above, which don't exercise the built database through the actual API layer.

## Stabilization

Suburban, Coleman-Mach, Atwood, the repair-parts/`fits` edge type, the public API, the
test website, vendor discovery tooling, and debug tooling all advanced quickly through
early August 2026. Before opening a 4th Stage 1 vendor arc, the existing three arcs were
hardened first: the canonical rebuild command above, this documentation pass, the
persisted-database e2e tests, and the edge-type registry. With that stabilization set
complete, vendor expansion can resume deliberately rather than by default.

## Known corrections logged

- **`L` in SW6DEL means 12-volt relay, not "longer."** SW6DE and SW6DEL share an identical
  cutout. An earlier assumption to the contrary was wrong. See `VENDOR-Suburban.md` §3.
