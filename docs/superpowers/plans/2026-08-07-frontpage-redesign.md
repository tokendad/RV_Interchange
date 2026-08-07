# Front page redesign (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `web/index.html` from a bare test/debug page into a three-state public lookup
site — Welcome/search → Search results → Part detail — per
`docs/superpowers/specs/2026-08-07-frontpage-redesign-design.md`, on the existing plain
HTML/CSS/JS stack, no framework, no build step, no backend changes.

**Architecture:** Plain `<script>` tags define global functions (matching the existing
`api-client.js` → `app.js` pattern, no ES modules/bundler). New focused files per
responsibility: `chrome.js` (shared header/footer, reused by 4 HTML pages), `url-state.js`
(pure URL parse/build helpers), `results.js` (search results + loading/no-result/error
states), `detail.js` (part detail view + tier pills), `discontinued.js` (the walked/branching
supersession chain — the one genuinely new piece of client-side logic). `app.js` becomes the
orchestrator: wires the form, switches between the three views inside a single `#content`
region below the persistent hero/search, and keeps the URL in sync via `history.pushState`/
`popstate`. All data comes from the existing `/public/v1/search`, `/public/v1/resolve`, and
`/public/v1/replacements` endpoints — no schema or endpoint changes.

**Tech Stack:** Plain HTML/CSS/JS (no framework, no build step), served by the existing
`web/Dockerfile` nginx image via `/data/DockerConfigs/docker-compose.yaml` (`rvinterchange-web`
+ `rvinterchange-api`, ports 8485/8484).

## Global Constraints

- No JS test framework introduced (spec "Testing" section) — verification is manual, mostly
  via directly opening files in a browser and, for the full data-driven flow, the running
  Docker stack. Every task still ends with a concrete, described verification step — "manual"
  does not mean "unspecified."
- No backend/API changes of any kind — consume `/public/v1/*` exactly as it exists today
  (`api/schemas.py`: `SearchResponse`, `ResolveResponse`, `ReplacementsResponse`).
- No framework, no bundler, no `type="module"` — plain global-scope `<script>` files, loaded
  in dependency order via `<script src="...">` tags, matching the existing `api-client.js`
  precedent.
