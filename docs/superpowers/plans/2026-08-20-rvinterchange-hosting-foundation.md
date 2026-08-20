# RV Interchange Hosting Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the existing RV Interchange lookup at `https://rvinterchange.com` from the local Docker host through Cloudflare Tunnel, isolate the review/debug surface behind Cloudflare Access, and establish domain email without exposing the API or host ports publicly.

**Architecture:** A repository-owned Compose project runs the read-only FastAPI catalog, a public Nginx proxy/static site, a separate review/debug Nginx site, and a remotely managed `cloudflared` connector. The browser uses same-origin `/public/v1/*` requests; only the public and review proxies can reach the API over a private Docker network. Cloudflare Email Routing forwards human `contact@` mail to an account-level verified destination kept out of Git; paid arbitrary-recipient transactional sending is deferred to the submission-intake plan.

**Tech Stack:** Python 3.12, FastAPI 0.136.3, Pydantic 2.13.4, Uvicorn 0.49.0, Nginx Alpine, Docker Compose v2, cloudflared 2026.7.2, Cloudflare DNS/Tunnel/Access/Email Routing.

**Spec:** `docs/superpowers/specs/2026-08-20-public-submission-queue-design.md`

## Global Constraints

- Keep `Docs/Tools/observations.db` append-only and keep `Docs/Tools/components.db` a derived, rebuildable read model.
- The catalog API receives read-only access to `Docs/Tools`; no hosting task may add a write endpoint.
- Public traffic may reach only `/`, static assets, `/public/v1/*`, and `/health/`; public `/debug/v1/*`, `/review/v1/*`, `/docs`, `/redoc`, `/openapi.json`, and admin assets must return `404`.
- The review hostname is deny-by-default in Cloudflare Access. Application-level Access JWT validation belongs to the later moderation plan; until then this plan exposes only the existing read/debug page behind Access.
- No public router port forwarding. Production host bindings are loopback-only diagnostics; Cloudflare Tunnel uses the private Docker network.
- Secrets stay outside Git. Never print, log, commit, or place the tunnel token, Cloudflare API token, Google credentials, or Access session values in command history examples.
- The first hosting release does not expose the unfinished submission API. `/submission/v1/*` returns a controlled `503` JSON response until the intake plan replaces it.
- Do not add public PDF upload, submission forms, or reviewer workflow UI in this plan.
- Preserve the unrelated untracked `Docs/Data/Fleetwood/` directory.
- `/data/DockerConfigs` is a mixed, dirty worktree. Modify only the two RV Interchange service blocks and the RV environment example line. Do not stage or commit that repository without separate explicit authorization and a reviewed full diff.
- Commit steps in this document are execution instructions, not current authorization. Before each commit, inspect staged and unstaged diffs and stage only the named RV Interchange paths.
- Use Cloudflare Email Routing for inbound `contact@` and DMARC reports. Keep the verified destination address out of Git and keep catch-all routing disabled.
- Arbitrary-recipient Cloudflare Email Sending requires Workers Paid and is not authorized by this hosting plan. Domain onboarding, credentials, application mail code, templates, and delivery tests belong to the submission-intake plan.

## File Structure

### Repository-owned files

- `api/main.py` — catalog routes plus a dependency-free liveness/readiness endpoint; no public writes.
- `tests/api/test_main.py` — health and same-origin/CORS boundary tests.
- `web/nginx.conf` — public static serving, same-origin catalog proxy, controlled intake-unavailable response, security headers, and denied internal routes.
- `web/page-init.js` — shared header/footer initialization moved out of inline scripts so the public CSP can disallow inline JavaScript.
- `web/api-client.js` — same-origin API URL construction.
- `web/Dockerfile` — public image only; it must not contain admin assets.
- `web/contact.html`, `web/how-it-works.html` — use `page-init.js` instead of inline scripts.
- `review/index.html`, `review/admin.js` — existing admin/debug interface moved out of the public web source set.
- `review/nginx.conf` — private review/debug proxy and static serving.
- `review/Dockerfile` — separate review image.
- `tests/web/test_hosting_boundary.py` — static assertions for public/review image separation, same-origin requests, CSP, and proxy allowlists.
- `deploy/docker-compose.yaml` — repository-owned local production stack.
- `tests/deploy/test_compose_contract.py` — rendered Compose contract assertions.
- `docs/operations/rvinterchange-local-hosting.md` — DNS, tunnel, Access, email, deployment, health, backup boundary, cutover, and rollback runbook.
- `README.md` — public URL, local diagnostics, and operations-document pointer.

### Local operations files outside this repository

- `/data/DockerConfigs/docker-compose.yaml` — mark the existing RV services with profile `rvinterchange-legacy`; preserve them as rollback definitions.
- `/data/DockerConfigs/.env.example` — add the empty key name `RVINTERCHANGE_TUNNEL_TOKEN=` only.
- `/data/DockerConfigs/.env` — operator places the real token here; never read or display its contents during implementation.
- `/data/DockerConfigs/RVInterchange/logs/` — existing API logs.
- `/data/DockerConfigs/RVInterchange/backups/` — reserved for later intake/canonical backup automation.

---

### Task 0: Align stale registry tests with the shipped catalog

**Files:**
- Modify: `tests/api/test_main.py`
- Modify: `tests/api/test_services.py`
- Modify: `tests/tools/test_manufacturers.py`
- Modify: `tests/tools/test_part_types.py`

