#!/usr/bin/env python3
"""
suburban_parser.py — Suburban water-heater model numbers into structured attributes.

The grammar is positional, not a lookup table of names:

    SW  6  D  E  L
    |   |  |  |  +-- L = 12V relay for interior operation of the electric element
    |   |  |  +----- E = 120V AC heating element
    |   |  +-------- D = 12V DC direct spark ignition
    |   +----------- capacity in US gallons
    +--------------- series

Source: cross-validated grammar chart (VENDOR-Suburban.md 3.2) plus per-model
confirmations from suburbanrv.com brochures and service manuals.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
1. It does NOT validate capacity against a list of known capacities.
   Suburban's own chart lists 4/6/10/12/16, but SW3P exists (discontinued
   ~2005) and is decoded correctly here. Vendor capacity lists enumerate a
   current lineup, not a closed set. See VENDOR-Suburban.md 9.

2. It does NOT guess when the suffix is unrecognised. Unknown suffixes come
   back with `suffix_provenance: unknown` and the raw text preserved, rather
   than a best-effort decode that would look confident and be wrong.

3. It does NOT treat "V Model" as evidence about the V suffix. `V` is
   overloaded in Suburban's data: an ignition suffix (120V AC direct spark,
   e.g. SW16VE) AND an older product line with its own door catalogue and an
   8-gallon size the SW line never offered. Only the suffix reading is
   implemented; the product line is out of scope. See VENDOR-Suburban.md 5.5.

USAGE
-----
    python3 suburban_parser.py SW6DEL SW16VE SAW6DE SW3P
    python3 suburban_parser.py --self-test
    python3 suburban_parser.py --check-fixture ../fixtures/ground-truth.yaml
    python3 suburban_parser.py --table          # every confirmed suffix decoded

    >>> from suburban_parser import parse_model
    >>> parse_model("SW6DEL")["opening"]["h"]
    12.75
"""

import argparse
import json
import re
import sys

# --------------------------------------------------------------------------
# Series prefixes. Only SW and SAW use the tank grammar below.
# --------------------------------------------------------------------------

SERIES = {
    "SW":  {"platform": "tank",     "label": "Suburban Water heater"},
    "SAW": {"platform": "tank",     "label": "Suburban Advantage Water heater"},
    "IW":  {"platform": "tankless", "label": "Nautilus on-demand"},
}

# --------------------------------------------------------------------------
# Suffix grammar.
#
# The suffix is fully compositional: a BASE letter (ignition system) followed
# by zero or more FLAG letters. Every confirmed suffix decomposes cleanly this
# way, which is why this parser composes rather than pattern-matches.
#
# That also sidesteps a real trap: DM and DEM differ by one letter and DM's
# letters are a subset of DEM's. Greedy or regex-based matching gets this
# wrong. Composition cannot.
# --------------------------------------------------------------------------

BASE = {
    "P": {"ignition_system": "pilot",
          "ignition_power_source": "none",
          "note": "standing pilot; no electrical supply needed for the gas side"},
    "D": {"ignition_system": "direct_spark",
          "ignition_power_source": "12vdc",
          "note": "needs 12V DC at the heater location"},
    "V": {"ignition_system": "direct_spark",
          "ignition_power_source": "120vac",
          "note": "needs 120V AC at the heater location - NOT interchangeable "
                  "with the D line on electrical supply, despite sharing the opening"},
}

FLAG = {
    "E": ("has_element", True,  "120V AC heating element"),
    "R": ("has_reignitor", True, "12V DC pilot re-igniter (pilot family only)"),
    "L": ("has_relay", True,    "12V relay for interior operation of the electric element"),
    "M": ("motor_aid", True,    "Motor Aid heat exchanger - MOTOR HOME ONLY"),
    "C": ("corded", True,       "120V corded"),
}

# --------------------------------------------------------------------------
# What each variant needs PRESENT AT THE INSTALL LOCATION.
#
# This is separate from the feature list and it is what actually governs
# whether a swap is a drop-in. VENDOR-Suburban.md 3 already makes this point
# for the V line: SW16VE shares an opening with the D line but needs 120V AC
# ignition power, so opening match alone does not make it interchangeable.
#
# The same logic applies to the FEATURE letters, which is easy to miss:
#   E  adds a 120V AC requirement    (a gas-only D install has no reason to have it)
#   R  adds a 12V DC requirement     (a plain P unit needs no electrical supply at all)
#   C  needs 120V AC as a RECEPTACLE rather than a hardwired junction
#   L  needs 12V DC - but L only ever appears on the D line, which already has
#      12V DC for ignition, so it is the one genuinely free upgrade
#
# Gaining a feature is therefore not automatically a clean upgrade. Only a
# feature whose supply is already present is.
# --------------------------------------------------------------------------

