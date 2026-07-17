"""S3.3 — driver-law unit wrapper tests (per-slot hints · hard per-X lint · OD-11 basis).

The proven mechanics live in the relocated unit_resolver (29+7 suite, untouched).
These tests cover only what CURRENT LAW adds on top (FINAL_DESIGN §6.1):
per-slot hints, per-X lint as a HARD failure on money levels, the OD-11
growth-basis ladder consuming the upstream period_scope, and the 10-unit enum.
"""
import pytest
from decimal import Decimal

from driver.core.driver_units import (
    DRIVER_UNITS,
    UnitResolutionError,
    resolve_driver_units,
)


def test_enum_is_the_ten_units():
    assert DRIVER_UNITS == frozenset({
        "usd", "m_usd", "percent", "percent_yoy", "percent_sequential",
        "percent_points", "basis_points", "count", "x", "unknown",
    })


def test_per_slot_hints_level_and_change_independent():
    out = resolve_driver_units(
        "revenue",
        level_values=[Decimal("1.5"), 2], level_unit_raw="$B",
        level_unit_kind_hint="money", level_money_mode_hint="aggregate",
        change_value=12, change_unit_raw="% yoy", change_unit_kind_hint="ratio",
        period_scope="quarter",
    )
    assert out["level_unit"] == "m_usd" and out["level_values"] == [1500.0, 2000.0]
    assert out["change_unit"] == "percent_yoy" and out["change_value"] == 12.0


def test_comparison_values_share_the_level_resolution():
    out = resolve_driver_units(
        "revenue",
        level_values=[Decimal("4.9")], level_unit_raw="B",
        level_unit_kind_hint="money", level_money_mode_hint="aggregate",
        comparison_values=[Decimal("4.8"), None],
        period_scope="quarter",
    )
    assert out["level_values"] == [4900.0]
    assert out["comparison_values"] == [4800.0, None]


def test_per_x_lint_is_a_hard_failure_on_money_level():
    with pytest.raises(UnitResolutionError, match="_per_"):
        resolve_driver_units("oil_price", level_values=[80], level_unit_raw="$/barrel",
                             period_scope="quarter")


def test_per_x_in_name_passes_with_base_usd():
    out = resolve_driver_units("oil_price_per_barrel", level_values=[80],
                               level_unit_raw="$/barrel", period_scope="quarter")
    assert out["level_unit"] == "usd" and out["level_values"] == [80.0]


def test_cents_on_aggregate_raises():
    with pytest.raises(UnitResolutionError, match="cents"):
        resolve_driver_units("revenue", level_values=[50], level_unit_raw="cents",
                             level_unit_kind_hint="money", level_money_mode_hint="aggregate",
                             period_scope="quarter")


# ---- OD-11 growth basis (consumes upstream period_scope, never infers) ----

def growth(change_raw="% yoy", **kw):
    kw.setdefault("percent_level_metric", False)
    out = resolve_driver_units("revenue", change_value=12, change_unit_raw=change_raw,
                               change_unit_kind_hint="ratio", **kw)
    return out["change_unit"]


def test_annual_pin_sequential_impossible_on_annual():
    assert growth(period_scope="annual", sequential_evidence=True) == "percent_yoy"


def test_sequential_needs_in_document_evidence():
    assert growth(period_scope="quarter", sequential_evidence=True) == "percent_sequential"
    assert growth(period_scope="quarter") == "percent_yoy"          # the dated default


def test_sentinel_or_missing_scope_fails_closed_to_unknown():
    assert growth(period_scope="long_term") == "unknown"
    assert growth(period_scope=None) == "unknown"


def test_points_and_bps_win_over_any_basis_wording():
    out = resolve_driver_units("margin", change_value=120, change_unit_raw="bps",
                               change_unit_kind_hint="ratio",
                               period_scope="quarter", sequential_evidence=True)
    assert out["change_unit"] == "basis_points"


def test_static_percent_gate_plain_pct_change_on_pct_level_metric():
    out = resolve_driver_units(
        "operating_margin",
        level_values=[Decimal("17.6")], level_unit_raw="%", level_unit_kind_hint="ratio",
        change_value=3, change_unit_raw="%", change_unit_kind_hint="ratio",
        period_scope="quarter",
    )
    assert out["level_unit"] == "percent"
    assert out["change_unit"] == "unknown"          # relative-vs-points ambiguity
    assert any("static" in w for w in out["warnings"])


def test_plain_pct_change_on_money_metric_is_growth():
    out = resolve_driver_units("revenue", change_value=12, change_unit_raw="%",
                               change_unit_kind_hint="ratio", percent_level_metric=False,
                               period_scope="quarter")
    assert out["change_unit"] == "percent_yoy"


def test_plain_pct_change_with_unknown_metric_levelness_fails_closed():
    out = resolve_driver_units("mystery_metric", change_value=3, change_unit_raw="%",
                               change_unit_kind_hint="ratio", period_scope="quarter")
    assert out["change_unit"] == "unknown"


def test_percent_growth_LEVEL_takes_the_basis_ladder():
    # "we expect revenue growth of 10%" — the growth basis rides level_unit (guidance)
    out = resolve_driver_units("revenue_growth", level_values=[10], level_unit_raw="% yoy",
                               level_unit_kind_hint="ratio", period_scope="annual")
    assert out["level_unit"] == "percent_yoy"
    out = resolve_driver_units("revenue_growth", level_values=[10], level_unit_raw="% yoy",
                               level_unit_kind_hint="ratio", period_scope="long_term")
    assert out["level_unit"] == "unknown"           # sentinel horizon fails closed


def test_numberless_growth_takes_unit_from_framing():
    out = resolve_driver_units("revenue_growth", level_unit_raw="% yoy",
                               level_unit_kind_hint="ratio", period_scope="quarter")
    assert out["level_unit"] == "percent_yoy" and out["level_values"] == []


def test_no_numbers_no_raw_no_resolution():
    out = resolve_driver_units("dividend", period_scope=None)
    assert out["level_unit"] is None and out["change_unit"] is None


# ---- owner exactness law (2026-07-17): exact Decimal scaling, no auto-rounding ----

def test_exact_scaling_no_six_decimal_rounding():
    from decimal import Decimal
    out = resolve_driver_units(
        "eps", level_values=[Decimal("0.1234567")], level_unit_raw="$",
        level_unit_kind_hint="money", level_money_mode_hint="price_like",
        period_scope="quarter")
    assert out["level_values"] == [Decimal("0.1234567")]   # 7th decimal SURVIVES
    out2 = resolve_driver_units(
        "revenue", level_values=[Decimal("8.125")], level_unit_raw="B",
        level_unit_kind_hint="money", level_money_mode_hint="aggregate",
        period_scope="quarter")
    assert out2["level_values"][0] == Decimal("8125")


def test_float_source_values_rejected_at_the_units_seam():
    with pytest.raises(UnitResolutionError, match="exact"):
        resolve_driver_units("revenue", level_values=[1.5], level_unit_raw="B",
                             level_unit_kind_hint="money",
                             level_money_mode_hint="aggregate", period_scope="quarter")