- Never build HTML via string concatenation with unescaped/user-controlled data (search query,
  part numbers) — use `document.createElement`/`textContent`/`createTextNode` throughout, never
  `innerHTML` with interpolated untrusted values. `innerHTML = ''` (clearing) and
  `innerHTML = <our own static authored markup>` (e.g. restoring the home view's own template)
  are fine; interpolating `query`, part numbers, or API string fields into an HTML string is not.
- `web/admin.html` / `web/admin.js` are out of scope — no changes, no shared markup with the
  public pages beyond the existing `style.css` base rules (body/h1/h2/form/label/input/button/
  `.admin-panel`/`.raw-form`/`pre`/`.error`), which must keep working unmodified.
- Repository is `tokendad/RV_Interchange` (per the recommendations doc header) — use this for
  the GitHub/issue links added to the footer and no-results state.
- Visual system from the spec §A: navy header `#0f1b2d`, amber accent `#d99a2b`, tier colors
  green `#dcfce7`/`#166534`, amber-yellow `#fef9c3`/`#854d0e`, red `#fee2e2`/`#991b1b` with a
  `2px solid #fecaca` card border on the Fits-With-Modification tier. Every tier pill carries
  an icon + text label — color is never the only signal.

---

## File structure

```
web/
  index.html          MODIFY — rewritten skeleton (header/footer slots, hero, #content)
  app.js              MODIFY — rewritten orchestrator (view switching, URL sync, wiring)
  style.css           MODIFY — rewritten/extended (base restyle + per-feature rule blocks)
  api-client.js        (unchanged — already generic rviFetch() wrapper)
  admin.html           (unchanged)
  admin.js             (unchanged)
  Dockerfile          MODIFY — new COPY lines for every new file below
  chrome.js            NEW — renderHeader(activeId), renderFooter()
  url-state.js         NEW — parseUrlState(), buildQueryString(), pushUrlState()
  results.js           NEW — renderResultsView(), renderNoResultsState(), renderErrorState(),
                              highlightMatch()
  detail.js            NEW — renderDetailView(), renderReplacementCard()
  discontinued.js      NEW — walkSupersessionChain(), renderDiscontinuedSection(),
                              renderChainNode(), formatAttribute()
  coverage.html         NEW — "Data Coverage" stub page
  how-it-works.html     NEW — "How It Works" stub page
  contact.html          NEW — "Contact" stub page
```

---

### Task 1: Shared page chrome, base restyle, and the three stub pages

**Files:**
- Create: `web/chrome.js`
- Create: `web/coverage.html`
- Create: `web/how-it-works.html`
- Create: `web/contact.html`
- Modify: `web/style.css` (replace entirely — old rules target markup this redesign replaces;
  `.admin-panel`/`.raw-form`/`pre`/`.error`/base element rules are preserved verbatim since
  `admin.html` depends on them)
- Modify: `web/Dockerfile` (add `COPY` lines for the 4 new files)

**Interfaces:**
- Produces: `renderHeader(activeId)` → `HTMLElement` (`<header>`), `activeId` is one of
  `'lookup'`, `'coverage'`, `'how-it-works'`, or `undefined`/any other value (no link marked
  active — used by `contact.html`). `renderFooter()` → `HTMLElement` (`<footer>`), no
  arguments.
- Consumes: nothing (first task, no dependencies on other new files).

- [ ] **Step 1: Write `web/chrome.js`**

```javascript
const NAV_LINKS = [
  { id: "lookup", label: "Parts Lookup", href: "/" },
  { id: "coverage", label: "Data Coverage", href: "/coverage.html" },
  { id: "how-it-works", label: "How It Works", href: "/how-it-works.html" },
  { id: "contribute", label: "Contribute", href: "https://github.com/tokendad/RV_Interchange" },
];

function renderHeader(activeId) {
  const header = document.createElement("header");
  header.className = "site-header";

  const nav = document.createElement("nav");
  nav.className = "site-nav";
  nav.setAttribute("aria-label", "Primary");

  for (const link of NAV_LINKS) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.label;
    a.className = link.id === activeId ? "nav-link nav-link-active" : "nav-link";
    nav.appendChild(a);
  }

  header.appendChild(nav);
  return header;
}

function renderFooter() {
  const footer = document.createElement("footer");
  footer.className = "site-footer";

  const brand = document.createElement("div");
  brand.className = "footer-brand";
  brand.textContent = "RV Interchange";
  footer.appendChild(brand);

  const coverage = document.createElement("div");
  coverage.className = "footer-coverage";
  coverage.textContent = "Currently covering Suburban, Coleman-Mach, Atwood, and Norcold";
  footer.appendChild(coverage);

  const links = document.createElement("div");
  links.className = "footer-links";

  const githubLink = document.createElement("a");
  githubLink.href = "https://github.com/tokendad/RV_Interchange";
  githubLink.textContent = "GitHub";
  links.appendChild(githubLink);

  const reportLink = document.createElement("a");
  reportLink.href = "https://github.com/tokendad/RV_Interchange/issues/new";
  reportLink.textContent = "Report missing or incorrect data";
  links.appendChild(reportLink);

  const contactLink = document.createElement("a");
  contactLink.href = "/contact.html";
  contactLink.textContent = "Contact";
  links.appendChild(contactLink);

  footer.appendChild(links);

  const disclaimer = document.createElement("p");
  disclaimer.className = "footer-disclaimer";
  disclaimer.textContent =
    "Compatibility information is provided as a research aid. Verify dimensions, " +
    "connections, electrical requirements, fuel type, and installation instructions " +
    "before purchasing or installing a replacement part.";
  footer.appendChild(disclaimer);

  return footer;
}
```

- [ ] **Step 2: Write the three stub pages**

`web/coverage.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Data Coverage</title>
  <link rel="stylesheet" href="style.css">
</head>
<body class="public-page">
  <div id="header-slot"></div>
  <main class="stub-page">
    <h1>Data Coverage</h1>
    <p>This page is coming soon.</p>
  </main>
  <div id="footer-slot"></div>
  <script src="chrome.js"></script>
  <script>
    document.getElementById("header-slot").replaceWith(renderHeader("coverage"));
    document.getElementById("footer-slot").replaceWith(renderFooter());
  </script>
</body>
</html>
```

`web/how-it-works.html` (identical structure, `activeId` `"how-it-works"`):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — How It Works</title>
  <link rel="stylesheet" href="style.css">
</head>
<body class="public-page">
  <div id="header-slot"></div>
  <main class="stub-page">
    <h1>How It Works</h1>
    <p>This page is coming soon.</p>
  </main>
  <div id="footer-slot"></div>
  <script src="chrome.js"></script>
  <script>
    document.getElementById("header-slot").replaceWith(renderHeader("how-it-works"));
    document.getElementById("footer-slot").replaceWith(renderFooter());
  </script>
</body>
</html>
```

`web/contact.html` (no nav link is "active" — Contact is footer-only):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Contact</title>
  <link rel="stylesheet" href="style.css">
</head>
<body class="public-page">
  <div id="header-slot"></div>
  <main class="stub-page">
    <h1>Contact</h1>
    <p>This page is coming soon.</p>
  </main>
  <div id="footer-slot"></div>
  <script src="chrome.js"></script>
  <script>
    document.getElementById("header-slot").replaceWith(renderHeader());
    document.getElementById("footer-slot").replaceWith(renderFooter());
  </script>
</body>
</html>
```

- [ ] **Step 3: Replace `web/style.css`**

Preserve every existing base/admin rule verbatim, replace everything below the `.error` rule
(the old `.result-card`/`.tier-section`/etc. rules target markup this redesign removes) with
the new base + chrome styling. Full new file contents:

```css
* {
  box-sizing: border-box;
}

body {
  font-family: system-ui, sans-serif;
  max-width: 48rem;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
}

h1 {
  margin-bottom: 1.5rem;
}

h2, h3 {
  margin-top: 1.5rem;
}

form {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  font-weight: bold;
  gap: 0.25rem;
}

input {
  font-size: 1rem;
  padding: 0.4rem;
}

button {
  font-size: 1rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
}

.admin-panel {
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.raw-form {
  margin-bottom: 0.75rem;
}

pre {
  background: #f2f2f2;
  padding: 1rem;
  overflow-x: auto;
  white-space: pre-wrap;
  border-radius: 0.35rem;
  max-height: 24rem;
  overflow-y: auto;
}

.error {
  color: #b00020;
  font-weight: bold;
}

/* ---- Public pages (index.html, coverage/how-it-works/contact.html) ---- */

body.public-page {
  max-width: none;
  margin: 0;
  padding: 0;
  color: #1f2937;
  background: #f4f5f7;
}

:focus-visible {
  outline: 2px solid #d99a2b;
  outline-offset: 2px;
}

.site-shell {
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.site-header {
  background: #0f1b2d;
  padding: 0.9rem 1.5rem;
}

.site-nav {
  max-width: 72rem;
  margin: 0 auto;
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.nav-link {
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.9rem;
  padding-bottom: 2px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

.nav-link-active {
  color: #fff;
  border-bottom: 2px solid #d99a2b;
}

.site-footer {
  max-width: 72rem;
  margin: 2.5rem auto 0;
  padding: 1.5rem;
  font-size: 0.85rem;
  color: #6b7280;
  border-top: 1px solid #e5e7eb;
}

.footer-brand {
  font-weight: 700;
  color: #111827;
}

.footer-links {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 0.5rem 0;
}

.footer-links a {
  color: #0f1b2d;
}

.footer-disclaimer {
  margin-top: 0.75rem;
  max-width: 48rem;
}

.stub-page {
  max-width: 72rem;
  margin: 0 auto;
  padding: 3rem 1.5rem;
}
```

- [ ] **Step 4: Add the new files to `web/Dockerfile`**

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
COPY chrome.js /usr/share/nginx/html/chrome.js
COPY coverage.html /usr/share/nginx/html/coverage.html
COPY how-it-works.html /usr/share/nginx/html/how-it-works.html
COPY contact.html /usr/share/nginx/html/contact.html
COPY admin.html /usr/share/nginx/html/admin.html
COPY admin.js /usr/share/nginx/html/admin.js
COPY api-client.js /usr/share/nginx/html/api-client.js
COPY style.css /usr/share/nginx/html/style.css
EXPOSE 80
```

- [ ] **Step 5: Manually verify**

Open `web/coverage.html` directly in a browser (`file://` path is fine — this page has no API
dependency). Confirm: dark navy header renders with 4 nav links, "Data Coverage" is
underlined/amber (active), page shows "Data Coverage" heading + "This page is coming soon.",
footer renders with brand/coverage line/3 links/disclaimer. Repeat for `how-it-works.html`
(confirm "How It Works" is the active link) and `contact.html` (confirm **no** nav link is
underlined/amber).

- [ ] **Step 6: Commit**

```bash
git add web/chrome.js web/coverage.html web/how-it-works.html web/contact.html web/style.css web/Dockerfile
git commit -m "feat: add shared header/footer chrome and coming-soon stub pages"
```

---

### Task 2: Rewrite `index.html` — hero, search, examples, info cards, empty state

**Files:**
- Modify: `web/index.html` (full rewrite)
- Modify: `web/style.css` (append hero/info-card/empty-state rules)

**Interfaces:**
- Consumes: `renderHeader`/`renderFooter` from Task 1's `chrome.js`.
- Produces: the DOM ids `app.js` (Task 7) will bind to: `#search-form`, `#search-input`,
  `#search-status`, `#content`, and `button.example-chip[data-example]`. Also produces the
  `#content` region's **initial static markup** (info cards + tier explainer) that Task 7's
  `showHome()` restores by caching `contentEl.innerHTML` at load — this task's markup for
  `#content` is exactly what "home" looks like, no JS needed for it.

