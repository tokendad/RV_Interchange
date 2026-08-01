# Coleman Thermostat Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture the in-hand Coleman thermostat and service manual as structured evidence, correct the fixture to the identifiers physically present, and refresh stale project status documentation.

**Architecture:** Preserve the two-layer design: photographs and the PDF become append-only rows in `observations.db`, while `ground-truth.yaml` records reviewed conclusions. Extend `resolver.py` only with generic canonical fields needed for identity and electrical-interface evidence; do not promote retailer-only candidate aliases.

**Tech Stack:** Python 3, SQLite, YAML/Markdown, existing inline `self_test()` convention and `unittest` discovery tests.

**Status:** Completed 2026-08-01. Observations #44/#45 were captured, the fixture and
canonical vocabulary were corrected, stale documentation was refreshed, and the full
verification suite passed.

## Global Constraints

- The photos are authoritative for identifiers, terminal order, installed wire colors, and board markings.
- The RV Products manual `1976-376 (4-02)` is authoritative for terminal functions and its stated family-level interchangeability.
- Installed wire color is supporting evidence, not the interchange key.
- `AP7862-3`, `PCB1060-4A`, `AR7815`, and `AR7816` must not be silently promoted to confirmed aliases.
- Observations are append-only; do not rewrite prior observation rows.
- Preserve the user's four untracked source photographs and add them intentionally to the implementation commit.

---

### Task 1: Classify thermostat evidence fields

**Files:**
- Modify: `Docs/Tools/resolver.py`

**Interfaces:**
- Consumes: raw observation keys passed to `normalize_extracted(observation_id, extracted, strict)`.
- Produces: canonical attributes `physical_identifiers`, `manufacture_date_code`, `terminal_order`, `installed_wire_colors`, `terminal_function_map`, and `compatibility_statement`.

- [x] **Step 1: Add a failing thermostat evidence case to `self_test()`**

Use a single representative payload containing `identifiers_observed`, `date_code`, `terminal_order`, `wire_colors`, `terminal_functions`, and `compatibility_statement`. Assert that non-strict normalization has no unmapped keys and that each value appears under the canonical name above.

- [x] **Step 2: Run the resolver self-test and verify RED**

Run: `cd Docs/Tools && python3 resolver.py --self-test`

Expected: `FAIL` reports the six thermostat keys as unmapped or missing canonical attributes.

- [x] **Step 3: Add the minimal canonical vocabulary and aliases**

Add the six canonical descriptions to `CANONICAL` and map the six raw keys in `ALIASES`. Do not add thermostat-specific parsing or identifier-merging behavior.

- [x] **Step 4: Run the resolver self-test and verify GREEN**

Run: `cd Docs/Tools && python3 resolver.py --self-test`

Expected: `ALL PASS`.

---

### Task 2: Capture the photos/manual and correct reviewed ground truth

**Files:**
- Modify: `Docs/Tools/observations.db`
- Modify: `Docs/Inital_Design/ground-truth.yaml`
- Create: `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md`
- Add: `Docs/Data/Coleman_Mach/Thermostat Images/20260801_103947.jpg`
- Add: `Docs/Data/Coleman_Mach/Thermostat Images/20260801_104000.jpg`
- Add: `Docs/Data/Coleman_Mach/Thermostat Images/20260801_104039.jpg`
- Add: `Docs/Data/Coleman_Mach/Thermostat Images/20260801_104050.jpg`

**Interfaces:**
- Consumes: the canonical fields from Task 1 and the four source photographs.
- Produces: two new observation IDs, corrected fixture identity, terminal semantics, and a Coleman adapter research record.

- [x] **Step 1: Add the in-hand teardown observation**

Use `observations.py add` with `source_type=dataplate_photo`. Record the four photo paths, exact identifiers (`icm:AP7862`, `coleman:7330G335`, `silkscreen:PCB1060`, `silkscreen:SPCB-2`), date code `1203`, terminal order `[R,Y,W,GL,GH,B]`, installed colors `{R:red,Y:yellow,W:white,GL:gray,GH:green,B:blue}`, and the board position labels `{R:W1,Y:W5,W:W6,GL:W3,GH:W4,B:W2}` in the source statement.

- [x] **Step 2: Fetch the service manual as an append-only observation**

