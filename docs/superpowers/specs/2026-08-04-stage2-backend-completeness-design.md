# Stage 2 backend completeness — design

**Date:** 2026-08-04
**Status:** approved, not yet implemented

## Context

Stage 2 (the free lookup tool, `PLAN-Staged_Build.md` §2) shipped a first working slice
on 2026-08-03: a Public API (`api/`) with two endpoints (`resolve`, `replacements`) and a
bare, explicitly-not-public test page (`web/`) that requires the caller to already know
the exact namespace and identifier. Four gaps were deliberately deferred at that time
(see `stage2_phase1_status` memory / `docs/superpowers/plans/2026-08-03-stage2-public-api.md`).

This is phase 1 of a three-phase push toward a real public lookup site:

1. **Backend completeness** (this spec)
2. Design and build a more formal frontend page (internal testing/debugging)
3. Publish to the public

Phases 2 and 3 are out of scope here and will each get their own brainstorm/spec when
picked up.

## Goal

Make the backend able to answer "what fits?" for a user who does *not* already know the
exact namespace + identifier, and close the four items already flagged as deferred.

## A. Search endpoint

`GET /public/v1/search?q=<query>&limit=<n, default 20>`

- New store function `search_identifiers(conn, query, limit)` in
  `Docs/Tools/interchange_store.py`. Matches `identifiers.value` case-insensitively,
  ranked exact-match-first then substring match, deduped by `component_id` (a component
  can have several matching identifiers across namespaces — it should appear once).
- No fuzzy matching, no search over `component_attributes`. With 5 v0 part families and
  two vendors' worth of data, plain substring match on identifiers is enough; adding
  fuzzy/ranked text search is explicitly deferred until the empty-result log (Stage 2's
  own demand-signal mechanism, `PLAN-Staged_Build.md` §2) shows it's needed.
- Response groups by component, each result carrying every identifier for that component
  (reuses `get_identifiers_for_component`, already used by `resolve`):

```json
{"query": "SW6", "results": [
  {"component_id": "c_...", "label": "SW6DE", "identifiers": [{"ns":"suburban","value":"SW6DE"}]}
]}
```

- New Pydantic response models in `api/schemas.py` (`SearchResult`, `SearchResponse`),
  new route in `api/main.py` following the existing `resolve`/`replacements` pattern
  (same `Depends(get_conn)`, same 404 semantics don't apply here — empty results is a
  valid 200, not a 404, since "no results" is itself the demand signal Stage 2 wants to
  capture, not an error).

## B. Punch-list fixes

1. **Surface `supersedes` edges.** `ReplacementService.get_replacements` currently only
   walks `type="substitutes"` edges (`api/services.py`). Extend it to also walk
   `type="supersedes"` edges and include them in the response — either as an additional
   tier in the existing `replacements` list or a separate field (implementer's call,
   guided by what reads cleanest against `ReplacementsResponse` in `api/schemas.py`).
   This is the Coleman-Mach dataset's strongest current use case (e.g.
   `7330G3351 → 9420-351`) and is currently unanswerable via the API.

2. **Fix the `_label_for()` namespace bug.** It currently returns
   `identifiers[0].value`, which can echo a value from the wrong namespace for
   multi-namespace components (e.g. querying `ns=icm` could return a `coleman` value as
   the label). Fix: prefer an identifier whose `ns` matches the querying namespace when
   one exists on that component, falling back to the first identifier otherwise. This
   needs the querying `ns` threaded through to `_label_for()` (currently only takes
   `conn, component_id`).

3. **Read-only DB connections.** `get_conn()` in `api/main.py` currently calls
   `init_db()` per request, which runs full DDL plus a write transaction — fine for
   personal use, not for anything public-facing. Switch the request-path connection to a
   `mode=ro` SQLite URI connection. Keep `init_db()` (full DDL) only for the
   `edge_resolver.py --build` CLI path that actually needs to create/migrate the schema.

4. **Small cleanup.**
   - Move the `interchange_store`/`interchange_models` imports in `api/services.py` from
     mid-file to the top (currently split across the file for no functional reason).
   - Add log rotation (`logging.handlers.RotatingFileHandler`) for `api.log` in
     `api/main.py` instead of the current unbounded `FileHandler`.

## Explicitly out of scope for this phase

- `/public/v1/compare` and `/public/v1/interchange/{code}` (from the original API design
  doc) — no data model support for either yet; deferred until there's a real use case.
- Any frontend work (`web/`) — phase 2, separate spec.
- Public deployment changes (open CORS, hosting, rate limiting) — phase 3, separate spec.
- Documenting/testing the current `web/app.js` test page — it's being replaced in phase
  2, so investing in it now is wasted effort.

## Testing

- New tests for `search_identifiers` (store layer): exact match ranked first, substring
  match, dedup across namespaces, empty query/no-match behavior.
- New tests for the `/public/v1/search` route (API layer): 200 with results, 200 with
  empty results list (not 404).
- Existing `ReplacementService`/`_label_for` tests updated to cover the namespace-label
  fix and the new `supersedes` tier.
- Existing full test suite (`tests/`) must continue to pass.