- [ ] **Step 1: Write `web/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Parts Lookup</title>
  <link rel="stylesheet" href="style.css">
</head>
<body class="public-page">
  <div id="header-slot"></div>

  <main class="site-shell">
    <section class="hero">
      <h1>RV Interchange</h1>
      <p class="hero-subtitle">
        Search by manufacturer part number, model number, SKU, or known alternate number.
      </p>

      <form id="search-form" class="search-form">
        <label for="search-input" class="visually-hidden">Search for a part</label>
        <input
          id="search-input"
          type="text"
          placeholder="Try SW6DE, 7330G335, or 630762..."
          autocomplete="off">
        <button type="submit">Search</button>
      </form>

      <div class="example-chips">
        <span class="example-chips-label">Examples:</span>
        <button type="button" class="example-chip" data-example="SW6DEL">SW6DEL</button>
        <button type="button" class="example-chip" data-example="7330G335">7330G335</button>
        <button type="button" class="example-chip" data-example="AP7862">AP7862</button>
        <button type="button" class="example-chip" data-example="2608A">2608A</button>
      </div>
    </section>

    <div id="search-status" aria-live="polite"></div>

    <div id="content">
      <div class="info-cards">
        <div class="info-card">
          <h2>Search Any Known Number</h2>
          <p>Use an OEM number, model number, SKU, retailer number, or known alternate
            identifier.</p>
        </div>
        <div class="info-card">
          <h2>Understand the Fit</h2>
          <p>Results distinguish exact replacements, direct-fit replacements, and parts that
            require modification.</p>
        </div>
        <div class="info-card">
          <h2>Evidence-Backed Data</h2>
          <p>Compatibility information is built from manufacturer literature, source
            documents, and captured research evidence.</p>
        </div>
      </div>

      <div class="tier-explainer">
        <h2>Understanding compatibility tiers</h2>
        <ul>
          <li><strong>Exact Match</strong> — matches the original part's fit and intended
            function.</li>
          <li><strong>Direct Fit</strong> — installs without physical modification, but
            specifications should still be reviewed.</li>
          <li><strong>Fits With Modification</strong> — may require wiring, adapters,
            installation changes, or additional parts.</li>
        </ul>
      </div>
    </div>
  </main>

  <div id="footer-slot"></div>

  <script src="api-client.js"></script>
  <script src="chrome.js"></script>
  <script src="url-state.js"></script>
  <script src="results.js"></script>
  <script src="detail.js"></script>
  <script src="discontinued.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Append hero/info-card/empty-state CSS to `web/style.css`**

```css
.hero {
  max-width: 40rem;
  margin: 0 auto;
  padding: 3rem 1.5rem 2rem;
  text-align: center;
}

.hero h1 {
  font-size: 2.1rem;
  color: #111827;
  margin: 0 0 0.6rem;
}

.hero-subtitle {
  color: #4b5563;
  margin: 0 0 1.5rem;
}

.search-form {
  justify-content: center;
}

.search-form input {
  flex: 1;
  min-width: 16rem;
  background: #fff;
  color: #111827;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}

.search-form button {
  background: #d99a2b;
  border: 1px solid #d99a2b;
  color: #1a1200;
  border-radius: 6px;
  min-height: 44px;
}

.example-chips {
  margin-top: 0.9rem;
  font-size: 0.85rem;
  color: #6b7280;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
}

.example-chip {
  background: none;
  border: none;
  color: #0f1b2d;
  text-decoration: underline;
  font-size: 0.85rem;
  padding: 0.3rem 0.4rem;
  min-height: 44px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

#search-status {
  text-align: center;
  min-height: 1.2rem;
  margin: 0.5rem 0;
  color: #374151;
}

#search-status.error {
  color: #b00020;
  font-weight: bold;
}

.info-cards {
  max-width: 56rem;
  margin: 1rem auto;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.info-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1rem;
}

.info-card h2 {
  font-size: 1rem;
  margin: 0 0 0.4rem;
  color: #111827;
}

.info-card p {
  font-size: 0.85rem;
  color: #6b7280;
  margin: 0;
}

.tier-explainer {
  max-width: 56rem;
  margin: 1.5rem auto 3rem;
  padding: 0 1.5rem;
}

.tier-explainer ul {
  padding-left: 1.2rem;
}

@media (max-width: 640px) {
  .info-cards {
    grid-template-columns: 1fr;
  }

  .search-form {
    flex-direction: column;
    align-items: stretch;
  }
}
```

- [ ] **Step 3: Manually verify**

Open `web/index.html` directly in a browser (`file://` — the search form won't work yet since
`app.js` doesn't exist as the orchestrator until Task 7, but this step only checks static
layout). Confirm: header renders, hero shows "RV Interchange" heading + search box + 4 example
chip buttons, three info cards render in a row (single column under 640px — resize to check),
tier explainer list renders, footer renders. No console errors about missing `renderHeader`/
`renderFooter` (both exist from Task 1); expect console errors about other undefined functions
referenced by not-yet-created scripts — that's expected at this point since `url-state.js`
etc. don't exist yet. To isolate this task's own markup from those errors, temporarily comment
out the `<script src="url-state.js">` through `<script src="app.js">` lines while checking,
then restore them (they'll be filled in by later tasks).

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/style.css
git commit -m "feat: rewrite index.html with hero, search, examples, and info cards"
```

---

### Task 3: URL state module

**Files:**
- Create: `web/url-state.js`
- Modify: `web/Dockerfile` (add `COPY url-state.js /usr/share/nginx/html/url-state.js`, right
  after the `chrome.js` line — every later task that adds a browser-loaded file adds its own
  `COPY` line the same way, so the Docker image never lags behind what `index.html` actually
  references)

**Interfaces:**
- Produces: `parseUrlState()` → `{ q: string|null, part: {ns: string, value: string}|null }`,
  reads `window.location.search`. `buildQueryString({ q, part })` → `string` (starts with `?`,
  or `""` if both `q` and `part` are falsy). `pushUrlState({ q, part })` → `void`, calls
  `history.pushState`.
- Consumes: nothing.

- [ ] **Step 1: Write `web/url-state.js`**

```javascript
function parseUrlState() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q");
  const partParam = params.get("part");

  let part = null;
  if (partParam && partParam.includes(":")) {
    const idx = partParam.indexOf(":");
    part = { ns: partParam.slice(0, idx), value: partParam.slice(idx + 1) };
  }

  return { q: q || null, part };
}

function buildQueryString({ q, part }) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (part) params.set("part", `${part.ns}:${part.value}`);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function pushUrlState(state) {
  const qs = buildQueryString(state);
  const url = `${window.location.pathname}${qs}`;
  history.pushState(null, "", url);
}
```

- [ ] **Step 2: Manually verify the pure logic**

These three functions have no DOM-rendering side effects, so verify them from the browser
console once `index.html` loads (after Task 2's script tag is uncommented — it already
references `url-state.js`). Open `web/index.html` in a browser, open devtools console, and run:

```javascript
buildQueryString({ q: "7330G335", part: null })
// expect: "?q=7330G335"
buildQueryString({ q: "7330G335", part: { ns: "coleman", value: "9420-351" } })
// expect: "?q=7330G335&part=coleman%3A9420-351"
buildQueryString({ q: null, part: null })
// expect: ""

