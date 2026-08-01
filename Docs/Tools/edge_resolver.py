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
    EdgeSupersessionDetail, EdgeControlsDetail, EdgeCaveat, EdgeRequiredPart,
    RelationshipEvidence, IdentifierEquivalenceCandidate, IdentifierEquivalenceEvidence,
    prior_for_basis, compute_confidence,
)
from interchange_schema import init_db
from interchange_store import (
    insert_component, insert_identifier, insert_edge, insert_substitution_detail,
    insert_supersession_detail,
    insert_caveat, insert_evidence, now_iso, get_caveats_for_edge, get_evidence_for_edge,
    insert_component_attribute, get_component_attributes,
    insert_identifier_equivalence_candidate, insert_identifier_equivalence_evidence,
    get_identifier_equivalence_candidates, get_identifier_equivalence_evidence,
    get_supersession_detail, insert_required_part, get_required_parts_for_edge,
    insert_controls_detail, get_controls_detail,
)

WATER_HEATER_PART_TYPE = 412
THERMOSTAT_PART_TYPE = 415
THERMOSTAT_CODE = "415-0012-A"
COLEMAN_ENDPOINT_MODELS = ("7330G3351", "7330F3852", "9420-351")
COLEMAN_ENDPOINT_RESOLVER_VERSION = "coleman_endpoint_v1"
COLEMAN_VISUAL_MATCH_CANDIDATE = {
    "candidate": {"ns": "coleman", "value": "8330-3362"},
    "comparison_source_observation_id": 45,
    "manual_figure": "electronic_digital_display_thermostat",
    "status": "open",
    "basis": [
        "RVComfort.HC face", "left display", "up/down controls",
        "three lower slide controls",
    ],
    "caveat": "visual similarity does not prove model identity",
}
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


def resolve_12del_component(retailer_row, channel_split_row, component_id):
    """
    Build the vendor-researched SW12DEL component from observation #11 (retailer
    spec block + buyer review) and confirm its 5148A/5248A channel-split
    identifiers against observation #35 (Suburban support's direct reply).
    Deliberately reads the raw extracted JSON rather than going through
    resolver.normalize_extracted's compound cutout handler: that handler always
    collapses cutout_in into opening_h/opening_w and drops depth (see
    resolver.py's _derive_opening, VENDOR-Suburban.md 6.5), but ground-truth.yaml
    keeps this component's cutout_h/cutout_w/cutout_d as raw retailer figures —
    unlike SW6DE/SW6DEL, this pair hasn't been cross-validated against the
    manufacturer's 2D opening figure (obs #19).
    """
    _validate_observation_source(retailer_row, 11, "retailer_page", 7, "12DEL retailer")
    extracted = json.loads(retailer_row["extracted"])
    if extracted.get("model") != "SW12DEL":
        raise ValueError(f"unexpected 12DEL model: {extracted.get('model')}")
    cutout = extracted.get("cutout_in")
    weight = extracted.get("weight_lb")
    element_watts = extracted.get("element_watts")
    if cutout != {"h": 16.38, "w": 16.38, "d": 22.25}:
        raise ValueError(f"unexpected 12DEL cutout: {cutout}")
    if weight != {"empty": 48.0, "full": 148.08}:
        raise ValueError(f"unexpected 12DEL weight: {weight}")
    if element_watts != [1400, 1440]:
        raise ValueError(f"unexpected 12DEL element watts: {element_watts}")
    if extracted.get("capacity_gal") != 12 or extracted.get("input_btuh") != 12000:
        raise ValueError("unexpected 12DEL capacity/BTU")

    try:
        channel_split = json.loads(channel_split_row["extracted"])
    except (KeyError, TypeError) as exc:
        raise ValueError("12DEL channel-split observation lacks extracted JSON") from exc
    if channel_split.get("relation") != "co-current_channel_split" or \
            set(channel_split.get("skus", [])) != {"5148A", "5248A"}:
        raise ValueError(f"unexpected 12DEL channel-split evidence: {channel_split}")

    component = Component(component_id, WATER_HEATER_PART_TYPE)
    identifiers = [
        Identifier(component_id, "suburban", "SW12DEL", "exterior_plate"),
        Identifier(component_id, "suburban", "5248A", "none_marked"),
        Identifier(component_id, "suburban", "5148A", "none_marked"),
    ]
    obs_id = retailer_row["id"]
    attributes = [
        ComponentAttribute(component_id, "capacity_gal", "retailer_spec_block",
                            obs_id, value_number=12.0),
        ComponentAttribute(component_id, "input_btuh", "retailer_spec_block",
                            obs_id, value_number=12000.0),
        ComponentAttribute(component_id, "element_watts", "retailer_spec_block",
                            obs_id, qualifier="1400", value_number=1400.0),
        ComponentAttribute(component_id, "element_watts", "retailer_spec_block",
                            obs_id, qualifier="1440", value_number=1440.0),
        ComponentAttribute(component_id, "cutout_h", "retailer_spec_block",
                            obs_id, unit="in", value_number=16.38),
        ComponentAttribute(component_id, "cutout_w", "retailer_spec_block",
                            obs_id, unit="in", value_number=16.38),
        ComponentAttribute(component_id, "cutout_d", "retailer_spec_block",
                            obs_id, unit="in", value_number=22.25),
        ComponentAttribute(component_id, "weight_empty", "retailer_spec_block",
                            obs_id, unit="lb", value_number=48.0),
        ComponentAttribute(component_id, "weight_full", "retailer_spec_block",
                            obs_id, unit="lb", value_number=148.08),
    ]
    return component, identifiers, attributes


_IGNITION_TEXT_TO_TYPE = {"Direct Spark Ignition": "direct_spark"}


