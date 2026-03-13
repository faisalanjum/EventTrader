#!/usr/bin/env python3
"""Tests for guidance_ids.py — covers every §2A rule."""

import sys
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")

from guidance_ids import (
    slug, canonicalize_unit, canonicalize_value, compute_evhash16,
    canonicalize_source_id, build_guidance_ids, build_period_u_id,
    build_guidance_period_id, KNOWN_INSTANT_LABELS, SENTINEL_MAP,
    _normalize_text, _normalize_numeric, _is_share_count_label,
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
    # Original 4 labels (must still work)
    assert canonicalize_unit("m_usd", "eps") == "usd"
    assert canonicalize_unit("usd", "eps") == "usd"
    assert canonicalize_unit("$", "eps") == "usd"
    assert canonicalize_unit("million", "eps") == "usd"
    assert canonicalize_unit("B", "dps") == "usd"
    assert canonicalize_unit("$", "earnings_per_share") == "usd"
    assert canonicalize_unit("$", "dividends_per_share") == "usd"

    # Variant EPS labels (Issue #28 — previously mapped to m_usd)
    assert canonicalize_unit("$", "adjusted_eps") == "usd"
    assert canonicalize_unit("$", "non_gaap_eps") == "usd"
    assert canonicalize_unit("$", "diluted_eps") == "usd"
    assert canonicalize_unit("$", "basic_eps") == "usd"
    assert canonicalize_unit("$", "gaap_eps") == "usd"
    assert canonicalize_unit("$", "pro_forma_eps") == "usd"
    assert canonicalize_unit("$", "core_eps") == "usd"
    assert canonicalize_unit("$", "normalized_eps") == "usd"
    assert canonicalize_unit("$", "operating_eps") == "usd"
    assert canonicalize_unit("million", "adjusted_eps") == "usd"

    # XBRL-ordered labels (base metric first — startswith rule)
    assert canonicalize_unit("$", "eps_diluted") == "usd"
    assert canonicalize_unit("$", "eps_basic") == "usd"
    assert canonicalize_unit("$", "dps_declared") == "usd"

    # Per-share / per-unit labels (REIT, MLP, specialty)
    assert canonicalize_unit("$", "ffo_per_share") == "usd"
    assert canonicalize_unit("$", "affo_per_share") == "usd"
    assert canonicalize_unit("$", "core_ffo_per_share") == "usd"
    assert canonicalize_unit("$", "nav_per_share") == "usd"
    assert canonicalize_unit("$", "book_value_per_share") == "usd"
    assert canonicalize_unit("$", "distributable_earnings_per_share") == "usd"
    assert canonicalize_unit("$", "distributions_per_unit") == "usd"
    assert canonicalize_unit("$", "affo_per_unit") == "usd"
    assert canonicalize_unit("$", "free_cash_flow_per_share") == "usd"

    # Per-share labels with non-currency units must NOT be overridden
    # (the override only fires when canonical == 'm_usd')
    assert canonicalize_unit("% yoy", "eps") == "percent_yoy"
    assert canonicalize_unit("%", "affo_per_share") == "percent"
    assert canonicalize_unit(None, "eps") == "unknown"
    assert canonicalize_unit(None, "dps") == "unknown"

    # Negative controls: aggregate labels must NOT trigger per-share override
    assert canonicalize_unit("$", "revenue") == "m_usd"
    assert canonicalize_unit("$", "opex") == "m_usd"
    assert canonicalize_unit("$", "capex") == "m_usd"
    assert canonicalize_unit("$", "net_income") == "m_usd"
    assert canonicalize_unit("$", "operating_expenses") == "m_usd"
    assert canonicalize_unit("$", "share_repurchase") == "m_usd"
    assert canonicalize_unit("$", "free_cash_flow") == "m_usd"
    assert canonicalize_unit("$", "adjusted_ebitda") == "m_usd"

    # Edge cases: words containing 'eps' substring must NOT match
    assert canonicalize_unit("$", "steps") == "m_usd"
    assert canonicalize_unit("$", "concepts") == "m_usd"
    assert canonicalize_unit("$", "receipts") == "m_usd"

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

    # Variant per-share labels also skip scaling (Issue #28)
    assert canonicalize_value(1.46, "$", "usd", "adjusted_eps") == 1.46
    assert canonicalize_value(3.50, "$", "usd", "non_gaap_eps") == 3.50
    assert canonicalize_value(2.15, "$", "usd", "affo_per_share") == 2.15
    assert canonicalize_value(0.26, "$", "usd", "distributions_per_unit") == 0.26

    # XBRL-ordered labels also skip scaling (startswith rule)
    assert canonicalize_value(1.13, "$", "usd", "eps_diluted") == 1.13
    assert canonicalize_value(1.13, "$", "usd", "eps_basic") == 1.13

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
    assert result['guidance_update_id'] == "gu:0001193125-25-000008:revenue:duration_2025-01-01_2025-03-31:non_gaap:total"
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

def test_build_different_values_same_id():
    """Same slot, different values → same ID (evhash not in ID). evhash differs as property."""
    base = dict(
        label="Revenue", source_id="src1",
        period_u_id="duration_2025-01-01_2025-03-31",
        basis_norm="gaap", unit_raw="m_usd",
    )
    r1 = build_guidance_ids(**base, low=100.0, high=110.0)
    r2 = build_guidance_ids(**base, low=100.0, high=115.0)
    assert r1['guidance_update_id'] == r2['guidance_update_id']  # same slot = same ID
    assert r1['evhash16'] != r2['evhash16']  # but values differ → evhash differs (property only)

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


# ── build_period_u_id ─────────────────────────────────────────────────────────

def test_period_quarter():
    result = build_period_u_id(cik='320193', fiscal_year=2025, fiscal_quarter=3)
    assert result == 'guidance_period_320193_duration_FY2025_Q3'

def test_period_annual():
    result = build_period_u_id(cik='320193', fiscal_year=2025)
    assert result == 'guidance_period_320193_duration_FY2025'

def test_period_half():
    result = build_period_u_id(cik='320193', fiscal_year=2025, half=2)
    assert result == 'guidance_period_320193_duration_FY2025_H2'

def test_period_long_range_single_year():
    result = build_period_u_id(cik='320193', long_range_start=2028)
    assert result == 'guidance_period_320193_duration_LR_2028'

def test_period_long_range_span():
    result = build_period_u_id(cik='320193', long_range_start=2026, long_range_end=2028)
    assert result == 'guidance_period_320193_duration_LR_2026_2028'

def test_period_long_range_same_start_end():
    """LR with start==end collapses to single year format."""
    result = build_period_u_id(cik='320193', long_range_start=2028, long_range_end=2028)
    assert result == 'guidance_period_320193_duration_LR_2028'

def test_period_medium_term():
    result = build_period_u_id(cik='320193', medium_term=True)
    assert result == 'guidance_period_320193_duration_MT'

def test_period_undefined():
    """No fiscal identity → UNDEF."""
    result = build_period_u_id(cik='320193')
    assert result == 'guidance_period_320193_duration_UNDEF'

def test_period_instant():
    result = build_period_u_id(cik='320193', period_type='instant', fiscal_year=2025, fiscal_quarter=3)
    assert result == 'guidance_period_320193_instant_FY2025_Q3'

def test_period_cik_strips_leading_zeros():
    """CIK '0000320193' → '320193' in output."""
    result = build_period_u_id(cik='0000320193', fiscal_year=2025, fiscal_quarter=1)
    assert result == 'guidance_period_320193_duration_FY2025_Q1'

def test_period_cik_integer_input():
    """Integer CIK accepted and converted."""
    result = build_period_u_id(cik=320193, fiscal_year=2025)
    assert result == 'guidance_period_320193_duration_FY2025'

def test_period_empty_cik_raises():
    try:
        build_period_u_id(cik='')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'cik' in str(e).lower()

def test_period_none_cik_raises():
    try:
        build_period_u_id(cik=None)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_period_invalid_period_type_raises():
    try:
        build_period_u_id(cik='320193', period_type='bogus')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'period_type' in str(e)

def test_period_medium_term_ignores_fiscal():
    """MT takes priority over fiscal_year/quarter if both given."""
    result = build_period_u_id(cik='320193', medium_term=True, fiscal_year=2025, fiscal_quarter=1)
    assert result == 'guidance_period_320193_duration_MT'


# ── build_guidance_period_id ────────────────────────────────────────────────

def test_gp_quarter_dec_fye():
    r = build_guidance_period_id(fye_month=12, fiscal_year=2025, fiscal_quarter=1)
    assert r['u_id'] == 'gp_2025-01-01_2025-03-31'
    assert r['period_scope'] == 'quarter'
    assert r['time_type'] == 'duration'
    assert r['start_date'] == '2025-01-01'
    assert r['end_date'] == '2025-03-31'

def test_gp_quarter_sep_fye():
    """AAPL Q1 FY2025 = Oct-Dec 2024."""
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025, fiscal_quarter=1)
    assert r['u_id'] == 'gp_2024-10-01_2024-12-31'
    assert r['period_scope'] == 'quarter'

