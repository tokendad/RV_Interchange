# Suburban Furnace & Cooktop Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Suburban vendor arc with a furnace (`SF-30FQ`) and a cooktop/range
(`SRNA3SBBM`), plus a furnace-core repair part (`2608A`/`RP-30FQ`) with a `fits` edge to the
furnace, backed by in-hand data-plate photos, two manufacturer manuals, one manufacturer
catalog page, and one retailer page — all per
`docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md`.

**Architecture:** Same append-only evidence → resolver → fixture pipeline as every other
vendor arc in this repo. New observations go into `Docs/Tools/observations.db` via the
existing `observations.py` CLI. Two new resolver functions in `Docs/Tools/edge_resolver.py`
build the components/edges from those observations, wired into `check_fixture()`'s existing
per-milestone comparison style. `Docs/Inital_Design/ground-truth.yaml` gets three new
`part_types` rows, three new `components` rows, and one new `edges` row.

**Tech Stack:** Python 3, sqlite3, PyYAML (already a dependency), the repo's existing
`observations.py` / `resolver.py` / `edge_resolver.py` / `interchange_*.py` modules.

## Global Constraints

- Every task must leave `python3 -m pytest tests/ Docs/Tools -q` green before it's done.
- `python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db` must reach `0 total mismatches` by the end of the plan.
- Do not assert furnace/cooktop model-number grammar (letter meanings) — out of scope per the design spec, unchanged by this plan.
- Do not create a `supersedes` edge from `SF-30FQ` toward `SF-30VHFQ`/`SF-30VHQ` — issue #26 closed as resolved "no".
- File the furnace's `cabinet_cutout_h_in`/`cabinet_cutout_w_in` under `secondary_attributes` (not `critical_attributes`) in the `416` part-type row — it's family-level, method-A-specific evidence, not confirmed `SF-30FQ`-specific the way the clearance table is.
- All new SQLite/YAML changes are additive — do not modify any existing observation, part type, component, or edge.

---

### Task 1: Extend the observation vocabulary for furnace/cooktop fields

**Files:**
- Modify: `Docs/Tools/resolver.py`

**Interfaces:**
- Produces: 24 new canonical field names (all simple scalars, `in`/`BTU`/`W.C.` units)
  that Task 3's observations and Task 4/5's resolver functions will read via
  `_normalized_attributes()`. Also reuses 8 existing canonical fields unchanged
  (`model`, `sku`, `skus`→`sku`, `parts`→`repair_part_fitment_table`,
  `identifiers_observed`→`physical_identifiers`, `manufacturer`, `photos`→`source_photos`,
  `quoted_text`→`source_statement`, `input_btuh`, `finding`) — no changes needed to those.

- [ ] **Step 1: Add the new canonical field descriptions**

In `Docs/Tools/resolver.py`, inside the `CANONICAL` dict, add a new section right after the
`"connector_hardware"` line (end of the "electrical interface / compatibility" block, before
the "dimensions" comment block):

```python
    # furnace / cooktop (2026-08-05) — Suburban SF-30FQ furnace and SRNA3SBBM
    # cooktop/range extension. See docs/superpowers/specs/
    # 2026-08-05-suburban-furnace-cooktop-design.md.
    "serial_number":             "manufacturer-assigned serial number physically observed on one in-hand unit",
    "burner_btu_front":          "cooktop front burner rate, BTU/hr",
    "burner_btu_left_rear":      "cooktop left-rear burner rate, BTU/hr",
    "burner_btu_right_rear":     "cooktop right-rear burner rate, BTU/hr",
    "oven_btu":                  "cooktop/range oven rate, BTU/hr",
    "burner_count":              "number of top burners on a cooktop/range",
    "manifold_pressure_wc":      "gas manifold pressure, inches water column",
    "clearance_below_counter_in": "cooktop minimum clearance below the counter, in",
    "clearance_right_sidewall_in": "cooktop minimum clearance to the right sidewall, in",
    "clearance_left_sidewall_in": "cooktop minimum clearance to the left sidewall, in",
    "clearance_backwall_in":     "cooktop minimum clearance to the backwall, in",
    "clearance_vertical_in":     "cooktop minimum vertical clearance to combustible material above the cooking surface, in",
    "cutout_a_in":                "cooktop cabinet cut-out dimension A (manual's own Figure 2 label), in",
    "cutout_b_in":                "cooktop cabinet cut-out dimension B (manual's own Figure 2 label), in",
    "cutout_c_in":                "cooktop cabinet cut-out dimension C (manual's own Figure 2 label), in",
    "cutout_d_in":                "cooktop cabinet cut-out dimension D (manual's own Figure 2 label), in",
    "cutout_e_in":                "cooktop cabinet cut-out dimension E (manual's own Figure 2 label), in",
    "clearance_front_in":        "furnace minimum clearance to the front, in",
    "clearance_left_in":         "furnace minimum clearance to the left side, in",
    "clearance_right_in":        "furnace minimum clearance to the right side, in",
    "clearance_top_in":          "furnace minimum clearance to the top, in",
    "clearance_bottom_in":       "furnace minimum clearance to the bottom, in",
    "clearance_back_in":         "furnace minimum clearance to the back, in",
    "cabinet_cutout_h_in":       "furnace inner-wall cabinet cut-out height, in (method-A install, family-level)",
    "cabinet_cutout_w_in":       "furnace inner-wall cabinet cut-out width, in (method-A install, family-level)",
```

- [ ] **Step 2: Add matching aliases**

In the same file, inside the `ALIASES` dict, add a matching section right after the
`"connector_hardware": "connector_hardware",` line (search for it — it's near the end of the
"electrical interface / compatibility" alias block):

```python
    # furnace / cooktop (2026-08-05)
    "serial_number": "serial_number",
    "burner_btu_front": "burner_btu_front",
    "burner_btu_left_rear": "burner_btu_left_rear",
    "burner_btu_right_rear": "burner_btu_right_rear",
    "oven_btu": "oven_btu",
    "burner_count": "burner_count",
    "manifold_pressure_wc": "manifold_pressure_wc",
    "clearance_below_counter_in": "clearance_below_counter_in",
    "clearance_right_sidewall_in": "clearance_right_sidewall_in",
    "clearance_left_sidewall_in": "clearance_left_sidewall_in",
    "clearance_backwall_in": "clearance_backwall_in",
    "clearance_vertical_in": "clearance_vertical_in",
    "cutout_a_in": "cutout_a_in",
    "cutout_b_in": "cutout_b_in",
    "cutout_c_in": "cutout_c_in",
    "cutout_d_in": "cutout_d_in",
    "cutout_e_in": "cutout_e_in",
    "clearance_front_in": "clearance_front_in",
    "clearance_left_in": "clearance_left_in",
    "clearance_right_in": "clearance_right_in",
    "clearance_top_in": "clearance_top_in",
    "clearance_bottom_in": "clearance_bottom_in",
    "clearance_back_in": "clearance_back_in",
    "cabinet_cutout_h_in": "cabinet_cutout_h_in",
    "cabinet_cutout_w_in": "cabinet_cutout_w_in",
```