def resolve_iw60rl_component(retailer_row, manual_row, component_id):
    """
    Build the vendor-researched IW60RL (tankless) component from observation
    #13 (retailer page) plus observation #14 (Nautilus service manual) for the
    manufacturer-documented vent hole diameter and cross-corroborating product
    depth. No cutout: this is a tankless platform (see ground-truth.yaml's
    part_type 412 TODO on the framed-opening/vent-hole split).
    """
    _validate_observation_source(retailer_row, 13, "retailer_page", 7, "IW60RL retailer")
    _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
    retailer = json.loads(retailer_row["extracted"])
    manual = json.loads(manual_row["extracted"])

    if retailer.get("model") != "IW60RL" or retailer.get("sku") != "5280A":
        raise ValueError(f"unexpected IW60RL identity: {retailer}")
    if retailer.get("capacity_gal") != 0.5 or retailer.get("btu") != 60000:
        raise ValueError("unexpected IW60RL capacity/BTU")
    ignition_text = retailer.get("ignition_type")
    if ignition_text not in _IGNITION_TEXT_TO_TYPE:
        raise ValueError(f"unrecognized IW60RL ignition text: {ignition_text}")
    product_size = retailer.get("product_size_in")
    if product_size != {"w": 12.5, "h": 12.5, "d": 20}:
        raise ValueError(f"unexpected IW60RL product size: {product_size}")
    if retailer.get("weight_lb") != 36.0:
        raise ValueError(f"unexpected IW60RL weight: {retailer.get('weight_lb')}")

    if manual.get("vent_hole_diameter_in") != 3.75:
        raise ValueError(f"unexpected IW60RL vent hole diameter: "
                          f"{manual.get('vent_hole_diameter_in')}")
    if manual.get("dimensions_in") != {"h": 12.5, "w": 12.5, "d": 20.0}:
        raise ValueError(f"unexpected IW60RL manual dimensions: "
                          f"{manual.get('dimensions_in')}")

    component = Component(component_id, WATER_HEATER_PART_TYPE)
    identifiers = [
        Identifier(component_id, "suburban", "IW60RL", "exterior_plate"),
        Identifier(component_id, "suburban", "5280A", "none_marked"),
    ]
    retailer_id, manual_id = retailer_row["id"], manual_row["id"]
    attributes = [
        ComponentAttribute(component_id, "tankless", "retailer_spec_block",
                            retailer_id, value_boolean=True),
        ComponentAttribute(component_id, "capacity_gal", "retailer_spec_block",
                            retailer_id, value_number=0.5),
        ComponentAttribute(component_id, "input_btuh", "retailer_spec_block",
                            retailer_id, value_number=60000.0),
        ComponentAttribute(component_id, "ignition_type", "retailer_spec_block",
                            retailer_id, value_text=_IGNITION_TEXT_TO_TYPE[ignition_text]),
        ComponentAttribute(component_id, "vent_hole_diameter_in", "manufacturer_pdf",
                            manual_id, unit="in", value_number=3.750),
        ComponentAttribute(component_id, "product_size_h", "retailer_spec_block",
                            retailer_id, unit="in", value_number=12.5),
        ComponentAttribute(component_id, "product_size_w", "retailer_spec_block",
                            retailer_id, unit="in", value_number=12.5),
        ComponentAttribute(component_id, "product_size_d", "manufacturer_pdf",
                            manual_id, unit="in", value_number=20.0),
        ComponentAttribute(component_id, "weight_empty", "retailer_spec_block",
                            retailer_id, unit="lb", value_number=36.0),
    ]
    return component, identifiers, attributes


def resolve_atwood_family_components(manual_row, component_ids):
    """
    Build the two Atwood family-placeholder components (6-gallon, 10-gallon)
    from the Nautilus service manual's replacement-panel table (observation
    #14) — the only source in this project naming these families at all.
    Manufacturer-asserted family placeholders, not verified Atwood models: no
    identifiers, matching ground-truth.yaml.
    """
    _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
    manual = json.loads(manual_row["extracted"])
    panels = manual.get("replacement_panel_part_numbers")
    if not isinstance(panels, list):
        raise ValueError("IW60RL manual has no replacement panel table")
    by_capacity = {
        (panel.get("brand"), panel.get("capacities")): panel.get("part_number")
        for panel in panels
    }
    if by_capacity.get(("Atwood", "6 gallon")) != "521147":
        raise ValueError("manual is missing the Atwood 6-gallon replacement panel")
    if by_capacity.get(("Atwood", "10 gallon")) != "521150":
        raise ValueError("manual is missing the Atwood 10-gallon replacement panel")
    if set(component_ids) != {"6gal", "10gal"}:
        raise ValueError(f"unexpected Atwood component id map: {component_ids}")

    obs_id = manual_row["id"]
    results = {}
    for key, gallons in (("6gal", 6.0), ("10gal", 10.0)):
        component_id = component_ids[key]
        component = Component(component_id, WATER_HEATER_PART_TYPE)
        attributes = [
            ComponentAttribute(component_id, "capacity_gal", "manufacturer_pdf",
                                obs_id, value_number=gallons),
            ComponentAttribute(component_id, "brand", "manufacturer_pdf",
                                obs_id, value_text="Atwood"),
        ]
        results[key] = (component, [], attributes)
    return results


SWITCH_DEL_MODEL = "SW6DEL"
SWITCH_CONFIRMED_VARIANTS = {"232882": "white", "233111": "black"}


def resolve_switch_component(catalog_row, component_id):
    """
    Build the DEL-line interior switch component from observation #51
    (Suburban 2025 Aftermarket Catalog, interior switch part numbers).
    Only two of ground-truth.yaml's three claimed identifiers
    (232882/white, 233111/black) are backed by this observation — the third
    (232881/cream) does not appear in the captured source and is
    deliberately NOT attached here. See the catalog observation's
    coverage_gap_note and VENDOR-Suburban.md.
    """
    _validate_observation_source(catalog_row, 51, "manufacturer_pdf", 2, "interior switch catalog")
    extracted = json.loads(catalog_row["extracted"])
    variants = extracted.get("switch_variants")
    if not isinstance(variants, dict):
        raise ValueError("interior switch catalog observation has no switch_variants table")
    del_variants = {
        part_number: variant for part_number, variant in variants.items()
        if SWITCH_DEL_MODEL in variant.get("applies_to", [])
    }
    if set(del_variants) != set(SWITCH_CONFIRMED_VARIANTS):
        raise ValueError(f"unexpected {SWITCH_DEL_MODEL} switch variant set: {set(del_variants)}")
    for part_number, expected_color in SWITCH_CONFIRMED_VARIANTS.items():
        if del_variants[part_number].get("color", "").lower() != expected_color:
            raise ValueError(
                f"unexpected {SWITCH_DEL_MODEL} switch color for {part_number}: "
                f"{del_variants[part_number]}")

    component = Component(component_id, WATER_HEATER_PART_TYPE)
    obs_id = catalog_row["id"]
    identifiers = []
    attributes = []
    for part_number, color in SWITCH_CONFIRMED_VARIANTS.items():
        identifiers.append(Identifier(component_id, "suburban", part_number, "exterior_plate"))
        attributes.append(ComponentAttribute(
            component_id, "colour", "manufacturer_pdf", obs_id,
            qualifier=part_number, value_text=color))
    return component, identifiers, attributes


