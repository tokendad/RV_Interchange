"""
api/services.py — Service Layer over the Docs/Tools interchange store, per
Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md §7.

Docs/Tools is not an installable package, so callers of this module must
insert it onto sys.path before importing this file (api/main.py does this
at process start; tests do it per-file — see tests/api/test_services.py).
"""

from interchange_store import (
    get_component, get_component_attributes, get_component_by_identifier,
    get_edges_from, get_caveats_for_edge, get_evidence_for_edge,
    get_identifiers_for_component, get_required_parts_for_edge,
    get_supersession_detail, search_identifiers,
)
from interchange_models import compute_confidence
from edge_types import EDGE_TYPE_SUBSTITUTES, EDGE_TYPE_SUPERSEDES
from manufacturers import MANUFACTURER_NAMES
from part_types import PART_TYPE_NAMES


def _attribute_value(attribute):
    if attribute.value_text is not None:
        return attribute.value_text
    if attribute.value_number is not None:
        return attribute.value_number
    return attribute.value_boolean


def _format_attributes(conn, component_id):
    return [
        {
            "name": attribute.name,
            "qualifier": attribute.qualifier,
            "value": _attribute_value(attribute),
            "unit": attribute.unit,
        }
        for attribute in get_component_attributes(conn, component_id)
    ]


def _ns_for_label(identifiers, label):
    for identifier in identifiers:
        if identifier.value == label:
            return identifier.ns
    return identifiers[0].ns if identifiers else None


class IdentifierService:
    @staticmethod
    def resolve(conn, ns, value):
        component = get_component_by_identifier(conn, ns, value)
        if component is None:
            return None
        identifiers = get_identifiers_for_component(conn, component.component_id)
        return {
            "component_id": component.component_id,
            "manufacturer": MANUFACTURER_NAMES.get(ns),
            "part_type": PART_TYPE_NAMES.get(component.part_type_id),
            "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
            "attributes": _format_attributes(conn, component.component_id),
        }


class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        matches = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id, matched_value in matches:
            identifiers = get_identifiers_for_component(conn, component_id)
            component = get_component(conn, component_id)
            matched_ns = _ns_for_label(identifiers, matched_value)
            results.append({
                "component_id": component_id,
                "label": matched_value,
                "manufacturer": MANUFACTURER_NAMES.get(matched_ns),
                "part_type": PART_TYPE_NAMES.get(component.part_type_id) if component else None,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
                "attributes": _format_attributes(conn, component_id),
            })
        return {"query": query, "results": results}


def _label_for(conn, component_id, ns=None):
    identifiers = get_identifiers_for_component(conn, component_id)
    if not identifiers:
        return component_id
    if ns is not None:
        for identifier in identifiers:
            if identifier.ns == ns:
                return identifier.value
    return identifiers[0].value


def _format_required_parts(conn, edge_id):
    return [
        {
            "ns": part.ns,
            "value": part.value,
            "role": part.role,
            "manufacturer": MANUFACTURER_NAMES.get(part.ns),
        }
        for part in get_required_parts_for_edge(conn, edge_id)
    ]


def _format_caveats(caveats):
    return [{"text": c.text, "blocking": c.blocking} for c in caveats]


def _tier_for_confidence(confidence):
    if confidence["value"] is None:
        return None
    if confidence["certainty"] >= 8 and confidence["value"] > 0.90:
        return "Direct Fit"
    if confidence["value"] > 0.70:
        return "Fits With Modification"
    return None


class ReplacementService:
    @staticmethod
    def get_replacements(conn, component_id, ns=None):
        component = get_component(conn, component_id)
        if component is None:
            return None

        source_label = _label_for(conn, component_id, ns)
        replacements = [
            {"part": source_label, "fit": "Exact Match", "rank": 1,
             "required_parts": [], "caveats": []},
        ]

        _TIER_PRIORITY = {"Direct Fit": 0, "Fits With Modification": 1}

        candidates = []
        for edge in get_edges_from(conn, component_id, type=EDGE_TYPE_SUBSTITUTES):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            candidates.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "fit": fit,
                "required_parts": _format_required_parts(conn, edge["id"]),
                "caveats": _format_caveats(caveats),
                "_confidence_value": confidence["value"],
            })

        candidates.sort(
            key=lambda c: (_TIER_PRIORITY[c["fit"]], -c["_confidence_value"])
        )

        rank = 2
        for candidate in candidates:
            del candidate["_confidence_value"]
            candidate["rank"] = rank
            replacements.append(candidate)
            rank += 1

        supersessions = []
        for edge in get_edges_from(conn, component_id, type=EDGE_TYPE_SUPERSEDES):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            if confidence["value"] is None:
                continue
            detail = get_supersession_detail(conn, edge["id"])
            supersessions.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "note": detail.note if detail else None,
            })

        return {
            "source": source_label,
            "replacements": replacements,
            "supersessions": supersessions,
        }
