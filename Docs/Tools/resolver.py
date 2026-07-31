#!/usr/bin/env python3
"""
resolver.py — normalizes observations.extracted blobs into a canonical
vocabulary, so the observations -> components/edges pipeline can be written
against stable field names instead of whatever a given observation happened
to call something.

THE PROBLEM THIS SOLVES
------------------------
`extracted` was deliberately specified with no schema at insert time — "your
best-effort guess" (see observations.py's module docstring). That was the
right call architecturally: a schema fixed at observation #1 would have been
wrong by observation #5, and the two-table design exists precisely so the
mess lives in the append-only layer and gets normalized downstream, not
re-litigated per record. But it does mean the resolver cannot be written
against raw field names.

Measured at 35 observations: 175 distinct top-level keys, 132 of which
appear exactly once. The same attribute goes by several names — heat input
is `btu` and `input_btuh`; the product envelope appears as `product_size_in`,
`product_size_hwd`, `unit_in`, and `dimensions_in`. That's the two-table
design working as intended, not failing — this module is the normalization
step it was always going to need.

THREE-WAY CLASSIFICATION
-------------------------
Every raw key that has ever appeared in `extracted` is classified exactly
one of three ways:

  1. ALIASES        — maps to a canonical attribute name. The resolver can
                       rely on the canonical name existing.
  2. IGNORED_KEYS    — reviewed and deliberately excluded, with a reason.
                       Usually research narrative (a `note`, a `context`, a
                       conflict flag already superseded by an append-only
                       correction) or data that's real but out of the water
                       heater resolver's scope (furnace/cooktop grammar
                       captured incidentally on the same chart image).
  3. unmapped        — anything not in the first two buckets. This is a
                       hard error (`classify_keys(strict=True)`, the
                       default), not a silent drop. The 132 one-off keys
                       contain both noise and real findings recorded once;
                       forcing a decision beats losing one quietly.

New observations will introduce new raw keys the classifier hasn't seen.
That is supposed to raise. Add the key to ALIASES or IGNORED_KEYS (with a
reason) and move on — that's the cost of the two-table design paying off
correctly, not a bug in this module.

MECHANICAL CORRECTIONS
-----------------------
Two things that used to live only in prose (VENDOR-Suburban.md) and would
otherwise get re-litigated per record are now code:

  - cutout_* blobs (`cutout_in`, `cutout_hwd`, `cutout_in_6gal`,
    `cutout_in_10gal`, `figure_1_framed_opening_in`, and the lone
    `cutout_confirmed_depth_in`) all collapse to `opening_h` / `opening_w`.
    Any third (depth) figure is DROPPED and logged in `dropped`, never kept
    as `opening_d` — see VENDOR-Suburban.md 6.5: there is no such dimension.

  - `weight_lb` (a combined {empty, full} blob) and its already-split
    cousins (`weight_empty_lb`, `weight_full_lb`) both resolve to the same
    two canonical fields.

  - `recovery_gph` ({gas_electric, electric_only}) splits into
    `recovery_gas_electric_gph` / `recovery_electric_only_gph`.

SOURCE TIER
-----------
`observations.source_tier` (INTEGER, 1=best) makes trust ranking a field the
resolver can sort on, instead of something inferred from `source_type` plus
prose on every conflict. See TIER_DEFAULTS / TIER_OVERRIDES / infer_source_tier
below. `--assign-tiers` backfills it for existing rows; new observations
should get one at insert time.

USAGE
-----
    python3 resolver.py --validate ../Tools/observations.db   # classify every
                                                                # extracted key
                                                                # in the db;
                                                                # non-zero exit
                                                                # on unmapped
    python3 resolver.py --show 4 --db observations.db          # normalized
                                                                 # view of one
                                                                 # observation
    python3 resolver.py --assign-tiers --db observations.db    # backfill
                                                                 # source_tier
    python3 resolver.py --self-test
"""

import argparse
import json
import sqlite3
import sys

# ==========================================================================
# Canonical vocabulary
# ==========================================================================