history.pushState(null, "", "/?q=SW6DE&part=suburban:SW6DE")
parseUrlState()
// expect: { q: "SW6DE", part: { ns: "suburban", value: "SW6DE" } }
history.pushState(null, "", "/")
```

Confirm each matches the expected value shown in the comment. Full integration (this module
driving actual navigation) is verified end-to-end in Task 9.

- [ ] **Step 3: Commit**

```bash
git add web/url-state.js web/Dockerfile
git commit -m "feat: add URL state parse/build helpers for search and part deep-linking"
```

---

### Task 4: Search results rendering — cards, loading, no-result, error states

**Files:**
- Create: `web/results.js`
- Modify: `web/style.css` (append result-card/no-results/error-state rules)
- Modify: `web/Dockerfile` (add `COPY results.js /usr/share/nginx/html/results.js`)

**Interfaces:**
- Produces: `renderResultsView(searchResponse, { onSelectResult })` → `HTMLElement`.
  `searchResponse` matches `SearchResponse` (`{ query, results }` where each result matches
  `SearchResultItem`: `{ component_id, label, manufacturer, part_type, identifiers, attributes }`).
  `onSelectResult(result)` is called with the clicked `SearchResultItem` when a card is
  activated (click or keyboard — native `<button>` gives keyboard activation for free).
  `renderNoResultsState(query)` → `HTMLElement`. `renderErrorState(message, technicalDetail)` →
  `HTMLElement` (`technicalDetail` optional; when present, rendered inside a collapsible
  `<details>`). `highlightMatch(label, query)` → `HTMLElement` (a `<span>` with the matched
  substring wrapped in `<mark>`; built via `createElement`/`createTextNode`, never `innerHTML`,
  since `label` and `query` can both come from user/API input).
- Consumes: nothing beyond the DOM API.

- [ ] **Step 1: Write `web/results.js`**

```javascript
function highlightMatch(label, query) {
  const wrapper = document.createElement("span");

  if (!query) {
    wrapper.textContent = label;
    return wrapper;
  }

  const idx = label.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) {
    wrapper.textContent = label;
    return wrapper;
  }

  const before = label.slice(0, idx);
  const match = label.slice(idx, idx + query.length);
  const after = label.slice(idx + query.length);

  if (before) wrapper.appendChild(document.createTextNode(before));
  const mark = document.createElement("mark");
  mark.textContent = match;
  wrapper.appendChild(mark);
  if (after) wrapper.appendChild(document.createTextNode(after));

  return wrapper;
}

function renderResultsView(searchResponse, { onSelectResult }) {
  const container = document.createElement("div");

  const summary = document.createElement("p");
  summary.className = "results-summary";
  const count = searchResponse.results.length;
  summary.textContent = `${count} match${count === 1 ? "" : "es"} for "${searchResponse.query}"`;
  container.appendChild(summary);

  const list = document.createElement("div");
  list.className = "result-list";

  for (const result of searchResponse.results) {
    list.appendChild(renderResultCard(result, searchResponse.query, onSelectResult));
  }

  container.appendChild(list);
  return container;
}

function renderResultCard(result, query, onSelectResult) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "result-card";

  if (result.manufacturer || result.part_type) {
    const meta = document.createElement("div");
    meta.className = "result-label-meta";
    meta.textContent = [result.manufacturer, result.part_type].filter(Boolean).join(" · ");
    card.appendChild(meta);
  }

  const title = document.createElement("div");
  title.className = "result-title";
  title.appendChild(highlightMatch(result.label, query));
  card.appendChild(title);

  const others = result.identifiers.map((i) => i.value).filter((v) => v !== result.label);
  if (others.length > 0) {
    const alt = document.createElement("div");
    alt.className = "result-alt";
    alt.textContent = `Also known as: ${others.join(" · ")}`;
    card.appendChild(alt);
  }

  const chevron = document.createElement("span");
  chevron.className = "result-chevron";
  chevron.setAttribute("aria-hidden", "true");
  chevron.textContent = "→";
  card.appendChild(chevron);

  card.addEventListener("click", () => onSelectResult(result));
  return card;
}

function renderNoResultsState(query) {
  const container = document.createElement("div");
  container.className = "no-results";

  const heading = document.createElement("p");
  heading.className = "no-results-heading";
  heading.textContent = "We couldn't find that number yet.";
  container.appendChild(heading);

  const sub = document.createElement("p");
  sub.textContent = `No match found for "${query}"`;
  container.appendChild(sub);

  const tryHeading = document.createElement("p");
  tryHeading.textContent = "Try:";
  container.appendChild(tryHeading);

  const list = document.createElement("ul");
  const suggestions = [
    "The number without spaces",
    "The number without hyphens",
    "Another number printed on the label",
    "Reviewing supported manufacturers",
  ];
  for (const s of suggestions) {
    const li = document.createElement("li");
    li.textContent = s;
    list.appendChild(li);
  }
  container.appendChild(list);

  const reportLink = document.createElement("a");
  reportLink.href = "https://github.com/tokendad/RV_Interchange/issues/new";
  reportLink.textContent = "Report a missing part";
  container.appendChild(reportLink);

  return container;
}

function renderErrorState(message, technicalDetail) {
  const container = document.createElement("div");
  container.className = "error-state";

  const msg = document.createElement("p");
  msg.className = "error-message";
  msg.textContent = message;
  container.appendChild(msg);

  if (technicalDetail) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Technical details";
    details.appendChild(summary);
    const pre = document.createElement("pre");
    pre.textContent = technicalDetail;
    details.appendChild(pre);
    container.appendChild(details);
  }

  return container;
}
```

- [ ] **Step 2: Append result/no-results/error CSS to `web/style.css`**

```css
.results-summary {
  color: #374151;
  font-size: 0.9rem;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin: 0.5rem 0 2rem;
}

.result-card {
  display: block;
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0.9rem 1rem;
  cursor: pointer;
  position: relative;
  min-height: 44px;
}

.result-card:hover {
  background: #f9fafb;
}

.result-label-meta {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #6b7280;
  text-transform: uppercase;
}

.result-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
  margin-top: 2px;
}

.result-title mark {
  background: #fde68a;
  padding: 0 2px;
}

.result-alt {
  font-size: 0.82rem;
  color: #6b7280;
  margin-top: 4px;
}

.result-chevron {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #d99a2b;
  font-size: 1.2rem;
}

.no-results,
.error-state {
  max-width: 40rem;
  margin: 1.5rem auto;
  padding: 0 1.5rem;
}

.no-results-heading,
.error-message {
  font-weight: 700;
  color: #111827;
}

@media (max-width: 640px) {
  .result-list {
    gap: 0.5rem;
  }
}
```

- [ ] **Step 3: Manually verify with fixture data**

Open `web/index.html` in a browser, open devtools console, and run:

```javascript
const fixture = {
  query: "7330",
  results: [
    {
      component_id: "c1", label: "7330G335", manufacturer: "Coleman-Mach",
      part_type: "Thermostat",
      identifiers: [{ ns: "coleman", value: "7330G335" }, { ns: "coleman", value: "AP7862" }],
      attributes: [],
    },
  ],
};
document.getElementById("content").replaceChildren(
  renderResultsView(fixture, { onSelectResult: (r) => console.log("selected", r) }));