**Interfaces:**
- Consumes: canonical `MANUFACTURERS` and `PART_TYPES` registries already shipped on `main`.
- Produces: a clean baseline whose tests recognize Furrion, Girard, and Lippert manufacturers plus the Furrion and Girard water-heater part types.

- [ ] **Step 1: Preserve the failing baseline as RED evidence**

Use the controller-recorded baseline run:

```bash
python3 -m pytest tests/ Docs/Tools -q
```

Expected before this task: 4 failures and 52 passes. The failures are the two coverage manufacturer sets, the shipped-manufacturer registry set, and the exported part-type constant set.

- [ ] **Step 2: Update manufacturer expectations**

In both API coverage tests, include `Furrion`, `Girard`, and `Lippert` alongside the original four display names. In `tests/tools/test_manufacturers.py`, rename the four-vendor test so it describes all shipped vendors, include namespaces `furrion`, `girard`, and `lippert`, and add their exact display-name assertions.

- [ ] **Step 3: Update exported part-type expectations**

Import `FURRION_PART_TYPE` and `GIRARD_PART_TYPE` from `part_types` in `tests/tools/test_part_types.py`, then include both constants in `exported_ids`. Do not duplicate numeric IDs in the test; the registry remains the source of those values.

- [ ] **Step 4: Run focused tests**

```bash
python3 -m pytest tests/api/test_main.py::test_coverage_endpoint tests/api/test_services.py::test_get_coverage_lists_every_known_manufacturer_even_with_no_data tests/tools/test_manufacturers.py tests/tools/test_part_types.py -v
```

Expected: all selected tests pass with pristine output.

- [ ] **Step 5: Run the full baseline**

```bash
python3 -m pytest tests/ Docs/Tools -q
```

Expected: 56 tests pass with no failures or warnings.

- [ ] **Step 6: Commit the baseline correction**

```bash
git add -- tests/api/test_main.py tests/api/test_services.py tests/tools/test_manufacturers.py tests/tools/test_part_types.py
git diff --cached --check
git commit -m "test: align registry expectations with shipped catalog"
```

---

### Task 1: Add an explicit catalog health endpoint and remove cross-origin browser access

**Files:**
- Modify: `api/main.py:18-54,87-123`
- Modify: `tests/api/test_main.py`
- Modify: `README.md:116-128`

**Interfaces:**
- Consumes: existing FastAPI `app` and read-only `DB_PATH`.
- Produces: `GET /health/ -> {"status": "ok"}` and a same-origin-only API with no CORS middleware.

- [ ] **Step 1: Write failing health and CORS-boundary tests**

Add to `tests/api/test_main.py`:

```python
def test_health_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cross_origin_preflight_is_not_enabled(client):
    response = client.options(
        "/public/v1/search",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 405
    assert "access-control-allow-origin" not in response.headers
```

- [ ] **Step 2: Run the focused tests and confirm the contract is absent**

Run:

```bash
python3 -m pytest tests/api/test_main.py::test_health_endpoint tests/api/test_main.py::test_cross_origin_preflight_is_not_enabled -v
```

Expected: the health test fails with `404`; the preflight test fails because the existing CORS middleware answers the request.

- [ ] **Step 3: Implement the health route and remove CORS middleware**

In `api/main.py`:

1. Remove `from fastapi.middleware.cors import CORSMiddleware`.
2. Remove the complete `app.add_middleware(CORSMiddleware, ...)` block.
3. Add this route immediately before the public catalog routes:

```python
@app.get("/health/")
def health():
    return {"status": "ok"}
```

Do not open the database from this endpoint. Container liveness must not fail merely because a rebuild temporarily swaps the read model; catalog behavior remains covered by the persisted-database tests.

- [ ] **Step 4: Update API documentation**

In the README endpoint list, add:

```markdown
- `GET /health/` — container/proxy health check; returns `{"status":"ok"}`.
```

Replace the old cross-origin test-site wording with one sentence stating that browser callers use the same origin through Nginx and the FastAPI service does not enable CORS.

- [ ] **Step 5: Run API tests**

Run:

```bash
python3 -m pytest tests/api/test_main.py tests/api/test_e2e.py -v
```

Expected: all tests pass, including the new health and preflight assertions.

- [ ] **Step 6: Commit the API boundary change after explicit commit authorization**

```bash
git add -- api/main.py tests/api/test_main.py README.md
git diff --cached --check
git commit -m "feat: add same-origin hosting health boundary"
```

### Task 2: Build the same-origin public Nginx image

**Files:**
- Create: `web/nginx.conf`
- Create: `web/page-init.js`
- Modify: `web/api-client.js:1-5`
- Modify: `web/contact.html:8-20`
- Modify: `web/how-it-works.html:8-20`
- Modify: `web/Dockerfile`
- Create: `tests/web/test_hosting_boundary.py`

**Interfaces:**
- Consumes: catalog API routes `/public/v1/*` and health route `/health/` from Task 1.
- Produces: a public image that serves static assets, proxies only approved API paths, returns controlled `503` for the not-yet-built intake API, contains no admin files, and executes no inline JavaScript.

- [ ] **Step 1: Write failing static boundary tests**