CANONICAL = {
    # identity
    "model":                    "SW-series model number as printed/claimed",
    "sku":                      "manufacturer catalog SKU",
    "vendor_catalog_number":        "a retailer/distributor's own catalog number (not a manufacturer SKU)",
    "vendor_catalog_number_legacy": "same, explicitly flagged by the source as superseded",
    "upc":                      "UPC barcode",
    "sku_relationship":         "structured relationship between two SKUs (e.g. co-current channel split)",
    "sku_renumbering_pattern":  "a documented SKU renumbering rule (e.g. the +100 pattern)",
    "model_sku_table":          "dict of {model: sku} captured from one source",
    "models_named_list":        "list of model names a source names without full specs",
    "model_spec_table":         "dict of {model: {spec fields}} from a multi-model chart",
    "model_spec_table_columns": "column headers paired with a model_spec_table (from 'rows')",
    "suffix_grammar_table":     "dict of {suffix letter: meaning} from a grammar chart",
    "discontinuation_info":     "lifecycle info (approx. discontinuation year + basis)",
    "lifecycle_status":         "e.g. 'discontinued'",
    "family_availability_constraint": "which suffixes/capacities a source says do NOT exist together",

    # capacity / heat / element
    "capacity_gal":              "nominal tank capacity in US gallons",
    "capacity_sizes_available":  "list of capacities a family is offered at",
    "input_btuh":                "gas heat input, BTU/hr",
    "element_watts":             "electric element wattage",
    "heating_element_description": "free-text description of the element (e.g. '120v AC')",
    "ignition_type":             "free-text ignition system description",
    "optional_equipment":        "equipment a source says is optional, not standard",
    "has_relay_claim":           "source's own claim of interior-relay presence",
    "has_interior_switch_claim": "source's own claim of an interior switch",
    "corded_claim":              "source's own claim of corded (vs hardwired) power",
    "portable_claim":            "source's own claim the unit is portable",
    "marine_claim":              "source's own claim of marine (non-RV) applicability",
    "chassis_constraint_claim":  "source's own statement of a chassis constraint (e.g. motorhome-only)",
    "gas_control_valve_type":    "e.g. 'adjustable'",
    "anode_type":                "anode rod description",
    "tank_liner":                "tank liner material (e.g. porcelain)",
    "tank_material":             "tank shell material (e.g. steel, aluminum)",
    "product_type":              "free-text product type/category claim",
    "product_line":              "product line name",
    "material":                  "generic component material",
    "markings":                  "physical markings observed on a part",
    "shape":                     "physical shape observed on a part",
    "minimum_clearance":         "minimum clearance from combustibles",
    "serial_number_format":      "documented serial-number format (e.g. YYWWNNNNN)",

    # dimensions — mechanically derived, see _derive_opening / _derive_product
    "opening_h":                 "framed installation opening height, in — 2D only",
    "opening_w":                 "framed installation opening width, in — 2D only",
    "product_hwd":               "unit product envelope {h, w, d}, in — NOT the opening",
    "vent_hole_diameter_in":     "tankless vent hole diameter, in",
    "duct_diameter_in":          "duct diameter, in (accessory-level measurement)",

    # weight — mechanically derived, see _derive_weight
    "weight_empty_lb":           "net empty weight, lb",
    "weight_full_lb":            "net full (water-filled) weight, lb",
    "weight_shipping_default_lb": "cart/shipping-default weight — NOT a net weight, see VENDOR-Suburban.md 6.3",
    "weight_dry_approx_lb":      "third-party approximate dry weight, lower confidence",

    # recovery — mechanically derived, see _derive_recovery
    "recovery_gas_electric_gph": "combined gas+electric recovery rate, gal/hr",
    "recovery_gas_only_gph":     "gas-only recovery rate, gal/hr",
    "recovery_electric_only_gph": "electric-only recovery rate, gal/hr",

    # warranty / door
    "warranty_heater":           "heater warranty term",
    "warranty_tank":             "tank-specific warranty term",
    "door_style":                "door style (e.g. flush)",
    "door_style_by_capacity":    "dict of {capacity: [door styles]}",
    "door_style_constraint":     "free-text door-style availability rule",

    # accessory / cross-sell — real, but out of scope for tank-identity
    # resolution; kept as one bucket so it isn't lost, not expanded into
    # the tank vocabulary above. Revisit when building accessory edges
    # (VENDOR-Suburban.md 5.2/5.5).
    "accessory_data":            "accessory/cross-sell finding out of scope for the tank resolver",

    # provenance-adjacent but still real content
    "alt_text_claim":            "an image alt/title-text attribute's claim — LOW trust, see VENDOR-Suburban.md 6.1",
    "customer_review":           "structured field-evidence review {reviewer, date, rating, text}",
    "source_statement":          "a direct quote/paraphrase of what a source said, load-bearing for a finding",

    # document metadata — real, but about the source, not the product
    "source_document_title":     "title of the source document",
    "source_document_type":      "e.g. 'spec_sheet_table'",
    "source_document_pages":     "page count",
    "source_document_publisher": "publisher of the source document",
    "source_pdf_page_stats":     "PDF text-layer stats used to decide whether OCR was needed",
    "source_extraction_method_detail": "detail on how text was pulled (e.g. OCR pipeline used)",
    "source_capture_method":     "how the document was captured (e.g. via a mirror/archive)",
}

# --------------------------------------------------------------------------
# ALIASES — raw extracted-blob key -> canonical name.
#
# Compound keys that need splitting (cutout blobs, weight_lb, recovery_gph)
# are handled specially in normalize_extracted() and are NOT simple 1:1
# aliases; they're listed in _COMPOUND_KEYS below instead, but every one of
# them still needs an entry here or there so the completeness check in
# --validate has something to point at. See _COMPOUND_KEYS.
# --------------------------------------------------------------------------

