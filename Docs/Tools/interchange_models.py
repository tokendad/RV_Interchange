#!/usr/bin/env python3
"""
interchange_models.py — dataclasses mirroring interchange_schema.py's tables,
plus the confidence math from ARCHITECTURE-Interchange_Core.md §7.

Confidence is never stored as a mutable field (see the edge schema design
doc, §7) — compute_confidence() sums relationship_evidence rows on demand.
"""

import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class Component:
    component_id: str
    part_type_id: int
    interchange_code: Optional[str] = None


@dataclass
class Identifier:
    component_id: str
    ns: str
    value: str
    visibility: Optional[str] = None


@dataclass
class ComponentAttribute:
    component_id: str
    name: str
    provenance: str
    source_observation_id: int
    qualifier: str = ""
    value_text: Optional[str] = None
    value_number: Optional[float] = None
    value_boolean: Optional[bool] = None
    unit: Optional[str] = None
    resolver_version: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self):
        values = (self.value_text, self.value_number, self.value_boolean)
        if sum(value is not None for value in values) != 1:
            raise ValueError("exactly one typed component attribute value is required")
        if self.value_boolean is not None and not isinstance(self.value_boolean, bool):
            raise ValueError("value_boolean must be a bool")


@dataclass
class Edge:
    type: str
    from_component_id: str
    to_component_id: Optional[str] = None
    group_key: Optional[str] = None
    status: str = "candidate"
    resolver_version: Optional[str] = None
    notes: Optional[str] = None
    id: Optional[int] = None


@dataclass
class EdgeSubstitutionDetail:
    edge_id: int
    basis: str
    verdict: str
    source_text: Optional[str] = None


@dataclass
class EdgeSupersessionDetail:
    edge_id: int
    note: Optional[str] = None


@dataclass
class EdgeCaveat:
    edge_id: int
    blocking: bool
    text: str
    becomes_input: Optional[str] = None
    id: Optional[int] = None


@dataclass
class EdgeRequiredPart:
    edge_id: int
    ns: str
    value: str
    role: Optional[str] = None
    id: Optional[int] = None


@dataclass
class RelationshipEvidence:
    edge_id: int
    event_type: str
    effect_alpha: float
    effect_beta: float
    occurred_at: str
    source_observation_id: Optional[int] = None
    actor_id: Optional[str] = None
    id: Optional[int] = None


@dataclass
class IdentifierEquivalenceCandidate:
    ns_a: str
    value_a: str
    ns_b: str
    value_b: str
    status: str = "open"
    merged_component_id: Optional[str] = None
    id: Optional[int] = None


@dataclass
class IdentifierEquivalenceEvidence:
    candidate_id: Optional[int]
    event_type: str
    effect_alpha: float
    effect_beta: float
    occurred_at: str
    source_observation_id: Optional[int] = None
    actor_id: Optional[str] = None
    id: Optional[int] = None


# ARCHITECTURE-Interchange_Core.md §7, "Prior, from attribute match" table.
PRIOR_BY_MATCH_QUALITY = {
    "all_critical_exact": (3.0, 1.0),
    "within_tolerance": (2.0, 1.0),
    "unknown_incomplete": (1.0, 1.0),
}

# Maps edge_substitution_detail.basis values to the match-quality prior.
# attribute_match_exact is the only basis that has actually exercised "all
# critical attributes exact" so far (the SW6DE/SW6DEL case) - every other
# basis starts from the honest "unknown/incomplete" prior per §7, then
# accumulates real evidence on top (buyer_confirmed_install,
# manufacturer_documented, etc. are EVENT types, not priors - see
# relationship_evidence event_type, not this table).
_BASIS_TO_PRIOR = {
    "attribute_match_exact": "all_critical_exact",
}


def prior_for_basis(basis):
    quality = _BASIS_TO_PRIOR.get(basis, "unknown_incomplete")
    return PRIOR_BY_MATCH_QUALITY[quality]


def compute_confidence(evidence_rows):
    alpha = sum(r.effect_alpha for r in evidence_rows)
    beta = sum(r.effect_beta for r in evidence_rows)
    if alpha + beta == 0:
        return {"alpha": 0.0, "beta": 0.0, "value": None, "certainty": 0.0}
    return {
        "alpha": alpha,
        "beta": beta,
        "value": alpha / (alpha + beta),
        "certainty": alpha + beta,
    }


def self_test(verbose=False):
    failures = []

    detail = EdgeSupersessionDetail(edge_id=7, note="7330G3351 replaced by 9420-351")
    if detail.edge_id != 7 or "9420-351" not in detail.note:
        failures.append(f"supersession detail mismatch: {detail}")

    for kwargs in (
        {"value_text": "12VDC"},
        {"value_number": 1.0},
        {"value_boolean": True},
    ):
        attr = ComponentAttribute(
            component_id="c_test", name="test", provenance="test",
            source_observation_id=999, **kwargs)
        if sum(v is not None for v in
               (attr.value_text, attr.value_number, attr.value_boolean)) != 1:
            failures.append(f"valid component attribute rejected: {attr}")

    for kwargs in ({}, {"value_text": "x", "value_number": 1.0},
                   {"value_boolean": 1}):
        try:
            ComponentAttribute(
                component_id="c_test", name="invalid", provenance="test",
                source_observation_id=999, **kwargs)
            failures.append(f"invalid component attribute accepted: {kwargs}")
        except ValueError:
            pass

    if prior_for_basis("attribute_match_exact") != (3.0, 1.0):
        failures.append("attribute_match_exact prior should be (3, 1)")
    if prior_for_basis("buyer_confirmed_install") != (1.0, 1.0):
        failures.append("unrecognized basis should fall back to (1, 1)")

    # Ground-truth.yaml's canonical edge: prior only, Beta(3,1) -> 0.75, n=4.
    ev = [RelationshipEvidence(edge_id=1, event_type="attribute_prior",
                                effect_alpha=3.0, effect_beta=1.0,
                                occurred_at="2026-07-31T00:00:00+00:00")]
    result = compute_confidence(ev)
    if result["value"] != 0.75 or result["certainty"] != 4.0:
        failures.append(f"expected value=0.75 certainty=4.0, got {result}")

    empty_result = compute_confidence([])
    if empty_result["value"] is not None:
        failures.append("confidence with no evidence should be None, not a number")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: prior lookup and confidence math both correct")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))


if __name__ == "__main__":
    main()