Create `tests/web/test_hosting_boundary.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_browser_api_client_uses_same_origin():
    source = read("web/api-client.js")
    assert ":8484" not in source
    assert "window.location.origin" in source


def test_public_image_excludes_admin_assets():
    dockerfile = read("web/Dockerfile")
    assert "admin.html" not in dockerfile
    assert "admin.js" not in dockerfile


def test_public_nginx_has_an_explicit_proxy_allowlist():
    config = read("web/nginx.conf")
    assert "location ^~ /public/v1/" in config
    assert "location ^~ /submission/v1/" in config
    assert "return 503" in config
    for private_path in ("/debug/", "/review/", "/docs", "/redoc", "/openapi.json"):
        assert private_path in config


def test_public_pages_have_no_inline_scripts():
    for name in ("contact.html", "how-it-works.html"):
        html = read(f"web/{name}")
        assert "<script>" not in html
        assert '<script src="page-init.js"></script>' in html


def test_public_csp_disallows_inline_script():
    config = read("web/nginx.conf")
    csp_line = next(line for line in config.splitlines() if "Content-Security-Policy" in line)
    assert "script-src 'self'" in csp_line
    assert "'unsafe-inline'" not in csp_line
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/web/test_hosting_boundary.py -v
```

Expected: failures for missing `web/nginx.conf`, the hard-coded `:8484`, public admin copies, and inline scripts.

- [ ] **Step 3: Make the browser API client same-origin**

Replace the first line of `web/api-client.js` with:

```javascript
const RVI_API_BASE = window.location.origin;
```

Keep `rviFetch(path)` and every caller path unchanged.

- [ ] **Step 4: Move shared page initialization out of inline scripts**

Create `web/page-init.js`:

```javascript
const activeNav = document.body.dataset.activeNav || undefined;
const headerSlot = document.getElementById("header-slot");
const footerSlot = document.getElementById("footer-slot");

if (headerSlot) {
  headerSlot.replaceWith(renderHeader(activeNav));
}
if (footerSlot) {
  footerSlot.replaceWith(renderFooter());
}
```

In `web/how-it-works.html`, set `<body class="public-page" data-active-nav="how-it-works">`, delete the inline `<script>...</script>`, and add `<script src="page-init.js"></script>` after `chrome.js`.

In `web/contact.html`, leave the body without an active navigation value, delete the inline `<script>...</script>`, and add `<script src="page-init.js"></script>` after `chrome.js`.

- [ ] **Step 5: Create the public Nginx configuration**

