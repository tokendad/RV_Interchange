# Coleman Thermostat Endpoint Components Implementation Plan

**Status:** implemented and verified 2026-08-01

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the three exact Coleman-Mach thermostat endpoints `7330G3351`, `7330F3852`, and `9420-351`, plus the two manufacturer-supported supersession edges, while retaining the `8330-3362` manual-image match as observation-only research.

**Architecture:** Append three retailer observations to the immutable evidence store, classify their relationship/conflict fields, then build exact components exclusively from manufacturer observations #40-#42. Extend the existing edge detail model/store boundary for supersession and resolve two candidate edges with manufacturer and retailer evidence. Expand the fixture without merging suffix-bearing identifiers into the in-hand thermostat or promoting the manual's unnamed illustrations into the graph.

**Tech Stack:** Python 3, SQLite, dataclasses, PyYAML, `requests`, and the repository's inline `self_test()` convention.

## Global Constraints

- Observations are append-only; observations #1-#47 must not be modified.
- Store retailer URLs without the transient `srsltid` query parameter.
- Retailer pages are Tier 7 and cannot override manufacturer attributes.
- `7330G335`, `7330G3351`, `7330F3852`, and `7330F3858` remain distinct identifiers.
- Do not copy the in-hand terminal map onto any catalog endpoint.
- All three new component `interchange_code` values remain null.
- Both supersession edges remain `candidate`, directed old component to current replacement.
- `8330-3362` remains observation-only; do not create a component, identifier-equivalence candidate, or edge for it.
- Do not create compatibility edges from observation #45's unnamed manual illustrations.
- Preserve unrelated untracked `Docs/Data/JR-Products/` and `Docs/Tools/components.db` files.

---

### Task 1: Retailer evidence capture and vocabulary

**Files:**
- Modify: `Docs/Tools/resolver.py`
- Modify: `Docs/Tools/observations.db`
- Modify: `Docs/Tools/TOOLS.md`

**Interfaces:**
- Consumes: `normalize_extracted(obs_id, extracted, strict=True)` and the append-only `observations.py fetch` command.
- Produces: observations #48-#50 and canonical attributes `replacement_claim`, `source_conflicts`, and `visual_match_candidate` for Tasks 3-5.

- [x] **Step 1: Add failing vocabulary assertions**

Extend `resolver.py:self_test()` with this exact input and expected normalized fields:

```python
endpoint_retailer_fields = {
    "relation": {
        "type": "retailer_replacement",
        "from": "7330G3351",
        "to": "9420-351",
    },
    "replacement_equivalence_claim": {
        "function": "same",
        "wiring": "same",
        "mounting": "same",
        "compatibility": "same",
    },
    "retailer_metadata_conflicts": [{
        "field": "functions",
        "title_value": "heat_cool",
        "specification_value": "gas_furnace",
    }],
    "visual_match_candidate": {
        "candidate": {"ns": "coleman", "value": "8330-3362"},
        "comparison_source_observation_id": 45,
        "manual_figure": "electronic_digital_display_thermostat",
        "status": "open",
        "basis": ["RVComfort.HC face", "left display", "up/down controls",
                  "three lower slide controls"],
        "caveat": "visual similarity does not prove model identity",
    },
}
r = normalize_extracted(999, endpoint_retailer_fields, strict=False)
if r["unmapped"]:
    failures.append(f"endpoint retailer fields must classify: {r['unmapped']}")
for key in ("replacement_claim", "source_conflicts", "visual_match_candidate"):
    if key not in r["attributes"]:
        failures.append(f"missing endpoint retailer canonical field: {key}")
```

- [x] **Step 2: Run the vocabulary test to verify RED**

Run:

```bash
cd Docs/Tools
python3 resolver.py --self-test
```

Expected: FAIL reporting the three new raw keys as unmapped.

- [x] **Step 3: Add the canonical fields and aliases**

Add to `CANONICAL`:

