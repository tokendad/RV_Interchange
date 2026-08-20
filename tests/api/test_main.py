import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sqlite3
import pytest
from fastapi.testclient import TestClient
from logging.handlers import RotatingFileHandler

from interchange_schema import init_db
from interchange_store import insert_component, insert_identifier
from interchange_models import Component, Identifier

import api.main as main_module


@pytest.fixture
def client():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))

    def _get_conn_override():
        return conn

    main_module.app.dependency_overrides[main_module.get_conn] = _get_conn_override
    yield TestClient(main_module.app)
    main_module.app.dependency_overrides.clear()


def test_resolve_endpoint(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "component_id": "c_test_a",
        "manufacturer": "Suburban",
        "part_type": "Water Heater",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
        "attributes": [],
    }


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


def test_resolve_endpoint_not_found(client):
    response = client.get("/public/v1/resolve", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404


def test_replacements_endpoint(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
             "required_parts": [], "caveats": []},
        ],
        "supersessions": [],
    }


def test_replacements_endpoint_not_found(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404


def test_coverage_endpoint(client):
    response = client.get("/public/v1/coverage")
    assert response.status_code == 200
    body = response.json()
    suburban = next(m for m in body["manufacturers"] if m["manufacturer"] == "Suburban")
    assert suburban["components"] == 1
    assert {m["manufacturer"] for m in body["manufacturers"]} == \
        {"Suburban", "Coleman-Mach", "Atwood", "Norcold", "Furrion", "Girard", "Lippert"}
    assert body["totals"]["components"] == 1


def test_unhandled_error_is_logged_and_returns_500(client, caplog):
    import api.main as main_module

    def _boom(conn, ns, identifier):
        raise RuntimeError("simulated failure")

    original = main_module.IdentifierService.resolve
    main_module.IdentifierService.resolve = staticmethod(_boom)
    # raise_server_exceptions=False: Starlette's ServerErrorMiddleware re-raises
    # unhandled exceptions after invoking the registered handler (by design, so
    # servers/tests can see the traceback) - the default TestClient behavior would
    # surface that RuntimeError instead of letting us assert on the 500 response
    # our unhandled_exception_handler actually produces. Scoped to a local client
    # here (rather than the shared `client` fixture) so the other tests that share
    # that fixture keep the default TestClient behavior. dependency_overrides lives
    # on main_module.app, not the TestClient instance, so it's already in effect.
    error_client = TestClient(main_module.app, raise_server_exceptions=False)
    try:
        with caplog.at_level("ERROR", logger="rvinterchange.api"):
            response = error_client.get(
                "/public/v1/resolve", params={"ns": "suburban", "identifier": "SW6DE"})
        assert response.status_code == 500
        assert response.json() == {"detail": "internal error"}
        assert any("Unhandled exception" in record.message for record in caplog.records)
    finally:
        main_module.IdentifierService.resolve = original


def test_search_endpoint(client):
    response = client.get("/public/v1/search", params={"q": "SW6DE"})
    assert response.status_code == 200
    assert response.json() == {
        "query": "SW6DE",
        "results": [
            {"component_id": "c_test_a", "label": "SW6DE",
             "manufacturer": "Suburban",
             "part_type": "Water Heater",
             "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
             "attributes": []},
        ],
    }


def test_search_endpoint_no_match_returns_200_with_empty_results(client):
    response = client.get("/public/v1/search", params={"q": "NOPE"})
    assert response.status_code == 200
    assert response.json() == {"query": "NOPE", "results": []}


def test_search_endpoint_rejects_out_of_range_limit(client):
    response = client.get("/public/v1/search", params={"q": "SW", "limit": 0})
    assert response.status_code == 422

    response = client.get("/public/v1/search", params={"q": "SW", "limit": 101})
    assert response.status_code == 422


def test_readonly_connection_rejects_writes(tmp_path):
    db_path = str(tmp_path / "ro_test.db")
    init_db(db_path).close()

    conn = main_module._readonly_connection(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO components (component_id, part_type_id, created_at) "
                "VALUES ('x', 1, 'now')")
    finally:
        conn.close()


def test_get_conn_yields_working_readonly_connection(tmp_path, monkeypatch):
    db_path = str(tmp_path / "get_conn_test.db")
    seed_conn = init_db(db_path)
    insert_component(seed_conn, Component("c_test_ro", 412, "412-0001-A"))
    seed_conn.close()

    monkeypatch.setattr(main_module, "DB_PATH", db_path)
    gen = main_module.get_conn()
    conn = next(gen)
    try:
        row = conn.execute(
            "SELECT component_id FROM components WHERE component_id = ?",
            ("c_test_ro",)).fetchone()
        assert row["component_id"] == "c_test_ro"
    finally:
        conn.close()


def test_api_log_uses_rotating_file_handler():
    rotating_handlers = [
        h for h in main_module.logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) == 1
    assert rotating_handlers[0].maxBytes == 1_000_000
    assert rotating_handlers[0].backupCount == 3


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
