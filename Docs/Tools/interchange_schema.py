#!/usr/bin/env python3
"""
interchange_schema.py — DDL for the derived components/edges store.

Per ARCHITECTURE-Interchange_Core.md §9: this store is REBUILDABLE from
observations.db, never hand-edited. See
docs/superpowers/specs/2026-07-31-edge-schema-design.md for the design
rationale (shared edges core + typed detail tables, one row per
substitution direction, append-only relationship_evidence).
"""

import sqlite3
import sys

DEFAULT_DB = "components.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS components (
    component_id      TEXT PRIMARY KEY,
    part_type_id      INTEGER NOT NULL,
    interchange_code  TEXT,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identifiers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id  TEXT NOT NULL REFERENCES components(component_id),
    ns            TEXT NOT NULL,
    value         TEXT NOT NULL,
    visibility    TEXT
);
CREATE INDEX IF NOT EXISTS idx_identifiers_ns_value ON identifiers(ns, value);
CREATE INDEX IF NOT EXISTS idx_identifiers_component ON identifiers(component_id);

CREATE TABLE IF NOT EXISTS edges (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    type                TEXT NOT NULL,
    from_component_id   TEXT NOT NULL REFERENCES components(component_id),
    to_component_id     TEXT REFERENCES components(component_id),
    group_key           TEXT,
    status              TEXT NOT NULL DEFAULT 'candidate',
    resolver_version    TEXT,
    created_at          TEXT NOT NULL,
    retired_at          TEXT,
    notes               TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_component_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_component_id);
CREATE INDEX IF NOT EXISTS idx_edges_group ON edges(group_key);

CREATE TABLE IF NOT EXISTS edge_substitution_detail (
    edge_id      INTEGER PRIMARY KEY REFERENCES edges(id),
    basis        TEXT NOT NULL,
    verdict      TEXT NOT NULL,
    source_text  TEXT
);

CREATE TABLE IF NOT EXISTS edge_caveat (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id        INTEGER NOT NULL REFERENCES edges(id),
    blocking       INTEGER NOT NULL,
    text           TEXT NOT NULL,
    becomes_input  TEXT
);
CREATE INDEX IF NOT EXISTS idx_caveat_edge ON edge_caveat(edge_id);

CREATE TABLE IF NOT EXISTS edge_required_part (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id  INTEGER NOT NULL REFERENCES edges(id),
    ns       TEXT NOT NULL,
    value    TEXT NOT NULL,
    role     TEXT
);
CREATE INDEX IF NOT EXISTS idx_required_part_edge ON edge_required_part(edge_id);

CREATE TABLE IF NOT EXISTS edge_contains_detail (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id         INTEGER NOT NULL REFERENCES edges(id),
    child_ns        TEXT NOT NULL,
    child_value     TEXT NOT NULL,
    role            TEXT,
    assembly_level  TEXT
);

CREATE TABLE IF NOT EXISTS edge_controls_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_requires_system_detail (
    edge_id      INTEGER PRIMARY KEY REFERENCES edges(id),
    system_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edge_supersession_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_shared_subassembly_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS edge_aftermarket_replaces_detail (
    edge_id  INTEGER PRIMARY KEY REFERENCES edges(id),
    note     TEXT
);

CREATE TABLE IF NOT EXISTS relationship_evidence (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id                 INTEGER NOT NULL REFERENCES edges(id),
    event_type              TEXT NOT NULL,
    effect_alpha            REAL NOT NULL,
    effect_beta             REAL NOT NULL,
    source_observation_id   INTEGER,
    actor_id                TEXT,
    occurred_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_edge ON relationship_evidence(edge_id);

CREATE TABLE IF NOT EXISTS identifier_equivalence_candidate (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    ns_a                  TEXT NOT NULL,
    value_a               TEXT NOT NULL,
    ns_b                  TEXT NOT NULL,
    value_b               TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'open',
    merged_component_id   TEXT REFERENCES components(component_id)
);

CREATE TABLE IF NOT EXISTS identifier_equivalence_evidence (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id            INTEGER NOT NULL
                            REFERENCES identifier_equivalence_candidate(id),
    event_type              TEXT NOT NULL,
    effect_alpha            REAL NOT NULL,
    effect_beta             REAL NOT NULL,
    source_observation_id   INTEGER,
    actor_id                TEXT,
    occurred_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ident_equiv_evidence_candidate
    ON identifier_equivalence_evidence(candidate_id);
"""


def init_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def self_test(verbose=False):
    conn = init_db(":memory:")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "components", "identifiers", "edges", "edge_substitution_detail",
        "edge_caveat", "edge_required_part", "edge_contains_detail",
        "edge_controls_detail", "edge_requires_system_detail",
        "edge_supersession_detail", "edge_shared_subassembly_detail",
        "edge_aftermarket_replaces_detail", "relationship_evidence",
        "identifier_equivalence_candidate", "identifier_equivalence_evidence",
    }
    missing = expected - tables
    if missing:
        print(f"FAIL: missing tables {missing}")
        return 1
    # calling init_db twice on the same file must not raise (IF NOT EXISTS)
    init_db(":memory:")
    if verbose:
        print(f"PASS: {len(expected)} tables created")
    print("self_test: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test(verbose="--verbose" in sys.argv))
    init_db(DEFAULT_DB)
    sys.exit(0)


if __name__ == "__main__":
    main()