- [ ] **Step 3: Verify with a quick inline check**

Run:

```bash
cd /data/Projects/RVInterchange/Docs/Tools && python3 -c "
from resolver import normalize_extracted
sample = {
    'model': 'SF-30FQ',
    'clearance_front_in': 1,
    'cabinet_cutout_h_in': 8,
    'burner_btu_front': 9000,
    'cutout_a_in': 18.625,
    'quoted_text': 'test',
}
result = normalize_extracted(999, sample, strict=True)
assert result['attributes']['clearance_front_in'] == 1
assert result['attributes']['cabinet_cutout_h_in'] == 8
assert result['attributes']['burner_btu_front'] == 9000
assert result['attributes']['cutout_a_in'] == 18.625
print('OK: all new keys classify')
"
```

Expected: `OK: all new keys classify`. If it raises `ValueError: unclassified key(s)`,
re-check Step 1/2's spelling against the sample dict.

- [ ] **Step 4: Run the full test suite**

Run: `cd /data/Projects/RVInterchange && python3 -m pytest tests/ Docs/Tools -q`
Expected: all tests still pass (this task doesn't touch any tested code path directly, but
confirms nothing broke).

- [ ] **Step 5: Commit**

```bash
cd /data/Projects/RVInterchange
git add Docs/Tools/resolver.py
git commit -m "feat: add furnace/cooktop vocabulary to resolver.py"
```

---

### Task 2: Add the three new part types to ground-truth.yaml

**Files:**
- Modify: `Docs/Inital_Design/ground-truth.yaml`

**Interfaces:**
- Produces: part type IDs `416` (furnace), `417` (furnace repair/service part), `601`
  (cooktop/range) that Task 4/5's resolver functions and fixture entries reference.

- [ ] **Step 1: Add the three part_types entries**

In `Docs/Inital_Design/ground-truth.yaml`, inside the `part_types:` list (starts at line 15),
add after the existing `id: 413` entry (the water-heater repair/service part, ends around
line 96, right before the `---` at line 97):

```yaml
  - id: 416
    label: furnace
    compat_mode: attribute
    critical_attributes: [btu_rating, ignition_type, clearance_front_in, clearance_left_in,
                           clearance_right_in, clearance_top_in, clearance_bottom_in,
                           clearance_back_in]
    secondary_attributes: [cabinet_cutout_h_in, cabinet_cutout_w_in]
    tags: [climate, lp_gas, appliance]
    pcdb_term_id: null
    # cabinet_cutout_h/w is SECONDARY: the installation manual states it once for
    # the whole SF-FQ family tied to one installation method (against the outer
    # skin), not confirmed SF-30FQ-specific the way the clearance table is. See
    # docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md sec 3.
    # ignition_type is left unpopulated on SF-30FQ (see that design's sec 4) --
    # the current VH-series is documented as direct-spark, the legacy pre-VH
    # SF-30FQ is not independently confirmed to share it.

  - id: 417
    label: furnace repair/service part
    compat_mode: fits_bracket
    critical_attributes: [description]
    tags: [climate, lp_gas, appliance, repair_part]
    pcdb_term_id: null
    # Mirrors 413 (water heater repair/service part) for the furnace host category.

  - id: 601
    label: cooktop/range
    compat_mode: attribute
    critical_attributes: [burner_count, btu_rating, cutout_a_in, cutout_b_in, cutout_c_in,
                           cutout_d_in, cutout_e_in]
    secondary_attributes: [oven_btu_rating, manifold_pressure_wc, clearance_below_counter_in,
                            clearance_right_sidewall_in, clearance_left_sidewall_in,
                            clearance_backwall_in, clearance_vertical_in]
    tags: [appliance, lp_gas]
    pcdb_term_id: null
    # cutout_a..e_in are the manual's own Figure 2 dimension labels, recorded
    # without further interpretation. First part type in the "appliances" (600s)
    # block per ARCHITECTURE-Interchange_Core.md sec 6.
```

- [ ] **Step 2: Verify the YAML still parses**

Run:

```bash
cd /data/Projects/RVInterchange && python3 -c "
import yaml
docs = [d for d in yaml.safe_load_all(open('Docs/Inital_Design/ground-truth.yaml')) if d]
part_types = next(d['part_types'] for d in docs if 'part_types' in d)
ids = {p['id'] for p in part_types}
assert {416, 417, 601}.issubset(ids), ids
print('OK: part types 416/417/601 present')
"
```

Expected: `OK: part types 416/417/601 present`.

- [ ] **Step 3: Commit**

```bash
git add Docs/Inital_Design/ground-truth.yaml
git commit -m "feat: add furnace, furnace repair-part, and cooktop part types"
```

---

### Task 3: Add the seven new observations

**Files:**
- None (operates directly on `Docs/Tools/observations.db` via the `observations.py` CLI —
  gitignored, not a tracked file).

**Interfaces:**
- Produces: observations `#97`–`#103` (IDs are sequential from the current max of `#96` —
  confirm each printed ID matches before moving on; if `observations.db` has gained rows
  from other work in the meantime, the actual IDs will differ and every reference to
  `97`–`103` in Tasks 4–5 must be updated to match), each with `source_tier` populated by
  Step 8 (`97`/`98`/`99` → `2`, `100`/`101`/`102` → `1`, `103` → `7`) — Tasks 4–5's
  `_validate_observation_source()` calls check these exact tiers.

- [ ] **Step 1: Insert observation #97 — furnace data plate photo**

```bash
cd /data/Projects/RVInterchange/Docs/Tools
python3 observations.py add \
  --source-type dataplate_photo \
  --extraction-method hand_typed \
  --source-name "in-hand data plate photo, Suburban SF-30FQ furnace (owner's coach)" \
  --extracted '{"model": "SF-30FQ", "sku": "2391", "serial_number": "122103492", "photos": ["Docs/Data/Current RV - DO NOT COMMIT THIS FOLDER/Furnace/20260805_124128.jpg"], "quoted_text": "Model No. SF-30FQ, Stock No. 2391, Serial No./Numero de Serie 122103492"}'
```

Expected output: `Inserted observation #97`. If a different number prints, use that number
in place of `97` everywhere below.

- [ ] **Step 2: Insert observation #98 — cooktop data plate / burner-rate photo**

