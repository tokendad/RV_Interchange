# Thermostat Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** implemented and verified 2026-08-01

**Goal:** Persist the in-hand Coleman thermostat, its queryable terminal interface, and its isolated retailer identifier-equivalence candidate in the derived SQLite store.

**Architecture:** Add a typed, qualified `component_attributes` table and matching model/store APIs. Resolve observations #44-#47 into one fixture component, and resolve observation #43 into a separate open identifier-equivalence candidate without creating unsupported compatibility or supersession edges.

**Tech Stack:** Python 3, SQLite, dataclasses, PyYAML, existing inline `self_test()` convention.

## Global Constraints

- Observations are append-only; add a structured supplement instead of editing observation #44.
- Persist only `AP7862`, `7330G335`, `PCB1060`, and `SPCB-2` on the in-hand component.
- Component attributes use typed scalar columns and qualifiers; no JSON appears in the query path.
- Every component attribute has a non-null source observation and provenance.
- Compatibility, supersession, and identifier equivalence remain distinct concepts.
- Do not create thermostat substitution or supersession edges until endpoint components are resolved.
- Preserve the unrelated untracked `Docs/Data/JR-Products/` files.

---

### Task 1: Structured board-position evidence and vocabulary

**Files:**
- Modify: `Docs/Tools/resolver.py`
- Modify: `Docs/Tools/observations.db`

**Interfaces:**
- Consumes: raw key `terminal_board_positions`.
- Produces: canonical `terminal_board_position_map` and append-only observation #46.

- [x] **Step 1: Add the failing vocabulary test**

Extend the thermostat case in `resolver.py:self_test()` with:

```python
"terminal_board_positions": {
    "R": "W1", "Y": "W5", "W": "W6",
    "GL": "W3", "GH": "W4", "B": "W2",
}
```

Assert it normalizes to `terminal_board_position_map` with no unmapped key.

- [x] **Step 2: Verify RED**

Run: `cd Docs/Tools && python3 resolver.py --self-test`

Expected: failure naming `terminal_board_positions` and the missing canonical value.

- [x] **Step 3: Add the minimal canonical mapping**

Add `terminal_board_position_map` to `CANONICAL` and map
`terminal_board_positions` to it in `ALIASES`.

- [x] **Step 4: Verify GREEN**

Run: `cd Docs/Tools && python3 resolver.py --self-test`

Expected: `ALL PASS`.

- [x] **Step 5: Add observation #46**

Use `observations.py add` with `source_type=dataplate_photo`, the same four photo paths,
and extracted JSON containing only the structured board-position map plus a source
statement that it supplements #44. Run `resolver.py --assign-tiers` and `--validate`;
require tier 2 and `ALL KEYS CLASSIFIED`.

- [x] **Step 6: Add observation #47 after input audit**

The implementation audit found that #45 documented voltage/stages but did not structure
them. Add an append-only manufacturer-PDF supplement with `voltage=12VDC` and
`stages=single`; classify both keys test-first, assign tier 2, and leave #45 unchanged.

---

### Task 2: Component attribute schema and model

**Files:**
- Modify: `Docs/Tools/interchange_schema.py`
- Modify: `Docs/Tools/interchange_models.py`

**Interfaces:**
- Produces: table `component_attributes` and dataclass
  `ComponentAttribute(component_id, name, provenance, source_observation_id,
  qualifier="", value_text=None, value_number=None, value_boolean=None, unit=None,
  resolver_version=None, id=None)`.

- [x] **Step 1: Add failing schema assertions**

Require `component_attributes` in the expected table set. Assert indexes
`idx_component_attributes_lookup` and `idx_component_attributes_observation` exist.
Attempt invalid SQL inserts with zero and two value columns and require
`sqlite3.IntegrityError`.

- [x] **Step 2: Verify schema RED**

Run: `cd Docs/Tools && python3 interchange_schema.py --self-test --verbose`

Expected: failure because the table/indexes do not exist.

- [x] **Step 3: Implement the table and indexes**

Add the exact DDL from the approved design, including typed-value checks, boolean check,
foreign key, uniqueness constraint, and both indexes.

- [x] **Step 4: Verify schema GREEN**

Run: `cd Docs/Tools && python3 interchange_schema.py --self-test --verbose`

Expected: 16 tables and `self_test: PASS`.

- [x] **Step 5: Add failing model assertions**

In `interchange_models.py:self_test()`, construct valid text, number, and boolean
attributes. Then construct attributes with zero and two populated value fields and require
`ValueError` from `__post_init__`.

- [x] **Step 6: Verify model RED**

Run: `cd Docs/Tools && python3 interchange_models.py --self-test`

Expected: failure because `ComponentAttribute` is absent.

- [x] **Step 7: Implement `ComponentAttribute`**

Add the dataclass and a `__post_init__` count of non-`None` typed values. Reject counts
other than one; reject a non-boolean `value_boolean`.

- [x] **Step 8: Verify model GREEN**

Run: `cd Docs/Tools && python3 interchange_models.py --self-test`

Expected: `self_test: PASS`.

---

### Task 3: Attribute and identifier-candidate persistence

**Files:**
- Modify: `Docs/Tools/interchange_schema.py`
- Modify: `Docs/Tools/interchange_models.py`
- Modify: `Docs/Tools/interchange_store.py`

**Interfaces:**
- Produces: `IdentifierEquivalenceCandidate`, `IdentifierEquivalenceEvidence`,
  `insert_component_attribute`, `get_component_attributes`,
  `insert_identifier_equivalence_candidate`, `insert_identifier_equivalence_evidence`,
  `get_identifier_equivalence_candidates`, and `get_identifier_equivalence_evidence`.

