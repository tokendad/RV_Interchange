import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from edge_types import (
    EDGE_TYPES,
    EDGE_TYPE_CONTROLS,
    EDGE_TYPE_FITS,
    EDGE_TYPE_SUBSTITUTES,
    EDGE_TYPE_SUPERSEDES,
)
from interchange_models import Edge
from interchange_schema import init_db
from interchange_store import insert_component, get_edges_from
from interchange_models import Component


def test_edge_type_registry_lists_the_canonical_vocabulary():
    assert EDGE_TYPES == (
        EDGE_TYPE_SUBSTITUTES,
        EDGE_TYPE_SUPERSEDES,
        EDGE_TYPE_CONTROLS,
        EDGE_TYPE_FITS,
    )


def test_edge_rejects_unknown_types():
    with pytest.raises(ValueError, match="unknown edge type"):
        Edge(type="bogus", from_component_id="c_test_a")


def test_edge_query_rejects_unknown_types():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    with pytest.raises(ValueError, match="unknown edge type"):
        get_edges_from(conn, "c_test_a", type="bogus")
