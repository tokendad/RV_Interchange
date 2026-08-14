#!/usr/bin/env python3
"""
edge_resolver.py — observations.db -> components/edges, proven against the
fixture's canonical edge case (SW6DE/SW6DEL) and the in-hand Coleman thermostat.
See docs/superpowers/plans/2026-07-31-edge-schema-resolver.md and
docs/superpowers/plans/2026-08-01-thermostat-resolver.md for scope. Full
fixture reproduction remains incremental.
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from resolver import normalize_extracted
from suburban_parser import compare_models
from edge_types import (
    EDGE_TYPE_CONTROLS, EDGE_TYPE_FITS, EDGE_TYPE_SUBSTITUTES, EDGE_TYPE_SUPERSEDES,
)
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
    insert_component_attribute, get_component_attributes, get_component_by_identifier,
    get_components_by_identifier, merge_component_into,
    insert_identifier_equivalence_candidate, insert_identifier_equivalence_evidence,
    get_identifier_equivalence_candidates, get_identifier_equivalence_evidence,
    get_supersession_detail, insert_required_part, get_required_parts_for_edge,
    insert_controls_detail, get_controls_detail,
)
from part_types import (
    ATWOOD_PART_TYPE, COLEMAN_AC_PART_TYPE, COLEMAN_AC_PLENUM_PART_TYPE,
    COLEMAN_AC_PLENUM_REPAIR_PART_TYPE, COLEMAN_AC_REPAIR_PART_TYPE,
    NORCOLD_REFRIGERATOR_PART_TYPE, NORCOLD_REPAIR_PART_TYPE,
    SUBURBAN_COOKTOP_PART_TYPE, SUBURBAN_COOKTOP_REPAIR_PART_TYPE, SUBURBAN_FURNACE_PART_TYPE,
    SUBURBAN_FURNACE_REPAIR_PART_TYPE, THERMOSTAT_PART_TYPE, WATER_HEATER_PART_TYPE,
)

THERMOSTAT_CODE = "415-0012-A"
COLEMAN_ENDPOINT_MODELS = ("7330G3351", "7330F3852", "9420-351")
COLEMAN_ENDPOINT_RESOLVER_VERSION = "coleman_endpoint_v1"
COLEMAN_SECOND_WAVE_ENDPOINT_MODELS = ("7330F3361", "7330-3861", "7330B3441")
COLEMAN_SECOND_WAVE_RESOLVER_VERSION = "coleman_endpoint_v2"
COLEMAN_THIRD_WAVE_ENDPOINT_MODELS = ("7330E335", "7330E385", "7330E336")
COLEMAN_THIRD_WAVE_RESOLVER_VERSION = "coleman_endpoint_v3"
ATWOOD_ENDPOINT_MODELS = (
    "G6A-7", "G6A-7P", "GC6AA-8", "GC6AA-10E", "GCH6A-10E", "G6A-8E", "GH6-8E",
    "G9-EXT", "GE9-EXT", "GEH9-EXT", "G10-2", "GC10A-2", "G10-3E", "GH10-3E",
    "GC10A-4E", "GCH10A-4E", "G16-EXT", "GE16-EXT", "GEH16-EXT",
)
ATWOOD_ENDPOINT_RESOLVER_VERSION = "atwood_endpoint_v1"
ATWOOD_PILOT_PARTS_RESOLVER_VERSION = "atwood_fits_v1"
ATWOOD_PILOT_PARTS_TARGET_MODELS = ("G6A-7", "G6A-7P", "GC6AA-8", "GC10A-2", "G10-2")
ATWOOD_ELECTRONIC_PARTS_RESOLVER_VERSION = "atwood_fits_v2"
ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS = (
    "GH6-8E", "G6A-8E", "G10-3E", "GH10-3E", "GCH6A-10E", "GC6AA-10E", "GC10A-4E", "GCH10A-4E",
)
ATWOOD_EXT_PARTS_RESOLVER_VERSION = "atwood_fits_v3"
ATWOOD_EXT_PARTS_TARGET_MODELS = (
    "G9-EXT", "GE9-EXT", "GEH9-EXT", "G16-EXT", "GE16-EXT", "GEH16-EXT",
)
SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION = "suburban_furnace_cooktop_v1"
SUBURBAN_COOKTOP_PARTS_RESOLVER_VERSION = "suburban_cooktop_parts_v1"
NORCOLD_ENDPOINT_RESOLVER_VERSION = "norcold_endpoint_v1"
NORCOLD_PARTS_RESOLVER_VERSION = "norcold_parts_v1"
NORCOLD_DRAIN_HOSE_HEATER_RESOLVER_VERSION = "norcold_drain_hose_heater_v1"
COLEMAN_AC_ENDPOINT_RESOLVER_VERSION = "coleman_ac_endpoint_v1"
COLEMAN_AC_PARTS_RESOLVER_VERSION = "coleman_ac_parts_v1"
COLEMAN_PLENUM_ENDPOINT_RESOLVER_VERSION = "coleman_plenum_endpoint_v1"
COLEMAN_PLENUM_PARTS_RESOLVER_VERSION = "coleman_plenum_parts_v1"
ATWOOD_GH6_6E_RESOLVER_VERSION = "atwood_gh6_6e_v1"
ATWOOD_GH6_6E_PARTS_RESOLVER_VERSION = "atwood_gh6_6e_parts_v1"
ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION = "atwood_gh6_6e_valve_v1"
ATWOOD_6_GAL_OPENING = (12.625, 16.25)
ATWOOD_10_GAL_OPENING = (15.625, 16.25)
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
    edge = Edge(type=EDGE_TYPE_CONTROLS, from_component_id=switch_id,
                to_component_id=water_heater_id)
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


def coleman_second_wave_endpoint_components(product_row, corroboration_rows, component_ids):
    """
    Build 7330F3361/7330-3861/7330B3441 as exact endpoint components, same
    shape as coleman_endpoint_components() above but from a different source
    triple: obs #40's manufacturer table plus obs #55/#56, two dedicated
    rvacguys.com retailer pages that corroborate two of the three models.
    7330B3441 has no dedicated corroborating page (only cross-sell mentions
    in #55/#56 with no stated attributes) and stays single-source.
    """
    expected_sources = ((product_row, 40, "manufacturer_page", "product"),)
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

    corroboration_by_model = {"7330F3361": 55, "7330-3861": 56}
    if {row["id"] for row in corroboration_rows} != set(corroboration_by_model.values()):
        raise ValueError(
            f"unexpected Coleman second-wave corroboration observations: "
            f"{[row['id'] for row in corroboration_rows]}")
    corroboration_by_id = {row["id"]: row for row in corroboration_rows}
    for row in corroboration_rows:
        if row["source_type"] != "retailer_page":
            raise ValueError(
                f"unexpected Coleman corroboration observation source: "
                f"{row['id']}/{row['source_type']}")

    product = _normalized_attributes(product_row)
    product_models = product.get("model_spec_table")
    if not isinstance(product_models, dict):
        raise ValueError("Coleman second-wave product observation requires a model table")
    if not set(COLEMAN_SECOND_WAVE_ENDPOINT_MODELS).issubset(product_models):
        raise ValueError("official product page is missing a second-wave endpoint model")
    if set(component_ids) != set(COLEMAN_SECOND_WAVE_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman second-wave endpoint ID map: {component_ids}")

    source_checks = (
        (product_models["7330F3361"].get("function"), "cool_only", "7330F3361 function"),
        (product_models["7330F3361"].get("color"), "white", "7330F3361 color"),
        (product_models["7330-3861"].get("function"), "cool_only", "7330-3861 function"),
        (product_models["7330-3861"].get("color"), "black", "7330-3861 color"),
        (product_models["7330B3441"].get("function"), "single_stage_standard",
         "7330B3441 function"),
        (product_models["7330B3441"].get("color"), "white", "7330B3441 color"),
    )
    for actual, expected, label in source_checks:
        if actual != expected:
            raise ValueError(f"unexpected {label}: {actual!r}")

    corroborated_models = {}
    for model, obs_id in corroboration_by_model.items():
        row = corroboration_by_id[obs_id]
        models = _normalized_attributes(row).get("model_spec_table")
        if not isinstance(models, dict) or model not in models:
            raise ValueError(f"Coleman corroboration observation #{obs_id} missing {model}")
        corroborated = models[model]
        if (corroborated.get("function") != product_models[model]["function"]
                or corroborated.get("stages") != "single"
                or corroborated.get("interface_type") != "mechanical"
                or corroborated.get("voltage") != "12VDC"):
            raise ValueError(
                f"Coleman corroboration mismatch for {model}: {corroborated}")
        corroborated_models[model] = corroborated

    def text_attr(component_id, name, value, provenance, source_row):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=COLEMAN_SECOND_WAVE_RESOLVER_VERSION)

    attribute_specs = {
        "7330F3361": (
            ("function", "cool_only", "manufacturer_page", product_row),
            ("color", "white", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "retailer_page", corroboration_by_id[55]),
            ("voltage", "12VDC", "retailer_page", corroboration_by_id[55]),
        ),
        "7330-3861": (
            ("function", "cool_only", "manufacturer_page", product_row),
            ("color", "black", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "retailer_page", corroboration_by_id[56]),
            ("voltage", "12VDC", "retailer_page", corroboration_by_id[56]),
        ),
        "7330B3441": (
            ("function", "single_stage_standard", "manufacturer_page", product_row),
            ("color", "white", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page_single_source", product_row),
            ("stages", "single", "manufacturer_page_inferred", product_row),
        ),
    }
    results = []
    for model in COLEMAN_SECOND_WAVE_ENDPOINT_MODELS:
        component_id = component_ids[model]
        component = Component(component_id, THERMOSTAT_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", model, None)]
        attributes = [text_attr(component_id, name, value, provenance, source_row)
                      for name, value, provenance, source_row in attribute_specs[model]]
        results.append((component, identifiers, attributes))
    return results


def coleman_third_wave_endpoint_components(naming_row, family_row, component_ids):
    """
    Build 7330E335/7330E385/7330E336 as exact endpoint components -- the
    "Electronic"-generation family's D->E transition instantiation (see
    VENDOR-Coleman-Mach.md sec 6.7). Two manufacturer-primary sources, neither
    a model_spec_table: obs #74 (rvcomfort.com's own catalog page, naming all
    three verbatim as the SKUs current for the linked installation PDF) and
    obs #58 (that same wildcard-family installation manual, whose
    family_statement gives the Heat/Cool vs Cool Only functional split by
    wildcard suffix: *335*/*385* = Heat/Cool, *336* = Cool Only). Neither
    source states color for any of the three (unlike the already-built
    7330G3351/7330F3852/7330F3361/7330-3861, where color is manufacturer- or
    retailer-stated) -- VENDOR-Coleman-Mach.md sec 6.7's "not yet confirmed"
    note -- so no color attribute is asserted here.
    """
    expected_sources = (
        (naming_row, 74, "manufacturer_page", "naming"),
        (family_row, 58, "manufacturer_pdf", "family"),
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

    naming = _normalized_attributes(naming_row)
    family = _normalized_attributes(family_row)

    models_named = naming.get("models_named_list")
    if not isinstance(models_named, list) or \
            set(models_named) != set(COLEMAN_THIRD_WAVE_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman third-wave naming: {models_named}")

    sku_relationship = naming.get("sku_relationship")
    expected_relationship = {
        "type": "link_target",
        "from": list(COLEMAN_THIRD_WAVE_ENDPOINT_MODELS),
        "to": "pdf_documents/1976190.pdf",
    }
    if sku_relationship != expected_relationship:
        raise ValueError(f"unexpected Coleman third-wave sku_relationship: {sku_relationship}")

    family_statement = family.get("compatibility_statement")
    if not family_statement or "*335*" not in family_statement or \
            "*385*" not in family_statement or \
            "Cool Only" not in family_statement:
        raise ValueError(f"unexpected Coleman third-wave family_statement: {family_statement}")

    if set(component_ids) != set(COLEMAN_THIRD_WAVE_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman third-wave endpoint ID map: {component_ids}")

    def text_attr(component_id, name, value, provenance, source_row):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=COLEMAN_THIRD_WAVE_RESOLVER_VERSION)

    function_by_model = {
        "7330E335": "heat_cool",
        "7330E385": "heat_cool",
        "7330E336": "cool_only",
    }
    results = []
    for model in COLEMAN_THIRD_WAVE_ENDPOINT_MODELS:
        component_id = component_ids[model]
        component = Component(component_id, THERMOSTAT_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", model, None)]
        attributes = [
            text_attr(component_id, "function", function_by_model[model],
                      "manufacturer_page", naming_row),
            text_attr(component_id, "interface_type", "analog",
                      "manufacturer_pdf_single_source", family_row),
            text_attr(component_id, "stages", "single",
                      "manufacturer_pdf_inferred", family_row),
        ]
        results.append((component, identifiers, attributes))
    return results


def resolve_coleman_third_wave_supersession(conn, retailer_row, corroboration_row,
                                             from_component_id, to_component_id):
    """
    7330E336 -> 7330F3361, retailer-tier only (no manufacturer statement,
    unlike the first-wave 7330G3351/7330F3852 -> 9420-351 edges): obs #59
    (MakariosRV's own replacement chart, "7330-E336": "7330F3361") plus a
    second, independent retailer corroboration, obs #64 (trvparts.com,
    structured `sku_relationship: retailer_named_replacement`). See
    VENDOR-Coleman-Mach.md sec 6.2/sec 8 item 3.
    """
    _validate_observation_source(corroboration_row, 64, "retailer_page", None, "corroboration")
    corroboration = _normalized_attributes(corroboration_row)
    relation = corroboration.get("sku_relationship")
    expected_relation = {
        "type": "retailer_named_replacement", "from": ["7330-E336"], "to": "7330F3361",
    }
    if relation != expected_relation:
        raise ValueError(f"unexpected Coleman third-wave corroboration relation: {relation}")

    try:
        retailer_id = retailer_row["id"]
        retailer_type = retailer_row["source_type"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Coleman third-wave retailer observation lacks source metadata") \
            from exc
    if (retailer_id, retailer_type) != (59, "retailer_prose"):
        raise ValueError(
            f"unexpected Coleman third-wave retailer observation source: "
            f"{retailer_id}/{retailer_type}")
    retailer = _normalized_attributes(retailer_row)
    chart = retailer.get("replacement_chart_entries")
    if not isinstance(chart, dict) or chart.get("7330-E336") != "7330F3361":
        raise ValueError(
            f"MakariosRV chart missing 7330-E336 -> 7330F3361: {chart}")

    edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=from_component_id,
        to_component_id=to_component_id,
        group_key="coleman_e336_cool_only_replacement",
        status="candidate",
        resolver_version=COLEMAN_THIRD_WAVE_RESOLVER_VERSION,
        notes="Two independent retailers (MakariosRV, trvparts.com) name "
              "7330F3361 as the current replacement for legacy 7330-E336; "
              "no manufacturer-primary statement of this specific pairing.",
    )
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id,
        note="Two independent retailers name 7330F3361 as the replacement "
             "for 7330-E336 (obs #59, obs #64); not manufacturer-documented."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("retailer_cross_reference", 1.0, 0.0, retailer_row["id"]),
        ("retailer_cross_reference", 1.0, 0.0, corroboration_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
    return edge.id


COLEMAN_9420_352_RESOLVER_VERSION = "coleman_endpoint_v4"


def coleman_9420_352_component_and_supersession(conn, catalog_row, component_id,
                                                 from_component_id):
    """
    Build 9420-352 as an exact endpoint component and its manufacturer-primary
    supersession edge from 7330F3361 -- obs #93, Airxcel's own current (May
    2025) dealer catalog (CM-4040.02), whose "NEW SINGLE STAGE THERMOSTATS"
    THIS#/REPLACES/DESCRIPTION table directly parallels the original
    7330G3351/7330F3852 -> 9420-351 evidence (obs #41), just for a different
    pair. This *revises* 7330F3361's status: the second-wave build (sec 6.1)
    described it as current/unsuperseded because no replacement was stated in
    evidence at that time -- this observation is that evidence, found later.
    See VENDOR-Coleman-Mach.md sec 6.8.
    """
    _validate_observation_source(catalog_row, 93, "manufacturer_pdf", 1, "2025 catalog")
    catalog = _normalized_attributes(catalog_row)
    models = catalog.get("model_spec_table")
    if not isinstance(models, dict) or "9420-352" not in models:
        raise ValueError(f"obs #93 catalog is missing 9420-352: {models}")
    spec = models["9420-352"]
    expected_spec = {"function": "cool_only", "color": "black",
                      "interface_type": "analog", "voltage": "12VDC"}
    if spec != expected_spec:
        raise ValueError(f"unexpected 9420-352 spec: {spec}")

    relation = catalog.get("sku_relationship")
    expected_relation = {
        "type": "manufacturer_supersedes", "from": ["7330F3361"], "to": "9420-352"}
    if relation != expected_relation:
        raise ValueError(f"unexpected 9420-352 supersession relation: {relation}")

    def text_attr(name, value):
        return ComponentAttribute(
            component_id, name, "manufacturer_pdf", catalog_row["id"], value_text=value,
            resolver_version=COLEMAN_9420_352_RESOLVER_VERSION)

    component = Component(component_id, THERMOSTAT_PART_TYPE, None)
    identifiers = [Identifier(component_id, "coleman", "9420-352", None)]
    attributes = [
        text_attr("function", "cool_only"),
        text_attr("color", "black"),
        text_attr("interface_type", "analog"),
        text_attr("voltage", "12VDC"),
    ]
    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=from_component_id,
        to_component_id=component_id,
        group_key="coleman_analog_cool_only_12v",
        status="candidate",
        resolver_version=COLEMAN_9420_352_RESOLVER_VERSION,
        notes="Coleman-Mach's current (2025) dealer catalog names 9420-352 as "
              "the replacement for 7330F3361, revising 7330F3361's earlier "
              "unsuperseded/current status (VENDOR-Coleman-Mach.md sec 6.1).",
    )
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id,
        note="Coleman-Mach's 2025 dealer catalog (CM-4040.02) names 9420-352 as "
             "the current replacement for 7330F3361."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, edge.id


COLEMAN_9420A382_RESOLVER_VERSION = "coleman_endpoint_v5"


def coleman_9420a382_component_and_supersession(conn, catalog_row, component_id,
                                                 from_component_id):
    """
    Build 9420A382 as an exact endpoint component and the one supersession
    edge this fixture can evidence into it: 7330F3361 -> 9420A382 (obs #94,
    same 2025 Airxcel catalog page as obs #93/9420-352). The catalog's own
    REPLACES entry for 9420A382 spans three separate old-part groups
    (cool-only, heat-pump, heat/cool control-package lines) -- one SKU used
    as the replacement across all three, evidently one multi-configuration
    digital thermostat rather than three products, so all three
    "configurable_mode" facts are recorded on the single component. Only the
    cool-only group's 7330F3361 already exists as an independently-evidenced
    component in this fixture; the other five old part numbers (9430-3392,
    9430A3392, 9630A3351, 9630A3361, 9630A3371, 9430A3372) appear ONLY as bare
    REPLACES targets on this one catalog row, with no independent product
    description anywhere in this fixture's evidence -- the same evidentiary
    gap that already keeps 7330D337/8330-339(2) unbuilt (VENDOR-Coleman-Mach.md
    sec 6.2) -- so no edge is built from any of them. This is a second,
    coexisting replacement path alongside the already-built analog
    7330F3361 -> 9420-352 edge: unlike the 8330-3362/8330-3862 digital
    alternatives sec 6.3 deliberately left ungraphed (because THOSE never
    cleared the manufacturer-primary-component bar), 9420A382 clears it right
    here, so both paths get real edges. See VENDOR-Coleman-Mach.md sec 6.9.
    """
    _validate_observation_source(
        catalog_row, 94, "manufacturer_pdf", 1, "2025 catalog (9420A382)")
    catalog = _normalized_attributes(catalog_row)
    models = catalog.get("model_spec_table")
    if not isinstance(models, dict) or "9420A382" not in models:
        raise ValueError(f"obs #94 catalog is missing 9420A382: {models}")
    spec = models["9420A382"]
    expected_spec = {"interface_type": "digital", "color": "black", "voltage": "12VDC"}
    if spec != expected_spec:
        raise ValueError(f"unexpected 9420A382 spec: {spec}")

    relation = catalog.get("sku_relationship")
    if not isinstance(relation, dict) or \
            relation.get("type") != "manufacturer_supersedes_multi":
        raise ValueError(f"unexpected 9420A382 relation: {relation}")
    groups = relation.get("groups")
    expected_groups = [
        {"from": ["7330F3361", "9430-3392", "9430A3392"], "to": "9420A382",
         "description": "Digital, Cool Only, 12VDC - Black"},
        {"from": ["9630A3351", "9630A3361"], "to": "9420A382",
         "description": "Digital, Heat Pump, 12VDC - Black, Used with Single "
                         "Stage Heat Pump Control Package & Gas Furnace"},
        {"from": ["9630A3371", "9430A3372"], "to": "9420A382",
         "description": "Digital, Heat/Cool, 12VDC - Black"},
    ]
    if groups != expected_groups:
        raise ValueError(f"unexpected 9420A382 REPLACES groups: {groups}")
    if "7330F3361" not in groups[0]["from"]:
        raise ValueError("9420A382 cool-only group must include 7330F3361")

    def text_attr(name, value):
        return ComponentAttribute(
            component_id, name, "manufacturer_pdf", catalog_row["id"], value_text=value,
            resolver_version=COLEMAN_9420A382_RESOLVER_VERSION)

    def mode_attr(mode):
        return ComponentAttribute(
            component_id, "configurable_mode", "manufacturer_pdf", catalog_row["id"],
            value_boolean=True, qualifier=mode,
            resolver_version=COLEMAN_9420A382_RESOLVER_VERSION)

    component = Component(component_id, THERMOSTAT_PART_TYPE, None)
    identifiers = [Identifier(component_id, "coleman", "9420A382", None)]
    attributes = [
        text_attr("interface_type", "digital"),
        text_attr("color", "black"),
        text_attr("voltage", "12VDC"),
        mode_attr("cool_only"),
        mode_attr("heat_pump"),
        mode_attr("heat_cool"),
    ]
    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=from_component_id,
        to_component_id=component_id,
        group_key="coleman_cool_only_digital_upgrade",
        status="candidate",
        resolver_version=COLEMAN_9420A382_RESOLVER_VERSION,
        notes="Coleman-Mach's current (2025) dealer catalog names 9420A382 as "
              "a digital replacement option for 7330F3361 -- one of three "
              "REPLACES groups on this catalog row; the other two groups' old "
              "part numbers have no independent evidence in this fixture and "
              "are not built (VENDOR-Coleman-Mach.md sec 6.9).",
    )
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id,
        note="Coleman-Mach's 2025 dealer catalog (CM-4040.02) names 9420A382 as "
             "a digital replacement for 7330F3361 -- a second, coexisting "
             "replacement path alongside the analog 7330F3361 -> 9420-352 edge "
             "(sec 6.3's 'two coexisting paths' pattern)."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, edge.id


def atwood_endpoint_components(catalog_row, component_ids):
    """
    Build the 19 RV Pilot/Electronic-Ignition Atwood water heater models named
    in obs #92 (Atwood Mobile Products' own service manual: the "Atwood LP Gas
    Water Heaters" catalog table cross-checked against its own Pilot and
    Electronic-Ignition model-number-explanation legends) as exact endpoint
    components. First Atwood vendor wave, catalog-only -- no in-hand teardown
    anchor yet, same evidentiary shape as Coleman's own first/second-wave
    endpoint builds. Marine/220V-CE water heaters in the same manual are out
    of scope (not RV parts) and are not built here.
    """
    _validate_observation_source(catalog_row, 92, "manufacturer_pdf", 1, "catalog")
    catalog = _normalized_attributes(catalog_row)
    models = catalog.get("model_spec_table")
    if not isinstance(models, dict) or set(models) != set(ATWOOD_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Atwood catalog model set: "
                          f"{sorted(models) if isinstance(models, dict) else models}")
    if set(component_ids) != set(ATWOOD_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Atwood endpoint ID map: {component_ids}")

    required_fields = {"capacity_gal", "power_type", "ignition_type",
                        "heat_exchanger", "exothermal"}
    for model, spec in models.items():
        if not required_fields.issubset(spec):
            raise ValueError(f"Atwood model {model} is missing required fields: {spec}")
        if spec["capacity_gal"] not in (6, 10):
            raise ValueError(f"unexpected Atwood capacity for {model}: {spec}")
        if spec["power_type"] not in ("gas_only", "gas_electric"):
            raise ValueError(f"unexpected Atwood power_type for {model}: {spec}")
        if spec["ignition_type"] not in ("pilot", "electronic"):
            raise ValueError(f"unexpected Atwood ignition_type for {model}: {spec}")
        if not isinstance(spec["heat_exchanger"], bool) or \
                not isinstance(spec["exothermal"], bool):
            raise ValueError(f"Atwood heat_exchanger/exothermal must be booleans: {spec}")
        # model-number legend cross-check: same document, second independent
        # presentation of the same facts (letters in the model string) --
        # must agree with the table's own stated attributes. The XT/EXT
        # legend ("G E H 9/16 - E XT") uses a different letter for the
        # gas/electric combo flag (E, not C) than the Pilot/Electronic
        # legend ("G C H 6 A -8 P" / "G C H 6 AA -10 E") does, so the two
        # families are decoded separately per the manual's own two legends.
        is_ext = model.endswith("-EXT")
        prefix = model.split("-")[0]
        if is_ext:
            letters = prefix.rstrip("0123456789")
            has_c = "E" in letters[1:]  # combo flag for XT models is E, not C
            has_h = "H" in letters
        else:
            has_c = "C" in prefix
            has_h = "H" in prefix
        is_electronic = model.endswith("E") or is_ext
        if has_c != (spec["power_type"] == "gas_electric"):
            raise ValueError(f"Atwood model-number/table power_type mismatch for {model}")
        if has_h != spec["heat_exchanger"]:
            raise ValueError(
                f"Atwood model-number/table heat_exchanger mismatch for {model}")
        # exothermal is NOT cross-checked against the model number: the
        # manual's own table shows it encoded via the "-EXT" suffix for the
        # 6/16-gallon exothermal family but via description text only (no
        # suffix change) for GC10A-4E/GCH10A-4E -- the manufacturer's own
        # naming isn't consistent here, so this attribute stays
        # single-presentation (description text), not cross-validated.
        if is_electronic != (spec["ignition_type"] == "electronic"):
            raise ValueError(
                f"Atwood model-number/table ignition_type mismatch for {model}")

    def text_attr(component_id, name, value, unit=None):
        return ComponentAttribute(
            component_id, name, "manufacturer_pdf", catalog_row["id"], value_text=value,
            unit=unit, resolver_version=ATWOOD_ENDPOINT_RESOLVER_VERSION)

    def number_attr(component_id, name, value, unit=None):
        return ComponentAttribute(
            component_id, name, "manufacturer_pdf", catalog_row["id"], value_number=value,
            unit=unit, resolver_version=ATWOOD_ENDPOINT_RESOLVER_VERSION)

    def bool_attr(component_id, name, value):
        return ComponentAttribute(
            component_id, name, "manufacturer_pdf", catalog_row["id"], value_boolean=value,
            resolver_version=ATWOOD_ENDPOINT_RESOLVER_VERSION)

    def opening_attrs(component_id, capacity_gal):
        if capacity_gal == 6:
            opening_h, opening_w = ATWOOD_6_GAL_OPENING
        elif capacity_gal == 10:
            opening_h, opening_w = ATWOOD_10_GAL_OPENING
        else:
            raise ValueError(f"unexpected Atwood capacity for opening attrs: {capacity_gal}")
        return [
            number_attr(component_id, "opening_h", opening_h, unit="in"),
            number_attr(component_id, "opening_w", opening_w, unit="in"),
        ]

    results = []
    for model in ATWOOD_ENDPOINT_MODELS:
        spec = models[model]
        component_id = component_ids[model]
        component = Component(component_id, WATER_HEATER_PART_TYPE, None)
        identifiers = [Identifier(component_id, "atwood", model, None)]
        attributes = [
            number_attr(component_id, "capacity_gal", float(spec["capacity_gal"]), "gal"),
            text_attr(component_id, "power_type", spec["power_type"]),
            text_attr(component_id, "ignition_type", spec["ignition_type"]),
            bool_attr(component_id, "heat_exchanger", spec["heat_exchanger"]),
            bool_attr(component_id, "exothermal", spec["exothermal"]),
        ]
        attributes.extend(opening_attrs(component_id, spec["capacity_gal"]))
        if "pilot_relight" in spec:
            attributes.append(bool_attr(component_id, "pilot_relight", spec["pilot_relight"]))
        if "status" in spec:
            attributes.append(text_attr(component_id, "status", spec["status"]))
        if "availability" in spec:
            attributes.append(text_attr(component_id, "availability", spec["availability"]))
        results.append((component, identifiers, attributes))
    return results


def atwood_repair_parts_and_fits(conn, catalog_row, host_component_ids):
    """
    Build Atwood repair/service-part components and "fits" edges from a
    manufacturer service-manual "Replacement Part Reference" cross-reference
    table -- a genuinely different relationship shape than supersedes
    (old model -> new model) or substitutes (interchangeable end products):
    one generic repair part (e.g. a thermostat valve or burner) fits MANY
    distinct end-product models. obs #95, the January 2007 edition's Pilot
    table (Docs/Data/Atwood/Atwood-Water-Heater-Service-Manual.pdf), scoped
    to the five Pilot models already built as exact endpoint components (see
    VENDOR-Atwood.md sec 7) -- not the full ~40-row x 12-column table.

    "fits" is a new edge type value (edges.type is free-text, no schema
    migration needed, same as how "controls" was added). Validation here is
    STRUCTURAL (required fields present, applies_to is a non-empty subset of
    the five known host models) rather than per-row hardcoded expected
    values -- deliberately, given the ~40-row scale; see the "bulk catalog
    ingestion" trade-off memo this mirrors, scoped tight to one table
    instead of a general-purpose ingestion pipeline.
    """
    _validate_observation_source(catalog_row, 95, "manufacturer_pdf", 1, "repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #95 catalog has no repair_part_fitment_table: {parts}")
    if set(host_component_ids) != set(ATWOOD_PILOT_PARTS_TARGET_MODELS):
        raise ValueError(f"unexpected Atwood repair-part host ID map: {host_component_ids}")

    results = []
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"Atwood repair part {part_number} missing required fields: {spec}")
        applies_to = spec["applies_to"]
        if not isinstance(applies_to, list) or not applies_to or \
                not set(applies_to).issubset(ATWOOD_PILOT_PARTS_TARGET_MODELS):
            raise ValueError(f"Atwood repair part {part_number} has invalid applies_to: {applies_to}")

        component_id = f"c_placeholder_wh_atwood_part_{part_number}"
        component = Component(component_id, ATWOOD_PART_TYPE, None)
        identifiers = [Identifier(component_id, "atwood", part_number, None)]
        attributes = [ComponentAttribute(
            component_id, "description", "manufacturer_pdf", catalog_row["id"],
            value_text=spec["description"], resolver_version=ATWOOD_PILOT_PARTS_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

        edge_ids = []
        for model in applies_to:
            edge = Edge(
                type=EDGE_TYPE_FITS,
                from_component_id=component_id,
                to_component_id=host_component_ids[model],
                group_key="atwood_pilot_repair_part",
                status="candidate",
                resolver_version=ATWOOD_PILOT_PARTS_RESOLVER_VERSION,
                notes=f"Atwood's January 2007 service manual Replacement Part Reference "
                      f"table names {part_number} as fitting {model}.",
            )
            insert_edge(conn, edge)
            for event_type, alpha, beta, source_id in (
                ("attribute_prior", 1.0, 1.0, None),
                ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
            ):
                insert_evidence(conn, RelationshipEvidence(
                    edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                    effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
            edge_ids.append(edge.id)
        results.append((component, identifiers, attributes, edge_ids))
    return results


def atwood_electronic_repair_parts_and_fits(conn, catalog_row, host_component_ids):
    """
    Same "fits" many-to-many relationship as atwood_repair_parts_and_fits()
    (see that function's docstring for the general rationale), for the
    Electronic Ignition table instead of the Pilot one: obs #96, the January
    2007 edition's Electronic Ignition "Replacement Part Reference" table
    (pp.35-36), scoped to the 8 Electronic models already built as exact
    endpoint components. Same coordinate-precise pdftotext -bbox extraction
    method as the Pilot table (VENDOR-Atwood.md sec 7.1) -- confirmed
    internally consistent here too: e.g. "Drawn Pan (Electronic 6 Gallon)"
    (part 91802) resolved to exactly the four 6-gallon models among the 8
    (GH6-8E, G6A-8E, GCH6A-10E, GC6AA-10E), and its 10-gallon sibling (93871)
    to three of the four 10-gallon ones.

    17 part numbers are the same physical part as one already built by
    atwood_repair_parts_and_fits() from the Pilot table (obs #95), just
    described slightly differently table-to-table (e.g. 90960's "Flue Box &
    Gasket" here vs "Flue Box and Gasket" there) -- issue #48. As with
    atwood_ext_repair_parts_and_fits() (see that function's docstring point
    3), this looks up each part number by its `atwood` identifier first and,
    on a hit, adds this table's description as a second attribute
    observation and its edges onto the EXISTING component(s) instead of
    minting a second one -- and if more than one component already shares
    that identifier (a duplicate from some other source), all of them are
    kept in sync rather than just one.
    """
    _validate_observation_source(catalog_row, 96, "manufacturer_pdf", 1, "repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #96 catalog has no repair_part_fitment_table: {parts}")
    if set(host_component_ids) != set(ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS):
        raise ValueError(f"unexpected Atwood electronic repair-part host ID map: "
                          f"{host_component_ids}")

    results = []
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(
                f"Atwood electronic repair part {part_number} missing required fields: {spec}")
        applies_to = spec["applies_to"]
        if not isinstance(applies_to, list) or not applies_to or \
                not set(applies_to).issubset(ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS):
            raise ValueError(
                f"Atwood electronic repair part {part_number} has invalid applies_to: "
                f"{applies_to}")

        existing = get_components_by_identifier(conn, "atwood", part_number)
        if existing:
            component_ids = [c.component_id for c in existing]
            component = existing[0]
            identifiers = []
        else:
            component_ids = [f"c_placeholder_wh_atwood_epart_{part_number}"]
            component = Component(component_ids[0], ATWOOD_PART_TYPE, None)
            identifiers = [Identifier(component_ids[0], "atwood", part_number, None)]
            insert_component(conn, component)
            for identifier in identifiers:
                insert_identifier(conn, identifier)

        attributes = []
        edge_ids = []
        for component_id in component_ids:
            attribute = ComponentAttribute(
                component_id, "description", "manufacturer_pdf", catalog_row["id"],
                value_text=spec["description"],
                resolver_version=ATWOOD_ELECTRONIC_PARTS_RESOLVER_VERSION)
            insert_component_attribute(conn, attribute)
            attributes.append(attribute)

            for model in applies_to:
                edge = Edge(
                    type=EDGE_TYPE_FITS,
                    from_component_id=component_id,
                    to_component_id=host_component_ids[model],
                    group_key="atwood_electronic_repair_part",
                    status="candidate",
                    resolver_version=ATWOOD_ELECTRONIC_PARTS_RESOLVER_VERSION,
                    notes=f"Atwood's January 2007 service manual Electronic Ignition "
                          f"Replacement Part Reference table names {part_number} as "
                          f"fitting {model}.",
                )
                insert_edge(conn, edge)
                for event_type, alpha, beta, source_id in (
                    ("attribute_prior", 1.0, 1.0, None),
                    ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
                ):
                    insert_evidence(conn, RelationshipEvidence(
                        edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                        effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
                edge_ids.append(edge.id)
        results.append((component, identifiers, attributes, edge_ids))
    return results


def atwood_ext_repair_parts_and_fits(conn, catalog_row, host_component_ids):
    """
    Same "fits" many-to-many relationship as atwood_repair_parts_and_fits()
    (see that function's docstring for the general rationale), for the XT
    family's own "XT Water Heater Part Identification" table (obs #119,
    p.38 of the same January 2007 service manual) -- closing issue #14, the
    one gap VENDOR-Atwood.md sec 6 item 4 left in the 19-model first wave.

    Three judgment calls this table's shape forced, all spelled out in obs
    #119's own data_quality_flag so they're traceable back to the source
    rather than silently encoded here:

    1. Unlike the Pilot/Electronic tables (one column per model), this
       table only brackets by tank size (6/10 gallon). The "SPARK IGNITION"
       section's parts are common to all 6 EXT models regardless of
       power_type. The "COMBINATION GAS/ELECTRIC" section's two NS
       (not-shown-in-diagram) rows -- Heating Element & Gasket, Relay --
       are genuinely electric-only components, restricted here to the four
       gas_electric models (GE9-EXT, GEH9-EXT, GE16-EXT, GEH16-EXT); the
       section's other parts (mixing valve/tee/hose/elbow assembly, the
       replacement valve kit) are NOT power-type-restricted -- p.37's own
       92690 valve-kit install instructions name only "10 GALLON XT" with
       no power-type qualifier, and three of those items print the same
       part number in both size columns.
    2. Item 21A's 6-gallon hose prints the same part number, 90032, as item
       20's 10-gallon Tee -- a real duplicate in the manual,
       coordinate-verified, not an extraction error. 90032 is only built as
       the Tee here; the 6-gallon-hose row is left unasserted.
    3. 14 of these 22 part numbers already exist as components from the
       Pilot (obs #95) and/or Electronic (obs #96) repair-parts tables --
       the XT family's spark-ignition hardware is largely the same generic
       service stock as the Electronic-ignition family's, just described
       slightly differently table-to-table (e.g. obs #96's "Switch 12 VDC -
       White Combo" vs this table's "Dual Switch" for the same part,
       91230). Rather than mint a second `atwood` identifier for the same
       physical part, this function looks up each part number first and,
       if found, adds this table's description as a second attribute
       observation and its edges onto the EXISTING component instead of
       creating a duplicate.
    """
    _validate_observation_source(catalog_row, 119, "manufacturer_pdf", 1, "EXT repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #119 catalog has no repair_part_fitment_table: {parts}")
    if set(host_component_ids) != set(ATWOOD_EXT_PARTS_TARGET_MODELS):
        raise ValueError(f"unexpected Atwood EXT repair-part host ID map: {host_component_ids}")

    results = []
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"Atwood EXT repair part {part_number} missing required fields: {spec}")
        applies_to = spec["applies_to"]
        if not isinstance(applies_to, list) or not applies_to or \
                not set(applies_to).issubset(ATWOOD_EXT_PARTS_TARGET_MODELS):
            raise ValueError(f"Atwood EXT repair part {part_number} has invalid applies_to: {applies_to}")

        existing = get_components_by_identifier(conn, "atwood", part_number)
        if existing:
            # A handful of part numbers already resolve to more than one
            # component -- the same physical part minted twice by the Pilot
            # and Electronic repair-parts tables before the duplication was
            # noticed (see the docstring's point 3 and the "NOTE ... resolved
            # to more than one component_id" diagnostic in check_fixture()).
            # This table's description/fits data applies equally to the real
            # part, so every duplicate must be updated in lockstep -- merging
            # onto only one would leave the others silently stale.
            component_ids = [c.component_id for c in existing]
            component = existing[0]
            identifiers = []
        else:
            component_ids = [f"c_placeholder_wh_atwood_extpart_{part_number}"]
            component = Component(component_ids[0], ATWOOD_PART_TYPE, None)
            identifiers = [Identifier(component_ids[0], "atwood", part_number, None)]
            insert_component(conn, component)
            for identifier in identifiers:
                insert_identifier(conn, identifier)

        attributes = []
        edge_ids = []
        for component_id in component_ids:
            attribute = ComponentAttribute(
                component_id, "description", "manufacturer_pdf", catalog_row["id"],
                value_text=spec["description"], resolver_version=ATWOOD_EXT_PARTS_RESOLVER_VERSION)
            insert_component_attribute(conn, attribute)
            attributes.append(attribute)

            for model in applies_to:
                edge = Edge(
                    type=EDGE_TYPE_FITS,
                    from_component_id=component_id,
                    to_component_id=host_component_ids[model],
                    group_key="atwood_ext_repair_part",
                    status="candidate",
                    resolver_version=ATWOOD_EXT_PARTS_RESOLVER_VERSION,
                    notes=f"Atwood's January 2007 service manual XT Water Heater Part "
                          f"Identification table names {part_number} as fitting {model}.",
                )
                insert_edge(conn, edge)
                for event_type, alpha, beta, source_id in (
                    ("attribute_prior", 1.0, 1.0, None),
                    ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
                ):
                    insert_evidence(conn, RelationshipEvidence(
                        edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                        effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
                edge_ids.append(edge.id)
        results.append((component, identifiers, attributes, edge_ids))
    return results


def suburban_furnace_cooktop_components(furnace_dataplate_row, furnace_manual_row,
                                         catalog_row, cooktop_dataplate_row,
                                         cooktop_clearance_row, cooktop_manual_row,
                                         component_ids):
    """
    Build the Suburban SF-30FQ furnace and SRNA3SBBM cooktop/range as exact
    endpoint components -- the owner's current-coach in-hand data plates
    (obs #97/#98/#99), cross-checked against matching manufacturer
    installation manuals the owner confirmed match their units (obs
    #101/#102), plus the 2025 catalog's parallel SF-30VHFQ/SF-30VHQ BTU
    listing (obs #100) for the furnace's btu_rating -- this unit's own plate
    does not print a BTU figure the way the cooktop's does, so that one
    attribute is provenance-flagged as inferred, not read. See
    docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md.

    No `conn` argument: like atwood_endpoint_components(), this only builds
    and returns data -- the caller inserts it and, separately, calls
    suburban_furnace_core_module() (which DOES take conn, because it also
    creates the fits edge) to build the repair part.
    """
    _validate_observation_source(furnace_dataplate_row, 97, "dataplate_photo", 2,
                                  "furnace dataplate")
    _validate_observation_source(furnace_manual_row, 101, "manufacturer_pdf", 1,
                                  "furnace installation manual")
    _validate_observation_source(catalog_row, 100, "manufacturer_pdf", 1,
                                  "furnace core module catalog")
    _validate_observation_source(cooktop_dataplate_row, 98, "dataplate_photo", 2,
                                  "cooktop dataplate")
    _validate_observation_source(cooktop_clearance_row, 99, "dataplate_photo", 2,
                                  "cooktop clearance dataplate")
    _validate_observation_source(cooktop_manual_row, 102, "manufacturer_pdf", 1,
                                  "cooktop installation manual")

    furnace_plate = _normalized_attributes(furnace_dataplate_row)
    if furnace_plate.get("model") != "SF-30FQ":
        raise ValueError(f"unexpected furnace dataplate model: {furnace_plate.get('model')}")
    furnace_manual = _normalized_attributes(furnace_manual_row)
    if furnace_manual.get("model") != "SF-30FQ":
        raise ValueError(f"unexpected furnace manual model: {furnace_manual.get('model')}")
    catalog = _normalized_attributes(catalog_row)
    fitment = catalog.get("repair_part_fitment_table")
    if not isinstance(fitment, dict) or "2608A" not in fitment:
        raise ValueError(f"catalog observation missing 2608A fitment row: {fitment}")
    applies_to = fitment["2608A"].get("applies_to")
    if set(applies_to or []) != {"SF-25FQ", "SF-30FQ"}:
        raise ValueError(
            f"2608A must apply to exactly SF-25FQ and SF-30FQ, got: {applies_to}")

    cooktop_plate = _normalized_attributes(cooktop_dataplate_row)
    if cooktop_plate.get("model") != "SRNA3SBBM":
        raise ValueError(f"unexpected cooktop dataplate model: {cooktop_plate.get('model')}")
    cooktop_clearance = _normalized_attributes(cooktop_clearance_row)
    cooktop_manual = _normalized_attributes(cooktop_manual_row)

    def text_attr(component_id, name, value, source_row, provenance="manufacturer_pdf"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)

    def number_attr(component_id, name, value, source_row, unit=None,
                     provenance="manufacturer_pdf"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_number=value,
            unit=unit, resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)

    furnace_id = component_ids["furnace"]
    furnace = Component(furnace_id, SUBURBAN_FURNACE_PART_TYPE, None)
    furnace_identifiers = [Identifier(furnace_id, "suburban", "SF-30FQ", "exterior_plate")]
    furnace_attributes = [
        number_attr(furnace_id, "btu_rating", float(catalog["input_btuh"]), catalog_row,
                    unit="BTU/h", provenance="manufacturer_pdf_inferred"),
        text_attr(furnace_id, "stock_no", furnace_plate["sku"], furnace_dataplate_row,
                   provenance="dataplate_photo"),
        text_attr(furnace_id, "serial", furnace_plate["serial_number"], furnace_dataplate_row,
                   provenance="dataplate_photo"),
    ]
    for name in ("clearance_front_in", "clearance_left_in", "clearance_right_in",
                 "clearance_top_in", "clearance_bottom_in", "clearance_back_in"):
        furnace_attributes.append(
            number_attr(furnace_id, name, float(furnace_manual[name]), furnace_manual_row,
                        unit="in"))
    furnace_attributes.append(number_attr(
        furnace_id, "cabinet_cutout_h_in", float(furnace_manual["cabinet_cutout_h_in"]),
        furnace_manual_row, unit="in"))
    furnace_attributes.append(number_attr(
        furnace_id, "cabinet_cutout_w_in", float(furnace_manual["cabinet_cutout_w_in"]),
        furnace_manual_row, unit="in"))

    cooktop_id = component_ids["cooktop"]
    cooktop = Component(cooktop_id, SUBURBAN_COOKTOP_PART_TYPE, None)
    cooktop_identifiers = [Identifier(cooktop_id, "suburban", "SRNA3SBBM", "exterior_plate")]
    cooktop_attributes = [
        number_attr(cooktop_id, "burner_count", 3.0, cooktop_dataplate_row,
                    provenance="dataplate_photo"),
        number_attr(cooktop_id, "btu_rating", float(cooktop_plate["burner_btu_front"]),
                    cooktop_dataplate_row, unit="BTU/h", provenance="dataplate_photo"),
        number_attr(cooktop_id, "oven_btu_rating", float(cooktop_plate["oven_btu"]),
                    cooktop_dataplate_row, unit="BTU/h", provenance="dataplate_photo"),
        number_attr(cooktop_id, "manifold_pressure_wc",
                    float(cooktop_plate["manifold_pressure_wc"]), cooktop_dataplate_row,
                    unit="in_wc", provenance="dataplate_photo"),
        text_attr(cooktop_id, "stock_no", cooktop_plate["sku"], cooktop_dataplate_row,
                   provenance="dataplate_photo"),
        text_attr(cooktop_id, "serial", cooktop_plate["serial_number"], cooktop_dataplate_row,
                   provenance="dataplate_photo"),
    ]
    for name in ("clearance_below_counter_in", "clearance_right_sidewall_in",
                 "clearance_left_sidewall_in", "clearance_backwall_in", "clearance_vertical_in"):
        cooktop_attributes.append(
            number_attr(cooktop_id, name, float(cooktop_clearance[name]), cooktop_clearance_row,
                        unit="in", provenance="dataplate_photo"))
    for name in ("cutout_a_in", "cutout_b_in", "cutout_c_in", "cutout_d_in", "cutout_e_in"):
        cooktop_attributes.append(
            number_attr(cooktop_id, name, float(cooktop_manual[name]), cooktop_manual_row,
                        unit="in"))

    return [
        (furnace, furnace_identifiers, furnace_attributes),
        (cooktop, cooktop_identifiers, cooktop_attributes),
    ]


def suburban_furnace_core_module(conn, catalog_row, retailer_row, furnace_component_id):
    """
    Build the Suburban 2608A furnace core replacement module and its `fits`
    edge to SF-30FQ -- a single-part case of the same many-to-many "fits"
    relationship Atwood's repair-parts tables use (see
    atwood_repair_parts_and_fits()'s docstring), sourced to the 2025 catalog
    (obs #100, manufacturer-primary) and independently corroborated by a
    retailer page (obs #103) that also supplies the core module's own model
    designation, RP-30FQ, not present in the catalog. See
    docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md
    sec 2/4/5.
    """
    _validate_observation_source(catalog_row, 100, "manufacturer_pdf", 1,
                                  "furnace core module catalog")
    _validate_observation_source(retailer_row, 103, "retailer_page", 7,
                                  "furnace core module retailer")

    catalog = _normalized_attributes(catalog_row)
    fitment = catalog.get("repair_part_fitment_table", {}).get("2608A")
    if fitment is None or set(fitment.get("applies_to", [])) != {"SF-25FQ", "SF-30FQ"}:
        raise ValueError(f"unexpected 2608A catalog fitment: {fitment}")

    retailer = _normalized_attributes(retailer_row)
    retailer_fitment = retailer.get("repair_part_fitment_table", {}).get("2608A")
    if retailer_fitment is None or "SF-30FQ" not in retailer_fitment.get("applies_to", []):
        raise ValueError(f"retailer observation does not corroborate 2608A/SF-30FQ: "
                          f"{retailer_fitment}")
    retailer_identifiers = retailer.get("physical_identifiers", [])
    rp_30fq = next(
        (i for i in retailer_identifiers if i.get("ns") == "suburban"
         and i.get("value") == "RP-30FQ"), None)
    if rp_30fq is None:
        raise ValueError(f"retailer observation missing RP-30FQ identifier: "
                          f"{retailer_identifiers}")

    component_id = "c_placeholder_furnace_part_2608a"
    component = Component(component_id, SUBURBAN_FURNACE_REPAIR_PART_TYPE, None)
    identifiers = [
        Identifier(component_id, "suburban", "2608A", "catalog"),
        Identifier(component_id, "suburban", "RP-30FQ", "retailer_page"),
    ]
    attributes = [ComponentAttribute(
        component_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text=fitment["description"],
        resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)]

    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_FITS,
        from_component_id=component_id,
        to_component_id=furnace_component_id,
        group_key="suburban_furnace_core_module",
        status="candidate",
        resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION,
        notes="Suburban's 2025 catalog names 2608A as the furnace core replacement "
              "module for SF-25FQ and SF-30FQ; unitedrvparts.com independently "
              "corroborates the SF-30FQ/2608A pairing and supplies the module's own "
              "model designation, RP-30FQ.",
    )
    insert_edge(conn, edge)
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ("retailer_cross_reference", 1.0, 0.0, retailer_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, [edge.id]


def suburban_srna3sbbm_repair_parts_and_fits(conn, catalog_row, host_component_id):
    """
    Build Suburban SRNA3SBBM repair-part components and their `fits` edges
    to the in-hand cooktop/range -- same many-to-many "fits" shape as
    atwood_repair_parts_and_fits() (see that function's docstring), sourced
    to Airxcel/Suburban's own "Replacement Parts List and Parts
    Illustrations for Cook Top & Range Models" (doc 203705XP, 03-13-2018,
    obs #117) rather than secondhand from the attached AI research report
    (issue #37) -- the report's own parts table (its section 8) was
    verified directly against this PDF and found to have missed two real
    entries (011008/011009/011010, the match-ignition top-burner
    assemblies; its table had only the oven burner 010994).

    The shared SRNA3S/SRSA3S table covers many finish/ignition/manifold
    variants at once; obs #117's extraction is pre-filtered to exactly the
    SRNA3SBBM configuration (conventional burner, short oven, black
    porcelain top, black painted door, match ignition) -- long-oven-only,
    Piezo/Spark-ignition-only, sealed-burner, and stainless/glass-finish
    rows are excluded at the observation layer, not here. BSI/Copreci
    manifold qualifiers stay in each part's own description text (the same
    "(Use with X)" precedent as Atwood's bracket rows) rather than becoming
    a caveat structure, since manifold generation is a property of the
    physical unit's build date, not of the SRNA3SBBM model itself -- see
    obs #98's serial for the in-hand unit's own likely generation.
    """
    _validate_observation_source(catalog_row, 117, "manufacturer_pdf", 2, "repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #117 catalog has no repair_part_fitment_table: {parts}")

    results = []
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"SRNA3SBBM repair part {part_number} missing required fields: {spec}")
        if spec["applies_to"] != ["SRNA3SBBM"]:
            raise ValueError(f"SRNA3SBBM repair part {part_number} has unexpected applies_to: "
                              f"{spec['applies_to']}")

        component_id = f"c_placeholder_suburban_cooktop_part_{part_number}"
        component = Component(component_id, SUBURBAN_COOKTOP_REPAIR_PART_TYPE, None)
        identifiers = [Identifier(component_id, "suburban", part_number, "catalog")]
        attributes = [ComponentAttribute(
            component_id, "description", "manufacturer_pdf", catalog_row["id"],
            value_text=spec["description"], resolver_version=SUBURBAN_COOKTOP_PARTS_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

        edge = Edge(
            type=EDGE_TYPE_FITS,
            from_component_id=component_id,
            to_component_id=host_component_id,
            group_key="suburban_srna3sbbm_repair_part",
            status="candidate",
            resolver_version=SUBURBAN_COOKTOP_PARTS_RESOLVER_VERSION,
            notes=f"Airxcel/Suburban's Replacement Parts List (203705XP) names "
                  f"{part_number} as fitting the SRNA3SBBM configuration (conventional "
                  f"burner, short oven, black top, black door, match ignition).",
        )
        insert_edge(conn, edge)
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        results.append((component, identifiers, attributes, [edge.id]))
    return results


def norcold_n811_component(dataplate_row, grammar_row, family_spec_row, component_id):
    """
    Build the owner's in-hand Norcold refrigerator as an exact endpoint
    component -- the 4th Stage 1 vendor. See Docs/Data/Norcold/VENDOR-Norcold.md.

    Identity is two identifiers on one physical unit, not a conflict: the
    permanent spec plate reads `N811` (obs #105) while a same-door warranty
    sticker reads `N811RT` (obs #105) -- both namespace `norcold`. The
    Service Manual's own model-identification grammar (obs #106, scoped to
    the later N611v/N811v models) decodes position 10 (door swing: L/R) and
    position 12 (packaging type: blank/T/M6), so `N811RT` = base `N811` + `R`
    (right-hand door swing, a real physical attribute) + `T` (returnable
    packaging tray, a shipping/batch attribute -- deliberately NOT asserted
    as a component attribute here, since it isn't a lasting physical
    feature of the installed unit).

    Specs come from obs #108 (Service Manual, N6XX/N8XX Models -- the plain,
    non-`v` family that actually matches this in-hand unit), not obs #106/
    #107's `v`-scoped documents, which are corroboration only.
    """
    _validate_observation_source(dataplate_row, 105, "dataplate_photo", 2,
                                  "refrigerator dataplate")
    _validate_observation_source(grammar_row, 106, "manufacturer_pdf", 2,
                                  "model-ID grammar")
    _validate_observation_source(family_spec_row, 108, "manufacturer_pdf", 2,
                                  "N6XX/N8XX family specifications")

    plate = _normalized_attributes(dataplate_row)
    plate_ids = {(i["ns"], i["value"]) for i in plate["physical_identifiers"]}
    if plate_ids != {("norcold", "N811"), ("norcold", "N811RT")}:
        raise ValueError(f"unexpected refrigerator identifiers: {plate_ids}")

    grammar = _normalized_attributes(grammar_row)
    positions = grammar.get("model_grammar_positions")
    if not isinstance(positions, dict) or "right-hand door swing" not in positions.get("10", ""):
        raise ValueError(f"model-ID grammar missing expected door-swing decode: {positions}")

    family_spec = _normalized_attributes(family_spec_row)
    if family_spec.get("compatibility_statement") != \
            "N61X/N81X Models (plain, non-v -- matches in-hand N811)":
        raise ValueError(
            f"unexpected family-spec scope: {family_spec.get('compatibility_statement')}")

    def text_attr(name, value, source_row, provenance="dataplate_photo"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=NORCOLD_ENDPOINT_RESOLVER_VERSION)

    def number_attr(name, value, source_row, unit=None, provenance="dataplate_photo"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_number=value,
            unit=unit, resolver_version=NORCOLD_ENDPOINT_RESOLVER_VERSION)

    component = Component(component_id, NORCOLD_REFRIGERATOR_PART_TYPE, None)
    identifiers = [
        Identifier(component_id, "norcold", "N811", "spec_plate_interior_upper_right"),
        Identifier(component_id, "norcold", "N811RT", "warranty_registration_sticker"),
    ]
    attributes = [
        text_attr("serial", plate["serial_number"], dataplate_row),
        text_attr("group_code", plate["group_code"], dataplate_row),
        number_attr("input_btuh", float(plate["input_btuh"]), dataplate_row, unit="BTU/h"),
        text_attr("refrigerant", plate["refrigerant"], dataplate_row),
        number_attr("refrigerant_lbs", float(plate["refrigerant_lbs"]), dataplate_row, unit="lb"),
        number_attr("ac_voltage_v", float(plate["ac_voltage_v"]), dataplate_row, unit="V"),
        number_attr("ac_amperage_a", float(plate["ac_amperage_a"]), dataplate_row, unit="A"),
        number_attr("ac_watts_w", float(plate["ac_watts_w"]), dataplate_row, unit="W"),
        number_attr("dc_voltage_v", float(plate["dc_voltage_v"]), dataplate_row, unit="V"),
        number_attr("dc_amperage_a", float(plate["dc_amperage_a"]), dataplate_row, unit="A"),
        number_attr("dc_watts_w", float(plate["dc_watts_w"]), dataplate_row, unit="W"),
        text_attr("cooling_unit_model", plate["cooling_unit_model"], dataplate_row),
        text_attr("cooling_unit_serial", plate["cooling_unit_serial_number"], dataplate_row),
        text_attr("door_swing", "R", grammar_row, provenance="manufacturer_pdf_inferred"),
        number_attr("storage_volume_cu_ft", float(family_spec["storage_volume_cu_ft"]),
                    family_spec_row, unit="ft3", provenance="manufacturer_pdf"),
        number_attr("rough_opening_h_in", float(family_spec["rough_opening_h_in"]),
                    family_spec_row, unit="in", provenance="manufacturer_pdf"),
        number_attr("rough_opening_w_in", float(family_spec["rough_opening_w_in"]),
                    family_spec_row, unit="in", provenance="manufacturer_pdf"),
        number_attr("rough_opening_d_in", float(family_spec["rough_opening_d_in"]),
                    family_spec_row, unit="in", provenance="manufacturer_pdf"),
    ]

    return component, identifiers, attributes


def norcold_base_board_fits(conn, catalog_row, host_component_ids):
    """
    Build the Norcold `628674` base/power board as a repair-part component and
    its `fits` edge to the in-hand N811 refrigerator -- same many-to-many
    "fits" shape as Atwood's repair-parts tables (see
    atwood_repair_parts_and_fits()'s docstring), sourced to the official
    Thetford/Norcold parts catalog (obs #109, PL_N61N81_623421). The catalog
    lists two serial-scoped board revisions (`618186` for serial 9056491 and
    below, `628674` for 9056492 and above); the in-hand unit's own
    refrigerator serial (15605897, obs #105) is well above that breakpoint,
    so only `628674` is built -- `618186` is out of scope for this unit, not
    a supersession target.
    """
    _validate_observation_source(catalog_row, 109, "manufacturer_pdf", 2, "parts catalog")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or "628674" not in parts:
        raise ValueError(f"obs #109 catalog missing 628674 fitment row: {parts}")
    spec = parts["628674"]
    if spec.get("applies_to") != ["N811"]:
        raise ValueError(f"unexpected 628674 applies_to: {spec.get('applies_to')}")

    component_id = "c_placeholder_norcold_part_628674"
    component = Component(component_id, NORCOLD_REPAIR_PART_TYPE, None)
    identifiers = [Identifier(component_id, "norcold", "628674", "catalog")]
    attributes = [ComponentAttribute(
        component_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text=spec["description"], resolver_version=NORCOLD_PARTS_RESOLVER_VERSION)]
    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_FITS,
        from_component_id=component_id,
        to_component_id=host_component_ids["N811"],
        group_key="norcold_base_board",
        status="candidate",
        resolver_version=NORCOLD_PARTS_RESOLVER_VERSION,
        notes="Thetford/Norcold's official N61/N81 parts catalog (623421) names "
              "628674 as the base/power board for serial 9056492 and above, "
              "confirmed applicable to N811 by column position; the in-hand "
              "unit's serial (15605897) is above that breakpoint.",
    )
    insert_edge(conn, edge)
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, [edge.id]


def norcold_drain_hose_and_heater_fits(conn, catalog_row, host_component_id):
    """
    Build the Norcold drain-hose (`622391`/`639101`) and AC-heater
    (`630811`/`638374`) part pairs as repair-part components, each with a
    `fits` edge to the in-hand N811 refrigerator AND a `supersedes` edge
    between the pair -- unlike norcold_optical_control_supersession()'s
    board pair (no host edge, since the installed board's own color/serial
    was never photographed), both pairs here are fully determined by data
    already photographed on the in-hand unit (obs #105): the drain hose is
    N8-series-scoped with no variants, and the heater generation is decided
    by the in-hand cooling-unit serial (15597729) against the catalog's own
    11232008 breakpoint -- same "observed data determines applicability"
    bar as norcold_base_board_fits()'s `628674`.

    Sourced to obs #118, a fresh coordinate-precise read of the same
    official Thetford/Norcold parts catalog as obs #109 (
    Docs/Data/Norcold/VENDOR-Norcold.md sec 4's evidentiary standard). The
    catalog's sibling below-serial rows (`622390`/`639100` for N6-series,
    `621702`/`638365` for the heater's earlier cooling-unit generation) are
    out of scope for this unit and not built, same treatment as the base
    board's `618186`.
    """
    _validate_observation_source(catalog_row, 118, "manufacturer_pdf", 2,
                                  "drain hose / AC heater parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #118 catalog has no repair_part_fitment_table: {parts}")

    results = []
    component_ids_by_part = {}
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"Norcold drain hose/heater part {part_number} missing "
                              f"required fields: {spec}")
        if spec["applies_to"] != ["N811"]:
            raise ValueError(f"Norcold drain hose/heater part {part_number} has "
                              f"unexpected applies_to: {spec['applies_to']}")

        component_id = f"c_placeholder_norcold_part_{part_number}"
        component_ids_by_part[part_number] = component_id
        component = Component(component_id, NORCOLD_REPAIR_PART_TYPE, None)
        identifiers = [Identifier(component_id, "norcold", part_number, "catalog")]
        attributes = [ComponentAttribute(
            component_id, "description", "manufacturer_pdf", catalog_row["id"],
            value_text=spec["description"],
            resolver_version=NORCOLD_DRAIN_HOSE_HEATER_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

        edge = Edge(
            type=EDGE_TYPE_FITS,
            from_component_id=component_id,
            to_component_id=host_component_id,
            group_key="norcold_drain_hose_heater",
            status="candidate",
            resolver_version=NORCOLD_DRAIN_HOSE_HEATER_RESOLVER_VERSION,
            notes=f"Thetford/Norcold's official N61/N81 parts catalog (623421) names "
                  f"{part_number} as fitting N811.",
        )
        insert_edge(conn, edge)
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        results.append((component, identifiers, attributes, [edge.id]))

    chart = catalog.get("replacement_chart_entries")
    if not isinstance(chart, dict) or chart.get("622391") != "639101" \
            or chart.get("630811") != "638374":
        raise ValueError(f"obs #118 replacement_chart missing expected pairs: {chart}")

    supersession_edge_ids = {}
    for old_part, new_part, note in (
            ("622391", "639101", "Catalog's own '(USE 639101)' wording for the N8-series "
             "drain hose assembly."),
            ("630811", "638374", "Catalog's own '(USE 638374)' wording for the AC heater/"
             "backer, cooling-unit serial 11232008 and above -- the generation matching "
             "the in-hand unit's cooling-unit serial (15597729, obs #105).")):
        supersession_edge = Edge(
            type=EDGE_TYPE_SUPERSEDES,
            from_component_id=component_ids_by_part[old_part],
            to_component_id=component_ids_by_part[new_part],
            group_key="norcold_drain_hose_heater",
            status="candidate",
            resolver_version=NORCOLD_DRAIN_HOSE_HEATER_RESOLVER_VERSION,
            notes=note,
        )
        insert_edge(conn, supersession_edge)
        insert_supersession_detail(conn, EdgeSupersessionDetail(
            edge_id=supersession_edge.id, note=note))
        for event_type, alpha, beta, source_id in (
                ("attribute_prior", 1.0, 1.0, None),
                ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"])):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=supersession_edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        supersession_edge_ids[(old_part, new_part)] = supersession_edge.id

    return results, supersession_edge_ids


def norcold_optical_control_supersession(conn, catalog_row):
    """
    Build the Norcold `628979`/`637775` optical-control-board pair and the
    `supersedes` edge between them -- family-level catalog evidence, not a
    claim about which exact board is on the in-hand unit (the control
    board's own color and internal serial were never photographed; see
    Docs/Data/Norcold/VENDOR-Norcold.md sec 4). Sourced to obs #109, whose
    own "(USE 637775)" wording is the same explicit supersession convention
    already used elsewhere in this project's Suburban/Coleman-Mach catalogs.
    Not attached to c_placeholder_refrigerator_n811 by any edge.
    """
    _validate_observation_source(catalog_row, 109, "manufacturer_pdf", 2, "parts catalog")
    catalog = _normalized_attributes(catalog_row)
    chart = catalog.get("replacement_chart_entries")
    if not isinstance(chart, dict) or chart.get("628979") != "637775":
        raise ValueError(f"obs #109 catalog missing 628979 -> 637775: {chart}")

    old_id, new_id = "c_placeholder_norcold_part_628979", "c_placeholder_norcold_part_637775"
    old_component = Component(old_id, NORCOLD_REPAIR_PART_TYPE, None)
    new_component = Component(new_id, NORCOLD_REPAIR_PART_TYPE, None)
    old_identifiers = [Identifier(old_id, "norcold", "628979", "catalog")]
    new_identifiers = [Identifier(new_id, "norcold", "637775", "catalog")]
    old_attributes = [ComponentAttribute(
        old_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text="Control Assy-Optical/Black (Serial # 9056492 & Above)",
        resolver_version=NORCOLD_PARTS_RESOLVER_VERSION)]
    new_attributes = [ComponentAttribute(
        new_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text="Kit Service Optical Control Replacement",
        resolver_version=NORCOLD_PARTS_RESOLVER_VERSION)]
    for component, identifiers, attributes in (
            (old_component, old_identifiers, old_attributes),
            (new_component, new_identifiers, new_attributes)):
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=old_id,
        to_component_id=new_id,
        group_key="norcold_optical_control_black",
        status="candidate",
        resolver_version=NORCOLD_PARTS_RESOLVER_VERSION,
        notes="Thetford/Norcold's official N61/N81 parts catalog (623421) names "
              "637775 as the current replacement kit for 628979 ('USE 637775').",
    )
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id,
        note="Catalog's own '(USE 637775)' wording for the black optical control "
             "board, serial 9056492 and above."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return (old_component, old_identifiers, old_attributes), \
           (new_component, new_identifiers, new_attributes), edge.id


def norcold_630762_component(dealer_row, component_id):
    """
    Build Norcold `630762`/`1172-321` as a standalone repair-part component --
    a dealer's board photograph (obs #110, Tim's RV/eBay) shows both numbers
    printed on the same physical board, corroborated by a second listing.
    Same "photo confirms co-location" evidence standard that resolved
    Coleman-Mach's AR7815/7330F3858 case (obs #104).

    Deliberately NOT connected to c_placeholder_refrigerator_n811 or to the
    official parts catalog's optical-control lineage (621988/628979/636105/
    629079, see norcold_optical_control_supersession()) by any edge: `630762`
    is absent from the current official parts list entirely, and the research
    pass that found it explicitly calls its relationship to that lineage
    unresolved, not merely under-evidenced -- "fits all N611/N811" and
    "replaces 621988/628979/637775" claims appear only in aftermarket
    listings. See Docs/Data/Norcold/VENDOR-Norcold.md sec 4.
    """
    _validate_observation_source(dealer_row, 110, "retailer_photo", 3, "630762 board photo")
    dealer = _normalized_attributes(dealer_row)
    relation = dealer.get("sku_relationship")
    models = dealer.get("model_spec_table")
    if not isinstance(relation, dict) or relation.get("type") != \
            "photographed_product_label":
        raise ValueError(f"observation #{dealer_row['id']} has no label-photo claim")
    values = relation.get("identifiers")
    if values != ["630762", "1172-321"] or not isinstance(models, dict):
        raise ValueError(f"unexpected identifier-equivalence claim: {relation}")
    namespaces = {value: models.get(value, {}).get("namespace") for value in values}
    if namespaces != {"630762": "norcold", "1172-321": "norcold"}:
        raise ValueError(f"unexpected identifier namespaces: {namespaces}")

    component = Component(component_id, NORCOLD_REPAIR_PART_TYPE, None)
    identifiers = [
        Identifier(component_id, "norcold", "630762", "board_marking"),
        Identifier(component_id, "norcold", "1172-321", "board_marking"),
    ]
    attributes = [ComponentAttribute(
        component_id, "description", "retailer_page", dealer_row["id"],
        value_text=dealer["product_type"], resolver_version=NORCOLD_PARTS_RESOLVER_VERSION)]

    return component, identifiers, attributes


COLEMAN_AC_48253B866_IDENTIFIERS = {("coleman", "48253B866")}


def coleman_ac_48253b866_component(dataplate_row, component_id):
    """
    Build the owner's in-hand Coleman-Mach "Mach 3 Plus A/C" rooftop unit as
    an exact endpoint component -- a new part type within the existing
    Coleman-Mach vendor arc (rooftop AC, not thermostats), split out from
    the `8330A733` ceiling plenum (see GitHub issue #23) which is a
    physically separate component the AC head sits above, not this unit.

    Identity comes from two photographs of the same physical unit (obs
    #111): a permanent rating plate riveted inside the AC base/shroud ring
    ('MODEL NO. 48253B866  SERIAL NO. 051218899') and a separate white
    manufacturer label on the same unit reading 'MACH 3 PLUS A/C'. The
    model number is independently corroborated (not just visually) by
    Coleman-Mach's own online model-number-replacement lookup tool, which
    returns 48253B866 as a real catalogued number ("MACH 3+ EZ A/C WHT
    OEM") with current replacement 38203-066 -- the exact SKU the 2025
    dealer catalog lists as "MACH 3 Plus, 13,500 BTU A/C - Textured White"
    (see VENDOR-Coleman-Mach.md sec 1 catalog evidence already in this
    fixture). That supersession/replacement relationship is not built as
    an edge here -- 38203-066 is not itself confirmed in-hand or built as a
    component, so this stays a description-level note, same caution
    already applied elsewhere in this vendor arc (e.g. the compressor's
    "USE 14504209" note in coleman_ac_repair_parts_and_fits()).

    The pink factory "build sheet" transcription that originally motivated
    this research (illegible handwritten "Coleman 4853B866"-ish text) is
    superseded by this photographed rating plate as the identity source --
    it was too illegible to trust alone and is not cited as evidence here.
    """
    _validate_observation_source(dataplate_row, 113, "dataplate_photo", 2,
                                  "AC rating plate")
    plate = _normalized_attributes(dataplate_row)
    plate_ids = {(i["ns"], i["value"]) for i in plate["physical_identifiers"]}
    if plate_ids != COLEMAN_AC_48253B866_IDENTIFIERS:
        raise ValueError(f"unexpected Coleman AC identifiers: {plate_ids}")
    if plate.get("serial_number") != "051218899":
        raise ValueError(f"unexpected Coleman AC serial: {plate.get('serial_number')}")

    def text_attr(name, value, provenance="dataplate_photo"):
        return ComponentAttribute(
            component_id, name, provenance, dataplate_row["id"], value_text=value,
            resolver_version=COLEMAN_AC_ENDPOINT_RESOLVER_VERSION)

    component = Component(component_id, COLEMAN_AC_PART_TYPE, None)
    identifiers = [Identifier(component_id, "coleman", "48253B866", "rating_plate")]
    attributes = [
        text_attr("serial", plate["serial_number"]),
        text_attr("product_line", plate["product_type"]),
    ]
    return component, identifiers, attributes


def atwood_gh6_6e_component(dataplate_row, component_id):
    """
    Build the owner's in-hand Atwood GH6-6E water heater as an exact endpoint
    component -- the project's first in-hand teardown anchor for Atwood
    (previously catalog-only, see VENDOR-Atwood.md sec 7 and issue #13).

    Identity (model GH6-6E, spec 266038, serial 96266000345) was settled only
    after two rounds of independent re-reads of the physical data plate photo
    (obs #111) -- an attached AI research report's "GH6-GE" reading was ruled
    out (doesn't fit Atwood's own Pilot/Electronic model-number grammar, no
    independent web corroboration) and its "Spec 260038" transcription was
    corrected to 266038 by direct visual re-inspection. See issue #33.
    """
    _validate_observation_source(dataplate_row, 111, "dataplate_photo", 2,
                                  "GH6-6E data plate")
    plate = _normalized_attributes(dataplate_row)
    if plate.get("model") != "GH6-6E":
        raise ValueError(f"unexpected GH6-6E data plate model: {plate.get('model')}")

    def text_attr(name, value):
        return ComponentAttribute(
            component_id, name, "dataplate_photo", dataplate_row["id"], value_text=value,
            resolver_version=ATWOOD_GH6_6E_RESOLVER_VERSION)

    def number_attr(name, value, unit=None):
        return ComponentAttribute(
            component_id, name, "dataplate_photo", dataplate_row["id"], value_number=value,
            unit=unit, resolver_version=ATWOOD_GH6_6E_RESOLVER_VERSION)

    def bool_attr(name, value):
        return ComponentAttribute(
            component_id, name, "dataplate_photo", dataplate_row["id"], value_boolean=value,
            resolver_version=ATWOOD_GH6_6E_RESOLVER_VERSION)

    component = Component(component_id, WATER_HEATER_PART_TYPE, None)
    identifiers = [Identifier(component_id, "atwood", "GH6-6E", "data_plate")]
    attributes = [
        text_attr("spec_no", plate["spec_no"]),
        text_attr("serial", plate["serial_number"]),
        number_attr("capacity_gal", float(plate["capacity_gal"]), "gal"),
        text_attr("power_type", "gas_only"),
        text_attr("ignition_type", "electronic"),
        bool_attr("heat_exchanger", True),
        number_attr("input_btu_hr", float(plate["input_btuh"]), "BTU/h"),
        number_attr("recovery_gal_hr", float(plate["recovery_gas_only_gph"]), "gal/h"),
        number_attr("min_gas_pressure_in_wc", float(plate["min_gas_pressure_in_wc"]), "in_wc"),
        number_attr("manifold_pressure_in_wc", float(plate["manifold_pressure_wc"]), "in_wc"),
        number_attr("max_working_pressure_psi", float(plate["max_working_pressure_psi"]), "psi"),
        number_attr("test_pressure_psi", float(plate["test_pressure_psi"]), "psi"),
    ]
    return component, identifiers, attributes


def coleman_ac_repair_parts_and_fits(conn, catalog_row, host_component_id):
    """
    Build Coleman-Mach 48253B866 repair/service-part components and their
    "fits" edges to the in-hand AC -- same one-host, many-repair-parts shape
    as atwood_repair_parts_and_fits()/norcold_base_board_fits(). Sourced to
    a single retailer illustrated-parts breakdown page for this exact
    product ID (obs #114, Young Farts RV Parts), the only parts-level source
    found for this legacy model -- Coleman-Mach's own current document
    library and 2025 catalog (already in this fixture, see VENDOR doc) cover
    the current 38203-066 replacement's sales listing, not a service parts
    breakdown for either SKU. Retailer-only sourcing (tier 7, not a
    manufacturer PDF) is reflected in weaker "fits" evidence than the
    manufacturer-catalog-sourced Atwood/Norcold repair-part edges.

    Two rows in the table name each other directly: `1468-3069` ("FAN MOTOR
    (FASCO D1092) USE 1468A3069") and `1468A3069` ("MOTOR") -- the same
    explicit "(USE X)" supersession wording already used for Suburban/
    Coleman-Mach thermostats and Norcold's optical control board elsewhere
    in this project. Both are still built as fitting components (the old
    number is a legitimate historical part, not a typo), plus a `supersedes`
    edge between them. The compressor row's own "USE 14504209" note is
    NOT built the same way: 14504209 does not otherwise appear in this
    table and is not independently confirmed, so it stays a caveat inside
    the component's description rather than an invented component.
    """
    _validate_observation_source(catalog_row, 114, "retailer_page", 7, "repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #114 catalog has no repair_part_fitment_table: {parts}")

    results = []
    component_ids_by_part = {}
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"Coleman AC repair part {part_number} missing required fields: {spec}")
        if spec["applies_to"] != ["48253B866"]:
            raise ValueError(f"Coleman AC repair part {part_number} has unexpected applies_to: "
                              f"{spec['applies_to']}")

        component_id = f"c_placeholder_coleman_ac_part_{part_number}"
        component_ids_by_part[part_number] = component_id
        component = Component(component_id, COLEMAN_AC_REPAIR_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", part_number, "catalog")]
        attributes = [ComponentAttribute(
            component_id, "description", "retailer_page", catalog_row["id"],
            value_text=spec["description"], resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

        edge = Edge(
            type=EDGE_TYPE_FITS,
            from_component_id=component_id,
            to_component_id=host_component_id,
            group_key="coleman_ac_48253b866_repair_part",
            status="candidate",
            resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION,
            notes=f"Young Farts RV Parts' 48253B866 illustrated parts breakdown names "
                  f"{part_number} as fitting this exact product ID.",
        )
        insert_edge(conn, edge)
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("retailer_cross_reference", 1.0, 0.0, catalog_row["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        results.append((component, identifiers, attributes, [edge.id]))

    old_motor, new_motor = "1468-3069", "1468A3069"
    if parts.get(old_motor, {}).get("superseded_by") != new_motor:
        raise ValueError(f"expected {old_motor} to name {new_motor} as its replacement")
    supersession_edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=component_ids_by_part[old_motor],
        to_component_id=component_ids_by_part[new_motor],
        group_key="coleman_ac_48253b866_fan_motor",
        status="candidate",
        resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION,
        notes="Young Farts RV Parts' 48253B866 parts breakdown names 1468A3069 as the "
              "replacement for 1468-3069 ('USE 1468A3069').",
    )
    insert_edge(conn, supersession_edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=supersession_edge.id,
        note="Retailer parts breakdown's own '(USE 1468A3069)' wording for the "
             "Fasco D1092 fan motor."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("retailer_cross_reference", 1.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=supersession_edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return results, supersession_edge.id


COLEMAN_AC_COMPRESSOR_OLD_PART = "14504029"
COLEMAN_AC_COMPRESSOR_NEW_PART = "14504209"


def coleman_ac_compressor_supersession(conn, original_row, corroboration_row, host_component_id):
    """
    Build the `14504029` -> `14504209` Tecumseh compressor supersession for
    the 48253B866 rooftop AC -- issue #38, closing the gap left open by
    coleman_ac_repair_parts_and_fits() (obs #114's own docstring/caveat):
    `14504029`'s source row there says "USE 14504209" but 14504209 appeared
    nowhere else in that one table, so it was built only as a caveat inside
    `14504029`'s description, not as a component or edge -- this project's
    standing rule against building identifiers from a single unconfirmed
    mention.

    That mention is no longer single. obs #126 independently corroborates
    it from a *different* retailer domain (rvpartshop.com's 48203-879 parts
    list, not youngfartsrvparts.com like obs #114) giving the identical
    "USE 14504209 * SEE NOTES FOR ADJ NEEDED*" row for a different rooftop
    unit sharing the same compressor, plus two more Young Farts pages
    (48203-876, 48253A876) repeating it, plus two dedicated product listings
    (Young Farts' own C7W14504209 and a third domain, highskyrvparts.com)
    independently identifying 1450-4209 as a real, currently-listed
    (discontinued) Coleman/RVP compressor package "For Use With Coleman
    Mach 3 Plus EZ Series Air Conditioners" -- the same "Mach 3+ EZ A/C"
    family Coleman-Mach's own lookup tool already assigned to the in-hand
    48253B866 (obs #113, see VENDOR-Coleman-Mach.md sec 9). Four independent
    parts-list pages across two retailer domains, plus two independent
    dedicated-product listings across two more, together clear the bar this
    project sets for treating a fitment claim as evidenced rather than a
    single unconfirmed mention.

    None of the six sources checked (across obs #114 and #126) explain what
    the "SEE NOTES FOR ADJ NEEDED" adjustment actually involves -- no
    notes/footnote section was found on any of the four parts-list pages.
    That detail stays an open caveat on the supersession edge rather than
    an invented explanation.
    """
    _validate_observation_source(original_row, 114, "retailer_page", 7,
                                  "compressor original mention")
    _validate_observation_source(corroboration_row, 126, "retailer_page", 7,
                                  "compressor corroboration")

    original = _normalized_attributes(original_row)
    original_note = original.get("repair_part_fitment_table", {}) \
        .get(COLEMAN_AC_COMPRESSOR_OLD_PART, {}).get("note", "")
    if COLEMAN_AC_COMPRESSOR_NEW_PART not in original_note:
        raise ValueError(f"obs #114 compressor note no longer names {COLEMAN_AC_COMPRESSOR_NEW_PART}: "
                          f"{original_note}")

    corroboration = _normalized_attributes(corroboration_row)
    corroboration_fitment = corroboration.get("repair_part_fitment_table", {}) \
        .get(COLEMAN_AC_COMPRESSOR_OLD_PART, {})
    if corroboration_fitment.get("superseded_by") != COLEMAN_AC_COMPRESSOR_NEW_PART:
        raise ValueError(f"obs #126 does not corroborate {COLEMAN_AC_COMPRESSOR_OLD_PART} -> "
                          f"{COLEMAN_AC_COMPRESSOR_NEW_PART}: {corroboration_fitment}")
    corroboration_identifiers = {(i["ns"], i["value"]) for i in corroboration["physical_identifiers"]}
    if ("coleman", COLEMAN_AC_COMPRESSOR_NEW_PART) not in corroboration_identifiers:
        raise ValueError(f"obs #126 missing {COLEMAN_AC_COMPRESSOR_NEW_PART} identifier: "
                          f"{corroboration_identifiers}")

    old_component_id = f"c_placeholder_coleman_ac_part_{COLEMAN_AC_COMPRESSOR_OLD_PART}"
    new_component_id = f"c_placeholder_coleman_ac_part_{COLEMAN_AC_COMPRESSOR_NEW_PART}"

    new_component = Component(new_component_id, COLEMAN_AC_REPAIR_PART_TYPE, None)
    new_identifiers = [Identifier(new_component_id, "coleman", COLEMAN_AC_COMPRESSOR_NEW_PART, "catalog")]
    new_attributes = [ComponentAttribute(
        new_component_id, "description", "retailer_page", corroboration_row["id"],
        value_text=corroboration["product_type"], resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION)]
    insert_component(conn, new_component)
    for identifier in new_identifiers:
        insert_identifier(conn, identifier)
    for attribute in new_attributes:
        insert_component_attribute(conn, attribute)

    fits_edge = Edge(
        type=EDGE_TYPE_FITS,
        from_component_id=new_component_id,
        to_component_id=host_component_id,
        group_key="coleman_ac_48253b866_repair_part",
        status="candidate",
        resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION,
        notes=f"Independent cross-domain retailer corroboration (obs #126) names "
              f"{COLEMAN_AC_COMPRESSOR_NEW_PART} as a real Coleman/RVP compressor package "
              f"for the Mach 3 Plus EZ Series family the in-hand 48253B866 belongs to.",
    )
    insert_edge(conn, fits_edge)
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("retailer_cross_reference", 1.0, 0.0, corroboration_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=fits_edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    supersession_edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=old_component_id,
        to_component_id=new_component_id,
        group_key="coleman_ac_48253b866_compressor",
        status="candidate",
        resolver_version=COLEMAN_AC_PARTS_RESOLVER_VERSION,
        notes=f"Four independent parts-list pages across two retailer domains "
              f"(youngfartsrvparts.com obs #114/#126-corroborated, rvpartshop.com obs #126) "
              f"name {COLEMAN_AC_COMPRESSOR_NEW_PART} as the replacement for "
              f"{COLEMAN_AC_COMPRESSOR_OLD_PART} ('USE 14504209').",
    )
    insert_edge(conn, supersession_edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=supersession_edge.id,
        note="All source pages carry the same '* SEE NOTES FOR ADJ NEEDED*' caveat but none "
             "include the referenced notes section -- the nature of the required adjustment "
             "(mounting, refrigerant charge, electrical) remains unconfirmed."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("retailer_cross_reference", 1.0, 0.0, original_row["id"]),
        ("retailer_cross_reference", 1.0, 0.0, corroboration_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=supersession_edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return (new_component, new_identifiers, new_attributes, [fits_edge.id]), supersession_edge.id


COLEMAN_PLENUM_8330A733_IDENTIFIERS = {("coleman", "8330A733")}


def coleman_plenum_8330a733_component(dataplate_row, catalog_row, component_id):
    """
    Build the owner's in-hand Coleman-Mach/RVP "8330A733" flush-mount
    ceiling plenum as an exact endpoint component -- a new part type within
    the existing Coleman-Mach vendor arc (issue #23), physically distinct
    from the `48253B866` rooftop AC head it sits below (VENDOR-Coleman-Mach.md
    sec 9): the AC head does the cooling, this plenum is the interior
    duct/return-air/relay-box assembly bolted underneath it.

    Identity comes from a small embossed tag riveted inside the plenum's own
    electrical/junction box (obs #122, photographed in-hand 2026-08-05) --
    the same "8330A733" number visible on the owner's coach that originally
    motivated issue #23, before the AC head/plenum split was discovered. The
    same photo set also shows the plenum's low-voltage terminal strip
    ("FREEZE B- Y GH GL" on block LAPP21), which independently corroborates
    Airxcel's own installation manual for this exact family (obs #123, doc
    1976G278 (5-12)): its terminal table names the identical five
    designations with the identical wire colors (B/Blue, Y/Yellow, GH/Green,
    GL/Gray, FREEZE/White) -- physical evidence and manufacturer documentation
    agreeing independently, not just one source repeating the other.

    The commercial description ("Cool-Only Ceiling Assembly, Lateral Ducted,
    without Thermostat, White", order #63130) is sourced to a direct read of
    a contemporaneous Coleman-Mach/RVP dealer catalog (obs #124, tier 1 --
    not secondhand from the attached AI research report, whose 8330A733
    identity claim this independently corroborates). That catalog also
    supplies the rooftop-unit family-compatibility statement recorded on
    obs #123's `compatible_system_claim` (installs under any 47200/48200/
    49200-series head) -- broad enough, and about a product family rather
    than the specific in-hand `48253B866` SKU, that it is NOT built as a
    `fits` edge to that component here, matching this project's standing
    caution about generic family-level claims (see the AC endpoint's own
    unbuilt `38203-066` replacement note). The two components' real-world
    pairing -- same coach, same ceiling opening -- stays a narrative fact in
    VENDOR-Coleman-Mach.md rather than an invented edge.

    obs #124 also caught a discrepancy in the attached AI research report:
    the report proposed `8430A633` as a "strong functional-successor
    candidate", but this catalog's own current Chillgrille cross-reference
    page names different model-8330-series numbers as the replacement
    ceiling assemblies for ducted Coleman-Mach ACs. Neither is built as a
    `supersedes` edge -- both stay caveats, but the report's specific
    successor claim is not carried forward.
    """
    _validate_observation_source(dataplate_row, 122, "dataplate_photo", 2,
                                  "plenum identity photo")
    _validate_observation_source(catalog_row, 124, "manufacturer_pdf", 1,
                                  "plenum catalog description")
    plate = _normalized_attributes(dataplate_row)
    plate_ids = {(i["ns"], i["value"]) for i in plate["physical_identifiers"]}
    if plate_ids != COLEMAN_PLENUM_8330A733_IDENTIFIERS:
        raise ValueError(f"unexpected Coleman plenum identifiers: {plate_ids}")

    catalog = _normalized_attributes(catalog_row)
    if catalog.get("vendor_catalog_number") != "63130":
        raise ValueError(f"unexpected Coleman plenum order number: {catalog.get('vendor_catalog_number')}")

    def text_attr(name, value, row):
        return ComponentAttribute(
            component_id, name, row["source_type"], row["id"], value_text=value,
            resolver_version=COLEMAN_PLENUM_ENDPOINT_RESOLVER_VERSION)

    component = Component(component_id, COLEMAN_AC_PLENUM_PART_TYPE, None)
    identifiers = [Identifier(component_id, "coleman", "8330A733", "model_tag")]
    attributes = [
        text_attr("product_line", plate["product_type"], dataplate_row),
        text_attr("description", catalog["product_type"], catalog_row),
    ]
    return component, identifiers, attributes


def coleman_plenum_repair_parts_and_fits(conn, catalog_row, host_component_id):
    """
    Build the 8330A733 ceiling plenum's repair-part components and their
    `fits` edges -- same one-host, many-repair-parts shape as
    coleman_ac_repair_parts_and_fits()/atwood_repair_parts_and_fits(), sourced
    to a direct read of RV Products/Airxcel's own repair-parts drawing
    R-483B (3-07) (obs #125, tier 1 manufacturer engineering drawing --
    independently corroborates the attached AI research report's identical
    8-part table rather than trusting it secondhand). This is stronger
    sourcing than the AC head's own repair parts (retailer-page-only, tier
    7): a genuine manufacturer drawing, not a retailer's transcription of
    one, so these edges get `manufacturer_assertion` evidence instead of
    `retailer_cross_reference` -- matching atwood_gh6_6e_tank_91642_fits()'s
    tier-1 pattern rather than coleman_ac_repair_parts_and_fits()'s tier-7
    one.

    One part (`6798-3041`, "Grille (Plastic)") is physically corroborated in
    obs #125's own quoted_text: the owner's in-hand grille has "6798 304"
    molded directly into the plastic (photographed 2026-07-31), matching
    this drawing's number under the same punctuation-normalization already
    seen elsewhere in this project's Coleman-Mach parts (e.g. the AC's own
    "83303501"/"8330101" retailer variants).
    """
    _validate_observation_source(catalog_row, 125, "manufacturer_pdf", 1, "plenum repair parts")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #125 catalog has no repair_part_fitment_table: {parts}")

    results = []
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"Coleman plenum repair part {part_number} missing required fields: {spec}")
        if spec["applies_to"] != ["8330A733"]:
            raise ValueError(f"Coleman plenum repair part {part_number} has unexpected applies_to: "
                              f"{spec['applies_to']}")

        component_id = f"c_placeholder_coleman_plenum_part_{part_number}"
        component = Component(component_id, COLEMAN_AC_PLENUM_REPAIR_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", part_number, "catalog")]
        attributes = [ComponentAttribute(
            component_id, "description", "manufacturer_pdf", catalog_row["id"],
            value_text=spec["description"], resolver_version=COLEMAN_PLENUM_PARTS_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

        edge = Edge(
            type=EDGE_TYPE_FITS,
            from_component_id=component_id,
            to_component_id=host_component_id,
            group_key="coleman_plenum_8330a733_repair_part",
            status="candidate",
            resolver_version=COLEMAN_PLENUM_PARTS_RESOLVER_VERSION,
            notes=f"RV Products/Airxcel's own repair-parts drawing R-483B (3-07) names "
                  f"{part_number} as fitting the 8330A733 ceiling plenum.",
        )
        insert_edge(conn, edge)
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        results.append((component, identifiers, attributes, [edge.id]))

    return results


def atwood_gh6_6e_tank_91642_fits(conn, catalog_row, host_component_id):
    """
    Build Atwood repair part `91642` (front-mount inner tank) as a
    repair-part component and its `fits` edge to the in-hand GH6-6E water
    heater -- same many-to-many "fits" shape as
    atwood_repair_parts_and_fits() (see that function's docstring), sourced
    to a genuinely independent third-party OEM catalog rather than Atwood's
    own service manual: the 1994 Winnebago WF424RC Parts Catalog (obs #112),
    read directly from the primary-source PDF (not secondhand from the
    attached AI research report). That catalog names Atwood part 91642 as
    the front-mount inner tank for "GH6-4E & 6E" under its own "WATER HEATER
    W/MOTOR AID" heading, which also names GH6-3E/GH6-4E/GH6-6E together as
    one product line -- corroborating the report's core model family claim
    even though two of the report's own numeric transcriptions needed
    correction. See issue #33; lower-confidence parts from the same report
    (board/electrode/valve/orifice supersession chains, disputed thermostat
    calibration) are deliberately NOT built here -- spun off to a follow-up
    issue instead.
    """
    _validate_observation_source(catalog_row, 112, "manufacturer_pdf", 2,
                                  "Winnebago parts catalog")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or "91642" not in parts:
        raise ValueError(f"obs #112 catalog missing 91642 fitment row: {parts}")
    spec = parts["91642"]
    if spec.get("applies_to") != ["GH6-6E"]:
        raise ValueError(f"unexpected 91642 applies_to: {spec.get('applies_to')}")

    component_id = "c_placeholder_wh_atwood_part_91642"
    component = Component(component_id, ATWOOD_PART_TYPE, None)
    identifiers = [Identifier(component_id, "atwood", "91642", "catalog")]
    attributes = [ComponentAttribute(
        component_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text=spec["description"], resolver_version=ATWOOD_GH6_6E_PARTS_RESOLVER_VERSION)]
    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_FITS,
        from_component_id=component_id,
        to_component_id=host_component_id,
        group_key="atwood_gh6_6e_tank",
        status="candidate",
        resolver_version=ATWOOD_GH6_6E_PARTS_RESOLVER_VERSION,
        notes="The 1994 Winnebago WF424RC Parts Catalog names Atwood 91642 as "
              "the front-mount inner tank for \"GH6-4E & 6E\", independently "
              "verified by direct PDF read (not secondhand from the attached "
              "AI research report).",
    )
    insert_edge(conn, edge)
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, [edge.id]


def atwood_gh6_6e_gas_valve_chain(conn, catalog_row, host_component_id):
    """
    Build the `93870` -> `93844` White Rodgers gas-valve supersession and
    both valves' `fits` edges to the in-hand GH6-6E water heater -- issue
    #42, split from the deferred #35 gas-valve item ("91605 -> 93870 ->
    93844 + 94787"). Sourced to a direct read of Atwood's own January 2014
    "Replacement Part Reference" table (obs #116), which combines both part
    numbers into a single row ("93870/93844 White Rodgers Valve (6&10
    Gal.)") with GH6-6E checked -- cross-checked against the January 2007
    edition, which lists only 93870 (checked for GH6-6E) and does not yet
    name 93844, confirming the combined listing is a later revision rather
    than an extraction artifact.

    The `94787` one-piece bracket named in the same issue's attached AI
    research report is deliberately NOT built here: column-by-column
    verification of all three local Atwood manuals (2003, 2007, Jan 2014)
    shows `94787` is never checked for GH6-6E in any edition -- the
    report's `93243 -> 94787` bracket chain comes from other models'
    parts lists, over-generalized to GH6-6E. See issue #42 review comment.

    93870 is also named in the Electronic Ignition table (obs #96), which
    runs earlier in the build and, before this, had no way to know this
    function would later mint its own canonical `c_placeholder_wh_atwood_
    part_93870` -- the two other Atwood resolvers avoid this by looking an
    identifier up before creating a component, but that only works when the
    canonical ID is whichever component gets found first. Here the ID is
    fixed (both `atwood_91605_93870_supersession()` and this function's own
    93870->93844 supersession name it directly), so instead this folds any
    such earlier duplicate onto the canonical component after creating it,
    via merge_component_into() -- issue #48.
    """
    _validate_observation_source(catalog_row, 116, "manufacturer_pdf", 2,
                                  "Jan 2014 Replacement Part Reference table")
    catalog = _normalized_attributes(catalog_row)
    parts = catalog.get("repair_part_fitment_table")
    if not isinstance(parts, dict) or not parts:
        raise ValueError(f"obs #116 catalog has no repair_part_fitment_table: {parts}")

    results = []
    component_ids_by_part = {}
    for part_number, spec in parts.items():
        if not isinstance(spec, dict) or "description" not in spec or "applies_to" not in spec:
            raise ValueError(f"gas valve {part_number} missing required fields: {spec}")
        if spec["applies_to"] != ["GH6-6E"]:
            raise ValueError(f"gas valve {part_number} has unexpected applies_to: "
                              f"{spec['applies_to']}")

        component_id = f"c_placeholder_wh_atwood_part_{part_number}"
        component_ids_by_part[part_number] = component_id
        duplicates = [c.component_id for c in get_components_by_identifier(conn, "atwood", part_number)
                      if c.component_id != component_id]
        component = Component(component_id, ATWOOD_PART_TYPE, None)
        identifiers = [Identifier(component_id, "atwood", part_number, "catalog")]
        attributes = [ComponentAttribute(
            component_id, "description", "manufacturer_pdf", catalog_row["id"],
            value_text=spec["description"], resolver_version=ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION)]
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)
        for duplicate_id in duplicates:
            merge_component_into(conn, duplicate_id, component_id)

        edge = Edge(
            type=EDGE_TYPE_FITS,
            from_component_id=component_id,
            to_component_id=host_component_id,
            group_key="atwood_gh6_6e_gas_valve",
            status="candidate",
            resolver_version=ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION,
            notes="Atwood's own January 2014 Replacement Part Reference table names "
                  f"{part_number} as fitting GH6-6E (combined '93870/93844' row, "
                  "cross-checked against the Jan 2007 edition's 93870-only row).",
        )
        insert_edge(conn, edge)
        for event_type, alpha, beta, source_id in (
            ("attribute_prior", 1.0, 1.0, None),
            ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ):
            insert_evidence(conn, RelationshipEvidence(
                edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
                effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
        results.append((component, identifiers, attributes, [edge.id]))

    old_valve, new_valve = "93870", "93844"
    if parts.get(old_valve, {}).get("superseded_by") != new_valve:
        raise ValueError(f"expected {old_valve} to name {new_valve} as its replacement")
    supersession_edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=component_ids_by_part[old_valve],
        to_component_id=component_ids_by_part[new_valve],
        group_key="atwood_gh6_6e_gas_valve",
        status="candidate",
        resolver_version=ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION,
        notes="Atwood's Jan 2014 Replacement Part Reference table combines 93870 and "
              "93844 into a single row, absent from the separately-confirmed Jan 2007 "
              "edition's 93870-only listing -- read as 93844 superseding 93870.",
    )
    insert_edge(conn, supersession_edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=supersession_edge.id,
        note="Jan 2014 table's combined '93870/93844' row for GH6-6E, absent from the "
             "Jan 2007 edition's 93870-only row for the same model."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=supersession_edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return results, supersession_edge.id


def atwood_91605_93870_supersession(conn, catalog_row):
    """
    Build the `91605` -> `93870` gas-valve supersession -- the predecessor
    step ahead of `atwood_gh6_6e_gas_valve_chain()`'s 93870 -> 93844 -- as
    a standalone component pair with a weaker evidence tier than that
    manufacturer-sourced chain, since no Atwood factory document names
    91605 at all (checked all three local service manuals; zero hits).

    Sourced to obs #115: Leisure Vehicle Services' 2012 Atwood spares list
    ("91605 Replaced by 93870"), a distributor/retailer document, cross-
    checked against a direct read of the 1995 Winnebago ICF23RC Parts
    Catalog PDF (not secondhand from the attached AI research report),
    which lists 91605 as "VALVE-GAS" under its "WATER HEATER W/ELECTRIC
    IGNITION" (G6A-7E) section and 93870 as "SOLENOID VALVE AND BRACKET"
    under its "WATER HEATER W/MOTOR AID" (GH6-7E) section, both at the
    identical Winnebago-internal key part number (051393-01-726). That
    catalog alone -- two adjacent model sections rather than one model's
    revision history -- does not independently prove chronological
    supersession; it corroborates without duplicating the LVS list's
    explicit wording, per issue #42's "second document family" standard.

    91605 is not built with a `fits` edge to GH6-6E: unlike 93870/93844
    (obs #116, Atwood's own applicability matrix), no source here states
    91605's model applicability directly -- only that it preceded 93870,
    which does fit GH6-6E.
    """
    _validate_observation_source(catalog_row, 115, "retailer_page", 7,
                                  "Atwood spares list / Winnebago catalog cross-check")
    catalog = _normalized_attributes(catalog_row)
    chart = catalog.get("replacement_chart_entries")
    if not isinstance(chart, dict) or chart.get("91605") != "93870":
        raise ValueError(f"obs #115 catalog missing 91605 -> 93870: {chart}")

    old_id, new_id = "c_placeholder_wh_atwood_part_91605", "c_placeholder_wh_atwood_part_93870"
    old_component = Component(old_id, ATWOOD_PART_TYPE, None)
    old_identifiers = [Identifier(old_id, "atwood", "91605", "catalog")]
    old_attributes = [ComponentAttribute(
        old_id, "description", "retailer_page", catalog_row["id"],
        value_text="Gas valve (predecessor); Winnebago 1995 ICF23RC catalog: "
                    "VALVE-GAS, WATER HEATER W/ELECTRIC IGNITION / G6A-7E section",
        resolver_version=ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION)]
    insert_component(conn, old_component)
    for identifier in old_identifiers:
        insert_identifier(conn, identifier)
    for attribute in old_attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_SUPERSEDES,
        from_component_id=old_id,
        to_component_id=new_id,
        group_key="atwood_gh6_6e_gas_valve",
        status="candidate",
        resolver_version=ATWOOD_GH6_6E_VALVE_RESOLVER_VERSION,
        notes="Leisure Vehicle Services' 2012 Atwood spares list states '91605 "
              "Replaced by 93870', cross-checked against the 1995 Winnebago ICF23RC "
              "catalog's parallel G6A-7E/GH6-7E valve listings at the same key part "
              "number (051393-01-726).",
    )
    insert_edge(conn, edge)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=edge.id,
        note="Distributor spares list's own '91605 Replaced by 93870' wording; not an "
             "Atwood factory document, so built at retailer-tier evidence."))
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("retailer_cross_reference", 1.0, 0.0, catalog_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return (old_component, old_identifiers, old_attributes), edge.id


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


def identifier_candidate_evidence_from_label_photo(obs_row):
    """
    Second evidence event for the AR7815/7330F3858 candidate: a photograph of the
    physical product label showing both identifiers printed on the same unit
    (obs #104), independent of and stronger than the single-retailer claim in
    identifier_candidate_from_observation (obs #43).
    """
    attrs = _normalized_attributes(obs_row)
    relation = attrs.get("sku_relationship")
    models = attrs.get("model_spec_table")
    if not isinstance(relation, dict) or relation.get("type") != \
            "photographed_product_label":
        raise ValueError(f"observation #{obs_row['id']} has no label-photo claim")
    values = relation.get("identifiers")
    if values != ["AR7815", "7330F3858"] or not isinstance(models, dict):
        raise ValueError(f"unexpected identifier-equivalence claim: {relation}")
    namespaces = {value: models.get(value, {}).get("namespace") for value in values}
    if namespaces != {"AR7815": "icm", "7330F3858": "coleman"}:
        raise ValueError(f"unexpected identifier namespaces: {namespaces}")
    return IdentifierEquivalenceEvidence(
        candidate_id=None, event_type="teardown_co_occurrence",
        effect_alpha=3.0, effect_beta=0.0, occurred_at=now_iso(),
        source_observation_id=obs_row["id"])


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
        edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id=src_id,
                    to_component_id=dst_id,
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

    edge_forward = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id=from_id,
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

    edge_backward = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id=to_id,
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

    edge = Edge(type=EDGE_TYPE_SUBSTITUTES, from_component_id=from_id,
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
            type=EDGE_TYPE_SUPERSEDES,
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
        f"SELECT * FROM edges WHERE type = '{EDGE_TYPE_SUPERSEDES}' "
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
    obs104 = load_observation(obs_db, 104)  # AR7815/7330F3858 label photo

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

    obs55 = load_observation(obs_db, 55)  # 7330F3361 retailer corroboration
    obs56 = load_observation(obs_db, 56)  # 7330-3861 retailer corroboration
    second_wave_ids = {
        "7330F3361": "c_placeholder_tstat_7330f3361",
        "7330-3861": "c_placeholder_tstat_7330_3861",
        "7330B3441": "c_placeholder_tstat_7330b3441",
    }
    second_wave_endpoints = coleman_second_wave_endpoint_components(
        obs40, [obs55, obs56], second_wave_ids)
    _validate_coleman_endpoint_results(second_wave_endpoints, second_wave_ids)
    second_wave_by_model = {
        identifiers[0].value: (component, identifiers, attributes)
        for component, identifiers, attributes in second_wave_endpoints
    }
    if set(second_wave_by_model) != set(second_wave_ids):
        failures.append(f"Coleman second-wave endpoint set mismatch: {set(second_wave_by_model)}")
    for model, (component, identifiers, attributes) in second_wave_by_model.items():
        if component.part_type_id != 415 or component.interchange_code is not None:
            failures.append(f"invalid second-wave endpoint component: {component}")
        if [(i.ns, i.value, i.visibility) for i in identifiers] != [
                ("coleman", model, None)]:
            failures.append(f"invalid second-wave endpoint identifiers for {model}: {identifiers}")

    expected_second_wave = {
        "7330F3361": {
            "function": ("cool_only", 40, "manufacturer_page",
                         COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "color": ("white", 40, "manufacturer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "interface_type": (
                "analog", 40, "manufacturer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "stages": ("single", 55, "retailer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "voltage": ("12VDC", 55, "retailer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
        },
        "7330-3861": {
            "function": ("cool_only", 40, "manufacturer_page",
                         COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "color": ("black", 40, "manufacturer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "interface_type": (
                "analog", 40, "manufacturer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "stages": ("single", 56, "retailer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "voltage": ("12VDC", 56, "retailer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
        },
        "7330B3441": {
            "function": ("single_stage_standard", 40, "manufacturer_page",
                         COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "color": ("white", 40, "manufacturer_page", COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "interface_type": ("analog", 40, "manufacturer_page_single_source",
                               COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
            "stages": ("single", 40, "manufacturer_page_inferred",
                      COLEMAN_SECOND_WAVE_RESOLVER_VERSION),
        },
    }
    for model, (_, _, attributes) in second_wave_by_model.items():
        actual = {
            attribute.name: (
                attribute.value_text, attribute.source_observation_id,
                attribute.provenance, attribute.resolver_version)
            for attribute in attributes
        }
        if actual != expected_second_wave[model]:
            failures.append(f"Coleman second-wave attributes mismatch for {model}: {actual}")

    invalid_second_wave_inputs = (
        (changed_row(obs40, lambda e: e["models"].pop("7330B3441")), [obs55, obs56]),
        (obs40, [obs55]),
        (obs40, [obs55, changed_row(obs56, lambda e: e["models"]["7330-3861"].__setitem__(
            "voltage", "24VAC"))]),
        (dict(obs40, id=400), [obs55, obs56]),
        (obs40, [dict(obs55, source_type="manufacturer_page"), obs56]),
    )
    for product, corroboration in invalid_second_wave_inputs:
        try:
            coleman_second_wave_endpoint_components(product, corroboration, second_wave_ids)
            failures.append("invalid Coleman second-wave endpoint evidence was accepted")
        except ValueError:
            pass

    obs58 = load_observation(obs_db, 58)  # wildcard family installation manual
    obs59 = load_observation(obs_db, 59)  # MakariosRV replacement chart
    obs64 = load_observation(obs_db, 64)  # trvparts.com corroboration
    obs74 = load_observation(obs_db, 74)  # rvcomfort.com E-suffix naming
    third_wave_ids = {
        "7330E335": "c_placeholder_tstat_7330e335",
        "7330E385": "c_placeholder_tstat_7330e385",
        "7330E336": "c_placeholder_tstat_7330e336",
    }
    third_wave_endpoints = coleman_third_wave_endpoint_components(
        obs74, obs58, third_wave_ids)
    _validate_coleman_endpoint_results(third_wave_endpoints, third_wave_ids)
    third_wave_by_model = {
        identifiers[0].value: (component, identifiers, attributes)
        for component, identifiers, attributes in third_wave_endpoints
    }
    if set(third_wave_by_model) != set(third_wave_ids):
        failures.append(f"Coleman third-wave endpoint set mismatch: {set(third_wave_by_model)}")
    for model, (component, identifiers, attributes) in third_wave_by_model.items():
        if component.part_type_id != 415 or component.interchange_code is not None:
            failures.append(f"invalid third-wave endpoint component: {component}")
        if [(i.ns, i.value, i.visibility) for i in identifiers] != [
                ("coleman", model, None)]:
            failures.append(f"invalid third-wave endpoint identifiers for {model}: {identifiers}")

    expected_third_wave = {
        "7330E335": {
            "function": ("heat_cool", 74, "manufacturer_page",
                         COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "interface_type": ("analog", 58, "manufacturer_pdf_single_source",
                                COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "stages": ("single", 58, "manufacturer_pdf_inferred",
                       COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
        },
        "7330E385": {
            "function": ("heat_cool", 74, "manufacturer_page",
                         COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "interface_type": ("analog", 58, "manufacturer_pdf_single_source",
                                COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "stages": ("single", 58, "manufacturer_pdf_inferred",
                       COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
        },
        "7330E336": {
            "function": ("cool_only", 74, "manufacturer_page",
                         COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "interface_type": ("analog", 58, "manufacturer_pdf_single_source",
                                COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
            "stages": ("single", 58, "manufacturer_pdf_inferred",
                       COLEMAN_THIRD_WAVE_RESOLVER_VERSION),
        },
    }
    for model, (_, _, attributes) in third_wave_by_model.items():
        actual = {
            attribute.name: (
                attribute.value_text, attribute.source_observation_id,
                attribute.provenance, attribute.resolver_version)
            for attribute in attributes
        }
        if actual != expected_third_wave[model]:
            failures.append(f"Coleman third-wave attributes mismatch for {model}: {actual}")

    invalid_third_wave_inputs = (
        (changed_row(obs74, lambda e: e["models_named"].remove("7330E336")), obs58),
        (changed_row(obs74, lambda e: e["sku_relationship"].__setitem__(
            "to", "pdf_documents/other.pdf")), obs58),
        (obs74, changed_row(obs58, lambda e: e.__setitem__(
            "family_statement", "no wildcard split stated"))),
        (dict(obs74, id=400), obs58),
        (obs74, dict(obs58, source_type="retailer_pdf")),
    )
    for naming, family in invalid_third_wave_inputs:
        try:
            coleman_third_wave_endpoint_components(naming, family, third_wave_ids)
            failures.append("invalid Coleman third-wave endpoint evidence was accepted")
        except ValueError:
            pass

    store_conn_third_wave = init_db(":memory:")
    for component, identifiers, attributes in third_wave_endpoints:
        insert_component(store_conn_third_wave, component)
        for identifier in identifiers:
            insert_identifier(store_conn_third_wave, identifier)
    insert_component(store_conn_third_wave, Component(
        second_wave_ids["7330F3361"], THERMOSTAT_PART_TYPE, None))
    third_wave_edge_id = resolve_coleman_third_wave_supersession(
        store_conn_third_wave, obs59, obs64,
        third_wave_ids["7330E336"], second_wave_ids["7330F3361"])
    third_wave_edge_confidence = compute_confidence(
        get_evidence_for_edge(store_conn_third_wave, third_wave_edge_id))
    if (third_wave_edge_confidence["value"], third_wave_edge_confidence["certainty"]) != \
            (0.75, 4.0):
        failures.append(
            f"Coleman third-wave supersession confidence mismatch: "
            f"{third_wave_edge_confidence}")

    invalid_third_wave_supersession_inputs = (
        (obs59, dict(obs64, id=400)),
        (obs59, changed_row(obs64, lambda e: e["sku_relationship"].__setitem__(
            "to", "9420-351"))),
        (changed_row(obs59, lambda e: e["replacement_chart"].__setitem__(
            "7330-E336", "8330-3482")), obs64),
        (dict(obs59, source_type="retailer_page"), obs64),
    )
    for retailer, corroboration in invalid_third_wave_supersession_inputs:
        try:
            resolve_coleman_third_wave_supersession(
                init_db(":memory:"), retailer, corroboration,
                third_wave_ids["7330E336"], second_wave_ids["7330F3361"])
            failures.append("invalid Coleman third-wave supersession evidence was accepted")
        except (ValueError, sqlite3.IntegrityError):
            pass

    obs93 = load_observation(obs_db, 93)  # 2025 Airxcel dealer catalog, 9420-352
    store_conn_9420_352 = init_db(":memory:")
    insert_component(store_conn_9420_352, Component(
        second_wave_ids["7330F3361"], THERMOSTAT_PART_TYPE, None))
    component_9420_352, identifiers_9420_352, attrs_9420_352, edge_id_9420_352 = \
        coleman_9420_352_component_and_supersession(
            store_conn_9420_352, obs93, "c_placeholder_tstat_9420_352",
            second_wave_ids["7330F3361"])
    if component_9420_352.part_type_id != 415 or \
            component_9420_352.interchange_code is not None:
        failures.append(f"invalid 9420-352 component: {component_9420_352}")
    if [(i.ns, i.value, i.visibility) for i in identifiers_9420_352] != [
            ("coleman", "9420-352", None)]:
        failures.append(f"invalid 9420-352 identifiers: {identifiers_9420_352}")
    attrs_9420_352_values = {a.name: a.value_text for a in attrs_9420_352}
    if attrs_9420_352_values != {
            "function": "cool_only", "color": "black",
            "interface_type": "analog", "voltage": "12VDC"}:
        failures.append(f"9420-352 attributes mismatch: {attrs_9420_352_values}")
    confidence_9420_352 = compute_confidence(
        get_evidence_for_edge(store_conn_9420_352, edge_id_9420_352))
    if (confidence_9420_352["value"], confidence_9420_352["certainty"]) != (0.75, 4.0):
        failures.append(f"9420-352 supersession confidence mismatch: {confidence_9420_352}")

    invalid_9420_352_inputs = (
        dict(obs93, id=400),
        changed_row(obs93, lambda e: e["sku_relationship"].__setitem__(
            "to", "9420A382")),
        changed_row(obs93, lambda e: e["models"]["9420-352"].__setitem__(
            "color", "white")),
    )
    for invalid in invalid_9420_352_inputs:
        try:
            coleman_9420_352_component_and_supersession(
                init_db(":memory:"), invalid, "c_placeholder_tstat_9420_352_bad",
                second_wave_ids["7330F3361"])
            failures.append("invalid 9420-352 evidence was accepted")
        except (ValueError, sqlite3.IntegrityError):
            pass

    obs94 = load_observation(obs_db, 94)  # 2025 Airxcel dealer catalog, 9420A382
    store_conn_9420a382 = init_db(":memory:")
    insert_component(store_conn_9420a382, Component(
        second_wave_ids["7330F3361"], THERMOSTAT_PART_TYPE, None))
    component_9420a382, identifiers_9420a382, attrs_9420a382, edge_id_9420a382 = \
        coleman_9420a382_component_and_supersession(
            store_conn_9420a382, obs94, "c_placeholder_tstat_9420a382",
            second_wave_ids["7330F3361"])
    if component_9420a382.part_type_id != 415 or \
            component_9420a382.interchange_code is not None:
        failures.append(f"invalid 9420A382 component: {component_9420a382}")
    if [(i.ns, i.value, i.visibility) for i in identifiers_9420a382] != [
            ("coleman", "9420A382", None)]:
        failures.append(f"invalid 9420A382 identifiers: {identifiers_9420a382}")
    attrs_9420a382_scalar = {
        a.name: a.value_text for a in attrs_9420a382 if a.value_text is not None}
    if attrs_9420a382_scalar != {
            "interface_type": "digital", "color": "black", "voltage": "12VDC"}:
        failures.append(f"9420A382 scalar attributes mismatch: {attrs_9420a382_scalar}")
    attrs_9420a382_modes = {
        a.qualifier for a in attrs_9420a382 if a.name == "configurable_mode"}
    if attrs_9420a382_modes != {"cool_only", "heat_pump", "heat_cool"}:
        failures.append(f"9420A382 configurable_mode mismatch: {attrs_9420a382_modes}")
    confidence_9420a382 = compute_confidence(
        get_evidence_for_edge(store_conn_9420a382, edge_id_9420a382))
    if (confidence_9420a382["value"], confidence_9420a382["certainty"]) != (0.75, 4.0):
        failures.append(f"9420A382 supersession confidence mismatch: {confidence_9420a382}")

    invalid_9420a382_inputs = (
        dict(obs94, id=400),
        changed_row(obs94, lambda e: e["sku_relationship"]["groups"][0].__setitem__(
            "from", ["9430-3392", "9430A3392"])),
        changed_row(obs94, lambda e: e["models"]["9420A382"].__setitem__(
            "interface_type", "analog")),
        changed_row(obs94, lambda e: e["sku_relationship"]["groups"].pop()),
    )
    for invalid in invalid_9420a382_inputs:
        try:
            coleman_9420a382_component_and_supersession(
                init_db(":memory:"), invalid, "c_placeholder_tstat_9420a382_bad",
                second_wave_ids["7330F3361"])
            failures.append("invalid 9420A382 evidence was accepted")
        except (ValueError, sqlite3.IntegrityError):
            pass

    obs92 = load_observation(obs_db, 92)  # Atwood RV catalog table
    atwood_endpoint_ids = {
        model: f"c_placeholder_wh_atwood_{model.lower().replace('-', '_')}"
        for model in ATWOOD_ENDPOINT_MODELS
    }
    atwood_endpoints = atwood_endpoint_components(obs92, atwood_endpoint_ids)
    if len(atwood_endpoints) != 19:
        failures.append(f"expected 19 Atwood endpoints, got {len(atwood_endpoints)}")
    atwood_by_model = {
        identifiers[0].value: (component, identifiers, attributes)
        for component, identifiers, attributes in atwood_endpoints
    }
    if set(atwood_by_model) != set(ATWOOD_ENDPOINT_MODELS):
        failures.append(f"Atwood endpoint model set mismatch: {set(atwood_by_model)}")
    for model, (component, identifiers, attributes) in atwood_by_model.items():
        if component.part_type_id != WATER_HEATER_PART_TYPE or \
                component.interchange_code is not None:
            failures.append(f"invalid Atwood endpoint component: {component}")
        if [(i.ns, i.value, i.visibility) for i in identifiers] != [
                ("atwood", model, None)]:
            failures.append(f"invalid Atwood endpoint identifiers for {model}: {identifiers}")
        for attribute in attributes:
            if attribute.provenance != "manufacturer_pdf" or \
                    attribute.source_observation_id != 92 or \
                    attribute.resolver_version != ATWOOD_ENDPOINT_RESOLVER_VERSION:
                failures.append(f"invalid Atwood attribute provenance for {model}: {attribute}")

    spot_check = atwood_by_model["GCH10A-4E"][2]
    spot_check_values = {
        a.name: (a.value_text if a.value_text is not None else
                  a.value_number if a.value_number is not None else a.value_boolean)
        for a in spot_check
    }
    if spot_check_values != {
            "capacity_gal": 10.0, "power_type": "gas_electric",
            "ignition_type": "electronic", "heat_exchanger": True, "exothermal": True,
            "opening_h": 15.625, "opening_w": 16.25}:
        failures.append(f"Atwood GCH10A-4E attributes mismatch: {spot_check_values}")

    invalid_atwood_inputs = (
        changed_row(obs92, lambda e: e["models"].pop("G6A-7")),
        changed_row(obs92, lambda e: e["models"]["GE9-EXT"].__setitem__(
            "power_type", "gas_only")),
        changed_row(obs92, lambda e: e["models"]["GCH6A-10E"].__setitem__(
            "heat_exchanger", False)),
        dict(obs92, id=400),
        dict(obs92, source_type="retailer_pdf"),
    )
    for invalid in invalid_atwood_inputs:
        try:
            atwood_endpoint_components(invalid, atwood_endpoint_ids)
            failures.append("invalid Atwood endpoint evidence was accepted")
        except ValueError:
            pass

    obs95 = load_observation(obs_db, 95)  # Atwood Pilot repair-parts cross-reference
    atwood_parts_host_ids = {
        model: atwood_endpoint_ids[model] for model in ATWOOD_PILOT_PARTS_TARGET_MODELS}
    store_conn_atwood_parts = init_db(":memory:")
    for component, identifiers, attrs in atwood_endpoints:
        if identifiers[0].value in ATWOOD_PILOT_PARTS_TARGET_MODELS:
            insert_component(store_conn_atwood_parts, component)
            for identifier in identifiers:
                insert_identifier(store_conn_atwood_parts, identifier)
    atwood_parts_results = atwood_repair_parts_and_fits(
        store_conn_atwood_parts, obs95, atwood_parts_host_ids)
    if len(atwood_parts_results) != 40:
        failures.append(f"expected 40 Atwood repair parts, got {len(atwood_parts_results)}")
    total_fits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_parts_results)
    if total_fits_edges != 119:
        failures.append(f"expected 119 Atwood fits edges, got {total_fits_edges}")
    for component, identifiers, attrs, edge_ids in atwood_parts_results:
        if component.part_type_id != ATWOOD_PART_TYPE or component.interchange_code is not None:
            failures.append(f"invalid Atwood repair-part component: {component}")
        if identifiers[0].ns != "atwood":
            failures.append(f"invalid Atwood repair-part identifier: {identifiers}")

    invalid_atwood_parts_inputs = (
        dict(obs95, id=400),
        changed_row(obs95, lambda e: e["parts"]["92610"].__setitem__(
            "applies_to", ["G6A-7", "NOT_A_REAL_MODEL"])),
        changed_row(obs95, lambda e: e["parts"]["92610"].__delitem__("description")),
        changed_row(obs95, lambda e: e.__setitem__("parts", {})),
    )
    for invalid in invalid_atwood_parts_inputs:
        try:
            atwood_repair_parts_and_fits(init_db(":memory:"), invalid, atwood_parts_host_ids)
            failures.append("invalid Atwood repair-part evidence was accepted")
        except (ValueError, KeyError, sqlite3.IntegrityError):
            pass

    obs96 = load_observation(obs_db, 96)  # Atwood Electronic repair-parts cross-reference
    atwood_eparts_host_ids = {
        model: atwood_endpoint_ids[model] for model in ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS}
    store_conn_atwood_eparts = init_db(":memory:")
    for component, identifiers, attrs in atwood_endpoints:
        if identifiers[0].value in ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS:
            insert_component(store_conn_atwood_eparts, component)
            for identifier in identifiers:
                insert_identifier(store_conn_atwood_eparts, identifier)
    atwood_eparts_results = atwood_electronic_repair_parts_and_fits(
        store_conn_atwood_eparts, obs96, atwood_eparts_host_ids)
    if len(atwood_eparts_results) != 47:
        failures.append(f"expected 47 Atwood electronic repair parts, got "
                         f"{len(atwood_eparts_results)}")
    total_efits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_eparts_results)
    if total_efits_edges != 248:
        failures.append(f"expected 248 Atwood electronic fits edges, got {total_efits_edges}")
    for component, identifiers, attrs, edge_ids in atwood_eparts_results:
        if component.part_type_id != ATWOOD_PART_TYPE or component.interchange_code is not None:
            failures.append(f"invalid Atwood electronic repair-part component: {component}")
        if identifiers[0].ns != "atwood":
            failures.append(f"invalid Atwood electronic repair-part identifier: {identifiers}")

    invalid_atwood_eparts_inputs = (
        dict(obs96, id=400),
        changed_row(obs96, lambda e: e["parts"]["91470"].__setitem__(
            "applies_to", ["GH6-8E", "NOT_A_REAL_MODEL"])),
        changed_row(obs96, lambda e: e["parts"]["91470"].__delitem__("description")),
        changed_row(obs96, lambda e: e.__setitem__("parts", {})),
    )
    for invalid in invalid_atwood_eparts_inputs:
        try:
            atwood_electronic_repair_parts_and_fits(
                init_db(":memory:"), invalid, atwood_eparts_host_ids)
            failures.append("invalid Atwood electronic repair-part evidence was accepted")
        except (ValueError, KeyError, sqlite3.IntegrityError):
            pass

    # Issue #48: on a shared connection where the Pilot table already built
    # its own atwood/90960 component, the Electronic table's own 90960 row
    # must merge onto it instead of minting a second "_epart_" duplicate.
    store_conn_atwood_pilot_then_eparts = init_db(":memory:")
    for component, identifiers, attrs in atwood_endpoints:
        if identifiers[0].value in ATWOOD_PILOT_PARTS_TARGET_MODELS or \
                identifiers[0].value in ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS:
            insert_component(store_conn_atwood_pilot_then_eparts, component)
            for identifier in identifiers:
                insert_identifier(store_conn_atwood_pilot_then_eparts, identifier)
    atwood_repair_parts_and_fits(
        store_conn_atwood_pilot_then_eparts, obs95, atwood_parts_host_ids)
    pilot_then_eparts_results = atwood_electronic_repair_parts_and_fits(
        store_conn_atwood_pilot_then_eparts, obs96, atwood_eparts_host_ids)
    merged_90960 = next(
        r for r, part_number in zip(
            pilot_then_eparts_results,
            _normalized_attributes(obs96)["repair_part_fitment_table"].keys())
        if part_number == "90960")
    if merged_90960[0].component_id != "c_placeholder_wh_atwood_part_90960":
        failures.append(f"expected Electronic table's 90960 to merge onto the Pilot "
                         f"table's component, got {merged_90960[0].component_id}")
    if merged_90960[1] != []:
        failures.append(f"expected no new identifiers for merged Atwood 90960, "
                         f"got {merged_90960[1]}")
    all_90960_after_merge = store_conn_atwood_pilot_then_eparts.execute(
        "SELECT component_id FROM identifiers WHERE ns='atwood' AND value='90960'").fetchall()
    if len(all_90960_after_merge) != 1:
        failures.append(f"expected 1 component for atwood/90960 after Pilot+Electronic merge, "
                         f"got {len(all_90960_after_merge)}")
    merged_90960_edges = store_conn_atwood_pilot_then_eparts.execute(
        "SELECT COUNT(*) AS n FROM edges WHERE from_component_id=?",
        ("c_placeholder_wh_atwood_part_90960",)).fetchone()
    if merged_90960_edges["n"] != 5 + 8:
        failures.append(f"expected merged Atwood 90960 to carry both tables' fits edges "
                         f"(5 Pilot + 8 Electronic = 13), got {merged_90960_edges['n']}")

    # Issue #48: 93870's canonical component_id is fixed by
    # atwood_gh6_6e_gas_valve_chain() itself (other code hardcodes it), so
    # unlike the Pilot/Electronic merge above, a pre-existing "atwood"/93870
    # component under some OTHER id (as if built by the Electronic table
    # first) must be folded onto the canonical one via merge_component_into()
    # rather than becoming the merge target.
    obs116 = load_observation(obs_db, 116)  # Atwood GH6-6E gas-valve chain
    store_conn_atwood_valve_merge = init_db(":memory:")
    insert_component(store_conn_atwood_valve_merge,
                      Component("c_placeholder_wh_atwood_gh6_6e", ATWOOD_PART_TYPE, None))
    insert_component(store_conn_atwood_valve_merge,
                      Component("c_placeholder_wh_atwood_epart_93870", ATWOOD_PART_TYPE, None))
    insert_identifier(store_conn_atwood_valve_merge,
                       Identifier("c_placeholder_wh_atwood_epart_93870", "atwood", "93870", None))
    insert_component_attribute(store_conn_atwood_valve_merge, ComponentAttribute(
        "c_placeholder_wh_atwood_epart_93870", "description", "manufacturer_pdf", obs96["id"],
        value_text="Flue Box and Gasket -- decoy pre-existing attribute",
        resolver_version=ATWOOD_ELECTRONIC_PARTS_RESOLVER_VERSION))
    decoy_edge = Edge(
        type=EDGE_TYPE_FITS, from_component_id="c_placeholder_wh_atwood_epart_93870",
        to_component_id="c_placeholder_wh_atwood_gh6_6e", group_key="atwood_electronic_repair_part",
        status="candidate", resolver_version=ATWOOD_ELECTRONIC_PARTS_RESOLVER_VERSION,
        notes="decoy pre-existing edge to be migrated onto the canonical component")
    insert_edge(store_conn_atwood_valve_merge, decoy_edge)
    valve_merge_results, _ = atwood_gh6_6e_gas_valve_chain(
        store_conn_atwood_valve_merge, obs116, "c_placeholder_wh_atwood_gh6_6e")
    if any(c.component_id == "c_placeholder_wh_atwood_epart_93870"
           for c, _, _, _ in valve_merge_results):
        failures.append("Atwood gas valve chain should never return the pre-merge duplicate id")
    all_93870_after_valve_merge = store_conn_atwood_valve_merge.execute(
        "SELECT component_id FROM identifiers WHERE ns='atwood' AND value='93870'").fetchall()
    if [r["component_id"] for r in all_93870_after_valve_merge] != [
            "c_placeholder_wh_atwood_part_93870"]:
        failures.append(f"expected atwood/93870 to resolve only to the canonical gas-valve "
                         f"component after merge, got {list(all_93870_after_valve_merge)}")
    if store_conn_atwood_valve_merge.execute(
            "SELECT 1 FROM components WHERE component_id='c_placeholder_wh_atwood_epart_93870'"
            ).fetchone() is not None:
        failures.append("expected pre-existing duplicate atwood/93870 component to be deleted "
                         "after merge_component_into()")
    migrated_edge = store_conn_atwood_valve_merge.execute(
        "SELECT from_component_id FROM edges WHERE id = ?", (decoy_edge.id,)).fetchone()
    if migrated_edge["from_component_id"] != "c_placeholder_wh_atwood_part_93870":
        failures.append(f"expected decoy edge to be migrated onto the canonical component, "
                         f"got {migrated_edge['from_component_id']}")

    obs119 = load_observation(obs_db, 119)  # Atwood XT repair-parts cross-reference
    atwood_extparts_host_ids = {
        model: atwood_endpoint_ids[model] for model in ATWOOD_EXT_PARTS_TARGET_MODELS}
    store_conn_atwood_extparts = init_db(":memory:")
    for component, identifiers, attrs in atwood_endpoints:
        if identifiers[0].value in ATWOOD_EXT_PARTS_TARGET_MODELS:
            insert_component(store_conn_atwood_extparts, component)
            for identifier in identifiers:
                insert_identifier(store_conn_atwood_extparts, identifier)
    atwood_extparts_results = atwood_ext_repair_parts_and_fits(
        store_conn_atwood_extparts, obs119, atwood_extparts_host_ids)
    if len(atwood_extparts_results) != 22:
        failures.append(f"expected 22 Atwood EXT repair parts, got {len(atwood_extparts_results)}")
    total_extfits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_extparts_results)
    if total_extfits_edges != 116:
        failures.append(f"expected 116 Atwood EXT fits edges, got {total_extfits_edges}")
    for component, identifiers, attrs, edge_ids in atwood_extparts_results:
        if component.part_type_id != ATWOOD_PART_TYPE or component.interchange_code is not None:
            failures.append(f"invalid Atwood EXT repair-part component: {component}")
        if identifiers and identifiers[0].ns != "atwood":
            failures.append(f"invalid Atwood EXT repair-part identifier: {identifiers}")

    # Reuse branch (docstring point 3): a pre-existing "atwood"/90960 component
    # (as if built by obs #95's Pilot table first) must be reused, not duplicated.
    store_conn_atwood_extparts_reuse = init_db(":memory:")
    for component, identifiers, attrs in atwood_endpoints:
        if identifiers[0].value in ATWOOD_EXT_PARTS_TARGET_MODELS:
            insert_component(store_conn_atwood_extparts_reuse, component)
            for identifier in identifiers:
                insert_identifier(store_conn_atwood_extparts_reuse, identifier)
    insert_component(store_conn_atwood_extparts_reuse,
                      Component("c_placeholder_wh_atwood_part_90960", ATWOOD_PART_TYPE, None))
    insert_identifier(store_conn_atwood_extparts_reuse,
                       Identifier("c_placeholder_wh_atwood_part_90960", "atwood", "90960", None))
    reuse_results = atwood_ext_repair_parts_and_fits(
        store_conn_atwood_extparts_reuse, obs119, atwood_extparts_host_ids)
    reused = next(r for r in reuse_results
                  if r[0].component_id == "c_placeholder_wh_atwood_part_90960")
    if reused[1] != []:
        failures.append(f"expected no new identifiers for reused Atwood EXT part 90960, "
                         f"got {reused[1]}")
    all_90960_components = store_conn_atwood_extparts_reuse.execute(
        "SELECT component_id FROM identifiers WHERE ns='atwood' AND value='90960'").fetchall()
    if len(all_90960_components) != 1:
        failures.append(f"expected 1 component for atwood/90960 after reuse, "
                         f"got {len(all_90960_components)}")

    invalid_atwood_extparts_inputs = (
        dict(obs119, id=400),
        changed_row(obs119, lambda e: e["parts"]["90960"].__setitem__(
            "applies_to", ["G9-EXT", "NOT_A_REAL_MODEL"])),
        changed_row(obs119, lambda e: e["parts"]["90960"].__delitem__("description")),
        changed_row(obs119, lambda e: e.__setitem__("parts", {})),
    )
    for invalid in invalid_atwood_extparts_inputs:
        try:
            atwood_ext_repair_parts_and_fits(
                init_db(":memory:"), invalid, atwood_extparts_host_ids)
            failures.append("invalid Atwood EXT repair-part evidence was accepted")
        except (ValueError, KeyError, sqlite3.IntegrityError):
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

    label_photo_evidence = identifier_candidate_evidence_from_label_photo(obs104)
    if (label_photo_evidence.event_type, label_photo_evidence.effect_alpha,
            label_photo_evidence.effect_beta,
            label_photo_evidence.source_observation_id) != (
            "teardown_co_occurrence", 3.0, 0.0, 104):
        failures.append(
            f"identifier candidate label-photo evidence mismatch: {label_photo_evidence}")

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
    if tuple(controls_row) != (
            EDGE_TYPE_CONTROLS, "c_placeholder_wh_switch", "c_placeholder_wh_6del"):
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
        type=EDGE_TYPE_SUPERSEDES,
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


def check_fixture(ground_truth_path, obs_db_path, db_path=":memory:"):
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

    conn = init_db(db_path)
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
        obs104 = load_observation(obs_db_path, 104)
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
        label_photo_evidence = identifier_candidate_evidence_from_label_photo(obs104)
        label_photo_evidence.candidate_id = candidate.id
        insert_identifier_equivalence_evidence(conn, label_photo_evidence)
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
            resolved_alpha = sum(e.effect_alpha for e in evidence)
            resolved_beta = sum(e.effect_beta for e in evidence)
            resolved_sources = sorted(e.source_observation_id for e in evidence)
            if (len(evidence) != 2 or resolved_sources != [43, 104] or
                    (resolved_alpha, resolved_beta) != (
                    float(expected_confidence["alpha"]),
                    float(expected_confidence["beta"]))):
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
            f"AND type IN ('{EDGE_TYPE_SUBSTITUTES}', '{EDGE_TYPE_SUPERSEDES}')",
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

    endpoint_component_ids = set(endpoint_ids.values())
    fixture_supersession_rows = [
        edge for edge in edges_doc if edge.get("type") == "supersedes"
        and edge.get("from") in endpoint_component_ids
        and edge.get("to") in endpoint_component_ids
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
        f"SELECT COUNT(*) FROM edges WHERE type = '{EDGE_TYPE_SUPERSEDES}' "
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
        f"SELECT COUNT(*) FROM edges WHERE type = '{EDGE_TYPE_SUBSTITUTES}' "
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

    second_wave_ids = {
        "7330F3361": "c_placeholder_tstat_7330f3361",
        "7330-3861": "c_placeholder_tstat_7330_3861",
        "7330B3441": "c_placeholder_tstat_7330b3441",
    }
    fixture_second_wave_rows = [
        component for component in components_doc
        if component.get("component_id") in set(second_wave_ids.values())
    ]
    fixture_second_wave = {
        component["component_id"]: component for component in fixture_second_wave_rows
    }
    if (len(fixture_second_wave_rows) != 3
            or set(fixture_second_wave) != set(second_wave_ids.values())):
        print(f"MISMATCH Coleman second-wave endpoint fixture set: "
              f"count={len(fixture_second_wave_rows)} ids={set(fixture_second_wave)}")
        mismatches += 1

    obs55 = load_observation(obs_db_path, 55)
    obs56 = load_observation(obs_db_path, 56)
    second_wave_endpoints = coleman_second_wave_endpoint_components(
        obs40, [obs55, obs56], second_wave_ids)
    _validate_coleman_endpoint_results(second_wave_endpoints, second_wave_ids)
    for endpoint, identifiers, attributes in second_wave_endpoints:
        insert_component(conn, endpoint)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    for component_id, fixture_component in fixture_second_wave.items():
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if resolved_component is None:
            print(f"MISMATCH Coleman second-wave endpoint missing: {component_id}")
            mismatches += 1
            continue
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Coleman second-wave endpoint component: "
                  f"resolved={dict(resolved_component)} fixture={fixture_component}")
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
            print(f"MISMATCH Coleman second-wave endpoint identifiers for {component_id}: "
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
            print(f"MISMATCH Coleman second-wave endpoint attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    fixture_second_wave_component_ids = tuple(second_wave_ids.values())
    second_wave_substitutes_placeholders = ", ".join(
        "?" for _ in fixture_second_wave_component_ids)
    second_wave_edges = conn.execute(
        f"SELECT COUNT(*) FROM edges WHERE type IN "
        f"('{EDGE_TYPE_SUBSTITUTES}', '{EDGE_TYPE_SUPERSEDES}') "
        f"AND (from_component_id IN ({second_wave_substitutes_placeholders}) "
        f"OR to_component_id IN ({second_wave_substitutes_placeholders}))",
        (*fixture_second_wave_component_ids,
         *fixture_second_wave_component_ids)).fetchone()[0]
    if second_wave_edges != 0:
        print(f"MISMATCH unsupported Coleman second-wave endpoint edges: {second_wave_edges}")
        mismatches += 1

    third_wave_ids = {
        "7330E335": "c_placeholder_tstat_7330e335",
        "7330E385": "c_placeholder_tstat_7330e385",
        "7330E336": "c_placeholder_tstat_7330e336",
    }
    fixture_third_wave_rows = [
        component for component in components_doc
        if component.get("component_id") in set(third_wave_ids.values())
    ]
    fixture_third_wave = {
        component["component_id"]: component for component in fixture_third_wave_rows
    }
    if (len(fixture_third_wave_rows) != 3
            or set(fixture_third_wave) != set(third_wave_ids.values())):
        print(f"MISMATCH Coleman third-wave endpoint fixture set: "
              f"count={len(fixture_third_wave_rows)} ids={set(fixture_third_wave)}")
        mismatches += 1

    obs58 = load_observation(obs_db_path, 58)
    obs59 = load_observation(obs_db_path, 59)
    obs64 = load_observation(obs_db_path, 64)
    obs74 = load_observation(obs_db_path, 74)
    third_wave_endpoints = coleman_third_wave_endpoint_components(
        obs74, obs58, third_wave_ids)
    _validate_coleman_endpoint_results(third_wave_endpoints, third_wave_ids)
    for endpoint, identifiers, attributes in third_wave_endpoints:
        insert_component(conn, endpoint)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    for component_id, fixture_component in fixture_third_wave.items():
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if resolved_component is None:
            print(f"MISMATCH Coleman third-wave endpoint missing: {component_id}")
            mismatches += 1
            continue
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Coleman third-wave endpoint component: "
                  f"resolved={dict(resolved_component)} fixture={fixture_component}")
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
            print(f"MISMATCH Coleman third-wave endpoint identifiers for {component_id}: "
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
            print(f"MISMATCH Coleman third-wave endpoint attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    third_wave_edge_id = resolve_coleman_third_wave_supersession(
        conn, obs59, obs64, third_wave_ids["7330E336"], second_wave_ids["7330F3361"])
    fixture_third_wave_edge = next(
        (edge for edge in edges_doc if edge.get("type") == "supersedes"
         and edge.get("from") == third_wave_ids["7330E336"]
         and edge.get("to") == second_wave_ids["7330F3361"]), None)
    if fixture_third_wave_edge is None:
        print("MISMATCH ground-truth.yaml has no 7330E336 -> 7330F3361 supersedes edge")
        mismatches += 1
    else:
        resolved_edge_row = conn.execute(
            "SELECT type, status, group_key FROM edges WHERE id = ?",
            (third_wave_edge_id,)).fetchone()
        expected_edge_fields = (
            "supersedes", fixture_third_wave_edge["status"], fixture_third_wave_edge["group"])
        if tuple(resolved_edge_row) != expected_edge_fields:
            print(f"MISMATCH Coleman third-wave supersession fields: "
                  f"resolved={tuple(resolved_edge_row)} fixture={expected_edge_fields}")
            mismatches += 1

        resolved_detail = get_supersession_detail(conn, third_wave_edge_id)
        expected_note = fixture_third_wave_edge["detail"]["note"]
        if resolved_detail is None or resolved_detail.note != expected_note:
            print(f"MISMATCH Coleman third-wave supersession detail: "
                  f"resolved={resolved_detail} fixture={expected_note}")
            mismatches += 1

        resolved_third_wave_evidence = get_evidence_for_edge(conn, third_wave_edge_id)
        resolved_confidence = compute_confidence(resolved_third_wave_evidence)
        expected_confidence = fixture_third_wave_edge["confidence"]
        if resolved_confidence != {
                "alpha": float(expected_confidence["alpha"]),
                "beta": float(expected_confidence["beta"]),
                "value": float(expected_confidence["value"]),
                "certainty": float(expected_confidence["certainty"])}:
            print(f"MISMATCH Coleman third-wave supersession confidence: "
                  f"resolved={resolved_confidence} fixture={expected_confidence}")
            mismatches += 1

    obs93 = load_observation(obs_db_path, 93)
    fixture_9420_352 = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_tstat_9420_352"), None)
    if fixture_9420_352 is None:
        print("MISMATCH ground-truth.yaml is missing c_placeholder_tstat_9420_352")
        mismatches += 1
    else:
        component_9420_352, identifiers_9420_352, attrs_9420_352, edge_id_9420_352 = \
            coleman_9420_352_component_and_supersession(
                conn, obs93, "c_placeholder_tstat_9420_352", second_wave_ids["7330F3361"])

        resolved_9420_352 = conn.execute(
            "SELECT * FROM components WHERE component_id = ?",
            ("c_placeholder_tstat_9420_352",)).fetchone()
        if (resolved_9420_352["part_type_id"], resolved_9420_352["interchange_code"]) != (
                fixture_9420_352["part_type_id"], fixture_9420_352["interchange_code"]):
            print(f"MISMATCH 9420-352 component: resolved={dict(resolved_9420_352)} "
                  f"fixture={fixture_9420_352}")
            mismatches += 1

        resolved_9420_352_ids = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_tstat_9420_352",)).fetchall()
        }
        expected_9420_352_ids = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_9420_352["identifiers"]
        }
        if resolved_9420_352_ids != expected_9420_352_ids:
            print(f"MISMATCH 9420-352 identifiers: resolved={resolved_9420_352_ids} "
                  f"fixture={expected_9420_352_ids}")
            mismatches += 1

        resolved_9420_352_attrs = {a.name: a.value_text for a in attrs_9420_352}
        expected_9420_352_attrs = {
            name: definition["value"]
            for name, definition in fixture_9420_352["attributes"].items()
        }
        if resolved_9420_352_attrs != expected_9420_352_attrs:
            print(f"MISMATCH 9420-352 attributes: resolved={resolved_9420_352_attrs} "
                  f"fixture={expected_9420_352_attrs}")
            mismatches += 1

        fixture_9420_352_edge = next(
            (e for e in edges_doc if e.get("type") == "supersedes"
             and e.get("from") == second_wave_ids["7330F3361"]
             and e.get("to") == "c_placeholder_tstat_9420_352"), None)
        if fixture_9420_352_edge is None:
            print("MISMATCH ground-truth.yaml has no 7330F3361 -> 9420-352 supersedes edge")
            mismatches += 1
        else:
            resolved_9420_352_conf = compute_confidence(
                get_evidence_for_edge(conn, edge_id_9420_352))
            expected_9420_352_conf = fixture_9420_352_edge["confidence"]
            if resolved_9420_352_conf != {
                    "alpha": float(expected_9420_352_conf["alpha"]),
                    "beta": float(expected_9420_352_conf["beta"]),
                    "value": float(expected_9420_352_conf["value"]),
                    "certainty": float(expected_9420_352_conf["certainty"])}:
                print(f"MISMATCH 9420-352 supersession confidence: "
                      f"resolved={resolved_9420_352_conf} fixture={expected_9420_352_conf}")
                mismatches += 1

    obs94 = load_observation(obs_db_path, 94)
    fixture_9420a382 = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_tstat_9420a382"), None)
    if fixture_9420a382 is None:
        print("MISMATCH ground-truth.yaml is missing c_placeholder_tstat_9420a382")
        mismatches += 1
    else:
        component_9420a382, identifiers_9420a382, attrs_9420a382, edge_id_9420a382 = \
            coleman_9420a382_component_and_supersession(
                conn, obs94, "c_placeholder_tstat_9420a382", second_wave_ids["7330F3361"])

        resolved_9420a382 = conn.execute(
            "SELECT * FROM components WHERE component_id = ?",
            ("c_placeholder_tstat_9420a382",)).fetchone()
        if (resolved_9420a382["part_type_id"], resolved_9420a382["interchange_code"]) != (
                fixture_9420a382["part_type_id"], fixture_9420a382["interchange_code"]):
            print(f"MISMATCH 9420A382 component: resolved={dict(resolved_9420a382)} "
                  f"fixture={fixture_9420a382}")
            mismatches += 1

        resolved_9420a382_ids = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_tstat_9420a382",)).fetchall()
        }
        expected_9420a382_ids = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_9420a382["identifiers"]
        }
        if resolved_9420a382_ids != expected_9420a382_ids:
            print(f"MISMATCH 9420A382 identifiers: resolved={resolved_9420a382_ids} "
                  f"fixture={expected_9420a382_ids}")
            mismatches += 1

        resolved_9420a382_attrs = get_component_attributes(conn, "c_placeholder_tstat_9420a382")
        resolved_9420a382_scalar = {
            a.name: a.value_text for a in resolved_9420a382_attrs if a.value_text is not None}
        resolved_9420a382_modes = {
            a.qualifier for a in resolved_9420a382_attrs if a.name == "configurable_mode"}
        expected_9420a382_scalar = {
            name: definition["value"]
            for name, definition in fixture_9420a382["attributes"].items()
            if name != "configurable_modes"
        }
        expected_9420a382_modes = set(
            fixture_9420a382["attributes"]["configurable_modes"]["value"])
        if resolved_9420a382_scalar != expected_9420a382_scalar:
            print(f"MISMATCH 9420A382 scalar attributes: resolved={resolved_9420a382_scalar} "
                  f"fixture={expected_9420a382_scalar}")
            mismatches += 1
        if resolved_9420a382_modes != expected_9420a382_modes:
            print(f"MISMATCH 9420A382 configurable modes: resolved={resolved_9420a382_modes} "
                  f"fixture={expected_9420a382_modes}")
            mismatches += 1

        fixture_9420a382_edge = next(
            (e for e in edges_doc if e.get("type") == "supersedes"
             and e.get("from") == second_wave_ids["7330F3361"]
             and e.get("to") == "c_placeholder_tstat_9420a382"), None)
        if fixture_9420a382_edge is None:
            print("MISMATCH ground-truth.yaml has no 7330F3361 -> 9420A382 supersedes edge")
            mismatches += 1
        else:
            resolved_9420a382_conf = compute_confidence(
                get_evidence_for_edge(conn, edge_id_9420a382))
            expected_9420a382_conf = fixture_9420a382_edge["confidence"]
            if resolved_9420a382_conf != {
                    "alpha": float(expected_9420a382_conf["alpha"]),
                    "beta": float(expected_9420a382_conf["beta"]),
                    "value": float(expected_9420a382_conf["value"]),
                    "certainty": float(expected_9420a382_conf["certainty"])}:
                print(f"MISMATCH 9420A382 supersession confidence: "
                      f"resolved={resolved_9420a382_conf} fixture={expected_9420a382_conf}")
                mismatches += 1

    print(f"Coleman endpoints: {mismatches - coleman_mismatches_before} mismatch(es)")

    atwood_mismatches_before = mismatches
    atwood_endpoint_ids = {
        model: f"c_placeholder_wh_atwood_{model.lower().replace('-', '_')}"
        for model in ATWOOD_ENDPOINT_MODELS
    }
    fixture_atwood_rows = [
        component for component in components_doc
        if component.get("component_id") in set(atwood_endpoint_ids.values())
    ]
    fixture_atwood = {
        component["component_id"]: component for component in fixture_atwood_rows
    }
    if (len(fixture_atwood_rows) != 19
            or set(fixture_atwood) != set(atwood_endpoint_ids.values())):
        print(f"MISMATCH Atwood endpoint fixture set: "
              f"count={len(fixture_atwood_rows)} ids={set(fixture_atwood)}")
        mismatches += 1

    obs92 = load_observation(obs_db_path, 92)
    atwood_endpoints = atwood_endpoint_components(obs92, atwood_endpoint_ids)
    for endpoint, identifiers, attributes in atwood_endpoints:
        insert_component(conn, endpoint)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    for component_id, fixture_component in fixture_atwood.items():
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if resolved_component is None:
            print(f"MISMATCH Atwood endpoint missing: {component_id}")
            mismatches += 1
            continue
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Atwood endpoint component: "
                  f"resolved={dict(resolved_component)} fixture={fixture_component}")
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
            print(f"MISMATCH Atwood endpoint identifiers for {component_id}: "
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
            print(f"MISMATCH Atwood endpoint attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    atwood_parts_fixture = next(
        (d["atwood_pilot_repair_parts_fixture"] for d in docs
         if isinstance(d, dict) and "atwood_pilot_repair_parts_fixture" in d), None)
    if atwood_parts_fixture is None:
        print("MISMATCH ground-truth.yaml is missing atwood_pilot_repair_parts_fixture")
        mismatches += 1
    else:
        obs95 = load_observation(obs_db_path, 95)
        atwood_parts_host_ids = {
            model: atwood_endpoint_ids[model] for model in ATWOOD_PILOT_PARTS_TARGET_MODELS}
        atwood_parts_results = atwood_repair_parts_and_fits(conn, obs95, atwood_parts_host_ids)
        if len(atwood_parts_results) != atwood_parts_fixture["total_parts"]:
            print(f"MISMATCH Atwood repair-part count: resolved={len(atwood_parts_results)} "
                  f"fixture={atwood_parts_fixture['total_parts']}")
            mismatches += 1
        total_fits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_parts_results)
        if total_fits_edges != atwood_parts_fixture["total_fits_edges"]:
            print(f"MISMATCH Atwood fits-edge count: resolved={total_fits_edges} "
                  f"fixture={atwood_parts_fixture['total_fits_edges']}")
            mismatches += 1

        results_by_part = {identifiers[0].value: (component, identifiers, attrs, edge_ids)
                            for component, identifiers, attrs, edge_ids in atwood_parts_results}
        for spot_check in atwood_parts_fixture["spot_checks"]:
            part = spot_check["part"]
            if part not in results_by_part:
                print(f"MISMATCH Atwood repair part {part} missing from resolver output")
                mismatches += 1
                continue
            component, identifiers, attrs, edge_ids = results_by_part[part]
            if attrs[0].value_text != spot_check["description"]:
                print(f"MISMATCH Atwood repair part {part} description: "
                      f"resolved={attrs[0].value_text} fixture={spot_check['description']}")
                mismatches += 1
            resolved_targets = {
                row["to_component_id"] for row in conn.execute(
                    "SELECT to_component_id FROM edges WHERE id IN ({})".format(
                        ",".join("?" for _ in edge_ids)), edge_ids).fetchall()
            }
            expected_targets = {atwood_parts_host_ids[m] for m in spot_check["applies_to"]}
            if resolved_targets != expected_targets:
                print(f"MISMATCH Atwood repair part {part} fits targets: "
                      f"resolved={resolved_targets} fixture={expected_targets}")
                mismatches += 1

    atwood_eparts_fixture = next(
        (d["atwood_electronic_repair_parts_fixture"] for d in docs
         if isinstance(d, dict) and "atwood_electronic_repair_parts_fixture" in d), None)
    if atwood_eparts_fixture is None:
        print("MISMATCH ground-truth.yaml is missing atwood_electronic_repair_parts_fixture")
        mismatches += 1
    else:
        obs96 = load_observation(obs_db_path, 96)
        atwood_eparts_host_ids = {
            model: atwood_endpoint_ids[model] for model in ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS}
        atwood_eparts_results = atwood_electronic_repair_parts_and_fits(
            conn, obs96, atwood_eparts_host_ids)
        if len(atwood_eparts_results) != atwood_eparts_fixture["total_parts"]:
            print(f"MISMATCH Atwood electronic repair-part count: "
                  f"resolved={len(atwood_eparts_results)} "
                  f"fixture={atwood_eparts_fixture['total_parts']}")
            mismatches += 1
        total_efits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_eparts_results)
        if total_efits_edges != atwood_eparts_fixture["total_fits_edges"]:
            print(f"MISMATCH Atwood electronic fits-edge count: resolved={total_efits_edges} "
                  f"fixture={atwood_eparts_fixture['total_fits_edges']}")
            mismatches += 1

        atwood_eparts_numbers = list(
            _normalized_attributes(obs96)["repair_part_fitment_table"].keys())
        eresults_by_part = {
            part_number: (component, identifiers, attrs, edge_ids)
            for part_number, (component, identifiers, attrs, edge_ids)
            in zip(atwood_eparts_numbers, atwood_eparts_results)
        }
        for spot_check in atwood_eparts_fixture["spot_checks"]:
            part = spot_check["part"]
            if part not in eresults_by_part:
                print(f"MISMATCH Atwood electronic repair part {part} missing from "
                      f"resolver output")
                mismatches += 1
                continue
            component, identifiers, attrs, edge_ids = eresults_by_part[part]
            if attrs[0].value_text != spot_check["description"]:
                print(f"MISMATCH Atwood electronic repair part {part} description: "
                      f"resolved={attrs[0].value_text} fixture={spot_check['description']}")
                mismatches += 1
            resolved_targets = {
                row["to_component_id"] for row in conn.execute(
                    "SELECT to_component_id FROM edges WHERE id IN ({})".format(
                        ",".join("?" for _ in edge_ids)), edge_ids).fetchall()
            }
            expected_targets = {atwood_eparts_host_ids[m] for m in spot_check["applies_to"]}
            if resolved_targets != expected_targets:
                print(f"MISMATCH Atwood electronic repair part {part} fits targets: "
                      f"resolved={resolved_targets} fixture={expected_targets}")
                mismatches += 1

    atwood_extparts_fixture = next(
        (d["atwood_ext_repair_parts_fixture"] for d in docs
         if isinstance(d, dict) and "atwood_ext_repair_parts_fixture" in d), None)
    if atwood_extparts_fixture is None:
        print("MISMATCH ground-truth.yaml is missing atwood_ext_repair_parts_fixture")
        mismatches += 1
    else:
        obs119 = load_observation(obs_db_path, 119)
        atwood_extparts_host_ids = {
            model: atwood_endpoint_ids[model] for model in ATWOOD_EXT_PARTS_TARGET_MODELS}
        atwood_extparts_results = atwood_ext_repair_parts_and_fits(
            conn, obs119, atwood_extparts_host_ids)
        if len(atwood_extparts_results) != atwood_extparts_fixture["total_parts"]:
            print(f"MISMATCH Atwood EXT repair-part count: "
                  f"resolved={len(atwood_extparts_results)} "
                  f"fixture={atwood_extparts_fixture['total_parts']}")
            mismatches += 1
        total_extfits_edges = sum(len(edge_ids) for _, _, _, edge_ids in atwood_extparts_results)
        if total_extfits_edges != atwood_extparts_fixture["total_fits_edges"]:
            print(f"MISMATCH Atwood EXT fits-edge count: resolved={total_extfits_edges} "
                  f"fixture={atwood_extparts_fixture['total_fits_edges']}")
            mismatches += 1

        atwood_extparts_numbers = list(
            _normalized_attributes(obs119)["repair_part_fitment_table"].keys())
        extresults_by_part = {
            part_number: (component, identifiers, attrs, edge_ids)
            for part_number, (component, identifiers, attrs, edge_ids)
            in zip(atwood_extparts_numbers, atwood_extparts_results)
        }
        for spot_check in atwood_extparts_fixture["spot_checks"]:
            part = spot_check["part"]
            if part not in extresults_by_part:
                print(f"MISMATCH Atwood EXT repair part {part} missing from resolver output")
                mismatches += 1
                continue
            component, identifiers, attrs, edge_ids = extresults_by_part[part]
            if attrs[0].value_text != spot_check["description"]:
                print(f"MISMATCH Atwood EXT repair part {part} description: "
                      f"resolved={attrs[0].value_text} fixture={spot_check['description']}")
                mismatches += 1
            resolved_targets = {
                row["to_component_id"] for row in conn.execute(
                    "SELECT to_component_id FROM edges WHERE id IN ({})".format(
                        ",".join("?" for _ in edge_ids)), edge_ids).fetchall()
            }
            expected_targets = {atwood_extparts_host_ids[m] for m in spot_check["applies_to"]}
            if resolved_targets != expected_targets:
                print(f"MISMATCH Atwood EXT repair part {part} fits targets: "
                      f"resolved={resolved_targets} fixture={expected_targets}")
                mismatches += 1

    # Non-blocking diagnostic, not a MISMATCH: all three Atwood repair-parts
    # resolvers (Pilot obs #95, Electronic obs #96, EXT obs #119) merge onto
    # an existing `atwood` identifier hit rather than minting a duplicate
    # component, so this should always come back empty (issue #48; formerly
    # a real 17-pair gap between the Pilot and Electronic tables). Left in
    # place as a standing invariant check rather than removed outright.
    duplicate_identifiers = conn.execute(
        "SELECT ns, value, COUNT(DISTINCT component_id) AS n FROM identifiers "
        "GROUP BY ns, value HAVING n > 1").fetchall()
    if duplicate_identifiers:
        print(f"NOTE {len(duplicate_identifiers)} (ns, value) pair(s) resolved to more than "
              f"one component_id (pre-existing Pilot/Electronic overlap, not a new issue): "
              f"{[(r['ns'], r['value']) for r in duplicate_identifiers]}")

    print(f"Atwood endpoints: {mismatches - atwood_mismatches_before} mismatch(es)")

    suburban_furnace_cooktop_mismatches_before = mismatches
    obs97 = load_observation(obs_db_path, 97)
    obs98 = load_observation(obs_db_path, 98)
    obs99 = load_observation(obs_db_path, 99)
    obs100 = load_observation(obs_db_path, 100)
    obs101 = load_observation(obs_db_path, 101)
    obs102 = load_observation(obs_db_path, 102)
    suburban_furnace_cooktop_ids = {
        "furnace": "c_placeholder_furnace_sf30fq",
        "cooktop": "c_placeholder_cooktop_srna3sbbm",
    }
    suburban_furnace_cooktop = suburban_furnace_cooktop_components(
        obs97, obs101, obs100, obs98, obs99, obs102, suburban_furnace_cooktop_ids)
    for component, identifiers, attributes in suburban_furnace_cooktop:
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    for component_id in suburban_furnace_cooktop_ids.values():
        fixture_component = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_component is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Suburban furnace/cooktop component: "
                  f"resolved={dict(resolved_component)} fixture={fixture_component}")
            mismatches += 1

        resolved_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        expected_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_component["identifiers"]
        }
        if resolved_identifiers != expected_identifiers:
            print(f"MISMATCH Suburban furnace/cooktop identifiers for {component_id}: "
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
            print(f"MISMATCH Suburban furnace/cooktop attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    print(f"Suburban furnace/cooktop endpoints: "
          f"{mismatches - suburban_furnace_cooktop_mismatches_before} mismatch(es)")

    obs103 = load_observation(obs_db_path, 103)
    core_module, core_ids, core_attrs, core_edge_ids = suburban_furnace_core_module(
        conn, obs100, obs103, suburban_furnace_cooktop_ids["furnace"])

    fixture_core_module = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_furnace_part_2608a"), None)
    if fixture_core_module is None:
        print("MISMATCH fixture is missing component: c_placeholder_furnace_part_2608a")
        mismatches += 1
    else:
        resolved_core_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_furnace_part_2608a",)).fetchall()
        }
        expected_core_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_core_module["identifiers"]
        }
        if resolved_core_identifiers != expected_core_identifiers:
            print(f"MISMATCH 2608A identifiers: resolved={resolved_core_identifiers} "
                  f"fixture={expected_core_identifiers}")
            mismatches += 1

    fixture_fits_edge = next(
        (e for e in edges_doc if e.get("type") == "fits"
         and e.get("group") == "suburban_furnace_core_module"), None)
    if fixture_fits_edge is None:
        print("MISMATCH ground-truth.yaml has no suburban_furnace_core_module fits edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (core_edge_ids[0],)).fetchone()
        if tuple(edge_row) != (
                "fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
            print(f"MISMATCH 2608A fits edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                  f"{fixture_fits_edge['to']})")
            mismatches += 1
        resolved_value = compute_confidence(get_evidence_for_edge(conn, core_edge_ids[0]))["value"]
        if round(resolved_value, 3) != fixture_fits_edge["confidence"]["value"]:
            print(f"MISMATCH 2608A fits edge confidence: resolved={resolved_value} "
                  f"fixture={fixture_fits_edge['confidence']['value']}")
            mismatches += 1

    print(f"Suburban furnace core module: "
          f"{mismatches - suburban_furnace_cooktop_mismatches_before} "
          f"mismatch(es) (cumulative with furnace/cooktop endpoints above)")

    suburban_cooktop_parts_mismatches_before = mismatches
    suburban_cooktop_parts_fixture = next(
        (d["suburban_srna3sbbm_repair_parts_fixture"] for d in docs
         if isinstance(d, dict) and "suburban_srna3sbbm_repair_parts_fixture" in d), None)
    if suburban_cooktop_parts_fixture is None:
        print("MISMATCH ground-truth.yaml is missing suburban_srna3sbbm_repair_parts_fixture")
        mismatches += 1
    else:
        obs117 = load_observation(obs_db_path, 117)
        suburban_cooktop_parts_results = suburban_srna3sbbm_repair_parts_and_fits(
            conn, obs117, suburban_furnace_cooktop_ids["cooktop"])
        if len(suburban_cooktop_parts_results) != suburban_cooktop_parts_fixture["total_parts"]:
            print(f"MISMATCH Suburban cooktop repair-part count: "
                  f"resolved={len(suburban_cooktop_parts_results)} "
                  f"fixture={suburban_cooktop_parts_fixture['total_parts']}")
            mismatches += 1
        total_fits_edges = sum(len(edge_ids) for _, _, _, edge_ids in suburban_cooktop_parts_results)
        if total_fits_edges != suburban_cooktop_parts_fixture["total_fits_edges"]:
            print(f"MISMATCH Suburban cooktop fits-edge count: resolved={total_fits_edges} "
                  f"fixture={suburban_cooktop_parts_fixture['total_fits_edges']}")
            mismatches += 1

        results_by_part = {identifiers[0].value: (component, identifiers, attrs, edge_ids)
                            for component, identifiers, attrs, edge_ids in suburban_cooktop_parts_results}
        for spot_check in suburban_cooktop_parts_fixture["spot_checks"]:
            part = spot_check["part"]
            if part not in results_by_part:
                print(f"MISMATCH Suburban cooktop repair part {part} missing from resolver output")
                mismatches += 1
                continue
            component, identifiers, attrs, edge_ids = results_by_part[part]
            if attrs[0].value_text != spot_check["description"]:
                print(f"MISMATCH Suburban cooktop repair part {part} description: "
                      f"resolved={attrs[0].value_text} fixture={spot_check['description']}")
                mismatches += 1
            resolved_targets = {
                row["to_component_id"] for row in conn.execute(
                    "SELECT to_component_id FROM edges WHERE id IN ({})".format(
                        ",".join("?" for _ in edge_ids)), edge_ids).fetchall()
            }
            if resolved_targets != {suburban_furnace_cooktop_ids["cooktop"]}:
                print(f"MISMATCH Suburban cooktop repair part {part} fits targets: "
                      f"resolved={resolved_targets} "
                      f"fixture={{suburban_furnace_cooktop_ids['cooktop']}}")
                mismatches += 1

    print(f"Suburban SRNA3SBBM cooktop repair parts: "
          f"{mismatches - suburban_cooktop_parts_mismatches_before} mismatch(es)")

    norcold_mismatches_before = mismatches
    obs105 = load_observation(obs_db_path, 105)
    obs106 = load_observation(obs_db_path, 106)
    obs108 = load_observation(obs_db_path, 108)
    norcold_component_id = "c_placeholder_refrigerator_n811"
    norcold_component, norcold_identifiers, norcold_attributes = norcold_n811_component(
        obs105, obs106, obs108, norcold_component_id)
    insert_component(conn, norcold_component)
    for identifier in norcold_identifiers:
        insert_identifier(conn, identifier)
    for attribute in norcold_attributes:
        insert_component_attribute(conn, attribute)

    fixture_norcold = next(
        (c for c in components_doc if c.get("component_id") == norcold_component_id), None)
    if fixture_norcold is None:
        print(f"MISMATCH fixture is missing component: {norcold_component_id}")
        mismatches += 1
    else:
        resolved_norcold = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (norcold_component_id,)).fetchone()
        if (resolved_norcold["part_type_id"], resolved_norcold["interchange_code"]) != (
                fixture_norcold["part_type_id"], fixture_norcold["interchange_code"]):
            print(f"MISMATCH Norcold component: "
                  f"resolved={dict(resolved_norcold)} fixture={fixture_norcold}")
            mismatches += 1

        resolved_norcold_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (norcold_component_id,)).fetchall()
        }
        expected_norcold_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_norcold["identifiers"]
        }
        if resolved_norcold_identifiers != expected_norcold_identifiers:
            print(f"MISMATCH Norcold identifiers: resolved={resolved_norcold_identifiers} "
                  f"fixture={expected_norcold_identifiers}")
            mismatches += 1

        resolved_norcold_attribute_rows = get_component_attributes(conn, norcold_component_id)
        resolved_norcold_attributes = {}
        for attribute in resolved_norcold_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_norcold_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_norcold_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_norcold["attributes"].items()
        }
        if (len(resolved_norcold_attribute_rows) != len(expected_norcold_attributes)
                or resolved_norcold_attributes != expected_norcold_attributes):
            print(f"MISMATCH Norcold attributes: resolved={resolved_norcold_attributes} "
                  f"fixture={expected_norcold_attributes}")
            mismatches += 1

    print(f"Norcold endpoint: {mismatches - norcold_mismatches_before} mismatch(es)")

    norcold_parts_mismatches_before = mismatches
    obs109 = load_observation(obs_db_path, 109)
    base_board_component, base_board_ids, base_board_attrs, base_board_edge_ids = \
        norcold_base_board_fits(conn, obs109, {"N811": norcold_component_id})
    (optical_old, optical_old_ids, optical_old_attrs), \
        (optical_new, optical_new_ids, optical_new_attrs), optical_edge_id = \
        norcold_optical_control_supersession(conn, obs109)

    for component_id in (
        "c_placeholder_norcold_part_628674",
        "c_placeholder_norcold_part_628979",
        "c_placeholder_norcold_part_637775",
    ):
        fixture_part = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_part is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_part_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        fixture_part_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_part["identifiers"]
        }
        if resolved_part_identifiers != fixture_part_identifiers:
            print(f"MISMATCH Norcold part identifiers for {component_id}: "
                  f"resolved={resolved_part_identifiers} fixture={fixture_part_identifiers}")
            mismatches += 1

    fixture_base_board_edge = next(
        (e for e in edges_doc if e.get("type") == "fits"
         and e.get("group") == "norcold_base_board"), None)
    if fixture_base_board_edge is None:
        print("MISMATCH ground-truth.yaml has no norcold_base_board fits edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (base_board_edge_ids[0],)).fetchone()
        if tuple(edge_row) != (
                "fits", fixture_base_board_edge["from"], fixture_base_board_edge["to"]):
            print(f"MISMATCH 628674 fits edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_base_board_edge['type']}, "
                  f"{fixture_base_board_edge['from']}, {fixture_base_board_edge['to']})")
            mismatches += 1

    fixture_optical_edge = next(
        (e for e in edges_doc if e.get("type") == "supersedes"
         and e.get("group") == "norcold_optical_control_black"), None)
    if fixture_optical_edge is None:
        print("MISMATCH ground-truth.yaml has no norcold_optical_control_black supersedes edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (optical_edge_id,)).fetchone()
        if tuple(edge_row) != (
                "supersedes", fixture_optical_edge["from"], fixture_optical_edge["to"]):
            print(f"MISMATCH optical control supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_optical_edge['type']}, {fixture_optical_edge['from']}, "
                  f"{fixture_optical_edge['to']})")
            mismatches += 1

    obs110 = load_observation(obs_db_path, 110)
    part_630762_id = "c_placeholder_norcold_part_630762"
    part_630762_component, part_630762_identifiers, part_630762_attributes = \
        norcold_630762_component(obs110, part_630762_id)
    insert_component(conn, part_630762_component)
    for identifier in part_630762_identifiers:
        insert_identifier(conn, identifier)
    for attribute in part_630762_attributes:
        insert_component_attribute(conn, attribute)

    fixture_630762 = next(
        (c for c in components_doc if c.get("component_id") == part_630762_id), None)
    if fixture_630762 is None:
        print(f"MISMATCH fixture is missing component: {part_630762_id}")
        mismatches += 1
    else:
        resolved_630762_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (part_630762_id,)).fetchall()
        }
        fixture_630762_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_630762["identifiers"]
        }
        if resolved_630762_identifiers != fixture_630762_identifiers:
            print(f"MISMATCH 630762 identifiers: resolved={resolved_630762_identifiers} "
                  f"fixture={fixture_630762_identifiers}")
            mismatches += 1
        no_edges = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE from_component_id = ? OR to_component_id = ?",
            (part_630762_id, part_630762_id)).fetchone()[0]
        if no_edges:
            print(f"MISMATCH 630762 has {no_edges} edge(s), expected none "
                  f"(fitment/supersession unresolved)")
            mismatches += 1

    obs118 = load_observation(obs_db_path, 118)
    drain_heater_results, drain_heater_supersession_ids = norcold_drain_hose_and_heater_fits(
        conn, obs118, norcold_component_id)

    for component, identifiers, attrs, edge_ids in drain_heater_results:
        component_id = component.component_id
        fixture_part = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_part is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_part_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        fixture_part_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_part["identifiers"]
        }
        if resolved_part_identifiers != fixture_part_identifiers:
            print(f"MISMATCH Norcold drain hose/heater identifiers for {component_id}: "
                  f"resolved={resolved_part_identifiers} fixture={fixture_part_identifiers}")
            mismatches += 1

        fixture_fits_edge = next(
            (e for e in edges_doc if e.get("type") == "fits"
             and e.get("from") == component_id and e.get("to") == norcold_component_id), None)
        if fixture_fits_edge is None:
            print(f"MISMATCH ground-truth.yaml has no fits edge for {component_id}")
            mismatches += 1
        else:
            edge_row = conn.execute(
                "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
                (edge_ids[0],)).fetchone()
            if tuple(edge_row) != ("fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
                print(f"MISMATCH {component_id} fits edge: resolved={tuple(edge_row)} "
                      f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                      f"{fixture_fits_edge['to']})")
                mismatches += 1

    for old_part, new_part in (("622391", "639101"), ("630811", "638374")):
        old_id = f"c_placeholder_norcold_part_{old_part}"
        new_id = f"c_placeholder_norcold_part_{new_part}"
        fixture_supersedes_edge = next(
            (e for e in edges_doc if e.get("type") == "supersedes"
             and e.get("from") == old_id and e.get("to") == new_id), None)
        if fixture_supersedes_edge is None:
            print(f"MISMATCH ground-truth.yaml has no {old_part}->{new_part} supersedes edge")
            mismatches += 1
            continue
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (drain_heater_supersession_ids[(old_part, new_part)],)).fetchone()
        if tuple(edge_row) != (
                "supersedes", fixture_supersedes_edge["from"], fixture_supersedes_edge["to"]):
            print(f"MISMATCH {old_part}->{new_part} supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_supersedes_edge['type']}, "
                  f"{fixture_supersedes_edge['from']}, {fixture_supersedes_edge['to']})")
            mismatches += 1

    print(f"Norcold repair parts: "
          f"{mismatches - norcold_parts_mismatches_before} mismatch(es)")

    coleman_ac_mismatches_before = mismatches
    obs113 = load_observation(obs_db_path, 113)
    coleman_ac_component_id = "c_placeholder_coleman_ac_48253b866"
    coleman_ac_component, coleman_ac_identifiers, coleman_ac_attributes = \
        coleman_ac_48253b866_component(obs113, coleman_ac_component_id)
    insert_component(conn, coleman_ac_component)
    for identifier in coleman_ac_identifiers:
        insert_identifier(conn, identifier)
    for attribute in coleman_ac_attributes:
        insert_component_attribute(conn, attribute)

    fixture_coleman_ac = next(
        (c for c in components_doc if c.get("component_id") == coleman_ac_component_id), None)
    if fixture_coleman_ac is None:
        print(f"MISMATCH fixture is missing component: {coleman_ac_component_id}")
        mismatches += 1
    else:
        resolved_coleman_ac_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (coleman_ac_component_id,)).fetchall()
        }
        expected_coleman_ac_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_coleman_ac["identifiers"]
        }
        if resolved_coleman_ac_identifiers != expected_coleman_ac_identifiers:
            print(f"MISMATCH Coleman AC identifiers: resolved={resolved_coleman_ac_identifiers} "
                  f"fixture={expected_coleman_ac_identifiers}")
            mismatches += 1

        resolved_coleman_ac_attribute_rows = get_component_attributes(conn, coleman_ac_component_id)
        resolved_coleman_ac_attributes = {}
        for attribute in resolved_coleman_ac_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_coleman_ac_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_coleman_ac_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_coleman_ac["attributes"].items()
        }
        if (len(resolved_coleman_ac_attribute_rows) != len(expected_coleman_ac_attributes)
                or resolved_coleman_ac_attributes != expected_coleman_ac_attributes):
            print(f"MISMATCH Coleman AC attributes: resolved={resolved_coleman_ac_attributes} "
                  f"fixture={expected_coleman_ac_attributes}")
            mismatches += 1

    print(f"Coleman AC endpoint: {mismatches - coleman_ac_mismatches_before} mismatch(es)")

    coleman_ac_parts_mismatches_before = mismatches
    obs114 = load_observation(obs_db_path, 114)
    coleman_ac_parts_results, coleman_ac_motor_supersession_edge_id = \
        coleman_ac_repair_parts_and_fits(conn, obs114, coleman_ac_component_id)

    for component, identifiers, attributes, edge_ids in coleman_ac_parts_results:
        component_id = component.component_id
        fixture_part = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_part is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_part_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        fixture_part_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_part["identifiers"]
        }
        if resolved_part_identifiers != fixture_part_identifiers:
            print(f"MISMATCH Coleman AC part identifiers for {component_id}: "
                  f"resolved={resolved_part_identifiers} fixture={fixture_part_identifiers}")
            mismatches += 1

        fixture_fits_edge = next(
            (e for e in edges_doc if e.get("type") == "fits"
             and e.get("from") == component_id and e.get("to") == coleman_ac_component_id), None)
        if fixture_fits_edge is None:
            print(f"MISMATCH ground-truth.yaml has no fits edge for {component_id}")
            mismatches += 1
        else:
            edge_row = conn.execute(
                "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
                (edge_ids[0],)).fetchone()
            if tuple(edge_row) != ("fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
                print(f"MISMATCH {component_id} fits edge: resolved={tuple(edge_row)} "
                      f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                      f"{fixture_fits_edge['to']})")
                mismatches += 1

    fixture_motor_supersession_edge = next(
        (e for e in edges_doc if e.get("type") == "supersedes"
         and e.get("group") == "coleman_ac_48253b866_fan_motor"), None)
    if fixture_motor_supersession_edge is None:
        print("MISMATCH ground-truth.yaml has no coleman_ac_48253b866_fan_motor supersedes edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (coleman_ac_motor_supersession_edge_id,)).fetchone()
        if tuple(edge_row) != ("supersedes", fixture_motor_supersession_edge["from"],
                                fixture_motor_supersession_edge["to"]):
            print(f"MISMATCH Coleman AC fan motor supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_motor_supersession_edge['type']}, "
                  f"{fixture_motor_supersession_edge['from']}, "
                  f"{fixture_motor_supersession_edge['to']})")
            mismatches += 1

    print(f"Coleman AC repair parts: "
          f"{mismatches - coleman_ac_parts_mismatches_before} mismatch(es)")

    coleman_ac_compressor_mismatches_before = mismatches
    obs126 = load_observation(obs_db_path, 126)
    (coleman_ac_compressor_component, coleman_ac_compressor_identifiers,
     coleman_ac_compressor_attributes, coleman_ac_compressor_fits_edge_ids), \
        coleman_ac_compressor_supersession_edge_id = coleman_ac_compressor_supersession(
            conn, obs114, obs126, coleman_ac_component_id)

    compressor_component_id = coleman_ac_compressor_component.component_id
    fixture_compressor_part = next(
        (c for c in components_doc if c.get("component_id") == compressor_component_id), None)
    if fixture_compressor_part is None:
        print(f"MISMATCH fixture is missing component: {compressor_component_id}")
        mismatches += 1
    else:
        resolved_compressor_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (compressor_component_id,)).fetchall()
        }
        fixture_compressor_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_compressor_part["identifiers"]
        }
        if resolved_compressor_identifiers != fixture_compressor_identifiers:
            print(f"MISMATCH Coleman AC compressor identifiers: "
                  f"resolved={resolved_compressor_identifiers} "
                  f"fixture={fixture_compressor_identifiers}")
            mismatches += 1

        fixture_compressor_fits_edge = next(
            (e for e in edges_doc if e.get("type") == "fits"
             and e.get("from") == compressor_component_id
             and e.get("to") == coleman_ac_component_id), None)
        if fixture_compressor_fits_edge is None:
            print(f"MISMATCH ground-truth.yaml has no fits edge for {compressor_component_id}")
            mismatches += 1
        else:
            edge_row = conn.execute(
                "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
                (coleman_ac_compressor_fits_edge_ids[0],)).fetchone()
            if tuple(edge_row) != ("fits", fixture_compressor_fits_edge["from"],
                                    fixture_compressor_fits_edge["to"]):
                print(f"MISMATCH {compressor_component_id} fits edge: resolved={tuple(edge_row)} "
                      f"fixture=({fixture_compressor_fits_edge['type']}, "
                      f"{fixture_compressor_fits_edge['from']}, {fixture_compressor_fits_edge['to']})")
                mismatches += 1

    fixture_compressor_supersession_edge = next(
        (e for e in edges_doc if e.get("type") == "supersedes"
         and e.get("group") == "coleman_ac_48253b866_compressor"), None)
    if fixture_compressor_supersession_edge is None:
        print("MISMATCH ground-truth.yaml has no coleman_ac_48253b866_compressor supersedes edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (coleman_ac_compressor_supersession_edge_id,)).fetchone()
        if tuple(edge_row) != ("supersedes", fixture_compressor_supersession_edge["from"],
                                fixture_compressor_supersession_edge["to"]):
            print(f"MISMATCH Coleman AC compressor supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_compressor_supersession_edge['type']}, "
                  f"{fixture_compressor_supersession_edge['from']}, "
                  f"{fixture_compressor_supersession_edge['to']})")
            mismatches += 1

    print(f"Coleman AC compressor supersession: "
          f"{mismatches - coleman_ac_compressor_mismatches_before} mismatch(es)")

    coleman_plenum_mismatches_before = mismatches
    obs122 = load_observation(obs_db_path, 122)
    obs124 = load_observation(obs_db_path, 124)
    coleman_plenum_component_id = "c_placeholder_coleman_plenum_8330a733"
    coleman_plenum_component, coleman_plenum_identifiers, coleman_plenum_attributes = \
        coleman_plenum_8330a733_component(obs122, obs124, coleman_plenum_component_id)
    insert_component(conn, coleman_plenum_component)
    for identifier in coleman_plenum_identifiers:
        insert_identifier(conn, identifier)
    for attribute in coleman_plenum_attributes:
        insert_component_attribute(conn, attribute)

    fixture_coleman_plenum = next(
        (c for c in components_doc if c.get("component_id") == coleman_plenum_component_id), None)
    if fixture_coleman_plenum is None:
        print(f"MISMATCH fixture is missing component: {coleman_plenum_component_id}")
        mismatches += 1
    else:
        resolved_coleman_plenum_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (coleman_plenum_component_id,)).fetchall()
        }
        expected_coleman_plenum_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_coleman_plenum["identifiers"]
        }
        if resolved_coleman_plenum_identifiers != expected_coleman_plenum_identifiers:
            print(f"MISMATCH Coleman plenum identifiers: "
                  f"resolved={resolved_coleman_plenum_identifiers} "
                  f"fixture={expected_coleman_plenum_identifiers}")
            mismatches += 1

        resolved_coleman_plenum_attribute_rows = get_component_attributes(
            conn, coleman_plenum_component_id)
        resolved_coleman_plenum_attributes = {}
        for attribute in resolved_coleman_plenum_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_coleman_plenum_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_coleman_plenum_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_coleman_plenum["attributes"].items()
        }
        if (len(resolved_coleman_plenum_attribute_rows) != len(expected_coleman_plenum_attributes)
                or resolved_coleman_plenum_attributes != expected_coleman_plenum_attributes):
            print(f"MISMATCH Coleman plenum attributes: "
                  f"resolved={resolved_coleman_plenum_attributes} "
                  f"fixture={expected_coleman_plenum_attributes}")
            mismatches += 1

    print(f"Coleman plenum endpoint: {mismatches - coleman_plenum_mismatches_before} mismatch(es)")

    coleman_plenum_parts_mismatches_before = mismatches
    obs125 = load_observation(obs_db_path, 125)
    coleman_plenum_parts_results = coleman_plenum_repair_parts_and_fits(
        conn, obs125, coleman_plenum_component_id)

    for component, identifiers, attributes, edge_ids in coleman_plenum_parts_results:
        component_id = component.component_id
        fixture_part = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_part is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_part_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        fixture_part_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_part["identifiers"]
        }
        if resolved_part_identifiers != fixture_part_identifiers:
            print(f"MISMATCH Coleman plenum part identifiers for {component_id}: "
                  f"resolved={resolved_part_identifiers} fixture={fixture_part_identifiers}")
            mismatches += 1

        fixture_fits_edge = next(
            (e for e in edges_doc if e.get("type") == "fits"
             and e.get("from") == component_id and e.get("to") == coleman_plenum_component_id), None)
        if fixture_fits_edge is None:
            print(f"MISMATCH ground-truth.yaml has no fits edge for {component_id}")
            mismatches += 1
        else:
            edge_row = conn.execute(
                "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
                (edge_ids[0],)).fetchone()
            if tuple(edge_row) != ("fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
                print(f"MISMATCH {component_id} fits edge: resolved={tuple(edge_row)} "
                      f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                      f"{fixture_fits_edge['to']})")
                mismatches += 1

    print(f"Coleman plenum repair parts: "
          f"{mismatches - coleman_plenum_parts_mismatches_before} mismatch(es)")

    atwood_gh6_6e_mismatches_before = mismatches
    obs111 = load_observation(obs_db_path, 111)
    gh6_6e_component_id = "c_placeholder_wh_atwood_gh6_6e"
    gh6_6e_component, gh6_6e_identifiers, gh6_6e_attributes = atwood_gh6_6e_component(
        obs111, gh6_6e_component_id)
    insert_component(conn, gh6_6e_component)
    for identifier in gh6_6e_identifiers:
        insert_identifier(conn, identifier)
    for attribute in gh6_6e_attributes:
        insert_component_attribute(conn, attribute)

    fixture_gh6_6e = next(
        (c for c in components_doc if c.get("component_id") == gh6_6e_component_id), None)
    if fixture_gh6_6e is None:
        print(f"MISMATCH fixture is missing component: {gh6_6e_component_id}")
        mismatches += 1
    else:
        resolved_gh6_6e = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (gh6_6e_component_id,)).fetchone()
        if (resolved_gh6_6e["part_type_id"], resolved_gh6_6e["interchange_code"]) != (
                fixture_gh6_6e["part_type_id"], fixture_gh6_6e["interchange_code"]):
            print(f"MISMATCH GH6-6E component: "
                  f"resolved={dict(resolved_gh6_6e)} fixture={fixture_gh6_6e}")
            mismatches += 1

        resolved_gh6_6e_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (gh6_6e_component_id,)).fetchall()
        }
        expected_gh6_6e_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_gh6_6e["identifiers"]
        }
        if resolved_gh6_6e_identifiers != expected_gh6_6e_identifiers:
            print(f"MISMATCH GH6-6E identifiers: resolved={resolved_gh6_6e_identifiers} "
                  f"fixture={expected_gh6_6e_identifiers}")
            mismatches += 1

        resolved_gh6_6e_attribute_rows = get_component_attributes(conn, gh6_6e_component_id)
        resolved_gh6_6e_attributes = {}
        for attribute in resolved_gh6_6e_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_gh6_6e_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_gh6_6e_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_gh6_6e["attributes"].items()
        }
        if (len(resolved_gh6_6e_attribute_rows) != len(expected_gh6_6e_attributes)
                or resolved_gh6_6e_attributes != expected_gh6_6e_attributes):
            print(f"MISMATCH GH6-6E attributes: resolved={resolved_gh6_6e_attributes} "
                  f"fixture={expected_gh6_6e_attributes}")
            mismatches += 1

    obs112 = load_observation(obs_db_path, 112)
    tank_91642_component, tank_91642_identifiers, tank_91642_attrs, tank_91642_edge_ids = \
        atwood_gh6_6e_tank_91642_fits(conn, obs112, gh6_6e_component_id)

    fixture_91642 = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_wh_atwood_part_91642"), None)
    if fixture_91642 is None:
        print("MISMATCH fixture is missing component: c_placeholder_wh_atwood_part_91642")
        mismatches += 1
    else:
        resolved_91642_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_wh_atwood_part_91642",)).fetchall()
        }
        fixture_91642_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_91642["identifiers"]
        }
        if resolved_91642_identifiers != fixture_91642_identifiers:
            print(f"MISMATCH 91642 identifiers: resolved={resolved_91642_identifiers} "
                  f"fixture={fixture_91642_identifiers}")
            mismatches += 1

    fixture_91642_edge = next(
        (e for e in edges_doc if e.get("type") == "fits"
         and e.get("group") == "atwood_gh6_6e_tank"), None)
    if fixture_91642_edge is None:
        print("MISMATCH ground-truth.yaml has no atwood_gh6_6e_tank fits edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (tank_91642_edge_ids[0],)).fetchone()
        if tuple(edge_row) != (
                "fits", fixture_91642_edge["from"], fixture_91642_edge["to"]):
            print(f"MISMATCH 91642 fits edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_91642_edge['type']}, "
                  f"{fixture_91642_edge['from']}, {fixture_91642_edge['to']})")
            mismatches += 1

    print(f"Atwood GH6-6E teardown anchor: "
          f"{mismatches - atwood_gh6_6e_mismatches_before} mismatch(es)")

    atwood_gh6_6e_valve_mismatches_before = mismatches
    obs116 = load_observation(obs_db_path, 116)
    valve_results, valve_supersession_edge_id = atwood_gh6_6e_gas_valve_chain(
        conn, obs116, gh6_6e_component_id)

    for component, identifiers, attributes, edge_ids in valve_results:
        component_id = component.component_id
        fixture_part = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_part is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_part_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        fixture_part_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_part["identifiers"]
        }
        if resolved_part_identifiers != fixture_part_identifiers:
            print(f"MISMATCH gas valve identifiers for {component_id}: "
                  f"resolved={resolved_part_identifiers} fixture={fixture_part_identifiers}")
            mismatches += 1

        fixture_fits_edge = next(
            (e for e in edges_doc if e.get("type") == "fits"
             and e.get("from") == component_id and e.get("to") == gh6_6e_component_id), None)
        if fixture_fits_edge is None:
            print(f"MISMATCH ground-truth.yaml has no fits edge for {component_id}")
            mismatches += 1
        else:
            edge_row = conn.execute(
                "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
                (edge_ids[0],)).fetchone()
            if tuple(edge_row) != ("fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
                print(f"MISMATCH {component_id} fits edge: resolved={tuple(edge_row)} "
                      f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                      f"{fixture_fits_edge['to']})")
                mismatches += 1

    fixture_valve_supersession_edge = next(
        (e for e in edges_doc if e.get("type") == "supersedes"
         and e.get("from") == "c_placeholder_wh_atwood_part_93870"
         and e.get("to") == "c_placeholder_wh_atwood_part_93844"), None)
    if fixture_valve_supersession_edge is None:
        print("MISMATCH ground-truth.yaml has no 93870->93844 supersedes edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (valve_supersession_edge_id,)).fetchone()
        if tuple(edge_row) != ("supersedes", fixture_valve_supersession_edge["from"],
                                fixture_valve_supersession_edge["to"]):
            print(f"MISMATCH 93870->93844 supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_valve_supersession_edge['type']}, "
                  f"{fixture_valve_supersession_edge['from']}, "
                  f"{fixture_valve_supersession_edge['to']})")
            mismatches += 1

    print(f"Atwood GH6-6E gas valve chain (93870->93844): "
          f"{mismatches - atwood_gh6_6e_valve_mismatches_before} mismatch(es)")

    atwood_91605_mismatches_before = mismatches
    obs115 = load_observation(obs_db_path, 115)
    (component_91605, identifiers_91605, attributes_91605), edge_91605_id = \
        atwood_91605_93870_supersession(conn, obs115)

    fixture_91605 = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_wh_atwood_part_91605"), None)
    if fixture_91605 is None:
        print("MISMATCH fixture is missing component: c_placeholder_wh_atwood_part_91605")
        mismatches += 1
    else:
        resolved_91605_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_wh_atwood_part_91605",)).fetchall()
        }
        fixture_91605_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_91605["identifiers"]
        }
        if resolved_91605_identifiers != fixture_91605_identifiers:
            print(f"MISMATCH 91605 identifiers: resolved={resolved_91605_identifiers} "
                  f"fixture={fixture_91605_identifiers}")
            mismatches += 1

    fixture_91605_edge = next(
        (e for e in edges_doc if e.get("type") == "supersedes"
         and e.get("from") == "c_placeholder_wh_atwood_part_91605"
         and e.get("to") == "c_placeholder_wh_atwood_part_93870"), None)
    if fixture_91605_edge is None:
        print("MISMATCH ground-truth.yaml has no 91605->93870 supersedes edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (edge_91605_id,)).fetchone()
        if tuple(edge_row) != ("supersedes", fixture_91605_edge["from"], fixture_91605_edge["to"]):
            print(f"MISMATCH 91605->93870 supersedes edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_91605_edge['type']}, {fixture_91605_edge['from']}, "
                  f"{fixture_91605_edge['to']})")
            mismatches += 1

    print(f"Atwood 91605->93870 supersession: "
          f"{mismatches - atwood_91605_mismatches_before} mismatch(es)")

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
    if "--build" in sys.argv:
        idx = sys.argv.index("--build")
        fixture_path = sys.argv[idx + 1]
        db_path = sys.argv[idx + 2]
        sys.exit(build_database(fixture_path, db_path))


def build_database(fixture_path, db_path):
    """
    Rebuild the persistent components/edges store into a temporary database
    first, then atomically replace the published file only after validation
    succeeds. This keeps the last known-good database intact if validation
    fails or raises.
    """
    db_path = Path(db_path)
    obs_db = str(Path(__file__).parent / "observations.db")
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f"{db_path.name}.tmp.",
        dir=str(db_path.parent),
    )
    os.close(temp_fd)
    temp_db_path = Path(temp_name)
    try:
        result = check_fixture(fixture_path, obs_db, db_path=str(temp_db_path))
        if result == 0:
            os.replace(temp_db_path, db_path)
        return result
    finally:
        if temp_db_path.exists():
            temp_db_path.unlink()


if __name__ == "__main__":
    main()
