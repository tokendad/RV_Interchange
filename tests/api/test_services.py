import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from interchange_schema import init_db
from interchange_store import insert_component, insert_identifier
from interchange_models import Component, Identifier
from edge_types import EDGE_TYPE_SUBSTITUTES, EDGE_TYPE_SUPERSEDES

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
        "manufacturer": "Suburban",
        "part_type": "Water Heater",
        "identifiers": [{"ns": "suburban", "value": "SW6DE"}],
        "attributes": [],
    }


def test_resolve_includes_component_attributes():
    from interchange_store import insert_component_attribute
    from interchange_models import ComponentAttribute

    conn = init_db(":memory:")
    _seed_basic_component(conn)
    insert_component_attribute(conn, ComponentAttribute(
        component_id="c_test_a", name="capacity", provenance="manufacturer_pdf",
        source_observation_id=1, value_number=6.0, unit="gal"))

    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result["attributes"] == [
        {"name": "capacity", "qualifier": "", "value": 6.0, "unit": "gal"},
    ]
    # provenance/source_observation_id must never leak into the response
    assert "provenance" not in result["attributes"][0]
    assert "source_observation_id" not in result["attributes"][0]


def test_resolve_excludes_instance_serial_attributes():
    from interchange_store import insert_component_attribute
    from interchange_models import ComponentAttribute

    conn = init_db(":memory:")
    _seed_basic_component(conn)
    insert_component_attribute(conn, ComponentAttribute(
        component_id="c_test_a", name="serial", provenance="dataplate_photo",
        source_observation_id=1, value_text="ABC123"))
    insert_component_attribute(conn, ComponentAttribute(
        component_id="c_test_a", name="cooling_unit_serial", provenance="dataplate_photo",
        source_observation_id=2, value_text="XYZ789"))
    insert_component_attribute(conn, ComponentAttribute(
        component_id="c_test_a", name="capacity", provenance="manufacturer_pdf",
        source_observation_id=3, value_number=6.0, unit="gal"))

    result = IdentifierService.resolve(conn, "suburban", "SW6DE")
    assert result["attributes"] == [
        {"name": "capacity", "qualifier": "", "value": 6.0, "unit": "gal"},
    ]
    names = [attribute["name"] for attribute in result["attributes"]]
    assert "serial" not in names
    assert "cooling_unit_serial" not in names


def test_resolve_unknown_identifier():
    conn = init_db(":memory:")
    _seed_basic_component(conn)
    result = IdentifierService.resolve(conn, "suburban", "NOPE")
    assert result is None


from datetime import datetime, timezone

from interchange_store import insert_edge, insert_evidence, insert_caveat, insert_supersession_detail
from interchange_models import Edge, RelationshipEvidence, EdgeCaveat, EdgeSupersessionDetail

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

    drop_in_edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                         to_component_id="c_test_b")
    insert_edge(conn, drop_in_edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=drop_in_edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))

    modified_edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
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
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2,
         "required_parts": [], "caveats": []},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "required_parts": [],
         "caveats": [{"text": "Requires switch kit", "blocking": True}]},
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
    modified_edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                          to_component_id="c_test_c")
    insert_edge(conn, modified_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=modified_edge.id, event_type="attribute_prior",
        effect_alpha=3.0, effect_beta=1.0, occurred_at=_now()))
    insert_caveat(conn, EdgeCaveat(edge_id=modified_edge.id, blocking=True,
                                   text="Requires switch kit"))

    # Stronger edge inserted SECOND.
    drop_in_edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                         to_component_id="c_test_b")
    insert_edge(conn, drop_in_edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=drop_in_edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")

    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
        {"part": "SW6DEL", "fit": "Direct Fit", "rank": 2,
         "required_parts": [], "caveats": []},
        {"part": "SW12DEL", "fit": "Fits With Modification", "rank": 3,
         "required_parts": [],
         "caveats": [{"text": "Requires switch kit", "blocking": True}]},
    ]


