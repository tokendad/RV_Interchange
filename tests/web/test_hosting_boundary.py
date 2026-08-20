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