```python
"replacement_claim": "structured claim that a replacement retains function/interface behavior",
"source_conflicts": "structured internal contradictions preserved from one source",
"visual_match_candidate": "open visual comparison that does not establish component identity",
```

Add to `ALIASES`:

```python
"replacement_equivalence_claim": "replacement_claim",
"retailer_metadata_conflicts": "source_conflicts",
"visual_match_candidate": "visual_match_candidate",
```

- [x] **Step 4: Run the vocabulary test to verify GREEN**

Run `python3 resolver.py --self-test`.

Expected: `ALL PASS`.

- [x] **Step 5: Fetch the two exact retailer replacement pages**

From `Docs/Tools`, run these commands in order so their IDs are #48 and #49:

```bash
python3 observations.py fetch \
  'https://www.rvproductsshop.com/thermostats/wall-thermostats/7330g3351-coleman-mach-heat-cool-standard-thermostat.html' \
  --source-type retailer_page --source-name rvproductsshop.com --no-interactive \
  --extraction-method hand_typed \
  --extracted '{"models":{"7330G3351":{"title_function":"heat_cool","color":"white","interface":"analog","voltage":"12VDC"}},"relation":{"type":"retailer_replacement","from":"7330G3351","to":"9420-351"},"replacement_equivalence_claim":{"function":"same","wiring":"same","mounting":"same","compatibility":"same"},"retailer_metadata_conflicts":[{"field":"functions","title_value":"heat_cool","specification_value":"gas_furnace"}],"quoted_text":"Function, wiring and compatibility remain the same, but the housing and display style are different."}'

python3 observations.py fetch \
  'https://www.rvproductsshop.com/thermostats/wall-thermostats/7330f3852-coleman-mach-12v-wall-thermostat-heat-cool-black.html' \
  --source-type retailer_page --source-name rvproductsshop.com --no-interactive \
  --extraction-method hand_typed \
  --extracted '{"models":{"7330F3852":{"title_function":"heat_cool","color":"black","interface":"analog","voltage":"12VDC"}},"relation":{"type":"retailer_replacement","from":"7330F3852","to":"9420-351"},"replacement_equivalence_claim":{"function":"same","wiring":"same","mounting":"same","compatibility":"same"},"retailer_metadata_conflicts":[{"field":"functions","title_value":"heat_cool","specification_value":"heat_pump_heat_strip"}],"quoted_text":"Function, wiring and compatibility remain the same, but the housing and display style are different."}'
```

Expected: `Inserted observation #48` and `Inserted observation #49`. If either URL already exists, stop and inspect instead of forcing a duplicate.

- [x] **Step 6: Fetch the visual-candidate page as observation #50**

```bash
python3 observations.py fetch \
  'https://www.rvproductsshop.com/thermostats/wall-thermostats/8330-3362-coleman-mach-digital-h-c-thermostat.html' \
  --source-type retailer_page --source-name rvproductsshop.com --no-interactive \
  --extraction-method hand_typed \
  --extracted '{"models":{"8330-3362":{"function":"heat_cool","interface":"digital","voltage":"12VDC"}},"visual_match_candidate":{"candidate":{"ns":"coleman","value":"8330-3362"},"comparison_source_observation_id":45,"manual_figure":"electronic_digital_display_thermostat","status":"open","basis":["RVComfort.HC face","left display","up/down controls","three lower slide controls"],"caveat":"visual similarity does not prove model identity"},"quoted_text":"8330-3362 Coleman-Mach DIGITAL H/C THERMOSTAT"}'
```

Expected: `Inserted observation #50`.

- [x] **Step 7: Assign tiers and validate the evidence store**

Run:

```bash
python3 resolver.py --assign-tiers --db observations.db
python3 resolver.py --db observations.db --validate
sqlite3 observations.db "SELECT id, source_type, source_tier, url FROM observations WHERE id BETWEEN 48 AND 50 ORDER BY id;"
sqlite3 observations.db "PRAGMA integrity_check;"
```

