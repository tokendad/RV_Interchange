#!/usr/bin/env python3
"""
interchange_store.py — sqlite persistence for the dataclasses in
interchange_models.py, against the schema in interchange_schema.py.
"""

import sys
from datetime import datetime, timezone

from interchange_models import (
    Component, Identifier, Edge, EdgeSubstitutionDetail, EdgeCaveat,
    EdgeRequiredPart, RelationshipEvidence,
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
        "SELECT * FROM relationship_evidence WHERE edge_id = ?", (edge_id,)).fetchall()
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

    edge = Edge(type="substitutes", from_component_id="c_test_a",
                to_component_id="c_test_b", group_key="412-0001")
    insert_edge(conn, edge)
    if edge.id is None:
        failures.append("insert_edge did not set edge.id")

    insert_substitution_detail(conn, EdgeSubstitutionDetail(
        edge_id=edge.id, basis="attribute_match_exact", verdict="drop_in"))
    insert_caveat(conn, EdgeCaveat(edge_id=edge.id, blocking=True, text="test caveat"))
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type="attribute_prior", effect_alpha=3.0, effect_beta=1.0,
        occurred_at=now_iso()))

    fetched = get_edges_from(conn, "c_test_a", type="substitutes")
    if len(fetched) != 1:
        failures.append(f"expected 1 edge from c_test_a, got {len(fetched)}")

    ev = get_evidence_for_edge(conn, edge.id)
    if len(ev) != 1 or ev[0].effect_alpha != 3.0:
        failures.append(f"expected 1 evidence row with alpha=3.0, got {ev}")

    caveats = get_caveats_for_edge(conn, edge.id)
    if len(caveats) != 1 or caveats[0].text != "test caveat":
        failures.append(f"expected 1 caveat, got {caveats}")

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
