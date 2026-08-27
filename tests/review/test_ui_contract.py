from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_review_page_is_queue_not_legacy_debug_console():
    html = read("review/index.html")
    script = read("review/admin.js")
    assert "Review queue" in html
    assert 'id="queue"' in html and 'id="detail"' in html
    assert "search-form" not in html
    assert "Resolve" not in html
    assert 'id="priority-filter"' in html
    assert "/review/v1/queue" in script
    assert "/request-information" in script
    assert "/spam" in script
    assert '["endorse", "dispute"]' in script
    assert 'capabilities.includes("publisher")' in script
    assert "target-context" in script
    assert "artifact-list" in script


def test_review_ui_uses_nocturne_visual_contract():
    css = read("review/style.css")
    assert "color-scheme: dark" in css
    assert "--lavender" in css
