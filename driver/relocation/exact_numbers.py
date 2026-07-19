"""exact_numbers — THE shared exact-value/date helpers for the locator engine (v5.5 §4/§5).

Pure functions, no I/O, no channel imports. Decimal-exact everywhere: floats are REJECTED at the
door because a float may have ALREADY lost the source value (same philosophy as the id law's
num_canon). Dates: the graph's storage convention is inclusive (verified live 2026-07-18, round-5
census); comparison is normalize-once-by-known-format then EXACT — no ±1-day tolerance sets
(they accepted convention-inconsistent pairs; reproduced round 5).
"""
from datetime import date
from decimal import Decimal, InvalidOperation


class ExactError(ValueError):
    """Bad input to an exact comparison — callers treat as non-matching / abstain."""


def dec(value):
    """Exact Decimal from str/int/Decimal. Floats REJECTED (already potentially lossy)."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ExactError(f"floats are rejected (lossy): {value!r}")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        raise ExactError(f"not a decimal number: {value!r}")


def eq(a, b):
    """Decimal-exact equality; trailing zeros are not a difference. Bad input -> ExactError."""
    return dec(a) == dec(b)


def _iso(d):
    try:
        return date.fromisoformat(d).isoformat()
    except (TypeError, ValueError):
        raise ExactError(f"bad ISO date: {d!r}")


def period_key(start, end):
    """Validated (start, end) ISO pair, EXACT — the one date rule. No tolerance of any kind."""
    s, e = _iso(start), _iso(end)
    if e < s:
        raise ExactError(f"period ends before it starts: {start!r}..{end!r}")
    return (s, e)


def plain(value):
    """Canonical plain string: no exponent, no trailing zeros, '-0' -> '0'."""
    out = format(dec(value), 'f')
    if '.' in out:
        out = out.rstrip('0').rstrip('.')
    return '0' if out in ('', '-0') else out


def is_instant(start, end):
    """True iff start == end — the law's proven instant form (gp_DATE_DATE)."""
    s, e = period_key(start, end)
    return s == e