BASE_SUPPLY = {
    "P": set(),
    "D": {"12vdc"},
    "V": {"120vac"},
}

FEATURE_SUPPLY = {
    "has_element":   {"120vac"},
    "has_reignitor": {"12vdc"},
    "has_relay":     {"12vdc"},
    "corded":        {"120vac"},
}

SUPPLY_LABEL = {
    "12vdc":  "12V DC at the heater location",
    "120vac": "120V AC at the heater location",
}

# Suffixes Suburban has published. Anything else that still composes cleanly is
# returned as `inferred_compositional` - grammatically valid, not vendor-attested.
CONFIRMED_SUFFIXES = {
    "P", "PR", "PE", "PER",          # pilot family
    "D", "DE", "DEL", "DEM", "DM",   # 12V DC direct spark family
    "DEC", "DELC",                   # corded variants
    "V", "VE",                       # 120V AC direct spark family
}

# --------------------------------------------------------------------------
# Installation opening. Manufacturer-stated, from the Master Service and
# Training Manual Figure 1 (observation #19).
#
# TWO DIMENSIONS ONLY. There is no opening depth - a unit's depth is a separate
# cavity-clearance constraint, not part of the hole. See VENDOR-Suburban.md 6.5.
#
# Note the asymmetric tolerance on the small family: an opening may be up to
# 1/8" oversize but must NEVER be undersize. A matcher treating tolerance as
# symmetric would accept a hole Suburban explicitly rejects.
# --------------------------------------------------------------------------

OPENING_FAMILIES = [
    {"name": "small", "capacities": {4, 6},
     "h": 12.75, "w": 12.75, "plus": 0.125, "minus": 0.0,
     "tolerance": '+1/8" -0'},
    {"name": "large", "capacities": {10, 12, 16},
     "h": 16.375, "w": 16.375, "plus": 0.0625, "minus": 0.0625,
     "tolerance": '+/- 1/16"'},
]

# SW3P predates the manual that defines the families, so it is not listed there.
# Its unit height and width match the 6-gallon line exactly, which makes small-
# family membership very likely - but likely is not confirmed, and this parser
# says so rather than quietly filing it as fact.
INFERRED_CAPACITIES = {3: "small"}

_MODEL_RE = re.compile(r"^(SAW|SW|IW)\s*[-_]?\s*(\d+)\s*[-_]?\s*([A-Z]*)$")


def parse_model(raw):
    """Parse a Suburban model number. Always returns a dict; never raises."""
    out = {
        "input": raw,
        "ok": False,
        "series": None, "platform": None, "capacity_gal": None,
        "suffix": None, "suffix_provenance": None,
        "ignition_system": None, "ignition_power_source": None,
        "has_element": False, "has_reignitor": False, "has_relay": False,
        "motor_aid": False, "corded": False,
        "chassis_constraint": None,
        "requires_supply": [],
        "ac_connection": None,
        "opening": None,
        "warnings": [],
        "notes": [],
    }

    s = (raw or "").strip().upper().replace(" ", "")
    m = _MODEL_RE.match(s)
    if not m:
        out["warnings"].append("unrecognised model format")
        return out

    series, cap, suffix = m.group(1), int(m.group(2)), m.group(3)
    out.update(series=series, capacity_gal=cap, suffix=suffix,
               platform=SERIES[series]["platform"])

    # Tankless is a different platform with no framed opening at all - it
    # mounts behind a panel and needs a 3.750" vent hole. The tank grammar
    # does not apply.
    if series == "IW":
        out["warnings"].append(
            "IW is the tankless Nautilus platform: no framed opening (vent hole "
            "instead), and the tank suffix grammar does not apply. Not parsed further.")
        return out

    # --- suffix: base letter + flags -------------------------------------
    if not suffix:
        out["warnings"].append("no ignition suffix present")
        return out

    base, flags = suffix[0], suffix[1:]
    if base not in BASE:
        out["suffix_provenance"] = "unknown"
        out["warnings"].append(
            f"unknown ignition base '{base}' - not decoded (raw suffix preserved)")
        return out

    out.update(BASE[base])
    out["notes"].append(f"{base}: {BASE[base]['note']}")
    out.pop("note", None)

    unknown = []
    for ch in flags:
        if ch in FLAG:
            key, val, desc = FLAG[ch]
            out[key] = val
            out["notes"].append(f"{ch}: {desc}")
        else:
            unknown.append(ch)

    if unknown:
        out["suffix_provenance"] = "unknown"
        out["warnings"].append(
            f"unknown suffix letter(s) {''.join(unknown)} - decoded what was "
            f"recognisable, treat the result as incomplete")
    else:
        out["suffix_provenance"] = (
            "vendor_confirmed" if suffix in CONFIRMED_SUFFIXES
            else "inferred_compositional")
        if out["suffix_provenance"] == "inferred_compositional":
            out["warnings"].append(
                f"suffix '{suffix}' composes cleanly but has not been seen in any "
                f"Suburban document - grammatically valid, not vendor-attested")

    # --- semantic checks --------------------------------------------------
    if out["motor_aid"]:
        # This is stronger than a caveat. A travel trailer has no engine to
        # draw heat from, so the variant cannot exist on that chassis - it is
        # knowable in advance and should filter, not warn.
        out["chassis_constraint"] = "motorhome_only"

    if out["has_reignitor"] and out["ignition_system"] != "pilot":
        out["warnings"].append(
            "R (re-igniter) outside the pilot family - re-igniters exist to relight "
            "a standing pilot, so this combination is probably a parse error")

    if out["has_relay"] and not out["has_element"]:
        out["warnings"].append(
            "L (relay) without E (element) - the relay switches the electric "
            "element, so this combination has nothing to control")

    # --- install-side supply requirements ---------------------------------
    supplies = set(BASE_SUPPLY.get(base, set()))
    for feat, needed in FEATURE_SUPPLY.items():
        if out.get(feat):
            supplies |= needed
    out["requires_supply"] = sorted(supplies)
    out["ac_connection"] = ("corded" if out["corded"]
                            else "hardwired" if "120vac" in supplies
                            else "none")

    # --- opening ----------------------------------------------------------
    out["opening"] = _opening_for(cap)
    if out["opening"] is None:
        out["warnings"].append(
            f"no opening family known for {cap} gallon - decoded on grammar alone")

    out["ok"] = True
    return out