```

Confirm: "1 match for \"7330\"" summary renders, one card shows "COLEMAN-MACH · THERMOSTAT",
title "7330G335" with "7330" highlighted in yellow, "Also known as: AP7862" line, amber arrow.
Click the card and confirm `selected {...}` logs to the console. Then run
`document.getElementById("content").replaceChildren(renderNoResultsState("bogus123"))` and
confirm the no-results copy renders with the report link, and
`document.getElementById("content").replaceChildren(renderErrorState("The lookup service is temporarily unavailable. Please try the search again.", "HTTP 500"))`
and confirm the message renders with a collapsible "Technical details" section.

- [ ] **Step 4: Commit**

```bash
git add web/results.js web/style.css web/Dockerfile
git commit -m "feat: add search result cards and loading/no-result/error states"
```

---

### Task 5: Part detail rendering — heading, tiered replacement cards, copy link

**Files:**
- Create: `web/detail.js`
- Modify: `web/style.css` (append detail-view/tier-pill rules)
- Modify: `web/Dockerfile` (add `COPY detail.js /usr/share/nginx/html/detail.js`)

**Interfaces:**
- Produces: `renderDetailView({ resolveData, replacementsData, ns }, { onBack, onCopyLink,
  onChainNodeClick })` → `HTMLElement`. `resolveData` matches `ResolveResponse` (`{
  component_id, manufacturer, part_type, identifiers, attributes }`). `replacementsData`
  matches `ReplacementsResponse` (`{ source, replacements, supersessions }`). `ns` is the
  namespace string used to resolve this part (needed to pass into the Discontinued chain
  walk). `onBack()`, `onCopyLink()` are no-arg callbacks. `onChainNodeClick(value)` is called
  with a part-number string when a Discontinued chain node is clicked (wired through to
  `discontinued.js`'s `renderDiscontinuedSection`, added in Task 6).
- Consumes (Task 6, added next but referenced here since Task 5's `renderDetailView` calls it —
  see the note in Step 1): `walkSupersessionChain(ns, sourceValue, supersessions)` → `Promise`
  resolving to a chain tree, and `renderDiscontinuedSection(tree, { onNodeClick })` →
  `HTMLElement`. These don't exist until Task 6, so Step 3 of this task verifies everything
  *except* the Discontinued section using a fixture with an empty `supersessions` array; the
  Discontinued behavior is verified in Task 6 once its functions exist.

- [ ] **Step 1: Write `web/detail.js`**

```javascript
const TIER_ORDER = ["Exact Match", "Direct Fit", "Fits With Modification"];
const TIER_CLASS = {
  "Exact Match": "tier-exact",
  "Direct Fit": "tier-direct",
  "Fits With Modification": "tier-modification",
};
const TIER_ICON = {
  "Exact Match": "✓",
  "Direct Fit": "↔",
  "Fits With Modification": "⚠",
};

function renderDetailView({ resolveData, replacementsData, ns }, { onBack, onCopyLink, onChainNodeClick }) {
  const container = document.createElement("div");
  container.className = "detail-view";

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.className = "back-link";
  backButton.textContent = "← Back to results";
  backButton.addEventListener("click", onBack);
  container.appendChild(backButton);

  if (resolveData.manufacturer || resolveData.part_type) {
    const metaLine = document.createElement("div");
    metaLine.className = "detail-meta";
    metaLine.textContent =
      [resolveData.manufacturer, resolveData.part_type].filter(Boolean).join(" · ");
    container.appendChild(metaLine);
  }

  const heading = document.createElement("h1");
  heading.className = "detail-heading";
  heading.textContent = replacementsData.source;
  container.appendChild(heading);

  const others = resolveData.identifiers
    .map((i) => i.value)
    .filter((v) => v !== replacementsData.source);
  const altLine = document.createElement("div");
  altLine.className = "detail-alt";
  altLine.textContent = others.length > 0
    ? `Also known as: ${others.join(" · ")}`
    : "No alternate identifiers on file";
  container.appendChild(altLine);

  const byTier = {};
  for (const item of replacementsData.replacements) {
    if (!byTier[item.fit]) byTier[item.fit] = [];
    byTier[item.fit].push(item);
  }
  const hasReplacements = TIER_ORDER.some((tier) => byTier[tier] && byTier[tier].length > 0);
  if (hasReplacements) {
    const repHeading = document.createElement("h2");
    repHeading.className = "section-heading";
    repHeading.textContent = "Compatible Replacements";
    container.appendChild(repHeading);

    for (const tier of TIER_ORDER) {
      const items = byTier[tier];
      if (!items || items.length === 0) continue;
      for (const item of items) {
        container.appendChild(renderReplacementCard(tier, item));
      }
    }
  }

  if (replacementsData.supersessions.length > 0) {
    const placeholder = document.createElement("div");
    placeholder.className = "discontinued-loading";
    placeholder.textContent = "Loading discontinued history…";
    container.appendChild(placeholder);

    walkSupersessionChain(ns, replacementsData.source, replacementsData.supersessions)
      .then((tree) => {
        placeholder.replaceWith(renderDiscontinuedSection(tree, { onNodeClick: onChainNodeClick }));
      });
  }

  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "copy-link-button";
  copyButton.textContent = "Copy link";
  copyButton.addEventListener("click", onCopyLink);
  container.appendChild(copyButton);

  return container;
}

function renderReplacementCard(tier, item) {
  const card = document.createElement("div");
  card.className = `replacement-card ${TIER_CLASS[tier]}`;

  const pill = document.createElement("span");
  pill.className = `tier-pill ${TIER_CLASS[tier]}`;
  pill.textContent = `${TIER_ICON[tier]} ${tier}`;
  card.appendChild(pill);

  const partLine = document.createElement("div");
  partLine.className = "replacement-part";
  partLine.textContent = item.part;
  card.appendChild(partLine);

  if (item.caveats && item.caveats.length > 0) {
    const caveatLine = document.createElement("div");
    caveatLine.className = "replacement-caveats";
    caveatLine.textContent = item.caveats.map((c) => c.text).join("; ");
    card.appendChild(caveatLine);
  }

  return card;
}
```

- [ ] **Step 2: Append detail-view/tier-pill CSS to `web/style.css`**

```css
.detail-view {
  max-width: 44rem;
  margin: 0 auto 3rem;
  padding: 0 1.5rem;
}

.back-link {
  background: none;
  border: none;
  color: #0f1b2d;
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.4rem 0;
  margin-bottom: 0.8rem;
  min-height: 44px;
}

.detail-meta {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #6b7280;
  text-transform: uppercase;
}

.detail-heading {
  font-size: 1.6rem;
  color: #111827;
  margin: 2px 0 4px;
}

.detail-alt {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 1.2rem;
}

.section-heading {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #374151;
  text-transform: uppercase;
  margin: 1.2rem 0 0.6rem;
}

.replacement-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 0.9rem 1rem;
  margin-bottom: 0.6rem;
}

.replacement-card.tier-modification {
  border: 2px solid #fecaca;
}

.tier-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 999px;
}

.tier-pill.tier-exact {
  background: #dcfce7;
  color: #166534;
}

.tier-pill.tier-direct {
  background: #fef9c3;
  color: #854d0e;
}

.tier-pill.tier-modification {
  background: #fee2e2;
  color: #991b1b;
}

.replacement-part {
  font-size: 1.05rem;
  font-weight: 600;
  color: #111827;
  margin-top: 6px;
}

.replacement-caveats {
  font-size: 0.85rem;
  color: #4b5563;
  margin-top: 2px;
}

