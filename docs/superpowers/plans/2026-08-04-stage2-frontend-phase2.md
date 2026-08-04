# Stage 2 Frontend Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare `web/` test form with two purpose-built internal pages — a
search-first main lookup page rehearsing the real public-site flow, and an admin/debug
page with raw-request access plus a log-tail view — backed by one new small debug
endpoint.

**Architecture:** No framework, no build step — plain static HTML/CSS/JS served by the
existing `web/` nginx container, exactly like today. One new FastAPI route in
`api/main.py` outside the `/public/v1/*` namespace. No database or schema changes.

**Tech Stack:** Python 3, FastAPI (backend endpoint), vanilla HTML/CSS/JS (frontend, no
framework, no bundler), pytest (backend tests only — no frontend test framework exists
in this project and none is introduced here).

## Global Constraints

- No authentication anywhere in this phase — this remains a personal/LAN-only tool, same
  trust model as today.
- No new third-party dependencies, frontend or backend.
- The existing CORS configuration in `api/main.py` (localhost:8485, 127.0.0.1:8485, and
  any `192.168.x.x`/`10.x.x.x` origin on port 8485) already covers both new pages since
  they're served from the same nginx container on the same port — do not modify CORS.
- `/debug/v1/logs` stays outside `/public/v1/*` and outside `api/schemas.py`'s Pydantic
  response-model contract (per that file's module docstring: the Public API's schemas
  never expose internals) — it returns a plain dict, not a modeled response.
- `/public/v1/compare`, `/public/v1/interchange/{code}`, auth, branding/design-system
  work, auto-refreshing logs, and public deployment changes are explicitly out of scope
  — do not add them.
- Every task must leave `python3 -m pytest tests/ -q` fully green before it's considered
  done. Frontend tasks additionally require manual verification against the running
  Docker stack (documented per-task below) since no frontend test framework exists.

---

### Task 1: `/debug/v1/logs` backend endpoint

**Files:**
- Modify: `api/main.py`
- Modify: `tests/api/test_main.py`

**Interfaces:**
- Produces: `GET /debug/v1/logs?lines=<n, default 100, 1-1000>` → `{"lines": [<str>, ...]}`.
  Later tasks (Task 4, the admin page) call this endpoint directly over HTTP — no Python
  interface is shared, only the URL and response shape.

- [ ] **Step 1: Write the failing tests**

Add to `tests/api/test_main.py` (append at the end of the file):

```python
def test_debug_logs_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "LOG_DIR", tmp_path / "nonexistent_logs")
    response = TestClient(main_module.app).get("/debug/v1/logs")
    assert response.status_code == 200
    assert response.json() == {"lines": []}


def test_debug_logs_returns_tail_of_log_file(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "api.log"
    log_file.write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n")
    monkeypatch.setattr(main_module, "LOG_DIR", log_dir)

    response = TestClient(main_module.app).get("/debug/v1/logs", params={"lines": 3})
    assert response.status_code == 200
    assert response.json() == {"lines": ["line 8", "line 9", "line 10"]}


def test_debug_logs_rejects_out_of_range_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "LOG_DIR", tmp_path)
    client = TestClient(main_module.app)
    assert client.get("/debug/v1/logs", params={"lines": 0}).status_code == 422
    assert client.get("/debug/v1/logs", params={"lines": 1001}).status_code == 422
```