```bash
python3 observations.py add \
  --source-type dataplate_photo \
  --extraction-method hand_typed \
  --source-name "in-hand data plate photo, Suburban SRNA3SBBM cooktop/range (owner's coach) -- model/serial/burner-rate block" \
  --extracted '{"model": "SRNA3SBBM", "sku": "2863", "serial_number": "122109479", "burner_btu_front": 9000, "burner_btu_left_rear": 6500, "burner_btu_right_rear": 6500, "oven_btu": 7100, "manifold_pressure_wc": 10.0, "photos": ["Docs/Data/Current RV - DO NOT COMMIT THIS FOLDER/Stove/20260805_124807.jpg"], "quoted_text": "Model No./Numero de Modele SRNA3SBBM, Serial No./Numero de Serie 122109479, Stock No. 2863, Burner Rate/Puissance Nominal: Front 9,000 BTU, Left Rear 6,500 BTU, Right Rear 6,500 BTU, Oven 7,100 BTU, Manifold Pressure 10.0 in W.C."}'
```

Expected: `Inserted observation #98`.

- [ ] **Step 3: Insert observation #99 — cooktop clearance/lighting plate photo**

```bash
python3 observations.py add \
  --source-type dataplate_photo \
  --extraction-method hand_typed \
  --source-name "in-hand data plate photo, Suburban SRNA3SBBM cooktop/range (owner's coach) -- clearance/lighting instructions plate" \
  --extracted '{"clearance_below_counter_in": 0, "clearance_right_sidewall_in": 6, "clearance_left_sidewall_in": 6, "clearance_backwall_in": 9, "clearance_vertical_in": 24, "manufacturer": "Suburban Manufacturing Company (Airxcel)", "photos": ["Docs/Data/Current RV - DO NOT COMMIT THIS FOLDER/Stove/20260805_124815.jpg"], "quoted_text": "Minimum Clearance From Combustible Walls Above and Below Counter: Below Counter 0in, Right Sidewall 6in, Left Sidewall 6in, Backwall 9in. Minimum Vertical Clearance To Combustible Surface When Over Cooktop 24in. AIRXCEL."}'
```

Expected: `Inserted observation #99`.

- [ ] **Step 4: Insert observation #100 — Suburban 2025 catalog, furnace core module section**

```bash
python3 observations.py add \
  --source-type manufacturer_pdf \
  --extraction-method script \
  --source-name "Suburban 2025 Catalogue (Catalogue_2025.pdf) -- Furnace Core Replacement Modules section" \
  --raw-file "../Data/Suburban/Catalogue_2025.pdf" \
  --extracted '{"doc": "Suburban 2025 Catalogue, FURNACE CORE REPLACEMENT MODULES and SF-Q/SF-FQ SERIES sections", "publisher": "Suburban Manufacturing Company / Airxcel, Inc.", "parts": {"2608A": {"description": "Furnace Core Replacement Module", "applies_to": ["SF-25FQ", "SF-30FQ"]}}, "input_btuh": 30000, "quoted_text": "FOR SF-25FQ / SF-30FQ ORDER 2608A. SF-Q SERIES: 2577A SF-30VHQ, 30,000 BTU/h. SF-FQ SERIES: 2576A SF-30VHFQ, 30,000 BTU/h."}'
```

If `--raw-file` fails because the PDF isn't plain text (it's a binary PDF), omit it and
insert without raw content instead:

```bash
python3 observations.py add \
  --source-type manufacturer_pdf \
  --extraction-method script \
  --source-name "Suburban 2025 Catalogue (Catalogue_2025.pdf) -- Furnace Core Replacement Modules section" \
  --extracted '{"doc": "Suburban 2025 Catalogue, FURNACE CORE REPLACEMENT MODULES and SF-Q/SF-FQ SERIES sections", "publisher": "Suburban Manufacturing Company / Airxcel, Inc.", "parts": {"2608A": {"description": "Furnace Core Replacement Module", "applies_to": ["SF-25FQ", "SF-30FQ"]}}, "input_btuh": 30000, "quoted_text": "FOR SF-25FQ / SF-30FQ ORDER 2608A. SF-Q SERIES: 2577A SF-30VHQ, 30,000 BTU/h. SF-FQ SERIES: 2576A SF-30VHFQ, 30,000 BTU/h."}'
```

Expected: `Inserted observation #100`.

- [ ] **Step 5: Insert observation #101 — furnace installation manual**

```bash
python3 observations.py add \
  --source-type manufacturer_pdf \
  --extraction-method script \
  --source-name "Suburban Gas Furnaces Installation Instructions, SF-20FQ/25FQ/30FQ/35FQ/42FQ, Part Number 205170 -- confirmed by owner as matching in-hand unit" \
  --extracted '{"doc": "Suburban Gas Furnaces Installation Instructions for SF-20FQ, SF-25FQ, SF-30FQ, SF-35FQ, SF-42FQ, Part Number 205170", "publisher": "Airxcel, Inc. -- Suburban Division", "model": "SF-30FQ", "clearance_front_in": 1, "clearance_left_in": 0, "clearance_right_in": 0, "clearance_top_in": 0, "clearance_bottom_in": 0, "clearance_back_in": 0, "cabinet_cutout_h_in": 8, "cabinet_cutout_w_in": 17.75, "quoted_text": "Table 2, SF-30FQ row: Front 1in, Left Side 0in, Right Side 0in, Top 0in, Bottom 0in, Back 0in, Exhaust and Intake Tube 3/8in. Cut an opening through the inner wall 17-3/4 x 8in."}'
```

Expected: `Inserted observation #101`.

- [ ] **Step 6: Insert observation #102 — cooktop/range installation manual**

```bash
python3 observations.py add \
  --source-type manufacturer_pdf \
  --extraction-method script \
  --source-name "Suburban Range and Cooktops Installation, Operation and Service Manual -- All SRNA3/SRSA3 Model Variations -- confirmed by owner as matching in-hand unit" \
  --extracted '{"doc": "Recreational Vehicle Range and Cooktops Installation, Operation and Service Manual, All SRNA3 and SRSA3 Model Variations", "publisher": "Suburban Manufacturing Company", "clearance_below_counter_in": 0, "clearance_right_sidewall_in": 6, "clearance_left_sidewall_in": 6, "clearance_backwall_in": 9, "clearance_vertical_in": 24, "cutout_a_in": 18.625, "cutout_b_in": 16, "cutout_c_in": 2, "cutout_d_in": 20.625, "cutout_e_in": 0.875, "quoted_text": "SRNA3/SRSA3 clearance row: Below Counter 0in, Right Sidewall 6in, Left Sidewall 6in, Backwall 9in. SRNA3S/SRSA3S cut-out dimensions (Figure 2): A 18-5/8in, B 16in, C 2in, D 20-5/8in, E 7/8in. Minimum vertical clearance 24in, reducible to 19-1/2in with range hood."}'
```

