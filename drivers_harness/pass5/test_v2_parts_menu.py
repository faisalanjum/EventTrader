"""Anchoring upgrade: the producer PICKS the segment from the company's official XBRL parts MENU;
snap_member is a PURE MEMBERSHIP CHECK (no prose parsing). Commodity goes in the segment via the menu →
(core,segment) separates oil≠gas, copper≠gold AND iphone≠services."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v2_schema as S


def _with_menu(ticker, members):
    S._PARTS[ticker] = members


def test_exact_member_pick():
    _with_menu("NVDA", ["DataCenter", "Gaming", "ProfessionalVisualization"])
    assert S.snap_member("NVDA", "DataCenter") == "DataCenter"
    assert S.snap_member("NVDA", "Gaming") == "Gaming"

def test_pick_case_and_spacing_robust():
    _with_menu("NVDA", ["DataCenter", "Gaming"])
    assert S.snap_member("NVDA", "datacenter") == "DataCenter"     # lowercase collapsed
    assert S.snap_member("NVDA", "Data Center") == "DataCenter"    # spaced
    assert S.snap_member("NVDA", "data_center") == "DataCenter"

def test_whole_company_to_total():
    _with_menu("NVDA", ["DataCenter"])
    assert S.snap_member("NVDA", "whole_company") == "Total"
    assert S.snap_member("NVDA", "") == "Total"
    assert S.snap_member("NVDA", "Total") == "Total"

def test_commodity_via_menu_separates_oil_gas():
    _with_menu("FANG", ["Oil", "NaturalGas", "NaturalGasLiquids"])
    assert S.snap_member("FANG", "Oil") == "Oil"
    assert S.snap_member("FANG", "NaturalGas") == "NaturalGas"
    assert S.snap_member("FANG", "Oil") != S.snap_member("FANG", "NaturalGas")   # the object_sib fix

def test_offmenu_pick_does_not_crash():
    # a pick not on the menu and not in the fixture passes through (producer is told: closest or whole_company)
    _with_menu("NVDA", ["DataCenter", "Gaming"])
    out = S.snap_member("NVDA", "SomeUnlistedThing")
    assert isinstance(out, str) and out != ""

def test_no_menu_falls_back_to_fixture_or_total():
    S._PARTS.pop("ZZZ", None)
    assert S.snap_member("ZZZ", "whole_company") == "Total"        # no menu, still resolves


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
