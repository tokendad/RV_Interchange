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


from datetime import datetime, timezone

from interchange_store import insert_edge, insert_evidence, insert_caveat
from interchange_models import Edge, RelationshipEvidence, EdgeCaveat

from api.services import ReplacementService


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def test_get_replacements_tiers_by_confidence():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_component(conn, Component("c_test_c", 412, "412-0001-C"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))
    insert_identifier(conn, Identifier("c_test_c", "suburban", "SW12DEL"))

    drop_in_edge = Edge(type="substitutes", from_component_id="c_test_a",
                         to_component_id="c_test_b")
    insert_edge(conn, drop_in_edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=drop_in_edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))

    modified_edge = Edge(type="substitutes", from_component_id="c_test_a",
                          to_component_id="c_test_c")
    insert_edge(conn, modified_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=modified_edge.id, event_type="attribute_prior",
        effect_alpha=3.0, effect_beta=1.0, occurred_at=_now()))
    insert_caveat(conn, EdgeCaveat(edge_id=modified_edge.id, blocking=True,
                                   text="Requires switch kit"))

    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["source"] == "SW6DE"
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2, "summary": None},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "summary": "Requires switch kit"},
    ]


def test_get_replacements_rank_reflects_tier_not_insertion_order():
    # Regression test: insert the WEAKER ("Fits With Modification") edge
    # before the STRONGER ("Direct Fit") edge, to verify rank is assigned
    # by tier quality (and confidence within a tier), not by the order rows
    # come back from get_edges_from (insertion/rowid order).
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_component(conn, Component("c_test_c", 412, "412-0001-C"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))
    insert_identifier(conn, Identifier("c_test_c", "suburban", "SW12DEL"))

    # Weaker edge inserted FIRST.
    modified_edge = Edge(type="substitutes", from_component_id="c_test_a",
                          to_component_id="c_test_c")
    insert_edge(conn, modified_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=modified_edge.id, event_type="attribute_prior",
        effect_alpha=3.0, effect_beta=1.0, occurred_at=_now()))
    insert_caveat(conn, EdgeCaveat(edge_id=modified_edge.id, blocking=True,
                                   text="Requires switch kit"))

    # Stronger edge inserted SECOND.
    drop_in_edge = Edge(type="substitutes", from_component_id="c_test_a",
                         to_component_id="c_test_b")
    insert_edge(conn, drop_in_edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=drop_in_edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2, "summary": None},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "summary": "Requires switch kit"},
    ]


def test_get_replacements_excludes_below_bar_and_unknown_component():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    weak_edge = Edge(type="substitutes", from_component_id="c_test_a",
                      to_component_id="c_test_b")
    insert_edge(conn, weak_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=weak_edge.id, event_type="unknown_incomplete",
        effect_alpha=1.0, effect_beta=1.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1, "summary": None},
    ]

    assert ReplacementService.get_replacements(conn, "c_does_not_exist") is None


from api.services import SearchService


def test_search_ranks_exact_match_first():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    result = SearchService.search(conn, "SW")

    assert result["query"] == "SW"
    assert [r["component_id"] for r in result["results"]] == ["c_test_a", "c_test_b"]
    assert result["results"][0]["label"] == "SW6DE"
    assert result["results"][0]["identifiers"] == [{"ns": "suburban", "value": "SW6DE"}]


def test_search_no_match_returns_empty_results():
    conn = init_db(":memory:")
    result = SearchService.search(conn, "NOPE")
    assert result == {"query": "NOPE", "results": []}


def test_search_respects_limit():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    result = SearchService.search(conn, "SW", limit=1)
    assert [r["component_id"] for r in result["results"]] == ["c_test_a"]
