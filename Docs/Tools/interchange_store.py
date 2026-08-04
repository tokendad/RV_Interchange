#!/usr/bin/env python3
"""
interchange_store.py — sqlite persistence for the dataclasses in
interchange_models.py, against the schema in interchange_schema.py.
"""

import sys
from datetime import datetime, timezone

from interchange_models import (
    Component, Identifier, ComponentAttribute, Edge, EdgeSubstitutionDetail,
    EdgeSupersessionDetail, EdgeControlsDetail, EdgeCaveat, EdgeRequiredPart,
    RelationshipEvidence, IdentifierEquivalenceCandidate, IdentifierEquivalenceEvidence,
)
from interchange_schema import init_db


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_component(conn, component):
    conn.execute(
        "INSERT INTO components (component_id, part_type_id, interchange_code, created_at) "
        "VALUES (?, ?, ?, ?)",
        (component.component_id, component.part_type_id, component.interchange_code,
         now_iso()))
    conn.commit()


def insert_identifier(conn, identifier):
    cur = conn.execute(
        "INSERT INTO identifiers (component_id, ns, value, visibility) VALUES (?, ?, ?, ?)",
        (identifier.component_id, identifier.ns, identifier.value, identifier.visibility))
    conn.commit()
    return cur.lastrowid


def get_component(conn, component_id):
    row = conn.execute(
        "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
    if row is None:
        return None
    return Component(component_id=row["component_id"], part_type_id=row["part_type_id"],
                      interchange_code=row["interchange_code"])


def get_component_by_identifier(conn, ns, value):
    row = conn.execute(
        "SELECT component_id FROM identifiers WHERE ns = ? AND value = ?",
        (ns, value)).fetchone()
    if row is None:
        return None
    return get_component(conn, row["component_id"])


def get_identifiers_for_component(conn, component_id):
    rows = conn.execute(
        "SELECT * FROM identifiers WHERE component_id = ? ORDER BY id",
        (component_id,)).fetchall()
    return [Identifier(component_id=r["component_id"], ns=r["ns"], value=r["value"],
                        visibility=r["visibility"]) for r in rows]


def search_identifiers(conn, query, limit=20):
    """Ranked, deduped (component_id, matched_value) pairs for identifiers matching `query`.

    Exact matches (case-insensitive) rank first; ties break by shorter value,
    then alphabetically. A component can carry several matching identifiers
    across namespaces — it appears once in the result (paired with the
    best-ranked identifier that matched), not once per match.
    """
    if not query or limit <= 0:
        return []
    escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = f"%{escaped_query}%"
    rows = conn.execute(
        "SELECT component_id, value FROM identifiers "
        "WHERE value LIKE ? ESCAPE '\\' COLLATE NOCASE "
        "ORDER BY (LOWER(value) = LOWER(?)) DESC, LENGTH(value), value",
        (like_pattern, query)).fetchall()
    results = []
    seen = set()
    for row in rows:
        if row["component_id"] in seen:
            continue
        seen.add(row["component_id"])
        results.append((row["component_id"], row["value"]))
        if len(results) >= limit:
            break
    return results


def insert_component_attribute(conn, attribute):
    cur = conn.execute(
        "INSERT INTO component_attributes "
        "(component_id, name, qualifier, value_text, value_number, value_boolean, unit, "
        "provenance, source_observation_id, resolver_version, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (attribute.component_id, attribute.name, attribute.qualifier,
         attribute.value_text, attribute.value_number,
         int(attribute.value_boolean) if attribute.value_boolean is not None else None,
         attribute.unit, attribute.provenance, attribute.source_observation_id,
         attribute.resolver_version, now_iso()))
    conn.commit()
    attribute.id = cur.lastrowid
    return attribute.id


