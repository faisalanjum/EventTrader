#!/usr/bin/env python3
"""Exhaustive tests for the math.isfinite() guards in _fmt_num and _fmt_pct.

Proves two things:
1. For ALL finite inputs, output is identical to pre-guard behavior.
2. For non-finite inputs (nan, inf, -inf), output is "—" instead of garbage.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from earnings_orchestrator import _fmt_num, _fmt_money, _fmt_pct


# ── Reference implementations (pre-guard behavior) ──────────────────

def _fmt_num_OLD(val, prefix="", suffix="") -> str:
    """Exact copy of _fmt_num BEFORE the isfinite guard."""
    if val is None:
        return "—"
    v = float(val)
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    abs_v_use = abs_v
    if abs_v_use >= 1e9:
        scaled = abs_v_use / 1e9
        s = f"{scaled:.0f}B" if scaled == int(scaled) else f"{scaled:.2f}B"
    elif abs_v_use >= 1e6:
        scaled = abs_v_use / 1e6
        s = f"{scaled:.0f}M" if scaled == int(scaled) else f"{scaled:.1f}M"
    elif abs_v_use >= 1e3:
        scaled = abs_v_use / 1e3
        s = f"{scaled:.0f}K" if scaled == int(scaled) else f"{scaled:.1f}K"
    elif abs_v_use == int(abs_v_use):
        s = str(int(abs_v_use))
    else:
        s = f"{abs_v_use:.2f}"
    return f"{sign}{prefix}{s}{suffix}"


def _fmt_pct_OLD(val) -> str:
    """Exact copy of _fmt_pct BEFORE the isfinite guard."""
    if val is None:
        return "—"
    sign = "+" if float(val) > 0 else ""
    return f"{sign}{float(val):.1f}%"


# ── Test data ────────────────────────────────────────────────────────

# Every category of finite input the formatters will encounter
FINITE_INPUTS = [
    # Zero
    0, 0.0, -0.0,
    # Small integers
    1, -1, 5, -5, 42, -42, 100, -100, 999, -999,
    # Small floats
    0.01, -0.01, 0.1, -0.1, 0.99, -0.99, 1.5, -1.5, 3.14, -3.14,
    # Thousands boundary
    1000, -1000, 1000.0, 1500, -1500, 9999, -9999, 999.99, -999.99,
    # Thousands
    1234, -1234, 5000, -5000, 10000, 50000, 100000, 999999,
    # Millions boundary
    1e6, -1e6, 1000000.0, 1500000, -1500000, 9999999,
    # Millions
    1.5e6, -1.5e6, 5e6, 10e6, 50e6, 100e6, 500e6, 999999999,
    # Billions boundary
    1e9, -1e9, 1000000000.0,
    # Billions
    1.5e9, -1.5e9, 2.5e9, 10e9, 100e9, 999e9,
    # Trillions (still formats as B)
    1e12, -1e12,
    # Very small
    0.001, -0.001, 0.0001, 0.009,
    # EPS-like values
    0.55, -0.55, 1.23, -1.23, 2.50, -2.50,
    # Revenue-like values
    9.53e9, 37.9e9, 1.234e9,
    # Integer floats
    5.0, -5.0, 100.0, -100.0, 1000.0, -1000.0,
]

NON_FINITE_INPUTS = [
    float("nan"),
    float("inf"),
    float("-inf"),
]

PCT_FINITE_INPUTS = [
    0, 0.0, -0.0,
    0.1, -0.1, 1.0, -1.0,
    5.5, -5.5, 10.0, -10.0,
    25.3, -25.3, 50.0, -50.0,
    99.9, -99.9, 100.0, -100.0,
    150.0, -150.0,  # outlier but valid
    0.01, -0.01,
]

passed = 0
failed = 0


def check(label, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}: got {actual!r}, expected {expected!r}")


# ── Test 1: _fmt_num finite inputs produce identical output ──────────

print("Test 1: _fmt_num — finite inputs (no prefix/suffix)")
for val in FINITE_INPUTS:
    old = _fmt_num_OLD(val)
    new = _fmt_num(val)
    check(f"_fmt_num({val})", new, old)

print("Test 2: _fmt_num — finite inputs with $ prefix")
for val in FINITE_INPUTS:
    old = _fmt_num_OLD(val, prefix="$")
    new = _fmt_num(val, prefix="$")
    check(f"_fmt_num({val}, '$')", new, old)

print("Test 3: _fmt_num — finite inputs with suffix")
for val in FINITE_INPUTS:
    old = _fmt_num_OLD(val, suffix="x")
    new = _fmt_num(val, suffix="x")
    check(f"_fmt_num({val}, suffix='x')", new, old)

print("Test 4: _fmt_money — finite inputs")
for val in FINITE_INPUTS:
    old = _fmt_num_OLD(val, prefix="$")
    new = _fmt_money(val)
    check(f"_fmt_money({val})", new, old)


# ── Test 2: _fmt_num non-finite inputs return "—" ────────────────────

print("Test 5: _fmt_num — non-finite inputs return dash")
for val in NON_FINITE_INPUTS:
    result = _fmt_num(val)
    check(f"_fmt_num({val})", result, "—")

print("Test 6: _fmt_num — non-finite with prefix still returns dash")
for val in NON_FINITE_INPUTS:
    result = _fmt_num(val, prefix="$")
    check(f"_fmt_num({val}, '$')", result, "—")

print("Test 7: _fmt_money — non-finite inputs return dash")
for val in NON_FINITE_INPUTS:
    result = _fmt_money(val)
    check(f"_fmt_money({val})", result, "—")


# ── Test 3: _fmt_num None still works ─────────────────────────────────

print("Test 8: _fmt_num — None input")
check("_fmt_num(None)", _fmt_num(None), "—")
check("_fmt_money(None)", _fmt_money(None), "—")


# ── Test 4: _fmt_pct finite inputs produce identical output ──────────

print("Test 9: _fmt_pct — finite inputs")
for val in PCT_FINITE_INPUTS:
    old = _fmt_pct_OLD(val)
    new = _fmt_pct(val)
    check(f"_fmt_pct({val})", new, old)


# ── Test 5: _fmt_pct non-finite inputs return "—" ────────────────────

print("Test 10: _fmt_pct — non-finite inputs return dash")
for val in NON_FINITE_INPUTS:
    result = _fmt_pct(val)
    check(f"_fmt_pct({val})", result, "—")

print("Test 11: _fmt_pct — None input")
check("_fmt_pct(None)", _fmt_pct(None), "—")


# ── Test 6: string "nan"/"inf" inputs ────────────────────────────────

print("Test 12: string nan/inf inputs")
for s in ["nan", "inf", "-inf", "infinity", "-infinity"]:
    check(f"_fmt_num('{s}')", _fmt_num(s), "—")
    check(f"_fmt_money('{s}')", _fmt_money(s), "—")
    check(f"_fmt_pct('{s}')", _fmt_pct(s), "—")


# ── Test 7: int inputs (common from XBRL/JSON) ──────────────────────

print("Test 13: integer inputs (from JSON deserialization)")
for val in [0, 1, -1, 1000, 1000000, 1000000000]:
    old = _fmt_num_OLD(val, prefix="$")
    new = _fmt_money(val)
    check(f"_fmt_money(int {val})", new, old)


# ── Test 8: Decimal inputs ───────────────────────────────────────────

print("Test 14: Decimal inputs")
from decimal import Decimal
for val in [Decimal("1.23"), Decimal("-5.50"), Decimal("1000000"), Decimal("0")]:
    old = _fmt_num_OLD(val, prefix="$")
    new = _fmt_money(val)
    check(f"_fmt_money(Decimal {val})", new, old)

for val in [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")]:
    check(f"_fmt_money(Decimal {val})", _fmt_money(val), "—")
    check(f"_fmt_pct(Decimal {val})", _fmt_pct(val), "—")


# ── Summary ──────────────────────────────────────────────────────────

print()
print(f"{'='*50}")
print(f"PASSED: {passed}")
print(f"FAILED: {failed}")
print(f"{'='*50}")
sys.exit(1 if failed else 0)
