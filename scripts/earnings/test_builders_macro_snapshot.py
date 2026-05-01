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


# ─── U34/U35 tests ────────────────────────────────────────────────────


def _build_packet(*, market_session, pit_cutoff, source="yahoo", live_mode=None):
    """Same mock topology as _build_yahoo_packet_for_session, but exposes
    `source` and `live_mode` for the U34 matrix."""
    fake_yf_ticker = MagicMock()
    fake_yf_ticker.fast_info.last_price = 17.5  # live VIX value
    # Historical VIX path: yfinance.history returns a non-empty frame so
    # vix_level resolves via the settled-close branch.
    import pandas as pd
    hist_df = pd.DataFrame(
        {"Close": [16.2, 16.4]},
        index=pd.to_datetime(["2026-04-29", "2026-04-30"]),
    )
    fake_yf_ticker.history.return_value = hist_df

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
         patch.object(ms, "_polygon_daily", return_value=_sample_daily_bars()), \
         patch.object(ms, "_polygon_minute", return_value=_sample_minute_bars()), \
         patch.object(ms, "_load_polygon_key", return_value="fake-key"), \
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
                source=source,
                live_mode=live_mode,
                out_path=out,
            )
        finally:
            os.unlink(out)


# U34 — explicit live_mode matrix


def test_vix_label_live_when_live_mode_true_yahoo():
    pkt = _build_packet(market_session="post_market",
                        pit_cutoff="2026-05-01T16:30:00-04:00",
                        source="yahoo", live_mode=True)
    assert pkt["market_now"]["vix_label"] == "live"
    assert pkt["market_now"]["vix_close"] == 17.5  # live VIX value


def test_vix_label_settled_when_live_mode_false_yahoo_override():
    """U34 release-blocker: yahoo + historical pit + live_mode=False → settled VIX."""
    pkt = _build_packet(market_session="post_market",
                        pit_cutoff="2024-09-15T16:00:00-04:00",
                        source="yahoo", live_mode=False)
    assert pkt["market_now"]["vix_label"] == "last settled close"
    # Should NOT be 17.5 (live); should come from yfinance.history mock
    assert pkt["market_now"]["vix_close"] != 17.5


def test_vix_label_settled_when_live_mode_false_polygon():
    """Regression — historical polygon path must remain on settled VIX."""
    pkt = _build_packet(market_session="post_market",
                        pit_cutoff="2024-09-15T16:00:00-04:00",
                        source="polygon", live_mode=False)
    assert pkt["market_now"]["vix_label"] == "last settled close"


# U34 — backward-compat inference (live_mode=None)


def test_vix_label_infers_live_mode_for_legacy_yahoo_without_session():
    """Legacy direct-caller pattern: yahoo + no market_session + live_mode=None
    → infer live → live VIX. Preserves test_builder_validation.py:712."""
    pkt = _build_packet(market_session=None,
                        pit_cutoff="2026-05-01T16:30:00-04:00",
                        source="yahoo", live_mode=None)
    assert pkt["market_now"]["vix_label"] == "live"


def test_vix_label_infers_historical_for_legacy_yahoo_with_explicit_session():
    """Defensive: yahoo + explicit session + live_mode=None → infer historical
    → settled VIX. caller_supplied_session=True triggers the fallback."""
    pkt = _build_packet(market_session="post_market",
                        pit_cutoff="2024-09-15T16:00:00-04:00",
                        source="yahoo", live_mode=None)
    assert pkt["market_now"]["vix_label"] == "last settled close"


def test_vix_label_explicit_live_mode_false_overrides_inference():
    """Explicit caller value always wins over inference."""
    # source=yahoo, no session — would normally infer live=True
    # but live_mode=False explicitly should force historical branch
    pkt = _build_packet(market_session=None,
                        pit_cutoff="2024-09-15T16:00:00-04:00",
                        source="yahoo", live_mode=False)
    assert pkt["market_now"]["vix_label"] == "last settled close"


# U35 — last_settled_date


def test_last_settled_date_yesterday_for_pre_market():
    """pre_market PIT → settled_daily excludes today → last_settled_date = yesterday."""
    pkt = _build_packet(market_session="pre_market",
                        pit_cutoff="2026-05-01T06:52:00-04:00",
                        source="polygon", live_mode=False)
    assert pkt["market_now"]["spy"]["last_settled_date"] == "2026-04-30"