def get_component_attributes(conn, component_id, name=None):
    if name is None:
        rows = conn.execute(
            "SELECT * FROM component_attributes WHERE component_id = ? ORDER BY id",
            (component_id,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM component_attributes WHERE component_id = ? AND name = ? "
            "ORDER BY id", (component_id, name)).fetchall()
    return [ComponentAttribute(
        id=r["id"], component_id=r["component_id"], name=r["name"],
        qualifier=r["qualifier"], value_text=r["value_text"],
        value_number=r["value_number"],
        value_boolean=(bool(r["value_boolean"])
                       if r["value_boolean"] is not None else None),
        unit=r["unit"], provenance=r["provenance"],
        source_observation_id=r["source_observation_id"],
        resolver_version=r["resolver_version"]) for r in rows]


def insert_identifier_equivalence_candidate(conn, candidate):
    duplicate = conn.execute(
        "SELECT id FROM identifier_equivalence_candidate WHERE "
        "(ns_a = ? AND value_a = ? AND ns_b = ? AND value_b = ?) OR "
        "(ns_a = ? AND value_a = ? AND ns_b = ? AND value_b = ?)",
        (candidate.ns_a, candidate.value_a, candidate.ns_b, candidate.value_b,
         candidate.ns_b, candidate.value_b, candidate.ns_a, candidate.value_a),
    ).fetchone()
    if duplicate is not None:
        raise ValueError(f"identifier-equivalence candidate already exists as #{duplicate['id']}")
    cur = conn.execute(
        "INSERT INTO identifier_equivalence_candidate "
        "(ns_a, value_a, ns_b, value_b, status, merged_component_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (candidate.ns_a, candidate.value_a, candidate.ns_b, candidate.value_b,
         candidate.status, candidate.merged_component_id))
    conn.commit()
    candidate.id = cur.lastrowid
    return candidate.id


def insert_identifier_equivalence_evidence(conn, evidence):
    cur = conn.execute(
        "INSERT INTO identifier_equivalence_evidence "
        "(candidate_id, event_type, effect_alpha, effect_beta, "
        "source_observation_id, actor_id, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evidence.candidate_id, evidence.event_type, evidence.effect_alpha,
         evidence.effect_beta, evidence.source_observation_id, evidence.actor_id,
         evidence.occurred_at))
    conn.commit()
    evidence.id = cur.lastrowid
    return evidence.id


def get_identifier_equivalence_candidates(conn, status=None):
    if status is None:
        rows = conn.execute(
            "SELECT * FROM identifier_equivalence_candidate ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM identifier_equivalence_candidate WHERE status = ? ORDER BY id",
            (status,)).fetchall()
    return [IdentifierEquivalenceCandidate(
        id=r["id"], ns_a=r["ns_a"], value_a=r["value_a"],
        ns_b=r["ns_b"], value_b=r["value_b"], status=r["status"],
        merged_component_id=r["merged_component_id"]) for r in rows]


def get_identifier_equivalence_evidence(conn, candidate_id):
    rows = conn.execute(
        "SELECT * FROM identifier_equivalence_evidence WHERE candidate_id = ? ORDER BY id",
        (candidate_id,)).fetchall()
    return [IdentifierEquivalenceEvidence(
        id=r["id"], candidate_id=r["candidate_id"], event_type=r["event_type"],
        effect_alpha=r["effect_alpha"], effect_beta=r["effect_beta"],
        source_observation_id=r["source_observation_id"], actor_id=r["actor_id"],
        occurred_at=r["occurred_at"]) for r in rows]


def insert_edge(conn, edge):
    cur = conn.execute(
        "INSERT INTO edges (type, from_component_id, to_component_id, group_key, "
        "status, resolver_version, created_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (edge.type, edge.from_component_id, edge.to_component_id, edge.group_key,
         edge.status, edge.resolver_version, now_iso(), edge.notes))
    conn.commit()
    edge.id = cur.lastrowid
    return edge.id


def insert_substitution_detail(conn, detail):
    conn.execute(
        "INSERT INTO edge_substitution_detail (edge_id, basis, verdict, source_text) "
        "VALUES (?, ?, ?, ?)",
        (detail.edge_id, detail.basis, detail.verdict, detail.source_text))
    conn.commit()


def insert_supersession_detail(conn, detail):
    conn.execute(
        "INSERT INTO edge_supersession_detail (edge_id, note) VALUES (?, ?)",
        (detail.edge_id, detail.note))
    conn.commit()


def get_supersession_detail(conn, edge_id):
    row = conn.execute(
        "SELECT * FROM edge_supersession_detail WHERE edge_id = ?", (edge_id,)).fetchone()
    if row is None:
        return None
    return EdgeSupersessionDetail(edge_id=row["edge_id"], note=row["note"])


def insert_controls_detail(conn, detail):
    conn.execute(
        "INSERT INTO edge_controls_detail (edge_id, note) VALUES (?, ?)",
        (detail.edge_id, detail.note))
    conn.commit()


def get_controls_detail(conn, edge_id):
    row = conn.execute(
        "SELECT * FROM edge_controls_detail WHERE edge_id = ?", (edge_id,)).fetchone()
    if row is None:
        return None
    return EdgeControlsDetail(edge_id=row["edge_id"], note=row["note"])


