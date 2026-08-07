import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Docs" / "Tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manufacturers import MANUFACTURERS, MANUFACTURER_NAMES


def test_manufacturers_cover_the_four_shipped_vendors():
    assert {m.ns for m in MANUFACTURERS} == {"suburban", "coleman", "atwood", "norcold"}


def test_manufacturer_names_is_derived_from_registry():
    assert MANUFACTURER_NAMES == {m.ns: m.display_name for m in MANUFACTURERS}


def test_known_manufacturer_display_names():
    assert MANUFACTURER_NAMES["coleman"] == "Coleman-Mach"
    assert MANUFACTURER_NAMES["suburban"] == "Suburban"
    assert MANUFACTURER_NAMES["atwood"] == "Atwood"
    assert MANUFACTURER_NAMES["norcold"] == "Norcold"


def test_non_manufacturer_namespaces_are_absent():
    # icm/dwin/kib (sub-component namespaces) and silkscreen (a physical-marking
    # identifier type) are real ns values in ground-truth.yaml but are not
    # manufacturers - callers must .get() and handle a miss, not assume coverage.
    for ns in ("icm", "dwin", "kib", "silkscreen"):
        assert ns not in MANUFACTURER_NAMES
