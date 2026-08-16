"""Canonical part-type registry for the interchange graph.

Mirrors edge_types.py's single-source-of-truth pattern: the resolver, the
service layer, and the seeded `part_types` table (interchange_schema.py)
all derive from PART_TYPES below instead of each keeping their own copy.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PartType:
    id: int
    display_name: str
    description: str = ""


WATER_HEATER_PART_TYPE = 412
ATWOOD_PART_TYPE = 413
THERMOSTAT_PART_TYPE = 415
SUBURBAN_FURNACE_PART_TYPE = 416
SUBURBAN_FURNACE_REPAIR_PART_TYPE = 417
SUBURBAN_COOKTOP_PART_TYPE = 601
NORCOLD_REFRIGERATOR_PART_TYPE = 602
NORCOLD_REPAIR_PART_TYPE = 603
COLEMAN_AC_PART_TYPE = 604
COLEMAN_AC_REPAIR_PART_TYPE = 605
SUBURBAN_COOKTOP_REPAIR_PART_TYPE = 606
COLEMAN_AC_PLENUM_PART_TYPE = 607
COLEMAN_AC_PLENUM_REPAIR_PART_TYPE = 608
FURRION_PART_TYPE = 418
GIRARD_PART_TYPE = 419

PART_TYPES = (
    PartType(id=WATER_HEATER_PART_TYPE, display_name="Water Heater"),
    PartType(id=ATWOOD_PART_TYPE, display_name="Water Heater"),
    PartType(id=THERMOSTAT_PART_TYPE, display_name="Wall Thermostat"),
    PartType(id=SUBURBAN_FURNACE_PART_TYPE, display_name="Furnace"),
    PartType(id=SUBURBAN_FURNACE_REPAIR_PART_TYPE, display_name="Furnace Repair Part"),
    PartType(id=SUBURBAN_COOKTOP_PART_TYPE, display_name="Cooktop"),
    PartType(id=NORCOLD_REFRIGERATOR_PART_TYPE, display_name="Refrigerator"),
    PartType(id=NORCOLD_REPAIR_PART_TYPE, display_name="Refrigerator Repair Part"),
    PartType(id=COLEMAN_AC_PART_TYPE, display_name="Rooftop Air Conditioner"),
    PartType(id=COLEMAN_AC_REPAIR_PART_TYPE, display_name="Rooftop Air Conditioner Repair Part"),
    PartType(id=SUBURBAN_COOKTOP_REPAIR_PART_TYPE, display_name="Cooktop/Range Repair Part"),
    PartType(id=COLEMAN_AC_PLENUM_PART_TYPE, display_name="Rooftop AC Ceiling Plenum"),
    PartType(id=COLEMAN_AC_PLENUM_REPAIR_PART_TYPE,
             display_name="Rooftop AC Ceiling Plenum Repair Part"),
    PartType(id=FURRION_PART_TYPE, display_name="Water Heater"),
    PartType(id=GIRARD_PART_TYPE, display_name="Water Heater"),
)

PART_TYPE_NAMES = {pt.id: pt.display_name for pt in PART_TYPES}