.copy-link-button {
  margin-top: 1.2rem;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  min-height: 44px;
}
```

- [ ] **Step 3: Manually verify with a no-supersessions fixture**

Open `web/index.html` in a browser (Tasks 1-4's scripts loaded; Task 6's `discontinued.js`
script tag is already referenced in `index.html` from Task 2 but the file doesn't exist yet —
temporarily comment out that one `<script src="discontinued.js">` line so the page doesn't
throw a load error, then run in the console):

```javascript
const resolveFixture = {
  component_id: "c1", manufacturer: "Coleman-Mach", part_type: "Wall Thermostat",
  identifiers: [{ ns: "coleman", value: "7330G335" }, { ns: "coleman", value: "AP7862" }],
  attributes: [],
};
const replacementsFixture = {
  source: "7330G335",
  replacements: [
    { part: "9420-351", fit: "Exact Match", rank: 1, required_parts: [], caveats: [] },
    { part: "AP9330", fit: "Fits With Modification", rank: 2, required_parts: [],
      caveats: [{ text: "Requires rewiring the thermostat harness", blocking: true }] },
  ],
  supersessions: [],
};
document.getElementById("content").replaceChildren(renderDetailView(
  { resolveData: resolveFixture, replacementsData: replacementsFixture, ns: "coleman" },
  { onBack: () => console.log("back"), onCopyLink: () => console.log("copy"), onChainNodeClick: () => {} }));
```

Confirm: back link, "COLEMAN-MACH · WALL THERMOSTAT" meta line, "7330G335" heading, "Also
known as: AP7862", "Compatible Replacements" heading, a green "✓ Exact Match" pill card
showing "9420-351", a red "⚠ Fits With Modification" pill card with the heavier red border
showing "AP9330" and its caveat text, no "Discontinued" section (supersessions was empty), a
"Copy link" button. Restore the commented-out `discontinued.js` script tag afterward.

- [ ] **Step 4: Commit**

```bash
git add web/detail.js web/style.css web/Dockerfile
git commit -m "feat: add part detail view with tiered replacement cards"
```

---

### Task 6: Discontinued section — chain walk with branch disambiguation

**Files:**
- Create: `web/discontinued.js`
- Modify: `web/style.css` (append discontinued-chain rules)
- Modify: `web/Dockerfile` (add `COPY discontinued.js /usr/share/nginx/html/discontinued.js` —
  this makes the Dockerfile complete for every file `index.html` references; Task 9 double
  checks this rather than adding anything new)

**Interfaces:**
- Produces: `walkSupersessionChain(ns, value, initialSupersessions)` → `Promise<ChainNode>`
  where `ChainNode` is `{ value: string, current: boolean, children: ChainNode[],
  attributes?: AttributeOut[], cycle?: boolean }`. `initialSupersessions` matches
  `ReplacementsResponse.supersessions` (`SupersessionItem[]`: `{ part, note }`).
  `renderDiscontinuedSection(rootNode, { onNodeClick })` → `HTMLElement` (a `<section>`
  containing the "Discontinued" heading + chain card) — always renders something; callers
  only invoke it when `supersessions.length > 0` (per `detail.js` Task 5). `formatAttribute(attr)`
  → `string`, given an `AttributeOut` (`{ name, qualifier, value, unit }`).
- Consumes: `rviFetch(path)` from `api-client.js` (already loaded).

- [ ] **Step 1: Write `web/discontinued.js`**

```javascript
async function walkSupersessionChain(ns, value, initialSupersessions) {
  const visited = new Set([`${ns}:${value}`]);

  async function buildNode(nodeValue, children) {
    if (!children || children.length === 0) {
      return { value: nodeValue, current: true, children: [] };
    }

    const showAttributes = children.length > 1;
    const childNodes = [];

    for (const child of children) {
      const key = `${ns}:${child.part}`;
      if (visited.has(key)) {
        childNodes.push({ value: child.part, current: true, children: [], cycle: true });
        continue;
      }
      visited.add(key);

      const replacementsResult = await rviFetch(
        `/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(child.part)}`);
      const nextSupersessions =
        replacementsResult.ok && replacementsResult.body ? replacementsResult.body.supersessions : [];

      let attributes = [];
      if (showAttributes) {
        const resolveResult = await rviFetch(
          `/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(child.part)}`);
        if (resolveResult.ok && resolveResult.body) {
          attributes = resolveResult.body.attributes.slice(0, 2);
        }
      }

      const childNode = await buildNode(child.part, nextSupersessions);
      childNode.attributes = attributes;
      childNodes.push(childNode);
    }

    return { value: nodeValue, current: false, children: childNodes };
  }

  return buildNode(value, initialSupersessions);
}

function formatAttribute(attr) {
  const name = attr.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const value = attr.qualifier ? `${attr.qualifier} ${attr.value}` : attr.value;
  return attr.unit ? `${name}: ${value} ${attr.unit}` : `${name}: ${value}`;
}

function renderDiscontinuedSection(rootNode, { onNodeClick }) {
  const section = document.createElement("section");
  section.className = "discontinued-section";

  const heading = document.createElement("h2");
  heading.className = "section-heading";
  heading.textContent = "Discontinued";
  section.appendChild(heading);

  const card = document.createElement("div");
  card.className = "discontinued-card";
  card.appendChild(renderChainNode(rootNode, true, onNodeClick));
  section.appendChild(card);

  return section;
}

function renderChainNode(node, isRoot, onNodeClick) {
  const wrapper = document.createElement("div");
  wrapper.className = "chain-branch";

  const nodeButton = document.createElement("button");
  nodeButton.type = "button";
  nodeButton.className = "chain-node" + (node.current ? " chain-node-current" : "");
  nodeButton.addEventListener("click", () => onNodeClick(node.value));

  const numberSpan = document.createElement("span");
  numberSpan.className = "chain-node-number";
  numberSpan.textContent = node.value;
  nodeButton.appendChild(numberSpan);

  const tagSpan = document.createElement("span");
  tagSpan.className = "chain-node-tag";
  tagSpan.textContent = isRoot
    ? "(this part)"
    : node.current ? "— current" : "(also discontinued)";
  nodeButton.appendChild(tagSpan);

  if (node.attributes && node.attributes.length > 0) {
    const attrLine = document.createElement("div");
    attrLine.className = "chain-node-attributes";
    attrLine.textContent = node.attributes.map(formatAttribute).join(" · ");
    nodeButton.appendChild(attrLine);
  }

  wrapper.appendChild(nodeButton);

  if (node.children.length > 0) {
    const arrow = document.createElement("div");
    arrow.className = "chain-arrow";
    arrow.textContent = node.children.length > 1
      ? "↓ replaced by two current options"
      : "↓ replaced by";
    wrapper.appendChild(arrow);

    const childrenRow = document.createElement("div");
    childrenRow.className = "chain-children";
    for (const child of node.children) {
      childrenRow.appendChild(renderChainNode(child, false, onNodeClick));
    }
    wrapper.appendChild(childrenRow);
  }

  return wrapper;
}
```

- [ ] **Step 2: Append discontinued-chain CSS to `web/style.css`**

```css
.discontinued-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1.2rem;
}