def _opening_for(cap):
    for fam in OPENING_FAMILIES:
        if cap in fam["capacities"]:
            return {"family": fam["name"], "h": fam["h"], "w": fam["w"],
                    "plus": fam["plus"], "minus": fam["minus"],
                    "tolerance": fam["tolerance"],
                    "provenance": "manufacturer_figure1",
                    "note": "installation opening is TWO-DIMENSIONAL; depth is a "
                            "separate cavity constraint, not part of the opening"}
    if cap in INFERRED_CAPACITIES:
        fam = next(f for f in OPENING_FAMILIES
                   if f["name"] == INFERRED_CAPACITIES[cap])
        return {"family": fam["name"], "h": fam["h"], "w": fam["w"],
                "plus": fam["plus"], "minus": fam["minus"],
                "tolerance": fam["tolerance"],
                "provenance": "inferred_from_unit_envelope",
                "note": f"{cap} gal is NOT listed in the manufacturer's opening figure. "
                        f"Unit H/W match the {fam['name']} family, so membership is likely "
                        f"but unconfirmed. Do not treat as a confirmed opening."}
    return None


def opening_accepts(parsed, measured_h, measured_w):
    """
    Would this unit fit an opening measured at (measured_h x measured_w)?

    Tolerance is asymmetric on the small family - oversize is allowed, undersize
    is not - so this cannot be a symmetric +/- comparison.
    """
    op = parsed.get("opening")
    if not op:
        return None, "no known opening for this capacity"
    for label, measured, nominal in (("height", measured_h, op["h"]),
                                     ("width", measured_w, op["w"])):
        low, high = nominal - op["minus"], nominal + op["plus"]
        if measured < low:
            return False, (f'{label} {measured}" is undersize (minimum {low}") - '
                           f'the unit will not go in')
        if measured > high:
            return False, (f'{label} {measured}" exceeds {high}" - the flange may '
                           f'not cover the opening')
    return True, f'within {op["tolerance"]} of {op["h"]}" x {op["w"]}"'


# --------------------------------------------------------------------------
# Substitution edges.
#
# The confirmed case (VENDOR-Suburban.md 5.1, SW6DE <-> SW6DEL) is not a
# one-off: it is a "one model's feature set is a strict superset of the
# other's, everything else that determines fit/electrical-compatibility is
# identical" pattern. That generalises to any suffix pair, not just DE/DEL,
# so it is implemented as a comparison rather than a hardcoded fact.
# --------------------------------------------------------------------------

# Fields that must match for two models to be candidates for the same group
# at all. If any of these differ, the units are not interchangeable and no
# feature-superset reasoning applies - they are simply different products.
_COMPATIBILITY_FIELDS = (
    "capacity_gal", "ignition_system", "ignition_power_source",
    "chassis_constraint",
)

