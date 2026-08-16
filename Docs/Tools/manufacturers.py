"""Canonical manufacturer registry for the interchange graph.

Mirrors edge_types.py's single-source-of-truth pattern. Keyed on the same
`ns` values used in identifiers.ns - not every ns is a manufacturer (some
are sub-component namespaces or physical-marking identifier types), so
callers look up MANUFACTURER_NAMES.get(ns) and treat a miss as "no
manufacturer name to show," not an error.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Manufacturer:
    ns: str
    display_name: str


MANUFACTURERS = (
    Manufacturer(ns="suburban", display_name="Suburban"),
    Manufacturer(ns="coleman", display_name="Coleman-Mach"),
    Manufacturer(ns="atwood", display_name="Atwood"),
    Manufacturer(ns="norcold", display_name="Norcold"),
    Manufacturer(ns="furrion", display_name="Furrion"),
    Manufacturer(ns="girard", display_name="Girard"),
    Manufacturer(ns="lippert", display_name="Lippert"),
)

MANUFACTURER_NAMES = {m.ns: m.display_name for m in MANUFACTURERS}