ALIASES = {
    # identity
    "model": "model",
    "sku": "sku",
    "sku_per_page": "sku",
    "url_path_sku": "sku",
    "skus": "sku",
    "aliases_mentioned": "sku",
    "item_number": "vendor_catalog_number",
    "vendor_number": "vendor_catalog_number",
    "ppl_item": "vendor_catalog_number",
    "ppl_item_old": "vendor_catalog_number_legacy",
    "upc": "upc",
    "relation": "sku_relationship",
    "renumbering_pattern": "sku_renumbering_pattern",
    "models_sku_only": "model_sku_table",
    "new_skus_found": "model_sku_table",
    "sibling_skus_seen": "model_sku_table",
    "models_named": "models_named_list",
    "models_covered": "models_named_list",
    "models": "model_spec_table",
    "rows": "model_spec_table",
    "columns": "model_spec_table_columns",
    "model_options_full": "suffix_grammar_table",
    "grammar_confirmed_in_page_text": "suffix_grammar_table",
    "SW3P_discontinuation": "discontinuation_info",
    "status": "lifecycle_status",
    "new_finding_4gal_lineup": "family_availability_constraint",

    # capacity / heat / element
    "capacity_gal": "capacity_gal",
    "gallon": "capacity_gal",
    "capacity_sizes_gal": "capacity_sizes_available",
    "btu": "input_btuh",
    "input_btuh": "input_btuh",
    "element_watts": "element_watts",
    "electric_element_w": "element_watts",
    "wattage": "element_watts",
    "heating_element": "heating_element_description",
    "ignition": "ignition_type",
    "ignition_type": "ignition_type",
    "optional": "optional_equipment",
    "interior_relay": "has_relay_claim",
    "with_switch": "has_interior_switch_claim",
    "corded": "corded_claim",
    "portable": "portable_claim",
    "marine": "marine_claim",
    "dem_constraint": "chassis_constraint_claim",
    "gas_control_valve": "gas_control_valve_type",
    "anode": "anode_type",
    "liner": "tank_liner",
    "tank": "tank_material",
    "type": "product_type",
    "product_line": "product_line",
    "material": "material",
    "markings": "markings",
    "shape": "shape",
    "minimum_clearance": "minimum_clearance",
    "serial_breakdown": "serial_number_format",

    # dimensions — plain product envelope (opening/cutout handled specially)
    "product_size_in": "product_hwd",
    "product_size_hwd": "product_hwd",
    "unit_in": "product_hwd",
    "dimensions_in": "product_hwd",
    "vent_hole_diameter_in": "vent_hole_diameter_in",
    "duct_diameter_in": "duct_diameter_in",

    # weight — split fields pass straight through; weight_lb is compound
    "weight_empty_lb": "weight_empty_lb",
    "weight_full_lb": "weight_full_lb",
    "weight_cart_field_lb": "weight_shipping_default_lb",
    "weight_dry_approx_lb": "weight_dry_approx_lb",

    # recovery — split fields pass straight through; recovery_gph is compound
    "recovery_gas_gph": "recovery_gas_only_gph",
    "recovery_electric_gph": "recovery_electric_only_gph",
    "recovery_electric_gph_additional": "recovery_electric_only_gph",

    # warranty / door
    "warranty": "warranty_heater",
    "tank_warranty": "warranty_tank",
    "door_style": "door_style",
    "door_types": "door_style_by_capacity",
    "door_constraint": "door_style_constraint",

    # accessory / cross-sell bucket
    "accessories": "accessory_data",
    "accessory_findings": "accessory_data",
    "doors_cross_sold": "accessory_data",
    "replacement_panel_part_numbers": "accessory_data",
    "replacement_panel_use_case": "accessory_data",
    "vent_cap_part_numbers": "accessory_data",
    "vent_cap_ordered_separately": "accessory_data",
    "vent_hole_note": "accessory_data",
    "vent_overlap_min_in": "accessory_data",
    "aluminum_tank_kits_corroborated": "accessory_data",
    "required_items": "accessory_data",
    "replaces": "accessory_data",
    "installation_without_replacement_panel": "accessory_data",
    "cutout_required": "accessory_data",

    # provenance-adjacent real content
    "alt_text": "alt_text_claim",
    "customer_review": "customer_review",
    "explanation": "source_statement",
    "quoted_text": "source_statement",

    # document metadata
    "doc": "source_document_title",
    "manual_title": "source_document_title",
    "doc_type": "source_document_type",
    "pages": "source_document_pages",
    "publisher": "source_document_publisher",
    "_pdf_pages": "source_pdf_page_stats",
    "ocr_method": "source_extraction_method_detail",
    "captured_via": "source_capture_method",
}

# --------------------------------------------------------------------------
# Compound keys — raw key -> the canonical field(s) it splits into, plus the
# handler that does the splitting. Listed here (not just in ALIASES) so
# --validate's completeness check treats them as classified.
# --------------------------------------------------------------------------