def insert_caveat(conn, caveat):
    cur = conn.execute(
        "INSERT INTO edge_caveat (edge_id, blocking, text, becomes_input) VALUES (?, ?, ?, ?)",
        (caveat.edge_id, int(caveat.blocking), caveat.text, caveat.becomes_input))
    conn.commit()
    caveat.id = cur.lastrowid
    return caveat.id


def insert_required_part(conn, part):
    cur = conn.execute(
        "INSERT INTO edge_required_part (edge_id, ns, value, role) VALUES (?, ?, ?, ?)",
        (part.edge_id, part.ns, part.value, part.role))
    conn.commit()
    part.id = cur.lastrowid
    return part.id


def get_required_parts_for_edge(conn, edge_id):
    rows = conn.execute(
        "SELECT * FROM edge_required_part WHERE edge_id = ?", (edge_id,)).fetchall()
    return [EdgeRequiredPart(id=r["id"], edge_id=r["edge_id"], ns=r["ns"],
                              value=r["value"], role=r["role"]) for r in rows]


def insert_evidence(conn, evidence):
    cur = conn.execute(
        "INSERT INTO relationship_evidence (edge_id, event_type, effect_alpha, effect_beta, "
        "source_observation_id, actor_id, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evidence.edge_id, evidence.event_type, evidence.effect_alpha, evidence.effect_beta,
         evidence.source_observation_id, evidence.actor_id, evidence.occurred_at))
    conn.commit()
    evidence.id = cur.lastrowid
    return evidence.id


def get_edges_from(conn, component_id, type=None):
    if type:
        return conn.execute(
            "SELECT * FROM edges WHERE from_component_id = ? AND type = ?",
            (component_id, type)).fetchall()
    return conn.execute(
        "SELECT * FROM edges WHERE from_component_id = ?", (component_id,)).fetchall()


def get_evidence_for_edge(conn, edge_id):
    rows = conn.execute(
        "SELECT * FROM relationship_evidence WHERE edge_id = ? ORDER BY id",
        (edge_id,)).fetchall()
    return [RelationshipEvidence(
        id=r["id"], edge_id=r["edge_id"], event_type=r["event_type"],
        effect_alpha=r["effect_alpha"], effect_beta=r["effect_beta"],
        source_observation_id=r["source_observation_id"], actor_id=r["actor_id"],
        occurred_at=r["occurred_at"]) for r in rows]


def get_caveats_for_edge(conn, edge_id):
    rows = conn.execute(
        "SELECT * FROM edge_caveat WHERE edge_id = ?", (edge_id,)).fetchall()
    return [EdgeCaveat(id=r["id"], edge_id=r["edge_id"], blocking=bool(r["blocking"]),
                        text=r["text"], becomes_input=r["becomes_input"]) for r in rows]