These tests call `TestClient(main_module.app)` directly (not the `client` fixture used
by the other tests in this file) because `/debug/v1/logs` doesn't use `get_conn`/the
database at all — there's nothing to override.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/api/test_main.py -k debug_logs -v`
Expected: FAIL — `404 Not Found` for all three (route doesn't exist yet)

- [ ] **Step 3: Implement the route**

In `api/main.py`, add this route after the existing `/public/v1/search` route (end of
file):

```python
@app.get("/debug/v1/logs")
def debug_logs(lines: int = Query(100, ge=1, le=1000)):
    log_path = LOG_DIR / "api.log"
    if not log_path.exists():
        return {"lines": []}
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    return {"lines": [line.rstrip("\n") for line in all_lines[-lines:]]}
```

No new imports needed — `Query` and `LOG_DIR` are already imported/defined earlier in
this file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/api/test_main.py -k debug_logs -v`
Expected: 3 passed

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass, no regressions

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/test_main.py
git commit -m "feat: add /debug/v1/logs endpoint for admin log-tail view"
```

---

### Task 2: Shared frontend API-client helper

**Files:**
- Create: `web/api-client.js`

**Interfaces:**
- Produces: a global `rviFetch(path)` async function, and a global `RVI_API_BASE`
  constant. `rviFetch` resolves to
  `{ ok: bool, status: number, body: any, elapsedMs: number, url: string, error?: string }`.
  Later tasks (3 and 4) load this file via `<script>` before their own script and call
  `rviFetch` directly (plain global-scope script, no ES module import/export — matches
  the existing `web/app.js`'s style, which also isn't a module).

- [ ] **Step 1: Create the file**

Create `web/api-client.js`:

```javascript
const RVI_API_BASE = `${window.location.protocol}//${window.location.hostname}:8484`;

async function rviFetch(path) {
  const url = `${RVI_API_BASE}${path}`;
  const start = performance.now();
  try {
    const response = await fetch(url);
    const elapsedMs = performance.now() - start;
    let body = null;
    try {
      body = await response.json();
    } catch (parseErr) {
      body = null;
    }
    return { ok: response.ok, status: response.status, body, elapsedMs, url };
  } catch (err) {
    const elapsedMs = performance.now() - start;
    return { ok: false, status: 0, body: null, error: err.message, elapsedMs, url };
  }
}
```

This mirrors the existing `API_BASE` computation already used in `web/app.js` (kept
identical so both pages resolve the API host the same way whether accessed via
`localhost`, `127.0.0.1`, or a LAN IP like `192.168.1.x`).

- [ ] **Step 2: Manual verification**

This file has no behavior to exercise on its own (it's a helper with no UI) — its
correctness is verified indirectly by Tasks 3 and 4, which are the first tasks that
actually call `rviFetch`. No standalone verification step here; do not skip ahead and
write a throwaway test page for it.

- [ ] **Step 3: Commit**

```bash
git add web/api-client.js
git commit -m "feat: add shared frontend API-client helper"
```

---

### Task 3: Main lookup page (search-first flow)

**Files:**
- Modify: `web/index.html` (full rewrite)
- Modify: `web/app.js` (full rewrite)

**Interfaces:**
- Consumes: `rviFetch(path)` from `web/api-client.js` (Task 2, must be loaded first via
  `<script>` tag).
- Consumes: `GET /public/v1/search` and `GET /public/v1/replacements` (already live from
  the phase-1 backend work — no backend changes needed here).

- [ ] **Step 1: Rewrite `web/index.html`**

Replace the entire contents of `web/index.html` with:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Parts Lookup</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>RV Interchange — Parts Lookup</h1>

  <form id="search-form">
    <input id="search-input" type="text" placeholder="Enter a part number, model, or SKU" autocomplete="off">
    <button type="submit">Search</button>
  </form>

  <div id="search-status"></div>
  <ul id="search-results" class="result-list"></ul>
  <div id="detail-view"></div>

  <script src="api-client.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

(`style.css` doesn't exist yet — it's created in Task 5. The page will render unstyled
until then; that's expected and fine for this task's verification, which only checks
behavior, not appearance.)

- [ ] **Step 2: Rewrite `web/app.js`**

Replace the entire contents of `web/app.js` with:

```javascript
const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const statusEl = document.getElementById("search-status");
const resultsEl = document.getElementById("search-results");
const detailEl = document.getElementById("detail-view");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  detailEl.innerHTML = "";
  resultsEl.innerHTML = "";

  if (!query) {
    statusEl.textContent = "";
    return;
  }

  statusEl.className = "";
  statusEl.textContent = "Searching...";

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/search?q=${encodeURIComponent(query)}&limit=20`);

  if (!ok) {
    statusEl.className = "error";
    statusEl.textContent = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "search failed"}`;
    return;
  }

  if (body.results.length === 0) {
    statusEl.className = "";
    statusEl.textContent = `No matches found for "${body.query}".`;
    return;
  }

  statusEl.className = "";
  statusEl.textContent =
    `${body.results.length} match${body.results.length === 1 ? "" : "es"} for "${body.query}"`;
  renderResults(body.results);
});

