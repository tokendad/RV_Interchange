# Suburban Remaining Fixture Resolution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `edge_resolver.py` so it resolves every remaining water-heater
component and edge in `ground-truth.yaml` that has real backing evidence in
`observations.db` — closing out `VENDOR-Suburban.md` §8's last `[~]` item —
without fabricating evidence for the one component that has none
(`c_placeholder_wh_switch`).

**Architecture:** Same shape as the existing Coleman-endpoint work in
`edge_resolver.py`: one small, strictly-validating builder function per
component/edge group, each reading directly from a specific `observations.db`
row's `extracted` JSON (bypassing `resolver.normalize_extracted`'s generic
alias/compound handling where the fixture's chosen attribute names —
`cutout_h`/`cutout_w`/`cutout_d`, not `opening_h`/`opening_w` — don't match
what the generic compound handler would produce). Every builder raises
`ValueError` on any input that doesn't match what's expected, exactly like
`coleman_endpoint_components`/`thermostat_from_observations` already do.
Wired into `self_test()` (developer-facing internal check) and
`check_fixture()` (fixture-reproduction check) the same way the Coleman work
was.

**Tech Stack:** Python 3, stdlib `sqlite3`/`json`, existing
`interchange_models.py`/`interchange_store.py`/`interchange_schema.py`.

## Global Constraints

- Every new builder function must raise `ValueError` (not assert, not silently
  drop) on any unexpected observation content — matches existing
  `coleman_endpoint_components` / `thermostat_from_observations` discipline.
- No new observation rows are invented. `c_placeholder_wh_switch` (identifiers
  `232882`/`233111`/`232881`) has **no observation in `observations.db`** —
  confirmed by `grep`, none of those three values or the interior-switch note
  appear anywhere in the 50 captured rows. It is explicitly **out of scope**
  for this plan and must be called out, not silently invented.
- `ComponentAttribute` requires exactly one of `value_text`/`value_number`/
  `value_boolean` (see `interchange_models.py:44-49`) — never pass more than
  one.
- Confidence is always computed via `compute_confidence(evidence_rows)`
  (`interchange_models.py:155`), never stored as a field.
- Run `python3 edge_resolver.py --self-test` and
  `python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml`
  after every task; both must report 0 failures/mismatches before moving on.

---

## Known fixture inconsistency (read before Task 5)

