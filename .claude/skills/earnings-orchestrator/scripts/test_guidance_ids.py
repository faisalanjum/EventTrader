#!/usr/bin/env python3
"""Tests for guidance_ids.py — covers every §2A rule."""

import sys
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")

from guidance_ids import (
    slug, canonicalize_unit, canonicalize_value, compute_evhash16,
    canonicalize_source_id, build_guidance_ids, _normalize_text, _normalize_numeric,
    CANONICAL_UNITS, UNIT_ALIASES, VALID_UNITS,
)


# ── slug ────────────────────────────────────────────────────────────────────

def test_slug_basic():
    assert slug("Revenue") == "revenue"
    assert slug("Gross Margin") == "gross_margin"
    assert slug("EPS") == "eps"
    assert slug("D&A") == "d_a"
    assert slug("  Operating Income  ") == "operating_income"

def test_slug_special_chars():
    assert slug("R&D + SG&A") == "r_d_sg_a"
    assert slug("Other Income/Expense Net") == "other_income_expense_net"
    assert slug("___leading___trailing___") == "leading_trailing"

def test_slug_already_clean():
    assert slug("revenue") == "revenue"
    assert slug("total") == "total"


# ── canonicalize_unit ───────────────────────────────────────────────────────

def test_unit_passthrough():
    assert canonicalize_unit("m_usd", "revenue") == "m_usd"
    assert canonicalize_unit("percent", "gross_margin") == "percent"
    assert canonicalize_unit("unknown", "revenue") == "unknown"

def test_unit_per_share_override():
    # EPS should always be usd, never m_usd
    assert canonicalize_unit("m_usd", "eps") == "usd"
    assert canonicalize_unit("usd", "eps") == "usd"
    assert canonicalize_unit("$", "eps") == "usd"
    assert canonicalize_unit("million", "eps") == "usd"
    assert canonicalize_unit("B", "dps") == "usd"

def test_unit_aggregate_currency():
    assert canonicalize_unit("$", "revenue") == "m_usd"
    assert canonicalize_unit("million", "revenue") == "m_usd"
    assert canonicalize_unit("B", "revenue") == "m_usd"
    assert canonicalize_unit("bn", "revenue") == "m_usd"
    assert canonicalize_unit("k", "revenue") == "m_usd"

def test_unit_percentage():
    assert canonicalize_unit("%", "gross_margin") == "percent"
    assert canonicalize_unit("pct", "tax_rate") == "percent"
    assert canonicalize_unit("% yoy", "revenue") == "percent_yoy"
    assert canonicalize_unit("pct_yoy", "revenue") == "percent_yoy"
    assert canonicalize_unit("% y/y", "revenue") == "percent_yoy"

def test_unit_percent_points():
    assert canonicalize_unit("percent_points", "margin_expansion") == "percent_points"
    assert canonicalize_unit("% points", "margin_expansion") == "percent_points"
    assert canonicalize_unit("pp", "margin_expansion") == "percent_points"
    assert canonicalize_unit("percentage points", "margin_delta") == "percent_points"
    assert canonicalize_unit("ppts", "margin_delta") == "percent_points"

def test_unit_basis_points():
    assert canonicalize_unit("basis_points", "yield_spread") == "basis_points"
    assert canonicalize_unit("bps", "yield_spread") == "basis_points"
    assert canonicalize_unit("bp", "yield_spread") == "basis_points"
    assert canonicalize_unit("basis points", "margin") == "basis_points"

def test_unit_misc():
    assert canonicalize_unit("x", "pe_ratio") == "x"
    assert canonicalize_unit("times", "coverage") == "x"
    assert canonicalize_unit("multiple", "ev_ebitda") == "x"
    assert canonicalize_unit("count", "stores") == "count"
    assert canonicalize_unit("shares", "diluted") == "count"
    assert canonicalize_unit("employees", "headcount") == "count"
    assert canonicalize_unit("stores", "locations") == "count"
    assert canonicalize_unit("units", "shipments") == "count"
    assert canonicalize_unit("???", "something") == "unknown"

def test_unit_none_and_empty():
    assert canonicalize_unit(None, "revenue") == "unknown"
    assert canonicalize_unit("", "revenue") == "unknown"


# ── canonicalize_value ──────────────────────────────────────────────────────

def test_value_none():
    assert canonicalize_value(None, "m_usd", "m_usd", "revenue") is None

def test_value_per_share_no_scaling():
    # EPS $1.13 stays 1.13 regardless of raw unit
    assert canonicalize_value(1.13, "usd", "usd", "eps") == 1.13
    assert canonicalize_value(1.13, "$", "usd", "eps") == 1.13

def test_value_percent_no_scaling():
    assert canonicalize_value(45.5, "%", "percent", "gross_margin") == 45.5

def test_value_already_millions():
    # If unit_raw is already 'm_usd' or 'million', no scaling
    assert canonicalize_value(94.0, "m_usd", "m_usd", "revenue") == 94.0