Expected: 50 observations classify, rows #48-#50 are `retailer_page` Tier 7, URLs have no query string, and integrity is `ok`.

- [x] **Step 8: Document the new observation IDs**

Add #48-#50 to `Docs/Tools/TOOLS.md`, including the two replacement-page conflicts and the candidate-only status of the visual comparison.

- [x] **Step 9: Commit the evidence slice**

```bash
git add Docs/Tools/resolver.py Docs/Tools/observations.db Docs/Tools/TOOLS.md
git commit -m "Capture Coleman endpoint retailer evidence"
```

---

### Task 2: Supersession detail model and store API

**Files:**
- Modify: `Docs/Tools/interchange_models.py`
- Modify: `Docs/Tools/interchange_store.py`

**Interfaces:**
- Consumes: existing `edge_supersession_detail(edge_id, note)` schema table.
- Produces: `EdgeSupersessionDetail`, `insert_supersession_detail(conn, detail) -> None`, and `get_supersession_detail(conn, edge_id) -> EdgeSupersessionDetail | None` for Task 4.

- [x] **Step 1: Add failing model and store assertions**

In `interchange_models.py:self_test()`, instantiate:

```python
detail = EdgeSupersessionDetail(edge_id=7, note="7330G3351 replaced by 9420-351")
if detail.edge_id != 7 or "9420-351" not in detail.note:
    failures.append(f"supersession detail mismatch: {detail}")
```

In `interchange_store.py:self_test()`, after creating the test edge, add:

```python
supersession = Edge(type="supersedes", from_component_id="c_test_a",
                    to_component_id="c_test_b")
insert_edge(conn, supersession)
insert_supersession_detail(conn, EdgeSupersessionDetail(
    edge_id=supersession.id, note="test replacement chain"))
stored = get_supersession_detail(conn, supersession.id)
if stored is None or stored.note != "test replacement chain":
    failures.append(f"supersession detail round trip failed: {stored}")
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
cd Docs/Tools
python3 interchange_models.py --self-test
python3 interchange_store.py --self-test
```

Expected: FAIL/exception because the dataclass and functions do not exist.

- [x] **Step 3: Implement the dataclass**

Add to `interchange_models.py`:

```python
@dataclass
class EdgeSupersessionDetail:
    edge_id: int
    note: Optional[str] = None
```

- [x] **Step 4: Implement the store functions**

Import `EdgeSupersessionDetail` and add:

```python
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
```

- [x] **Step 5: Run tests to verify GREEN**

Run both self-tests from Step 2.

Expected: both print `self_test: PASS`.

- [x] **Step 6: Commit the store slice**

```bash
git add Docs/Tools/interchange_models.py Docs/Tools/interchange_store.py
git commit -m "Add supersession detail store support"
```

---

### Task 3: Exact Coleman endpoint component builder

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: observations #40-#42, `Component`, `Identifier`, and `ComponentAttribute`.
- Produces: `coleman_endpoint_components(product_row, replacement_row, legacy_row, component_ids) -> list[tuple[Component, list[Identifier], list[ComponentAttribute]]]`.

- [x] **Step 1: Add failing happy-path assertions**

Load observations #40-#42 in `edge_resolver.py:self_test()` and call:

```python
endpoint_ids = {
    "7330G3351": "c_placeholder_tstat_7330g3351",
    "7330F3852": "c_placeholder_tstat_7330f3852",
    "9420-351": "c_placeholder_tstat_9420_351",
}
endpoints = coleman_endpoint_components(obs40, obs41, obs42, endpoint_ids)
by_model = {
    identifiers[0].value: (component, identifiers, attributes)
    for component, identifiers, attributes in endpoints
}
if set(by_model) != set(endpoint_ids):
    failures.append(f"Coleman endpoint set mismatch: {set(by_model)}")
for model, (component, identifiers, attributes) in by_model.items():
    if component.part_type_id != 415 or component.interchange_code is not None:
        failures.append(f"invalid endpoint component: {component}")
    if [(i.ns, i.value, i.visibility) for i in identifiers] != [
            ("coleman", model, None)]:
        failures.append(f"invalid endpoint identifiers for {model}: {identifiers}")
```

