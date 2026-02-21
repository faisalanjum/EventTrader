#!/usr/bin/env python3
"""Tests for fiscal_resolve.py — the CLI wrapper for fiscal→calendar resolution."""

import json
import sys
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")

from fiscal_resolve import resolve, _resolve_from_periods
from get_quarterly_filings import _compute_fiscal_dates


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_period(u_id, start, end):
    """Shorthand for building a period dict."""
    return {"u_id": u_id, "start_date": start, "end_date": end}


# Pre-built period sets for common test scenarios

# Apple FYE=9 (September), FY2024
AAPL_PERIODS = [
    _make_period("duration_2023-10-01_2023-12-30", "2023-10-01", "2023-12-30"),  # Q1 FY2024
    _make_period("duration_2023-12-31_2024-03-30", "2023-12-31", "2024-03-30"),  # Q2 FY2024
    _make_period("duration_2024-03-31_2024-06-29", "2024-03-31", "2024-06-29"),  # Q3 FY2024
    _make_period("duration_2023-10-01_2024-09-28", "2023-10-01", "2024-09-28"),  # FY 2024
]

# Standard calendar FYE=12 (December), FY2025
STD_PERIODS = [
    _make_period("duration_2025-01-01_2025-03-31", "2025-01-01", "2025-03-31"),  # Q1
    _make_period("duration_2025-04-01_2025-06-30", "2025-04-01", "2025-06-30"),  # Q2
    _make_period("duration_2025-07-01_2025-09-30", "2025-07-01", "2025-09-30"),  # Q3
    _make_period("duration_2025-01-01_2025-12-31", "2025-01-01", "2025-12-31"),  # FY
]


# ── resolve() with empty periods (fallback path) ────────────────────────────

def test_fallback_q1_dec_fye():
    """Q1 with December FYE → Jan-Mar."""
    result = resolve("TEST", 2025, "Q1", 12, "[]")
    assert result["start_date"] == "2025-01-01"
    assert result["end_date"] == "2025-03-31"
    assert result["period_u_id"] == "duration_2025-01-01_2025-03-31"
    assert result["period_node_type"] == "duration"
    assert result["source"] == "fallback"

def test_fallback_q2_dec_fye():
    result = resolve("TEST", 2025, "Q2", 12, "[]")
    assert result["start_date"] == "2025-04-01"
    assert result["end_date"] == "2025-06-30"
    assert result["source"] == "fallback"

def test_fallback_q3_dec_fye():
    result = resolve("TEST", 2025, "Q3", 12, "[]")
    assert result["start_date"] == "2025-07-01"
    assert result["end_date"] == "2025-09-30"

def test_fallback_q4_dec_fye():
    result = resolve("TEST", 2025, "Q4", 12, "[]")
    assert result["start_date"] == "2025-10-01"
    assert result["end_date"] == "2025-12-31"

def test_fallback_fy_dec_fye():
    result = resolve("TEST", 2025, "FY", 12, "[]")
    assert result["start_date"] == "2025-01-01"
    assert result["end_date"] == "2025-12-31"

def test_fallback_q1_sep_fye():
    """Q1 with September FYE (Apple-like) → Oct-Dec."""
    result = resolve("AAPL", 2025, "Q1", 9, "[]")
    assert result["start_date"] == "2024-10-01"
    assert result["end_date"] == "2024-12-31"
    assert result["source"] == "fallback"

def test_fallback_fy_sep_fye():
    result = resolve("AAPL", 2025, "FY", 9, "[]")
    assert result["start_date"] == "2024-10-01"
    assert result["end_date"] == "2025-09-30"


# ── resolve() with pre-fetched periods (lookup path) ────────────────────────

def test_lookup_q1_std():
    """Standard Q1 lookup from pre-fetched periods."""
    result = resolve("TEST", 2025, "Q1", 12, json.dumps(STD_PERIODS))
    assert result["start_date"] == "2025-01-01"
    assert result["end_date"] == "2025-03-31"
    assert result["source"] == "lookup"

def test_lookup_q2_std():
    result = resolve("TEST", 2025, "Q2", 12, json.dumps(STD_PERIODS))
    assert result["start_date"] == "2025-04-01"
    assert result["end_date"] == "2025-06-30"
    assert result["source"] == "lookup"

def test_lookup_fy_std():
    result = resolve("TEST", 2025, "FY", 12, json.dumps(STD_PERIODS))
    assert result["start_date"] == "2025-01-01"
    assert result["end_date"] == "2025-12-31"
    assert result["source"] == "lookup"

def test_lookup_aapl_q1():
    """Apple Q1 FY2024 (52-week calendar, non-standard dates)."""
    result = resolve("AAPL", 2024, "Q1", 9, json.dumps(AAPL_PERIODS))
    assert result["start_date"] == "2023-10-01"
    assert result["end_date"] == "2023-12-30"
    assert result["source"] == "lookup"

def test_lookup_aapl_q2():
    result = resolve("AAPL", 2024, "Q2", 9, json.dumps(AAPL_PERIODS))
    assert result["start_date"] == "2023-12-31"
    assert result["end_date"] == "2024-03-30"
    assert result["source"] == "lookup"

def test_lookup_aapl_q3():
    result = resolve("AAPL", 2024, "Q3", 9, json.dumps(AAPL_PERIODS))
    assert result["start_date"] == "2024-03-31"
    assert result["end_date"] == "2024-06-29"
    assert result["source"] == "lookup"