_FEATURE_FIELDS = ("has_element", "has_reignitor", "has_relay", "corded")

_FEATURE_LABELS = {
    "has_element":   "120V AC heating element",
    "has_reignitor": "12V DC pilot re-igniter",
    "has_relay":     "12V relay for interior switching of the electric element",
    "corded":        "120V cord (vs. hardwired)",
}


def _supply_caveats(src, dst):
    """
    What must be added at the install location to go from `src` to `dst`?

    Returns a list of blocking caveats. An empty list means the target needs
    nothing the source did not already need - only then is a swap a true
    drop-in, regardless of how the feature sets compare.
    """
    caveats = []
    new = set(dst["requires_supply"]) - set(src["requires_supply"])
    for supply in sorted(new):
        caveats.append(
            f"requires {SUPPLY_LABEL[supply]}, which the {src['input']} did not - "
            f"verify it is present before treating this as a drop-in")
    if (src["ac_connection"] == "hardwired" and dst["ac_connection"] == "corded"
            and "120vac" not in new):
        caveats.append(
            "the replacement is corded and needs a 120V AC receptacle; the original "
            "was hardwired, so a junction box may be present instead of an outlet")
    if (src["ac_connection"] == "corded" and dst["ac_connection"] == "hardwired"
            and "120vac" not in new):
        caveats.append(
            "the replacement is hardwired and the original was corded - the existing "
            "receptacle will need converting to a junction")
    return caveats


def compare_models(model_a, model_b):
    """
    Compare two Suburban model numbers and, where possible, resolve a
    `substitutes` edge between them.

    Returns a dict with a `verdict` of:
      - "incompatible"   - core fields differ; not the same group at all
      - "identical"      - same suffix, nothing to resolve
      - "symmetric"      - same feature set; drop-in either direction
      - "asymmetric"     - one is a strict feature superset of the other
      - "needs_review"   - features differ but neither is a superset of the
                            other (e.g. relay vs. reignitor swap) - a human
                            call, not something this parser should guess at
    """
    a, b = parse_model(model_a), parse_model(model_b)
    out = {"a": model_a, "b": model_b, "verdict": None, "reasons": []}

    if not a["ok"] or not b["ok"]:
        out["verdict"] = "incompatible"
        out["reasons"].append("one or both models failed to parse")
        return out

    if a["platform"] != b["platform"]:
        out["verdict"] = "incompatible"
        out["reasons"].append(f"different platform ({a['platform']} vs {b['platform']})")
        return out

    if a.get("opening") is None or b.get("opening") is None:
        out["verdict"] = "incompatible"
        out["reasons"].append("opening unknown for at least one model - cannot verify fit")
        return out

    mismatched = [f for f in _COMPATIBILITY_FIELDS if a[f] != b[f]]
    if a["opening"]["h"] != b["opening"]["h"] or a["opening"]["w"] != b["opening"]["w"]:
        mismatched.append("opening")
    if mismatched:
        out["verdict"] = "incompatible"
        out["reasons"].append(f"core mismatch on: {', '.join(mismatched)}")
        return out

    if a["suffix"] == b["suffix"]:
        out["verdict"] = "identical"
        return out

    a_feats = {f for f in _FEATURE_FIELDS if a[f]}
    b_feats = {f for f in _FEATURE_FIELDS if b[f]}

    if a_feats == b_feats:
        out["verdict"] = "symmetric"
        for direction, src, dst in (("a_to_b", a, b), ("b_to_a", b, a)):
            cav = _supply_caveats(src, dst)
            out[direction] = ({"verdict": "drop_in"} if not cav else
                              {"verdict": "fits_with_caveat", "blocking_caveats": cav})
        return out

    if a_feats < b_feats:
        gained = b_feats - a_feats
        out["verdict"] = "asymmetric"
        gain_note = "upgrade - gains " + ", ".join(_FEATURE_LABELS[f] for f in gained)
        cav = _supply_caveats(a, b)
        out["a_to_b"] = ({"verdict": "drop_in", "note": gain_note} if not cav else
                         {"verdict": "fits_with_caveat", "note": gain_note,
                          "blocking_caveats": cav})
        out["b_to_a"] = {"verdict": "fits_with_caveat",
                         "blocking_caveats": ["loses " + ", ".join(
                             _FEATURE_LABELS[f] for f in gained)] + _supply_caveats(b, a)}
        return out

    if b_feats < a_feats:
        gained = a_feats - b_feats
        out["verdict"] = "asymmetric"
        gain_note = "upgrade - gains " + ", ".join(_FEATURE_LABELS[f] for f in gained)
        cav = _supply_caveats(b, a)
        out["b_to_a"] = ({"verdict": "drop_in", "note": gain_note} if not cav else
                         {"verdict": "fits_with_caveat", "note": gain_note,
                          "blocking_caveats": cav})
        out["a_to_b"] = {"verdict": "fits_with_caveat",
                         "blocking_caveats": ["loses " + ", ".join(
                             _FEATURE_LABELS[f] for f in gained)] + _supply_caveats(a, b)}
        return out

    out["verdict"] = "needs_review"
    only_a = a_feats - b_feats
    only_b = b_feats - a_feats
    out["reasons"].append(
        f"neither is a strict feature superset - {model_a} has "
        f"{sorted(only_a) or 'nothing extra'}, {model_b} has {sorted(only_b) or 'nothing extra'}"
    )
    return out