def test_gp_annual_sep_fye():
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025)
    assert r['u_id'] == 'gp_2024-10-01_2025-09-30'
    assert r['period_scope'] == 'annual'

def test_gp_half_h2_sep_fye():
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025, half=2)
    assert r['u_id'] == 'gp_2025-04-01_2025-09-30'
    assert r['period_scope'] == 'half'

def test_gp_monthly_march():
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025, month=3)
    assert r['u_id'] == 'gp_2025-03-01_2025-03-31'
    assert r['period_scope'] == 'monthly'

def test_gp_long_range_single_year():
    r = build_guidance_period_id(fye_month=12, long_range_end_year=2028)
    assert r['u_id'] == 'gp_2028-01-01_2028-12-31'
    assert r['period_scope'] == 'long_range'

def test_gp_long_range_span():
    r = build_guidance_period_id(fye_month=12, long_range_start_year=2026, long_range_end_year=2028)
    assert r['u_id'] == 'gp_2026-01-01_2028-12-31'
    assert r['period_scope'] == 'long_range'

def test_gp_sentinel_short_term():
    r = build_guidance_period_id(fye_month=9, sentinel_class='short_term')
    assert r['u_id'] == 'gp_ST'
    assert r['start_date'] is None
    assert r['end_date'] is None
    assert r['period_scope'] == 'short_term'

