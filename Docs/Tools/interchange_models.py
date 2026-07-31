#!/usr/bin/env python3
"""
interchange_models.py — dataclasses mirroring interchange_schema.py's tables,
plus the confidence math from ARCHITECTURE-Interchange_Core.md §7.

Confidence is never stored as a mutable field (see the edge schema design
doc, §7) — compute_confidence() sums relationship_evidence rows on demand.
"""

import sys
from dataclasses import dataclass, field
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