.chain-branch {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.chain-node {
  display: block;
  text-align: left;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  min-height: 44px;
  font-size: 0.95rem;
  color: #111827;
}

.chain-node-current {
  border: 2px solid #16a34a;
  background: #f0fdf4;
  font-weight: 600;
}

.chain-node-tag {
  color: #9ca3af;
  font-size: 0.8rem;
  margin-left: 6px;
}

.chain-node-current .chain-node-tag {
  color: #166534;
}

.chain-node-attributes {
  font-size: 0.78rem;
  color: #4b5563;
  margin-top: 3px;
}

.chain-arrow {
  color: #d99a2b;
  padding: 2px 0 2px 20px;
  font-size: 0.85rem;
}

.chain-children {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.discontinued-loading {
  color: #6b7280;
  font-size: 0.85rem;
  margin-top: 1rem;
}
```

- [ ] **Step 3: Manually verify against the real API**

This is the one piece that genuinely needs live data (the branching chain), so this
verification runs against the Docker stack rather than a fixture. Bring up the stack:

```bash
cd /data/DockerConfigs && docker compose up -d --build rvinterchange-api rvinterchange-web
```

Open `http://localhost:8485/` (restore the `discontinued.js` script tag in `index.html` if it
was commented out during Task 5's verification), open devtools console, and run:

```javascript
const result = await rviFetch("/public/v1/replacements?ns=coleman&identifier=7330E336");
const tree = await walkSupersessionChain("coleman", result.body.source, result.body.supersessions);
document.getElementById("content").replaceChildren(
  renderDiscontinuedSection(tree, { onNodeClick: (v) => console.log("clicked", v) }));
```

Confirm the chain renders: `7330E336 (this part)` → arrow "replaced by" → `7330F3361 (also
discontinued)` → arrow "replaced by two current options" → two green "current" boxes for
`9420-352` and `9420A382`, each showing a short attribute line (e.g. something like "Interface
Type: analog" vs "Interface Type: digital" — exact wording depends on `formatAttribute`'s
humanization of whatever attribute names the API returns first). Click each of the 4 nodes and
confirm `clicked <value>` logs the right part number each time.

- [ ] **Step 4: Commit**

```bash
git add web/discontinued.js web/style.css web/Dockerfile
git commit -m "feat: add Discontinued section with walked, branch-aware supersession chain"
```

---

### Task 7: `app.js` — orchestration, view switching, URL sync

**Files:**
- Modify: `web/app.js` (full rewrite)

**Interfaces:**
- Consumes: `renderHeader`/`renderFooter` (Task 1), `parseUrlState`/`pushUrlState` (Task 3),
  `renderResultsView`/`renderNoResultsState`/`renderErrorState` (Task 4), `renderDetailView`
  (Task 5), `rviFetch` (`api-client.js`, pre-existing).
- Produces: nothing consumed by other files — this is the top-level wiring, invoked by the
  browser on page load.

- [ ] **Step 1: Write `web/app.js`**

```javascript
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchButton = searchForm.querySelector('button[type="submit"]');
const statusEl = document.getElementById("search-status");
const contentEl = document.getElementById("content");
const homeContentHTML = contentEl.innerHTML;

let lastSearchResponse = null;
let currentQuery = null;

document.getElementById("header-slot").replaceWith(renderHeader("lookup"));
document.getElementById("footer-slot").replaceWith(renderFooter());

document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    searchInput.value = chip.dataset.example;
    searchForm.requestSubmit();
  });
});

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;
  runSearch(query, { pushUrl: true });
});

window.addEventListener("popstate", () => {
  const state = parseUrlState();
  if (!state.q) {
    showHome();
    return;
  }
  searchInput.value = state.q;
  runSearch(state.q, { pushUrl: false, thenOpenPart: state.part });
});

async function runSearch(query, { pushUrl, thenOpenPart }) {
  statusEl.className = "";
  statusEl.textContent = "Searching RV Interchange…";
  searchButton.disabled = true;

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/search?q=${encodeURIComponent(query)}&limit=20`);

  searchButton.disabled = false;
  currentQuery = query;

  if (!ok) {
    statusEl.className = "error";
    statusEl.textContent = "The lookup service is temporarily unavailable.";
    const detail = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "search failed"}`;
    contentEl.innerHTML = "";
    contentEl.appendChild(renderErrorState(
      "The lookup service is temporarily unavailable. Please try the search again.", detail));
    if (pushUrl) pushUrlState({ q: query, part: null });
    return;
  }

  lastSearchResponse = body;

  if (body.results.length === 0) {
    statusEl.className = "";
    statusEl.textContent = "";
    contentEl.innerHTML = "";
    contentEl.appendChild(renderNoResultsState(query));
    if (pushUrl) pushUrlState({ q: query, part: null });
    return;
  }

  statusEl.className = "";
  statusEl.textContent =
    `${body.results.length} match${body.results.length === 1 ? "" : "es"} for "${body.query}"`;
  showResultsView();
  if (pushUrl) pushUrlState({ q: query, part: null });

  if (thenOpenPart) {
    const matched = body.results
      .flatMap((r) => r.identifiers.map((i) => ({ i })))
      .find(({ i }) => i.ns === thenOpenPart.ns && i.value === thenOpenPart.value);
    if (matched) {
      await openDetail(thenOpenPart.ns, thenOpenPart.value, { pushUrl: false });
    }
  }
}

function showHome() {
  contentEl.innerHTML = homeContentHTML;
  statusEl.textContent = "";
  statusEl.className = "";
  searchInput.value = "";
  lastSearchResponse = null;
}

function showResultsView() {
  if (!lastSearchResponse) {
    showHome();
    return;
  }
  contentEl.innerHTML = "";
  contentEl.appendChild(renderResultsView(lastSearchResponse, { onSelectResult: handleSelectResult }));
}

function handleSelectResult(result) {
  const matched = result.identifiers.find((i) => i.value === result.label) || result.identifiers[0];
  openDetail(matched.ns, matched.value, { pushUrl: true });
}

async function openDetail(ns, value, { pushUrl }) {
  contentEl.innerHTML = "<p>Loading part details…</p>";

  const [resolveResult, replacementsResult] = await Promise.all([
    rviFetch(`/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(value)}`),
    rviFetch(`/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(value)}`),
  ]);

  if (!resolveResult.ok || !replacementsResult.ok) {
    contentEl.innerHTML = "";
    const detail = resolveResult.error || replacementsResult.error || "lookup failed";
    contentEl.appendChild(renderErrorState(
      "The lookup service is temporarily unavailable. Please try the search again.", detail));
    return;
  }

  contentEl.innerHTML = "";
  contentEl.appendChild(renderDetailView(
    { resolveData: resolveResult.body, replacementsData: replacementsResult.body, ns },
    {
      onBack: () => {
        showResultsView();
        pushUrlState({ q: currentQuery, part: null });
      },
      onCopyLink: () => {
        navigator.clipboard.writeText(window.location.href);
      },
      onChainNodeClick: (nextValue) => openDetail(ns, nextValue, { pushUrl: true }),
    },
  ));

  if (pushUrl) pushUrlState({ q: currentQuery, part: { ns, value } });
}

(function init() {
  const state = parseUrlState();
  if (state.q) {
    searchInput.value = state.q;
    runSearch(state.q, { pushUrl: false, thenOpenPart: state.part });
  }
})();
```

- [ ] **Step 2: Manually verify the full in-page flow**

Bring up the stack if it isn't already running:

```bash
cd /data/DockerConfigs && docker compose up -d --build rvinterchange-api rvinterchange-web
```

Open `http://localhost:8485/`. Confirm:
1. Home view shows hero + info cards + tier explainer.
2. Type `7330` and submit — status shows "Searching RV Interchange…" briefly, then result
   cards render, URL updates to `/?q=7330`.