def test_gp_sentinel_medium_term():
    r = build_guidance_period_id(fye_month=9, sentinel_class='medium_term')
    assert r['u_id'] == 'gp_MT'

def test_gp_sentinel_long_term():
    r = build_guidance_period_id(fye_month=9, sentinel_class='long_term')
    assert r['u_id'] == 'gp_LT'

def test_gp_sentinel_undefined():
    r = build_guidance_period_id(fye_month=9, sentinel_class='undefined')
    assert r['u_id'] == 'gp_UNDEF'

def test_gp_instant_by_label():
    """cash_and_equivalents is a known instant label."""
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025, fiscal_quarter=3, label_slug='cash_and_equivalents')
    assert r['time_type'] == 'instant'
    assert r['start_date'] == r['end_date']  # instant: same date
    assert r['u_id'] == 'gp_2025-06-30_2025-06-30'

def test_gp_instant_by_time_type():
    """Explicit time_type='instant' overrides default."""
    r = build_guidance_period_id(fye_month=12, fiscal_year=2025, fiscal_quarter=2, time_type='instant')
    assert r['time_type'] == 'instant'
    assert r['start_date'] == '2025-06-30'
    assert r['end_date'] == '2025-06-30'

def test_gp_calendar_override():
    """calendar_override forces FYE=12 regardless of actual FYE."""
    r = build_guidance_period_id(fye_month=9, fiscal_year=2025, fiscal_quarter=1, calendar_override=True)
    assert r['u_id'] == 'gp_2025-01-01_2025-03-31'  # Jan-Mar, not Oct-Dec