# --------------------------------------------------------------------------
# Weight consistency (the "full - empty" validity rule).
#
# A tank does not fill to nominal capacity - there is air space at the top.
# Suburban's own 15-row spec chart (obs #20) gives a fill ratio of 0.971
# (13 of 15 rows exactly), not the naive 1.000 this rule originally assumed.
# See VENDOR-Suburban.md 6.3 - that section documents the miscalibrated
# first version of this rule and why it inverted the verdict on two retailer
# weight records.
# --------------------------------------------------------------------------

WATER_LB_PER_GAL = 8.34
FILL_RATIO = 0.971
FILL_RATIO_TOLERANCE = 0.01


def check_weight_consistency(nominal_gal, weight_empty_lb, weight_full_lb):
    """
    Cross-check a claimed empty/full weight pair against nominal capacity.

    Returns (ok, ratio, message). `ok` is None if the inputs don't allow a
    check (e.g. nominal capacity unknown).
    """
    if not nominal_gal or weight_empty_lb is None or weight_full_lb is None:
        return None, None, "insufficient data to check"

    implied_gal = (weight_full_lb - weight_empty_lb) / WATER_LB_PER_GAL
    ratio = implied_gal / nominal_gal
    low, high = FILL_RATIO - FILL_RATIO_TOLERANCE, FILL_RATIO + FILL_RATIO_TOLERANCE

    if low <= ratio <= high:
        return True, ratio, (f"ratio {ratio:.3f} within {low:.3f}-{high:.3f} "
                             f"of design fill constant {FILL_RATIO}")
    return False, ratio, (f"ratio {ratio:.3f} outside {low:.3f}-{high:.3f} "
                          f"of design fill constant {FILL_RATIO} - one or both "
                          f"weight figures are suspect")


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

CASES = [
    # (model, expectations)
    ("SW6DEL",  dict(capacity_gal=6, ignition_system="direct_spark",
                     ignition_power_source="12vdc", has_element=True,
                     has_relay=True, corded=False, opening_h=12.75,
                     suffix_provenance="vendor_confirmed")),
    ("SW6DE",   dict(capacity_gal=6, has_element=True, has_relay=False,
                     opening_h=12.75, suffix_provenance="vendor_confirmed")),
    ("SW6D",    dict(capacity_gal=6, has_element=False, opening_h=12.75)),
    ("SW12DELC", dict(capacity_gal=12, has_relay=True, corded=True,
                      opening_h=16.375, suffix_provenance="vendor_confirmed")),
    ("SW16VE",  dict(capacity_gal=16, ignition_system="direct_spark",
                     ignition_power_source="120vac", has_element=True,
                     opening_h=16.375, suffix_provenance="vendor_confirmed")),
    ("SW6PER",  dict(capacity_gal=6, ignition_system="pilot",
                     ignition_power_source="none", has_element=True,
                     has_reignitor=True, opening_h=12.75)),
    ("SW6DEM",  dict(capacity_gal=6, motor_aid=True,
                     chassis_constraint="motorhome_only", has_element=True)),
    ("SW6DM",   dict(capacity_gal=6, motor_aid=True, has_element=False,
                     chassis_constraint="motorhome_only",
                     suffix_provenance="vendor_confirmed")),
    ("SW6DEC",  dict(capacity_gal=6, corded=True, has_relay=False,
                     suffix_provenance="vendor_confirmed")),
    # the discontinued 3-gallon: must decode, opening must be flagged inferred
    ("SW3P",    dict(capacity_gal=3, ignition_system="pilot",
                     opening_h=12.75, opening_provenance="inferred_from_unit_envelope")),
    # SAW shares the suffix grammar across the prefix boundary
    ("SAW6DE",  dict(series="SAW", capacity_gal=6, has_element=True,
                     ignition_system="direct_spark")),
    # tolerant of formatting noise
    ("sw6del",  dict(capacity_gal=6, has_relay=True)),
    ("SW-6-DEL", dict(capacity_gal=6, has_relay=True)),
]