Expected: `Inserted observation #102`.

- [ ] **Step 7: Insert observation #103 — retailer corroboration and supersession-absence check**

```bash
python3 observations.py add \
  --source-type retailer_page \
  --extraction-method hand_typed \
  --source-name "unitedrvparts.com -- Suburban SF-30FQ, SF-30VHFQ, and SF-30VHQ furnace product pages" \
  --url "https://unitedrvparts.com/products/suburban-30-000-btu-furnace-sf-30fq-2518a" \
  --extracted '{"model": "SF-30FQ", "skus": ["2518A", "2391A", "2558A"], "parts": {"2608A": {"description": "Furnace Core Replacement Module", "applies_to": ["SF-30FQ"]}}, "identifiers_observed": [{"ns": "suburban", "value": "RP-30FQ", "visibility": null}], "finding": "Neither the SF-30VHFQ (2576J/2576A) nor the SF-30VHQ (2577A) product pages on this same retailer state a supersession/replacement relationship toward SF-30FQ. This retailer explicitly uses Superseded from 2563A language elsewhere (its SF-35VHFQ 2587A listing) when a real supersession exists, so the absence here is evidence the manufacturer has not declared one -- not just missing data.", "quoted_text": "SF-30FQ | 2391 | Stock# 2608A, Model# RP-30FQ. OEM numbers: 2518A, 2391A, 2558A."}'
```

Expected: `Inserted observation #103`.

- [ ] **Step 8: Assign source tiers to the new observations**

`observations.py add` never sets `source_tier` (it stays `NULL` until a separate pass
computes it) — this step is required, not optional, or every `_validate_observation_source`
call in Tasks 4–5 will see `source_tier=None` and reject the observation.

Run: `python3 resolver.py --assign-tiers --db observations.db`
Expected: output lists `obs #97: source_tier None -> 2 ...` through `obs #103: source_tier
None -> 7 ...` (or similar) — specifically: `97`/`98`/`99` → tier `2`, `100`/`101`/`102` →
tier `1`, `103` → tier `7`. If any of these three groups shows a different number, the
`--extraction-method` passed in Steps 1–7 doesn't match what was intended — fix it with a
direct `UPDATE observations SET extraction_method = ... WHERE id = ...` and re-run
`--assign-tiers`, since observations are otherwise append-only (don't re-insert a duplicate
row).

- [ ] **Step 9: Validate every new observation classifies cleanly**

Run: `python3 resolver.py --validate observations.db`
Expected: exit code 0, no `unclassified key` errors mentioning observations 97–103. If it
fails, re-check Task 1's `ALIASES`/`CANONICAL` spelling against the exact keys used above.

- [ ] **Step 10: Spot-check one observation's normalized view and its tier**

Run: `python3 resolver.py --show 101 --db observations.db`
Expected: prints observation #101 with `clearance_front_in: 1` (etc.) visible in its
normalized fields, not an error.

Run: `python3 -c "
import sqlite3
conn = sqlite3.connect('observations.db')
rows = conn.execute('SELECT id, source_tier FROM observations WHERE id BETWEEN 97 AND 103').fetchall()
print(rows)
"`
Expected: `[(97, 2), (98, 2), (99, 2), (100, 1), (101, 1), (102, 1), (103, 7)]`.