Assert these exact attribute maps and source IDs:

```python
expected = {
    "7330G3351": {
        "function": ("heat_cool", 40), "color": ("white", 40),
        "interface_type": ("analog", 40), "stages": ("single", 42),
        "voltage": ("12VDC", 42),
    },
    "7330F3852": {
        "function": ("heat_cool", 40), "color": ("black", 40),
        "interface_type": ("analog", 40), "stages": ("single", 40),
    },
    "9420-351": {
        "function": ("heat_cool", 41), "color": ("black", 41),
        "interface_type": ("analog", 41), "voltage": ("12VDC", 41),
    },
}
```

Also assert no endpoint has `terminal_order`, `terminal_function`, or
`terminal_board_position` attributes.

- [x] **Step 2: Add failing rejection assertions**

Use the existing `changed_row()` helper to verify all of these raise `ValueError`:

```python
invalid_endpoint_inputs = (
    (changed_row(obs40, lambda e: e["models"].pop("7330F3852")), obs41, obs42),
    (obs40, changed_row(obs41, lambda e: e["relation"].__setitem__(
        "from", ["7330G335", "7330F3852"])), obs42),
    (obs40, changed_row(obs41, lambda e: e["relation"].__setitem__(
        "to", "7330F3858")), obs42),
)
for product, replacement, legacy in invalid_endpoint_inputs:
    try:
        coleman_endpoint_components(product, replacement, legacy, endpoint_ids)
        failures.append("invalid Coleman endpoint evidence was accepted")
    except ValueError:
        pass
```

Pass an ID map containing `7330G335` or `7330F3858` and require rejection.

- [x] **Step 3: Run the resolver test to verify RED**

Run `python3 edge_resolver.py --self-test --verbose`.

Expected: FAIL/exception because `coleman_endpoint_components` does not exist.

- [x] **Step 4: Implement the exact endpoint builder**

Add constants:

```python
COLEMAN_ENDPOINT_MODELS = ("7330G3351", "7330F3852", "9420-351")
COLEMAN_ENDPOINT_RESOLVER_VERSION = "coleman_endpoint_v1"
```

Implement the declared function with validation before construction:

```python
def coleman_endpoint_components(product_row, replacement_row, legacy_row, component_ids):
    product = _normalized_attributes(product_row)
    replacement = _normalized_attributes(replacement_row)
    legacy = _normalized_attributes(legacy_row)
    product_models = product.get("model_spec_table")
    replacement_models = replacement.get("model_spec_table")
    legacy_models = legacy.get("model_spec_table")
    relation = replacement.get("sku_relationship")

    if not all(isinstance(models, dict) for models in
               (product_models, replacement_models, legacy_models)):
        raise ValueError("Coleman endpoint observations require model tables")
    if not {"7330G3351", "7330F3852"}.issubset(product_models):
        raise ValueError("official product page is missing a retired endpoint")
    expected_relation = {
        "type": "manufacturer_supersedes",
        "from": ["7330G3351", "7330F3852"],
        "to": "9420-351",
    }
    if relation != expected_relation or "9420-351" not in replacement_models:
        raise ValueError(f"unexpected Coleman replacement relation: {relation}")
    if "7330G3351" not in legacy_models:
        raise ValueError("legacy catalog is missing 7330G3351")
    if set(component_ids) != set(COLEMAN_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman endpoint ID map: {component_ids}")

    def text_attr(component_id, name, value, provenance, source_row):
        return ComponentAttribute(
            component_id, name, provenance, source_row["id"], value_text=value,
            resolver_version=COLEMAN_ENDPOINT_RESOLVER_VERSION)

    source_checks = (
        (product_models["7330G3351"].get("function"), "heat_cool", "7330G3351 function"),
        (product_models["7330G3351"].get("color"), "white", "7330G3351 color"),
        (product_models["7330F3852"].get("function"), "heat_cool", "7330F3852 function"),
        (product_models["7330F3852"].get("color"), "black", "7330F3852 color"),
        (legacy_models["7330G3351"].get("function"), "single_stage_heat_cool",
         "7330G3351 legacy function"),
        (legacy_models["7330G3351"].get("voltage"), "12VDC", "7330G3351 voltage"),
        (replacement_models["9420-351"].get("function"), "heat_cool",
         "9420-351 function"),
        (replacement_models["9420-351"].get("color"), "black", "9420-351 color"),
        (replacement_models["9420-351"].get("voltage"), "12VDC", "9420-351 voltage"),
    )
    for actual, expected, label in source_checks:
        if actual != expected:
            raise ValueError(f"unexpected {label}: {actual!r}")

    attribute_specs = {
        "7330G3351": (
            ("function", "heat_cool", "manufacturer_page", product_row),
            ("color", "white", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "manufacturer_pdf", legacy_row),
            ("voltage", "12VDC", "manufacturer_pdf", legacy_row),
        ),
        "7330F3852": (
            ("function", "heat_cool", "manufacturer_page", product_row),
            ("color", "black", "manufacturer_page", product_row),
            ("interface_type", "analog", "manufacturer_page", product_row),
            ("stages", "single", "manufacturer_page_inferred", product_row),
        ),
        "9420-351": (
            ("function", "heat_cool", "manufacturer_pdf", replacement_row),
            ("color", "black", "manufacturer_pdf", replacement_row),
            ("interface_type", "analog", "manufacturer_pdf", replacement_row),
            ("voltage", "12VDC", "manufacturer_pdf", replacement_row),
        ),
    }
    results = []
    for model in COLEMAN_ENDPOINT_MODELS:
        component_id = component_ids[model]
        component = Component(component_id, THERMOSTAT_PART_TYPE, None)
        identifiers = [Identifier(component_id, "coleman", model, None)]
        attributes = [text_attr(component_id, name, value, provenance, source_row)
                      for name, value, provenance, source_row in attribute_specs[model]]
        results.append((component, identifiers, attributes))
    return results
```

- [x] **Step 5: Run the resolver test to verify GREEN**

Run `python3 edge_resolver.py --self-test --verbose`.

Expected: the endpoint assertions pass while all existing Suburban and in-hand thermostat
assertions remain green.

- [x] **Step 6: Commit the component-builder slice**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "Resolve exact Coleman thermostat endpoints"
```

---

### Task 4: Directed Coleman supersession resolver

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: `resolve_coleman_supersessions(conn, replacement_row, retailer_rows, component_ids)`, Task 2 store APIs, and already-persisted Task 3 endpoint components.
- Produces: two persisted edge IDs ordered as `7330G3351 -> 9420-351`, then `7330F3852 -> 9420-351`.

- [x] **Step 1: Add failing happy-path edge assertions**

Load observations #48 and #49. Persist the three endpoint components and call:

```python
edge_ids = resolve_coleman_supersessions(
    store_conn, obs41, [obs48, obs49], endpoint_ids)
if len(edge_ids) != 2:
    failures.append(f"expected two Coleman supersession edges, got {edge_ids}")
rows = store_conn.execute(
    "SELECT * FROM edges WHERE id IN (?, ?) ORDER BY id", edge_ids).fetchall()
expected_pairs = [
    (endpoint_ids["7330G3351"], endpoint_ids["9420-351"]),
    (endpoint_ids["7330F3852"], endpoint_ids["9420-351"]),
]
actual_pairs = [(r["from_component_id"], r["to_component_id"]) for r in rows]
if actual_pairs != expected_pairs:
    failures.append(f"Coleman supersession direction mismatch: {actual_pairs}")