NEGATIVE = [
    ("IW60RL", "tankless", "IW must not be parsed with the tank grammar"),
    ("SW6DZ",  "unknown",  "unknown suffix letter must not be guessed"),
    ("SW6XE",  "unknown",  "unknown ignition base must not be guessed"),
    ("HELLO",  "format",   "junk input must fail cleanly"),
]


def self_test(verbose=False):
    failures = []

    for model, exp in CASES:
        got = parse_model(model)
        if not got["ok"]:
            failures.append(f"{model}: parse failed - {got['warnings']}")
            continue
        for key, want in exp.items():
            if key == "opening_h":
                have = (got["opening"] or {}).get("h")
            elif key == "opening_provenance":
                have = (got["opening"] or {}).get("provenance")
            else:
                have = got.get(key)
            if have != want:
                failures.append(f"{model}: {key} expected {want!r}, got {have!r}")
        if verbose:
            print(f"  {model:<10} -> {got['capacity_gal']}gal "
                  f"{got['ignition_system']}/{got['ignition_power_source']} "
                  f"opening {got['opening']['h'] if got['opening'] else '?'}")

    for model, kind, why in NEGATIVE:
        got = parse_model(model)
        if kind == "tankless":
            if got["platform"] != "tankless" or got["ok"]:
                failures.append(f"{model}: {why}")
        elif kind == "unknown":
            if got["suffix_provenance"] != "unknown":
                failures.append(f"{model}: {why} (got {got['suffix_provenance']!r})")
        elif kind == "format":
            if got["ok"] or not got["warnings"]:
                failures.append(f"{model}: {why}")

    # asymmetric tolerance must actually behave asymmetrically
    p = parse_model("SW6DEL")
    checks = [
        ((12.75, 12.75), True,  "nominal must fit"),
        ((12.85, 12.85), True,  "+0.10 is within +1/8"),
        ((12.70, 12.75), False, "undersize must be REJECTED (minus tolerance is 0)"),
        ((13.00, 12.75), False, "+0.25 exceeds +1/8"),
    ]
    for (h, w), want, why in checks:
        ok, _ = opening_accepts(p, h, w)
        if ok is not want:
            failures.append(f"opening_accepts({h},{w}) expected {want}: {why}")

    # substitution edge resolution - the canonical confirmed case (5.1) and
    # its generalisations
    edge_cases = [
        ("SW6DE", "SW6DEL", "asymmetric",
         {"a_to_b": "drop_in", "b_to_a": "fits_with_caveat"},
         "the confirmed fixture edge: DEL is a strict superset of DE (adds relay)"),
        ("SW6DEL", "SW6DE", "asymmetric",
         {"a_to_b": "fits_with_caveat", "b_to_a": "drop_in"},
         "same pair, reversed argument order - direction must flip, not the verdict"),
        # CORRECTED 2026-07-30: this case previously expected a_to_b="drop_in".
        # Gaining the element gains a 120V AC requirement, and a gas-only D
        # install has no reason to have 120V AC at the cavity. Feature-superset
        # reasoning alone was overstating this as a clean drop-in.
        ("SW6D", "SW6DE", "asymmetric",
         {"a_to_b": "fits_with_caveat", "b_to_a": "fits_with_caveat"},
         "D -> DE adds the element AND a 120V AC supply requirement"),
        ("SW6P", "SW6PR", "asymmetric",
         {"a_to_b": "fits_with_caveat", "b_to_a": "fits_with_caveat"},
         "P -> PR adds a 12V DC requirement to a unit that needed no supply at all"),
        ("SW6DE", "SW6DEC", "asymmetric",
         {"a_to_b": "fits_with_caveat", "b_to_a": "fits_with_caveat"},
         "hardwired <-> corded: same 120V AC supply, but receptacle vs junction differs"),
        ("SW6DEL", "SW6DEL", "identical", None,
         "same suffix must not be reported as an edge at all"),
        ("SW6DEL", "SW12DEL", "incompatible", None,
         "different capacity/opening - not the same group, no feature reasoning applies"),
        ("SW6PER", "SW6DEL", "incompatible", None,
         "different ignition system/power source - pilot vs direct spark are not interchangeable"),
        ("SW6DEM", "SW6DE", "incompatible", None,
         "motorhome-only chassis constraint differs from the unconstrained DE - not a plain feature superset"),
    ]
    for model_a, model_b, want_verdict, want_dirs, why in edge_cases:
        got = compare_models(model_a, model_b)
        if got["verdict"] != want_verdict:
            failures.append(f"compare_models({model_a},{model_b}): expected verdict "
                            f"{want_verdict!r}, got {got['verdict']!r} ({why})")
            continue
        if want_dirs:
            for direction, want_v in want_dirs.items():
                have_v = got.get(direction, {}).get("verdict")
                if have_v != want_v:
                    failures.append(f"compare_models({model_a},{model_b}).{direction}: "
                                    f"expected {want_v!r}, got {have_v!r} ({why})")
    if verbose:
        for model_a, model_b, want_verdict, _, _ in edge_cases:
            got = compare_models(model_a, model_b)
            print(f"  {model_a} <-> {model_b}: {got['verdict']}")

    # install-side supply requirements - the thing feature-superset reasoning
    # alone does not capture (see _supply_caveats)
    supply_cases = [
        ("SW6P",   [],                    "none", "standing pilot needs no supply at all"),
        ("SW6PR",  ["12vdc"],             "none", "re-igniter adds a 12V DC requirement"),
        ("SW6D",   ["12vdc"],             "none", "direct spark needs 12V DC, no AC"),
        ("SW6DE",  ["120vac", "12vdc"],   "hardwired", "element adds 120V AC"),
        ("SW6DEL", ["120vac", "12vdc"],   "hardwired", "relay is 12V DC, already present - adds nothing"),
        ("SW6DEC", ["120vac", "12vdc"],   "corded", "corded needs AC as a receptacle"),
        ("SW16V",  ["120vac"],            "hardwired", "120V AC ignition, no 12V DC needed"),
        ("SW16VE", ["120vac"],            "hardwired", "AC ignition + AC element - still only 120V AC"),
    ]
    for model, want_supply, want_conn, why in supply_cases:
        p = parse_model(model)
        if p["requires_supply"] != want_supply:
            failures.append(f"{model}: requires_supply expected {want_supply}, "
                            f"got {p['requires_supply']} - {why}")
        if p["ac_connection"] != want_conn:
            failures.append(f"{model}: ac_connection expected {want_conn!r}, "
                            f"got {p['ac_connection']!r} - {why}")

    # the canonical fixture edge must survive the supply logic unchanged:
    # the relay runs on 12V DC the D line already has, so it stays a drop-in
    canonical = compare_models("SW6DE", "SW6DEL")
    if canonical.get("a_to_b", {}).get("verdict") != "drop_in":
        failures.append("SW6DE -> SW6DEL must remain a clean drop_in (VENDOR-Suburban.md 5.1) "
                        f"- got {canonical.get('a_to_b')}")

    # full-empty weight validity rule, against manufacturer chart rows
    # (VENDOR-Suburban.md 6.3, obs #20) and the two retailer records it
    # was checked against
    weight_cases = [
        (6, 34.3, 82.6, True,  "manufacturer SW6DE row - must pass at the corrected 0.971 ratio"),
        (3, 28.3, 52.6, True,  "manufacturer SW3P row"),
        (10, 44.6, 125.6, True, "manufacturer SW10P row"),
        (6, 37.4, 82.6, False, "retailer SW6DE record - empty weight is wrong, must fail"),
        (6, 36.0, 86.04, False, "retailer SW6DEL record - too clean at 1.000, must fail against 0.971"),
    ]
    for nominal, empty, full, want_ok, why in weight_cases:
        ok, ratio, _ = check_weight_consistency(nominal, empty, full)
        if ok is not want_ok:
            failures.append(f"check_weight_consistency({nominal},{empty},{full}): "
                            f"expected ok={want_ok}, got ok={ok} (ratio {ratio}) - {why}")

    print(f"\n{len(CASES)} decode cases, {len(NEGATIVE)} negative cases, "
          f"{len(checks)} tolerance checks, {len(edge_cases)} edge-resolution cases, "
          f"{len(supply_cases)} supply-requirement cases, "
          f"{len(weight_cases)} weight-consistency cases")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