def test_gp_fallthrough_to_undef():
    """All nulls with no sentinel_class -> defensive fallthrough to gp_UNDEF."""
    r = build_guidance_period_id(fye_month=9)
    assert r['u_id'] == 'gp_UNDEF'
    assert r['period_scope'] == 'undefined'

def test_gp_default_time_type_duration():
    """Default time_type is duration when not specified."""
    r = build_guidance_period_id(fye_month=12, fiscal_year=2025, fiscal_quarter=1)
    assert r['time_type'] == 'duration'

def test_gp_invalid_sentinel_raises():
    """Invalid sentinel_class raises ValueError."""
    try:
        build_guidance_period_id(fye_month=9, sentinel_class='bogus')
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_gp_invalid_half_raises():
    """Invalid half value raises ValueError."""
    try:
        build_guidance_period_id(fye_month=9, fiscal_year=2025, half=3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ── Share-count canonicalization (Change 1-3 + Guard C) ─────────────────────

def test_count_label_unit_billion_diluted_share_count():
    """canonicalize_unit('billion', 'diluted_share_count') → 'count'"""
    assert canonicalize_unit('billion', 'diluted_share_count') == 'count'

def test_count_label_unit_million_share_count():
    """canonicalize_unit('million', 'share_count') → 'count'"""
    assert canonicalize_unit('million', 'share_count') == 'count'

def test_count_label_unit_billion_revenue_negative():
    """Negative control: revenue is NOT a count label."""
    assert canonicalize_unit('billion', 'revenue') == 'm_usd'

def test_count_label_unit_billion_share_repurchase_negative():
    """Negative control: share_repurchase is NOT a count label."""
    assert canonicalize_unit('billion', 'share_repurchase') == 'm_usd'

def test_count_value_scaling_billion():
    """4.94 billion diluted shares → 4,940,000,000.0 absolute."""
    result = canonicalize_value(4.94, 'billion', 'count', 'diluted_share_count')
    assert result == 4940000000.0, f"expected 4940000000.0, got {result}"

def test_share_count_value_scaling_million():
    """300 million share_count → 300,000,000.0 absolute."""
    result = canonicalize_value(300, 'million', 'count', 'share_count')
    assert result == 300000000.0, f"expected 300000000.0, got {result}"

def test_is_share_count_label_classifier():
    """_is_share_count_label matches reviewed share-count labels only."""
    assert _is_share_count_label('diluted_share_count') is True
    assert _is_share_count_label('share_count') is True
    assert _is_share_count_label('diluted_shares') is True
    assert _is_share_count_label('basic_shares') is True
    assert _is_share_count_label('shares_outstanding') is True
    # Negative controls
    assert _is_share_count_label('subscriber_count') is False
    assert _is_share_count_label('store_count') is False
    assert _is_share_count_label('share_repurchase') is False
    assert _is_share_count_label('share_based_compensation') is False
    assert _is_share_count_label('revenue') is False
    assert _is_share_count_label('eps') is False
    assert _is_share_count_label('discount') is False

def test_build_guidance_ids_avgo_share_count():
    """Integration: AVGO diluted share count gets count, not m_usd."""
    ids = build_guidance_ids(
        label='Diluted Share Count',
        source_id='AVGO_test',
        period_u_id='gp_test',
        unit_raw='billion',
        low=4.94, mid=4.94, high=4.94,
        basis_norm='unknown',
    )
    assert ids['canonical_unit'] == 'count', f"got {ids['canonical_unit']}"
    assert ids['canonical_low'] == 4940000000.0, f"got {ids['canonical_low']}"
    assert ids['canonical_mid'] == 4940000000.0
    assert ids['canonical_high'] == 4940000000.0
    # unit_raw should be stripped for known canonical units
    assert 'unit_raw' not in ids or ids.get('unit_raw') is None


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