3. Click a result card — detail view replaces the results list, URL updates to add
   `&part=coleman:...`.
4. Click "← Back to results" — results list reappears (no new network call — check the
   Network tab shows no new `/search` request), URL drops `part`.
5. Click browser Back — returns to the pre-search home state (or whatever the prior history
   entry was); click Forward — search re-runs and results reappear.
6. Reload the page directly at a URL like `http://localhost:8485/?q=7330G335` — confirm it
   reproduces the search results without you typing anything.
7. Click an example chip (e.g. "SW6DEL") — confirm it populates the input and submits
   automatically.
8. Search for a nonsense string like `zzzzz999` — confirm the no-results copy renders.

- [ ] **Step 3: Commit**

```bash
git add web/app.js
git commit -m "feat: rewrite app.js to orchestrate home/results/detail views with URL sync"
```

---

### Task 8: Accessibility and mobile polish pass

**Files:**
- Modify: `web/style.css` (append focus/mobile rules; this task is a review pass over what
  Tasks 1-7 already built, not new functionality)
- Modify: `web/index.html` (nav collapse markup, if needed after manual review — see Step 1)

**Interfaces:** none new — this task audits and patches gaps in what earlier tasks already
built, per spec §E.

- [ ] **Step 1: Audit against the spec's accessibility checklist**

Using the running stack from Task 7, walk through spec §E's list and confirm/fix each:

- Semantic landmarks: `<header>` (from `chrome.js`), `<main class="site-shell">` (`index.html`),
  `<footer>` (from `chrome.js`) — already present from Tasks 1-2, no change needed.
- `<label for="search-input">` — already present in Task 2's `index.html`
  (`.visually-hidden` class keeps it out of the visual layout while staying in the
  accessibility tree) — no change needed.
- Result cards, example chips, chain nodes are all real `<button>` elements — already true
  from Tasks 4 and 6 — no change needed.
- `:focus-visible` outline — already added in Task 1's base CSS
  (`:focus-visible { outline: 2px solid #d99a2b; ... }`) and applies globally — tab through
  the page and confirm every interactive element (nav links, example chips, result cards,
  back link, chain nodes, copy-link button) shows a visible amber outline. If any element is
  missing an outline (e.g. an `<a>` with `outline: none` inherited from somewhere), fix it
  here.
- `aria-live="polite"` on `#search-status` — already present in Task 2's `index.html` — no
  change needed.
- 44px touch targets — already applied via `min-height: 44px` on `.nav-link`,
  `.search-form button`, `.example-chip`, `.result-card`, `.back-link`, `.chain-node`,
  `.copy-link-button` across Tasks 1, 2, 4, 5, 6 — measure a few in devtools to confirm the
  computed height is actually ≥44px (padding can get overridden by cascade order; fix any
  that measure short).
- Mobile: resize the browser to ~375px wide and confirm — search input goes full-width,
  search button stacks below it (Task 2's `@media (max-width: 640px)` rule), result cards
  stay single-column (already true, `.result-list` is a column flex), header nav wraps
  instead of overflowing (Task 1's `.site-nav { flex-wrap: wrap }`). If the nav wrapping
  looks cramped at very narrow widths, add:

```css
@media (max-width: 480px) {
  .site-nav {
    flex-direction: column;
    gap: 0.5rem;
  }
}
```

- [ ] **Step 2: Keyboard-only pass**

Using only Tab/Shift+Tab/Enter/Space (no mouse), navigate from the top of the page through:
nav links → search input → search button → example chips → (after searching) result cards →
(after opening a detail) back link, replacement cards are not focusable (they're static, not
links — confirm this is intentional per spec, which only calls out result cards and chain
nodes as needing keyboard activation, not replacement-tier cards), chain nodes, copy-link
button. Confirm Enter and Space both activate a focused result card and a focused chain node.

- [ ] **Step 3: Commit**

```bash
git add web/style.css web/index.html
git commit -m "fix: accessibility and mobile polish pass on the redesigned front page"
```

(If Step 1/2 found nothing to fix beyond what Tasks 1-7 already built, this commit may end up
empty on `style.css`/`index.html` — in that case, skip the commit and note in the task
checklist that the audit found no gaps.)

---

### Task 9: Final Dockerfile check and full end-to-end verification

**Files:**
- Modify: `web/Dockerfile` (confirm all files from Tasks 1-6 have a `COPY` line — each of
  Tasks 1, 3, 4, 5, and 6 already added its own line as it introduced a new file; this task
  double-checks the full set rather than adding anything new)

**Interfaces:** none — this is the closing verification task tying every earlier task
together against the spec's full "Testing" section.

- [ ] **Step 1: Confirm `web/Dockerfile` lists every file**

```bash
diff <(ls web/*.html web/*.js web/*.css | sort) \
     <(grep -oP '(?<=COPY )\S+' web/Dockerfile | sort)
```

Expect no output (every source file has a matching `COPY` line). If `diff` shows a file
missing from the `Dockerfile`, add the corresponding `COPY <file> /usr/share/nginx/html/<file>`
line.

- [ ] **Step 2: Rebuild and run the full stack**

```bash
cd /data/DockerConfigs && docker compose up -d --build rvinterchange-api rvinterchange-web
docker compose ps rvinterchange-api rvinterchange-web
```

Confirm both containers show `healthy`/`running`.

- [ ] **Step 3: Walk the spec's full "Testing" checklist**

Against `http://localhost:8485/`:

1. Search → click a result → view tiered replacements and (when present) the Discontinued
   chain → back to results → browser Back/Forward → reload a shared `/?q=...&part=...` URL
   directly and confirm it reproduces the same view. (Already spot-checked in Task 7 Step 2 —
   repeat once more now that Tasks 8's polish is in too, to confirm nothing regressed.)
2. Discontinued chain walk specifically: search `7330E336`, open its detail view, confirm the
   chain renders both hops and both branch endpoints (`9420-352`, `9420A382`) with their
   disambiguating attribute lines; click each of the 4 chain nodes and confirm each opens that
   part's own detail view with a correctly updated URL (check the address bar after each
   click).
3. No-result state: search `zzzzz999`, confirm the helpful copy renders (not a bare "no
   matches" line).
4. Error state: stop the API container (`docker compose stop rvinterchange-api`), search
   anything, confirm the friendly "temporarily unavailable" message renders with a collapsible
   technical-details section — then restart it (`docker compose start rvinterchange-api`).
5. Keyboard-only navigation: repeat Task 8 Step 2's walk-through once more end-to-end.
6. Stub pages: click "Data Coverage", "How It Works" in the header nav, and "Contact" in the
   footer — confirm each renders its "coming soon" stub with header/footer intact and the
   correct nav link (if any) marked active.
7. `web/admin.html` regression check: open `http://localhost:8485/admin.html` and confirm it
   still works exactly as before (raw search/resolve/replacements forms, log tail) — this
   page had zero code changes across this whole plan, so this is purely a "nothing broke it"
   sanity check (`style.css`'s base rules were preserved verbatim in Task 1).

- [ ] **Step 4: Commit (if Step 1 found any missing Dockerfile lines)**

```bash
git add web/Dockerfile
git commit -m "fix: ensure Dockerfile copies every web/ source file"
```

If Step 1 found nothing missing, there's nothing to commit — the plan is complete as of
Task 8's commit.