- [x] **Step 1: Add failing store round-trip tests**

Extend `interchange_store.py:self_test()` to insert/query one attribute of each typed value,
one open `AR7815`/`7330F3858` candidate, and one observation #43 evidence row with effects
2/1. Assert reverse candidate insertion raises `ValueError`.

- [x] **Step 2: Verify store RED**

Run: `cd Docs/Tools && python3 interchange_store.py --self-test`

Expected: import/name failure for the missing APIs.

- [x] **Step 3: Add candidate constraints and indexes**

Add a unique constraint for the stored candidate orientation and indexes for both
identifier endpoints. Preserve existing tables with `CREATE ... IF NOT EXISTS`.

- [x] **Step 4: Implement dataclasses and store APIs**

Map SQLite rows back to dataclasses. Before candidate insert, query both orientations and
raise `ValueError` when either exists. Store candidate evidence using the existing
append-only alpha/beta event shape.

- [x] **Step 5: Verify store GREEN**

Run: `cd Docs/Tools && python3 interchange_schema.py --self-test && python3 interchange_models.py --self-test && python3 interchange_store.py --self-test`

Expected: all three report `PASS`.

---

### Task 4: Thermostat component resolver

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: observations #43-#47 and APIs from Tasks 1-3.
- Produces: `thermostat_from_observations(photo_row, manual_row, positions_row,
  scalar_row, component_id)` and `identifier_candidate_from_observation(obs_row)`.

- [x] **Step 1: Add failing happy-path resolver assertions**

Load #44, #45, #46, and #47. Require component ID `c_placeholder_tstat`, part type 415, code
`415-0012-A`, exactly four identifiers, 26 attributes (six each for order, position,
color, function plus voltage and stages), correct sources/provenance, and no candidate
identifiers attached.

- [x] **Step 2: Add failing validation assertions**

Copy rows into dictionaries with malformed extracted JSON and require `ValueError` for a
missing terminal color, mismatched function terminal set, duplicate terminal order, and
an unexpected fifth physical identifier.

- [x] **Step 3: Add failing candidate assertions**

Load #43 and require an open `AR7815`/`7330F3858` candidate plus evidence event
`retailer_cross_reference`, effects 2/1, and `source_observation_id=43`.

- [x] **Step 4: Verify resolver RED**

Run: `cd Docs/Tools && python3 edge_resolver.py --self-test --verbose`

Expected: failure because the thermostat builders are absent.

- [x] **Step 5: Implement the thermostat builder**

Normalize all rows with `strict=True`. Compare exact identifier and terminal sets before
constructing the component, identifiers, and qualified typed attributes. Use
`in_hand`/44, `in_hand`/46, and `manufacturer_pdf`/45 provenance exactly.

- [x] **Step 6: Implement the candidate builder**

Read #43's normalized `sku_relationship`, require the two expected namespaces/values, and
return the candidate/evidence without returning or modifying component identifiers.

- [x] **Step 7: Verify resolver GREEN**

Run: `cd Docs/Tools && python3 edge_resolver.py --self-test --verbose`

Expected: existing Suburban assertions and new thermostat/candidate assertions pass.

---

### Task 5: Full fixture reproduction and status documentation

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`
- Modify: `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md`
- Modify: `Docs/Inital_Design/PLAN-Staged_Build.md`
- Modify: `README.md`

**Interfaces:**
- Extends: `check_fixture(ground_truth_path, obs_db_path) -> int`.

- [x] **Step 1: Add thermostat fixture mismatch checks**

Build and persist the thermostat in the in-memory store. Compare the component, exact
identifiers, 26 attributes, open candidate, and candidate evidence against the fixture.
Assert the component has no thermostat `substitutes`/`supersedes` edges and none of the six
forbidden candidate/nearby identifiers.

- [x] **Step 2: Verify fixture RED**

Run: `cd Docs/Tools && python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml`

Expected: nonzero thermostat mismatches while the Suburban edge still matches.

- [x] **Step 3: Complete fixture comparison and reporting**

Accumulate Suburban and thermostat mismatches into one final count. Print labeled
Suburban and thermostat summaries and return nonzero for any mismatch.

- [x] **Step 4: Refresh status documents**

Update observation count to 46, mark the thermostat component/attribute/candidate resolver
milestone complete, and name resolved endpoint components for compatibility/supersession
as the next Coleman step.

- [x] **Step 5: Verify fixture GREEN**

Run: `cd Docs/Tools && python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml`

Expected: both sections pass and the command reports zero total mismatches.

---

### Task 6: Regression verification and commit

**Files:**
- Verify all files named above plus the approved design and this plan.

- [x] **Step 1: Run the full suite**

```bash
cd Docs/Tools
python3 -m unittest -v test_vendor_discovery.py
python3 resolver.py --self-test
python3 resolver.py --db observations.db --validate
python3 suburban_parser.py --self-test
python3 interchange_schema.py --self-test --verbose
python3 interchange_models.py --self-test
python3 interchange_store.py --self-test
python3 edge_resolver.py --self-test --verbose
python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml
```

Expected: all tests pass, 47 observations classify, and fixture mismatches equal zero.

- [x] **Step 2: Audit the final diff**

Run `git diff --check`, inspect the fixture and schema diffs, verify database integrity,
and confirm `Docs/Data/JR-Products/` remains untracked.

- [x] **Step 3: Commit**

Stage only planned paths and commit with message:

```text
Resolve Coleman thermostat into interchange store
```