def self_test(verbose=False):
    conn = init_db(":memory:")
    failures = []

    insert_component(conn, Component("c_test_a", 412, "412-0001-A"))
    insert_component(conn, Component("c_test_b", 412, "412-0001-B"))
    insert_identifier(conn, Identifier("c_test_a", "suburban", "SW6DE"))

    fetched_component = get_component(conn, "c_test_a")
    if fetched_component is None or fetched_component.part_type_id != 412:
        failures.append(f"expected c_test_a with part_type_id 412, got {fetched_component}")

    by_identifier = get_component_by_identifier(conn, "suburban", "SW6DE")
    if by_identifier is None or by_identifier.component_id != "c_test_a":
        failures.append(f"expected SW6DE to resolve to c_test_a, got {by_identifier}")

    missing_identifier = get_component_by_identifier(conn, "suburban", "NOPE")
    if missing_identifier is not None:
        failures.append(f"expected None for unknown identifier, got {missing_identifier}")

    idents = get_identifiers_for_component(conn, "c_test_a")
    if len(idents) != 1 or idents[0].value != "SW6DE":
        failures.append(f"expected 1 identifier SW6DE for c_test_a, got {idents}")

    for attr in (
        ComponentAttribute("c_test_a", "voltage", "test", 900,
                           value_text="12VDC"),
        ComponentAttribute("c_test_a", "terminal_order", "test", 901,
                           qualifier="R", value_number=1.0),
        ComponentAttribute("c_test_a", "enabled", "test", 902,
                           value_boolean=True),
    ):
        insert_component_attribute(conn, attr)
    attrs = get_component_attributes(conn, "c_test_a")
    if len(attrs) != 3 or {a.name for a in attrs} != {
            "voltage", "terminal_order", "enabled"}:
        failures.append(f"expected 3 typed component attributes, got {attrs}")

    candidate = IdentifierEquivalenceCandidate(
        ns_a="icm", value_a="AR7815", ns_b="coleman", value_b="7330F3858")
    insert_identifier_equivalence_candidate(conn, candidate)
    insert_identifier_equivalence_evidence(conn, IdentifierEquivalenceEvidence(
        candidate_id=candidate.id, event_type="retailer_cross_reference",
        effect_alpha=2.0, effect_beta=1.0, occurred_at=now_iso(),
        source_observation_id=43))
    candidates = get_identifier_equivalence_candidates(conn, status="open")
    if len(candidates) != 1 or candidates[0].value_a != "AR7815":
        failures.append(f"expected open AR7815 candidate, got {candidates}")
    candidate_evidence = get_identifier_equivalence_evidence(conn, candidate.id)
    if len(candidate_evidence) != 1 or candidate_evidence[0].effect_alpha != 2.0:
        failures.append(f"expected candidate alpha=2 evidence, got {candidate_evidence}")
    try:
        insert_identifier_equivalence_candidate(conn, IdentifierEquivalenceCandidate(
            ns_a="coleman", value_a="7330F3858", ns_b="icm", value_b="AR7815"))
        failures.append("reverse-orientation duplicate candidate was accepted")
    except ValueError:
        pass

    edge = Edge(type="substitutes", from_component_id="c_test_a",
                to_component_id="c_test_b", group_key="412-0001")
    insert_edge(conn, edge)
    if edge.id is None:
        failures.append("insert_edge did not set edge.id")

    supersession = Edge(type="supersedes", from_component_id="c_test_a",
                        to_component_id="c_test_b")
    insert_edge(conn, supersession)
    insert_supersession_detail(conn, EdgeSupersessionDetail(
        edge_id=supersession.id, note="test replacement chain"))
    stored = get_supersession_detail(conn, supersession.id)
    if stored is None or stored.note != "test replacement chain":
        failures.append(f"supersession detail round trip failed: {stored}")

    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge.id, basis="attribute_match_exact", verdict="drop_in"))
    insert_caveat(conn, EdgeCaveat(edge_id=edge.id, blocking=True, text="test caveat"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="attribute_prior", effect_alpha=3.0, effect_beta=1.0,
        occurred_at=now_iso()))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="manufacturer_assertion", effect_alpha=2.0,
        effect_beta=0.0, occurred_at=now_iso()))
    conn.execute(
        "CREATE INDEX test_relationship_evidence_desc "
        "ON relationship_evidence(edge_id, id DESC)")

    fetched = get_edges_from(conn, "c_test_a", type="substitutes")
    if len(fetched) != 1:
        failures.append(f"expected 1 edge from c_test_a, got {len(fetched)}")

    ev = get_evidence_for_edge(conn, edge.id)
    if [item.event_type for item in ev] != [
            "attribute_prior", "manufacturer_assertion"]:
        failures.append(f"expected evidence in insertion order, got {ev}")

    caveats = get_caveats_for_edge(conn, edge.id)
    if len(caveats) != 1 or caveats[0].text != "test caveat":
        failures.append(f"expected 1 caveat, got {caveats}")

    insert_identifier(conn, Identifier("c_test_b", "suburban", "SW12DEL"))

    exact_match = search_identifiers(conn, "SW6DE")
    if exact_match != [("c_test_a", "SW6DE")]:
        failures.append(f"expected exact match search to return only c_test_a, got {exact_match}")

    substring_match = search_identifiers(conn, "SW")
    if substring_match != [("c_test_a", "SW6DE"), ("c_test_b", "SW12DEL")]:
        failures.append(
            f"expected substring search ranked shortest-value-first, got {substring_match}")

    limited = search_identifiers(conn, "SW", limit=1)
    if limited != [("c_test_a", "SW6DE")]:
        failures.append(f"expected limit=1 to return only the best match, got {limited}")

    no_match = search_identifiers(conn, "NOPE")
    if no_match != []:
        failures.append(f"expected no match for unknown query, got {no_match}")

    empty_query = search_identifiers(conn, "")
    if empty_query != []:
        failures.append(f"expected empty query to return [], got {empty_query}")

    wildcard_query = search_identifiers(conn, "%")
    if wildcard_query != []:
        failures.append(f"expected literal '%' query to match nothing, got {wildcard_query}")

    zero_limit = search_identifiers(conn, "SW", limit=0)
    if zero_limit != []:
        failures.append(f"expected limit=0 to return [], got {zero_limit}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    if verbose:
        print("PASS: full round trip through every insert/get function")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))


if __name__ == "__main__":
    main()