_CUTOUT_KEYS = {
    "cutout_in", "cutout_hwd", "cutout_in_6gal", "cutout_in_10gal",
    "figure_1_framed_opening_in", "cutout_confirmed_depth_in",
}
_WEIGHT_COMPOUND_KEYS = {"weight_lb"}
_RECOVERY_COMPOUND_KEYS = {"recovery_gph"}

_COMPOUND_KEYS = _CUTOUT_KEYS | _WEIGHT_COMPOUND_KEYS | _RECOVERY_COMPOUND_KEYS

# --------------------------------------------------------------------------
# IGNORED_KEYS — reviewed, deliberately excluded, reason given. This is the
# record of a decision, not a silent drop. Grouped by why.
# --------------------------------------------------------------------------

IGNORED_KEYS = {
    # research narrative / conflict flags already superseded by an
    # append-only correction elsewhere — the resolved data lives under a
    # real canonical key in the same or a later observation.
    "CONFLICTS_WITH_OBS_1_AND_2": "narrative conflict flag; resolution lives in a later observation",
    "DEFINITIVE_FINDING_framed_opening_is_2D": "narrative evidence annotation; the rule itself is encoded in the parser (OPENING_FAMILIES)",
    "NEW_CONFLICT": "narrative conflict flag",
    "ONLY_TWO_OPENING_FAMILIES": "narrative finding; structural fact already encoded in the parser",
    "RESOLVES": "narrative resolution annotation",
    "closes_gaps": "narrative summary of what an observation closed",
    "confirms": "narrative confirmation prose",
    "confirms_dm_is_real": "narrative prose; the underlying fact is captured via 'model'",
    "confirms_dm_meaning": "narrative prose; restates the suffix grammar already encoded structurally",
    "content": "narrative description of what a document contains",
    "context": "narrative context",
    "cover_list_claim": "narrative unverified claim, not yet independently confirmed",
    "coverage_gap_note": "narrative",
    "cross_validated": "meta flag about the observation, not a product attribute",
    "cross_validated_against": "meta pointer to another observation",
    "data_quality_flag": "narrative note about a known artifact in a source document",
    "dimension_kind_basis": "narrative justification for a dimension_kind classification",
    "dimension_note": "narrative",
    "door_note": "narrative",
    "key_findings": "narrative summary",
    "new_data": "narrative summary",
    "new_family_found": "narrative announcement; structured data captured via other keys in the same observation",
    "new_family_revealed": "narrative announcement",
    "new_suffix_found": "narrative announcement; the suffix itself is captured via 'model'",
    "no_16gal_D_line_sibling_in_cross_sell": "narrative negative finding",
    "no_dimension_data_recovered": "meta flag",
    "no_dimension_table": "meta flag",
    "no_top_level_sku_or_dimensions": "meta flag",
    "note": "generic narrative catch-all",
    "note_no_cutout_column": "meta flag",
    "opening_confirmation": "narrative; redundant with the structurally-encoded opening rule",
    "parts_list_claim": "narrative unverified claim",
    "resolves_conflict": "narrative",
    "same_document_as": "narrative/meta pointer to another observation",
    "seo_metadata_contradiction": "narrative data-quality curiosity, not a product attribute",
    "significance": "narrative",
    "significant_negative_finding": "narrative",
    "sku_conflict": "narrative; conflicts are tracked by the append-only log itself, not duplicated here",
    "sku_conflict_flagged": "narrative",
    "sku_status": "narrative prose about SKU absence",
    "supersedes_prior_reading": "narrative pointer to a superseded reading",
    "third_party_terminology_error": "narrative data-quality note about a competitor's mislabeling",
    "warranty_conflict_RESOLVED": "narrative",
    "water_heater_chart": "narrative confirmation, no new info per the observation itself",
    "weight_source": "narrative provenance note for weight_dry_approx_lb",
    "action_needed": "narrative TODO, not product data",
    "all_text": "meta flag about extraction completeness",
    "also_captured_incidentally": "narrative pointer",
    "asymmetric_substitution_direction": "narrative framing of an edge; the edge logic itself lives in the parser's compare_models()",
    "btu_missing_from_source": "meta flag (absence, not data)",
    "cutout_depth_note": "narrative explaining a depth drop; the drop itself is now mechanical, see _derive_opening",
    "depth_missing_from_source": "meta flag",
    "dimension_kind": "narrative classification note; superseded by the mechanical cutout/product split",
    "wattage_missing_from_source": "meta flag",
    "weight_cart_field_is_shipping_default_not_net_weight": "meta flag; the value itself is weight_cart_field_lb",

    # out of scope: furnace/cooktop grammar captured incidentally on the
    # same chart image as the water heater grammar. Real data, wrong
    # resolver — revisit if a furnace/cooktop resolver gets built.
    "cooktop_chart_1_era": "out of scope: cooktop family, not water heater",
    "cooktop_chart_2_era": "out of scope: cooktop family, not water heater",
    "cooktop_grammar_may_differ_between_eras": "out of scope: cooktop family, not water heater",
    "cooktop_two_distinct_charts": "out of scope: cooktop family, not water heater",
    "furnace_grammar_structure": "out of scope: furnace family, not water heater",
    "furnace_letter_meanings_confirmed": "out of scope: furnace family, not water heater",
    "furnace_series_seen": "out of scope: furnace family, not water heater",

    # source-tier inputs — consumed directly by infer_source_tier(), not a
    # generic product attribute.
    "trust_tier": "consumed directly by infer_source_tier(), not a product attribute",
    "source_tier": "consumed directly by infer_source_tier(), not a product attribute",
    "confidence_note": "consumed directly by infer_source_tier(), not a product attribute",
    "user_supplied": "meta/provenance narrative about how the source was found; can inform tier inference but isn't itself a product attribute",

    # narrative rate note that never resolved to clean per-model numbers
    "recovery_rate_gph": "narrative note about recovery rate applicability, not a clean numeric field in this observation",
    "recovery_rate_minor_conflict": "narrative conflict flag",
}