def test_get_replacements_excludes_below_bar_and_unknown_component():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    weak_edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                      to_component_id="c_test_b")
    insert_edge(conn, weak_edge)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=weak_edge.id, event_type="unknown_incomplete",
        effect_alpha=1.0, effect_beta=1.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["replacements"] == [
        {"part": "SW6DE", "fit": "Exact Match", "rank": 1,
         "required_parts": [], "caveats": []},
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
    assert result["results"][0]["manufacturer"] == "Suburban"
    assert result["results"][0]["part_type"] == "Water Heater"


def test_search_result_manufacturer_is_none_for_unmapped_namespace():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 415, "415-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "icm", "PCB1060"))

    result = SearchService.search(conn, "PCB1060")
    assert result["results"][0]["manufacturer"] is None
    assert result["results"][0]["part_type"] == "Wall Thermostat"


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


def test_label_for_prefers_querying_namespace():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_a", "icm", "PCB1060"))

    assert ReplacementService.get_replacements(conn, "c_test_a", ns="icm")["source"] == "PCB1060"
    assert ReplacementService.get_replacements(conn, "c_test_a", ns="coleman")["source"] == "7330G3351"
    # No ns given: falls back to the first identifier (insertion order).
    assert ReplacementService.get_replacements(conn, "c_test_a")["source"] == "7330G3351"


def test_get_replacements_includes_supersessions():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_b", "coleman", "9420-351"))

    edge = Edge(type=EDGE_TYPE_SUPERSEDES, from_component_id="c_test_a",
                to_component_id="c_test_b")
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id, note="Coleman catalog names 9420-351 as the replacement"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="manufacturer_assertion", effect_alpha=2.0,
        effect_beta=0.0, occurred_at=_now()))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["supersessions"] == [
        {"part": "9420-351", "note": "Coleman catalog names 9420-351 as the replacement"},
    ]


def test_get_replacements_omits_supersession_with_no_evidence():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "coleman", "7330G3351"))
    insert_identifier(conn, Identifier("c_test_b", "coleman", "9420-351"))

    edge = Edge(type=EDGE_TYPE_SUPERSEDES, from_component_id="c_test_a",
                to_component_id="c_test_b")
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(edge_id=edge.id, note="no evidence yet"))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    assert result["supersessions"] == []


def test_get_replacements_includes_required_parts():
    from interchange_store import insert_required_part
    from interchange_models import EdgeRequiredPart

    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))

    edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                to_component_id="c_test_b")
    insert_edge(conn, edge)
    for _ in range(8):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type="buyer_confirmed_install",
            effect_alpha=3.0, effect_beta=0.0, occurred_at=_now()))
    insert_required_part(conn, EdgeRequiredPart(
        edge_id=edge.id, ns="suburban", value="6276APW", role="replacement_panel"))

    result = ReplacementService.get_replacements(conn, "c_test_a")
    match = next(r for r in result["replacements"] if r["part"] == "SW6DEL")
    assert match["required_parts"] == [
        {"ns": "suburban", "value": "6276APW", "role": "replacement_panel",
         "manufacturer": "Suburban"},
    ]


from edge_types import EDGE_TYPE_FITS

from api.services import CoverageService


def test_get_coverage_counts_components_and_edges_per_manufacturer():
    conn = init_db(":memory:")
    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_component(conn, Component("c_test_c", 413, "413-0001-A"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))
    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW6DEL"))
    insert_identifier(conn, Identifier("c_test_c", "atwood", "GH6-6E"))

    insert_edge(conn, Edge(type=EDGE_TYPE_FITS, from_component_id="c_test_a",
                            to_component_id="c_test_b"))
    insert_edge(conn, Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id="c_test_a",
                            to_component_id="c_test_b"))

    result = CoverageService.get_coverage(conn)

    suburban = next(m for m in result["manufacturers"] if m["manufacturer"] == "Suburban")
    assert suburban == {
        "manufacturer": "Suburban", "components": 2,
        "fits_edges": 1, "substitutes_edges": 1, "supersedes_edges": 0,
    }
    atwood = next(m for m in result["manufacturers"] if m["manufacturer"] == "Atwood")
    assert atwood == {
        "manufacturer": "Atwood", "components": 1,
        "fits_edges": 0, "substitutes_edges": 0, "supersedes_edges": 0,
    }
    assert result["totals"] == {
        "components": 3, "fits_edges": 1, "substitutes_edges": 1, "supersedes_edges": 0,
    }


def test_get_coverage_lists_every_known_manufacturer_even_with_no_data():
    conn = init_db(":memory:")
    result = CoverageService.get_coverage(conn)
    names = {m["manufacturer"] for m in result["manufacturers"]}
    assert names == {"Suburban", "Coleman-Mach", "Atwood", "Norcold"}
    assert all(m["components"] == 0 for m in result["manufacturers"])