```

For each row, require type `supersedes`, status `candidate`, group key
`coleman_analog_heat_cool_12v`, resolver version `coleman_endpoint_v1`, a non-null
supersession detail, and these evidence tuples, using observation #48 for the
`7330G3351` edge and #49 for the `7330F3852` edge:

```python
[
    ("attribute_prior", 1.0, 1.0, None),
    ("manufacturer_assertion", 2.0, 0.0, 41),
    ("retailer_cross_reference", 1.0, 0.0, expected_retailer_observation_id),
]
```

Require `compute_confidence()` to return alpha `4`, beta `1`, value `0.8`, certainty `5`.

- [x] **Step 2: Add failing edge rejection assertions**

Verify `ValueError` for:

- a reversed manufacturer relation;
- a relation with either endpoint missing or an extra endpoint;
- a self-reference to `9420-351`;
- a retailer row whose relation pair does not match its edge;
- a connection to `c_placeholder_tstat`;
- calling the resolver before all three endpoint components exist.

After each rejected call, assert validation occurred before writes and left zero Coleman
supersession edges in the test connection.

- [x] **Step 3: Run the resolver test to verify RED**

Run `python3 edge_resolver.py --self-test --verbose`.

Expected: FAIL/exception because `resolve_coleman_supersessions` does not exist.

- [x] **Step 4: Implement validation before writes**

Start the function with this validation block:

```python
def resolve_coleman_supersessions(conn, replacement_row, retailer_rows, component_ids):
    manufacturer = _normalized_attributes(replacement_row)
    expected_manufacturer_relation = {
        "type": "manufacturer_supersedes",
        "from": ["7330G3351", "7330F3852"],
        "to": "9420-351",
    }
    if manufacturer.get("sku_relationship") != expected_manufacturer_relation:
        raise ValueError("unexpected manufacturer supersession relation")
    if set(component_ids) != set(COLEMAN_ENDPOINT_MODELS):
        raise ValueError(f"unexpected Coleman endpoint ID map: {component_ids}")
    if "c_placeholder_tstat" in component_ids.values():
        raise ValueError("in-hand thermostat cannot be a catalog endpoint")
    if len(set(component_ids.values())) != 3:
        raise ValueError("Coleman endpoint components must be distinct")

    retailer_by_model = {}
    for row in retailer_rows:
        attrs = _normalized_attributes(row)
        relation = attrs.get("sku_relationship")
        if not isinstance(relation, dict) or relation.get("type") != "retailer_replacement":
            raise ValueError(f"observation #{row['id']} lacks a retailer replacement")
        retired_model = relation.get("from")
        if retired_model not in ("7330G3351", "7330F3852") or \
                relation.get("to") != "9420-351":
            raise ValueError(f"unexpected retailer replacement pair: {relation}")
        claim = attrs.get("replacement_claim")
        if claim != {"function": "same", "wiring": "same", "mounting": "same",
                     "compatibility": "same"}:
            raise ValueError(f"incomplete retailer replacement claim: {claim}")
        if retired_model in retailer_by_model:
            raise ValueError(f"duplicate retailer row for {retired_model}")
        retailer_by_model[retired_model] = row
    if set(retailer_by_model) != {"7330G3351", "7330F3852"}:
        raise ValueError("both retired endpoint retailer rows are required")

    existing = conn.execute(
        "SELECT component_id FROM components WHERE component_id IN (?, ?, ?)",
        tuple(component_ids[m] for m in COLEMAN_ENDPOINT_MODELS)).fetchall()
    if {row["component_id"] for row in existing} != set(component_ids.values()):
        raise ValueError("all Coleman endpoint components must exist before edge resolution")