# ==========================================================================
# Compound-key derivation
# ==========================================================================


def _derive_opening(obs_id, key, value, attrs, dropped):
    """cutout_* -> opening_h / opening_w. Any depth figure is dropped and
    logged, never kept as opening_d. See VENDOR-Suburban.md 6.5."""
    if key == "cutout_confirmed_depth_in":
        # A bare depth figure with no h/w alongside it - nothing to derive
        # an opening from, but the depth claim itself is worth logging so
        # it isn't silently lost.
        dropped.append({"obs_id": obs_id, "key": key, "dropped_value": value,
                        "reason": "cutout depth is not part of the opening (VENDOR-Suburban.md 6.5)"})
        return

    if key == "figure_1_framed_opening_in":
        # {"A": "12.75 +1/8/-0", "B": "12.75 +1/8/-0"} - already 2D, no
        # depth present to drop, but the format differs (strings with
        # tolerance baked in) from the numeric h/w/d dicts.
        if isinstance(value, dict) and "A" in value and "B" in value:
            attrs.setdefault("opening_h", []).append(value["A"])
            attrs.setdefault("opening_w", []).append(value["B"])
        return

    if isinstance(value, dict):
        h, w, d = value.get("h"), value.get("w"), value.get("d")
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        h, w = value[0], value[1]
        d = value[2] if len(value) > 2 else None
    else:
        dropped.append({"obs_id": obs_id, "key": key, "dropped_value": value,
                        "reason": "unrecognised cutout shape - could not derive h/w"})
        return

    if h is not None:
        attrs.setdefault("opening_h", []).append(h)
    if w is not None:
        attrs.setdefault("opening_w", []).append(w)
    if d is not None:
        dropped.append({"obs_id": obs_id, "key": key, "dropped_value": d,
                        "reason": "cutout depth is not part of the opening (VENDOR-Suburban.md 6.5)"})


def _derive_weight(obs_id, key, value, attrs, dropped):
    if not isinstance(value, dict):
        dropped.append({"obs_id": obs_id, "key": key, "dropped_value": value,
                        "reason": "weight_lb expected {empty, full}, got something else"})
        return
    if "empty" in value:
        attrs.setdefault("weight_empty_lb", []).append(value["empty"])
    if "full" in value:
        attrs.setdefault("weight_full_lb", []).append(value["full"])


def _derive_recovery(obs_id, key, value, attrs, dropped):
    if not isinstance(value, dict):
        dropped.append({"obs_id": obs_id, "key": key, "dropped_value": value,
                        "reason": "recovery_gph expected a dict, got something else"})
        return
    if "gas_electric" in value:
        attrs.setdefault("recovery_gas_electric_gph", []).append(value["gas_electric"])
    if "electric_only" in value:
        attrs.setdefault("recovery_electric_only_gph", []).append(value["electric_only"])
    if "gas_only" in value:
        attrs.setdefault("recovery_gas_only_gph", []).append(value["gas_only"])


_COMPOUND_HANDLERS = {}
for _k in _CUTOUT_KEYS:
    _COMPOUND_HANDLERS[_k] = _derive_opening
for _k in _WEIGHT_COMPOUND_KEYS:
    _COMPOUND_HANDLERS[_k] = _derive_weight
for _k in _RECOVERY_COMPOUND_KEYS:
    _COMPOUND_HANDLERS[_k] = _derive_recovery


# ==========================================================================
# Classification + normalization
# ==========================================================================


def classify_keys(extracted):
    """
    Split an extracted blob's keys into (mapped, compound, ignored, unmapped).

    mapped: {raw_key: canonical_name} for simple 1:1 aliases
    compound: [raw_key, ...] for keys handled by _COMPOUND_HANDLERS
    ignored: {raw_key: reason}
    unmapped: [raw_key, ...] - not classified anywhere; the caller decides
              whether that's a hard error.
    """
    mapped, compound, ignored, unmapped = {}, [], {}, []
    for key in extracted:
        if key in _COMPOUND_KEYS:
            compound.append(key)
        elif key in ALIASES:
            mapped[key] = ALIASES[key]
        elif key in IGNORED_KEYS:
            ignored[key] = IGNORED_KEYS[key]
        else:
            unmapped.append(key)
    return mapped, compound, ignored, unmapped


