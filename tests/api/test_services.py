import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from interchange_schema import init_db
from interchange_store import insert_component, insert_identifier
from interchange_models import Component, Identifier

from api.services import IdentifierService


def _seed_basic_component(conn):
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))


def test_resolve_known_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result == {
        "component_id": "c_test_a",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
    }


def test_resolve_unknown_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "NOPE")
    assert result is None