No commit for this task — `observations.db` is gitignored (append-only evidence store, not
tracked in git, same as every other vendor arc's observations).

---

### Task 4: Furnace and cooktop identity components

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`
- Modify: `Docs/Inital_Design/ground-truth.yaml`

**Interfaces:**
- Consumes: observations `#97` (furnace dataplate), `#98`/`#99` (cooktop dataplates),
  `#100` (catalog, for `input_btuh`), `#101` (furnace manual), `#102` (cooktop manual) —
  from Task 3.
- Produces: `suburban_furnace_cooktop_components(furnace_dataplate_row, furnace_manual_row,
  catalog_row, cooktop_dataplate_row, cooktop_clearance_row, cooktop_manual_row,
  component_ids) -> list[tuple[Component, list[Identifier], list[ComponentAttribute]]]`,
  matching `atwood_endpoint_components()`'s shape (`Docs/Tools/edge_resolver.py:985`) —
  Task 5 inserts the returned components/identifiers/attributes into `conn` the same way
  `check_fixture()` already does for Atwood endpoints (`Docs/Tools/edge_resolver.py:3397`-`3403`).

- [ ] **Step 1: Add the new constants**

In `Docs/Tools/edge_resolver.py`, after the existing `ATWOOD_ELECTRONIC_PARTS_TARGET_MODELS`
tuple (ends around line 63), add:

```python
SUBURBAN_FURNACE_PART_TYPE = 416
SUBURBAN_FURNACE_REPAIR_PART_TYPE = 417
SUBURBAN_COOKTOP_PART_TYPE = 601
SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION = "suburban_furnace_cooktop_v1"
```

- [ ] **Step 2: Write the identity-component builder function**

Add this function right after `atwood_electronic_repair_parts_and_fits()` (search for its
closing `return results` — the function ends around line 1250, just before the next `def`):

```python
def suburban_furnace_cooktop_components(furnace_dataplate_row, furnace_manual_row,
                                         catalog_row, cooktop_dataplate_row,
                                         cooktop_clearance_row, cooktop_manual_row,
                                         component_ids):
    """
    Build the Suburban SF-30FQ furnace and SRNA3SBBM cooktop/range as exact
    endpoint components -- the owner's current-coach in-hand data plates
    (obs #97/#98/#99), cross-checked against matching manufacturer
    installation manuals the owner confirmed match their units (obs
    #101/#102), plus the 2025 catalog's parallel SF-30VHFQ/SF-30VHQ BTU
    listing (obs #100) for the furnace's btu_rating -- this unit's own plate
    does not print a BTU figure the way the cooktop's does, so that one
    attribute is provenance-flagged as inferred, not read. See
    docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md.

    No `conn` argument: like atwood_endpoint_components(), this only builds
    and returns data -- the caller inserts it and, separately, calls
    suburban_furnace_core_module() (which DOES take conn, because it also
    creates the fits edge) to build the repair part.
    """
    _validate_observation_source(furnace_dataplate_row, 97, "dataplate_photo", 2,
                                  "furnace dataplate")
    _validate_observation_source(furnace_manual_row, 101, "manufacturer_pdf", 1,
                                  "furnace installation manual")
    _validate_observation_source(catalog_row, 100, "manufacturer_pdf", 1,
                                  "furnace core module catalog")
    _validate_observation_source(cooktop_dataplate_row, 98, "dataplate_photo", 2,
                                  "cooktop dataplate")
    _validate_observation_source(cooktop_clearance_row, 99, "dataplate_photo", 2,
                                  "cooktop clearance dataplate")
    _validate_observation_source(cooktop_manual_row, 102, "manufacturer_pdf", 1,
                                  "cooktop installation manual")

    furnace_plate = _normalized_attributes(furnace_dataplate_row)
    if furnace_plate.get("model") != "SF-30FQ":
        raise ValueError(f"unexpected furnace dataplate model: {furnace_plate.get('model')}")
    furnace_manual = _normalized_attributes(furnace_manual_row)
    if furnace_manual.get("model") != "SF-30FQ":
        raise ValueError(f"unexpected furnace manual model: {furnace_manual.get('model')}")
    catalog = _normalized_attributes(catalog_row)
    fitment = catalog.get("repair_part_fitment_table")
    if not isinstance(fitment, dict) or "2608A" not in fitment:
        raise ValueError(f"catalog observation missing 2608A fitment row: {fitment}")
    applies_to = fitment["2608A"].get("applies_to")
    if set(applies_to or []) != {"SF-25FQ", "SF-30FQ"}:
        raise ValueError(
            f"2608A must apply to exactly SF-25FQ and SF-30FQ, got: {applies_to}")

    cooktop_plate = _normalized_attributes(cooktop_dataplate_row)
    if cooktop_plate.get("model") != "SRNA3SBBM":
        raise ValueError(f"unexpected cooktop dataplate model: {cooktop_plate.get('model')}")
    cooktop_clearance = _normalized_attributes(cooktop_clearance_row)
    cooktop_manual = _normalized_attributes(cooktop_manual_row)

    def text_attr(component_id, name, value, source_row, provenance="manufacturer_pdf"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)

    def number_attr(component_id, name, value, source_row, unit=None,
                     provenance="manufacturer_pdf"):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_number=value,
            unit=unit, resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)

    furnace_id = component_ids["furnace"]
    furnace = Component(furnace_id, SUBURBAN_FURNACE_PART_TYPE, None)
    furnace_identifiers = [Identifier(furnace_id, "suburban", "SF-30FQ", "exterior_plate")]
    furnace_attributes = [
        number_attr(furnace_id, "btu_rating", float(catalog["input_btuh"]), catalog_row,
                    unit="BTU/h", provenance="manufacturer_pdf_inferred"),
        text_attr(furnace_id, "stock_no", furnace_plate["sku"], furnace_dataplate_row,
                   provenance="dataplate_photo"),
        text_attr(furnace_id, "serial", furnace_plate["serial_number"], furnace_dataplate_row,
                   provenance="dataplate_photo"),
    ]
    for name in ("clearance_front_in", "clearance_left_in", "clearance_right_in",
                 "clearance_top_in", "clearance_bottom_in", "clearance_back_in"):
        furnace_attributes.append(
            number_attr(furnace_id, name, float(furnace_manual[name]), furnace_manual_row,
                        unit="in"))
    furnace_attributes.append(number_attr(
        furnace_id, "cabinet_cutout_h_in", float(furnace_manual["cabinet_cutout_h_in"]),
        furnace_manual_row, unit="in"))
    furnace_attributes.append(number_attr(
        furnace_id, "cabinet_cutout_w_in", float(furnace_manual["cabinet_cutout_w_in"]),
        furnace_manual_row, unit="in"))

    cooktop_id = component_ids["cooktop"]
    cooktop = Component(cooktop_id, SUBURBAN_COOKTOP_PART_TYPE, None)
    cooktop_identifiers = [Identifier(cooktop_id, "suburban", "SRNA3SBBM", "exterior_plate")]
    cooktop_attributes = [
        number_attr(cooktop_id, "burner_count", 3.0, cooktop_dataplate_row,
                    provenance="dataplate_photo"),
        number_attr(cooktop_id, "btu_rating", float(cooktop_plate["burner_btu_front"]),
                    cooktop_dataplate_row, unit="BTU/h", provenance="dataplate_photo"),
        number_attr(cooktop_id, "oven_btu_rating", float(cooktop_plate["oven_btu"]),
                    cooktop_dataplate_row, unit="BTU/h", provenance="dataplate_photo"),
        number_attr(cooktop_id, "manifold_pressure_wc",
                    float(cooktop_plate["manifold_pressure_wc"]), cooktop_dataplate_row,
                    unit="in_wc", provenance="dataplate_photo"),
        text_attr(cooktop_id, "stock_no", cooktop_plate["sku"], cooktop_dataplate_row,
                   provenance="dataplate_photo"),
        text_attr(cooktop_id, "serial", cooktop_plate["serial_number"], cooktop_dataplate_row,
                   provenance="dataplate_photo"),
    ]
    for name in ("clearance_below_counter_in", "clearance_right_sidewall_in",
                 "clearance_left_sidewall_in", "clearance_backwall_in", "clearance_vertical_in"):
        cooktop_attributes.append(
            number_attr(cooktop_id, name, float(cooktop_clearance[name]), cooktop_clearance_row,
                        unit="in", provenance="dataplate_photo"))
    for name in ("cutout_a_in", "cutout_b_in", "cutout_c_in", "cutout_d_in", "cutout_e_in"):
        cooktop_attributes.append(
            number_attr(cooktop_id, name, float(cooktop_manual[name]), cooktop_manual_row,
                        unit="in"))

    return [
        (furnace, furnace_identifiers, furnace_attributes),
        (cooktop, cooktop_identifiers, cooktop_attributes),
    ]
```

- [ ] **Step 3: Add the fixture entries to ground-truth.yaml**

In `Docs/Inital_Design/ground-truth.yaml`, inside the `components:` list, add two new
entries. Place them right after the last Atwood endpoint component (search for
`c_placeholder_wh_atwood_gc10a_4e` or similar — the last one before the `---` separator at
line 855):

```yaml
  - component_id: c_placeholder_furnace_sf30fq
    part_type_id: 416
    interchange_code: null
    identifiers:
      - {ns: suburban, value: "SF-30FQ", visibility: exterior_plate}
    attributes:
      btu_rating:          {value: 30000, unit: "BTU/h", provenance: manufacturer_pdf_inferred, source_observation_id: 100}
      stock_no:             {value: "2391", provenance: dataplate_photo, source_observation_id: 97}
      serial:                {value: "122103492", provenance: dataplate_photo, source_observation_id: 97}
      clearance_front_in:   {value: 1, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      clearance_left_in:    {value: 0, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      clearance_right_in:   {value: 0, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      clearance_top_in:     {value: 0, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      clearance_bottom_in:  {value: 0, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      clearance_back_in:    {value: 0, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      cabinet_cutout_h_in:  {value: 8, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}
      cabinet_cutout_w_in:  {value: 17.75, unit: in, provenance: manufacturer_pdf, source_observation_id: 101}

  - component_id: c_placeholder_cooktop_srna3sbbm
    part_type_id: 601
    interchange_code: null
    identifiers:
      - {ns: suburban, value: "SRNA3SBBM", visibility: exterior_plate}
    attributes:
      burner_count:                 {value: 3, provenance: dataplate_photo, source_observation_id: 98}
      btu_rating:                   {value: 9000, unit: "BTU/h", provenance: dataplate_photo, source_observation_id: 98}
      oven_btu_rating:              {value: 7100, unit: "BTU/h", provenance: dataplate_photo, source_observation_id: 98}
      manifold_pressure_wc:         {value: 10.0, unit: in_wc, provenance: dataplate_photo, source_observation_id: 98}
      stock_no:                     {value: "2863", provenance: dataplate_photo, source_observation_id: 98}
      serial:                        {value: "122109479", provenance: dataplate_photo, source_observation_id: 98}
      clearance_below_counter_in:   {value: 0, unit: in, provenance: dataplate_photo, source_observation_id: 99}
      clearance_right_sidewall_in:  {value: 6, unit: in, provenance: dataplate_photo, source_observation_id: 99}
      clearance_left_sidewall_in:   {value: 6, unit: in, provenance: dataplate_photo, source_observation_id: 99}
      clearance_backwall_in:        {value: 9, unit: in, provenance: dataplate_photo, source_observation_id: 99}
      clearance_vertical_in:        {value: 24, unit: in, provenance: dataplate_photo, source_observation_id: 99}
      cutout_a_in:                  {value: 18.625, unit: in, provenance: manufacturer_pdf, source_observation_id: 102}
      cutout_b_in:                  {value: 16, unit: in, provenance: manufacturer_pdf, source_observation_id: 102}
      cutout_c_in:                  {value: 2, unit: in, provenance: manufacturer_pdf, source_observation_id: 102}
      cutout_d_in:                  {value: 20.625, unit: in, provenance: manufacturer_pdf, source_observation_id: 102}
      cutout_e_in:                  {value: 0.875, unit: in, provenance: manufacturer_pdf, source_observation_id: 102}
```

- [ ] **Step 4: Wire the builder into check_fixture()**

In `Docs/Tools/edge_resolver.py`, inside `check_fixture()`, find the `print(f"Atwood
endpoints: ...")` line (around line 3545 — it's right after the Atwood electronic repair
parts block). Insert this block immediately after that print statement:

```python
    suburban_furnace_cooktop_mismatches_before = mismatches
    obs97 = load_observation(obs_db_path, 97)
    obs98 = load_observation(obs_db_path, 98)
    obs99 = load_observation(obs_db_path, 99)
    obs100 = load_observation(obs_db_path, 100)
    obs101 = load_observation(obs_db_path, 101)
    obs102 = load_observation(obs_db_path, 102)
    suburban_furnace_cooktop_ids = {
        "furnace": "c_placeholder_furnace_sf30fq",
        "cooktop": "c_placeholder_cooktop_srna3sbbm",
    }
    suburban_furnace_cooktop = suburban_furnace_cooktop_components(
        obs97, obs101, obs100, obs98, obs99, obs102, suburban_furnace_cooktop_ids)
    for component, identifiers, attributes in suburban_furnace_cooktop:
        insert_component(conn, component)
        for identifier in identifiers:
            insert_identifier(conn, identifier)
        for attribute in attributes:
            insert_component_attribute(conn, attribute)

    for component_id in suburban_furnace_cooktop_ids.values():
        fixture_component = next(
            (c for c in components_doc if c.get("component_id") == component_id), None)
        if fixture_component is None:
            print(f"MISMATCH fixture is missing component: {component_id}")
            mismatches += 1
            continue
        resolved_component = conn.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)).fetchone()
        if (resolved_component["part_type_id"], resolved_component["interchange_code"]) != (
                fixture_component["part_type_id"], fixture_component["interchange_code"]):
            print(f"MISMATCH Suburban furnace/cooktop component: "
                  f"resolved={dict(resolved_component)} fixture={fixture_component}")
            mismatches += 1

        resolved_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                (component_id,)).fetchall()
        }
        expected_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_component["identifiers"]
        }
        if resolved_identifiers != expected_identifiers:
            print(f"MISMATCH Suburban furnace/cooktop identifiers for {component_id}: "
                  f"resolved={resolved_identifiers} fixture={expected_identifiers}")
            mismatches += 1

        resolved_attribute_rows = get_component_attributes(conn, component_id)
        resolved_attributes = {}
        for attribute in resolved_attribute_rows:
            value = attribute.value_text if attribute.value_text is not None else (
                attribute.value_number if attribute.value_number is not None
                else attribute.value_boolean)
            resolved_attributes[attribute.name] = (
                value, attribute.provenance, attribute.source_observation_id)
        expected_attributes = {
            name: (definition["value"], definition["provenance"],
                   definition["source_observation_id"])
            for name, definition in fixture_component["attributes"].items()
        }
        if (len(resolved_attribute_rows) != len(expected_attributes)
                or resolved_attributes != expected_attributes):
            print(f"MISMATCH Suburban furnace/cooktop attributes for {component_id}: "
                  f"resolved={resolved_attributes} fixture={expected_attributes}")
            mismatches += 1

    print(f"Suburban furnace/cooktop endpoints: "
          f"{mismatches - suburban_furnace_cooktop_mismatches_before} mismatch(es)")
```

- [ ] **Step 5: Run the fixture check**

Run:
```bash
cd /data/Projects/RVInterchange
python3 Docs/Tools/edge_resolver.py --check-fixture Docs/Inital_Design/ground-truth.yaml
```
Expected: `Suburban furnace/cooktop endpoints: 0 mismatch(es)` in the output, and the final
`N total mismatches` line unchanged from before this task except for this new line (Task 5
still needs the core-module/fits edge, so a nonzero total is still expected at this point —
just confirm this task's own line is `0 mismatch(es)`).

- [ ] **Step 6: Run the full test suite**

Run: `python3 -m pytest tests/ Docs/Tools -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add Docs/Tools/edge_resolver.py Docs/Inital_Design/ground-truth.yaml
git commit -m "feat: build SF-30FQ furnace and SRNA3SBBM cooktop endpoint components"
```

---

### Task 5: Furnace core-module repair part and its `fits` edge

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`
- Modify: `Docs/Inital_Design/ground-truth.yaml`

**Interfaces:**
- Consumes: `SUBURBAN_FURNACE_PART_TYPE`, `SUBURBAN_FURNACE_REPAIR_PART_TYPE`,
  `SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION` from Task 4. Consumes observation `#100`
  (catalog) and `#103` (retailer) from Task 3. Consumes `c_placeholder_furnace_sf30fq`'s
  component ID from Task 4.
- Produces: `suburban_furnace_core_module(conn, catalog_row, retailer_row,
  furnace_component_id) -> tuple[Component, list[Identifier], list[ComponentAttribute],
  list[int]]` — same 4-tuple-with-edge-ids shape as
  `atwood_repair_parts_and_fits()`'s per-part result, but for a single part (this function
  inserts its own component/identifiers/attributes/edge/evidence via `conn`, unlike Task 4's
  builder).

- [ ] **Step 1: Write the core-module builder function**

Add this function immediately after `suburban_furnace_cooktop_components()` (Task 4, Step 2):

```python
def suburban_furnace_core_module(conn, catalog_row, retailer_row, furnace_component_id):
    """
    Build the Suburban 2608A furnace core replacement module and its `fits`
    edge to SF-30FQ -- a single-part case of the same many-to-many "fits"
    relationship Atwood's repair-parts tables use (see
    atwood_repair_parts_and_fits()'s docstring), sourced to the 2025 catalog
    (obs #100, manufacturer-primary) and independently corroborated by a
    retailer page (obs #103) that also supplies the core module's own model
    designation, RP-30FQ, not present in the catalog. See
    docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md
    sec 2/4/5.
    """
    _validate_observation_source(catalog_row, 100, "manufacturer_pdf", 1,
                                  "furnace core module catalog")
    _validate_observation_source(retailer_row, 103, "retailer_page", 7,
                                  "furnace core module retailer")

    catalog = _normalized_attributes(catalog_row)
    fitment = catalog.get("repair_part_fitment_table", {}).get("2608A")
    if fitment is None or set(fitment.get("applies_to", [])) != {"SF-25FQ", "SF-30FQ"}:
        raise ValueError(f"unexpected 2608A catalog fitment: {fitment}")

    retailer = _normalized_attributes(retailer_row)
    retailer_fitment = retailer.get("repair_part_fitment_table", {}).get("2608A")
    if retailer_fitment is None or "SF-30FQ" not in retailer_fitment.get("applies_to", []):
        raise ValueError(f"retailer observation does not corroborate 2608A/SF-30FQ: "
                          f"{retailer_fitment}")
    retailer_identifiers = retailer.get("physical_identifiers", [])
    rp_30fq = next(
        (i for i in retailer_identifiers if i.get("ns") == "suburban"
         and i.get("value") == "RP-30FQ"), None)
    if rp_30fq is None:
        raise ValueError(f"retailer observation missing RP-30FQ identifier: "
                          f"{retailer_identifiers}")

    component_id = "c_placeholder_furnace_part_2608a"
    component = Component(component_id, SUBURBAN_FURNACE_REPAIR_PART_TYPE, None)
    identifiers = [
        Identifier(component_id, "suburban", "2608A", "catalog"),
        Identifier(component_id, "suburban", "RP-30FQ", "retailer_page"),
    ]
    attributes = [ComponentAttribute(
        component_id, "description", "manufacturer_pdf", catalog_row["id"],
        value_text=fitment["description"],
        resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION)]

    insert_component(conn, component)
    for identifier in identifiers:
        insert_identifier(conn, identifier)
    for attribute in attributes:
        insert_component_attribute(conn, attribute)

    edge = Edge(
        type=EDGE_TYPE_FITS,
        from_component_id=component_id,
        to_component_id=furnace_component_id,
        group_key="suburban_furnace_core_module",
        status="candidate",
        resolver_version=SUBURBAN_FURNACE_COOKTOP_RESOLVER_VERSION,
        notes="Suburban's 2025 catalog names 2608A as the furnace core replacement "
              "module for SF-25FQ and SF-30FQ; unitedrvparts.com independently "
              "corroborates the SF-30FQ/2608A pairing and supplies the module's own "
              "model designation, RP-30FQ.",
    )
    insert_edge(conn, edge)
    for event_type, alpha, beta, source_id in (
        ("attribute_prior", 1.0, 1.0, None),
        ("manufacturer_assertion", 2.0, 0.0, catalog_row["id"]),
        ("retailer_cross_reference", 1.0, 0.0, retailer_row["id"]),
    ):
        insert_evidence(conn, RelationshipEvidence(
            edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
            effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))

    return component, identifiers, attributes, [edge.id]
```

- [ ] **Step 2: Add the fixture entries to ground-truth.yaml**

Add the component entry right after the two entries added in Task 4, Step 3:

```yaml
  - component_id: c_placeholder_furnace_part_2608a
    part_type_id: 417
    interchange_code: null
    identifiers:
      - {ns: suburban, value: "2608A", visibility: catalog}
      - {ns: suburban, value: "RP-30FQ", visibility: retailer_page}
    attributes:
      description: {value: "Furnace Core Replacement Module", provenance: manufacturer_pdf, source_observation_id: 100}
```

Add the edge entry to the `edges:` list (starts at line 857), right after the last
`type: controls` or `type: supersedes` entry (any position in that list is fine — it's
matched by `type`+`group` in Step 4 below, not by list position):

```yaml
  - type: fits
    from: c_placeholder_furnace_part_2608a
    to: c_placeholder_furnace_sf30fq
    group: suburban_furnace_core_module
    status: candidate
    confidence: {alpha: 4, beta: 1, value: 0.8, certainty: 5}
    evidence:
      - {event_type: attribute_prior, alpha: 1, beta: 1, source_observation_id: null}
      - {event_type: manufacturer_assertion, alpha: 2, beta: 0, source_observation_id: 100}
      - {event_type: retailer_cross_reference, alpha: 1, beta: 0, source_observation_id: 103}
```

- [ ] **Step 3: Wire the builder into check_fixture()**

Immediately after Task 4 Step 4's new block (right after its
`print(f"Suburban furnace/cooktop endpoints: ...")` line), add:

