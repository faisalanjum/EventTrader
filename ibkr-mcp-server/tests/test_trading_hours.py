"""Unit tests for app.services.trading_hours.

Two layers:
1. _is_in_window — pure parser, no IB. Boundary + asset-class coverage.
2. is_contract_open — IB-fronted cache + fallback. Mock IB via SimpleNamespace.

Coverage targets: US-equity boundaries, forex cross-midnight, index day session,
CLOSED segments, malformed input, network failure, cache hit/miss/expiry,
empty details, conId=0 path.
"""

import asyncio
import time
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.services import trading_hours
from app.services.trading_hours import _is_in_window, is_contract_open


ET = ZoneInfo("US/Eastern")
CT = ZoneInfo("US/Central")


# Real strings sampled from IBKR's reqContractDetails 2026-05-14
AAPL_TH = (
    "20260514:0400-20260514:2000;"
    "20260515:0400-20260515:2000;"
    "20260516:CLOSED;"
    "20260517:CLOSED;"
    "20260518:0400-20260518:2000"
)
SPX_TH = (  # SPX day session only, Chicago time
    "20260514:0830-20260514:1500;"
    "20260515:0830-20260515:1500;"
    "20260516:CLOSED;"
    "20260517:CLOSED;"
    "20260518:0830-20260518:1500"
)
EURUSD_TH = (  # forex, cross-midnight 17:15-17:00; weekend closed Fri 17:00 → Sun 17:15
    "20260513:1715-20260514:1700;"  # Wed 17:15 → Thu 17:00
    "20260514:1715-20260515:1700;"  # Thu 17:15 → Fri 17:00 (last session of week)
    "20260515:CLOSED;"               # Fri after-close + weekend
    "20260516:CLOSED;"               # Sat
    "20260517:1715-20260518:1700"    # Sun 17:15 → Mon 17:00 (week resumes)
)


# ============================================================================
# _is_in_window — pure parser tests
# ============================================================================

class TestStockBoundaries:
  """US equity: 04:00-20:00 ET on session days."""

  def test_thu_0359_et_just_before_premarket(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 3, 59, tzinfo=ET)) is False

  def test_thu_0400_et_premarket_open(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 4, 0, tzinfo=ET)) is True

  def test_thu_0930_et_rth_open(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 9, 30, tzinfo=ET)) is True

  def test_thu_1600_et_ah_start(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 16, 0, tzinfo=ET)) is True

  def test_thu_1959_et_ah_last_min(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 19, 59, tzinfo=ET)) is True

  def test_thu_2000_et_ah_closed(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 20, 0, tzinfo=ET)) is False

  def test_sat_closed(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 16, 12, 0, tzinfo=ET)) is False

  def test_sun_closed(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 17, 12, 0, tzinfo=ET)) is False

  def test_mon_premarket(self):
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 18, 5, 0, tzinfo=ET)) is True


class TestForexCrossMidnight:
  """CASH/forex: cross-midnight sessions 17:15(d)-17:00(d+1)."""

  def test_wed_1714_et_just_before_session(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 13, 17, 14, tzinfo=ET)) is False

  def test_wed_1715_et_session_start(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 13, 17, 15, tzinfo=ET)) is True

  def test_thu_0200_et_via_cross_midnight(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 14, 2, 0, tzinfo=ET)) is True

  def test_fri_1700_et_weekend_close(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 15, 17, 0, tzinfo=ET)) is False

  def test_sat_1200_et_closed(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 16, 12, 0, tzinfo=ET)) is False

  def test_sun_1714_et_before_resume(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 17, 17, 14, tzinfo=ET)) is False

  def test_sun_1715_et_resume(self):
    assert _is_in_window(EURUSD_TH, "US/Eastern", datetime(2026, 5, 17, 17, 15, tzinfo=ET)) is True


class TestIndexDaySession:
  """IND/SPX: 08:30-15:00 CT (= 09:30-16:00 ET)."""

  def test_thu_0628_et_index_closed(self):
    # 06:28 ET = 05:28 CT, before SPX day session
    assert _is_in_window(SPX_TH, "US/Central", datetime(2026, 5, 14, 5, 28, tzinfo=CT)) is False

  def test_thu_0830_ct_day_session_open(self):
    assert _is_in_window(SPX_TH, "US/Central", datetime(2026, 5, 14, 8, 30, tzinfo=CT)) is True

  def test_thu_1500_ct_day_session_close(self):
    assert _is_in_window(SPX_TH, "US/Central", datetime(2026, 5, 14, 15, 0, tzinfo=CT)) is False