function renderResults(results) {
  resultsEl.innerHTML = "";
  for (const result of results) {
    const li = document.createElement("li");
    li.className = "result-card";

    const label = document.createElement("div");
    label.className = "result-label";
    label.textContent = result.label;
    li.appendChild(label);

    const idList = document.createElement("div");
    idList.className = "identifier-pills";
    for (const identifier of result.identifiers) {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = `${identifier.ns}: ${identifier.value}`;
      idList.appendChild(pill);
    }
    li.appendChild(idList);

    li.addEventListener("click", () => showDetail(result));
    resultsEl.appendChild(li);
  }
}

async function showDetail(result) {
  detailEl.innerHTML = "<p>Loading replacements...</p>";

  // Use the specific identifier that matched the search (result.label holds the
  // matched value — see api/services.py SearchService.search), not an arbitrary
  // identifier off the component.
  const matched = result.identifiers.find((i) => i.value === result.label)
    || result.identifiers[0];

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/replacements?ns=${encodeURIComponent(matched.ns)}` +
    `&identifier=${encodeURIComponent(matched.value)}`);

  if (!ok) {
    detailEl.innerHTML = "";
    const errEl = document.createElement("p");
    errEl.className = "error";
    errEl.textContent = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "lookup failed"}`;
    detailEl.appendChild(errEl);
    return;
  }

  renderDetail(body);
}

function renderDetail(data) {
  detailEl.innerHTML = "";

  const heading = document.createElement("h2");
  heading.textContent = `Replacements for ${data.source}`;
  detailEl.appendChild(heading);

  const tierOrder = ["Exact Match", "Direct Fit", "Fits With Modification"];
  const byTier = {};
  for (const item of data.replacements) {
    if (!byTier[item.fit]) byTier[item.fit] = [];
    byTier[item.fit].push(item);
  }

  for (const tier of tierOrder) {
    const items = byTier[tier];
    if (!items || items.length === 0) continue;

    const section = document.createElement("section");
    section.className = "tier-section";

    const tierHeading = document.createElement("h3");
    tierHeading.textContent = tier;
    section.appendChild(tierHeading);

    const list = document.createElement("ul");
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item.summary ? `${item.part} — ${item.summary}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }

  if (data.supersessions && data.supersessions.length > 0) {
    const section = document.createElement("section");
    section.className = "supersession-section";

    const heading2 = document.createElement("h3");
    heading2.textContent = "Superseded by";
    section.appendChild(heading2);

    const list = document.createElement("ul");
    for (const item of data.supersessions) {
      const li = document.createElement("li");
      li.textContent = item.note ? `${item.part} — ${item.note}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }
}
```

- [ ] **Step 3: Manual verification**

This requires the Docker stack running with real data (`Docs/Tools/components.db`
already populated per the Stage 2 Phase 1 work). From the repo root:

```bash
cd /data/DockerConfigs && docker compose up -d --build rvinterchange-api rvinterchange-web
```

Then in a browser, open `http://localhost:8485/` (or `http://<LAN-IP>:8485/` from
another device on the network) and verify:
- Searching `SW6` returns at least one result card (Suburban water heater fixture data).
- Clicking a result card shows a "Replacements for ..." heading with at least an
  "Exact Match" tier listing the part itself.
- Searching for a Coleman-Mach part known to have a `supersedes` edge (e.g. a retired
  endpoint model from the fixture data) shows a "Superseded by" section.
- Searching for garbage text (e.g. `zzzzz`) shows "No matches found" — not styled as an
  error.