```

Do not call helper functions that commit until this entire block has succeeded. After
validation, the existing commit-per-insert store functions are acceptable because no later
input validation can fail.

- [x] **Step 5: Implement both edges, details, and evidence**

Import `EdgeSupersessionDetail`, `insert_supersession_detail()`, and
`get_supersession_detail()` into `edge_resolver.py`. For each retired model in
`("7330G3351", "7330F3852")`:

```python
edge = Edge(
    type="supersedes",
    from_component_id=component_ids[retired_model],
    to_component_id=component_ids["9420-351"],
    group_key="coleman_analog_heat_cool_12v",
    status="candidate",
    resolver_version=COLEMAN_ENDPOINT_RESOLVER_VERSION,
    notes="Coleman catalog names 9420-351 as the current replacement",
)
insert_edge(conn, edge)
insert_supersession_detail(conn, EdgeSupersessionDetail(
    edge_id=edge.id,
    note=f"Coleman 2025 catalog names 9420-351 as the replacement for {retired_model}."))
for event_type, alpha, beta, source_id in (
    ("attribute_prior", 1.0, 1.0, None),
    ("manufacturer_assertion", 2.0, 0.0, replacement_row["id"]),
    ("retailer_cross_reference", 1.0, 0.0,
     retailer_by_model[retired_model]["id"]),
):
    insert_evidence(conn, RelationshipEvidence(
        edge_id=edge.id, event_type=event_type, effect_alpha=alpha,
        effect_beta=beta, source_observation_id=source_id, occurred_at=now_iso()))
edge_ids.append(edge.id)
```

Initialize `edge_ids = []` before the loop and return `tuple(edge_ids)` after it. The three
evidence rows must remain in the Step 1 order.

- [x] **Step 6: Run the resolver test to verify GREEN**

Run `python3 edge_resolver.py --self-test --verbose`.

Expected: all resolver assertions pass, including the negative validation-before-write checks.

- [x] **Step 7: Commit the edge-resolver slice**

```bash
git add Docs/Tools/edge_resolver.py
git commit -m "Persist Coleman thermostat supersession edges"
```

---

### Task 5: Ground-truth fixture and milestone documentation

**Files:**
- Modify: `Docs/Inital_Design/ground-truth.yaml`
- Modify: `Docs/Tools/edge_resolver.py`
- Modify: `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md`
- Modify: `Docs/Inital_Design/PLAN-Staged_Build.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-01-coleman-endpoint-components-design.md`
- Modify: `docs/superpowers/plans/2026-08-01-coleman-endpoint-components.md`

**Interfaces:**
- Consumes: all builders and store APIs from Tasks 1-4.
- Produces: a zero-mismatch fixture covering endpoint identity, attributes, direction, detail, evidence, and prohibited graph promotions.

- [x] **Step 1: Add the three fixture components**

Append the three component records from the approved design table. Each must use part type
`415`, a null interchange code, one `coleman` identifier, and per-attribute source and
provenance. Do not include terminal attributes.

- [x] **Step 2: Add the two fixture edges**

Add two records with this exact shape, substituting the retired component ID, identifier,
and retailer observation ID for each row:

```yaml
- type: supersedes
  from: c_placeholder_tstat_7330g3351
  to: c_placeholder_tstat_9420_351
  group: coleman_analog_heat_cool_12v
  status: candidate
  detail:
    note: "Coleman 2025 catalog names 9420-351 as the replacement for 7330G3351."
  confidence: {alpha: 4, beta: 1, value: 0.8, certainty: 5}
  evidence:
    - {event_type: attribute_prior, alpha: 1, beta: 1, source_observation_id: null}
    - {event_type: manufacturer_assertion, alpha: 2, beta: 0, source_observation_id: 41}
    - {event_type: retailer_cross_reference, alpha: 1, beta: 0, source_observation_id: 48}
```

The second row is `c_placeholder_tstat_7330f3852 -> c_placeholder_tstat_9420_351` and uses
observation #49.

- [x] **Step 3: Add failing fixture comparisons**

Extend `check_fixture()` to load #40-#42 and #48-#50, build/persist the endpoints and edges,
and compare:

- exact identifier sets and null interchange codes;
- every expected attribute value, provenance, and observation ID;
- exact old-to-current edge pairs;
- edge type/status/group/resolver version;
- supersession detail note;
- all three evidence rows and computed confidence per edge.

Add explicit forbidden queries requiring:

```sql
SELECT COUNT(*) FROM edges
WHERE type = 'supersedes'
  AND (from_component_id = 'c_placeholder_tstat'
       OR to_component_id = 'c_placeholder_tstat');