class TestMalformedInput:
  """Fail-safe: every malformed input returns False, never raises."""

  def test_empty_string(self):
    assert _is_in_window("", "US/Eastern") is False

  def test_none_safe(self):
    assert _is_in_window(None, "US/Eastern") is False  # type: ignore[arg-type]

  def test_unknown_timezone(self):
    assert _is_in_window(AAPL_TH, "Mars/Olympus_Mons") is False

  def test_unparseable_segment_skipped_other_kept(self):
    th = (
      "GARBAGE;"
      "20260514:0400-20260514:2000;"
      "AAA-BBB"
    )
    assert _is_in_window(th, "US/Eastern", datetime(2026, 5, 14, 10, 0, tzinfo=ET)) is True

  def test_all_closed_segments(self):
    th = "20260516:CLOSED;20260517:CLOSED"
    assert _is_in_window(th, "US/Eastern", datetime(2026, 5, 16, 12, 0, tzinfo=ET)) is False

  def test_now_naive_assumes_contract_tz(self):
    # naive datetime should be treated as already-in-tz
    assert _is_in_window(AAPL_TH, "US/Eastern", datetime(2026, 5, 14, 10, 0)) is True

  def test_now_other_tz_converted(self):
    # 10:00 UTC = 06:00 ET → still in premarket window
    utc_now = datetime(2026, 5, 14, 10, 0, tzinfo=ZoneInfo("UTC"))
    assert _is_in_window(AAPL_TH, "US/Eastern", utc_now) is True


# ============================================================================
# is_contract_open — IB-fronted tests with mock IB
# ============================================================================

class FakeIB:
  """Minimal IB stub. reqContractDetailsAsync coroutine returns whatever
  call_returns yields, and increments call_count."""

  def __init__(self, returns=None, raises=None):
    self._returns = returns
    self._raises = raises
    self.call_count = 0

  async def reqContractDetailsAsync(self, contract):
    self.call_count += 1
    if self._raises is not None:
      raise self._raises
    return self._returns


def _details(trading_hours_str: str, tz: str = "US/Eastern", conid: int = 0):
  """Build a ContractDetails-like SimpleNamespace."""
  return SimpleNamespace(
    contract=SimpleNamespace(conId=conid),
    tradingHours=trading_hours_str,
    timeZoneId=tz,
  )


@pytest.fixture(autouse=True)
def clear_cache():
  """Each test starts with an empty cache."""
  trading_hours._CACHE.clear()
  yield
  trading_hours._CACHE.clear()


class TestIsContractOpen:

  def test_cache_miss_fetches_then_hits(self):
    ib = FakeIB(returns=[_details(AAPL_TH, "US/Eastern", conid=12345)])
    contract = SimpleNamespace(conId=12345)
    # First call → network fetch
    asyncio.run(is_contract_open(ib, contract))
    assert ib.call_count == 1
    # Second call → cache hit, no extra fetch
    asyncio.run(is_contract_open(ib, contract))
    assert ib.call_count == 1

  def test_cache_expiry_refetches(self):
    ib = FakeIB(returns=[_details(AAPL_TH, "US/Eastern", conid=99)])
    contract = SimpleNamespace(conId=99)
    asyncio.run(is_contract_open(ib, contract))
    assert ib.call_count == 1
    # Force expiry by rewriting fetched_at to 7h ago
    th, tz, _ = trading_hours._CACHE[99]
    trading_hours._CACHE[99] = (th, tz, time.time() - 7 * 3600)
    asyncio.run(is_contract_open(ib, contract))
    assert ib.call_count == 2

  def test_network_failure_returns_false(self):
    ib = FakeIB(raises=asyncio.TimeoutError())
    contract = SimpleNamespace(conId=77)
    assert asyncio.run(is_contract_open(ib, contract)) is False

  def test_generic_exception_returns_false(self):
    ib = FakeIB(raises=RuntimeError("ib gateway dead"))
    contract = SimpleNamespace(conId=78)
    assert asyncio.run(is_contract_open(ib, contract)) is False

  def test_empty_details_returns_false(self):
    ib = FakeIB(returns=[])
    contract = SimpleNamespace(conId=79)
    assert asyncio.run(is_contract_open(ib, contract)) is False

  def test_empty_trading_hours_returns_false(self):
    ib = FakeIB(returns=[_details("", "US/Eastern", conid=80)])
    contract = SimpleNamespace(conId=80)
    assert asyncio.run(is_contract_open(ib, contract)) is False

  def test_conid_zero_bypasses_cache(self):
    """conId=0 (unqualified) should always re-fetch — no cache key."""
    ib = FakeIB(returns=[_details(AAPL_TH, "US/Eastern", conid=0)])
    contract = SimpleNamespace(conId=0)
    asyncio.run(is_contract_open(ib, contract))
    asyncio.run(is_contract_open(ib, contract))
    assert ib.call_count == 2
