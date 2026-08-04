import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sqlite3
import pytest
from fastapi.testclient import TestClient

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
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
    }


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
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        ],
        "supersessions": [],
    }


def test_replacements_endpoint_not_found(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404


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
             "identifiers": [{"ns": "suburban", "value": "SW6DE"}]},
        ],
    }


def test_search_endpoint_no_match_returns_200_with_empty_results(client):
    response = client.get("/public/v1/search", params={"q": "NOPE"})
    assert response.status_code == 200
    assert response.json() == {"query": "NOPE", "results": []}


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
    conn = next(main_module.get_conn())
    try:
        row = conn.execute(
            "SELECT component_id FROM components WHERE component_id = ?",
            ("c_test_ro",)).fetchone()
        assert row["component_id"] == "c_test_ro"
    finally:
        conn.close()
