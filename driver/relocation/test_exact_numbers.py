"""RED battery for the shared exact-number/date utility (WP1 Step 1; module built in Step 2).

`driver/relocation/exact_numbers.py` — pure functions, no I/O, no channel imports:
  dec(value)            exact Decimal from str/int/Decimal; floats REJECTED (may already be lossy)
  eq(a, b)              Decimal-exact equality (no float round-trips)
  period_key(s, e)      validated (start, end) ISO pair, EXACT — no ±1-day sets; bad ISO raises
  is_instant(s, e)      True iff start == end (the law's gp_DATE_DATE instant form)

    venv/bin/python -m pytest driver/relocation/test_exact_numbers.py -q
"""
import pytest
from decimal import Decimal

import exact_numbers as X   # does not exist yet -> the whole file is RED until Step 2


def test_dec_exact_from_string():
    assert X.dec("2.34") == Decimal("2.34")
    assert X.dec("38.3") == Decimal("38.3")
    assert X.dec("0") == Decimal("0")
    assert X.dec("-1138000000") == Decimal("-1138000000")


def test_dec_rejects_floats():
    with pytest.raises(X.ExactError):
        X.dec(2.34)                      # a float may have ALREADY lost the source value


def test_dec_rejects_nan_and_infinity():
    for bad in ('nan', 'NaN', 'Infinity', '-inf', 'inf'):
        with pytest.raises(X.ExactError):
            X.dec(bad)                   # round-12: non-finite values are never source numbers


def test_eq_no_rounding():
    assert not X.eq("2.34", "2.01")      # int-truncation used to conflate these (tier1 L353)
    assert not X.eq("2.34", "2")
    assert X.eq("2.340", "2.34")         # trailing zeros are not a difference
    assert X.eq("0", "0.0")


def test_period_key_exact_no_tolerance():
    assert X.period_key("2024-01-01", "2024-12-31") == ("2024-01-01", "2024-12-31")
    with pytest.raises(X.ExactError):
        X.period_key("2024-13-01", "2024-12-31")     # impossible date
    with pytest.raises(X.ExactError):
        X.period_key("not-a-date", "2024-12-31")


def test_is_instant():
    assert X.is_instant("2024-12-31", "2024-12-31")
    assert not X.is_instant("2024-01-01", "2024-12-31")


def test_EU007_the_graph_stored_spellings_resolve_from_the_boundary_clause():
    """EU-007 (#827): the two stored-spelling members pinned against the
    graph stored-spelling clause at the F7 boundary owner — the boolean set
    is EXACTLY the strings '0'/'1', and the date shape is the strict
    four-digit intersection (narrower than xs:date), calendar-checked."""
    from driver.relocation.exact_numbers import ROUTE_A_BOOLS, _iso_date
    assert ROUTE_A_BOOLS == {'0': False, '1': True}
    assert _iso_date("2024-06-30") is not None
    import pytest as _pytest
    from driver.relocation.exact_numbers import ExactError
    for bad in ("224-04-01", "20240630", "+2024-06-30", "2024-02-30",
                "2024-6-30"):
        with _pytest.raises(ExactError):
            _iso_date(bad)


def test_EU020_the_graph_unit_join_spelling_is_the_clauses():
    """EU-020 (#827): the stored divide-unit name is numerator+denominator
    CONCATENATED with NO separator (the F7 boundary owner's stored-spelling
    clause; iso4217:USDshares in the live census) — pinned here because no
    lead suite reddened on a separator drift (measured 2026-08-08)."""
    from driver.relocation.exact_numbers import graph_unit_spelling
    assert graph_unit_spelling((), ("iso4217:USD",), ("shares",),
                               True) == "iso4217:USDshares"
    assert graph_unit_spelling(("iso4217:USD",), (), (), False) == "iso4217:USD"
    assert graph_unit_spelling(("a", "b"), (), (), False) is None


def test_EU032_plain_is_the_one_canonical_decimal_form():
    """EU-032 (#827): plain() IS the boundary clause's canonical decimal
    form (no exponent, no trailing zeros, -0 -> 0) — pinned member-for-
    member because no lead suite reddened on a strip-off drift (measured
    2026-08-08)."""
    from driver.relocation.exact_numbers import plain
    assert plain("1.500") == "1.5"
    assert plain("1.000") == "1"
    assert plain("-0") == "0"
    assert plain("-0.00") == "0"
    assert plain("1E+3") == "1000"
    assert plain("390") == "390"
    assert plain("-1234567890.12") == "-1234567890.12"
