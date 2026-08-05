"""Canonical edge-type registry for the interchange graph.

The database column stays free-text, but the code paths that create, query,
and validate edges should all use this single vocabulary.
"""

EDGE_TYPE_SUBSTITUTES = "substitutes"
EDGE_TYPE_SUPERSEDES = "supersedes"
EDGE_TYPE_CONTROLS = "controls"
EDGE_TYPE_FITS = "fits"

EDGE_TYPES = (
    EDGE_TYPE_SUBSTITUTES,
    EDGE_TYPE_SUPERSEDES,
    EDGE_TYPE_CONTROLS,
    EDGE_TYPE_FITS,
)

REPLACEMENT_EDGE_TYPES = (
    EDGE_TYPE_SUBSTITUTES,
    EDGE_TYPE_SUPERSEDES,
)

EDGE_TYPES_SET = frozenset(EDGE_TYPES)
REPLACEMENT_EDGE_TYPES_SET = frozenset(REPLACEMENT_EDGE_TYPES)


def validate_edge_type(edge_type):
    if edge_type not in EDGE_TYPES_SET:
        raise ValueError(f"unknown edge type: {edge_type!r}")
    return edge_type