def resolve_switch_controls_edge(conn, switch_id, water_heater_id):
    """
    The switch->water-heater `controls` edge: sold separately, surfaces in
    the PARTS FOR THIS UNIT tier. Structural membership, not a probabilistic
    match — no confidence/evidence rows, matching ground-truth.yaml's
    controls edge (no confidence block at all, unlike substitutes/supersedes).
    """
    edge = Edge(type="controls", from_component_id=switch_id, to_component_id=water_heater_id)
    insert_edge(conn, edge)
    insert_controls_detail(conn, EdgeControlsDetail(
        edge_id=edge.id,
        note="Sold separately. Buyer needs it but does not know to ask. Surfaces in "
             "the PARTS FOR THIS UNIT tier."))
    return edge.id


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


def _validate_observation_source(row, expected_id, expected_type, expected_tier, label):
    try:
        actual = (row["id"], row["source_type"], row["source_tier"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Coleman {label} observation lacks source metadata") from exc
    expected = (expected_id, expected_type, expected_tier)
    if actual != expected:
        raise ValueError(
            f"unexpected Coleman {label} observation source: "
            f"{actual[0]}/{actual[1]}/Tier {actual[2]}")


def validate_coleman_visual_candidate(obs_row):
    _validate_observation_source(obs_row, 50, "retailer_page", 7, "visual candidate")
    candidate = _normalized_attributes(obs_row).get("visual_match_candidate")
    if candidate != COLEMAN_VISUAL_MATCH_CANDIDATE:
        raise ValueError(f"unexpected Coleman visual match candidate: {candidate}")
    return candidate


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


def resolve_cross_capacity_edge(conn, review_row, from_id, to_id, group_key):
    """
    First fixture edge with real field evidence rather than an attribute
    prior alone (see ground-truth.yaml's "FIRST EDGE WITH REAL FIELD
    EVIDENCE" note): a genuine customer review (observation #11's
    customer_review field) reporting a confirmed SW6DEL -> SW12DEL cutout
    upgrade install. Not handled by resolve_substitution_pair /
    suburban_parser.compare_models, since these two components have
    genuinely different capacities/cutouts — this is an upgrade path, not a
    same-group interchange match.
    """
    extracted = json.loads(review_row["extracted"])
    review = extracted.get("customer_review")
    if not isinstance(review, dict):
        raise ValueError(f"observation #{review_row['id']} has no customer_review")
    if review.get("evidence_type") != "buyer_confirmed_install":
        raise ValueError(f"unexpected cross-capacity evidence_type: {review}")
    if review.get("verdict") != "fits_with_modification":
        raise ValueError(f"unexpected cross-capacity verdict: {review}")
    if review.get("modifications_required") != [
            "enlarge cutout from 12.75x12.75 to 16.38x16.38",
            "lengthen bypass line"]:
        raise ValueError(f"unexpected cross-capacity modifications: {review}")

    basis = "buyer_confirmed_install"

    edge_forward = Edge(type="substitutes", from_component_id=from_id,
                         to_component_id=to_id, group_key=group_key)
    insert_edge(conn, edge_forward)
    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge_forward.id, basis=basis, verdict="fits_with_modification"))
    insert_caveat(conn, EdgeCaveat(
        edge_id=edge_forward.id, blocking=True,
        text="Cutout must be enlarged from 12.75x12.75 to 16.38x16.38. This is not "
             "a same-group substitution — capacities and cutouts differ."))
    insert_caveat(conn, EdgeCaveat(
        edge_id=edge_forward.id, blocking=False,
        text="Bypass line needs to be lengthened."))
    prior_alpha, prior_beta = prior_for_basis(basis)
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge_forward.id, event_type="attribute_prior",
        effect_alpha=prior_alpha, effect_beta=prior_beta, occurred_at=now_iso()))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge_forward.id, event_type="buyer_confirmed_install",
        effect_alpha=3.0, effect_beta=0.0, occurred_at=now_iso(),
        source_observation_id=review_row["id"]))

    edge_backward = Edge(type="substitutes", from_component_id=to_id,
                          to_component_id=from_id, group_key=group_key)
    insert_edge(conn, edge_backward)
    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge_backward.id, basis=basis, verdict="not_observed"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge_backward.id, event_type="attribute_prior",
        effect_alpha=prior_alpha, effect_beta=prior_beta, occurred_at=now_iso()))

    return edge_forward.id, edge_backward.id


_IW60RL_PANEL_ROLE = "replacement_panel"
_IW60RL_PANEL_BY_VALUE = {
    "6276APW": ("Suburban", "6 gallon"),
    "6277APW": ("Suburban", "10, 12, 16 gallon"),
    "521147": ("Atwood", "6 gallon"),
    "521150": ("Atwood", "10 gallon"),
}


