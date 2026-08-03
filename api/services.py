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
