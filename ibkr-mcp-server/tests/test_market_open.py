"""Unit tests for IBClient._is_market_open.

Verifies the truth table for the US-equity real-time streaming window:
- 04:00-20:00 ET on NYSE session days -> True
- Outside that window or on non-session days -> False

NOTE: We patch `app.services.client.dt.datetime` with a subclass that
freezes `.now()` to a deterministic ET wall-clock moment. Other dt
attributes (UTC, time) are inherited unchanged.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from app.services.client import IBClient


ET = ZoneInfo("America/New_York")


def _frozen_utc(year: int, month: int, day: int, hour: int, minute: int) -> dt.datetime:
  """Build a UTC datetime that represents the given ET wall-clock moment."""
  return dt.datetime(year, month, day, hour, minute, tzinfo=ET).astimezone(dt.UTC)


@pytest.fixture
def freeze_now(monkeypatch):
  """Returns a callable that freezes dt.datetime.now() to a given ET moment."""
  def _freeze(year, month, day, hour, minute):
    target = _frozen_utc(year, month, day, hour, minute)

    class FakeDatetime(dt.datetime):
      @classmethod
      def now(cls, tz=None):
        if tz is None:
          return target.replace(tzinfo=None)
        return target.astimezone(tz)

    monkeypatch.setattr("app.services.client.dt.datetime", FakeDatetime)
  return _freeze


def _bare_client() -> IBClient:
  """Build an IBClient skipping __init__ (which needs config + IB())."""
  return IBClient.__new__(IBClient)


# ─── Session-day, in-window cases (must return True) ───────────────────────

def test_rth_midday(freeze_now):
  """Tue 2026-05-12 12:00 ET (RTH center) -> True."""
  freeze_now(2026, 5, 12, 12, 0)
  assert _bare_client()._is_market_open() is True


def test_premarket(freeze_now):
  """Tue 2026-05-12 06:30 ET (premarket) -> True."""
  freeze_now(2026, 5, 12, 6, 30)
  assert _bare_client()._is_market_open() is True


def test_after_hours(freeze_now):
  """Tue 2026-05-12 18:00 ET (after-hours) -> True."""
  freeze_now(2026, 5, 12, 18, 0)
  assert _bare_client()._is_market_open() is True


def test_boundary_04_00_inclusive(freeze_now):
  """04:00:00 ET sharp -> True (inclusive lower bound)."""
  freeze_now(2026, 5, 12, 4, 0)
  assert _bare_client()._is_market_open() is True


def test_boundary_19_59(freeze_now):
  """19:59 ET -> True (just before close of after-hours)."""
  freeze_now(2026, 5, 12, 19, 59)
  assert _bare_client()._is_market_open() is True


# ─── Session-day, out-of-window cases (must return False) ──────────────────

def test_boundary_20_00_exclusive(freeze_now):
  """20:00:00 ET sharp -> False (exclusive upper bound)."""
  freeze_now(2026, 5, 12, 20, 0)
  assert _bare_client()._is_market_open() is False


def test_boundary_03_59(freeze_now):
  """03:59 ET -> False (just before premarket starts)."""
  freeze_now(2026, 5, 12, 3, 59)
  assert _bare_client()._is_market_open() is False


def test_overnight_02_00(freeze_now):
  """02:00 ET on a session day -> False (overnight)."""
  freeze_now(2026, 5, 12, 2, 0)
  assert _bare_client()._is_market_open() is False


def test_overnight_23_30(freeze_now):
  """23:30 ET on a session day -> False (post-AH overnight)."""
  freeze_now(2026, 5, 12, 23, 30)
  assert _bare_client()._is_market_open() is False


# ─── Non-session days (must return False regardless of time) ───────────────

def test_saturday(freeze_now):
  """2026-05-09 (Sat) 12:00 ET -> False (weekend)."""
  freeze_now(2026, 5, 9, 12, 0)
  assert _bare_client()._is_market_open() is False


def test_sunday(freeze_now):
  """2026-05-10 (Sun) 12:00 ET -> False (weekend)."""
  freeze_now(2026, 5, 10, 12, 0)
  assert _bare_client()._is_market_open() is False


def test_christmas_holiday(freeze_now):
  """2026-12-25 (Fri, observed) 12:00 ET -> False (NYSE holiday)."""
  freeze_now(2026, 12, 25, 12, 0)
  assert _bare_client()._is_market_open() is False


def test_new_year_holiday(freeze_now):
  """2026-01-01 (Thu) 12:00 ET -> False (NYSE holiday)."""
  freeze_now(2026, 1, 1, 12, 0)
  assert _bare_client()._is_market_open() is False


def test_independence_day_observed(freeze_now):
  """2026-07-03 (Fri) 12:00 ET -> False.
  July 4 2026 falls on Saturday, so NYSE observes the holiday on Friday July 3.
  exchange_calendars handles the observed-day shift automatically.
  """
  freeze_now(2026, 7, 3, 12, 0)
  assert _bare_client()._is_market_open() is False