def test_lookup_aapl_fy():
    result = resolve("AAPL", 2024, "FY", 9, json.dumps(AAPL_PERIODS))
    assert result["start_date"] == "2023-10-01"
    assert result["end_date"] == "2024-09-28"
    assert result["source"] == "lookup"


# ── Q4 derivation from Q3+FY ────────────────────────────────────────────────

def test_lookup_q4_derived_from_q3_fy():
    """Q4 derived from Q3 end + 1 day to FY end (Apple-style, no explicit Q4 period)."""
    result = resolve("AAPL", 2024, "Q4", 9, json.dumps(AAPL_PERIODS))
    assert result["start_date"] == "2024-06-30"
    assert result["end_date"] == "2024-09-28"
    assert result["source"] == "lookup"

def test_lookup_q4_std():
    """Q4 with standard periods where no explicit Q4 period exists but FY does."""
    result = resolve("TEST", 2025, "Q4", 12, json.dumps(STD_PERIODS))
    assert result["start_date"] == "2025-10-01"
    assert result["end_date"] == "2025-12-31"
    assert result["source"] == "lookup"


# ── Missing period → fallback ───────────────────────────────────────────────

def test_missing_quarter_falls_back():
    """If requested quarter not in periods, falls back to deterministic."""
    # Only Q1 exists, asking for Q3
    partial = [_make_period("duration_2025-01-01_2025-03-31", "2025-01-01", "2025-03-31")]
    result = resolve("TEST", 2025, "Q3", 12, json.dumps(partial))
    assert result["start_date"] == "2025-07-01"
    assert result["end_date"] == "2025-09-30"
    assert result["source"] == "fallback"

def test_wrong_year_falls_back():
    """Periods from different year don't match."""
    result = resolve("TEST", 2026, "Q1", 12, json.dumps(STD_PERIODS))
    assert result["source"] == "fallback"
    assert result["start_date"] == "2026-01-01"


# ── period_u_id format ──────────────────────────────────────────────────────

def test_period_u_id_format():
    """period_u_id is always duration_{start}_{end}."""
    result = resolve("TEST", 2025, "Q1", 12, "[]")
    assert result["period_u_id"] == f"duration_{result['start_date']}_{result['end_date']}"

def test_period_u_id_from_lookup():
    """period_u_id built from resolved dates, not from Period node u_id."""
    result = resolve("TEST", 2025, "Q1", 12, json.dumps(STD_PERIODS))
    assert result["period_u_id"] == "duration_2025-01-01_2025-03-31"


# ── Quarter normalization ────────────────────────────────────────────────────

def test_quarter_normalization():
    """Accepts various quarter formats."""
    r1 = resolve("TEST", 2025, "1", 12, "[]")
    r2 = resolve("TEST", 2025, "Q1", 12, "[]")
    assert r1["start_date"] == r2["start_date"]
    assert r1["end_date"] == r2["end_date"]

def test_annual_normalization():
    r1 = resolve("TEST", 2025, "FY", 12, "[]")
    r2 = resolve("TEST", 2025, "ANNUAL", 12, "[]")
    assert r1["start_date"] == r2["start_date"]


# ── Edge cases ───────────────────────────────────────────────────────────────

def test_invalid_fye_month():
    result = resolve("TEST", 2025, "Q1", 13, "[]")
    assert "error" in result

def test_invalid_quarter_raises():
    try:
        resolve("TEST", 2025, "Q5", 12, "[]")
        assert False, "Should have raised"
    except ValueError:
        pass

def test_empty_periods_json_string():
    """Empty string treated as empty array."""
    result = resolve("TEST", 2025, "Q1", 12, "[]")
    assert result["source"] == "fallback"

def test_periods_as_list():
    """Can pass periods as list directly (not JSON string)."""
    result = resolve("TEST", 2025, "Q1", 12, STD_PERIODS)
    assert result["source"] == "lookup"
    assert result["start_date"] == "2025-01-01"

def test_malformed_period_skipped():
    """Periods with bad dates are silently skipped."""
    bad = [{"u_id": "bad", "start_date": "not-a-date", "end_date": "also-bad"}]
    result = resolve("TEST", 2025, "Q1", 12, json.dumps(bad))
    assert result["source"] == "fallback"

def test_inverted_period_skipped():
    """Period where end < start is skipped."""
    bad = [_make_period("inv", "2025-03-31", "2025-01-01")]
    result = resolve("TEST", 2025, "Q1", 12, json.dumps(bad))
    assert result["source"] == "fallback"


# ── Consistency with _compute_fiscal_dates ───────────────────────────────────

def test_fallback_matches_compute_fiscal_dates():
    """Fallback output matches _compute_fiscal_dates() directly."""
    for fye in [3, 6, 9, 12]:
        for fq in ["Q1", "Q2", "Q3", "Q4", "FY"]:
            expected_start, expected_end = _compute_fiscal_dates(fye, 2025, fq)
            result = resolve("TEST", 2025, fq, fye, "[]")
            assert result["start_date"] == expected_start, \
                f"FYE={fye} {fq}: {result['start_date']} != {expected_start}"
            assert result["end_date"] == expected_end, \
                f"FYE={fye} {fq}: {result['end_date']} != {expected_end}"


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
