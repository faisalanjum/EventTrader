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
    with pytest.raises(Exception):
        X.dec(2.34)                      # a float may have ALREADY lost the source value


def test_dec_rejects_nan_and_infinity():
    for bad in ('nan', 'NaN', 'Infinity', '-inf', 'inf'):
        with pytest.raises(Exception):
            X.dec(bad)                   # round-12: non-finite values are never source numbers


def test_eq_no_rounding():
    assert not X.eq("2.34", "2.01")      # int-truncation used to conflate these (tier1 L353)
    assert not X.eq("2.34", "2")
    assert X.eq("2.340", "2.34")         # trailing zeros are not a difference
    assert X.eq("0", "0.0")


def test_period_key_exact_no_tolerance():
    assert X.period_key("2024-01-01", "2024-12-31") == ("2024-01-01", "2024-12-31")
    with pytest.raises(Exception):
        X.period_key("2024-13-01", "2024-12-31")     # impossible date
    with pytest.raises(Exception):
        X.period_key("not-a-date", "2024-12-31")


def test_is_instant():
    assert X.is_instant("2024-12-31", "2024-12-31")
    assert not X.is_instant("2024-01-01", "2024-12-31")