```python
    obs103 = load_observation(obs_db_path, 103)
    core_module, core_ids, core_attrs, core_edge_ids = suburban_furnace_core_module(
        conn, obs100, obs103, suburban_furnace_cooktop_ids["furnace"])

    fixture_core_module = next(
        (c for c in components_doc
         if c.get("component_id") == "c_placeholder_furnace_part_2608a"), None)
    if fixture_core_module is None:
        print("MISMATCH fixture is missing component: c_placeholder_furnace_part_2608a")
        mismatches += 1
    else:
        resolved_core_identifiers = {
            (row["ns"], row["value"], row["visibility"])
            for row in conn.execute(
                "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
                ("c_placeholder_furnace_part_2608a",)).fetchall()
        }
        expected_core_identifiers = {
            (i["ns"], str(i["value"]), i.get("visibility"))
            for i in fixture_core_module["identifiers"]
        }
        if resolved_core_identifiers != expected_core_identifiers:
            print(f"MISMATCH 2608A identifiers: resolved={resolved_core_identifiers} "
                  f"fixture={expected_core_identifiers}")
            mismatches += 1

    fixture_fits_edge = next(
        (e for e in edges_doc if e.get("type") == "fits"
         and e.get("group") == "suburban_furnace_core_module"), None)
    if fixture_fits_edge is None:
        print("MISMATCH ground-truth.yaml has no suburban_furnace_core_module fits edge")
        mismatches += 1
    else:
        edge_row = conn.execute(
            "SELECT type, from_component_id, to_component_id FROM edges WHERE id = ?",
            (core_edge_ids[0],)).fetchone()
        if tuple(edge_row) != (
                "fits", fixture_fits_edge["from"], fixture_fits_edge["to"]):
            print(f"MISMATCH 2608A fits edge: resolved={tuple(edge_row)} "
                  f"fixture=({fixture_fits_edge['type']}, {fixture_fits_edge['from']}, "
                  f"{fixture_fits_edge['to']})")
            mismatches += 1
        resolved_value = compute_confidence(get_evidence_for_edge(conn, core_edge_ids[0]))["value"]
        if round(resolved_value, 3) != fixture_fits_edge["confidence"]["value"]:
            print(f"MISMATCH 2608A fits edge confidence: resolved={resolved_value} "
                  f"fixture={fixture_fits_edge['confidence']['value']}")
            mismatches += 1

    print(f"Suburban furnace core module: "
          f"{mismatches - suburban_furnace_cooktop_mismatches_before} "
          f"mismatch(es) (cumulative with furnace/cooktop endpoints above)")
```

