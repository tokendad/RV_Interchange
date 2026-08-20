import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from part_types import (
    PART_TYPES,
    PART_TYPE_NAMES,
    ATWOOD_PART_TYPE,
    COLEMAN_AC_PART_TYPE,
    COLEMAN_AC_PLENUM_PART_TYPE,
    COLEMAN_AC_PLENUM_REPAIR_PART_TYPE,
    COLEMAN_AC_REPAIR_PART_TYPE,
    NORCOLD_REFRIGERATOR_PART_TYPE,
    NORCOLD_REPAIR_PART_TYPE,
    SUBURBAN_COOKTOP_PART_TYPE,
    SUBURBAN_COOKTOP_REPAIR_PART_TYPE,
    SUBURBAN_FURNACE_PART_TYPE,
    SUBURBAN_FURNACE_REPAIR_PART_TYPE,
    THERMOSTAT_PART_TYPE,
    WATER_HEATER_PART_TYPE,
    FURRION_PART_TYPE,
    GIRARD_PART_TYPE,
)


def test_part_types_cover_every_exported_constant():
    exported_ids = {
        WATER_HEATER_PART_TYPE, ATWOOD_PART_TYPE, THERMOSTAT_PART_TYPE,
        SUBURBAN_FURNACE_PART_TYPE, SUBURBAN_FURNACE_REPAIR_PART_TYPE,
        SUBURBAN_COOKTOP_PART_TYPE, SUBURBAN_COOKTOP_REPAIR_PART_TYPE,
        NORCOLD_REFRIGERATOR_PART_TYPE, NORCOLD_REPAIR_PART_TYPE,
        COLEMAN_AC_PART_TYPE, COLEMAN_AC_REPAIR_PART_TYPE,
        COLEMAN_AC_PLENUM_PART_TYPE, COLEMAN_AC_PLENUM_REPAIR_PART_TYPE,
        FURRION_PART_TYPE, GIRARD_PART_TYPE,
    }
    registry_ids = {pt.id for pt in PART_TYPES}
    assert registry_ids == exported_ids
    assert len(PART_TYPES) == len(exported_ids)  # no duplicate ids


def test_part_type_names_is_derived_from_registry():
    assert PART_TYPE_NAMES == {pt.id: pt.display_name for pt in PART_TYPES}


def test_known_part_type_display_names():
    assert PART_TYPE_NAMES[WATER_HEATER_PART_TYPE] == "Water Heater"
    assert PART_TYPE_NAMES[THERMOSTAT_PART_TYPE] == "Wall Thermostat"
    assert PART_TYPE_NAMES[NORCOLD_REFRIGERATOR_PART_TYPE] == "Refrigerator"