def test_last_settled_date_yesterday_for_in_market():
    """in_market PIT → settled_daily excludes today → last_settled_date = yesterday."""
    pkt = _build_packet(market_session="in_market",
                        pit_cutoff="2026-05-01T10:31:00-04:00",
                        source="polygon", live_mode=False)
    assert pkt["market_now"]["spy"]["last_settled_date"] == "2026-04-30"


def test_last_settled_date_today_for_post_market():
    """post_market PIT → settled_daily includes today → last_settled_date = today."""
    pkt = _build_packet(market_session="post_market",
                        pit_cutoff="2026-05-01T16:30:00-04:00",
                        source="polygon", live_mode=False)
    assert pkt["market_now"]["spy"]["last_settled_date"] == "2026-05-01"


def test_last_settled_date_none_when_no_daily_bars():
    """No daily bars → last_settled_date is None (defensive)."""
    fake_yf_ticker = MagicMock()
    fake_yf_ticker.fast_info.last_price = 17.5
    fake_yf_ticker.history.return_value = MagicMock(empty=True)

    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = []

    with patch.object(ms, "_yahoo_daily", return_value=[]), \
         patch.object(ms, "_yahoo_minute", return_value=[]), \
         patch.object(ms, "_polygon_daily", return_value=[]), \
         patch.object(ms, "_polygon_minute", return_value=[]), \
         patch.object(ms, "_load_polygon_key", return_value="fake-key"), \
         patch.object(ms, "get_manager", return_value=mock_manager), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout='{"data": []}', stderr="")), \
         patch("yfinance.Ticker", return_value=fake_yf_ticker):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            pkt = ms.build_macro_snapshot(
                ticker="CRM",
                pit_cutoff="2026-05-01T16:30:00-04:00",
                market_session="post_market",
                source="polygon", live_mode=False,
                out_path=out,
            )
            assert pkt["market_now"]["spy"]["last_settled_date"] is None
        finally:
            os.unlink(out)


# CLI live_mode propagation — invoked via subprocess


def test_cli_pit_now_routes_to_live_mode_true():
    """CLI `--pit now` must propagate live_mode=True to builder."""
    import subprocess
    import sys as _sys
    captured = {}

    # We capture by patching the canonical builder. The CLI calls into the
    # same module-level function we can monkey-patch.
    real_build = ms.build_macro_snapshot

    def spy_build(ticker, pit_cutoff, market_session=None, out_path=None,
                  source='polygon', live_mode=None, **kw):
        captured["live_mode"] = live_mode
        captured["source"] = source
        return {"schema_version": "macro_snapshot.v2", "ticker": ticker,
                "market_now": {}, "catalysts": {}, "gaps": []}

    with patch.object(ms, "build_macro_snapshot", side_effect=spy_build), \
         patch.object(_sys, "argv", ["macro_snapshot.py", "AAPL", "--pit", "now",
                                     "--source", "yahoo", "--out-path", "/tmp/x.json"]):
        try:
            ms.main()
        except SystemExit:
            pass

    assert captured.get("live_mode") is True
    assert captured.get("source") == "yahoo"


def test_cli_explicit_pit_routes_to_live_mode_false():
    """CLI `--pit <ISO>` must propagate live_mode=False (defensive case)."""
    import sys as _sys
    captured = {}

    def spy_build(ticker, pit_cutoff, market_session=None, out_path=None,
                  source='polygon', live_mode=None, **kw):
        captured["live_mode"] = live_mode
        return {"schema_version": "macro_snapshot.v2", "ticker": ticker,
                "market_now": {}, "catalysts": {}, "gaps": []}

    with patch.object(ms, "build_macro_snapshot", side_effect=spy_build), \
         patch.object(_sys, "argv", ["macro_snapshot.py", "AAPL", "--pit",
                                     "2024-09-15T16:00:00-04:00",
                                     "--source", "yahoo",
                                     "--out-path", "/tmp/x.json"]):
        try:
            ms.main()
        except SystemExit:
            pass

    assert captured.get("live_mode") is False
