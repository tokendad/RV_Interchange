from pathlib import Path
import json
import subprocess

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


def test_review_ui_exposes_distinct_draft_and_promotion_actions():
    html = read("review/index.html")
    script = read("review/admin.js")
    assert 'id="evidence-workflow"' in html
    assert "/observation-drafts" in script
    assert "/canonical-preview" in script
    assert "/promotions" in script
    assert "canPromote" in script
    assert 'roles.includes("admin")' in script
    assert 'capabilities.includes("publisher")' in script
    assert "integration pending" in script.lower()


def test_serialize_draft_payload_is_pure_and_serializes_fields():
    script = read("review/admin.js")
    helper = "function serializeDraftPayload" + script.split("function serializeDraftPayload", 1)[1].split("function serializeDraft", 1)[0]
    result = subprocess.run(
        ["node", "-e", f"{helper}; console.log(JSON.stringify(serializeDraftPayload({{source_type:'manufacturer_pdf',source_name:'Sheet',source_url:'https://example.test/a',raw_content:'Model SF-30FQ',extracted:{{model:'SF-30FQ'}},claim_ids:['c1'],artifact_ids:['a1']}}, 's1', 'key')));"],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == {
        "source_type": "manufacturer_pdf", "source_name": "Sheet",
        "source_url": "https://example.test/a", "raw_content": "Model SF-30FQ",
        "extracted": {"model": "SF-30FQ"}, "claim_ids": ["c1"],
        "artifact_ids": ["a1"], "idempotency_key": "key",
    }


def test_review_ui_keeps_promotion_state_and_preview_authoritative():
    script = read("review/admin.js")
    assert 'return canPromote();' not in script.split("function canDecide", 1)[1].split("function canAdminister", 1)[0]
    assert 'return reviewer.roles.includes("admin") || reviewer.capabilities.includes("publisher");' in script
    assert 'promotionState(data)' in script
    assert 'evidence_state' not in script
    assert 'dataset.payloadHash = ""' in script
    assert 'previewTier !== tier.value' in script