def resolve_iw60rl_retrofit_edge(conn, manual_row, from_id, to_id, group_key,
                                  required_part_value):
    """
    One manufacturer-documented IW60RL retrofit edge (obs #14's replacement-
    panel table): an existing tank unit's cutout is COVERED by a replacement
    panel rather than resized, plus a new 3.750in vent hole. Called once per
    source family (SW6DEL, SW12DEL, Atwood 6gal, Atwood 10gal) — see
    ground-truth.yaml's four iw60_retrofit_* edges.
    """
    _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
    manual = json.loads(manual_row["extracted"])
    if manual.get("vent_cap_ordered_separately") is not True:
        raise ValueError("IW60RL manual must confirm the vent cap ships separately")
    panels = manual.get("replacement_panel_part_numbers")
    if not isinstance(panels, list):
        raise ValueError("IW60RL manual has no replacement panel table")
    expected_brand, expected_capacities = _IW60RL_PANEL_BY_VALUE[required_part_value]
    matches = [p for p in panels if p.get("part_number") == required_part_value
               and p.get("brand") == expected_brand
               and p.get("capacities") == expected_capacities]
    if len(matches) != 1:
        raise ValueError(
            f"IW60RL manual is missing the {required_part_value} replacement panel row")

    edge = Edge(type="substitutes", from_component_id=from_id,
                to_component_id=to_id, group_key=group_key)
    insert_edge(conn, edge)
    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge.id, basis="manufacturer_documented",
        verdict="fits_with_modification"))
    insert_caveat(conn, EdgeCaveat(
        edge_id=edge.id, blocking=True,
        text=f"Existing tank cutout is COVERED by replacement panel "
             f"{required_part_value}, not resized. A new 3.750in vent hole must "
             f"still be cut."))
    insert_caveat(conn, EdgeCaveat(
        edge_id=edge.id, blocking=True,
        text=f"Replacement panel ({required_part_value}) must be ordered "
             f"separately from the IW60RL unit itself."))
    insert_required_part(conn, EdgeRequiredPart(
        edge_id=edge.id, ns="suburban", value=required_part_value,
        role=_IW60RL_PANEL_ROLE))

    # Suburban-target retrofit families reach fixture confidence 0.833
    # (alpha=5, beta=1); Atwood-target families are docked to 0.80
    # (alpha=4, beta=1) per ground-truth.yaml's note that the evidence *type*
    # is the same manufacturer_documented tier but Atwood has zero
    # independent research of its own in this fixture.
    manufacturer_event_alpha = 4.0 if expected_brand == "Suburban" else 3.0

    prior_alpha, prior_beta = prior_for_basis("manufacturer_documented")
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="attribute_prior", effect_alpha=prior_alpha,
        effect_beta=prior_beta, occurred_at=now_iso()))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="manufacturer_documented",
        effect_alpha=manufacturer_event_alpha, effect_beta=0.0, occurred_at=now_iso(),
        source_observation_id=manual_row["id"]))

    return edge.id