def _accumulate(attrs, canonical, value):
    """
    Record a value under a canonical field, flattening rather than
    clobbering when the field already has one - a canonical field can
    legitimately receive more than one raw key's worth of value in the same
    observation (e.g. sku/sku_per_page/url_path_sku all present at once on
    obs #23/#24, or aliases_mentioned contributing a list of extra SKUs).
    """
    if canonical not in attrs:
        attrs[canonical] = value
        return
    existing = attrs[canonical]
    if not isinstance(existing, list):
        existing = [existing]
    existing.extend(value) if isinstance(value, list) else existing.append(value)
    attrs[canonical] = existing


def normalize_extracted(obs_id, extracted, strict=True):
    """
    Normalize one observation's `extracted` blob.

    Returns {"attributes": {canonical: value_or_[values]}, "dropped": [...],
    "ignored": {...}}. Raises ValueError if `strict` (the default) and any
    key isn't classified in ALIASES, _COMPOUND_KEYS, or IGNORED_KEYS.
    """
    mapped, compound, ignored, unmapped = classify_keys(extracted)

    if unmapped and strict:
        raise ValueError(
            f"observation #{obs_id}: unclassified key(s) {unmapped!r} - "
            f"add to ALIASES or IGNORED_KEYS in resolver.py (with a reason) "
            f"before this observation can be resolved")

    attrs, dropped = {}, []
    for raw_key, canonical in mapped.items():
        _accumulate(attrs, canonical, extracted[raw_key])

    multi_valued = {}
    for raw_key in compound:
        handler = _COMPOUND_HANDLERS[raw_key]
        handler(obs_id, raw_key, extracted[raw_key], multi_valued, dropped)
    for canonical, values in multi_valued.items():
        for v in values:
            _accumulate(attrs, canonical, v)

    return {"attributes": attrs, "dropped": dropped, "ignored": ignored, "unmapped": unmapped}


# ==========================================================================
# Source tier
# ==========================================================================
#
# Rank 1 = most trusted. This is what lets the resolver pick a winner on
# conflict mechanically instead of re-deriving "which source do I believe"
# by prose every time (VENDOR-Suburban.md 2's informal spec-block > prose >
# alt-text ordering, made concrete and per-observation).

TIER = {
    1: "manufacturer_primary",       # official manufacturer doc, native/scripted text extraction
    2: "manufacturer_manual_or_direct_statement",  # manufacturer install manual (hand-typed) or a
                                      # direct manufacturer communication (email/call); also
                                      # first-hand physical measurement
    3: "manufacturer_secondary",     # reserved for manufacturer content one step removed
                                      # (mirrors, older reprints) - not currently used by any
                                      # observation but kept distinct from tier 2
    4: "other_primary_source",       # a coach-builder OEM parts portal, etc: not Suburban
                                      # itself, but not a retailer either
    5: "manufacturer_image_transcription",  # manufacturer content, but only available as an
                                      # image (OCR'd or hand-transcribed) - digits less certain
    6: "retailer_spec_block",        # structured retailer spec table, scripted extraction
    7: "retailer_spec_block_manual", # same, hand-transcribed
    8: "retailer_prose",             # retailer body copy / fitment notes, unstructured
    9: "low_confidence_secondary",   # page-summary of a paywalled/viewer-only source, not a
                                      # raw file the resolver itself parsed
}

TIER_DEFAULTS = {
    ("manufacturer_page", "script"): 1,
    ("manufacturer_pdf", "script"): 1,
    ("manufacturer_page", "hand_typed"): 2,
    ("manufacturer_pdf", "hand_typed"): 2,
    ("dealer_call", "hand_typed"): 2,
    ("manual_measurement", "hand_typed"): 2,
    ("other", "script"): 4,
    ("other", "hand_typed"): 4,
    ("manufacturer_page", "ocr"): 5,
    ("manufacturer_pdf", "ocr"): 5,
    ("retailer_page", "script"): 6,
    ("retailer_page", "hand_typed"): 7,
    ("retailer_prose", "hand_typed"): 8,
}

# Per-observation overrides for cases where the observation's own text
# (trust_tier / confidence_note) already made an explicit call that
# shouldn't be re-derived from source_type defaults.
TIER_OVERRIDES = {
    6:  (9, "own confidence_note: 'LOWEST trust tier, below all others' (compressed-screenshot OCR)"),
    20: (1, "own trust_tier: 'MANUFACTURER — Suburban's own site, highest trust captured so far'"),
    28: (8, "own trust_tier: explicitly retailer_prose, lower than a spec block"),
    30: (9, "own trust_tier: 'LOW-MEDIUM — page-summary of a paywalled viewer, not a raw file'"),
}


