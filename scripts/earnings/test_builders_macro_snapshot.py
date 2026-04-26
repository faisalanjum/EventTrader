"""Mocked unit tests for scripts.earnings.builders.macro_snapshot."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile
import pytest

from scripts.earnings.builders import macro_snapshot as ms

pytestmark = pytest.mark.builders


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
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="[]", stderr="")), \
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