# ── normalize helpers ───────────────────────────────────────────────────────

def test_normalize_text():
    assert _normalize_text(None) == "."
    assert _normalize_text("") == "."
    assert _normalize_text("  Some  Text  ") == "some text"
    assert _normalize_text("assumes no\n  rate   hikes") == "assumes no rate hikes"

def test_normalize_numeric():
    assert _normalize_numeric(None) == "."
    assert _normalize_numeric(1130.0) == "1130"
    assert _normalize_numeric(1.5) == "1.5"
    assert _normalize_numeric(0.0) == "0"
    assert _normalize_numeric(94.123) == "94.123"


# ── evhash16 ────────────────────────────────────────────────────────────────

def test_evhash16_deterministic():
    h1 = compute_evhash16(94.0, 95.5, 97.0, "m_usd", None, None)
    h2 = compute_evhash16(94.0, 95.5, 97.0, "m_usd", None, None)
    assert h1 == h2
    assert len(h1) == 16
    assert all(c in '0123456789abcdef' for c in h1)

def test_evhash16_different_values():
    h1 = compute_evhash16(94.0, 95.5, 97.0, "m_usd", None, None)
    h2 = compute_evhash16(94.0, 96.0, 97.0, "m_usd", None, None)
    assert h1 != h2

def test_evhash16_qualitative():
    h1 = compute_evhash16(None, None, None, "unknown", "low single digits", None)
    h2 = compute_evhash16(None, None, None, "unknown", "mid single digits", None)
    assert h1 != h2

def test_evhash16_conditions_matter():
    h1 = compute_evhash16(100.0, None, None, "m_usd", None, None)
    h2 = compute_evhash16(100.0, None, None, "m_usd", None, "assumes no rate hikes")
    assert h1 != h2

def test_evhash16_all_null():
    h = compute_evhash16(None, None, None, "unknown", None, None)
    assert len(h) == 16


# ── source_id canonicalization ──────────────────────────────────────────────

def test_source_id_colon_replacement():
    assert canonicalize_source_id("0001193125-25-000001") == "0001193125-25-000001"
    assert canonicalize_source_id("bzNews:50123456") == "bzNews_50123456"
    assert canonicalize_source_id("  spaced  ") == "spaced"


# ── build_guidance_ids (integration) ────────────────────────────────────────

def test_build_basic():
    result = build_guidance_ids(
        label="Revenue",
        source_id="0001193125-25-000008",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="non_gaap",
        segment="Total",
        low=94.0, mid=95.5, high=97.0,
        unit_raw="m_usd",
    )
    assert result['guidance_id'] == "guidance:revenue"
    assert result['guidance_update_id'].startswith("gu:0001193125-25-000008:revenue:duration_2025-01-01_2025-03-31:non_gaap:total:")
    assert len(result['evhash16']) == 16
    assert result['label_slug'] == "revenue"
    assert result['segment_slug'] == "total"
    assert result['canonical_unit'] == "m_usd"
    assert result['canonical_low'] == 94.0
    assert result['canonical_mid'] == 95.5
    assert result['canonical_high'] == 97.0

def test_build_eps():
    result = build_guidance_ids(
        label="EPS",
        source_id="AAPL_2025-01-30T17:00:00",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="gaap",
        low=1.10, high=1.15,
        unit_raw="usd",
    )
    assert result['guidance_id'] == "guidance:eps"
    assert result['canonical_unit'] == "usd"
    assert result['canonical_mid'] == 1.125  # auto-computed
    assert "eps" in result['guidance_update_id']

def test_build_qualitative_only():
    result = build_guidance_ids(
        label="Gross Margin",
        source_id="bzNews_50123456",
        period_u_id="duration_2025-04-01_2025-06-30",
        basis_norm="unknown",
        qualitative="low to mid single digits",
    )
    assert result['guidance_id'] == "guidance:gross_margin"
    assert result['canonical_low'] is None
    assert result['canonical_mid'] is None
    assert result['canonical_high'] is None
    assert result['canonical_unit'] == "unknown"

def test_build_source_id_with_colons():
    result = build_guidance_ids(
        label="Revenue",
        source_id="bzNews:50123456",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="m_usd",
        low=100.0, high=110.0,
    )
    assert "bzNews_50123456" in result['guidance_update_id']
    assert ":" not in result['guidance_update_id'].split("gu:")[1].split(":revenue:")[0]

def test_build_idempotent():
    """Same inputs → identical IDs."""
    kwargs = dict(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="gaap", low=100.0, high=110.0, unit_raw="m_usd",
    )
    r1 = build_guidance_ids(**kwargs)
    r2 = build_guidance_ids(**kwargs)
    assert r1['guidance_update_id'] == r2['guidance_update_id']
    assert r1['evhash16'] == r2['evhash16']