def infer_source_tier(obs_id, source_type, extraction_method, extracted):
    if obs_id in TIER_OVERRIDES:
        return TIER_OVERRIDES[obs_id][0]

    # Fallback for future observations with no hardcoded override: if the
    # observation itself already made an explicit call (trust_tier /
    # confidence_note free text), prefer that signal over the source_type
    # default rather than silently ignoring it.
    note = " ".join(str(extracted.get(k, "")) for k in ("trust_tier", "confidence_note")).upper()
    if "LOWEST" in note or "LOW-MEDIUM" in note or "LOW MEDIUM" in note:
        return 9
    if "MANUFACTURER" in note and "HIGHEST" in note:
        return 1

    return TIER_DEFAULTS.get((source_type, extraction_method), 9)


# ==========================================================================
# DB-facing operations
# ==========================================================================


def _load_observations(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT id, source_type, source_name, extraction_method, extracted, source_tier "
                "FROM observations WHERE extracted IS NOT NULL ORDER BY id")
    rows = cur.fetchall()
    con.close()
    return rows


def validate_db(db_path, verbose=False):
    rows = _load_observations(db_path)
    total_unmapped = []
    total_ignored_hits = 0
    total_dropped = 0

    for row in rows:
        extracted = json.loads(row["extracted"])
        mapped, compound, ignored, unmapped = classify_keys(extracted)
        total_ignored_hits += len(ignored)
        if unmapped:
            total_unmapped.append((row["id"], unmapped))
        else:
            result = normalize_extracted(row["id"], extracted, strict=True)
            total_dropped += len(result["dropped"])
            if verbose:
                print(f"  obs #{row['id']:<3} {len(mapped)+len(compound):2} mapped, "
                      f"{len(ignored):2} ignored, {len(result['dropped']):2} dropped "
                      f"(depth/shape corrections)")

    print(f"\n{len(rows)} observations with extracted data")
    print(f"{total_ignored_hits} ignored-key hits (reviewed, not product data)")
    print(f"{total_dropped} mechanical corrections logged (cutout depth etc.)")
    if total_unmapped:
        print(f"\nUNMAPPED ({sum(len(u) for _, u in total_unmapped)} key instances "
              f"across {len(total_unmapped)} observations):")
        for obs_id, keys in total_unmapped:
            print(f"  obs #{obs_id}: {keys}")
        return 1
    print("\nALL KEYS CLASSIFIED")
    return 0


def show_observation(db_path, obs_id):
    rows = _load_observations(db_path)
    row = next((r for r in rows if r["id"] == obs_id), None)
    if row is None:
        print(f"observation #{obs_id} not found (or has no extracted data)")
        return 1
    extracted = json.loads(row["extracted"])
    result = normalize_extracted(obs_id, extracted, strict=False)
    tier = row["source_tier"] if row["source_tier"] is not None else \
        infer_source_tier(obs_id, row["source_type"], row["extraction_method"], extracted)
    print(f"observation #{obs_id}  [{row['source_type']}/{row['extraction_method']}]  "
          f"{row['source_name']}")
    print(f"source_tier: {tier} ({TIER[tier]})")
    print("\nattributes:")
    for k, v in result["attributes"].items():
        print(f"  {k}: {json.dumps(v)}")
    if result["dropped"]:
        print("\ndropped (mechanical corrections):")
        for d in result["dropped"]:
            print(f"  {d['key']} -> discarded {json.dumps(d['dropped_value'])}: {d['reason']}")
    if result["unmapped"]:
        print("\nUNMAPPED:", result["unmapped"])
    return 0


def assign_tiers(db_path, dry_run=False):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(observations)")
    cols = {r[1] for r in cur.fetchall()}
    if "source_tier" not in cols:
        cur.execute("ALTER TABLE observations ADD COLUMN source_tier INTEGER")
        con.commit()

    cur.execute("SELECT id, source_type, extraction_method, extracted, source_tier "
                "FROM observations ORDER BY id")
    updated = 0
    for oid, st, em, ext, existing in cur.fetchall():
        extracted = json.loads(ext) if ext else {}
        tier = infer_source_tier(oid, st, em, extracted)
        if existing != tier:
            print(f"  obs #{oid}: source_tier {existing} -> {tier} ({TIER[tier]})")
            if not dry_run:
                cur.execute("UPDATE observations SET source_tier=? WHERE id=?", (tier, oid))
            updated += 1
    if not dry_run:
        con.commit()
    con.close()
    print(f"\n{updated} row(s) {'would be ' if dry_run else ''}updated")
    return 0


# ==========================================================================
# Self-test
# ==========================================================================


