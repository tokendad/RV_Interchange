# Public lookup site — front page redesign (Phase 1) — design

**Date:** 2026-08-07
**Status:** approved, not yet implemented

## Context

The backend "public API enrichment" work (`docs/superpowers/plans/2026-08-06-public-api-enrichment.md`)
shipped 2026-08-06: `/public/v1/search`, `/public/v1/resolve`, and `/public/v1/replacements`
now return manufacturer display name, part-type display name, component attributes, required
parts, and structured caveats. The frontend (`web/`) was updated to consume the new contract
(field renames only — `ReplacementItem.summary` → `caveats`) but its look and structure are
still the bare "search-first lookup flow" page from `docs/superpowers/plans/2026-08-04-stage2-frontend-phase2.md`:
a plain `<h1>`, unstyled form, minimal card list, no header/nav, no footer, no URL sync.

`Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_Public_Lookup_Recommendations.md` is a
prior recommendations document (not written as an approved spec) proposing a full "Phase 1:
Frontend-Only Redesign" — this design adopts its **Recommended First Release Scope** (§19)
in full, confirmed with the user via visual mockups (see "Visual style" below), grounded in
the real API contract rather than the doc's illustrative field names.

This turns `web/index.html` from an internal test/debug tool into the public-facing site
described in that recommendations doc's stated goal: "make RV Interchange feel like a
public-facing product rather than an API test page."

## Goal

Redesign `web/index.html` (+ `app.js`, `style.css`) into a three-state public lookup site —
**Welcome/search → Search results → Part detail** — on the existing plain HTML/CSS/JS stack,
no framework, no build step, no backend changes. `web/admin.html` is unaffected (recommendations
doc §3: admin stays off primary public navigation, reachable only by direct URL).

## A. Visual style (confirmed via mockups)

- Dark navy header (`#0f1b2d`), white/light-gray body background, charcoal/slate body text.
- Amber accent (`#d99a2b`) for primary CTA (search button) and active-nav underline.
- System font stack (no web-font dependency), matching the current `style.css` precedent.
- Page width: `max-width: 72rem` for results/detail views; hero content stays narrower
  (`max-width: 640px`, centered) for readability.
- Moderate border radius (`~10px` on cards), `1px solid #e5e7eb` card borders.
- Compatibility tier colors — **icon + text label inside a pill, color is reinforcement, never
  the only signal** (recommendations doc §7, §15 accessibility requirement):
  - Exact Match: green pill (`background:#dcfce7; color:#166534`), `✓` icon.
  - Direct Fit: amber-yellow pill (`background:#fef9c3; color:#854d0e`), `↔` icon.
  - Fits With Modification: red pill (`background:#fee2e2; color:#991b1b`), `⚠` icon, **plus**
    a heavier `2px solid #fecaca` border on the whole card — confirmed with the user as a
    deliberate deviation from the recommendations doc's suggested amber-only treatment, to
    make this tier unmistakable even in grayscale or for colorblind users.

## B. Page structure — three states, one page, no reloads

### 1. Home (welcome + search)

- Header: dark navy bar, nav links only (**no "RV Interchange" wordmark in the header** —
  confirmed with the user; the wordmark lives in the hero instead). Links: Parts Lookup
  (active/current), Data Coverage, How It Works, Contribute. On narrow screens these collapse
  behind a menu; wordmark is absent so only the search stays pinned.
- Hero: `<h1>RV Interchange</h1>` (confirmed spelling: capital I, lowercase c — "Interchange"),
  supporting text "Search by manufacturer part number, model number, SKU, or known alternate
  number.", search input + amber "Search" button, clickable example chips
  (`SW6DEL`, `7330G335`, `AP7862`, `2608A` — clicking populates and submits automatically).
  No "Evidence-backed..." manufacturer-coverage line under the hero (removed per user feedback
  during mockup review) — manufacturer coverage instead lives in the footer (see F) and the
  "Evidence-Backed Data" info card below.
- Three info cards below the hero (recommendations doc §9, unchanged): "Search Any Known
  Number", "Understand the Fit", "Evidence-Backed Data".
- Empty state below the cards (recommendations doc §10): a short explanation of the three
  compatibility tiers, so the page never looks unfinished before a search.

### 2. Search results

Renders **below the search box on the same page** (confirmed with the user — not a new tab/page).
Calls `GET /public/v1/search?q=<query>&limit=20`, one card per `SearchResultItem`:

- Small-caps label line: `manufacturer — part_type` (e.g. "COLEMAN-MACH · THERMOSTAT"), using
  the API's already-enriched `manufacturer`/`part_type` display strings (no client-side
  namespace-to-label mapping needed — that table in the recommendations doc §5 is now
  redundant with the Phase-2 API work).