def check_fixture(path):
    """Cross-check the parser against ground-truth.yaml."""
    try:
        import yaml
    except ImportError:
        print("pyyaml not installed", file=sys.stderr)
        return 1

    docs = [d for d in yaml.safe_load_all(open(path)) if d]
    comps = next((d["components"] for d in docs
                  if isinstance(d, dict) and "components" in d), [])

    checked = mismatched = 0
    for c in comps:
        for ident in c.get("identifiers", []):
            val = str(ident.get("value", ""))
            if not _MODEL_RE.match(val.upper().replace(" ", "")):
                continue
            p = parse_model(val)
            if not p["ok"]:
                continue
            checked += 1
            attrs = c.get("attributes", {})
            for fixture_key, parsed_val in (("capacity_gal", p["capacity_gal"]),
                                            ("opening_h", (p["opening"] or {}).get("h")),
                                            ("opening_w", (p["opening"] or {}).get("w"))):
                a = attrs.get(fixture_key)
                if isinstance(a, dict) and a.get("value") is not None:
                    if a["value"] != parsed_val:
                        print(f"  MISMATCH {val} {fixture_key}: "
                              f"fixture={a['value']} parser={parsed_val}")
                        mismatched += 1
            print(f"  {val:<10} {p['capacity_gal']}gal  "
                  f"opening {(p['opening'] or {}).get('h')} x {(p['opening'] or {}).get('w')}"
                  f"  [{p['suffix_provenance']}]")

    print(f"\n{checked} model identifiers parsed from fixture, {mismatched} mismatches")
    return 1 if mismatched else 0


