"""
api/services.py — Service Layer over the Docs/Tools interchange store, per
Docs/Inital_Design/Stage 2 (Frontend)/RV_Interchange_API_Design.md §7.

Docs/Tools is not an installable package, so callers of this module must
insert it onto sys.path before importing this file (api/main.py does this
at process start; tests do it per-file — see tests/api/test_services.py).
"""

from interchange_store import (
    get_component, get_component_by_identifier, get_edges_from,
    get_caveats_for_edge, get_evidence_for_edge, get_identifiers_for_component,
    get_supersession_detail, search_identifiers,
)
from interchange_models import compute_confidence


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


class SearchService:
    @staticmethod
    def search(conn, query, limit=20):
        matches = search_identifiers(conn, query, limit=limit)
        results = []
        for component_id, matched_value in matches:
            identifiers = get_identifiers_for_component(conn, component_id)
            results.append({
                "component_id": component_id,
                "label": matched_value,
                "identifiers": [{"ns": i.ns, "value": i.value} for i in identifiers],
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
            {"part": source_label, "fit": "Exact Match", "rank": 1, "summary": None},
        ]

        _TIER_PRIORITY = {"Direct Fit": 0, "Fits With Modification": 1}

        candidates = []
        for edge in get_edges_from(conn, component_id, type="substitutes"):
            evidence = get_evidence_for_edge(conn, edge["id"])
            confidence = compute_confidence(evidence)
            fit = _tier_for_confidence(confidence)
            if fit is None:
                continue
            caveats = get_caveats_for_edge(conn, edge["id"])
            summary = "; ".join(c.text for c in caveats) if caveats else None
            candidates.append({
                "part": _label_for(conn, edge["to_component_id"], ns),
                "fit": fit,
                "summary": summary,
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
        for edge in get_edges_from(conn, component_id, type="supersedes"):
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