- [ ] **Step 4: Run the fixture check**

Run: `python3 Docs/Tools/edge_resolver.py --check-fixture Docs/Inital_Design/ground-truth.yaml`
Expected: `0 total mismatches against ground-truth.yaml`.

- [ ] **Step 5: Run the canonical rebuild command**

Run:
```bash
python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db
```
Expected: `0 total mismatches against ground-truth.yaml`, and `Docs/Tools/components.db`
updated (atomically swapped in per the existing `--build` behavior).

- [ ] **Step 6: Run the full test suite**

Run: `python3 -m pytest tests/ Docs/Tools -q`
Expected: all tests pass, including `tests/api/test_e2e.py` (which builds its own temporary
database the same way and would surface any regression here).

- [ ] **Step 7: Commit**

```bash
git add Docs/Tools/edge_resolver.py Docs/Inital_Design/ground-truth.yaml
git commit -m "feat: build 2608A furnace core module and its fits edge to SF-30FQ"
```

---

### Task 6: Documentation updates

**Files:**
- Modify: `Docs/Data/Suburban/VENDOR-Suburban-Furnace_Cooktop.md`
- Modify: `Docs/Data/Suburban/VENDOR-Suburban.md`
- Modify: `README.md`

**Interfaces:** None — pure documentation, no code interfaces.