Use `observations.py fetch --no-interactive` against `https://myrvworks.com/wp-content/uploads/2019/04/Coleman-Wall-Thermostat.pdf` with `source_type=manufacturer_pdf`. Record document number `1976-376 (4-02)`, the terminal-function map `{R:+12VDC_supply,Y:compressor_control,W:furnace_heat_control,GL:low_fan_control,GH:high_fan_control,B:12VDC_negative_ground}`, the manual's wire-color caveat, and its family-level interchangeability statement.

- [x] **Step 3: Correct the thermostat fixture**

Replace `AP7862-3` with `AP7862` and `PCB1060-4A` with `PCB1060`; remove unproven `AR7815` and `AR7816` from the confirmed identifier list. Preserve `SPCB-2` and `7330G335`. Add in-hand provenance, terminal order, installed colors, and the semantic terminal-function map; remove the completed terminal-mapping TODO and rewrite the note so candidate cross-references are not stated as fact.

- [x] **Step 4: Correct the fixture's candidate relationship**

Do not retain an `alias` edge asserting `AP7862` equals `AR7815`. Represent the existing retailer-only `AR7815`/`7330F3858` claim as an `identifier_equivalence_candidate`, or remove it from confirmed fixture edges and document it in the Coleman vendor note if the fixture vocabulary cannot express candidate identity without contradicting the schema.

- [x] **Step 5: Write `VENDOR-Coleman-Mach.md`**

Document the physical identifiers, date code, terminal order/colors, service-manual functions, the manual's interchangeability statement, the distinction between compatibility and aliasing, all Coleman observation IDs, and remaining candidate crosswalk questions.

- [x] **Step 6: Validate observation vocabulary coverage**

Run: `python3 Docs/Tools/resolver.py --db Docs/Tools/observations.db --validate`

Expected: `ALL KEYS CLASSIFIED`.

---

### Task 3: Refresh stale project documentation

**Files:**
- Modify: `README.md`
- Modify: `Docs/Inital_Design/ARCHITECTURE-Interchange_Core.md`
- Modify: `Docs/Inital_Design/PLAN-Staged_Build.md`
- Modify: `Docs/Tools/TOOLS.md`

**Interfaces:**
- Consumes: repository implementation state and observation count after Task 2.
- Produces: accurate current status and next-action guidance.

- [x] **Step 1: Update the README**

Replace `Pre-implementation. No code written yet.` and the obsolete `Where to start` list with a Stage 1 status summary: evidence store, canonical resolver vocabulary, Suburban parser, SQLite component/edge store, canonical SW6DE/SW6DEL edge, Coleman evidence capture, and the next resolver milestone.

- [x] **Step 2: Update architecture status**

Change `design, pre-implementation` to language stating that the scoped Stage 1 core is implemented while clustering, full-fixture resolution, channel qualifiers, and some typed edge details remain open.

- [x] **Step 3: Update the staged plan**

Use the actual post-capture observation count. Mark the initial Coleman thermostat teardown/manual evidence complete, summarize what it proves, and name the next action as resolving the Coleman compatibility/candidate-crosswalk data into the component/edge store without conflating compatibility with identity.

- [x] **Step 4: Update the tools guide**

Replace the stale observation #3 register TODO with the completed #36/#39 measurement and correction state, and add the Coleman photo/manual observations.

---

### Task 4: Full verification and implementation commit

**Files:**
- Verify all files modified or created in Tasks 1-3.

**Interfaces:**
- Consumes: completed evidence, fixture, vocabulary, research, and documentation updates.
- Produces: a clean, verified implementation commit containing no unrelated files.

- [x] **Step 1: Run all focused and regression checks**

Run:

```bash
cd Docs/Tools
python3 -m unittest -v test_vendor_discovery.py
python3 resolver.py --self-test
python3 resolver.py --db observations.db --validate
python3 suburban_parser.py --self-test
python3 interchange_schema.py --self-test --verbose
python3 interchange_models.py --self-test
python3 interchange_store.py --self-test
python3 edge_resolver.py --self-test
python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml
```

Expected: all unit/self-tests pass, all keys are classified, and the canonical edge fixture reports `0 mismatches`.

- [x] **Step 2: Inspect the evidence and diff**

Run `python3 Docs/Tools/observations.py --db Docs/Tools/observations.db list`, `git diff --check`, `git diff --stat`, and a focused diff of the fixture to confirm no candidate identifier was promoted.

- [x] **Step 3: Commit the complete implementation**

Stage only the files named in this plan and commit with message `Capture Coleman thermostat teardown evidence`.