def self_test():
    failures = []

    # every ALIASES target must be a documented canonical field
    for raw, canon in ALIASES.items():
        if canon not in CANONICAL:
            failures.append(f"ALIASES[{raw!r}] -> {canon!r} is not in CANONICAL")

    # no key can be classified two different ways
    dupe = (set(ALIASES) & set(IGNORED_KEYS)) | (set(ALIASES) & _COMPOUND_KEYS) | \
           (set(IGNORED_KEYS) & _COMPOUND_KEYS)
    if dupe:
        failures.append(f"keys classified more than one way: {dupe}")

    # cutout collapse: h/w kept, d dropped and logged
    r = normalize_extracted(999, {"cutout_in": {"h": 12.75, "w": 12.75, "d": 19.19}})
    if r["attributes"].get("opening_h") != 12.75 or r["attributes"].get("opening_w") != 12.75:
        failures.append(f"cutout_in h/w not derived correctly: {r['attributes']}")
    if "opening_d" in r["attributes"]:
        failures.append("opening_d must never appear - depth is not part of the opening")
    if not r["dropped"] or r["dropped"][0]["dropped_value"] != 19.19:
        failures.append(f"cutout depth must be logged in `dropped`: {r['dropped']}")

    # figure_1_framed_opening_in (string-tolerance format) also collapses
    r = normalize_extracted(999, {"figure_1_framed_opening_in":
                                   {"A": "12.75 +1/8/-0", "B": "12.75 +1/8/-0"}})
    if r["attributes"].get("opening_h") != "12.75 +1/8/-0":
        failures.append(f"figure_1_framed_opening_in not derived: {r['attributes']}")

    # weight_lb splits
    r = normalize_extracted(999, {"weight_lb": {"empty": 36, "full": 86.04}})
    if r["attributes"].get("weight_empty_lb") != 36 or r["attributes"].get("weight_full_lb") != 86.04:
        failures.append(f"weight_lb not split correctly: {r['attributes']}")

    # recovery_gph splits
    r = normalize_extracted(999, {"recovery_gph": {"gas_electric": 10.1, "electric_only": 6.1}})
    if (r["attributes"].get("recovery_gas_electric_gph") != 10.1
            or r["attributes"].get("recovery_electric_only_gph") != 6.1):
        failures.append(f"recovery_gph not split correctly: {r['attributes']}")

    # multiple raw keys mapping to one canonical in the same observation
    # must accumulate, not clobber
    r = normalize_extracted(999, {"sku": "5248A", "url_path_sku": "5248a"})
    if r["attributes"].get("sku") != ["5248A", "5248a"]:
        failures.append(f"same-canonical multi-key accumulation failed: {r['attributes']}")

    # a list-valued raw key (e.g. aliases_mentioned) must flatten into the
    # accumulator, not nest as a list-inside-a-list
    r = normalize_extracted(999, {"sku": "5240A", "aliases_mentioned": ["5140A"]})
    if r["attributes"].get("sku") != ["5240A", "5140A"]:
        failures.append(f"list-valued accumulation must flatten, not nest: {r['attributes']}")

    # a genuinely unclassified key must raise in strict mode, and must NOT
    # raise (just get reported) in non-strict mode
    try:
        normalize_extracted(999, {"totally_new_field_never_seen": 1}, strict=True)
        failures.append("strict normalize_extracted must raise on an unmapped key")
    except ValueError:
        pass
    r = normalize_extracted(999, {"totally_new_field_never_seen": 1}, strict=False)
    if r["unmapped"] != ["totally_new_field_never_seen"]:
        failures.append(f"non-strict normalize_extracted must report unmapped keys: {r}")

    # ignored keys produce no attribute at all
    r = normalize_extracted(999, {"note": "some narrative text"})
    if r["attributes"]:
        failures.append(f"an ignored-only observation must produce zero attributes: {r['attributes']}")
    if "note" not in r["ignored"]:
        failures.append("ignored key must be reported in result['ignored']")

    # tier inference
    if infer_source_tier(22, "manufacturer_page", "script", {}) != 1:
        failures.append("manufacturer_page/script should default to tier 1")
    if infer_source_tier(6, "manufacturer_page", "ocr", {}) != 9:
        failures.append("obs #6 override should force tier 9 regardless of source_type default")
    if infer_source_tier(1, "retailer_page", "hand_typed", {}) != 7:
        failures.append("retailer_page/hand_typed should default to tier 7")

    print(f"{len(ALIASES)} aliases, {len(IGNORED_KEYS)} ignored keys, "
          f"{len(_COMPOUND_KEYS)} compound keys classified")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="observations.db")
    ap.add_argument("--validate", action="store_true",
                    help="classify every extracted key in the db; fails if anything is unmapped")
    ap.add_argument("--show", type=int, metavar="OBS_ID",
                    help="print the normalized view of one observation")
    ap.add_argument("--assign-tiers", action="store_true",
                    help="backfill/refresh source_tier for every row")
    ap.add_argument("--dry-run", action="store_true", help="with --assign-tiers, don't write")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if args.validate:
        sys.exit(validate_db(args.db, args.verbose))
    if args.show is not None:
        sys.exit(show_observation(args.db, args.show))
    if args.assign_tiers:
        sys.exit(assign_tiers(args.db, args.dry_run))
    ap.print_help()


if __name__ == "__main__":
    main()
