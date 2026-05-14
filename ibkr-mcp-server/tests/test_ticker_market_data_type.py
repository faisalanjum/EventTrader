"""Unit tests for TickerData.marketDataType field (added 2026-05-14).

Mirror contract from Phase 1's PriceSnapshot.market_data_type:
  None / 1 / 2 / 3 / 4 — and propagates through _process_tickers DataFrame path.
"""

import pandas as pd
import pytest
from types import SimpleNamespace

from app.models import TickerData
from app.services.market_data import MarketDataClient


def test_market_data_type_field_optional_default_none():
  """Field is optional; defaults to None when not provided."""
  t = TickerData(contractId=1, symbol="X", secType="STK")
  assert t.marketDataType is None


@pytest.mark.parametrize("mdt", [1, 2, 3, 4])
def test_market_data_type_accepts_all_ib_classifications(mdt):
  """All 4 IB classifications accepted."""
  t = TickerData(contractId=1, symbol="X", secType="STK", marketDataType=mdt)
  assert t.marketDataType == mdt


def test_market_data_type_in_model_dump():
  """Field round-trips through model_dump (matters because get_and_filter_options
  serializes via model_dump → DataFrame → reconstruct)."""
  t = TickerData(contractId=1, symbol="X", secType="OPT", marketDataType=2)
  d = t.model_dump()
  assert d["marketDataType"] == 2


def test_process_tickers_propagates_market_data_type():
  """_process_tickers extracts ticker.marketDataType and sets it on TickerData."""
  fake_contract = SimpleNamespace(conId=123, localSymbol="AAPL", secType="STK")
  fake_ticker = {
    "contract": fake_contract,
    "last": 300.0,
    "bid": 299.9,
    "ask": 300.1,
    "marketDataType": 1,
    "modelGreeks": None,
  }
  client = MarketDataClient.__new__(MarketDataClient)  # skip __init__ (needs IB)
  result = client._process_tickers([fake_ticker])
  assert len(result) == 1
  assert result[0].marketDataType == 1
  assert result[0].last == 300.0


def test_process_tickers_handles_missing_market_data_type_column():
  """If IB never set marketDataType (older util.df shape), default to None."""
  fake_contract = SimpleNamespace(conId=124, localSymbol="JPM", secType="STK")
  fake_ticker = {
    "contract": fake_contract,
    "last": 301.0,
    "bid": 300.9,
    "ask": 301.1,
    # marketDataType key omitted entirely
    "modelGreeks": None,
  }
  client = MarketDataClient.__new__(MarketDataClient)
  result = client._process_tickers([fake_ticker])
  assert result[0].marketDataType is None


def test_process_tickers_nan_market_data_type_becomes_none():
  """A NaN value (rare but possible from pandas coercion) becomes None."""
  fake_contract = SimpleNamespace(conId=125, localSymbol="WMT", secType="STK")
  fake_ticker = {
    "contract": fake_contract,
    "last": 131.0,
    "bid": 130.9,
    "ask": 131.1,
    "marketDataType": float("nan"),
    "modelGreeks": None,
  }
  client = MarketDataClient.__new__(MarketDataClient)
  result = client._process_tickers([fake_ticker])
  assert result[0].marketDataType is None
