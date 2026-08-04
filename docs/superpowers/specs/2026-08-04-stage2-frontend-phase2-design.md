# Stage 2 frontend, phase 2 — formal internal test/debug page — design

**Date:** 2026-08-04
**Status:** approved, not yet implemented

## Context

Stage 2 (the free lookup tool) shipped a first backend slice on 2026-08-03, and phase 1
(backend completeness — search endpoint, supersedes-edge surfacing, namespace-label fix,
read-only DB connections, log rotation) shipped 2026-08-04. The frontend (`web/`) is still
the bare test tool from the original ship: a namespace dropdown + identifier text field,
raw JSON dump, explicitly labeled "not public" (`web/index.html`'s `<h1>`).

This is phase 2 of the three-phase push toward a real public lookup site:

1. Backend completeness (done, `docs/superpowers/plans/2026-08-04-stage2-backend-completeness.md`)
2. **Design and build a more formal frontend page (internal testing/debugging)** (this spec)
3. Publish to the public

Phase 3 is out of scope here and will get its own brainstorm/spec when picked up.

## Goal

Replace the bare test form with two purpose-built internal pages:
- A **main lookup page** that exercises the real search-first user flow the public site
  will eventually offer, so it can be used to rehearse and sanity-check that flow.
- An **admin/debug page** that keeps direct raw-request access to all three endpoints
  (for verifying API behavior and data quality) and adds visibility into recent request
  activity via the API's log file.

No authentication — this remains a locally/LAN-hosted internal tool, same trust model as
today. No new backend business logic beyond one small debug endpoint; all real logic
(search ranking, replacement tiering, supersession surfacing) already exists from phase 1.

## A. File structure

Two static HTML pages, served by the existing `web/` nginx container (no new container,
no build step, no framework — matches the current plain-static setup):

- `web/index.html` + `web/app.js` — rewritten: the main lookup flow (replaces the current
  namespace-dropdown form).
- `web/admin.html` + `web/admin.js` — new: raw-request panel + log-tail panel.
- `web/api-client.js` — new: a small shared helper both pages import via `<script>` tag —
  base-URL resolution (mirrors the existing `API_BASE` computation in `app.js`) and a thin
  `fetch` wrapper that returns `{ ok, status, body, elapsedMs }` so both pages can render
  status/timing consistently without duplicating that logic.
- `web/style.css` — new: shared stylesheet for both pages (plain CSS, no framework).

`web/Dockerfile` gets two more `COPY` lines for the new files; no other Docker/compose
changes (same port, same nginx image, same CORS rules already cover this origin).

## B. Main page (`web/index.html` / `app.js`)

**Search-first flow**, calling the phase-1 endpoints in this order:

1. A single search input ("Enter a part number, model, or SKU") + a "Search" button (and
   Enter-to-submit). Calls `GET /public/v1/search?q=<query>&limit=20`.
2. Results render as a list of cards, one per `SearchResultItem`: the `label`, and every
   identifier in `identifiers` grouped/tagged by `ns` (e.g. a small pill per identifier:
   `suburban: SW6DE`, `icm: PCB1060`).
3. Each result card is clickable. Clicking it calls
   `GET /public/v1/replacements?ns=<that identifier's ns>&identifier=<that identifier's value>`
   (using the specific identifier that matched the search, not an arbitrary one off the
   component — reuse the `ns`/`value` pair the card already has) and renders a detail
   view below/in-place:
   - `replacements` tiers as cards, grouped/labeled by `fit` (`Exact Match`, `Direct Fit`,
     `Fits With Modification`), each showing `part` and `summary` (caveat text) if present.
   - A visually distinct "Superseded by" section listing `supersessions` entries
     (`part` + `note`) **only when the array is non-empty** — no empty-state clutter when
     a component has no supersession edges (the common case today).
4. **Empty search results** (valid `200` with `results: []`) render a plain, non-error
   "No matches found for '<query>'" message — this is an expected outcome (Stage 2's own
   demand-signal mechanism per `PLAN-Staged_Build.md` §2), not styled as a failure.
5. **Actual errors** (non-2xx, network failure) keep the existing `.error` styling pattern
   from the current `app.js`.

Styling: real layout (flexbox for the search bar, a card grid/list for results), readable
type scale, clear visual hierarchy between "you searched for X" / "matches" / "replacement
detail" — "clean and functional," no branding investment (that's phase 3).

## C. Admin page (`web/admin.html` / `admin.js`)

Two independent panels on one page, no shared state between them.

**Raw request panel** — three small forms, one per endpoint, each showing the full raw
JSON response, HTTP status code, and elapsed time (via `api-client.js`'s wrapper):
- Search: `q`, `limit` inputs → `GET /public/v1/search`
- Resolve: `ns`, `identifier` inputs → `GET /public/v1/resolve`
- Replacements: `ns`, `identifier` inputs → `GET /public/v1/replacements`

This directly replaces today's bare test tool rather than discarding it — same
"paste in exact values, see raw JSON" utility, just relocated off the main page.

**Log tail panel** — fetches `GET /debug/v1/logs?lines=100` (default 100, no UI control to
change it in this first pass — YAGNI) and renders the returned lines in a scrollable
monospace `<pre>` block. A manual "Refresh" button re-fetches; no auto-polling, no
WebSocket — keep it simple, this is a debug convenience, not a live dashboard.

## D. Backend addition: log-tail endpoint

`GET /debug/v1/logs?lines=100` in `api/main.py`.

Deliberately **not** under `/public/v1/*` — it's an ops/debug concern, not part of the
public-facing API surface (`RV_Interchange_API_Design.md` §10's "hidden from public
users" principle extends naturally to server logs, even though this project has no
Dealer-API auth layer yet to formally gate it behind).

- Reads the tail of the same `api.log` file `RotatingFileHandler` (phase 1) already
  writes, from `LOG_DIR / "api.log"`.
- `lines` query param, default `100`, reasonable bound (e.g. `Query(100, ge=1, le=1000)`
  matching the phase-1 precedent set for `/public/v1/search`'s `limit` param).
- Response shape: `{"lines": ["<log line 1>", "<log line 2>", ...]}` — a plain list of
  the last N lines, oldest first within that window.
- If the log file doesn't exist yet (fresh container, no requests logged), return
  `{"lines": []}` with `200`, not a `404` — an empty log is a valid state, not an error.
- No new response schema class needed beyond a simple dict return (this endpoint is
  intentionally outside the `api/schemas.py` Public API contract described in that
  file's module docstring).

## E. Network access

No changes needed. The existing CORS configuration in `api/main.py` already allows:
- `http://localhost:8485` / `http://127.0.0.1:8485` (exact)
- Any `http://192.168.x.x:8485` or `http://10.x.x.x:8485` origin (regex)

Both new pages are served from the same nginx container on the same port 8485 as today,
so they ride on this existing rule without modification. The new `/debug/v1/logs`
endpoint is on the same FastAPI app (`api/main.py`) as the existing endpoints, so it's
automatically covered by the same CORS middleware — no separate configuration required.

## Explicitly out of scope for this phase

- Authentication/authorization on the admin page or the debug-logs endpoint (no trust
  boundary needed yet — this remains a personal/LAN-only tool).
- `/public/v1/compare`, `/public/v1/interchange/{code}` (still not built, per phase 1's
  scope boundary).
- Any branding, color system, or responsive/mobile-specific design work (phase 3).
- Auto-refreshing/live-updating log tail (manual refresh only).
- A build step, bundler, or JS framework — plain HTML/CSS/JS, matching the existing
  static-nginx deployment.
- Public deployment changes (open CORS beyond LAN, hosting, rate limiting) — phase 3.

## Testing

- Backend: pytest coverage for `/debug/v1/logs` — default line count, custom `lines`
  param, out-of-range `lines` rejected (422, matching the `/public/v1/search` precedent),
  missing-log-file returns `{"lines": []}` with 200.
- Frontend: no test framework introduced, consistent with the existing project (plain
  static JS, no build tooling, no existing frontend tests to extend). Verification is
  manual: exercise both pages against the running Docker stack — search → click a result
  → see replacements and (when present) supersessions on the main page; all three raw
  forms plus the log-tail refresh on the admin page — before considering the phase done.