- The page loads and works identically from a LAN IP, not just `localhost`.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: rewrite main page as search-first lookup flow"
```

---

### Task 4: Admin/debug page

**Files:**
- Create: `web/admin.html`
- Create: `web/admin.js`

**Interfaces:**
- Consumes: `rviFetch(path)` from `web/api-client.js` (Task 2).
- Consumes: `GET /public/v1/search`, `GET /public/v1/resolve`, `GET /public/v1/replacements`
  (existing), and `GET /debug/v1/logs` (Task 1).

- [ ] **Step 1: Create `web/admin.html`**

Create `web/admin.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RV Interchange — Admin</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>RV Interchange — Admin / Debug</h1>
  <p><a href="index.html">&larr; Back to lookup</a></p>

  <section class="admin-panel">
    <h2>Search</h2>
    <form id="search-form" class="raw-form">
      <label>q <input id="search-q" type="text" value="SW6DE"></label>
      <label>limit <input id="search-limit" type="number" value="20"></label>
      <button type="submit">Send</button>
    </form>
    <pre id="search-output">(nothing yet)</pre>
  </section>

  <section class="admin-panel">
    <h2>Resolve</h2>
    <form id="resolve-form" class="raw-form">
      <label>ns <input id="resolve-ns" type="text" value="suburban"></label>
      <label>identifier <input id="resolve-identifier" type="text" value="SW6DE"></label>
      <button type="submit">Send</button>
    </form>
    <pre id="resolve-output">(nothing yet)</pre>
  </section>

  <section class="admin-panel">
    <h2>Replacements</h2>
    <form id="replacements-form" class="raw-form">
      <label>ns <input id="replacements-ns" type="text" value="suburban"></label>
      <label>identifier <input id="replacements-identifier" type="text" value="SW6DE"></label>
      <button type="submit">Send</button>
    </form>
    <pre id="replacements-output">(nothing yet)</pre>
  </section>

  <section class="admin-panel">
    <h2>Recent log lines</h2>
    <button id="logs-refresh">Refresh</button>
    <pre id="logs-output">(not loaded yet)</pre>
  </section>

  <script src="api-client.js"></script>
  <script src="admin.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `web/admin.js`**

Create `web/admin.js`:

```javascript
function wireRawForm(formId, outputId, buildPath) {
  const form = document.getElementById(formId);
  const output = document.getElementById(outputId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    output.className = "";
    output.textContent = "Loading...";

    const path = buildPath();
    const { ok, status, body, error, elapsedMs, url } = await rviFetch(path);

    const header = error
      ? `Request failed: ${error} (${url})`
      : `HTTP ${status} — ${elapsedMs.toFixed(1)}ms — ${url}`;
    output.className = ok ? "" : "error";
    output.textContent = `${header}\n\n${JSON.stringify(body, null, 2)}`;
  });
}

wireRawForm("search-form", "search-output", () => {
  const q = document.getElementById("search-q").value;
  const limit = document.getElementById("search-limit").value;
  return `/public/v1/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`;
});

wireRawForm("resolve-form", "resolve-output", () => {
  const ns = document.getElementById("resolve-ns").value;
  const identifier = document.getElementById("resolve-identifier").value;
  return `/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;
});

