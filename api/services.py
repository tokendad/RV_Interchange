"""
api/services.py — Service Layer over the Docs/Tools interchange store, per
Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md §7.

Docs/Tools is not an installable package, so callers of this module must
insert it onto sys.path before importing this file (api/main.py does this
at process start; tests do it per-file — see tests/api/test_services.py).
"""

from interchange_store import get_component_by_identifier, get_identifiers_for_component


class IdentifierService:
    @staticmethod
    def resolve(conn, ns, value):
        component = get_component_by_identifier(conn, ns, value)
        if component is None:
            return None
        identifiers = get_identifiers_for_component(conn, component.component_id)
        return {
            "component_id": component.component_id,
            "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
        }


from interchange_store import (
    get_component, get_edges_from, get_evidence_for_edge, get_caveats_for_edge,
)
from interchange_models import compute_confidence


def _label_for(conn, component_id):
    identifiers = get_identifiers_for_component(conn, component_id)
    return identifiers[0].value if identifiers else component_id


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
    def get_replacements(conn, component_id):
        component = get_component(conn, component_id)
        if component is None:
            return None

        source_label = _label_for(conn, component_id)
        replacements = [
            {"part": source_label, "fit": "Exact Match", "rank": 1, "summary": None},
        ]

        rank = 2
        for edge in get_edges_from(conn, component_id, type="substitutes"):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            summary = "; ".join(c.text for c in caveats) if caveats else None
            replacements.append({
                "part": _label_for(conn, edge["to_component_id"]),
                "fit": fit,
                "rank": rank,
                "summary": summary,
            })
            rank += 1

        return {"source": source_label, "replacements": replacements}