Create `web/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    server_tokens off;

    root /usr/share/nginx/html;
    index index.html;

    add_header Content-Security-Policy "default-src 'self'; base-uri 'none'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Permissions-Policy "camera=(), geolocation=(), microphone=()" always;
    add_header X-Frame-Options "DENY" always;

    location = /health/ {
        proxy_pass http://rvinterchange-api:8484/health/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location ^~ /public/v1/ {
        proxy_pass http://rvinterchange-api:8484;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location ^~ /submission/v1/ {
        default_type application/json;
        return 503 '{"detail":"submission intake is not available yet"}';
    }

    location ^~ /debug/ { return 404; }
    location ^~ /review/ { return 404; }
    location = /docs { return 404; }
    location = /redoc { return 404; }
    location = /openapi.json { return 404; }
    location = /admin.html { return 404; }
    location = /admin.js { return 404; }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

- [ ] **Step 6: Update the public Dockerfile**

Add these copy lines:

```dockerfile
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY page-init.js /usr/share/nginx/html/page-init.js
```

Delete the `COPY admin.html ...` and `COPY admin.js ...` lines. Keep every other currently shipped public asset.

- [ ] **Step 7: Run static tests and validate the Nginx image**

Run:

```bash
python3 -m pytest tests/web/test_hosting_boundary.py -v
docker build -f web/Dockerfile -t rvinterchange-web:hosting-test web
docker run --rm rvinterchange-web:hosting-test nginx -t
```

Expected: tests pass; `nginx -t` reports syntax and configuration successful.

- [ ] **Step 8: Commit the public proxy change after explicit commit authorization**

```bash
git add -- web/nginx.conf web/page-init.js web/api-client.js web/contact.html web/how-it-works.html web/Dockerfile tests/web/test_hosting_boundary.py
git diff --cached --check
git commit -m "feat: add same-origin public web proxy"
```

### Task 3: Separate the review/debug image from the public site

**Files:**
- Move: `web/admin.html` -> `review/index.html`
- Move: `web/admin.js` -> `review/admin.js`
- Create: `review/nginx.conf`
- Create: `review/Dockerfile`
- Modify: `tests/web/test_hosting_boundary.py`

**Interfaces:**
- Consumes: `web/api-client.js`, `web/style.css`, catalog `/public/v1/*`, debug `/debug/v1/*`, and Cloudflare Access at the review hostname.
- Produces: a standalone review/debug image on port 80 that proxies public reads and debug logs but does not expose FastAPI documentation or future moderation paths publicly.

- [ ] **Step 1: Extend the failing boundary tests**

Append to `tests/web/test_hosting_boundary.py`:

```python
def test_review_image_owns_admin_assets():
    dockerfile = read("review/Dockerfile")
    copy_sources = {
        line.split()[1] for line in dockerfile.splitlines()
        if line.startswith("COPY ")
    }
    assert copy_sources == {
        "review/nginx.conf",
        "review/index.html",
        "review/admin.js",
        "web/api-client.js",
        "web/style.css",
    }
    assert not (ROOT / "web/admin.html").exists()
    assert not (ROOT / "web/admin.js").exists()


def test_review_proxy_exposes_only_existing_debug_contract():
    config = read("review/nginx.conf")
    blocks = location_blocks(config)
    proxied = {name for name, body in blocks.items() if "proxy_pass" in body}
    assert proxied == {
        "= /public/v1/search",
        "= /public/v1/resolve",
        "= /public/v1/replacements",
        "= /debug/v1/logs",
    }
    assert "return 503" in blocks["^~ /review/v1/"]
    for denied in ("^~ /submission/v1/", "= /docs", "= /redoc", "= /openapi.json", "/"):
        assert "proxy_pass" not in blocks[denied]
```

- [ ] **Step 2: Run the focused tests and confirm the review image is missing**

Run:

```bash
python3 -m pytest tests/web/test_hosting_boundary.py -v
```

Expected: the new review tests fail because `review/Dockerfile` and `review/nginx.conf` do not exist.

- [ ] **Step 3: Move the admin sources**

Use repository-aware moves:

```bash
mkdir -p review
git mv web/admin.html review/index.html
git mv web/admin.js review/admin.js
```

The moved `review/index.html` already references `api-client.js`, `admin.js`, and `style.css`; the review image supplies those exact names.

Change its `Back to lookup` link from the old same-directory `index.html` target to the canonical public URL `https://rvinterchange.com/`. After the move, a relative `index.html` target would reload the review page itself.

- [ ] **Step 4: Create the review Nginx configuration**

Create `review/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    server_tokens off;

    root /usr/share/nginx/html;
    index index.html;

    add_header Content-Security-Policy "default-src 'self'; base-uri 'none'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self'" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Permissions-Policy "camera=(), geolocation=(), microphone=()" always;
    add_header X-Frame-Options "DENY" always;

    location = /health/ {
        default_type application/json;
        return 200 '{"status":"ok"}';
    }

    location = /public/v1/search {
        proxy_pass http://rvinterchange-api:8484;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location = /public/v1/resolve {
        proxy_pass http://rvinterchange-api:8484;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location = /public/v1/replacements {
        proxy_pass http://rvinterchange-api:8484;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location = /debug/v1/logs {
        proxy_pass http://rvinterchange-api:8484;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }

    location ^~ /review/v1/ {
        default_type application/json;
        return 503 '{"detail":"moderation API is not available yet"}';
    }

    location ^~ /submission/v1/ { return 404; }

    location = /docs { return 404; }
    location = /redoc { return 404; }
    location = /openapi.json { return 404; }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

- [ ] **Step 5: Create the review Dockerfile**

Create `review/Dockerfile` with repository root as its build context:

```dockerfile
FROM nginx:alpine
COPY review/nginx.conf /etc/nginx/conf.d/default.conf
COPY review/index.html /usr/share/nginx/html/index.html
COPY review/admin.js /usr/share/nginx/html/admin.js
COPY web/api-client.js /usr/share/nginx/html/api-client.js
COPY web/style.css /usr/share/nginx/html/style.css
EXPOSE 80
```

- [ ] **Step 6: Run tests and validate both images**

Run:

```bash
python3 -m pytest tests/web/test_hosting_boundary.py -v
docker build -f web/Dockerfile -t rvinterchange-web:hosting-test web
docker build -f review/Dockerfile -t rvinterchange-review:hosting-test .
docker run --rm rvinterchange-web:hosting-test nginx -t
docker run --rm rvinterchange-review:hosting-test nginx -t
```

Expected: all tests pass and both Nginx configurations validate.

- [ ] **Step 7: Commit the review image separation after explicit commit authorization**

```bash
git add -- review/index.html review/admin.js review/nginx.conf review/Dockerfile web/admin.html web/admin.js tests/web/test_hosting_boundary.py
git diff --cached --check
git commit -m "feat: isolate review debug interface"
```

### Task 4: Add the repository-owned production Compose project

**Files:**
- Create: `deploy/docker-compose.yaml`
- Create: `tests/deploy/test_compose_contract.py`
- Modify outside repo: `/data/DockerConfigs/docker-compose.yaml:607-641`
- Modify outside repo: `/data/DockerConfigs/.env.example`

**Interfaces:**
- Consumes: API/public/review images from Tasks 1-3, `Docs/Tools` read-only data, `/data/DockerConfigs/RVInterchange/logs`, and environment key `RVINTERCHANGE_TUNNEL_TOKEN`.
- Produces: Compose project `rvinterchange` with private service networking, loopback-only diagnostics, health ordering, a tunnel profile, and a reversible legacy profile in the shared stack.

- [ ] **Step 1: Write the failing rendered-Compose contract test**

Create `tests/deploy/test_compose_contract.py`:

```python
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy" / "docker-compose.yaml"


def rendered_compose(*profiles):
    if shutil.which("docker") is None:
        pytest.skip("docker compose is required for the deployment contract test")
    env = os.environ.copy()
    env.pop("COMPOSE_PROFILES", None)
    env["RVINTERCHANGE_TUNNEL_TOKEN"] = "test-token"
    command = ["docker", "compose", "-f", str(COMPOSE)]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["config", "--format", "json"])
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(result.stdout)


def test_production_compose_network_and_mount_boundaries():
    default_config = rendered_compose()
    assert set(default_config["services"]) == {
        "rvinterchange-api",
        "rvinterchange-review",
        "rvinterchange-web",
    }

    config = rendered_compose("tunnel")
    services = config["services"]
    assert set(services) == {
        "rvinterchange-api",
        "rvinterchange-cloudflared",
        "rvinterchange-review",
        "rvinterchange-web",
    }
    assert "ports" not in services["rvinterchange-api"]
    assert services["rvinterchange-web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert services["rvinterchange-review"]["ports"][0]["host_ip"] == "127.0.0.1"
    tool_mount = next(
        mount for mount in services["rvinterchange-api"]["volumes"]
        if mount["target"] == "/app/Docs/Tools"
    )
    assert tool_mount["read_only"] is True
    assert services["rvinterchange-cloudflared"]["profiles"] == ["tunnel"]
```

- [ ] **Step 2: Run the test and confirm the deployment file is absent**

Run:

```bash
python3 -m pytest tests/deploy/test_compose_contract.py -v
```

Expected: failure because `deploy/docker-compose.yaml` does not exist.

- [ ] **Step 3: Create the production Compose file**

Create `deploy/docker-compose.yaml`:

```yaml
name: rvinterchange

services:
  rvinterchange-api:
    container_name: rvinterchange-api
    build:
      context: ..
      dockerfile: api/Dockerfile
    image: rvinterchange-api:latest
    restart: unless-stopped
    environment:
      TZ: America/New_York
      RVI_LOG_DIR: /app/logs
    volumes:
      - ../Docs/Tools:/app/Docs/Tools:ro
      - /data/DockerConfigs/RVInterchange/logs:/app/logs
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8484/health/')"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3

  rvinterchange-web:
    container_name: rvinterchange-web
    build:
      context: ../web
      dockerfile: Dockerfile
    image: rvinterchange-web:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8485:80"
    depends_on:
      rvinterchange-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1/health/"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3

  rvinterchange-review:
    container_name: rvinterchange-review
    build:
      context: ..
      dockerfile: review/Dockerfile
    image: rvinterchange-review:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8486:80"
    depends_on:
      rvinterchange-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1/health/"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3

  rvinterchange-cloudflared:
    container_name: rvinterchange-cloudflared
    image: cloudflare/cloudflared:2026.7.2
    restart: unless-stopped
    profiles: ["tunnel"]
    command: ["tunnel", "--no-autoupdate", "run"]
    environment:
      TUNNEL_TOKEN: ${RVINTERCHANGE_TUNNEL_TOKEN:-}
    depends_on:
      rvinterchange-web:
        condition: service_healthy
      rvinterchange-review:
        condition: service_healthy
```

The tunnel service intentionally fails rather than creating an unauthenticated tunnel when the `tunnel` profile is started without a real token.

- [ ] **Step 4: Render and test the repository-owned Compose project**

Run:

```bash
RVINTERCHANGE_TUNNEL_TOKEN=test-token docker compose -f deploy/docker-compose.yaml config --quiet
RVINTERCHANGE_TUNNEL_TOKEN=test-token docker compose -f deploy/docker-compose.yaml --profile tunnel config --quiet
python3 -m pytest tests/deploy/test_compose_contract.py -v
```

Expected: both the default and tunnel-profile views render successfully. The default view omits `rvinterchange-cloudflared`, the tunnel view includes it, and the contract test passes.

- [ ] **Step 5: Put the old shared-stack services behind a rollback profile**

In `/data/DockerConfigs/docker-compose.yaml`, add this exact property under both existing `rvinterchange-api` and `rvinterchange-web` service names:

```yaml
    profiles: ["rvinterchange-legacy"]
```

Do not alter any other service or reformat the shared file. Validate both ordinary and rollback renders:

```bash
docker compose -f /data/DockerConfigs/docker-compose.yaml config --quiet
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy config --services
```

Expected: the ordinary shared-stack service list omits RV Interchange; the rollback-profile list includes `rvinterchange-api` and `rvinterchange-web`.

- [ ] **Step 6: Document the environment key without reading the real environment**

Append this one line to `/data/DockerConfigs/.env.example` if it is not already present:

```dotenv
RVINTERCHANGE_TUNNEL_TOKEN=
```

Do not open or print `/data/DockerConfigs/.env`. The operator adds the real token through a local editor or Cloudflare's displayed Docker command, then verifies only that the variable name is populated without echoing its value.

- [ ] **Step 7: Commit only the repository-owned deployment contract after explicit authorization**

```bash
git add -- deploy/docker-compose.yaml tests/deploy/test_compose_contract.py
git diff --cached --check
git commit -m "feat: add local production compose project"
```

Do not stage or commit `/data/DockerConfigs`; report its two targeted uncommitted changes separately.

### Task 5: Establish Cloudflare inbound contact routing

**Files:**
- Create: `docs/operations/rvinterchange-local-hosting.md` (email sections first; later tasks extend the same file)

**Interfaces:**
- Consumes: Cloudflare-managed DNS for `rvinterchange.com` and one existing verified account-level destination address supplied to the executor out of band and never written to Git.
- Produces: working inbound routes for `contact@rvinterchange.com` and `dmarc-reports@rvinterchange.com`, disabled catch-all routing, and reporting-only DMARC. It does not produce branded outbound mail.

- [ ] **Step 1: Verify the existing routing prerequisites without mutation**

Run:

```bash
wrangler whoami
wrangler email routing addresses list
wrangler email routing rules list rvinterchange.com
wrangler email routing dns get rvinterchange.com
dig +short TXT _dmarc.rvinterchange.com
```

Require all of these conditions before mutation:

- the authenticated Cloudflare account owns the zone;
- exactly one intended destination is already verified;
- no conflicting custom rule exists for either routed address;
- catch-all is disabled;
- Cloudflare's root routing MX, SPF, and DKIM records are active.

- [ ] **Step 2: Create the two exact forwarding rules**

The controller supplies the verified destination address only in the execution task prompt. Set it in the executor process as `RVI_EMAIL_DESTINATION`; do not echo it, add it to a file, or include it in the operations guide. Create only these literal-recipient rules:

```bash
wrangler email routing rules create rvinterchange.com \
  --name "RV Interchange contact" \
  --match-type literal --match-field to \
  --match-value contact@rvinterchange.com \
  --action-type forward --action-value "$RVI_EMAIL_DESTINATION"

wrangler email routing rules create rvinterchange.com \
  --name "RV Interchange DMARC reports" \
  --match-type literal --match-field to \
  --match-value dmarc-reports@rvinterchange.com \
  --action-type forward --action-value "$RVI_EMAIL_DESTINATION"

unset RVI_EMAIL_DESTINATION
```

List the rules afterward. Require exactly those two enabled custom rules and a disabled catch-all. Do not create a wildcard rule.

- [ ] **Step 3: Add reporting-only DMARC**

Ensure there is exactly one DMARC TXT record at `_dmarc`. If one exists, update it rather than publishing a duplicate. Its value must be:

```text
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:dmarc-reports@rvinterchange.com; adkim=s; aspf=s
```

Do not move to `quarantine` during this plan. The operations guide records that enforcement changes only after every active sender passes alignment checks in DMARC reports.

- [ ] **Step 4: Verify DNS and inbound forwarding**

Run read-only DNS checks:

```bash
dig +short MX rvinterchange.com
dig +short TXT rvinterchange.com
dig +short TXT cf2024-1._domainkey.rvinterchange.com
dig +short TXT _dmarc.rvinterchange.com
```

Send one message from an unrelated mailbox to `contact@rvinterchange.com` and one to `dmarc-reports@rvinterchange.com`. Confirm both arrive at the verified destination. Send one message to a random, unconfigured address at the domain and confirm catch-all does not forward it.

Do not claim that replies originate from `contact@`. Cloudflare Email Routing is inbound forwarding, not a branded mailbox. Outbound transactional testing is intentionally deferred.

- [ ] **Step 5: Record the non-secret email configuration**

Create `docs/operations/rvinterchange-local-hosting.md` with:

- Routed public address names, without the private destination address.
- The presence and purpose of Cloudflare root routing MX, SPF, and DKIM.
- The disabled catch-all policy.
- DMARC reporting policy and enforcement gate.
- A statement that the verified destination, provider tokens, and generated DNS values are intentionally excluded.
- Date and result of both inbound forwarding tests and the catch-all rejection test.
- The limitation that replies may expose the personal destination until a branded outbound service is added.
- The gate that arbitrary-recipient Cloudflare Email Sending requires explicit Workers Paid authorization in the submission-intake plan.

- [ ] **Step 6: Commit the initial operations guide after explicit authorization**

```bash
git add -- docs/operations/rvinterchange-local-hosting.md
git diff --cached --check
git commit -m "docs: record RV Interchange email foundation"
```

### Task 6: Create the Cloudflare Tunnel, public routes, and review Access policy

**Files:**
- Modify: `docs/operations/rvinterchange-local-hosting.md`
- Local secret modification: `/data/DockerConfigs/.env` (operator-only; never read back or commit)

**Interfaces:**
- Consumes: repository Compose stack from Task 4, Cloudflare-managed DNS, and the verified `contact@rvinterchange.com` forwarding route from Task 5.
- Produces: `rvinterchange.com` and `review.rvinterchange.com` tunnel routes, canonical `www` redirect, and deny-by-default Access protection on the review hostname.

- [ ] **Step 1: Build and start the local stack without the tunnel**

Run:

```bash
docker compose -f deploy/docker-compose.yaml build rvinterchange-api rvinterchange-web rvinterchange-review
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy stop rvinterchange-api rvinterchange-web
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy rm -f rvinterchange-api rvinterchange-web
docker compose -f deploy/docker-compose.yaml up -d rvinterchange-api rvinterchange-web rvinterchange-review
docker compose -f deploy/docker-compose.yaml ps
```

Expected: all three repository-owned services become healthy; no tunnel service starts because its profile is inactive.

- [ ] **Step 2: Verify loopback-only behavior before public routing**

Run:

```bash
curl -fsS http://127.0.0.1:8485/health/
curl -fsS "http://127.0.0.1:8485/public/v1/search?q=SW6DE&limit=1"
curl -fsS http://127.0.0.1:8486/health/
ss -ltnp
```

Expected: both health checks return `{"status":"ok"}`; search returns JSON; ports `8485` and `8486` listen only on `127.0.0.1`; port `8484` has no host listener.

- [ ] **Step 3: Create a remotely managed tunnel**

In Cloudflare Dashboard, create a remotely managed tunnel named `rvinterchange-local`. Choose the Docker connector instructions. Store its token as `RVINTERCHANGE_TUNNEL_TOKEN` in `/data/DockerConfigs/.env` without printing the file or token.

Start the connector:

```bash
docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml --profile tunnel up -d rvinterchange-cloudflared
docker compose -f deploy/docker-compose.yaml ps rvinterchange-cloudflared
docker logs --tail 50 rvinterchange-cloudflared
```

Expected: Cloudflare Dashboard shows the connector healthy and logs show registered connections without authentication errors.

- [ ] **Step 4: Add the public hostname routes**

Configure these exact published application routes on `rvinterchange-local`:

```text
rvinterchange.com        -> http://rvinterchange-web:80
review.rvinterchange.com -> http://rvinterchange-review:80
```

Create a Cloudflare redirect rule from `www.rvinterchange.com/*` to `https://rvinterchange.com/$1` with permanent status `301`. Do not create a route to `rvinterchange-api`.

- [ ] **Step 5: Create the review Access application before using the review route**

Create a Cloudflare Access self-hosted application for `review.rvinterchange.com`:

- Session duration: 8 hours.
- Policy action: Allow.
- Include rule: exact email `contact@rvinterchange.com`.
- All other requests: deny by default.
- Authentication method for the first release: email one-time PIN delivered through Cloudflare Email Routing to the verified destination.

Copy the non-secret Application Audience tag into the private operations record under `/data/DockerConfigs/RVInterchange/`; do not add it to application code until the moderation API plan implements origin JWT validation.

- [ ] **Step 6: Configure edge behavior**

In Cloudflare:

- Enable Always Use HTTPS.
- Keep cache bypassed for `/public/v1/*`, `/submission/v1/*`, and `/health/`.
- Permit normal static caching for version-stable CSS/JS/images, but do not create an “cache everything” rule for HTML.
- Enable the Cloudflare managed WAF ruleset available on the account.
- Do not enable HSTS yet; Task 7 does so only after the complete HTTPS verification matrix passes.

- [ ] **Step 7: Verify public and protected routes**

From a device not using the host's loopback interface, run:

```bash
curl -fsS https://rvinterchange.com/health/
curl -fsS "https://rvinterchange.com/public/v1/search?q=SW6DE&limit=1"
curl -sS -o /dev/null -w '%{http_code}\n' https://rvinterchange.com/debug/v1/logs
curl -sS -o /dev/null -w '%{http_code}\n' https://rvinterchange.com/docs
curl -sS -o /dev/null -w '%{http_code}\n' https://rvinterchange.com/openapi.json
curl -sS -o /dev/null -w '%{http_code}\n' https://rvinterchange.com/admin.html
curl -sS -o /dev/null -w '%{http_code}\n' https://rvinterchange.com/submission/v1/status
curl -sS -o /dev/null -w '%{http_code}\n' https://review.rvinterchange.com/
```

Expected:

- Public health and search return `200`.
- Public debug, docs, OpenAPI, and admin paths return `404`.
- Submission placeholder returns `503`.
- Unauthenticated review request redirects to or displays Cloudflare Access, never the review HTML.
- After authenticating as `contact@rvinterchange.com`, the review page loads and its existing search/debug calls work.

- [ ] **Step 8: Extend the operations guide and commit after explicit authorization**

Record tunnel name, hostnames, service targets, loopback diagnostic ports, Access application name, session duration, allow-policy identity, caching exceptions, and the verification results. Exclude tokens, cookies, generated login URLs, and private keys.

```bash
git add -- docs/operations/rvinterchange-local-hosting.md
git diff --cached --check
git commit -m "docs: add Cloudflare local hosting runbook"
```

### Task 7: Complete the cutover, security verification, rollback drill, and repository checks

**Files:**
- Modify: `README.md`
- Modify: `docs/operations/rvinterchange-local-hosting.md`
- Verify: all files changed in Tasks 1-6

**Interfaces:**
- Consumes: healthy public/review/tunnel services, DNS/email configuration, and legacy rollback profile.
- Produces: a verified public cutover, tested rollback, HSTS safety decision, current documentation, and a complete clean test result.

- [ ] **Step 1: Update the README hosting section**

Document:

- Public site: `https://rvinterchange.com`.
- Protected review site: `https://review.rvinterchange.com`.
- Loopback diagnostics: public `http://127.0.0.1:8485`, review `http://127.0.0.1:8486`.
- Repository stack command:

```bash
docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml --profile tunnel up -d --build
```

- Operations guide: `docs/operations/rvinterchange-local-hosting.md`.
- Explicit statement that `components.db` remains read-only to the API and is rebuilt with the canonical command.

Remove wording that describes the Docker site as personal-use-only or instructs operators to start the RV services from the shared Compose project by default. Keep the `rvinterchange-legacy` command in the operations guide, not the main quick start.

- [ ] **Step 2: Run the complete automated suite**

Run:

```bash
python3 -m pytest tests/ Docs/Tools -v
git diff --check
RVINTERCHANGE_TUNNEL_TOKEN=test-token docker compose -f deploy/docker-compose.yaml config --quiet
```

Expected: all tests pass, the diff has no whitespace errors, and Compose renders successfully.

- [ ] **Step 3: Verify headers and same-origin behavior**

Run:

```bash
curl -fsSI https://rvinterchange.com/
curl -fsSI https://rvinterchange.com/how-it-works.html
curl -fsS -D - -o /dev/null "https://rvinterchange.com/public/v1/search?q=SW6DE&limit=1"
```

Confirm:

- HTTPS is used.
- CSP contains `script-src 'self'` and no `unsafe-inline`.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and the Permissions Policy are present.
- The API response contains no `Access-Control-Allow-Origin` header.
- Browser search, coverage, result detail, discontinued-chain navigation, and browser Back/Forward continue working at the public origin.

- [ ] **Step 4: Perform a controlled tunnel outage test**

Run:

```bash
docker compose -f deploy/docker-compose.yaml stop rvinterchange-cloudflared
curl -fsS http://127.0.0.1:8485/health/
docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml --profile tunnel up -d rvinterchange-cloudflared
```

Expected: the public Internet route becomes unavailable while the local health endpoint remains healthy; after restart, Cloudflare reconnects and the public health check returns `200` again.

- [ ] **Step 5: Perform and document the legacy rollback drill**

Rollback:

```bash
docker compose -f deploy/docker-compose.yaml --profile tunnel down
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy up -d --build rvinterchange-api rvinterchange-web
curl -fsS http://127.0.0.1:8484/docs >/dev/null
curl -fsS http://127.0.0.1:8485/ >/dev/null
```

Return to the new stack:

```bash
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy stop rvinterchange-api rvinterchange-web
docker compose -f /data/DockerConfigs/docker-compose.yaml --profile rvinterchange-legacy rm -f rvinterchange-api rvinterchange-web
docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml --profile tunnel up -d --build
```

Expected: both rollback and return-to-production paths succeed. Record timestamps and outcomes in the operations guide. Do not delete legacy images or service definitions during this plan.

- [ ] **Step 6: Enable conservative HSTS after the verification matrix passes**

Only after public, review, email, and rollback verification pass, enable Cloudflare HSTS with:

```text
max-age: 2592000
includeSubDomains: false
preload: false
```

Do not enable preload or a one-year lifetime in the first release. Record the enablement date and the condition for later extension.

- [ ] **Step 7: Review repository and external worktree scope**

Run:

```bash
git status --short
git diff --check
git -C /data/DockerConfigs status --short
git -C /data/DockerConfigs diff -- docker-compose.yaml .env.example
```

Confirm the RV Interchange repository contains only approved hosting/spec/plan changes plus the pre-existing untracked Fleetwood directory. Confirm the external diff touches only the two legacy service profiles and the tunnel-token example key; report all unrelated pre-existing `/data/DockerConfigs` changes without staging them.

- [ ] **Step 8: Commit final repository documentation after explicit authorization**

```bash
git add -- README.md docs/operations/rvinterchange-local-hosting.md docs/superpowers/specs/2026-08-20-public-submission-queue-design.md docs/superpowers/plans/2026-08-20-rvinterchange-hosting-foundation.md
git diff --cached --check
git commit -m "docs: finalize local hosting foundation"
```

Do not commit the external `/data/DockerConfigs` repository without a separate user instruction after its complete dirty-worktree diff is reviewed.

## Plan Completion Criteria

- The public site and catalog API work at `https://rvinterchange.com` over Cloudflare Tunnel.
- The browser uses same-origin API requests; FastAPI CORS middleware is absent.
- Public routes deny debug, review, OpenAPI, documentation, and admin assets.
- `review.rvinterchange.com` requires Cloudflare Access and serves the existing debug UI only after authentication.
- API data tooling is mounted read-only; no API host port exists; public/review diagnostics bind loopback only.
- The unfinished intake route returns controlled `503` and is not mistaken for a working submission system.
- `contact@rvinterchange.com` and `dmarc-reports@rvinterchange.com` forward through Cloudflare Email Routing, while catch-all remains disabled.
- Root routing MX, SPF, DKIM, and reporting-only DMARC checks pass.
- Branded replies and Cloudflare arbitrary-recipient transactional sending remain explicitly deferred to the submission-intake plan.
- The repository-owned Compose project passes its contract test.
- The full Python/Docs test suite passes.
- Tunnel outage and legacy rollback drills both pass and are documented.
- No secret appears in Git, logs, shell output captured in documentation, or Docker build contexts.
- The shared `/data/DockerConfigs` worktree remains uncommitted unless separately authorized.

## Gates Intentionally Left for Later Plans

This plan makes the current read-only lookup public; it does not authorize the public
submission launch. The following approved-spec release gates remain open and must be
completed by the intake/moderation plans before `/submission/v1/*` stops returning `503`:

- Application-level validation of the Cloudflare Access JWT and local reviewer roles.
- Intake database, artifact store, encrypted daily backup, off-host backup copy, and clean
  restore drill.
- Turnstile and application rate limits.
- Public privacy/contribution terms and evidence licensing.
- Contributor and reviewer UX designs and their accessibility verification.
- Idempotent promotion and canonical rebuild integration tests.

## Authoritative References

- Cloudflare Tunnel: `https://developers.cloudflare.com/tunnel/`
- Cloudflare remotely managed Docker connector: `https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/update-cloudflared/`
- Cloudflare Access JWT validation requirement: `https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/`
- Cloudflare Email Routing: `https://developers.cloudflare.com/email-service/get-started/route-emails/`
- Cloudflare routing rules and destinations: `https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/`
- Cloudflare Email Service pricing: `https://developers.cloudflare.com/email-service/platform/pricing/`
- Cloudflare Email Sending, deferred to intake: `https://developers.cloudflare.com/email-service/get-started/send-emails/`
