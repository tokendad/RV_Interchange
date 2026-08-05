import contextlib
import io
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edge_resolver import build_database
from interchange_store import get_component_by_identifier, get_edges_from

import api.main as main_module


GROUND_TRUTH_PATH = Path(__file__).resolve().parents[2] / "Docs" / "Inital_Design" / "ground-truth.yaml"


@pytest.fixture(scope="module")
def persisted_db_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "components.db"
        with contextlib.redirect_stdout(io.StringIO()):
            build_database(GROUND_TRUTH_PATH, db_path)
        yield db_path


@pytest.fixture
def client(persisted_db_path):
    main_module.app.dependency_overrides.clear()
    original_db_path = main_module.DB_PATH
    main_module.DB_PATH = str(persisted_db_path)
    try:
        with TestClient(main_module.app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        main_module.DB_PATH = original_db_path
        main_module.app.dependency_overrides.clear()


def test_sw6de_and_sw6del_replacement_behavior_is_directional(client):
    sw6de = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DE"})
    assert sw6de.status_code == 200
    assert sw6de.json() == {
        "source": "SW6DE",
        "replacements": [
            {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
            {"part": "SW6DEL", "fit": "Fits With Modification", "rank": 2, "summary": None},
        ],
        "supersessions": [],
    }

    sw6del = client.get("/public/v1/replacements", params={"ns": "suburban", "identifier": "SW6DEL"})
    assert sw6del.status_code == 200
    body = sw6del.json()
    assert body["source"] == "SW6DEL"
    assert body["replacements"][0] == {
        "part": "SW6DEL", "fit": "Exact Match", "rank": 1, "summary": None,
    }
    assert any(
        item["part"] == "SW6DE" and "12V relay" in (item["summary"] or "")
        for item in body["replacements"]
    )


def test_coleman_supersession_chain_is_visible_through_api(client):
    response = client.get(
        "/public/v1/replacements",
        params={"ns": "coleman", "identifier": "7330F3361"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "7330F3361"
    assert body["replacements"] == [
        {"part": "7330F3361", "fit": "Exact Match", "rank": 1, "summary": None},
    ]
    assert {
        "part": "9420-352",
        "note": "Coleman-Mach's 2025 dealer catalog (CM-4040.02) names 9420-352 as the current replacement for 7330F3361.",
    } in body["supersessions"]


def test_atwood_repair_part_is_served_from_the_persisted_database(client, persisted_db_path):
    search = client.get("/public/v1/search", params={"q": "91230"})
    assert search.status_code == 200
    assert search.json() == {
        "query": "91230",
        "results": [
            {
                "component_id": "c_placeholder_wh_atwood_epart_91230",
                "label": "91230",
                "identifiers": [{"ns": "atwood", "value": "91230"}],
            },
        ],
    }

    conn = sqlite3.connect(f"file:{persisted_db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        component = get_component_by_identifier(conn, "atwood", "91230")
        assert component is not None
        fits_edges = get_edges_from(conn, component.component_id, type="fits")
        assert len(fits_edges) == 4
    finally:
        conn.close()


def test_unresolved_identifier_equivalence_candidate_stays_unresolved(client):
    assert client.get(
        "/public/v1/resolve",
        params={"ns": "icm", "identifier": "AR7815"},
    ).status_code == 404
    assert client.get(
        "/public/v1/resolve",
        params={"ns": "coleman", "identifier": "7330F3858"},
    ).status_code == 404