def test_build_different_basis_different_id():
    base = dict(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        low=100.0, high=110.0, unit_raw="m_usd",
    )
    r1 = build_guidance_ids(**base, basis_norm="gaap")
    r2 = build_guidance_ids(**base, basis_norm="non_gaap")
    assert r1['guidance_update_id'] != r2['guidance_update_id']
    # But same guidance_id (metric node is shared)
    assert r1['guidance_id'] == r2['guidance_id']

def test_build_different_values_different_id():
    base = dict(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="gaap", unit_raw="m_usd",
    )
    r1 = build_guidance_ids(**base, low=100.0, high=110.0)
    r2 = build_guidance_ids(**base, low=100.0, high=115.0)
    assert r1['guidance_update_id'] != r2['guidance_update_id']
    assert r1['evhash16'] != r2['evhash16']

def test_build_segment_variations():
    base = dict(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="gaap", low=50.0, high=55.0, unit_raw="m_usd",
    )
    r1 = build_guidance_ids(**base, segment="Total")
    r2 = build_guidance_ids(**base, segment="Services")
    assert r1['guidance_update_id'] != r2['guidance_update_id']
    assert "total" in r1['guidance_update_id']
    assert "services" in r2['guidance_update_id']

def test_build_undefined_period():
    result = build_guidance_ids(
        label="Revenue", source_id="src1",
        period_u_id="undefined",
        basis_norm="unknown",
        qualitative="significant growth expected",
    )
    assert "undefined" in result['guidance_update_id']

def test_build_invalid_basis_raises():
    try:
        build_guidance_ids(
            label="Revenue", source_id="src1",
            period_u_id="duration_2025-01-01_2025-03-31",
            basis_norm="adjusted",  # not a valid enum
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_build_empty_label_raises():
    try:
        build_guidance_ids(
            label="", source_id="src1",
            period_u_id="duration_2025-01-01_2025-03-31",
            basis_norm="unknown",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_build_empty_source_id_raises():
    try:
        build_guidance_ids(
            label="Revenue", source_id="  ",
            period_u_id="duration_2025-01-01_2025-03-31",
            basis_norm="unknown",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_build_empty_period_uid_raises():
    try:
        build_guidance_ids(
            label="Revenue", source_id="src1",
            period_u_id="",
            basis_norm="unknown",
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_build_long_range_period():
    result = build_guidance_ids(
        label="Revenue", source_id="src1",
        period_u_id="other_long_range_2028",
        basis_norm="unknown",
        qualitative="mid-teens by FY27",
    )
    assert "other_long_range_2028" in result['guidance_update_id']


# ── Unit registry ─────────────────────────────────────────────────────────────

def test_canonical_units_contains_new_types():
    """basis_points and percent_points are in canonical set."""
    assert 'basis_points' in CANONICAL_UNITS
    assert 'percent_points' in CANONICAL_UNITS

def test_valid_units_is_alias():
    """VALID_UNITS backward alias points to same object."""
    assert VALID_UNITS is CANONICAL_UNITS

def test_all_aliases_resolve_to_canonical():
    """Every UNIT_ALIASES value must be in CANONICAL_UNITS."""
    for alias, canonical in UNIT_ALIASES.items():
        assert canonical in CANONICAL_UNITS, (
            f"alias '{alias}' maps to '{canonical}' which is not in CANONICAL_UNITS"
        )


# ── unit_raw preservation ─────────────────────────────────────────────────────

def test_build_unknown_unit_preserves_raw():
    """When canonical_unit is 'unknown', unit_raw is returned."""
    result = build_guidance_ids(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="widgets",
        low=100.0, high=110.0,
    )
    assert result['canonical_unit'] == 'unknown'
    assert result.get('unit_raw') == 'widgets'

def test_build_known_unit_no_raw():
    """When canonical_unit is known, unit_raw is NOT in result."""
    result = build_guidance_ids(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="m_usd",
        low=100.0, high=110.0,
    )
    assert result['canonical_unit'] == 'm_usd'
    assert 'unit_raw' not in result

def test_build_unknown_string_no_raw():
    """When unit_raw is literally 'unknown', unit_raw is NOT in result."""
    result = build_guidance_ids(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="unknown",
    )
    assert result['canonical_unit'] == 'unknown'
    assert 'unit_raw' not in result

def test_build_basis_points_via_alias():
    """bps alias resolves to basis_points in build_guidance_ids."""
    result = build_guidance_ids(
        label="Yield Spread", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="bps",
        low=50.0, high=75.0,
    )
    assert result['canonical_unit'] == 'basis_points'
    assert 'unit_raw' not in result

def test_build_percent_points_via_alias():
    """pp alias resolves to percent_points in build_guidance_ids."""
    result = build_guidance_ids(
        label="Margin Expansion", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="unknown",
        unit_raw="pp",
        low=1.0, high=2.0,
    )
    assert result['canonical_unit'] == 'percent_points'
    assert 'unit_raw' not in result


# ── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import inspect
    tests = [(name, obj) for name, obj in globals().items()
             if name.startswith('test_') and callable(obj)]
    passed = failed = 0
    for name, fn in sorted(tests):
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
