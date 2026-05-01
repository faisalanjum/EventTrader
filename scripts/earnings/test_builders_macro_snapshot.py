"""Mocked unit tests for scripts.earnings.builders.macro_snapshot."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile
import pytest

from scripts.earnings.builders import macro_snapshot as ms

pytestmark = pytest.mark.builders


def _sample_daily_bars():
    return [
        {"date": "2026-04-29", "open": 98.0, "high": 101.0, "low": 97.0,
         "close": 100.0, "volume": 1_000_000},
        {"date": "2026-04-30", "open": 100.0, "high": 102.0, "low": 99.0,
         "close": 101.0, "volume": 1_000_000},
        {"date": "2026-05-01", "open": 101.0, "high": 112.0, "low": 100.0,
         "close": 110.0, "volume": 1_000_000},
    ]


def _sample_minute_bars():
    return [
        {"ts_ms": 1777629600000, "ts_iso": "2026-05-01T14:00:00Z",
         "open": 101.0, "high": 102.0, "low": 100.5, "close": 102.0, "volume": 100_000},
        {"ts_ms": 1777631400000, "ts_iso": "2026-05-01T14:30:00Z",
         "open": 102.0, "high": 103.0, "low": 101.5, "close": 103.0, "volume": 100_000},
    ]


def _build_yahoo_packet_for_session(market_session: str, pit_cutoff: str) -> dict:
    fake_yf_ticker = MagicMock()
    fake_yf_ticker.fast_info.last_price = 20.0
    fake_yf_ticker.history.return_value = MagicMock(empty=True)

    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.side_effect = [
        [{"sector": "Technology", "sector_etf": "XLK"}],
        [
            {"date": "2026-04-29", "ret": 0.2},
            {"date": "2026-04-30", "ret": 0.4},
            {"date": "2026-05-01", "ret": 9.9},
        ],
    ]

    with patch.object(ms, "_yahoo_daily", return_value=_sample_daily_bars()), \
         patch.object(ms, "_yahoo_minute", return_value=_sample_minute_bars()), \
         patch.object(ms, "get_manager", return_value=mock_manager), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout='{"data": []}', stderr="")), \
         patch("yfinance.Ticker", return_value=fake_yf_ticker):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            return ms.build_macro_snapshot(
                ticker="CRM",
                pit_cutoff=pit_cutoff,
                market_session=market_session,
                source="yahoo",
                out_path=out,
            )
        finally:
            os.unlink(out)


def test_yahoo_source_uses_yahoo_helpers():
    """Mock _yahoo_daily/_yahoo_minute (return list[dict] of bars, not scalars)
    AND yfinance.Ticker (used directly inside _compute_spy_now around line 445)
    AND subprocess.run (the pit_fetch invocation for Benzinga headlines).

    Verified at scripts/earnings/macro_snapshot.py:115 — `def _yahoo_daily(...) -> list[dict]:`
    with bar shape {date, open, high, low, close, volume}; line 141 — `_yahoo_minute(...) -> list[dict]:`
    with shape {ts_ms, ts_iso, open, high, low, close, volume}.
    """
    daily_bars = [
        {"date": "2024-09-13", "open": 99.0, "high": 100.5, "low": 98.5,
         "close": 100.0, "volume": 1_000_000},
    ]
    minute_bars = [
        {"ts_ms": 1726425600000, "ts_iso": "2024-09-15T16:00:00Z",
         "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.5, "volume": 100_000},
    ]
    fake_yf_ticker = MagicMock()
    fake_yf_ticker.info = {"regularMarketPrice": 5500.0}
    fake_yf_ticker.history.return_value = MagicMock(empty=True)  # safe default
    # macro_snapshot.py:448 calls `yf.Ticker('^VIX').fast_info.last_price` in
    # live mode. Without an explicit float here, MagicMock's auto-attribute
    # returns ANOTHER MagicMock; `float(MagicMock())` raises TypeError; the
    # bare `except Exception` at line 463 swallows it; vix_level stays None and
    # a `missing_vix` gap is appended. The test "passes" but never exercises
    # the VIX-success branch. Setting an explicit float makes the path real.
    fake_yf_ticker.fast_info.last_price = 20.0
    # Configure the manager mock explicitly: macro_snapshot.py calls
    # manager.execute_cypher_query_all(...) for sector lookup. A bare
    # `MagicMock()` would let that call return a MagicMock object that
    # could end up in packet fields and silently break json.dump.
    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = []
    with patch.object(ms, "_yahoo_daily", return_value=daily_bars) as yd, \
         patch.object(ms, "_yahoo_minute", return_value=minute_bars) as ym, \
         patch.object(ms, "get_manager", return_value=mock_manager), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout='{"data": []}', stderr="")), \
         patch("yfinance.Ticker", return_value=fake_yf_ticker):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            packet = ms.build_macro_snapshot(
                ticker="CRM",
                pit_cutoff="2024-09-15T16:00:00+00:00",
                market_session="post_market",
                source="yahoo",
                out_path=out,
            )
            assert packet["schema_version"].startswith("macro_snapshot.v")
            assert os.path.exists(out)
            assert yd.called or ym.called
        finally:
            os.unlink(out)


@pytest.mark.parametrize("market_session,pit_cutoff", [
    ("pre_market", "2026-05-01T06:52:00-04:00"),
    ("in_market", "2026-05-01T10:31:00-04:00"),
])
def test_yahoo_pre_and_in_market_do_not_treat_current_daily_bar_as_settled(market_session, pit_cutoff):
    packet = _build_yahoo_packet_for_session(market_session, pit_cutoff)

    spy = packet["market_now"]["spy"]
    assert packet["market_session"] == market_session
    assert spy["today_return"] is None
    assert spy["yesterday"] == 1.0

    indicator = packet["market_now"]["indicators"]["Volatility (VIXY)"]
    assert indicator["return_label"] == "last close"
    assert indicator["last_return"] == 1.0

    sector = packet["market_now"]["sector"]
    assert sector["return_label"] == "last close"
    assert sector["last_return"] == 0.4


def test_yahoo_post_market_still_treats_current_daily_bar_as_settled():
    packet = _build_yahoo_packet_for_session(
        "post_market",
        "2026-05-01T16:30:00-04:00",
    )

    spy = packet["market_now"]["spy"]
    assert packet["market_session"] == "post_market"
    assert spy["today_return"] == 8.91
    assert spy["yesterday"] == 1.0

    indicator = packet["market_now"]["indicators"]["Volatility (VIXY)"]
    assert indicator["return_label"] == "today"
    assert indicator["last_return"] == 8.91

    sector = packet["market_now"]["sector"]
    assert sector["return_label"] == "today"
    assert sector["last_return"] == 9.9


def test_render_text_accepts_packet():
    packet = {
        "schema_version": "macro_snapshot.v2",
        "ticker": "CRM",
        "pit_cutoff": "2024-09-15T16:00:00+00:00",
        "spy": {"close": 5500.0},
        "indicators": {},
        "headlines": [],
    }
    text = ms.render_text(packet)
    assert isinstance(text, str)


def test_pit_fetch_resolves_correctly():
    """Verify PIT_FETCH path is computed via _paths.skill_script and exists."""
    assert os.path.exists(ms.PIT_FETCH)
    assert ms.PIT_FETCH.endswith("pit_fetch.py")