wireRawForm("replacements-form", "replacements-output", () => {
  const ns = document.getElementById("replacements-ns").value;
  const identifier = document.getElementById("replacements-identifier").value;
  return `/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;
});

async function loadLogs() {
  const output = document.getElementById("logs-output");
  output.className = "";
  output.textContent = "Loading...";

  const { ok, status, body, error } = await rviFetch("/debug/v1/logs?lines=100");

  if (!ok) {
    output.className = "error";
    output.textContent = error ? `Request failed: ${error}` : `HTTP ${status}`;
    return;
  }

  output.textContent = body.lines.length > 0 ? body.lines.join("\n") : "(no log lines yet)";
}

document.getElementById("logs-refresh").addEventListener("click", loadLogs);
loadLogs();
```

- [ ] **Step 3: Manual verification**

With the Docker stack running (from Task 3's Step 3), open
`http://localhost:8485/admin.html` and verify:
- The Search/Resolve/Replacements forms, submitted with their prefilled default values,
  each show a raw JSON response, HTTP status, and elapsed time.
- Changing an input (e.g. `identifier` to a value that doesn't exist) and resubmitting
  shows a 404 with the `error`-styled output.
- The log panel loads on page load and shows recent lines (it will include the requests
  you just made via the forms above, and your `/admin.html`-triggered log fetches
  themselves once you refresh again).
- Clicking "Refresh" on the log panel re-fetches and updates it.
- "&larr; Back to lookup" navigates to the main page.

- [ ] **Step 4: Commit**

```bash
git add web/admin.html web/admin.js
git commit -m "feat: add admin/debug page with raw requests and log tail"
```

---

### Task 5: Shared stylesheet + Docker wiring

**Files:**
- Create: `web/style.css`
- Modify: `web/Dockerfile`

**Interfaces:**
- None — this is the final integration task. Both HTML files already reference
  `style.css` (Tasks 3 and 4); this task creates the file they're pointing at and makes
  sure the Docker image actually ships it.

- [ ] **Step 1: Create `web/style.css`**

Create `web/style.css`:

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

#search-form input#search-input {
  flex: 1;
  min-width: 16rem;
}

.result-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.result-card {
  border: 1px solid #ccc;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
}

.result-card:hover {
  background: #f5f5f5;
}

.result-label {
  font-weight: bold;
  font-size: 1.05rem;
}

.identifier-pills {
  margin-top: 0.4rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.pill {
  background: #eee;
  border-radius: 999px;
  padding: 0.15rem 0.6rem;
  font-size: 0.8rem;
}

.tier-section,
.supersession-section {
  border-left: 3px solid #ccc;
  padding-left: 1rem;
  margin-top: 1rem;
}

.supersession-section {
  border-left-color: #b8860b;
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
```

- [ ] **Step 2: Update `web/Dockerfile`**

Replace the entire contents of `web/Dockerfile` with:

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
COPY admin.html /usr/share/nginx/html/admin.html
COPY admin.js /usr/share/nginx/html/admin.js
COPY api-client.js /usr/share/nginx/html/api-client.js
COPY style.css /usr/share/nginx/html/style.css
EXPOSE 80
```

- [ ] **Step 3: Full manual verification**

Rebuild and restart both containers so the new Dockerfile and all files take effect:

```bash
cd /data/DockerConfigs && docker compose up -d --build rvinterchange-api rvinterchange-web
```

Then, in a browser:
- Open `http://localhost:8485/` — confirm the styling from Task 1's checklist now
  actually renders (card borders, pill badges, spacing) instead of being unstyled.
- Repeat the Task 3 Step 3 checklist (search, click a result, supersession display,
  no-match state) and confirm it all still works with styling applied.
- Open `http://localhost:8485/admin.html` — confirm styling applies there too, and
  repeat the Task 4 Step 3 checklist.
- From another device on the LAN (or by using the host's `192.168.1.x` address instead
  of `localhost`), load both pages again and confirm they work identically.

- [ ] **Step 4: Run the full backend suite one more time**

Run: `python3 -m pytest tests/ -q`
Expected: all tests pass (this task touches no Python, but this is the final task in the
plan — confirm nothing drifted).

- [ ] **Step 5: Commit**

```bash
git add web/style.css web/Dockerfile
git commit -m "feat: add shared stylesheet and wire it into the Docker image"
```

---

## Definition of done

- [ ] `web/index.html` is a search-first lookup page: search → result cards → detail
  view with tiered replacements and (when present) a supersessions section.
- [ ] `web/admin.html` exposes raw search/resolve/replacements requests and a
  manually-refreshable log tail.
- [ ] `GET /debug/v1/logs` exists, is bounded (`1-1000` lines), and handles a missing log
  file gracefully (`200` with `{"lines": []}`, not a `404`/`500`).
- [ ] Both pages work from `localhost` and from a LAN IP (e.g. `192.168.1.x`), with no
  CORS changes required.
- [ ] No authentication was added anywhere.
- [ ] `python3 -m pytest tests/ -q` is green.
- [ ] `/public/v1/compare`, `/public/v1/interchange/{code}`, any branding/design-system
  work, auto-refreshing logs, and public deployment changes remain explicitly out of
  scope (phase 3, a separate future spec).