- Matched number as the card title, with the matched substring highlighted (`<mark>`).
- "Also known as: <other identifiers>" line (omitted if there are no other identifiers).
- Trailing amber `→` chevron icon.
- Whole card is a focusable, clickable unit (button semantics, not just a `<div onclick>`) —
  keyboard Enter/Space activate it, visible focus ring.
- Query synced to the URL: `/?q=<query>`.

Loading state: "Searching RV Interchange..." replaces the static "Searching..." text; search
button disabled while a request is in flight (recommendations doc §12).

No-result state (recommendations doc §11): "We couldn't find that number yet." + suggestions
(try without spaces/hyphens, try another number on the label, review supported manufacturers,
report a missing part link) instead of the current bare "No matches found" line.

Error state: friendly message ("The lookup service is temporarily unavailable. Please try the
search again.") instead of surfacing raw `HTTP 500`/`error` text directly; the current
technical detail moves into a collapsible `<details>` block rather than being deleted (still
useful for the user to include in a bug report).

### 3. Part detail

Selecting a result card **replaces the results list** with a dedicated detail view (not stacked
below it, not a new browser page) and updates the URL to `/?q=<query>&part=<component identifier
ns>:<value>`. A "← Back to results" link/button returns to the results list without re-querying
the search endpoint (results are already in memory).

Calls `GET /public/v1/replacements?ns=<matched ns>&identifier=<matched value>` (same
matched-identifier selection logic already in `app.js`'s `showDetail`, unchanged).

Layout, top to bottom:

- Back link.
- Manufacturer / part type label line + part number heading + alternate-identifiers line
  (same visual pattern as the result card, just larger).
- "Compatible Replacements" section: one card per `ReplacementItem`, grouped in tier order
  (Exact Match, Direct Fit, Fits With Modification — sections with zero items are omitted
  entirely, not shown empty), each card showing the tier pill (per §A), the replacement
  `part` number, and its `caveats[].text` joined as supporting copy (present today —
  `required_parts` display is **out of scope for this pass**, see "Explicitly out of scope").
- "Discontinued" section (renamed from "Supersession History" — confirmed with the user that
  "supersession" reads as manufacturer jargon; "Discontinued" is the public-facing label).
  Only rendered when the current part has at least one outgoing `supersedes` edge. See §B.1
  below for the full behavior — this isn't a single-hop line, it's a walked chain.
- Copy-link button (copies the current `/?q=...&part=...` URL to the clipboard).

### B.1 "Discontinued" section — full chain walk, not single hop

The existing `/public/v1/replacements` endpoint only returns the **immediate** outgoing
`supersedes` edge(s) for the queried part (`api/services.py:168-178`,
`get_edges_from(conn, component_id, type=EDGE_TYPE_SUPERSEDES)` — one hop, no traversal).
Real data already has a 2-hop case that branches: `7330E336 → 7330F3361 → {9420-352,
9420A382}` (`7330F3361` supersedes to two different current parts — an analog cool-only
thermostat and a digital multi-mode thermostat; confirmed via `edge_resolver.py` docstrings
that these are genuinely different products, not equivalent alternates, and there is no edge
between them). Confirmed with the user: the page should walk the **full chain to every
current endpoint**, not just show one hop, so a user searching the oldest part number in a
chain isn't left thinking `7330F3361` (itself discontinued) is the final answer.

Behavior:

- After the initial `/public/v1/replacements` call, for every part in the returned
  `supersessions` list, recursively call `/public/v1/replacements?ns=<same ns>&identifier=<that
  part>` and keep following `supersessions` until a part has none — that's a "current"
  endpoint. No backend change; this is repeated calls to the existing endpoint. Depth is
  small in practice (deepest known chain today is 2 hops); no explicit depth cap needed for
  this pass, but the walk must terminate on a part already visited in this walk (cycle guard)
  since nothing in the schema prevents one being introduced later.
- Rendered as a vertical chain: `this part → replaced by → next part → ...`, ending in one or
  more boxes tagged "current" (green outline) when a hop branches into multiple parts.
- Every node in the chain — including "this part" — is a link. Clicking any node navigates to
  *that* part's own detail view (re-running the detail flow rooted on the clicked part,
  including its own URL update), not an inline expansion. This reuses the existing detail
  view/URL-sync machinery; no new view type.
- When a hop branches (2+ target parts), each branch endpoint shows up to 2 of its own
  `attributes` (from that part's `resolve` response — one extra `/public/v1/resolve` call per
  branch endpoint during the walk) as a short line under its part number, so the user can tell
  the branches apart (e.g. "Analog · Cool only" vs "Digital · Heat/cool, multi-mode"). This is
  generic attribute rendering — no part-type-specific logic in the frontend, since different
  part types (thermostats, water heaters, fridges) expose different attribute names. A
  single-target hop doesn't show this line — nothing to disambiguate.
- Non-branching intermediate nodes stay compact (part number + "(also discontinued)" only, no
  attribute line) to keep the common case readable.
- A future idea, **not in scope for this pass**: a product photo next to the part
  name/number at the top of the detail view (confirmed placement: beside the heading, not
  below the attributes list, if/when this is picked up).

## C. URL / browser history sync

- `/?q=<query>` — set on search submit (via `history.pushState`, not a full navigation).
- `/?q=<query>&part=<ns>:<value>` — set when a detail view opens.
- Back/Forward browser buttons move between home → results → detail by listening to
  `popstate` and re-deriving the view from the URL (re-running the search/replacements
  fetch as needed — no client-side result cache across a back-navigation, keeping this
  simple rather than building a state store).
- On initial page load, if `q` (and optionally `part`) are present in the URL, the page
  reproduces that state immediately (fires the search, and the detail fetch if `part` is
  also present) instead of starting blank — this is what makes shared/bookmarked links work.

## D. Footer

Compact footer (recommendations doc §17): "RV Interchange", current manufacturer coverage
line ("Currently covering Suburban, Coleman-Mach, Atwood, and Norcold" — this is where that
line moves to, having been removed from the hero), a link to the GitHub repository, a "Report
missing or incorrect data" link, a "Contact" link (stubbed, see below), and the disclaimer
text verbatim from the recommendations doc:

> Compatibility information is provided as a research aid. Verify dimensions, connections,
> electrical requirements, fuel type, and installation instructions before purchasing or
> installing a replacement part.

### D.1 "Coming soon" stub pages

Three links point at content that doesn't exist yet: **Data Coverage** and **How It Works**
(header nav) and **Contact** (footer). Rather than link to nothing (404) or omit the links
(which would make the nav/footer feel incomplete against the recommendations doc's structure),
each gets a minimal static stub page — same header/footer chrome as the main site, a heading
matching the link text, and one line of body copy: "This page is coming soon." No form, no
content, no backend involvement (a plain additional static HTML file per stub, e.g.
`web/coverage.html`, `web/how-it-works.html`, `web/contact.html`). Filling these in with real
content is a follow-up, not part of this pass.

## E. Accessibility & mobile

- Semantic `<header>`, `<nav>`, `<main>`, `<section>` landmarks (current page is a flat
  `<body>` with no structure).
- Explicit `<label for="search-input">` (currently just a `placeholder`, no label).
- Result cards and example chips are real `<button>`s, not `<li onclick>`/`<span onclick>`.
- Visible `:focus-visible` outline on all interactive elements.
- `aria-live="polite"` on the existing `#search-status` element so loading/result-count/error
  text is announced without extra markup changes.
- Minimum 44px touch target height on the search button, example chips, and result cards.
- Mobile: full-width search input, search button below/attached to the input rather than
  squeezed beside it, single-column result cards (already the case, just needs the width
  cap removed at narrow viewports), header nav collapses to a menu, wordmark/search stay
  visible.

## Explicitly out of scope for this pass

- `required_parts` display in the detail view — the API returns it (`ReplacementItem.required_parts`)
  but the recommendations doc doesn't specify a treatment and it wasn't covered in the mockup
  review; defer to a follow-up rather than guessing the presentation.
- Sub-component/attribute searchability (e.g. searching a fridge's `cooling_unit_model`
  attribute value directly) — confirmed with the user as a separate future scope change, not
  part of this redesign. Tracked in memory (`subpart_searchability_idea.md`), not in this spec.
- A dedicated `/part/<ns>/<value>` route (recommendations doc §16 mentions this as a
  longer-term option) — the query-string approach (`?q=...&part=...`) is sufficient for this
  pass and avoids server-side routing changes (the site is served as static files by nginx).
- `web/admin.html` — no changes; stays reachable only by direct URL, no link from public nav.
- Any framework migration — plain HTML/CSS/JS, matching the current stack.
- Backend/API changes of any kind — this redesign consumes the existing `/public/v1/*`
  contract as-is.
- Product photos in the part detail view (confirmed future placement: beside the part
  name/number heading) — not built this pass, no image data exists in the catalog yet.

## Testing

- No JS test framework introduced, consistent with the existing project precedent (phase 2
  frontend work also shipped without one). Verification is manual: exercise the full flow
  against the running Docker stack — search → click a result → view tiered replacements and
  (when present) the Discontinued chain → back to results → browser Back/Forward → reload a
  shared `/?q=...&part=...` URL directly and confirm it reproduces the same view.
- Confirm the Discontinued chain walk specifically: search `7330E336` (Coleman-Mach namespace)
  and verify the chain renders both hops and both branch endpoints (`9420-352`, `9420A382`)
  with their disambiguating attribute lines; click each chain node and confirm it opens that
  part's own detail view with a correctly updated URL.
- Confirm no-result and error states render their new copy (trigger via a nonsense query and
  a temporarily-stopped API container, respectively).
- Confirm keyboard-only navigation: tab through header nav, example chips, search, result
  cards, detail-view controls, and Discontinued chain nodes; confirm Enter/Space activate them.