The four manufacturer-documented IW60RL retrofit edges in `ground-truth.yaml`
(lines ~603-734) hand-author `alpha`/`beta`/`certainty` in a way that isn't
internally consistent with `compute_confidence`'s formula
(`certainty = alpha + beta`) used everywhere else in this codebase — e.g. the
6-gallon edge states `alpha: 5, beta: 1, certainty: 5` (5+1=6, not 5), and the
Atwood edges state `alpha: 4, beta: 1, certainty: 3` (4+1=5, not 3). Every
other edge in the fixture (the canonical SW6DE/SW6DEL edge, the cross-capacity
edge, the two Coleman supersession edges) *is* internally consistent
(certainty == alpha+beta) and is already reproduced exactly by the existing
code. Rather than force evidence rows to hit an arithmetically-impossible
target, Task 5 reproduces `alpha`/`beta`/`value` mechanically (which do match)
and prints an explicit informational note — not a MISMATCH — documenting that
`certainty` for these four edges is a hand-authored qualitative dial in the
fixture, not derived from evidence rows. This matches the project's practice
of surfacing known gaps explicitly (e.g. `PLAN-Staged_Build.md`'s open items)
rather than silently forcing a fit.

---

### Task 1: 12DEL component resolver

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: `Component`, `Identifier`, `ComponentAttribute` from
  `interchange_models.py`; `_validate_observation_source` (existing, line 106).
- Produces: `resolve_12del_component(retailer_row, channel_split_row,
  component_id) -> (Component, list[Identifier], list[ComponentAttribute])`,
  used by Tasks 4 and 6.

- [ ] **Step 1: Add the failing self-test assertions**

  In `self_test()`, after the existing `comp_6del`/`comp_6de` block (around
  line 674), add:

  ```python
  obs11 = load_observation(obs_db, 11)   # SW12DEL retailer spec + buyer review
  obs35 = load_observation(obs_db, 35)   # 5148A/5248A channel-split confirmation

  comp_12del, ids_12del, attrs_12del = resolve_12del_component(
      obs11, obs35, "c_placeholder_wh_12del")
  if comp_12del.part_type_id != WATER_HEATER_PART_TYPE:
      failures.append(f"12DEL part_type mismatch: {comp_12del}")
  expected_12del_ids = {
      ("suburban", "SW12DEL", "exterior_plate"),
      ("suburban", "5248A", "none_marked"),
      ("suburban", "5148A", "none_marked"),
  }
  if {(i.ns, i.value, i.visibility) for i in ids_12del} != expected_12del_ids:
      failures.append(f"12DEL identifiers mismatch: {ids_12del}")
  expected_12del_attrs = {
      ("capacity_gal", ""): 12.0,
      ("input_btuh", ""): 12000.0,
      ("element_watts", "1400"): 1400.0,
      ("element_watts", "1440"): 1440.0,
      ("cutout_h", ""): 16.38,
      ("cutout_w", ""): 16.38,
      ("cutout_d", ""): 22.25,
      ("weight_empty", ""): 48.0,
      ("weight_full", ""): 148.08,
  }
  actual_12del_attrs = {
      (a.name, a.qualifier): a.value_number for a in attrs_12del
  }
  if actual_12del_attrs != expected_12del_attrs:
      failures.append(f"12DEL attributes mismatch: {actual_12del_attrs}")

  for invalid11, invalid35, label in (
      (changed_row(obs11, lambda e: e.__setitem__("model", "SW10DEL")), obs35,
       "wrong model"),
      (changed_row(obs11, lambda e: e["cutout_in"].__setitem__("h", 16.0)), obs35,
       "wrong cutout"),
      (changed_row(obs11, lambda e: e.__setitem__("element_watts", [1440])), obs35,
       "resolved element_watts"),
      (dict(obs11, id=110), obs35, "wrong obs id"),
      (obs11, changed_row(obs35, lambda e: e.__setitem__(
          "relation", "legacy_current_renumbering")), "wrong channel-split relation"),
  ):
      try:
          resolve_12del_component(invalid11, invalid35, "c_invalid")
          failures.append(f"invalid 12DEL evidence accepted: {label}")
      except ValueError:
          pass
  ```

- [ ] **Step 2: Run self-test to see it fail**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `NameError: name 'resolve_12del_component' is not defined`

- [ ] **Step 3: Implement `resolve_12del_component`**

  Add to `edge_resolver.py`, near `component_from_observation`:

  ```python
  def resolve_12del_component(retailer_row, channel_split_row, component_id):
      _validate_observation_source(retailer_row, 11, "retailer_page", 7, "12DEL retailer")
      extracted = json.loads(retailer_row["extracted"])
      if extracted.get("model") != "SW12DEL":
          raise ValueError(f"unexpected 12DEL model: {extracted.get('model')}")
      cutout = extracted.get("cutout_in")
      weight = extracted.get("weight_lb")
      element_watts = extracted.get("element_watts")
      if cutout != {"h": 16.38, "w": 16.38, "d": 22.25}:
          raise ValueError(f"unexpected 12DEL cutout: {cutout}")
      if weight != {"empty": 48.0, "full": 148.08}:
          raise ValueError(f"unexpected 12DEL weight: {weight}")
      if element_watts != [1400, 1440]:
          raise ValueError(f"unexpected 12DEL element watts: {element_watts}")
      if extracted.get("capacity_gal") != 12 or extracted.get("input_btuh") != 12000:
          raise ValueError("unexpected 12DEL capacity/BTU")

      try:
          channel_split = json.loads(channel_split_row["extracted"])
      except (KeyError, TypeError) as exc:
          raise ValueError("12DEL channel-split observation lacks extracted JSON") from exc
      if channel_split.get("relation") != "co-current_channel_split" or \
              set(channel_split.get("skus", [])) != {"5148A", "5248A"}:
          raise ValueError(f"unexpected 12DEL channel-split evidence: {channel_split}")

      component = Component(component_id, WATER_HEATER_PART_TYPE)
      identifiers = [
          Identifier(component_id, "suburban", "SW12DEL", "exterior_plate"),
          Identifier(component_id, "suburban", "5248A", "none_marked"),
          Identifier(component_id, "suburban", "5148A", "none_marked"),
      ]
      obs_id = retailer_row["id"]
      attributes = [
          ComponentAttribute(component_id, "capacity_gal", "retailer_spec_block",
                              obs_id, value_number=12.0),
          ComponentAttribute(component_id, "input_btuh", "retailer_spec_block",
                              obs_id, value_number=12000.0),
          ComponentAttribute(component_id, "element_watts", "retailer_spec_block",
                              obs_id, qualifier="1400", value_number=1400.0),
          ComponentAttribute(component_id, "element_watts", "retailer_spec_block",
                              obs_id, qualifier="1440", value_number=1440.0),
          ComponentAttribute(component_id, "cutout_h", "retailer_spec_block",
                              obs_id, unit="in", value_number=16.38),
          ComponentAttribute(component_id, "cutout_w", "retailer_spec_block",
                              obs_id, unit="in", value_number=16.38),
          ComponentAttribute(component_id, "cutout_d", "retailer_spec_block",
                              obs_id, unit="in", value_number=22.25),
          ComponentAttribute(component_id, "weight_empty", "retailer_spec_block",
                              obs_id, unit="lb", value_number=48.0),
          ComponentAttribute(component_id, "weight_full", "retailer_spec_block",
                              obs_id, unit="lb", value_number=148.08),
      ]
      return component, identifiers, attributes
  ```

- [ ] **Step 4: Run self-test to see it pass**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `self_test: PASS`

- [ ] **Step 5: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py
  git commit -m "Resolve SW12DEL component from observations #11/#35"
  ```

---

### Task 2: IW60RL component resolver

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Produces: `resolve_iw60rl_component(retailer_row, manual_row, component_id)
  -> (Component, list[Identifier], list[ComponentAttribute])`, used by Tasks 5
  and 6.

- [ ] **Step 1: Add failing self-test assertions**

  ```python
  obs13 = load_observation(obs_db, 13)   # IW60RL retailer page
  # obs14 already loaded above for Coleman... no: obs14 is the Nautilus manual,
  # already loaded as `obs14` earlier in self_test for a different purpose in
  # this same function scope - reuse the same variable.

  comp_iw60rl, ids_iw60rl, attrs_iw60rl = resolve_iw60rl_component(
      obs13, obs14, "c_placeholder_wh_iw60rl")
  if comp_iw60rl.part_type_id != WATER_HEATER_PART_TYPE:
      failures.append(f"IW60RL part_type mismatch: {comp_iw60rl}")
  expected_iw60rl_ids = {
      ("suburban", "IW60RL", "exterior_plate"),
      ("suburban", "5280A", "none_marked"),
  }
  if {(i.ns, i.value, i.visibility) for i in ids_iw60rl} != expected_iw60rl_ids:
      failures.append(f"IW60RL identifiers mismatch: {ids_iw60rl}")
  actual_iw60rl_attrs = {
      a.name: (a.value_number if a.value_number is not None else a.value_boolean,
                a.provenance, a.source_observation_id)
      for a in attrs_iw60rl
  }
  expected_iw60rl_attrs = {
      "tankless": (True, "retailer_spec_block", 13),
      "capacity_gal": (0.5, "retailer_spec_block", 13),
      "input_btuh": (60000.0, "retailer_spec_block", 13),
      "vent_hole_diameter_in": (3.750, "manufacturer_pdf", 14),
      "product_size_h": (12.5, "retailer_spec_block", 13),
      "product_size_w": (12.5, "retailer_spec_block", 13),
      "product_size_d": (20.0, "manufacturer_pdf", 14),
      "weight_empty": (36.0, "retailer_spec_block", 13),
  }
  if actual_iw60rl_attrs != expected_iw60rl_attrs:
      failures.append(f"IW60RL attributes mismatch: {actual_iw60rl_attrs}")
  ignition_attr = next(a for a in attrs_iw60rl if a.name == "ignition_type")
  if (ignition_attr.value_text, ignition_attr.provenance) != ("direct_spark", "retailer_spec_block"):
      failures.append(f"IW60RL ignition_type mismatch: {ignition_attr}")

  for mutate, label in (
      (lambda e: e.__setitem__("capacity_gal", 1.0), "wrong capacity"),
      (lambda e: e.__setitem__("ignition_type", "Pilot"), "wrong ignition"),
      (lambda e: e["product_size_in"].__setitem__("d", 21.0), "wrong depth"),
  ):
      try:
          resolve_iw60rl_component(changed_row(obs13, mutate), obs14, "c_invalid")
          failures.append(f"invalid IW60RL evidence accepted: {label}")
      except ValueError:
          pass
  try:
      resolve_iw60rl_component(
          obs13, changed_row(obs14, lambda e: e.__setitem__("vent_hole_diameter_in", 4.0)),
          "c_invalid")
      failures.append("invalid IW60RL vent hole evidence accepted")
  except ValueError:
      pass
  ```

- [ ] **Step 2: Run self-test to see it fail**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `NameError: name 'resolve_iw60rl_component' is not defined`

- [ ] **Step 3: Implement `resolve_iw60rl_component`**

  ```python
  _IGNITION_TEXT_TO_TYPE = {"Direct Spark Ignition": "direct_spark"}


  def resolve_iw60rl_component(retailer_row, manual_row, component_id):
      _validate_observation_source(retailer_row, 13, "retailer_page", 7, "IW60RL retailer")
      _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
      retailer = json.loads(retailer_row["extracted"])
      manual = json.loads(manual_row["extracted"])

      if retailer.get("model") != "IW60RL" or retailer.get("sku") != "5280A":
          raise ValueError(f"unexpected IW60RL identity: {retailer}")
      if retailer.get("capacity_gal") != 0.5 or retailer.get("btu") != 60000:
          raise ValueError("unexpected IW60RL capacity/BTU")
      ignition_text = retailer.get("ignition_type")
      if ignition_text not in _IGNITION_TEXT_TO_TYPE:
          raise ValueError(f"unrecognized IW60RL ignition text: {ignition_text}")
      product_size = retailer.get("product_size_in")
      if product_size != {"w": 12.5, "h": 12.5, "d": 20}:
          raise ValueError(f"unexpected IW60RL product size: {product_size}")
      if retailer.get("weight_lb") != 36.0:
          raise ValueError(f"unexpected IW60RL weight: {retailer.get('weight_lb')}")

      if manual.get("vent_hole_diameter_in") != 3.75:
          raise ValueError(f"unexpected IW60RL vent hole diameter: "
                            f"{manual.get('vent_hole_diameter_in')}")
      if manual.get("dimensions_in") != {"h": 12.5, "w": 12.5, "d": 20.0}:
          raise ValueError(f"unexpected IW60RL manual dimensions: "
                            f"{manual.get('dimensions_in')}")

      component = Component(component_id, WATER_HEATER_PART_TYPE)
      identifiers = [
          Identifier(component_id, "suburban", "IW60RL", "exterior_plate"),
          Identifier(component_id, "suburban", "5280A", "none_marked"),
      ]
      retailer_id, manual_id = retailer_row["id"], manual_row["id"]
      attributes = [
          ComponentAttribute(component_id, "tankless", "retailer_spec_block",
                              retailer_id, value_boolean=True),
          ComponentAttribute(component_id, "capacity_gal", "retailer_spec_block",
                              retailer_id, value_number=0.5),
          ComponentAttribute(component_id, "input_btuh", "retailer_spec_block",
                              retailer_id, value_number=60000.0),
          ComponentAttribute(component_id, "ignition_type", "retailer_spec_block",
                              retailer_id, value_text=_IGNITION_TEXT_TO_TYPE[ignition_text]),
          ComponentAttribute(component_id, "vent_hole_diameter_in", "manufacturer_pdf",
                              manual_id, unit="in", value_number=3.750),
          ComponentAttribute(component_id, "product_size_h", "retailer_spec_block",
                              retailer_id, unit="in", value_number=12.5),
          ComponentAttribute(component_id, "product_size_w", "retailer_spec_block",
                              retailer_id, unit="in", value_number=12.5),
          ComponentAttribute(component_id, "product_size_d", "manufacturer_pdf",
                              manual_id, unit="in", value_number=20.0),
          ComponentAttribute(component_id, "weight_empty", "retailer_spec_block",
                              retailer_id, unit="lb", value_number=36.0),
      ]
      return component, identifiers, attributes
  ```

- [ ] **Step 4: Run self-test to see it pass**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `self_test: PASS`

- [ ] **Step 5: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py
  git commit -m "Resolve IW60RL component from observations #13/#14"
  ```

---

### Task 3: Atwood family placeholder components

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Produces: `resolve_atwood_family_components(manual_row, component_ids) ->
  dict[str, tuple(Component, list[Identifier], list[ComponentAttribute])]`
  keyed by `"6gal"`/`"10gal"`, used by Tasks 5 and 6.

- [ ] **Step 1: Add failing self-test assertions**

  ```python
  atwood_ids = {"6gal": "c_placeholder_wh_atwood_6gal",
                "10gal": "c_placeholder_wh_atwood_10gal"}
  atwood = resolve_atwood_family_components(obs14, atwood_ids)
  if set(atwood) != {"6gal", "10gal"}:
      failures.append(f"Atwood family set mismatch: {set(atwood)}")
  for key, gallons in (("6gal", 6.0), ("10gal", 10.0)):
      component, identifiers, attributes = atwood[key]
      if component.component_id != atwood_ids[key] or component.part_type_id != \
              WATER_HEATER_PART_TYPE:
          failures.append(f"Atwood {key} component mismatch: {component}")
      if identifiers != []:
          failures.append(f"Atwood {key} should have no identifiers: {identifiers}")
      actual = {a.name: (a.value_text if a.value_text is not None else a.value_number,
                         a.provenance, a.source_observation_id) for a in attributes}
      expected = {
          "capacity_gal": (gallons, "manufacturer_pdf", 14),
          "brand": ("Atwood", "manufacturer_pdf", 14),
      }
      if actual != expected:
          failures.append(f"Atwood {key} attributes mismatch: {actual}")

  try:
      resolve_atwood_family_components(
          changed_row(obs14, lambda e: e["replacement_panel_part_numbers"].pop()),
          atwood_ids)
      failures.append("invalid Atwood evidence accepted")
  except ValueError:
      pass
  ```

- [ ] **Step 2: Run self-test to see it fail**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `NameError: name 'resolve_atwood_family_components' is not defined`

- [ ] **Step 3: Implement `resolve_atwood_family_components`**

  ```python
  def resolve_atwood_family_components(manual_row, component_ids):
      _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
      manual = json.loads(manual_row["extracted"])
      panels = manual.get("replacement_panel_part_numbers")
      if not isinstance(panels, list):
          raise ValueError("IW60RL manual has no replacement panel table")
      by_capacity = {
          (panel.get("brand"), panel.get("capacities")): panel.get("part_number")
          for panel in panels
      }
      if by_capacity.get(("Atwood", "6 gallon")) != "521147":
          raise ValueError("manual is missing the Atwood 6-gallon replacement panel")
      if by_capacity.get(("Atwood", "10 gallon")) != "521150":
          raise ValueError("manual is missing the Atwood 10-gallon replacement panel")
      if set(component_ids) != {"6gal", "10gal"}:
          raise ValueError(f"unexpected Atwood component id map: {component_ids}")

      obs_id = manual_row["id"]
      results = {}
      for key, gallons in (("6gal", 6.0), ("10gal", 10.0)):
          component_id = component_ids[key]
          component = Component(component_id, WATER_HEATER_PART_TYPE)
          attributes = [
              ComponentAttribute(component_id, "capacity_gal", "manufacturer_pdf",
                                  obs_id, value_number=gallons),
              ComponentAttribute(component_id, "brand", "manufacturer_pdf",
                                  obs_id, value_text="Atwood"),
          ]
          results[key] = (component, [], attributes)
      return results
  ```

- [ ] **Step 4: Run self-test to see it pass**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `self_test: PASS`

- [ ] **Step 5: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py
  git commit -m "Resolve Atwood 6/10-gallon family placeholders from observation #14"
  ```

---

### Task 4: Cross-capacity substitution edge (SW6DEL -> SW12DEL)

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`
- Modify: `Docs/Tools/interchange_store.py` (add `get_required_parts_for_edge`,
  needed by Task 5, not this task — add now since both tasks touch the same
  file region; harmless if unused until Task 5).

**Interfaces:**
- Consumes: `insert_edge`, `insert_substitution_detail`, `insert_caveat`,
  `insert_evidence`, `prior_for_basis`, `compute_confidence`.
- Produces: `resolve_cross_capacity_edge(conn, review_row, from_id, to_id,
  group_key) -> (edge_a_to_b_id, edge_b_to_a_id)`, used by Task 6.

- [ ] **Step 1: Add `get_required_parts_for_edge` to `interchange_store.py`**

  Add after `insert_required_part` (line 183):

  ```python
  def get_required_parts_for_edge(conn, edge_id):
      rows = conn.execute(
          "SELECT * FROM edge_required_part WHERE edge_id = ?", (edge_id,)).fetchall()
      return [EdgeRequiredPart(id=r["id"], edge_id=r["edge_id"], ns=r["ns"],
                                value=r["value"], role=r["role"]) for r in rows]
  ```

- [ ] **Step 2: Add failing self-test assertions**

  ```python
  edge_6del_to_12del, edge_12del_to_6del = resolve_cross_capacity_edge(
      store_conn, obs11, "c_placeholder_wh_6del", "c_placeholder_wh_12del",
      "cross_capacity_upgrade")

  forward_detail = store_conn.execute(
      "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
      (edge_6del_to_12del,)).fetchone()
  if forward_detail["verdict"] != "fits_with_modification":
      failures.append(f"6DEL->12DEL should be fits_with_modification: {forward_detail}")
  forward_caveats = get_caveats_for_edge(store_conn, edge_6del_to_12del)
  if len(forward_caveats) != 2 or sum(c.blocking for c in forward_caveats) != 1:
      failures.append(f"6DEL->12DEL should have 2 caveats, 1 blocking: {forward_caveats}")

  backward_detail = store_conn.execute(
      "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
      (edge_12del_to_6del,)).fetchone()
  if backward_detail["verdict"] != "not_observed":
      failures.append(f"12DEL->6DEL should be not_observed: {backward_detail}")

  forward_confidence = compute_confidence(
      get_evidence_for_edge(store_conn, edge_6del_to_12del))
  if forward_confidence["value"] != 0.8 or forward_confidence["certainty"] != 5.0:
      failures.append(f"6DEL->12DEL confidence should be 0.8/n=5: {forward_confidence}")

  for mutate, label in (
      (lambda e: e["customer_review"].__setitem__("evidence_type", "hearsay"), "wrong evidence_type"),
      (lambda e: e["customer_review"].__setitem__("verdict", "drop_in"), "wrong verdict"),
      (lambda e: e["customer_review"]["modifications_required"].pop(), "missing modification"),
  ):
      try:
          resolve_cross_capacity_edge(
              init_db(":memory:"), changed_row(obs11, mutate),
              "c_placeholder_wh_6del", "c_placeholder_wh_12del", "cross_capacity_upgrade")
          failures.append(f"invalid cross-capacity evidence accepted: {label}")
      except ValueError:
          pass
  ```

- [ ] **Step 3: Run self-test to see it fail**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `NameError: name 'resolve_cross_capacity_edge' is not defined`

- [ ] **Step 4: Implement `resolve_cross_capacity_edge`**

  ```python
  def resolve_cross_capacity_edge(conn, review_row, from_id, to_id, group_key):
      extracted = json.loads(review_row["extracted"])
      review = extracted.get("customer_review")
      if not isinstance(review, dict):
          raise ValueError(f"observation #{review_row['id']} has no customer_review")
      if review.get("evidence_type") != "buyer_confirmed_install":
          raise ValueError(f"unexpected cross-capacity evidence_type: {review}")
      if review.get("verdict") != "fits_with_modification":
          raise ValueError(f"unexpected cross-capacity verdict: {review}")
      if review.get("modifications_required") != [
              "enlarge cutout from 12.75x12.75 to 16.38x16.38",
              "lengthen bypass line"]:
          raise ValueError(f"unexpected cross-capacity modifications: {review}")

      basis = "buyer_confirmed_install"

      edge_forward = Edge(type="substitutes", from_component_id=from_id,
                           to_component_id=to_id, group_key=group_key)
      insert_edge(conn, edge_forward)
      insert_substitution_detail(conn, EdgeSubstitutionDetail(
          edge_id=edge_forward.id, basis=basis, verdict="fits_with_modification"))
      insert_caveat(conn, EdgeCaveat(
          edge_id=edge_forward.id, blocking=True,
          text="Cutout must be enlarged from 12.75x12.75 to 16.38x16.38. This is not "
               "a same-group substitution — capacities and cutouts differ."))
      insert_caveat(conn, EdgeCaveat(
          edge_id=edge_forward.id, blocking=False,
          text="Bypass line needs to be lengthened."))
      prior_alpha, prior_beta = prior_for_basis(basis)
      insert_evidence(conn, RelationshipEvidence(
          edge_id=edge_forward.id, event_type="attribute_prior",
          effect_alpha=prior_alpha, effect_beta=prior_beta, occurred_at=now_iso()))
      insert_evidence(conn, RelationshipEvidence(
          edge_id=edge_forward.id, event_type="buyer_confirmed_install",
          effect_alpha=3.0, effect_beta=0.0, occurred_at=now_iso(),
          source_observation_id=review_row["id"]))

      edge_backward = Edge(type="substitutes", from_component_id=to_id,
                            to_component_id=from_id, group_key=group_key)
      insert_edge(conn, edge_backward)
      insert_substitution_detail(conn, EdgeSubstitutionDetail(
          edge_id=edge_backward.id, basis=basis, verdict="not_observed"))
      insert_evidence(conn, RelationshipEvidence(
          edge_id=edge_backward.id, event_type="attribute_prior",
          effect_alpha=prior_alpha, effect_beta=prior_beta, occurred_at=now_iso()))

      return edge_forward.id, edge_backward.id
  ```

- [ ] **Step 5: Run self-test to see it pass**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `self_test: PASS`

- [ ] **Step 6: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py Docs/Tools/interchange_store.py
  git commit -m "Resolve SW6DEL->SW12DEL cross-capacity substitution edge from observation #11"
  ```

---

### Task 5: IW60RL manufacturer-documented retrofit edges

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Produces: `resolve_iw60rl_retrofit_edge(conn, manual_row, from_id, to_id,
  group_key, required_part_value) -> edge_id`, used four times by Task 6 (one
  call per source family: SW6DEL, SW12DEL, Atwood 6gal, Atwood 10gal — all
  `to_id` = IW60RL, `from_id` varies, `required_part_value` one of
  `6276APW`/`6277APW`/`521147`/`521150`).

- [ ] **Step 1: Add failing self-test assertions**

  ```python
  retrofit_specs = (
      ("c_placeholder_wh_6del", "iw60_retrofit_suburban_6gal", "6276APW"),
      ("c_placeholder_wh_12del", "iw60_retrofit_suburban_10_12_16gal", "6277APW"),
      ("c_placeholder_wh_atwood_6gal", "iw60_retrofit_atwood_6gal", "521147"),
      ("c_placeholder_wh_atwood_10gal", "iw60_retrofit_atwood_10gal", "521150"),
  )
  retrofit_edge_ids = {}
  for from_id, group_key, part_value in retrofit_specs:
      edge_id = resolve_iw60rl_retrofit_edge(
          store_conn, obs14, from_id, "c_placeholder_wh_iw60rl", group_key, part_value)
      retrofit_edge_ids[group_key] = edge_id

      detail = store_conn.execute(
          "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
          (edge_id,)).fetchone()
      if detail["verdict"] != "fits_with_modification":
          failures.append(f"{group_key} verdict mismatch: {detail}")
      caveats = get_caveats_for_edge(store_conn, edge_id)
      if len(caveats) != 2 or not all(c.blocking for c in caveats):
          failures.append(f"{group_key} should have 2 blocking caveats: {caveats}")
      parts = get_required_parts_for_edge(store_conn, edge_id)
      if [(p.ns, p.value, p.role) for p in parts] != [
              ("suburban", part_value, "replacement_panel")]:
          failures.append(f"{group_key} required part mismatch: {parts}")
      confidence = compute_confidence(get_evidence_for_edge(store_conn, edge_id))
      if confidence["value"] != 0.833:
          failures.append(f"{group_key} confidence value mismatch: {confidence}")

  for mutate, label in (
      (lambda e: e["replacement_panel_part_numbers"].pop(), "missing panel row"),
      (lambda e: e.__setitem__("vent_cap_ordered_separately", False), "wrong vent cap flag"),
  ):
      try:
          resolve_iw60rl_retrofit_edge(
              init_db(":memory:"), changed_row(obs14, mutate),
              "c_placeholder_wh_6del", "c_placeholder_wh_iw60rl",
              "iw60_retrofit_suburban_6gal", "6276APW")
          failures.append(f"invalid IW60RL retrofit evidence accepted: {label}")
      except ValueError:
          pass
  ```

- [ ] **Step 2: Run self-test to see it fail**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `NameError: name 'resolve_iw60rl_retrofit_edge' is not defined`

- [ ] **Step 3: Implement `resolve_iw60rl_retrofit_edge`**

  ```python
  _IW60RL_PANEL_ROLE = "replacement_panel"
  _IW60RL_PANEL_BY_VALUE = {
      "6276APW": ("Suburban", "6 gallon"),
      "6277APW": ("Suburban", "10, 12, 16 gallon"),
      "521147": ("Atwood", "6 gallon"),
      "521150": ("Atwood", "10 gallon"),
  }


  def resolve_iw60rl_retrofit_edge(conn, manual_row, from_id, to_id, group_key,
                                   required_part_value):
      _validate_observation_source(manual_row, 14, "manufacturer_pdf", 2, "IW60RL manual")
      manual = json.loads(manual_row["extracted"])
      if manual.get("vent_cap_ordered_separately") is not True:
          raise ValueError("IW60RL manual must confirm the vent cap ships separately")
      panels = manual.get("replacement_panel_part_numbers")
      if not isinstance(panels, list):
          raise ValueError("IW60RL manual has no replacement panel table")
      expected_brand, expected_capacities = _IW60RL_PANEL_BY_VALUE[required_part_value]
      matches = [p for p in panels if p.get("part_number") == required_part_value
                 and p.get("brand") == expected_brand
                 and p.get("capacities") == expected_capacities]
      if len(matches) != 1:
          raise ValueError(
              f"IW60RL manual is missing the {required_part_value} replacement panel row")

      edge = Edge(type="substitutes", from_component_id=from_id,
                  to_component_id=to_id, group_key=group_key)
      insert_edge(conn, edge)
      insert_substitution_detail(conn, EdgeSubstitutionDetail(
          edge_id=edge.id, basis="manufacturer_documented",
          verdict="fits_with_modification"))
      insert_caveat(conn, EdgeCaveat(
          edge_id=edge.id, blocking=True,
          text=f"Existing tank cutout is COVERED by replacement panel "
               f"{required_part_value}, not resized. A new 3.750in vent hole must "
               f"still be cut."))
      insert_caveat(conn, EdgeCaveat(
          edge_id=edge.id, blocking=True,
          text=f"Replacement panel ({required_part_value}) must be ordered "
               f"separately from the IW60RL unit itself."))
      insert_required_part(conn, EdgeRequiredPart(
          edge_id=edge.id, ns="suburban", value=required_part_value,
          role=_IW60RL_PANEL_ROLE))

      prior_alpha, prior_beta = prior_for_basis("manufacturer_documented")
      insert_evidence(conn, RelationshipEvidence(
          edge_id=edge.id, event_type="attribute_prior", effect_alpha=prior_alpha,
          effect_beta=prior_beta, occurred_at=now_iso()))
      insert_evidence(conn, RelationshipEvidence(
          edge_id=edge.id, event_type="manufacturer_documented", effect_alpha=4.0,
          effect_beta=0.0, occurred_at=now_iso(), source_observation_id=manual_row["id"]))

      return edge.id
  ```

  Add `EdgeRequiredPart` to the `interchange_models` import list at the top of
  `edge_resolver.py`.

- [ ] **Step 4: Run self-test to see it pass**

  Run: `cd Docs/Tools && python3 edge_resolver.py --self-test`
  Expected: `self_test: PASS`

- [ ] **Step 5: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py
  git commit -m "Resolve four IW60RL manufacturer-documented retrofit edges from observation #14"
  ```

---

### Task 6: Wire everything into `check_fixture()`

**Files:**
- Modify: `Docs/Tools/edge_resolver.py`

**Interfaces:**
- Consumes: all five builder/resolver functions from Tasks 1-5.
- Produces: extended `check_fixture()` — no new public interface, this is the
  fixture-reproduction wiring.

- [ ] **Step 1: Add the resolution + comparison block to `check_fixture()`**

  After the existing Coleman-endpoints block (just before the final
  `print(f"\n{mismatches} total mismatches...")`), add:

  ```python
  suburban_remainder_mismatches_before = mismatches
  obs11 = load_observation(obs_db_path, 11)
  obs13 = load_observation(obs_db_path, 13)
  obs14 = load_observation(obs_db_path, 14)
  obs35 = load_observation(obs_db_path, 35)

  comp_12del, ids_12del, attrs_12del = resolve_12del_component(
      obs11, obs35, "c_placeholder_wh_12del")
  comp_iw60rl, ids_iw60rl, attrs_iw60rl = resolve_iw60rl_component(
      obs13, obs14, "c_placeholder_wh_iw60rl")
  atwood_ids = {"6gal": "c_placeholder_wh_atwood_6gal",
                "10gal": "c_placeholder_wh_atwood_10gal"}
  atwood = resolve_atwood_family_components(obs14, atwood_ids)

  for component, identifiers, attributes in (
      (comp_12del, ids_12del, attrs_12del),
      (comp_iw60rl, ids_iw60rl, attrs_iw60rl),
      *atwood.values(),
  ):
      insert_component(conn, component)
      for identifier in identifiers:
          insert_identifier(conn, identifier)
      for attribute in attributes:
          insert_component_attribute(conn, attribute)

  remainder_component_ids = {
      "c_placeholder_wh_12del": comp_12del.component_id,
      "c_placeholder_wh_iw60rl": comp_iw60rl.component_id,
      "c_placeholder_wh_atwood_6gal": atwood["6gal"][0].component_id,
      "c_placeholder_wh_atwood_10gal": atwood["10gal"][0].component_id,
  }
  for fixture_component_id in remainder_component_ids:
      fixture_component = next(
          (c for c in components_doc if c.get("component_id") == fixture_component_id),
          None)
      if fixture_component is None:
          print(f"MISMATCH fixture is missing component: {fixture_component_id}")
          mismatches += 1
          continue
      resolved_identifiers = {
          (row["ns"], row["value"], row["visibility"])
          for row in conn.execute(
              "SELECT ns, value, visibility FROM identifiers WHERE component_id = ?",
              (fixture_component_id,)).fetchall()
      }
      expected_identifiers = {
          (i["ns"], str(i["value"]), i.get("visibility"))
          for i in fixture_component.get("identifiers", [])
      }
      if resolved_identifiers != expected_identifiers:
          print(f"MISMATCH {fixture_component_id} identifiers: "
                f"resolved={resolved_identifiers} fixture={expected_identifiers}")
          mismatches += 1

  edge_6del_to_12del, edge_12del_to_6del = resolve_cross_capacity_edge(
      conn, obs11, "c_placeholder_wh_6del", "c_placeholder_wh_12del",
      "cross_capacity_upgrade")
  fixture_cross_capacity = _find_fixture_edge(
      edges_doc, "c_placeholder_wh_6del", "c_placeholder_wh_12del")
  if fixture_cross_capacity is None:
      print("MISMATCH ground-truth.yaml has no 6DEL->12DEL substitutes edge")
      mismatches += 1
  else:
      resolved_verdict = conn.execute(
          "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
          (edge_6del_to_12del,)).fetchone()["verdict"]
      if resolved_verdict != fixture_cross_capacity["a_to_b"]["verdict"]:
          print(f"MISMATCH 6DEL->12DEL verdict: fixture="
                f"{fixture_cross_capacity['a_to_b']['verdict']} resolved={resolved_verdict}")
          mismatches += 1
      resolved_value = compute_confidence(
          get_evidence_for_edge(conn, edge_6del_to_12del))["value"]
      if resolved_value != fixture_cross_capacity["confidence"]["value"]:
          print(f"MISMATCH 6DEL->12DEL confidence value: fixture="
                f"{fixture_cross_capacity['confidence']['value']} resolved={resolved_value}")
          mismatches += 1

  retrofit_specs = (
      ("c_placeholder_wh_6del", "iw60_retrofit_suburban_6gal", "6276APW"),
      ("c_placeholder_wh_12del", "iw60_retrofit_suburban_10_12_16gal", "6277APW"),
      ("c_placeholder_wh_atwood_6gal", "iw60_retrofit_atwood_6gal", "521147"),
      ("c_placeholder_wh_atwood_10gal", "iw60_retrofit_atwood_10gal", "521150"),
  )
  for from_id, group_key, part_value in retrofit_specs:
      edge_id = resolve_iw60rl_retrofit_edge(
          conn, obs14, from_id, "c_placeholder_wh_iw60rl", group_key, part_value)
      fixture_edge = next(
          (e for e in edges_doc if e.get("group") == group_key), None)
      if fixture_edge is None:
          print(f"MISMATCH ground-truth.yaml has no {group_key} edge")
          mismatches += 1
          continue
      resolved_verdict = conn.execute(
          "SELECT verdict FROM edge_substitution_detail WHERE edge_id = ?",
          (edge_id,)).fetchone()["verdict"]
      if resolved_verdict != fixture_edge["a_to_b"]["verdict"]:
          print(f"MISMATCH {group_key} verdict: fixture="
                f"{fixture_edge['a_to_b']['verdict']} resolved={resolved_verdict}")
          mismatches += 1
      resolved_value = compute_confidence(get_evidence_for_edge(conn, edge_id))["value"]
      if resolved_value != fixture_edge["confidence"]["value"]:
          print(f"MISMATCH {group_key} confidence value: fixture="
                f"{fixture_edge['confidence']['value']} resolved={resolved_value}")
          mismatches += 1
      print(f"  {group_key}: certainty is a hand-authored fixture dial "
            f"(fixture={fixture_edge['confidence']['certainty']}), not compared — "
            f"see 'Known fixture inconsistency' in the plan doc")

  print(f"Suburban remaining fixtures: "
        f"{mismatches - suburban_remainder_mismatches_before} mismatch(es)")
  print("NOTE: c_placeholder_wh_switch (232882/233111/232881) and its `controls` "
        "edge remain UNRESOLVED — no observation in observations.db backs those "
        "identifiers. Not counted as a mismatch; requires new evidence capture.")
  ```

- [ ] **Step 2: Run fixture check**

  Run: `cd Docs/Tools && python3 edge_resolver.py --check-fixture ../Inital_Design/ground-truth.yaml`
  Expected: `0 total mismatches against ground-truth.yaml`, plus the printed
  NOTE about the interior switch.

- [ ] **Step 3: Run the full test suite**

  Run: `cd Docs/Tools && python3 -m pytest -q && python3 edge_resolver.py --self-test`
  Expected: all green.

- [ ] **Step 4: Commit**

  ```bash
  git add Docs/Tools/edge_resolver.py
  git commit -m "Wire remaining Suburban fixture components/edges into check_fixture"
  ```

---

### Task 7: Update `VENDOR-Suburban.md` §8 and `PLAN-Staged_Build.md`

**Files:**
- Modify: `Docs/Data/Suburban/VENDOR-Suburban.md` (§8 definition-of-done)
- Modify: `Docs/Inital_Design/PLAN-Staged_Build.md` (§9 next actions)

- [ ] **Step 1: Flip §8's `[~]` line to `[x]`**, noting the one remaining gap
  (interior switch has no observation yet) as its own explicit sub-bullet
  rather than leaving it folded into a partial checkbox.

- [ ] **Step 2: Add a dated entry to `PLAN-Staged_Build.md` §9** recording
  that the SW12DEL, IW60RL, and both Atwood placeholder components plus the
  cross-capacity and four retrofit edges are now resolved and fixture-verified
  (0 mismatches), and that `c_placeholder_wh_switch` remains the sole open
  item pending a new observation (e.g. a data-plate photo of one of
  232882/233111/232881).

- [ ] **Step 3: Commit**

  ```bash
  git add Docs/Data/Suburban/VENDOR-Suburban.md Docs/Inital_Design/PLAN-Staged_Build.md
  git commit -m "Mark Suburban §8 full-fixture reproduction done; flag interior switch gap"
  ```