```

to equal zero; `8330-3362` to appear in neither `identifiers` nor
`identifier_equivalence_candidate`; and no `substitutes` edge among the four Coleman fixture
components.

- [x] **Step 4: Run fixture validation to verify RED**

Run:

```bash
cd Docs/Tools
python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml
```

Expected: endpoint/supersession mismatches until the fixture integration is completed.

- [x] **Step 5: Complete fixture integration and reporting**

Finish the persistence/comparison path and add one summary line:

```text
Coleman endpoints: 0 mismatch(es)
```

Keep the existing Suburban and in-hand thermostat summary lines unchanged.

- [x] **Step 6: Refresh milestone documents**

Update:

- `README.md`: 50 observations; endpoint resolver and two supersession edges complete; next
  Coleman task is independently identifying the manual's unnamed generations.
- `Docs/Inital_Design/PLAN-Staged_Build.md`: mark the endpoint/supersession milestone done
  while retaining the manual compatibility boundary.
- `Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md`: add observations #48-#50, retailer
  conflicts, exact edges, and candidate-only `8330-3362` finding.
- Approved design status: `implemented 2026-08-01`.
- This plan status: `implemented and verified 2026-08-01`; mark completed checkboxes `[x]`
  immediately before the final implementation commit.

- [x] **Step 7: Run fixture validation to verify GREEN**

Run the command from Step 4.

Expected: Suburban, thermostat, and Coleman endpoint mismatch counts all equal zero, followed
by `0 total mismatches against ground-truth.yaml`.

- [x] **Step 8: Commit fixture and documentation**

```bash
git add Docs/Inital_Design/ground-truth.yaml Docs/Tools/edge_resolver.py \
  Docs/Data/Coleman_Mach/VENDOR-Coleman-Mach.md \
  Docs/Inital_Design/PLAN-Staged_Build.md README.md \
  docs/superpowers/specs/2026-08-01-coleman-endpoint-components-design.md \
  docs/superpowers/plans/2026-08-01-coleman-endpoint-components.md
git commit -m "Verify Coleman thermostat endpoint graph"
```

---

### Task 6: Full regression verification and scope audit

**Files:**
- Verify all files named above.

**Interfaces:**
- Consumes: the complete endpoint implementation.
- Produces: fresh evidence that the observation, resolver, schema, store, and fixture contracts all pass together.

- [x] **Step 1: Run the complete test matrix**

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

Expected: all tests pass, 50 observations classify, and every fixture mismatch count is zero.

- [x] **Step 2: Audit database integrity and append-only history**

```bash
sqlite3 observations.db "PRAGMA integrity_check;"
sqlite3 observations.db "SELECT COUNT(*) FROM observations;"
sqlite3 observations.db "SELECT COUNT(*) FROM observations WHERE source_tier IS NULL;"
sqlite3 observations.db "SELECT id, source_type, source_tier, url FROM observations WHERE id >= 48 ORDER BY id;"
```

Expected: `ok`, count `50`, null-tier count `0`, and exactly the three Tier 7 clean URLs.

- [x] **Step 3: Audit repository scope**

From the repository root:

```bash
git diff --check
git status --short
git diff --stat
```

Expected: only planned endpoint files are modified during implementation; untracked
`Docs/Data/JR-Products/` and `Docs/Tools/components.db` remain untouched and unstaged.

- [x] **Step 4: Commit any final plan-status-only change**

If marking the final Task 6 boxes created a plan-only diff after Task 5's commit:

```bash
git add docs/superpowers/plans/2026-08-01-coleman-endpoint-components.md
git commit -m "Complete Coleman endpoint implementation plan"
```

Do not stage either unrelated untracked path.