def resolve_coleman_supersessions(conn, replacement_row, retailer_rows, component_ids):
    _validate_observation_source(
        replacement_row, 41, "manufacturer_pdf", 2, "replacement")
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
    expected_retailer_model_by_id = {48: "7330G3351", 49: "7330F3852"}
    for row in retailer_rows:
        try:
            retailer_id = row["id"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Coleman retailer observation lacks source metadata") from exc
        if retailer_id not in expected_retailer_model_by_id:
            raise ValueError(f"unexpected Coleman retailer observation #{retailer_id}")
        expected_retired_model = expected_retailer_model_by_id[retailer_id]
        _validate_observation_source(
            row, retailer_id, "retailer_page", 7,
            f"{expected_retired_model} retailer")
        attrs = _normalized_attributes(row)
        relation = attrs.get("sku_relationship")
        if not isinstance(relation, dict) or relation.get("type") != "retailer_replacement":
            raise ValueError(f"observation #{row['id']} lacks a retailer replacement")
        retired_model = relation.get("from")
        if retired_model != expected_retired_model or \
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


def _validate_coleman_endpoint_results(endpoints, component_ids):
    actual_ids = [component.component_id for component, _, _ in endpoints]
    expected_ids = set(component_ids.values())
    if len(actual_ids) != 3 or set(actual_ids) != expected_ids:
        raise ValueError(
            f"unexpected Coleman endpoint builder results: {actual_ids}")


def _get_coleman_endpoint_supersessions(conn, component_ids):
    ids = tuple(component_ids)
    if len(ids) != 3 or len(set(ids)) != 3:
        raise ValueError(f"expected three distinct Coleman endpoint IDs: {ids}")
    placeholders = ", ".join("?" for _ in ids)
    return conn.execute(
        f"SELECT * FROM edges WHERE type = 'supersedes' "
        f"AND from_component_id IN ({placeholders}) "
        f"AND to_component_id IN ({placeholders}) ORDER BY id",
        (*ids, *ids)).fetchall()


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
    obs50 = load_observation(obs_db, 50)  # observation-only visual candidate

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

    try:
        actual_visual_candidate = validate_coleman_visual_candidate(obs50)
        if actual_visual_candidate != COLEMAN_VISUAL_MATCH_CANDIDATE:
            failures.append(
                f"Coleman visual candidate mismatch: {actual_visual_candidate}")
    except (NameError, ValueError) as exc:
        failures.append(f"valid Coleman visual candidate was rejected: {exc}")
    malformed_visual_rows = (
        changed_row(obs50, lambda e: e["visual_match_candidate"]["candidate"].__setitem__(
            "ns", "rv_products_shop")),
        changed_row(obs50, lambda e: e["visual_match_candidate"]["candidate"].__setitem__(
            "value", "8330-3361")),
        changed_row(obs50, lambda e: e["visual_match_candidate"].__setitem__(
            "comparison_source_observation_id", 44)),
        changed_row(obs50, lambda e: e["visual_match_candidate"].__setitem__(
            "manual_figure", "mechanical_thermostat")),
        changed_row(obs50, lambda e: e["visual_match_candidate"].__setitem__(
            "status", "resolved")),
        changed_row(obs50, lambda e: e["visual_match_candidate"]["basis"].pop()),
        changed_row(obs50, lambda e: e["visual_match_candidate"]["basis"].__setitem__(
            0, "similar face")),
        changed_row(obs50, lambda e: e["visual_match_candidate"].__setitem__(
            "caveat", "looks identical")),
    )
    for malformed in malformed_visual_rows:
        try:
            validate_coleman_visual_candidate(malformed)
            failures.append("malformed Coleman visual candidate was accepted")
        except (NameError, ValueError):
            pass

    endpoint_ids = {
        "7330G3351": "c_placeholder_tstat_7330g3351",
        "7330F3852": "c_placeholder_tstat_7330f3852",
        "9420-351": "c_placeholder_tstat_9420_351",
    }
    endpoints = coleman_endpoint_components(obs40, obs41, obs42, endpoint_ids)
    _validate_coleman_endpoint_results(endpoints, endpoint_ids)
    try:
        _validate_coleman_endpoint_results(
            endpoints + [(Component("c_unexpected_endpoint", 415), [], [])], endpoint_ids)
        failures.append("fourth Coleman endpoint builder result was accepted")
    except ValueError:
        pass
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

    obs11 = load_observation(obs_db, 11)   # SW12DEL retailer spec + buyer review
    obs35 = load_observation(obs_db, 35)   # 5148A/5248A channel-split confirmation

    comp_12del, ids_12del, attrs_12del = resolve_12del_component(
        obs11, obs35, "c_placeholder_wh_12del")
    if comp_12del.part_type_id != WATER_HEATER_PART_TYPE:
        failures.append(f"12DEL part_type mismatch: {comp_12del}")
    expected_12del_ids = {
        ("suburban", "SW12DEL", "exterior_plate"),
        ("suburban", "5248A", "none_marked"),
        ("suburban", "5148A", "none_marked"),
    }
    if {(i.ns, i.value, i.visibility) for i in ids_12del} != expected_12del_ids:
        failures.append(f"12DEL identifiers mismatch: {ids_12del}")
    expected_12del_attrs = {
        ("capacity_gal", ""): 12.0,
        ("input_btuh", ""): 12000.0,
        ("element_watts", "1400"): 1400.0,
        ("element_watts", "1440"): 1440.0,
        ("cutout_h", ""): 16.38,
        ("cutout_w", ""): 16.38,
        ("cutout_d", ""): 22.25,
        ("weight_empty", ""): 48.0,
        ("weight_full", ""): 148.08,
    }
    actual_12del_attrs = {
        (a.name, a.qualifier): a.value_number for a in attrs_12del
    }
    if actual_12del_attrs != expected_12del_attrs:
        failures.append(f"12DEL attributes mismatch: {actual_12del_attrs}")

    for invalid11, invalid35, label in (
        (changed_row(obs11, lambda e: e.__setitem__("model", "SW10DEL")), obs35,
         "wrong model"),
        (changed_row(obs11, lambda e: e["cutout_in"].__setitem__("h", 16.0)), obs35,
         "wrong cutout"),
        (changed_row(obs11, lambda e: e.__setitem__("element_watts", [1440])), obs35,
         "resolved element_watts"),
        (dict(obs11, id=110), obs35, "wrong obs id"),
        (obs11, changed_row(obs35, lambda e: e.__setitem__(
            "relation", "legacy_current_renumbering")), "wrong channel-split relation"),
    ):
        try:
            resolve_12del_component(invalid11, invalid35, "c_invalid")
            failures.append(f"invalid 12DEL evidence accepted: {label}")
        except ValueError:
            pass

    obs13 = load_observation(obs_db, 13)   # IW60RL retailer page
    obs14 = load_observation(obs_db, 14)   # Nautilus (IW60) service manual

    comp_iw60rl, ids_iw60rl, attrs_iw60rl = resolve_iw60rl_component(
        obs13, obs14, "c_placeholder_wh_iw60rl")
    if comp_iw60rl.part_type_id != WATER_HEATER_PART_TYPE:
        failures.append(f"IW60RL part_type mismatch: {comp_iw60rl}")
    expected_iw60rl_ids = {
        ("suburban", "IW60RL", "exterior_plate"),
        ("suburban", "5280A", "none_marked"),
    }
    if {(i.ns, i.value, i.visibility) for i in ids_iw60rl} != expected_iw60rl_ids:
        failures.append(f"IW60RL identifiers mismatch: {ids_iw60rl}")
    actual_iw60rl_attrs = {
        a.name: (a.value_number if a.value_number is not None else a.value_boolean,
                 a.provenance, a.source_observation_id)
        for a in attrs_iw60rl if a.name != "ignition_type"
    }
    expected_iw60rl_attrs = {
        "tankless": (True, "retailer_spec_block", 13),
        "capacity_gal": (0.5, "retailer_spec_block", 13),
        "input_btuh": (60000.0, "retailer_spec_block", 13),
        "vent_hole_diameter_in": (3.750, "manufacturer_pdf", 14),
        "product_size_h": (12.5, "retailer_spec_block", 13),
        "product_size_w": (12.5, "retailer_spec_block", 13),
        "product_size_d": (20.0, "manufacturer_pdf", 14),
        "weight_empty": (36.0, "retailer_spec_block", 13),
    }
    if actual_iw60rl_attrs != expected_iw60rl_attrs:
        failures.append(f"IW60RL attributes mismatch: {actual_iw60rl_attrs}")
    ignition_attr = next(a for a in attrs_iw60rl if a.name == "ignition_type")
    if (ignition_attr.value_text, ignition_attr.provenance) != (
            "direct_spark", "retailer_spec_block"):
        failures.append(f"IW60RL ignition_type mismatch: {ignition_attr}")

    for mutate, label in (
        (lambda e: e.__setitem__("capacity_gal", 1.0), "wrong capacity"),
        (lambda e: e.__setitem__("ignition_type", "Pilot"), "wrong ignition"),
        (lambda e: e["product_size_in"].__setitem__("d", 21.0), "wrong depth"),
    ):
        try:
            resolve_iw60rl_component(changed_row(obs13, mutate), obs14, "c_invalid")
            failures.append(f"invalid IW60RL evidence accepted: {label}")
        except ValueError:
            pass
    try:
        resolve_iw60rl_component(
            obs13, changed_row(obs14, lambda e: e.__setitem__("vent_hole_diameter_in", 4.0)),
            "c_invalid")
        failures.append("invalid IW60RL vent hole evidence accepted")
    except ValueError:
        pass

    atwood_ids = {"6gal": "c_placeholder_wh_atwood_6gal",
                  "10gal": "c_placeholder_wh_atwood_10gal"}
    atwood = resolve_atwood_family_components(obs14, atwood_ids)
    if set(atwood) != {"6gal", "10gal"}:
        failures.append(f"Atwood family set mismatch: {set(atwood)}")
    for key, gallons in (("6gal", 6.0), ("10gal", 10.0)):
        component, identifiers, attributes = atwood[key]
        if component.component_id != atwood_ids[key] or \
                component.part_type_id != WATER_HEATER_PART_TYPE:
            failures.append(f"Atwood {key} component mismatch: {component}")
        if identifiers != []:
            failures.append(f"Atwood {key} should have no identifiers: {identifiers}")
        actual = {a.name: (a.value_text if a.value_text is not None else a.value_number,
                           a.provenance, a.source_observation_id) for a in attributes}
        expected = {
            "capacity_gal": (gallons, "manufacturer_pdf", 14),
            "brand": ("Atwood", "manufacturer_pdf", 14),
        }
        if actual != expected:
            failures.append(f"Atwood {key} attributes mismatch: {actual}")

    try:
        resolve_atwood_family_components(
            changed_row(obs14, lambda e: e["replacement_panel_part_numbers"].pop()),
            atwood_ids)
        failures.append("invalid Atwood evidence accepted")
    except ValueError:
        pass

    insert_component(store_conn, comp_12del)
    for identifier in ids_12del:
        insert_identifier(store_conn, identifier)
    for attribute in attrs_12del:
        insert_component_attribute(store_conn, attribute)

    edge_6del_to_12del, edge_12del_to_6del = resolve_cross_capacity_edge(
        store_conn, obs11, "c_placeholder_wh_6del", "c_placeholder_wh_12del",
        "cross_capacity_upgrade")

    forward_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_6del_to_12del,)).fetchone()
    if forward_detail["verdict"] != "fits_with_modification":
        failures.append(f"6DEL->12DEL should be fits_with_modification: {forward_detail}")
    forward_caveats = get_caveats_for_edge(store_conn, edge_6del_to_12del)
    if len(forward_caveats) != 2 or sum(c.blocking for c in forward_caveats) != 1:
        failures.append(f"6DEL->12DEL should have 2 caveats, 1 blocking: {forward_caveats}")

    backward_detail = store_conn.execute(
        "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
        (edge_12del_to_6del,)).fetchone()
    if backward_detail["verdict"] != "not_observed":
        failures.append(f"12DEL->6DEL should be not_observed: {backward_detail}")

    forward_confidence = compute_confidence(
        get_evidence_for_edge(store_conn, edge_6del_to_12del))
    if forward_confidence["value"] != 0.8 or forward_confidence["certainty"] != 5.0:
        failures.append(f"6DEL->12DEL confidence should be 0.8/n=5: {forward_confidence}")

    for mutate, label in (
        (lambda e: e["customer_review"].__setitem__("evidence_type", "hearsay"),
         "wrong evidence_type"),
        (lambda e: e["customer_review"].__setitem__("verdict", "drop_in"), "wrong verdict"),
        (lambda e: e["customer_review"]["modifications_required"].pop(),
         "missing modification"),
    ):
        try:
            resolve_cross_capacity_edge(
                init_db(":memory:"), changed_row(obs11, mutate),
                "c_placeholder_wh_6del", "c_placeholder_wh_12del", "cross_capacity_upgrade")
            failures.append(f"invalid cross-capacity evidence accepted: {label}")
        except ValueError:
            pass

    insert_component(store_conn, comp_iw60rl)
    for identifier in ids_iw60rl:
        insert_identifier(store_conn, identifier)
    for attribute in attrs_iw60rl:
        insert_component_attribute(store_conn, attribute)
    for key in ("6gal", "10gal"):
        component, identifiers, attributes = atwood[key]
        insert_component(store_conn, component)
        for attribute in attributes:
            insert_component_attribute(store_conn, attribute)

    retrofit_specs = (
        ("c_placeholder_wh_6del", "iw60_retrofit_suburban_6gal", "6276APW"),
        ("c_placeholder_wh_12del", "iw60_retrofit_suburban_10_12_16gal", "6277APW"),
        ("c_placeholder_wh_atwood_6gal", "iw60_retrofit_atwood_6gal", "521147"),
        ("c_placeholder_wh_atwood_10gal", "iw60_retrofit_atwood_10gal", "521150"),
    )
    expected_retrofit_values = {
        "iw60_retrofit_suburban_6gal": 0.833,
        "iw60_retrofit_suburban_10_12_16gal": 0.833,
        "iw60_retrofit_atwood_6gal": 0.8,
        "iw60_retrofit_atwood_10gal": 0.8,
    }
    for from_id, group_key, part_value in retrofit_specs:
        edge_id = resolve_iw60rl_retrofit_edge(
            store_conn, obs14, from_id, "c_placeholder_wh_iw60rl", group_key, part_value)

        detail = store_conn.execute(
            "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
            (edge_id,)).fetchone()
        if detail["verdict"] != "fits_with_modification":
            failures.append(f"{group_key} verdict mismatch: {detail}")
        caveats = get_caveats_for_edge(store_conn, edge_id)
        if len(caveats) != 2 or not all(c.blocking for c in caveats):
            failures.append(f"{group_key} should have 2 blocking caveats: {caveats}")
        parts = get_required_parts_for_edge(store_conn, edge_id)
        if [(p.ns, p.value, p.role) for p in parts] != [
                ("suburban", part_value, "replacement_panel")]:
            failures.append(f"{group_key} required part mismatch: {parts}")
        confidence = compute_confidence(get_evidence_for_edge(store_conn, edge_id))
        if round(confidence["value"], 3) != expected_retrofit_values[group_key]:
            failures.append(f"{group_key} confidence value mismatch: {confidence}")

    for mutate, label in (
        (lambda e: e["replacement_panel_part_numbers"].pop(0), "missing panel row"),
        (lambda e: e.__setitem__("vent_cap_ordered_separately", False),
         "wrong vent cap flag"),
    ):
        try:
            resolve_iw60rl_retrofit_edge(
                init_db(":memory:"), changed_row(obs14, mutate),
                "c_placeholder_wh_6del", "c_placeholder_wh_iw60rl",
                "iw60_retrofit_suburban_6gal", "6276APW")
            failures.append(f"invalid IW60RL retrofit evidence accepted: {label}")
        except ValueError:
            pass

    obs51 = load_observation(obs_db, 51)   # Suburban 2025 catalog interior switch table

    comp_switch, ids_switch, attrs_switch = resolve_switch_component(
        obs51, "c_placeholder_wh_switch")
    if comp_switch.part_type_id != WATER_HEATER_PART_TYPE:
        failures.append(f"switch part_type mismatch: {comp_switch}")
    expected_switch_ids = {
        ("suburban", "232882", "exterior_plate"),
        ("suburban", "233111", "exterior_plate"),
    }
    if {(i.ns, i.value, i.visibility) for i in ids_switch} != expected_switch_ids:
        failures.append(f"switch identifiers mismatch: {ids_switch}")
    if "232881" in {i.value for i in ids_switch}:
        failures.append("unconfirmed 232881 identifier attached to switch component")
    actual_switch_colours = {a.qualifier: a.value_text for a in attrs_switch
                              if a.name == "colour"}
    if actual_switch_colours != {"232882": "white", "233111": "black"}:
        failures.append(f"switch colours mismatch: {actual_switch_colours}")

    for mutate, label in (
        (lambda e: e["switch_variants"]["232882"].__setitem__("color", "Almond"),
         "wrong color"),
        (lambda e: e["switch_variants"]["232882"]["applies_to"].remove("SW6DEL"),
         "missing DEL applicability"),
        (lambda e: e["switch_variants"].pop("233111"), "missing variant"),
    ):
        try:
            resolve_switch_component(changed_row(obs51, mutate), "c_invalid")
            failures.append(f"invalid switch evidence accepted: {label}")
        except ValueError:
            pass

    insert_component(store_conn, comp_switch)
    for identifier in ids_switch:
        insert_identifier(store_conn, identifier)
    for attribute in attrs_switch:
        insert_component_attribute(store_conn, attribute)

    edge_switch_controls = resolve_switch_controls_edge(
        store_conn, "c_placeholder_wh_switch", "c_placeholder_wh_6del")
    controls_detail = get_controls_detail(store_conn, edge_switch_controls)
    if controls_detail is None or "PARTS FOR THIS UNIT" not in controls_detail.note:
        failures.append(f"switch controls detail mismatch: {controls_detail}")
    controls_row = store_conn.execute(
        "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
        (edge_switch_controls,)).fetchone()
    if tuple(controls_row) != ("controls", "c_placeholder_wh_switch", "c_placeholder_wh_6del"):
        failures.append(f"switch controls edge mismatch: {tuple(controls_row)}")

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

    insert_edge(store_conn, Edge(
        type="supersedes",
        from_component_id=endpoint_ids["7330G3351"],
        to_component_id=endpoint_ids["7330F3852"],
        group_key="unexpected_coleman_group",
        resolver_version=COLEMAN_ENDPOINT_RESOLVER_VERSION,
    ))
    all_endpoint_supersessions = _get_coleman_endpoint_supersessions(
        store_conn, endpoint_ids.values())
    if len(all_endpoint_supersessions) != 3:
        failures.append(
            "Coleman endpoint edge query missed an alternate-group supersession")

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
        (dict(obs41, id=410), [obs48, obs49], endpoint_ids, True),
        (dict(obs41, source_type="manufacturer_page"),
         [obs48, obs49], endpoint_ids, True),
        (dict(obs41, source_tier=7), [obs48, obs49], endpoint_ids, True),
        (obs41, [dict(obs48, id=480), obs49], endpoint_ids, True),
        (obs41, [obs48, dict(obs49, id=490)], endpoint_ids, True),
        (obs41, [dict(obs48, source_type="manufacturer_pdf"), obs49],
         endpoint_ids, True),
        (obs41, [obs48, dict(obs49, source_type="manufacturer_pdf")],
         endpoint_ids, True),
        (obs41, [dict(obs48, source_tier=2), obs49], endpoint_ids, True),
        (obs41, [obs48, dict(obs49, source_tier=2)], endpoint_ids, True),
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
    _validate_coleman_endpoint_results(endpoints, endpoint_ids)
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

    resolved_edges = _get_coleman_endpoint_supersessions(conn, endpoint_ids.values())
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

    try:
        validate_coleman_visual_candidate(obs50)
    except ValueError as exc:
        print(f"MISMATCH Coleman visual candidate observation: {exc}")
        mismatches += 1

    print(f"Coleman endpoints: {mismatches - coleman_mismatches_before} mismatch(es)")

    suburban_remainder_mismatches_before = mismatches
    obs11 = load_observation(obs_db_path, 11)
    obs13 = load_observation(obs_db_path, 13)
    obs14 = load_observation(obs_db_path, 14)
    obs35 = load_observation(obs_db_path, 35)

    comp_12del, ids_12del, attrs_12del = resolve_12del_component(
        obs11, obs35, "c_placeholder_wh_12del")
    comp_iw60rl, ids_iw60rl, attrs_iw60rl = resolve_iw60rl_component(
        obs13, obs14, "c_placeholder_wh_iw60rl")
    atwood_ids = {"6gal": "c_placeholder_wh_atwood_6gal",
                  "10gal": "c_placeholder_wh_atwood_10gal"}
    atwood = resolve_atwood_family_components(obs14, atwood_ids)

    for component, identifiers, attributes in (
        (comp_12del, ids_12del, attrs_12del),
        (comp_iw60rl, ids_iw60rl, attrs_iw60rl),
        *atwood.values(),
    ):
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    remainder_component_ids = {
        "c_placeholder_wh_12del": comp_12del.component_id,
        "c_placeholder_wh_iw60rl": comp_iw60rl.component_id,
        "c_placeholder_wh_atwood_6gal": atwood["6gal"][0].component_id,
        "c_placeholder_wh_atwood_10gal": atwood["10gal"][0].component_id,
    }
    for fixture_component_id in remainder_component_ids:
        fixture_component = next(
            (c for c in components_doc if c.get("component_id") == fixture_component_id),
            None)
        if fixture_component is None:
            print(f"MISMATCH fixture is missing component: {fixture_component_id}")
            mismatches += 1
            continue
        resolved_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (fixture_component_id,)).fetchall()
        }
        expected_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_component.get("identifiers", [])
        }
        if resolved_identifiers != expected_identifiers:
            print(f"MISMATCH {fixture_component_id} identifiers: "
                  f"resolved={resolved_identifiers} fixture={expected_identifiers}")
            mismatches += 1

    edge_6del_to_12del, edge_12del_to_6del = resolve_cross_capacity_edge(
        conn, obs11, "c_placeholder_wh_6del", "c_placeholder_wh_12del",
        "cross_capacity_upgrade")
    fixture_cross_capacity = _find_fixture_edge(
        edges_doc, "c_placeholder_wh_6del", "c_placeholder_wh_12del")
    if fixture_cross_capacity is None:
        print("MISMATCH ground-truth.yaml has no 6DEL->12DEL substitutes edge")
        mismatches += 1
    else:
        resolved_verdict = conn.execute(
            "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
            (edge_6del_to_12del,)).fetchone()["verdict"]
        if resolved_verdict != fixture_cross_capacity["a_to_b"]["verdict"]:
            print(f"MISMATCH 6DEL->12DEL verdict: fixture="
                  f"{fixture_cross_capacity['a_to_b']['verdict']} resolved={resolved_verdict}")
            mismatches += 1
        resolved_value = compute_confidence(
            get_evidence_for_edge(conn, edge_6del_to_12del))["value"]
        if round(resolved_value, 2) != fixture_cross_capacity["confidence"]["value"]:
            print(f"MISMATCH 6DEL->12DEL confidence value: fixture="
                  f"{fixture_cross_capacity['confidence']['value']} resolved={resolved_value}")
            mismatches += 1

    retrofit_specs = (
        ("c_placeholder_wh_6del", "iw60_retrofit_suburban_6gal", "6276APW"),
        ("c_placeholder_wh_12del", "iw60_retrofit_suburban_10_12_16gal", "6277APW"),
        ("c_placeholder_wh_atwood_6gal", "iw60_retrofit_atwood_6gal", "521147"),
        ("c_placeholder_wh_atwood_10gal", "iw60_retrofit_atwood_10gal", "521150"),
    )
    for from_id, group_key, part_value in retrofit_specs:
        edge_id = resolve_iw60rl_retrofit_edge(
            conn, obs14, from_id, "c_placeholder_wh_iw60rl", group_key, part_value)
        fixture_edge = next(
            (e for e in edges_doc if e.get("group") == group_key), None)
        if fixture_edge is None:
            print(f"MISMATCH ground-truth.yaml has no {group_key} edge")
            mismatches += 1
            continue
        resolved_verdict = conn.execute(
            "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
            (edge_id,)).fetchone()["verdict"]
        if resolved_verdict != fixture_edge["a_to_b"]["verdict"]:
            print(f"MISMATCH {group_key} verdict: fixture="
                  f"{fixture_edge['a_to_b']['verdict']} resolved={resolved_verdict}")
            mismatches += 1
        resolved_value = compute_confidence(get_evidence_for_edge(conn, edge_id))["value"]
        if round(resolved_value, 3) != fixture_edge["confidence"]["value"]:
            print(f"MISMATCH {group_key} confidence value: fixture="
                  f"{fixture_edge['confidence']['value']} resolved={resolved_value}")
            mismatches += 1
        print(f"  {group_key}: certainty is a hand-authored fixture dial "
              f"(fixture={fixture_edge['confidence']['certainty']}), not compared — "
              f"see 'Known fixture inconsistency' in "
              f"docs/superpowers/plans/2026-08-01-suburban-remaining-fixtures.md")

    obs51 = load_observation(obs_db_path, 51)
    comp_switch, ids_switch, attrs_switch = resolve_switch_component(
        obs51, "c_placeholder_wh_switch")
    insert_component(conn, comp_switch)
    for identifier in ids_switch:
        insert_identifier(conn, identifier)
    for attribute in attrs_switch:
        insert_component_attribute(conn, attribute)

    fixture_switch = next(
        (c for c in components_doc if c.get("component_id") == "c_placeholder_wh_switch"),
        None)
    if fixture_switch is None:
        print("MISMATCH ground-truth.yaml is missing c_placeholder_wh_switch")
        mismatches += 1
    else:
        resolved_switch_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_wh_switch",)).fetchall()
        }
        fixture_switch_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_switch.get("identifiers", [])
        }
        # 232881 ("cream") is claimed by the fixture but confirmed by no
        # observation captured so far (see obs #51's coverage_gap_note) — the
        # resolver deliberately under-produces here rather than inventing
        # evidence. A strict subset, not equality, is the correct check.
        unconfirmed = fixture_switch_identifiers - resolved_switch_identifiers
        if not resolved_switch_identifiers.issubset(fixture_switch_identifiers):
            print(f"MISMATCH switch identifiers: resolved has identifiers the fixture "
                  f"doesn't: {resolved_switch_identifiers - fixture_switch_identifiers}")
            mismatches += 1
        if unconfirmed != {("suburban", "232881", "exterior_plate")}:
            print(f"MISMATCH switch unconfirmed-identifier set changed: {unconfirmed}")
            mismatches += 1
        else:
            print("  switch: 232881 remains unconfirmed by any observation — not "
                  "attached, not a mismatch (see obs #51 coverage_gap_note)")

    edge_switch_controls = resolve_switch_controls_edge(
        conn, "c_placeholder_wh_switch", "c_placeholder_wh_6del")
    fixture_controls_edge = next(
        (e for e in edges_doc if e.get("type") == "controls"
         and e.get("a") == "c_placeholder_wh_switch"
         and e.get("b") == "c_placeholder_wh_6del"), None)
    if fixture_controls_edge is None:
        print("MISMATCH ground-truth.yaml has no switch->6del controls edge")
        mismatches += 1
    else:
        controls_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (edge_switch_controls,)).fetchone()
        if tuple(controls_row) != (
                "controls", "c_placeholder_wh_switch", "c_placeholder_wh_6del"):
            print(f"MISMATCH switch controls edge: {tuple(controls_row)}")
            mismatches += 1

    print(f"Suburban remaining fixtures: "
          f"{mismatches - suburban_remainder_mismatches_before} mismatch(es)")

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
