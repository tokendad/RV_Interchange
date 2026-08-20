from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def location_blocks(config):
    """Return each Nginx location declaration and its complete block text."""
    blocks = {}
    lines = config.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped.startswith("location ") or "{" not in stripped:
            index += 1
            continue

        declaration = stripped.split("{", maxsplit=1)[0].strip()
        block = [line]
        depth = line.count("{") - line.count("}")
        index += 1
        while depth > 0:
            line = lines[index]
            block.append(line)
            depth += line.count("{") - line.count("}")
            index += 1
        blocks[declaration] = "\n".join(block)
    return blocks


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
    blocks = location_blocks(config)
    proxied_locations = {
        declaration
        for declaration, block in blocks.items()
        if "proxy_pass" in block
    }

    assert proxied_locations == {"location = /health/", "location ^~ /public/v1/"}
    assert "proxy_pass http://rvinterchange-api:8484/health/;" in blocks["location = /health/"]
    assert "proxy_set_header Host $host;" in blocks["location = /health/"]
    assert (
        "proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;"
        in blocks["location = /health/"]
    )
    assert "proxy_pass http://rvinterchange-api:8484;" in blocks["location ^~ /public/v1/"]
    assert "proxy_set_header Host $host;" in blocks["location ^~ /public/v1/"]
    assert (
        "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
        in blocks["location ^~ /public/v1/"]
    )
    assert (
        "proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;"
        in blocks["location ^~ /public/v1/"]
    )


def test_submission_intake_is_a_non_proxied_controlled_503():
    block = location_blocks(read("web/nginx.conf"))["location ^~ /submission/v1/"]

    assert "proxy_pass" not in block
    assert "return 503 '{\"detail\":\"submission intake is not available yet\"}';" in block


def test_internal_routes_are_denied_without_proxying():
    blocks = location_blocks(read("web/nginx.conf"))

    for declaration in (
        "location ^~ /debug/",
        "location ^~ /review/",
        "location = /docs",
        "location = /redoc",
        "location = /openapi.json",
        "location = /admin.html",
        "location = /admin.js",
    ):
        assert "return 404;" in blocks[declaration]
        assert "proxy_pass" not in blocks[declaration]


def test_public_pages_have_no_inline_scripts():
    for name in ("contact.html", "how-it-works.html"):
        html = read(f"web/{name}")
        assert "<script>" not in html
        assert '<script src="page-init.js"></script>' in html


def test_public_nginx_sets_the_required_security_headers():
    config = read("web/nginx.conf")
    required_headers = (
        "add_header Content-Security-Policy \"default-src 'self'; base-uri 'none'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self'\" always;",
        'add_header X-Content-Type-Options "nosniff" always;',
        'add_header Referrer-Policy "no-referrer" always;',
        'add_header Permissions-Policy "camera=(), geolocation=(), microphone=()" always;',
        'add_header X-Frame-Options "DENY" always;',
    )

    for header in required_headers:
        assert header in config
    assert "'unsafe-inline'" not in config


def test_review_image_owns_admin_assets():
    dockerfile = read("review/Dockerfile")
    assert "review/index.html" in dockerfile
    assert "review/admin.js" in dockerfile
    assert "web/api-client.js" in dockerfile
    assert "web/style.css" in dockerfile


def test_review_proxy_exposes_only_existing_debug_contract():
    config = read("review/nginx.conf")
    assert "location ^~ /public/v1/" in config
    assert "location ^~ /debug/v1/" in config
    assert "location ^~ /review/v1/" in config
    assert "return 503" in config
    for private_path in ("/docs", "/redoc", "/openapi.json"):
        assert private_path in config
