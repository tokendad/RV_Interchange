#!/usr/bin/env python3
"""
edge_resolver.py — observations.db -> components/edges, proven against the
fixture's canonical edge case (SW6DE/SW6DEL) and the in-hand Coleman thermostat.
See docs/superpowers/plans/2026-07-31-edge-schema-resolver.md and
docs/superpowers/plans/2026-08-01-thermostat-resolver.md for scope. Full
fixture reproduction remains incremental.
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from resolver import normalize_extracted
from suburban_parser import compare_models
from interchange_models import (
    Component, Identifier, ComponentAttribute, Edge, EdgeSubstitutionDetail,
    EdgeSupersessionDetail, EdgeCaveat, RelationshipEvidence, IdentifierEquivalenceCandidate,
    IdentifierEquivalenceEvidence, prior_for_basis, compute_confidence,
)
from interchange_schema import init_db
from interchange_store import (
    insert_component, insert_identifier, insert_edge, insert_substitution_detail,
    insert_supersession_detail,
    insert_caveat, insert_evidence, now_iso, get_caveats_for_edge, get_evidence_for_edge,
    insert_component_attribute, get_component_attributes,
    insert_identifier_equivalence_candidate, insert_identifier_equivalence_evidence,
    get_identifier_equivalence_candidates, get_identifier_equivalence_evidence,
    get_supersession_detail,
)

WATER_HEATER_PART_TYPE = 412
THERMOSTAT_PART_TYPE = 415
THERMOSTAT_CODE = "415-0012-A"
COLEMAN_ENDPOINT_MODELS = ("7330G3351", "7330F3852", "9420-351")
COLEMAN_ENDPOINT_RESOLVER_VERSION = "coleman_endpoint_v1"
THERMOSTAT_TERMINALS = ("R", "Y", "W", "GL", "GH", "B")
THERMOSTAT_IDENTIFIERS = {
    ("icm", "AP7862"),
    ("coleman", "7330G335"),
    ("silkscreen", "PCB1060"),
    ("silkscreen", "SPCB-2"),
}


def component_from_observation(obs_row, component_id, part_type_id):
    """
    Build a Component + its Identifier rows from one observations.db row
    whose `extracted` blob has a `model` and `sku` field (the two anchor
    observations, #1 and #2, both do).
    """
    extracted = json.loads(obs_row["extracted"])
    normalized = normalize_extracted(obs_row["id"], extracted, strict=True)
    attrs = normalized["attributes"]

    model_raw = attrs.get("model")
    if not model_raw:
        raise ValueError(f"observation #{obs_row['id']} has no 'model' attribute")

    component = Component(component_id=component_id, part_type_id=part_type_id)
    identifiers = [Identifier(component_id, "suburban", model_raw, "exterior_plate")]

    # normalize_extracted accumulates same-canonical-key values into a list
    # when more than one raw key maps to `sku` (e.g. obs #1's `sku` field
    # PLUS its `aliases_mentioned` list both canonicalize to `sku`, giving
    # attrs["sku"] == ['5240A', '5140A']) - a plain string otherwise (obs #2
    # has only `sku`, giving attrs["sku"] == '5239A'). Confirmed by running
    # normalize_extracted directly against observations.db during plan
    # verification - do not assume it is always a scalar.
    sku = attrs.get("sku")
    sku_values = sku if isinstance(sku, list) else ([sku] if sku else [])
    for value in sku_values:
        identifiers.append(Identifier(component_id, "suburban", str(value), "none_marked"))
    return component, identifiers


def load_observation(obs_db_path, obs_id):
    conn = sqlite3.connect(obs_db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM observations WHERE id = ?", (obs_id,)).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"no observation #{obs_id} in {obs_db_path}")
    return row


def _normalized_attributes(obs_row):
    extracted = json.loads(obs_row["extracted"])
    return normalize_extracted(obs_row["id"], extracted, strict=True)["attributes"]


def thermostat_from_observations(photo_row, manual_row, positions_row, scalar_row,
                                 component_id):
    photo = _normalized_attributes(photo_row)
    manual = _normalized_attributes(manual_row)
    positions = _normalized_attributes(positions_row)
    scalars = _normalized_attributes(scalar_row)

    raw_identifiers = photo.get("physical_identifiers")
    if not isinstance(raw_identifiers, list):
        raise ValueError("thermostat photo evidence has no physical identifier list")
    identifier_pairs = {(item.get("ns"), item.get("value")) for item in raw_identifiers}
    if len(raw_identifiers) != 4 or identifier_pairs != THERMOSTAT_IDENTIFIERS:
        raise ValueError(f"unexpected thermostat physical identifiers: {raw_identifiers}")

    terminal_order = photo.get("terminal_order")
    if terminal_order != list(THERMOSTAT_TERMINALS) or len(set(terminal_order)) != 6:
        raise ValueError(f"unexpected thermostat terminal order: {terminal_order}")

    colors = photo.get("installed_wire_colors")
    board_positions = positions.get("terminal_board_position_map")
    functions = manual.get("terminal_function_map")
    expected_terminals = set(THERMOSTAT_TERMINALS)
    for label, mapping in (("wire colors", colors), ("board positions", board_positions),
                           ("terminal functions", functions)):
        if not isinstance(mapping, dict) or set(mapping) != expected_terminals:
            raise ValueError(f"thermostat {label} do not match terminal set: {mapping}")

    if scalars.get("voltage") != "12VDC" or scalars.get("stages") != "single":
        raise ValueError(f"unexpected thermostat voltage/stages: {scalars}")

    component = Component(component_id, THERMOSTAT_PART_TYPE, THERMOSTAT_CODE)
    identifiers = [Identifier(
        component_id, item["ns"], item["value"], item.get("visibility"))
        for item in raw_identifiers]

    attributes = []
    for ordinal, terminal in enumerate(THERMOSTAT_TERMINALS, start=1):
        attributes.extend((
            ComponentAttribute(component_id, "terminal_order", "in_hand", photo_row["id"],
                               qualifier=terminal, value_number=float(ordinal)),
            ComponentAttribute(component_id, "terminal_board_position", "in_hand",
                               positions_row["id"], qualifier=terminal,
                               value_text=board_positions[terminal]),
            ComponentAttribute(component_id, "installed_wire_color", "in_hand",
                               photo_row["id"], qualifier=terminal,
                               value_text=colors[terminal]),
            ComponentAttribute(component_id, "terminal_function", "manufacturer_pdf",
                               manual_row["id"], qualifier=terminal,
                               value_text=functions[terminal]),
        ))
    attributes.extend((
        ComponentAttribute(component_id, "voltage", "manufacturer_pdf", scalar_row["id"],
                           value_text="12VDC"),
        ComponentAttribute(component_id, "stages", "manufacturer_pdf_inferred",
                           scalar_row["id"], value_text="single"),
    ))
    return component, identifiers, attributes


def coleman_endpoint_components(product_row, replacement_row, legacy_row, component_ids):
    expected_sources = (
        (product_row, 40, "manufacturer_page", "product"),
        (replacement_row, 41, "manufacturer_pdf", "replacement"),
        (legacy_row, 42, "manufacturer_pdf", "legacy"),
    )
    for row, expected_id, expected_type, label in expected_sources:
        try:
            actual_id = row["id"]
            actual_type = row["source_type"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Coleman {label} observation lacks source metadata") from exc
        if (actual_id, actual_type) != (expected_id, expected_type):
            raise ValueError(
                f"unexpected Coleman {label} observation source: "
                f"{actual_id}/{actual_type}")

    product = _normalized_attributes(product_row)
    replacement = _normalized_attributes(replacement_row)
    legacy = _normalized_attributes(legacy_row)
    product_models = product.get("model_spec_table")
    replacement_models = replacement.get("model_spec_table")
    legacy_models = legacy.get("model_spec_table")
    relation = replacement.get("sku_relationship")

    if not all(isinstance(models, dict) for models in
               (product_models, replacement_models, legacy_models)):
        raise ValueError("Coleman endpoint observations require model tables")
    if not {"7330G3351", "7330F3852"}.issubset(product_models):
        raise ValueError("official product page is missing a retired endpoint")
    expected_relation = {
        "type": "manufacturer_supersedes",
        "from": ["7330G3351", "7330F3852"],
        "to": "9420-351",
    }
    if relation != expected_relation or "9420-351" not in replacement_models:
        raise ValueError(f"unexpected Coleman replacement relation: {relation}")
    if "7330G3351" not in legacy_models:
        raise ValueError("legacy catalog is missing 7330G3351")
    if set(component_ids) != set(COLEMAN_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman endpoint ID map: {component_ids}")

    def text_attr(component_id, name, value, provenance, source_row):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=COLEMAN_ENDPOINT_RESOLVER_VERSION)

    source_checks = (
        (product_models["7330G3351"].get("function"), "heat_cool", "7330G3351 function"),
        (product_models["7330G3351"].get("color"), "white", "7330G3351 color"),
        (product_models["7330F3852"].get("function"), "heat_cool", "7330F3852 function"),
        (product_models["7330F3852"].get("color"), "black", "7330F3852 color"),
        (legacy_models["7330G3351"].get("function"), "single_stage_heat_cool",
         "7330G3351 legacy function"),
        (legacy_models["7330G3351"].get("voltage"), "12VDC", "7330G3351 voltage"),
        (replacement_models["9420-351"].get("function"), "heat_cool",
         "9420-351 function"),
        (replacement_models["9420-351"].get("color"), "black", "9420-351 color"),
        (replacement_models["9420-351"].get("voltage"), "12VDC", "9420-351 voltage"),
    )
    for actual, expected, label in source_checks:
        if actual != expected:
            raise ValueError(f"unexpected {label}: {actual!r}")

    attribute_specs = {
        "7330G3351": (
            ("function", "heat_cool", "manufacturer_page", product_row),
            ("color", "white", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "manufacturer_pdf", legacy_row),
            ("voltage", "12VDC", "manufacturer_pdf", legacy_row),
        ),
        "7330F3852": (
            ("function", "heat_cool", "manufacturer_page", product_row),
            ("color", "black", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "manufacturer_page_inferred", product_row),
        ),
        "9420-351": (
            ("function", "heat_cool", "manufacturer_pdf", replacement_row),
            ("color", "black", "manufacturer_pdf", replacement_row),
            ("interface_type", "analog", "manufacturer_pdf", replacement_row),
            ("voltage", "12VDC", "manufacturer_pdf", replacement_row),
        ),
    }
    results = []
    for model in COLEMAN_ENDPOINT_MODELS:
        component_id = component_ids[model]
        component = Component(component_id, THERMOSTAT_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", model, None)]
        attributes = [text_attr(component_id, name, value, provenance, source_row)
                      for name, value, provenance, source_row in attribute_specs[model]]
        results.append((component, identifiers, attributes))
    return results


def identifier_candidate_from_observation(obs_row):
    attrs = _normalized_attributes(obs_row)
    relation = attrs.get("sku_relationship")
    models = attrs.get("model_spec_table")
    if not isinstance(relation, dict) or relation.get("type") != \
            "retailer_claimed_same_part":
        raise ValueError(f"observation #{obs_row['id']} has no retailer same-part claim")
    values = relation.get("identifiers")
    if values != ["AR7815", "7330F3858"] or not isinstance(models, dict):
        raise ValueError(f"unexpected identifier-equivalence claim: {relation}")
    namespaces = {value: models.get(value, {}).get("namespace") for value in values}
    if namespaces != {"AR7815": "icm", "7330F3858": "coleman"}:
        raise ValueError(f"unexpected identifier namespaces: {namespaces}")
    candidate = IdentifierEquivalenceCandidate(
        ns_a="icm", value_a="AR7815", ns_b="coleman", value_b="7330F3858")
    evidence = IdentifierEquivalenceEvidence(
        candidate_id=None, event_type="retailer_cross_reference",
        effect_alpha=2.0, effect_beta=1.0, occurred_at=now_iso(),
        source_observation_id=obs_row["id"])
    return candidate, evidence


def resolve_substitution_pair(conn, from_id, from_model, to_id, to_model, group_key):
    """
    Derive the two directed substitutes edges between from_id and to_id
    using suburban_parser.compare_models, and persist them (edges,
    edge_substitution_detail, edge_caveat, prior relationship_evidence).

    Returns (edge_from_to_id, edge_to_from_id).
    """
    cmp = compare_models(from_model, to_model)
    if cmp["verdict"] not in ("symmetric", "asymmetric"):
        raise ValueError(f"{from_model}/{to_model}: not a substitutable pair "
                          f"(verdict={cmp['verdict']}, reasons={cmp.get('reasons')})")

    basis = "attribute_match_exact"
    edge_ids = []
    for _, src_id, dst_id, cmp_key in (
        ("a_to_b", from_id, to_id, "a_to_b"), ("b_to_a", to_id, from_id, "b_to_a"),
    ):
        verdict_info = cmp[cmp_key]
        edge = Edge(type="substitutes", from_component_id=src_id, to_component_id=dst_id,
                    group_key=group_key)
        insert_edge(conn, edge)

        insert_substitution_detail(conn, EdgeSubstitutionDetail(
            edge_id=edge.id, basis=basis, verdict=verdict_info["verdict"]))

        for caveat_text in verdict_info.get("blocking_caveats", []):
            insert_caveat(conn, EdgeCaveat(edge_id=edge.id, blocking=True, text=caveat_text))

        alpha, beta = prior_for_basis(basis)
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type="attribute_prior", effect_alpha=alpha,
            effect_beta=beta, occurred_at=now_iso()))

        edge_ids.append(edge.id)

    return tuple(edge_ids)


def resolve_coleman_supersessions(conn, replacement_row, retailer_rows, component_ids):
    manufacturer = _normalized_attributes(replacement_row)
    expected_manufacturer_relation = {
        "type": "manufacturer_supersedes",
        "from": ["7330G3351", "7330F3852"],
        "to": "9420-351",
    }
    if manufacturer.get("sku_relationship") != expected_manufacturer_relation:
        raise ValueError("unexpected manufacturer supersession relation")
    if set(component_ids) != set(COLEMAN_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman endpoint ID map: {component_ids}")
    if "c_placeholder_tstat" in component_ids.values():
        raise ValueError("in-hand thermostat cannot be a catalog endpoint")
    if len(set(component_ids.values())) != 3:
        raise ValueError("Coleman endpoint components must be distinct")

    retailer_by_model = {}
    for row in retailer_rows:
        attrs = _normalized_attributes(row)
        relation = attrs.get("sku_relationship")
        if not isinstance(relation, dict) or relation.get("type") != "retailer_replacement":
            raise ValueError(f"observation #{row['id']} lacks a retailer replacement")
        retired_model = relation.get("from")
        if retired_model not in ("7330G3351", "7330F3852") or \
                relation.get("to") != "9420-351":
            raise ValueError(f"unexpected retailer replacement pair: {relation}")
        claim = attrs.get("replacement_claim")
        if claim != {"function": "same", "wiring": "same", "mounting": "same",
                     "compatibility": "same"}:
            raise ValueError(f"incomplete retailer replacement claim: {claim}")
        if retired_model in retailer_by_model:
            raise ValueError(f"duplicate retailer row for {retired_model}")
        retailer_by_model[retired_model] = row
    if set(retailer_by_model) != {"7330G3351", "7330F3852"}:
        raise ValueError("both retired endpoint retailer rows are required")

    existing = conn.execute(
        "SELECT component_id FROM components WHERE component_id IN (?, ?, ?)",
        tuple(component_ids[m] for m in COLEMAN_ENDPOINT_MODELS)).fetchall()
    if {row["component_id"] for row in existing} != set(component_ids.values()):
        raise ValueError("all Coleman endpoint components must exist before edge resolution")

    edge_ids = []
    for retired_model in ("7330G3351", "7330F3852"):
        edge = Edge(
            type="supersedes",
            from_component_id=component_ids[retired_model],
            to_component_id=component_ids["9420-351"],
            group_key="coleman_analog_heat_cool_12v",
            status="candidate",
            resolver_version=COLEMAN_ENDPOINT_RESOLVER_VERSION,
            notes="Coleman catalog names 9420-351 as the current replacement",
        )
        insert_edge(conn, edge)
        insert_supersession_detail(conn, EdgeSupersessionDetail(
            edge_id=edge.id,
            note=f"Coleman 2025 catalog names 9420-351 as the replacement for "
                 f"{retired_model}."))
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, replacement_row["id"]),
            ("retailer_cross_reference", 1.0, 0.0,
             retailer_by_model[retired_model]["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id,
                occurred_at=now_iso()))
        edge_ids.append(edge.id)
    return tuple(edge_ids)


def self_test(verbose=False):
    obs_db = str(Path(__file__).parent / "observations.db")
    failures = []

    obs1 = load_observation(obs_db, 1)  # SW6DEL
    obs2 = load_observation(obs_db, 2)  # SW6DE
    obs40 = load_observation(obs_db, 40)  # Coleman product page
    obs41 = load_observation(obs_db, 41)  # Coleman replacement sheet
    obs42 = load_observation(obs_db, 42)  # Coleman legacy catalog
    obs43 = load_observation(obs_db, 43)  # retailer identifier candidate
    obs44 = load_observation(obs_db, 44)  # in-hand thermostat
    obs45 = load_observation(obs_db, 45)  # terminal functions
    obs46 = load_observation(obs_db, 46)  # PCB positions
    obs47 = load_observation(obs_db, 47)  # voltage/stages supplement
    obs48 = load_observation(obs_db, 48)  # 7330G3351 retailer replacement
    obs49 = load_observation(obs_db, 49)  # 7330F3852 retailer replacement

    thermostat, thermostat_ids, thermostat_attrs = thermostat_from_observations(
        obs44, obs45, obs46, obs47, "c_placeholder_tstat")
    if (thermostat.component_id, thermostat.part_type_id,
            thermostat.interchange_code) != ("c_placeholder_tstat", 415, "415-0012-A"):
        failures.append(f"thermostat component mismatch: {thermostat}")
    expected_ids = {
        ("icm", "AP7862"), ("coleman", "7330G335"),
        ("silkscreen", "PCB1060"), ("silkscreen", "SPCB-2"),
    }
    actual_ids = {(i.ns, i.value) for i in thermostat_ids}
    if actual_ids != expected_ids or any(i.visibility != "behind_faceplate"
                                          for i in thermostat_ids):
        failures.append(f"thermostat identifiers mismatch: {thermostat_ids}")
    if len(thermostat_attrs) != 26:
        failures.append(f"expected 26 thermostat attributes, got {len(thermostat_attrs)}")
    expected_attribute_sources = {
        "terminal_order": (44, "in_hand", 6),
        "terminal_board_position": (46, "in_hand", 6),
        "installed_wire_color": (44, "in_hand", 6),
        "terminal_function": (45, "manufacturer_pdf", 6),
        "voltage": (47, "manufacturer_pdf", 1),
        "stages": (47, "manufacturer_pdf_inferred", 1),
    }
    for name, (source_id, provenance, count) in expected_attribute_sources.items():
        selected = [a for a in thermostat_attrs if a.name == name]
        if len(selected) != count or any(
                a.source_observation_id != source_id or a.provenance != provenance
                for a in selected):
            failures.append(
                f"{name} must have {count} row(s) from obs #{source_id} / {provenance}: "
                f"{selected}")

    def changed_row(row, mutate):
        changed = dict(row)
        extracted = json.loads(changed["extracted"])
        mutate(extracted)
        changed["extracted"] = json.dumps(extracted)
        return changed

    endpoint_ids = {
        "7330G3351": "c_placeholder_tstat_7330g3351",
        "7330F3852": "c_placeholder_tstat_7330f3852",
        "9420-351": "c_placeholder_tstat_9420_351",
    }
    endpoints = coleman_endpoint_components(obs40, obs41, obs42, endpoint_ids)
    by_model = {
        identifiers[0].value: (component, identifiers, attributes)
        for component, identifiers, attributes in endpoints
    }
    if set(by_model) != set(endpoint_ids):
        failures.append(f"Coleman endpoint set mismatch: {set(by_model)}")
    for model, (component, identifiers, attributes) in by_model.items():
        if component.part_type_id != 415 or component.interchange_code is not None:
            failures.append(f"invalid endpoint component: {component}")
        if [(i.ns, i.value, i.visibility) for i in identifiers] != [
                ("coleman", model, None)]:
            failures.append(f"invalid endpoint identifiers for {model}: {identifiers}")

    expected = {
        "7330G3351": {
            "function": ("heat_cool", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "color": ("white", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "interface_type": (
                "analog", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "stages": ("single", 42, "manufacturer_pdf", "coleman_endpoint_v1"),
            "voltage": ("12VDC", 42, "manufacturer_pdf", "coleman_endpoint_v1"),
        },
        "7330F3852": {
            "function": ("heat_cool", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "color": ("black", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "interface_type": (
                "analog", 40, "manufacturer_page", "coleman_endpoint_v1"),
            "stages": (
                "single", 40, "manufacturer_page_inferred", "coleman_endpoint_v1"),
        },
        "9420-351": {
            "function": ("heat_cool", 41, "manufacturer_pdf", "coleman_endpoint_v1"),
            "color": ("black", 41, "manufacturer_pdf", "coleman_endpoint_v1"),
            "interface_type": (
                "analog", 41, "manufacturer_pdf", "coleman_endpoint_v1"),
            "voltage": ("12VDC", 41, "manufacturer_pdf", "coleman_endpoint_v1"),
        },
    }
    forbidden_endpoint_attributes = {
        "terminal_order", "terminal_function", "terminal_board_position",
    }
    for model, (_, _, attributes) in by_model.items():
        actual = {
            attribute.name: (
                attribute.value_text, attribute.source_observation_id,
                attribute.provenance, attribute.resolver_version)
            for attribute in attributes
        }
        if actual != expected[model]:
            failures.append(f"Coleman endpoint attributes mismatch for {model}: {actual}")
        attached_forbidden = {
            attribute.name for attribute in attributes
        } & forbidden_endpoint_attributes
        if attached_forbidden:
            failures.append(
                f"forbidden Coleman endpoint attributes for {model}: {attached_forbidden}")

    invalid_endpoint_inputs = (
        (changed_row(obs40, lambda e: e["models"].pop("7330F3852")), obs41, obs42),
        (obs40, changed_row(obs41, lambda e: e["relation"].__setitem__(
            "from", ["7330G335", "7330F3852"])), obs42),
        (obs40, changed_row(obs41, lambda e: e["relation"].__setitem__(
            "to", "7330F3858")), obs42),
        (dict(obs40, id=400), obs41, obs42),
        (obs40, dict(obs41, id=410), obs42),
        (obs40, obs41, dict(obs42, id=420)),
        (dict(obs40, source_type="retailer_page"), obs41, obs42),
        (obs40, dict(obs41, source_type="retailer_pdf"), obs42),
        (obs40, obs41, dict(obs42, source_type="retailer_pdf")),
    )
    for product, replacement, legacy in invalid_endpoint_inputs:
        try:
            coleman_endpoint_components(product, replacement, legacy, endpoint_ids)
            failures.append("invalid Coleman endpoint evidence was accepted")
        except ValueError:
            pass

    for forbidden_model in ("7330G335", "7330F3858"):
        invalid_endpoint_ids = dict(endpoint_ids)
        invalid_endpoint_ids[forbidden_model] = f"c_forbidden_{forbidden_model.lower()}"
        try:
            coleman_endpoint_components(obs40, obs41, obs42, invalid_endpoint_ids)
            failures.append(f"forbidden Coleman endpoint ID was accepted: {forbidden_model}")
        except ValueError:
            pass

    invalid_inputs = (
        (changed_row(obs44, lambda e: e["wire_colors"].pop("B")), obs45, obs46, obs47),
        (obs44, changed_row(obs45, lambda e: e["terminal_functions"].pop("B")), obs46, obs47),
        (changed_row(obs44, lambda e: e.__setitem__(
            "terminal_order", ["R", "Y", "W", "GL", "GH", "GH"])), obs45, obs46, obs47),
        (changed_row(obs44, lambda e: e["identifiers_observed"].append(
            {"ns": "icm", "value": "AR7815", "visibility": "behind_faceplate"})),
         obs45, obs46, obs47),
    )
    for invalid in invalid_inputs:
        try:
            thermostat_from_observations(*invalid, "c_invalid")
            failures.append("invalid thermostat evidence was accepted")
        except ValueError:
            pass

    candidate, candidate_evidence = identifier_candidate_from_observation(obs43)
    if (candidate.ns_a, candidate.value_a, candidate.ns_b, candidate.value_b,
            candidate.status) != ("icm", "AR7815", "coleman", "7330F3858", "open"):
        failures.append(f"identifier candidate mismatch: {candidate}")
    if (candidate_evidence.event_type, candidate_evidence.effect_alpha,
            candidate_evidence.effect_beta, candidate_evidence.source_observation_id) != (
            "retailer_cross_reference", 2.0, 1.0, 43):
        failures.append(f"identifier candidate evidence mismatch: {candidate_evidence}")

    comp_6del, ids_6del = component_from_observation(
        obs1, "c_placeholder_wh_6del", WATER_HEATER_PART_TYPE)
    comp_6de, ids_6de = component_from_observation(
        obs2, "c_placeholder_wh_6de", WATER_HEATER_PART_TYPE)

    if comp_6del.component_id != "c_placeholder_wh_6del":
        failures.append("SW6DEL component_id mismatch")
    if not any(i.value == "SW6DEL" for i in ids_6del):
        failures.append(f"expected SW6DEL identifier, got {ids_6del}")
    if not any(i.value == "5240A" for i in ids_6del):
        failures.append(f"expected 5240A sku identifier, got {ids_6del}")
    if not any(i.value == "5140A" for i in ids_6del):
        failures.append(f"expected 5140A legacy-sku identifier (from aliases_mentioned "
                         f"canonicalizing into sku), got {ids_6del}")
    if not any(i.value == "SW6DE" for i in ids_6de):
        failures.append(f"expected SW6DE identifier, got {ids_6de}")

    store_conn = init_db(":memory:")
    insert_component(store_conn, comp_6de)
    for ident in ids_6de:
        insert_identifier(store_conn, ident)
    insert_component(store_conn, comp_6del)
    for ident in ids_6del:
        insert_identifier(store_conn, ident)

    edge_de_to_del, edge_del_to_de = resolve_substitution_pair(
        store_conn, "c_placeholder_wh_6de", "SW6DE",
        "c_placeholder_wh_6del", "SW6DEL", "412-0087")

    de_to_del_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_de_to_del,)).fetchone()
    if de_to_del_detail["verdict"] != "drop_in":
        failures.append(f"SW6DE->SW6DEL should be drop_in, got {de_to_del_detail['verdict']}")

    del_to_de_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_del_to_de,)).fetchone()
    if del_to_de_detail["verdict"] != "fits_with_caveat":
        failures.append(
            f"SW6DEL->SW6DE should be fits_with_caveat, got {del_to_de_detail['verdict']}")

    del_to_de_caveats = get_caveats_for_edge(store_conn, edge_del_to_de)
    if len(del_to_de_caveats) != 1:
        failures.append(f"expected exactly 1 caveat SW6DEL->SW6DE, got {del_to_de_caveats}")

    evidence = get_evidence_for_edge(store_conn, edge_de_to_del)
    confidence = compute_confidence(evidence)
    if confidence["value"] != 0.75 or confidence["certainty"] != 4.0:
        failures.append(f"expected prior confidence 0.75/n=4, got {confidence}")

    def persist_endpoints(conn):
        for component, identifiers, attributes in endpoints:
            insert_component(conn, component)
            for identifier in identifiers:
                insert_identifier(conn, identifier)
            for attribute in attributes:
                insert_component_attribute(conn, attribute)

    persist_endpoints(store_conn)
    edge_ids = resolve_coleman_supersessions(
        store_conn, obs41, [obs48, obs49], endpoint_ids)
    if len(edge_ids) != 2:
        failures.append(f"expected two Coleman supersession edges, got {edge_ids}")
    rows = store_conn.execute(
        "SELECT * FROM edges WHERE id IN (?, ?) ORDER BY id", edge_ids).fetchall()
    expected_pairs = [
        (endpoint_ids["7330G3351"], endpoint_ids["9420-351"]),
        (endpoint_ids["7330F3852"], endpoint_ids["9420-351"]),
    ]
    actual_pairs = [(r["from_component_id"], r["to_component_id"]) for r in rows]
    if actual_pairs != expected_pairs:
        failures.append(f"Coleman supersession direction mismatch: {actual_pairs}")
    for row, retailer_observation_id in zip(rows, (48, 49)):
        actual_edge_fields = (
            row["type"], row["status"], row["group_key"], row["resolver_version"])
        expected_edge_fields = (
            "supersedes", "candidate", "coleman_analog_heat_cool_12v",
            "coleman_endpoint_v1")
        if actual_edge_fields != expected_edge_fields:
            failures.append(f"Coleman supersession edge fields mismatch: {actual_edge_fields}")
        if get_supersession_detail(store_conn, row["id"]) is None:
            failures.append(f"Coleman supersession detail missing for edge #{row['id']}")
        edge_evidence = get_evidence_for_edge(store_conn, row["id"])
        actual_evidence = [
            (item.event_type, item.effect_alpha, item.effect_beta,
             item.source_observation_id)
            for item in edge_evidence
        ]
        expected_evidence = [
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, 41),
            ("retailer_cross_reference", 1.0, 0.0, retailer_observation_id),
        ]
        if actual_evidence != expected_evidence:
            failures.append(
                f"Coleman supersession evidence mismatch for edge #{row['id']}: "
                f"{actual_evidence}")
        edge_confidence = compute_confidence(edge_evidence)
        if edge_confidence != {"alpha": 4.0, "beta": 1.0, "value": 0.8,
                               "certainty": 5.0}:
            failures.append(
                f"Coleman supersession confidence mismatch: {edge_confidence}")

    invalid_manufacturer_rows = (
        changed_row(obs41, lambda e: e.__setitem__("relation", {
            "type": "manufacturer_supersedes", "from": ["9420-351"],
            "to": "7330G3351"})),
        changed_row(obs41, lambda e: e["relation"].__setitem__(
            "from", ["7330G3351"])),
        changed_row(obs41, lambda e: e["relation"].pop("to")),
        changed_row(obs41, lambda e: e["relation"]["from"].append("7330G335")),
        changed_row(obs41, lambda e: e["relation"]["from"].append("9420-351")),
    )
    rejection_inputs = [
        (row, [obs48, obs49], endpoint_ids, True)
        for row in invalid_manufacturer_rows
    ]
    rejection_inputs.extend((
        (obs41, [changed_row(obs48, lambda e: e["relation"].__setitem__(
            "to", "7330F3852")), obs49], endpoint_ids, True),
        (obs41, [obs48, obs49], dict(endpoint_ids, **{
            "7330G3351": "c_placeholder_tstat"}), True),
        (obs41, [obs48, obs49], endpoint_ids, False),
    ))
    for replacement, retailers, ids, should_persist_endpoints in rejection_inputs:
        rejected_conn = init_db(":memory:")
        if should_persist_endpoints:
            if ids == endpoint_ids:
                persist_endpoints(rejected_conn)
            else:
                invalid_endpoints = coleman_endpoint_components(obs40, obs41, obs42, ids)
                for component, identifiers, attributes in invalid_endpoints:
                    insert_component(rejected_conn, component)
                    for identifier in identifiers:
                        insert_identifier(rejected_conn, identifier)
                    for attribute in attributes:
                        insert_component_attribute(rejected_conn, attribute)
        try:
            resolve_coleman_supersessions(rejected_conn, replacement, retailers, ids)
            failures.append("invalid Coleman supersession evidence was accepted")
        except ValueError:
            pass
        rejected_edges = rejected_conn.execute(
            "SELECT id FROM edges WHERE group_key = ?",
            ("coleman_analog_heat_cool_12v",)).fetchall()
        if rejected_edges:
            failures.append(
                f"Coleman supersession rejection wrote edges: {rejected_edges}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: both anchor components built from observations #1 and #2")
        print("PASS: SW6DE/SW6DEL substitution edge pair derived with correct "
              "verdicts, caveats, and prior confidence")
    print("self_test: PASS")
    return 0


def _find_fixture_edge(edges_doc, a_id, b_id):
    for e in edges_doc:
        if e.get("type") == "substitutes" and e.get("a") == a_id and e.get("b") == b_id:
            return e
    return None


def check_fixture(ground_truth_path, obs_db_path):
    try:
        import yaml
    except ImportError:
        print("pyyaml not installed", file=sys.stderr)
        return 1

    docs = [d for d in yaml.safe_load_all(open(ground_truth_path)) if d]
    components_doc = next(
        (d["components"] for d in docs if isinstance(d, dict) and "components" in d), [])
    edges_doc = next((d["edges"] for d in docs if isinstance(d, dict) and "edges" in d), [])
    fixture_edge = _find_fixture_edge(edges_doc, "c_placeholder_wh_6de",
                                       "c_placeholder_wh_6del")
    if fixture_edge is None:
        print("FAIL: ground-truth.yaml has no c_placeholder_wh_6de -> "
              "c_placeholder_wh_6del substitutes edge")
        return 1

    obs1 = load_observation(obs_db_path, 1)
    obs2 = load_observation(obs_db_path, 2)
    comp_6del, ids_6del = component_from_observation(
        obs1, "c_placeholder_wh_6del", WATER_HEATER_PART_TYPE)
    comp_6de, ids_6de = component_from_observation(
        obs2, "c_placeholder_wh_6de", WATER_HEATER_PART_TYPE)

    conn = init_db(":memory:")
    insert_component(conn, comp_6de)
    for ident in ids_6de:
        insert_identifier(conn, ident)
    insert_component(conn, comp_6del)
    for ident in ids_6del:
        insert_identifier(conn, ident)

    edge_de_to_del, edge_del_to_de = resolve_substitution_pair(
        conn, "c_placeholder_wh_6de", "SW6DE",
        "c_placeholder_wh_6del", "SW6DEL", "412-0087")

    mismatches = 0

    fixture_group = fixture_edge.get("group")
    resolved_group = conn.execute(
        "SELECT group_key FROM edges WHERE id = ?", (edge_de_to_del,)).fetchone()["group_key"]
    if fixture_group != resolved_group:
        print(f"MISMATCH group_key: fixture={fixture_group} resolved={resolved_group}")
        mismatches += 1

    for label, edge_id, fixture_key in (
        ("a_to_b", edge_de_to_del, "a_to_b"), ("b_to_a", edge_del_to_de, "b_to_a"),
    ):
        fixture_verdict = fixture_edge[fixture_key]["verdict"]
        resolved_verdict = conn.execute(
            "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
            (edge_id,)).fetchone()["verdict"]
        if fixture_verdict != resolved_verdict:
            print(f"MISMATCH {label} verdict: fixture={fixture_verdict} "
                  f"resolved={resolved_verdict}")
            mismatches += 1
        print(f"  {label}: verdict={resolved_verdict} (fixture={fixture_verdict})")

    fixture_conf = fixture_edge["confidence"]
    evidence = get_evidence_for_edge(conn, edge_de_to_del)
    resolved_conf = compute_confidence(evidence)
    if (resolved_conf["value"], resolved_conf["certainty"]) != \
            (fixture_conf["value"], fixture_conf["certainty"]):
        print(f"MISMATCH confidence: fixture={fixture_conf} resolved={resolved_conf}")
        mismatches += 1

    print(f"\nSuburban edge: {mismatches} mismatch(es)")

    fixture_thermostat = next(
        (c for c in components_doc if c.get("component_id") == "c_placeholder_tstat"),
        None)
    if fixture_thermostat is None:
        print("MISMATCH thermostat: fixture component missing")
        mismatches += 1
    else:
        thermostat_mismatches_before = mismatches
        obs43 = load_observation(obs_db_path, 43)
        obs44 = load_observation(obs_db_path, 44)
        obs45 = load_observation(obs_db_path, 45)
        obs46 = load_observation(obs_db_path, 46)
        obs47 = load_observation(obs_db_path, 47)
        thermostat, thermostat_ids, thermostat_attrs = thermostat_from_observations(
            obs44, obs45, obs46, obs47, "c_placeholder_tstat")
        insert_component(conn, thermostat)
        for identifier in thermostat_ids:
            insert_identifier(conn, identifier)
        for attribute in thermostat_attrs:
            insert_component_attribute(conn, attribute)

        if thermostat.part_type_id != fixture_thermostat.get("part_type_id") or \
                thermostat.interchange_code != fixture_thermostat.get("interchange_code"):
            print(f"MISMATCH thermostat component: resolved={thermostat} "
                  f"fixture={fixture_thermostat}")
            mismatches += 1

        expected_identifiers = {
            (i["ns"], str(i["value"]), i["visibility"])
            for i in fixture_thermostat.get("identifiers", [])
        }
        resolved_identifiers = {(i.ns, i.value, i.visibility) for i in thermostat_ids}
        if resolved_identifiers != expected_identifiers:
            print(f"MISMATCH thermostat identifiers: resolved={resolved_identifiers} "
                  f"fixture={expected_identifiers}")
            mismatches += 1

        resolved_attrs = get_component_attributes(conn, thermostat.component_id)
        by_name = {}
        for attr in resolved_attrs:
            value = attr.value_text if attr.value_text is not None else (
                attr.value_number if attr.value_number is not None else attr.value_boolean)
            by_name.setdefault(attr.name, {})[attr.qualifier] = value

        fixture_attrs = fixture_thermostat["attributes"]
        expected_order = fixture_attrs["terminal_order"]["value"]
        resolved_order = [label for label, _ in sorted(
            by_name.get("terminal_order", {}).items(), key=lambda item: item[1])]
        if resolved_order != expected_order:
            print(f"MISMATCH thermostat order: resolved={resolved_order} "
                  f"fixture={expected_order}")
            mismatches += 1

        expected_map = fixture_attrs["terminal_map"]["value"]
        for terminal in THERMOSTAT_TERMINALS:
            expected_position = expected_map[terminal]["board_position"]
            expected_function = expected_map[terminal]["function"]
            if by_name.get("terminal_board_position", {}).get(terminal) != expected_position:
                print(f"MISMATCH {terminal} board position")
                mismatches += 1
            if by_name.get("terminal_function", {}).get(terminal) != expected_function:
                print(f"MISMATCH {terminal} terminal function")
                mismatches += 1

        expected_colors = fixture_attrs["installed_wire_colors"]["value"]
        if by_name.get("installed_wire_color") != expected_colors:
            print(f"MISMATCH installed wire colors: "
                  f"resolved={by_name.get('installed_wire_color')} fixture={expected_colors}")
            mismatches += 1
        for scalar in ("voltage", "stages"):
            resolved = by_name.get(scalar, {}).get("")
            expected = fixture_attrs[scalar]["value"]
            if resolved != expected:
                print(f"MISMATCH thermostat {scalar}: resolved={resolved} fixture={expected}")
                mismatches += 1

        candidate, candidate_evidence = identifier_candidate_from_observation(obs43)
        insert_identifier_equivalence_candidate(conn, candidate)
        candidate_evidence.candidate_id = candidate.id
        insert_identifier_equivalence_evidence(conn, candidate_evidence)
        candidates = get_identifier_equivalence_candidates(conn, status="open")
        fixture_candidates = next(
            (d.get("identifier_equivalence_candidates", []) for d in docs
             if isinstance(d, dict) and "identifier_equivalence_candidates" in d), [])
        if len(candidates) != 1 or len(fixture_candidates) != 1:
            print(f"MISMATCH identifier candidate counts: resolved={len(candidates)} "
                  f"fixture={len(fixture_candidates)}")
            mismatches += 1
        else:
            fixture_candidate = fixture_candidates[0]
            resolved_pair = (candidates[0].ns_a, candidates[0].value_a,
                             candidates[0].ns_b, candidates[0].value_b)
            expected_pair = (fixture_candidate["a"]["ns"],
                             str(fixture_candidate["a"]["value"]),
                             fixture_candidate["b"]["ns"],
                             str(fixture_candidate["b"]["value"]))
            if resolved_pair != expected_pair:
                print(f"MISMATCH identifier candidate: resolved={resolved_pair} "
                      f"fixture={expected_pair}")
                mismatches += 1
            evidence = get_identifier_equivalence_evidence(conn, candidates[0].id)
            expected_confidence = fixture_candidate["confidence"]
            if len(evidence) != 1 or (evidence[0].effect_alpha,
                    evidence[0].effect_beta, evidence[0].source_observation_id) != (
                    float(expected_confidence["alpha"]),
                    float(expected_confidence["beta"]), 43):
                print(f"MISMATCH identifier candidate evidence: {evidence}")
                mismatches += 1

        forbidden = {"AR7815", "AR7816", "AP7862-3", "PCB1060-4A",
                     "7330G3351", "7330F3858"}
        attached_forbidden = {i.value for i in thermostat_ids} & forbidden
        if attached_forbidden:
            print(f"MISMATCH candidate identifiers attached to thermostat: {attached_forbidden}")
            mismatches += 1
        thermostat_edges = conn.execute(
            "SELECT type FROM edges WHERE (from_component_id = ? OR to_component_id = ?) "
            "AND type IN ('substitutes', 'supersedes')",
            (thermostat.component_id, thermostat.component_id)).fetchall()
        if thermostat_edges:
            print(f"MISMATCH unsupported thermostat edges: {thermostat_edges}")
            mismatches += 1

        print(f"Thermostat fixture: "
              f"{mismatches - thermostat_mismatches_before} mismatch(es)")

    coleman_mismatches_before = mismatches
    endpoint_ids = {
        "7330G3351": "c_placeholder_tstat_7330g3351",
        "7330F3852": "c_placeholder_tstat_7330f3852",
        "9420-351": "c_placeholder_tstat_9420_351",
    }
    fixture_endpoint_rows = [
        component for component in components_doc
        if component.get("component_id") in set(endpoint_ids.values())
    ]
    fixture_endpoints = {
        component["component_id"]: component for component in fixture_endpoint_rows
    }
    if len(fixture_endpoint_rows) != 3 or set(fixture_endpoints) != set(endpoint_ids.values()):
        print(f"MISMATCH Coleman endpoint fixture set: "
              f"count={len(fixture_endpoint_rows)} ids={set(fixture_endpoints)}")
        mismatches += 1

    # Load the complete evidence slice, including the observation-only visual
    # candidate, before deriving the fixture graph.
    obs40 = load_observation(obs_db_path, 40)
    obs41 = load_observation(obs_db_path, 41)
    obs42 = load_observation(obs_db_path, 42)
    obs48 = load_observation(obs_db_path, 48)
    obs49 = load_observation(obs_db_path, 49)
    obs50 = load_observation(obs_db_path, 50)

    endpoints = coleman_endpoint_components(obs40, obs41, obs42, endpoint_ids)
    for endpoint, identifiers, attributes in endpoints:
        insert_component(conn, endpoint)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)
    resolve_coleman_supersessions(conn, obs41, [obs48, obs49], endpoint_ids)

    for component_id, fixture_component in fixture_endpoints.items():
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if resolved_component is None:
            print(f"MISMATCH Coleman endpoint missing: {component_id}")
            mismatches += 1
            continue
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Coleman endpoint component: resolved={dict(resolved_component)} "
                  f"fixture={fixture_component}")
            mismatches += 1

        resolved_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        expected_identifiers = {
            (identifier["ns"], str(identifier["value"]), identifier.get("visibility"))
            for identifier in fixture_component["identifiers"]
        }
        if resolved_identifiers != expected_identifiers:
            print(f"MISMATCH Coleman endpoint identifiers for {component_id}: "
                  f"resolved={resolved_identifiers} fixture={expected_identifiers}")
            mismatches += 1

        resolved_attribute_rows = get_component_attributes(conn, component_id)
        resolved_attributes = {}
        for attribute in resolved_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_component["attributes"].items()
        }
        if (len(resolved_attribute_rows) != len(expected_attributes)
                or resolved_attributes != expected_attributes):
            print(f"MISMATCH Coleman endpoint attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    fixture_supersession_rows = [
        edge for edge in edges_doc if edge.get("type") == "supersedes"
    ]
    fixture_supersessions = {
        (edge["from"], edge["to"]): edge for edge in fixture_supersession_rows
    }
    expected_pairs = {
        (endpoint_ids["7330G3351"], endpoint_ids["9420-351"]),
        (endpoint_ids["7330F3852"], endpoint_ids["9420-351"]),
    }
    if len(fixture_supersession_rows) != 2 or set(fixture_supersessions) != expected_pairs:
        print(f"MISMATCH Coleman fixture supersession pairs: "
              f"count={len(fixture_supersession_rows)} pairs={set(fixture_supersessions)}")
        mismatches += 1

    resolved_edges = conn.execute(
        "SELECT * FROM edges WHERE type = 'supersedes' AND group_key = ? ORDER BY id",
        ("coleman_analog_heat_cool_12v",)).fetchall()
    resolved_pairs = {
        (row["from_component_id"], row["to_component_id"]) for row in resolved_edges
    }
    if len(resolved_edges) != 2 or resolved_pairs != expected_pairs:
        print(f"MISMATCH Coleman resolved supersession pairs: "
              f"count={len(resolved_edges)} pairs={resolved_pairs}")
        mismatches += 1
    for row in resolved_edges:
        pair = (row["from_component_id"], row["to_component_id"])
        fixture_supersession = fixture_supersessions.get(pair)
        if fixture_supersession is None:
            continue
        resolved_fields = (
            row["type"], row["status"], row["group_key"], row["resolver_version"])
        expected_fields = (
            fixture_supersession["type"], fixture_supersession["status"],
            fixture_supersession["group"], COLEMAN_ENDPOINT_RESOLVER_VERSION)
        if resolved_fields != expected_fields:
            print(f"MISMATCH Coleman supersession fields for {pair}: "
                  f"resolved={resolved_fields} fixture={expected_fields}")
            mismatches += 1

        detail = get_supersession_detail(conn, row["id"])
        expected_note = fixture_supersession["detail"]["note"]
        if detail is None or detail.note != expected_note:
            print(f"MISMATCH Coleman supersession detail for {pair}: "
                  f"resolved={detail} fixture={expected_note}")
            mismatches += 1

        evidence = get_evidence_for_edge(conn, row["id"])
        resolved_evidence = [
            (item.event_type, item.effect_alpha, item.effect_beta,
             item.source_observation_id) for item in evidence
        ]
        expected_evidence = [
            (item["event_type"], float(item["alpha"]), float(item["beta"]),
             item["source_observation_id"])
            for item in fixture_supersession["evidence"]
        ]
        if resolved_evidence != expected_evidence:
            print(f"MISMATCH Coleman supersession evidence for {pair}: "
                  f"resolved={resolved_evidence} fixture={expected_evidence}")
            mismatches += 1
        resolved_confidence = compute_confidence(evidence)
        expected_confidence = fixture_supersession["confidence"]
        if resolved_confidence != {
                "alpha": float(expected_confidence["alpha"]),
                "beta": float(expected_confidence["beta"]),
                "value": float(expected_confidence["value"]),
                "certainty": float(expected_confidence["certainty"])}:
            print(f"MISMATCH Coleman supersession confidence for {pair}: "
                  f"resolved={resolved_confidence} fixture={expected_confidence}")
            mismatches += 1

    placeholder_promotions = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE type = 'supersedes' "
        "AND (from_component_id = 'c_placeholder_tstat' "
        "OR to_component_id = 'c_placeholder_tstat')").fetchone()[0]
    if placeholder_promotions != 0:
        print(f"MISMATCH Coleman in-hand supersession promotions: {placeholder_promotions}")
        mismatches += 1
    visual_identifier_promotions = conn.execute(
        "SELECT COUNT(*) FROM identifiers WHERE value = '8330-3362'").fetchone()[0]
    visual_candidate_promotions = conn.execute(
        "SELECT COUNT(*) FROM identifier_equivalence_candidate "
        "WHERE value_a = '8330-3362' OR value_b = '8330-3362'").fetchone()[0]
    if visual_identifier_promotions or visual_candidate_promotions:
        print("MISMATCH 8330-3362 escaped observation-only boundary: "
              f"identifiers={visual_identifier_promotions} "
              f"identifier_candidates={visual_candidate_promotions}")
        mismatches += 1
    fixture_component_ids = ("c_placeholder_tstat", *endpoint_ids.values())
    substitutes_placeholders = ", ".join("?" for _ in fixture_component_ids)
    coleman_substitutes = conn.execute(
        f"SELECT COUNT(*) FROM edges WHERE type = 'substitutes' "
        f"AND from_component_id IN ({substitutes_placeholders}) "
        f"AND to_component_id IN ({substitutes_placeholders})",
        (*fixture_component_ids, *fixture_component_ids)).fetchone()[0]
    if coleman_substitutes != 0:
        print(f"MISMATCH unsupported Coleman substitutes edges: {coleman_substitutes}")
        mismatches += 1

    # Loading observation #50 is deliberate: its visual candidate must remain
    # evidence-only and is guarded by the forbidden graph queries above.
    if obs50["id"] != 50:
        print(f"MISMATCH Coleman visual candidate observation: {obs50['id']}")
        mismatches += 1

    print(f"Coleman endpoints: {mismatches - coleman_mismatches_before} mismatch(es)")

    print(f"\n{mismatches} total mismatches against ground-truth.yaml")
    return 1 if mismatches else 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))
    if "--check-fixture" in sys.argv:
        idx = sys.argv.index("--check-fixture")
        fixture_path = sys.argv[idx + 1]
        obs_db = str(Path(__file__).parent / "observations.db")
        sys.exit(check_fixture(fixture_path, obs_db))


if __name__ == "__main__":
    main()