def print_table():
    print(f"{'suffix':<8}{'ignition':<15}{'power':<9}{'elem':<6}{'reign':<7}"
          f"{'relay':<7}{'cord':<6}{'motor-aid':<11}provenance")
    print("-" * 96)
    for suf in sorted(CONFIRMED_SUFFIXES, key=lambda s: (s[0], len(s), s)):
        p = parse_model(f"SW6{suf}")
        print(f"{suf:<8}{p['ignition_system'] or '-':<15}"
              f"{p['ignition_power_source'] or '-':<9}"
              f"{'yes' if p['has_element'] else '-':<6}"
              f"{'yes' if p['has_reignitor'] else '-':<7}"
              f"{'yes' if p['has_relay'] else '-':<7}"
              f"{'yes' if p['corded'] else '-':<6}"
              f"{'MOTORHOME' if p['motor_aid'] else '-':<11}"
              f"{p['suffix_provenance']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", help="model numbers to parse")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check-fixture", metavar="PATH")
    ap.add_argument("--table", action="store_true",
                    help="print every confirmed suffix, decoded")
    ap.add_argument("--compare", nargs=2, metavar=("MODEL_A", "MODEL_B"),
                    help="resolve a substitution edge between two model numbers")
    ap.add_argument("--weight-check", nargs=3, metavar=("NOMINAL_GAL", "EMPTY_LB", "FULL_LB"),
                    type=float, help="check an empty/full weight pair against nominal capacity")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test(args.verbose))
    if args.check_fixture:
        sys.exit(check_fixture(args.check_fixture))
    if args.table:
        print_table()
        return
    if args.compare:
        result = compare_models(*args.compare)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            a, b = args.compare
            print(f"{a} <-> {b}: {result['verdict']}")
            for reason in result.get("reasons", []):
                print(f"  ! {reason}")
            for direction, label in (("a_to_b", f"{a} -> {b}"), ("b_to_a", f"{b} -> {a}")):
                d = result.get(direction)
                if d:
                    print(f"  {label}: {d['verdict']}"
                          + (f" - {d['note']}" if d.get("note") else ""))
                    for c in d.get("blocking_caveats", []):
                        print(f"      ! {c}")
        return
    if args.weight_check:
        nominal, empty, full = args.weight_check
        ok, _, msg = check_weight_consistency(nominal, empty, full)
        print(f"{'PASS' if ok else 'FAIL'}: {msg}")
        return
    if not args.models:
        ap.print_help()
        return

    for m in args.models:
        p = parse_model(m)
        if args.json:
            print(json.dumps(p, indent=2))
            continue
        print(f"\n{m}")
        if not p["ok"]:
            for w in p["warnings"]:
                print(f"  ! {w}")
            continue
        print(f"  {p['capacity_gal']} gal | {p['ignition_system']} ignition "
              f"on {p['ignition_power_source']}")
        feats = [n for n, on in (("element", p["has_element"]),
                                 ("re-igniter", p["has_reignitor"]),
                                 ("interior relay", p["has_relay"]),
                                 ("corded", p["corded"]),
                                 ("motor aid", p["motor_aid"])) if on]
        print(f"  features: {', '.join(feats) if feats else 'none'}")
        if p["opening"]:
            o = p["opening"]
            print(f"  opening:  {o['h']}\" x {o['w']}\" {o['tolerance']} "
                  f"({o['family']}, {o['provenance']})")
        if p["chassis_constraint"]:
            print(f"  CONSTRAINT: {p['chassis_constraint']}")
        print(f"  suffix:   {p['suffix']} [{p['suffix_provenance']}]")
        for w in p["warnings"]:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()