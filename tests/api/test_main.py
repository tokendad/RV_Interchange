import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
    }


def test_replacements_endpoint_not_found(client):
    response = client.get(
        "/public/v1/replacements", params={"ns": "suburban", "identifier": "NOPE"})
    assert response.status_code == 404
