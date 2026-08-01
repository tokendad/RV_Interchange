# Thermostat Resolver Design

**Status:** approved for implementation
**Date:** 2026-08-01
**Scope:** persist the in-hand Coleman thermostat, its queryable electrical interface,
and the retailer-only identifier-equivalence candidate from observations #43-#46.

## 1. Goal

Extend the Stage 1 derived SQLite store beyond the two Suburban anchor components so it
can reproduce the thermostat component in `ground-truth.yaml`. The resolver must persist
the exact identifiers photographed on the installed unit and a queryable, provenance-aware
terminal interface without promoting compatibility, supersession, or retailer crosswalks
into confirmed physical identity.

## 2. Component attribute storage

Add a generic `component_attributes` table:

```sql
CREATE TABLE component_attributes (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id           TEXT NOT NULL REFERENCES components(component_id),
    name                   TEXT NOT NULL,
    qualifier              TEXT NOT NULL DEFAULT '',
    value_text             TEXT,
    value_number           REAL,
    value_boolean          INTEGER,
    unit                   TEXT,
    provenance             TEXT NOT NULL,
    source_observation_id  INTEGER NOT NULL,
    resolver_version       TEXT,
    created_at             TEXT NOT NULL,
    CHECK (
      (value_text IS NOT NULL) +
      (value_number IS NOT NULL) +
      (value_boolean IS NOT NULL) = 1
    ),
    CHECK (value_boolean IS NULL OR value_boolean IN (0, 1)),
    UNIQUE (component_id, name, qualifier, source_observation_id)
);
```

Create indexes on `(component_id, name, qualifier)` and
`source_observation_id`. The observation ID is required and is a provenance pointer rather
than a foreign key because `observations` lives in a separate SQLite database.

The table is a qualified, typed EAV model. Scalar attributes use an empty qualifier.
Repeated structured facts use a meaningful qualifier, allowing ordinary indexed SQL
without JSON parsing. Exactly one typed value column must be populated.

For the thermostat, observation #44 produces:

| Name | Qualifier | Value | Provenance |
|---|---|---|---|
| `terminal_order` | terminal label | ordinal 1-6 | obs #44, in hand |
| `installed_wire_color` | terminal label | observed color | obs #44, in hand |

Observation #44 recorded the board positions in its source statement but not as a
structured extracted field. Because observations are append-only, add observation #46 as
a structured transcription supplement rather than editing #44. It produces:

| Name | Qualifier | Value | Provenance |
|---|---|---|---|
| `terminal_board_position` | terminal label | `W1`/`W5`/`W6`/`W3`/`W4`/`W2` | obs #46, in hand |

Observation #45 produces:

| Name | Qualifier | Value | Provenance |
|---|---|---|---|
| `terminal_function` | terminal label | documented electrical function | obs #45, manufacturer PDF |
| `voltage` | empty | `12VDC` | obs #45, manufacturer PDF |
| `stages` | empty | `single` | obs #45, manufacturer-PDF inference from one compressor-control circuit |

Wire color remains supporting evidence rather than an interchange key because the manual
warns that installer-provided colors may differ.

## 3. Python model and store interfaces

Add `ComponentAttribute` to `interchange_models.py` with fields matching the table and
optional `id`. Its constructor must reject zero or multiple populated value fields before
database insertion, giving callers the same invariant as the SQLite `CHECK` constraint.

Add these store operations to `interchange_store.py`:

```python
insert_component_attribute(conn, attribute) -> int
get_component_attributes(conn, component_id, name=None) -> list[ComponentAttribute]
```

Add dataclasses and store operations for the already-existing candidate tables:

```python
IdentifierEquivalenceCandidate
IdentifierEquivalenceEvidence
insert_identifier_equivalence_candidate(conn, candidate) -> int
insert_identifier_equivalence_evidence(conn, evidence) -> int
get_identifier_equivalence_candidates(conn, status=None) -> list[IdentifierEquivalenceCandidate]
get_identifier_equivalence_evidence(conn, candidate_id) -> list[IdentifierEquivalenceEvidence]
```

