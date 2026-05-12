"""Unit tests for PriceSnapshot is_realtime + market_data_type fields.

Contract:
  is_realtime = (ticker.marketDataType == 1)   # IB's live classification
  market_data_type = ticker.marketDataType     # 1=Live 2=Frozen 3=Delayed 4=DelayedFrozen

Both fields are REQUIRED on PriceSnapshot — Pydantic fails loud if missing.
"""

import pytest
from pydantic import ValidationError

from app.models.history import PriceSnapshot


def test_required_is_realtime_field():
  """is_realtime is required — missing it raises ValidationError."""
  with pytest.raises(ValidationError):
    PriceSnapshot(
      symbol="X", sec_type="STK", timestamp="t",
      market_data_type=1,  # provided but is_realtime missing
    )


def test_required_market_data_type_field():
  """market_data_type is required — missing it raises ValidationError."""
  with pytest.raises(ValidationError):
    PriceSnapshot(
      symbol="X", sec_type="STK", timestamp="t",
      is_realtime=True,  # provided but market_data_type missing
    )


def test_live_real_time_snapshot():
  """Subscribed stock during RTH: type=1, bid/ask populated, is_realtime=True."""
  p = PriceSnapshot(
    symbol="AAPL", sec_type="STK", timestamp="2026-05-12T12:00:00Z",
    last=293.92, bid=293.90, ask=293.93, close=292.68,
    is_realtime=True, market_data_type=1,
  )
  assert p.is_realtime is True
  assert p.market_data_type == 1


def test_index_snapshot_no_live_feed():
  """Index without CBOE sub: type=2 (frozen) or 3, is_realtime=False."""
  p = PriceSnapshot(
    symbol="SPX", sec_type="IND", timestamp="2026-05-12T12:00:00Z",
    last=7342.18, bid=None, ask=None, close=7342.18,
    is_realtime=False, market_data_type=2,
  )
  assert p.is_realtime is False
  assert p.market_data_type == 2


def test_paper_account_delayed():
  """Paper account without live sub: type=3 delayed, is_realtime=False."""
  p = PriceSnapshot(
    symbol="AAPL", sec_type="STK", timestamp="2026-05-12T12:00:00Z",
    last=294.09, bid=None, ask=None, close=294.09,
    is_realtime=False, market_data_type=3,
  )
  assert p.is_realtime is False
  assert p.market_data_type == 3


def test_historical_fallback_path():
  """Historical-bar fallback: is_realtime=False, market_data_type=2 (frozen)."""
  p = PriceSnapshot(
    symbol="^SPX", sec_type="IND", timestamp="2026-05-12T22:00:00Z",
    last=7342.18, bid=None, ask=None, close=7342.18,
    is_realtime=False, market_data_type=2,
  )
  assert p.is_realtime is False
  assert p.market_data_type == 2


def test_serialization_includes_new_fields():
  """JSON output MUST include both new fields."""
  p = PriceSnapshot(
    symbol="X", sec_type="STK", timestamp="t",
    is_realtime=True, market_data_type=1,
  )
  data = p.model_dump()
  assert "is_realtime" in data
  assert "market_data_type" in data
  assert data["is_realtime"] is True
  assert data["market_data_type"] == 1
