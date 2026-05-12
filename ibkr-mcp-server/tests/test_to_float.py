"""Unit tests for app.services.history._to_float.

Verifies handling of all IB-side sentinel values that indicate "no data":
- NaN: ticker field never populated
- -1:  IB-documented sentinel returned when market closed for the venue
- None: defensive against direct None input
"""

import math

from app.services.history import _to_float


def test_valid_positive_float():
  assert _to_float(123.45) == 123.45


def test_zero_preserved():
  """0 is a valid price for some securities (e.g., expired options, zero-cost bonds).
  Must NOT be treated as a missing-data sentinel.
  """
  assert _to_float(0) == 0
  assert _to_float(0.0) == 0.0


def test_nan_returns_none():
  assert _to_float(float("nan")) is None


def test_minus_one_returns_none():
  """IB documented behavior: bid/ask = -1 when market closed.
  Must propagate as None to downstream consumers.
  """
  assert _to_float(-1) is None
  assert _to_float(-1.0) is None


def test_none_returns_none():
  """Defensive: should not crash on direct None input."""
  assert _to_float(None) is None


def test_other_negative_values_preserved():
  """Only -1 is the sentinel; other negatives are legitimate values
  (e.g., options deltas, basis spreads, futures spread quotes).
  """
  assert _to_float(-0.5) == -0.5
  assert _to_float(-2.0) == -2.0
  assert _to_float(-100.0) == -100.0


def test_large_positive():
  assert _to_float(1_000_000.5) == 1_000_000.5