Add a uniqueness constraint on `(ns_a, value_a, ns_b, value_b)` plus lookup indexes for
both identifier endpoints. The resolver preserves the source's pair ordering and checks for
the reverse ordering before insert so one claim cannot be duplicated in both directions.

The candidate insert stores `AR7815` and `7330F3858` as an open pair. Its evidence row
uses observation #43, event type `retailer_cross_reference`, and the fixture's existing
Beta effects `alpha=2`, `beta=1`.

## 4. Thermostat resolver

Add a focused builder in `edge_resolver.py`:

```python
thermostat_from_observations(photo_row, manual_row, positions_row, component_id)
    -> tuple[Component, list[Identifier], list[ComponentAttribute]]
```

The builder normalizes all three observations through `resolver.py`, then requires:

- physical identifiers exactly containing `icm:AP7862`, `coleman:7330G335`,
  `silkscreen:PCB1060`, and `silkscreen:SPCB-2`;
- terminal order exactly `R, Y, W, GL, GH, B`;
- board positions for every terminal;
- installed colors for every terminal;
- documented functions for every terminal.

Missing terminals, duplicate terminal labels, unknown identifiers, or a mismatch between
the two terminal sets raise `ValueError` before any rows are inserted. The returned
component uses fixture ID `c_placeholder_tstat`, part type `415`, and interchange code
`415-0012-A`. Opaque production ID generation remains outside this milestone, consistent
with the existing Suburban resolver.

Add a separate helper that reads observation #43 and returns the open
`AR7815`/`7330F3858` candidate plus its evidence. It must not attach either identifier to
the in-hand component.

## 5. Relationship boundaries

This milestone deliberately does not create broader thermostat `substitutes` or
`supersedes` edges:

- Observation #45 proves family-level compatibility among the thermostat generations
  depicted in the manual, but the captured text does not establish resolved component IDs
  for every depicted endpoint.
- Observation #41 states that `9420-351` replaces `7330G3351` and `7330F3852`, but those
  exact catalog models are not the photographed legacy `7330G335` and are not yet resolved
  as components.

Their evidence stays in `observations.db`. Persisting an edge without resolved endpoints
would violate the schema and risk conflating compatibility, supersession, and identity.

## 6. Fixture validation

Extend `edge_resolver.py --check-fixture` without weakening the existing Suburban check.
It must additionally verify:

- one thermostat component with part type `415` and code `415-0012-A`;
- exactly the four confirmed identifiers and their `behind_faceplate` visibility;
- six terminal ordinals, board positions, installed colors, and functions;
- scalar voltage and stage attributes;
- one open identifier-equivalence candidate `AR7815`/`7330F3858` backed by observation
  #43 evidence;
- no `AR7815`, `AR7816`, `AP7862-3`, `PCB1060-4A`, `7330G3351`, or `7330F3858` identifier
  attached to the in-hand component;
- no inferred thermostat substitution or supersession edge.

The command continues to return nonzero on any mismatch and prints the total mismatch
count across both the Suburban and thermostat fixture cases.

## 7. Testing and compatibility

Implementation follows test-driven development:

1. Schema self-test first fails because `component_attributes` is absent, then passes.
2. Model/store tests first fail for the missing attribute and candidate interfaces, then
   pass with SQLite round trips and invalid typed-value cases.
3. Resolver tests first fail for the absent thermostat builder, incomplete terminal sets,
   and candidate isolation, then pass.
4. Fixture validation first reports thermostat mismatches, then reaches zero without
   changing the existing SW6DE/SW6DEL result.

No existing table or public function is removed. Existing Suburban component and edge
resolution behavior remains byte-for-byte compatible at its interfaces. No new external
dependency is introduced.