- [ ] **Step 1: Update VENDOR-Suburban-Furnace_Cooktop.md**

Add a new section at the top of `Docs/Data/Suburban/VENDOR-Suburban-Furnace_Cooktop.md`,
right after the existing header block (before "## 1. Furnace — structure confirmed..."):

```markdown
## 0. Update 2026-08-05 — exact endpoint components built

The owner's in-hand furnace (`SF-30FQ`) and cooktop/range (`SRNA3SBBM`) are now built as
exact fixture components, sourced from in-hand data-plate photographs and matching
manufacturer installation manuals the owner confirmed match their units — see
`docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md`. The furnace also has
a `fits` edge to its `2608A` core replacement module (catalog + retailer corroborated).

This is identity/dimension data for these two specific in-hand models, built independently
of the letter-by-letter grammar question below, which remains open. Do not treat this
section as resolving anything in sections 1–4.
```

- [ ] **Step 2: Update VENDOR-Suburban.md's status summary**

Find the "Current Stage 1 status" or equivalent summary section in
`Docs/Data/Suburban/VENDOR-Suburban.md` (search for the most recent dated status entry near
the top or bottom of the file) and add a bullet:

```markdown
- **2026-08-05:** Furnace (`SF-30FQ`) and cooktop/range (`SRNA3SBBM`) added as exact
  endpoint components — see `VENDOR-Suburban-Furnace_Cooktop.md` sec 0 and
  `docs/superpowers/specs/2026-08-05-suburban-furnace-cooktop-design.md`.
```

- [ ] **Step 3: Update README.md's Suburban status bullet**

In `README.md`, find the `**Suburban**` bullet under "Current Stage 1 status" and append a
sentence:

```markdown
Also carries two exact endpoint components from the owner's current coach — the
`SF-30FQ` furnace (with a `fits` edge to its `2608A` core module) and the `SRNA3SBBM`
cooktop/range, both with manual-sourced clearance and cutout dimensions.
```

- [ ] **Step 4: Run the full test suite one more time**

Run: `python3 -m pytest tests/ Docs/Tools -q`
Expected: all tests pass (this task touches no code, confirms nothing drifted).

- [ ] **Step 5: Commit**

```bash
git add Docs/Data/Suburban/VENDOR-Suburban-Furnace_Cooktop.md \
        Docs/Data/Suburban/VENDOR-Suburban.md README.md
git commit -m "docs: record the SF-30FQ furnace and SRNA3SBBM cooktop endpoint components"
```

---

## Definition of done

- [ ] `python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db` reaches `0 total mismatches`.
- [ ] `python3 -m pytest tests/ Docs/Tools -q` is green.
- [ ] `python3 Docs/Tools/resolver.py --validate Docs/Tools/observations.db` exits 0.
- [ ] `SF-30FQ`, `SRNA3SBBM`, and `2608A` all resolve as components with their in-hand/manual
      attributes, and one `fits` edge (`2608A -> SF-30FQ`) with three evidence rows exists.
- [ ] No `supersedes` edge exists from `SF-30FQ` toward `SF-30VHFQ`/`SF-30VHQ`.
- [ ] No furnace/cooktop model-number grammar claims were added.
- [ ] `Docs/Data/Suburban/VENDOR-Suburban-Furnace_Cooktop.md`, `VENDOR-Suburban.md`, and
      `README.md` all reflect the new components.
