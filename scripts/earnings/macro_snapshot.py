#!/usr/bin/env python3
"""Macro Context — PIT-safe market state at the moment of earnings.

Three sections:
  1. MARKET NOW — SPY intraday state at PIT (minute bars) + indicator levels
  2. IMMEDIATE CATALYSTS — today/yesterday/earlier headlines
  3. REGIME — 5d/20d/YTD background

Session-aware:
  post_market  → today's session settled, show full day + last 60m
  in_market    → session in progress, show open-to-PIT + last 60m from minute bars
  pre_market   → session not started, yesterday is "last session"

Usage:
    # PIT-safe historical (Polygon — default):
    python3 scripts/earnings/macro_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00 --session post_market

    # Live real-time (Yahoo Finance):
    python3 scripts/earnings/macro_snapshot.py SPY --pit now
    python3 scripts/earnings/macro_snapshot.py AAPL --pit now --source yahoo

    # Manual CLI: --session omitted, auto-inferred from PIT timestamp (fallback only)
    python3 scripts/earnings/macro_snapshot.py NOG --pit 2024-11-07T13:01:00-05:00

Note:
    --session should always be passed by the orchestrator using the stored r.market_session
    from the 8-K Report node in Neo4j. Clock-time inference is only for manual/CLI convenience.
    The script behavior changes materially by session (which bars are PIT-safe, which are not).

    --source yahoo provides real-time data via yfinance. Minute bars are limited to ~7 days
    of history. For historical PIT analysis, use --source polygon (default).

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    POLYGON_API_KEY (polygon source only)
    BENZINGA_API_KEY (via pit_fetch.py)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, date as date_cls, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from neograph.Neo4jConnection import get_manager
except ImportError:
    sys.exit('macro_snapshot requires the project venv — run: source venv/bin/activate')

PIT_FETCH = str(Path(__file__).resolve().parents[2] / '.claude' / 'skills' / 'earnings-orchestrator' / 'scripts' / 'pit_fetch.py')

# ── Polygon helpers ──────────────────────────────────────────────────

def _load_polygon_key() -> str:
    env_path = Path(__file__).resolve().parents[2] / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith('POLYGON_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('POLYGON_API_KEY', '')


def _polygon_request(url: str, api_key: str) -> dict:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
    full_url = f"{url}&apiKey={api_key}" if '?' in url else f"{url}?apiKey={api_key}"
    try:
        with urlopen(Request(full_url), timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f'Polygon error: {url[:80]}... → {e}', file=sys.stderr)
        return {}
    except Exception as e:
        print(f'Polygon error: {url[:80]}... → {e}', file=sys.stderr)
        return {}


def _polygon_daily(ticker: str, from_date: str, to_date: str, api_key: str) -> list[dict]:
    """Fetch daily bars from Polygon."""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}?adjusted=true&sort=asc&limit=250"
    data = _polygon_request(url, api_key)
    bars = []
    for r in data.get('results', []):
        ts = r.get('t', 0) / 1000
        bars.append({
            'date': datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d'),
            'open': r.get('o'), 'high': r.get('h'), 'low': r.get('l'),
            'close': r.get('c'), 'volume': r.get('v'),
        })
    return bars


def _polygon_minute(ticker: str, date_str: str, api_key: str) -> list[dict]:
    """Fetch minute bars for a single day from Polygon."""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date_str}/{date_str}?adjusted=true&sort=asc&limit=1000"
    data = _polygon_request(url, api_key)
    bars = []
    for r in data.get('results', []):
        ts_ms = r.get('t', 0)
        bars.append({
            'ts_ms': ts_ms,
            'ts_iso': datetime.utcfromtimestamp(ts_ms / 1000).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'open': r.get('o'), 'high': r.get('h'), 'low': r.get('l'),
            'close': r.get('c'), 'volume': r.get('v'),
        })
    return bars


# ── Yahoo Finance helpers ────────────────────────────────────────────

def _yahoo_daily(ticker: str, from_date: str, to_date: str) -> list[dict]:
    """Fetch daily bars from Yahoo Finance (yfinance).
    Returns same format as _polygon_daily for drop-in compatibility."""
    import yfinance as yf
    try:
        # yfinance end is EXCLUSIVE — add 1 day to include to_date
        end_dt = date_cls.fromisoformat(to_date) + timedelta(days=1)
        df = yf.Ticker(ticker).history(start=from_date, end=end_dt.isoformat(),
                                        auto_adjust=True)
        if df is None or df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            dt = idx.tz_localize(None) if hasattr(idx, 'tz_localize') and idx.tzinfo else idx
            bars.append({
                'date': dt.strftime('%Y-%m-%d'),
                'open': float(row['Open']), 'high': float(row['High']),
                'low': float(row['Low']), 'close': float(row['Close']),
                'volume': int(row['Volume']),
            })
        return bars
    except Exception as e:
        print(f'Yahoo daily error ({ticker}): {e}', file=sys.stderr)
        return []


def _yahoo_minute(ticker: str, date_str: str) -> list[dict]:
    """Fetch minute bars for a single day from Yahoo Finance.
    Returns same format as _polygon_minute for drop-in compatibility.
    Note: yfinance only provides ~7 days of 1-minute history."""
    import yfinance as yf
    try:
        end_dt = date_cls.fromisoformat(date_str) + timedelta(days=1)
        df = yf.Ticker(ticker).history(start=date_str, end=end_dt.isoformat(),
                                        interval='1m')
        if df is None or df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            # .timestamp() converts timezone-aware datetime to UTC epoch
            ts_ms = int(idx.timestamp() * 1000)
            bars.append({
                'ts_ms': ts_ms,
                'ts_iso': idx.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'open': float(row['Open']), 'high': float(row['High']),
                'low': float(row['Low']), 'close': float(row['Close']),
                'volume': int(row['Volume']),
            })
        return bars
    except Exception as e:
        print(f'Yahoo minute error ({ticker}): {e}', file=sys.stderr)
        return []


def _pct(a: float | None, b: float | None) -> float | None:
    """Percent change from a to b."""
    if a is None or b is None or a == 0:
        return None
    return round(((b - a) / a) * 100, 2)


# ── SPY intraday state ───────────────────────────────────────────────

def _compute_spy_now(minute_bars: list[dict], daily_bars: list[dict],
                     pit_cutoff: str, market_session: str) -> dict:
    """Compute SPY state at PIT from minute + daily bars."""

    # Parse PIT as UTC ms for comparison with Polygon timestamps
    try:
        pit_dt = datetime.fromisoformat(pit_cutoff.replace('Z', '+00:00'))
        pit_ms = int(pit_dt.timestamp() * 1000)
    except ValueError:
        pit_ms = None

    pit_date = pit_cutoff[:10]

    # Daily bars for regime. PIT-SAFE: for in_market/pre_market, exclude today's
    # daily bar (it includes post-PIT trading). Only post_market can use today's bar.
    all_daily = [b for b in daily_bars if b['date'] <= pit_date]
    if market_session != 'post_market':
        # Exclude today — not settled at PIT time
        settled_daily = [b for b in all_daily if b['date'] < pit_date]
    else:
        settled_daily = all_daily

    today_return = None   # close-to-close for today (post_market only)
    yesterday_return = None  # close-to-close for the day before
    change_5d = None
    change_20d = None
    change_ytd = None
    vol_5d = None
    vol_20d = None

    if market_session == 'post_market':
        # settled_daily includes today's bar
        if len(settled_daily) >= 2:
            today_return = _pct(settled_daily[-2]['close'], settled_daily[-1]['close'])
        if len(settled_daily) >= 3:
            yesterday_return = _pct(settled_daily[-3]['close'], settled_daily[-2]['close'])
    else:
        # settled_daily excludes today — [-1] IS yesterday
        if len(settled_daily) >= 2:
            yesterday_return = _pct(settled_daily[-2]['close'], settled_daily[-1]['close'])

    if len(settled_daily) >= 6:
        change_5d = _pct(settled_daily[-6]['close'], settled_daily[-1]['close'])
    if len(settled_daily) >= 21:
        change_20d = _pct(settled_daily[-21]['close'], settled_daily[-1]['close'])

    # YTD — also from settled bars only
    pit_year = pit_date[:4]
    ytd_bars = [b for b in settled_daily if b['date'].startswith(pit_year)]
    if ytd_bars and len(ytd_bars) >= 2:
        change_ytd = _pct(ytd_bars[0]['close'], ytd_bars[-1]['close'])

    # Volume — from settled bars only
    vols = [b['volume'] for b in settled_daily if b['volume']]
    if len(vols) >= 5:
        vol_5d = round(sum(vols[-5:]) / 5)
    if len(vols) >= 20:
        vol_20d = round(sum(vols[-20:]) / 20)

    # Minute bars: level at PIT, open-to-PIT, last 60m
    level_at_pit = None
    open_to_pit = None
    last_60m = None
    today_open = None

    if minute_bars and pit_ms:
        # Filter to bars at or before PIT
        # Only include bars fully settled before PIT (bar start + 60s <= PIT)
        pit_bars = [b for b in minute_bars if b['ts_ms'] + 60_000 <= pit_ms]

        if pit_bars:
            level_at_pit = pit_bars[-1]['close']
            today_open = minute_bars[0]['open'] if minute_bars else None

            if today_open and today_open != 0:
                open_to_pit = _pct(today_open, level_at_pit)

            # Last 60 min
            sixty_min_ago = pit_ms - (60 * 60 * 1000)
            bars_60m_ago = [b for b in pit_bars if b['ts_ms'] + 60_000 <= sixty_min_ago]
            if bars_60m_ago:
                last_60m = _pct(bars_60m_ago[-1]['close'], level_at_pit)

    # For post_market: today's close IS the level (session settled)
    if market_session == 'post_market' and all_daily:
        today_bar = all_daily[-1]
        if today_bar['date'] == pit_date:
            level_at_pit = level_at_pit or today_bar['close']
            if not open_to_pit and today_bar['open']:
                open_to_pit = _pct(today_bar['open'], today_bar['close'])

    # Fallback: if still no level (pre_market with no minute bars), use last settled close
    if level_at_pit is None and settled_daily:
        level_at_pit = settled_daily[-1]['close']

    # Overnight gap: yesterday's close → today's open (captures after-hours + pre-market)
    overnight_gap = None
    if minute_bars and settled_daily:
        today_open = minute_bars[0]['open']
        yest_close = settled_daily[-1]['close'] if market_session != 'post_market' else (settled_daily[-2]['close'] if len(settled_daily) >= 2 else None)
        if today_open and yest_close:
            overnight_gap = _pct(yest_close, today_open)

    # Trend context: SPY vs 50d / 200d moving averages
    ma_50 = None
    ma_200 = None
    closes = [b['close'] for b in settled_daily if b.get('close')]
    if len(closes) >= 50:
        ma_50 = round(sum(closes[-50:]) / 50, 2)
    if len(closes) >= 200:
        ma_200 = round(sum(closes[-200:]) / 200, 2)

    ref_price = level_at_pit or (settled_daily[-1]['close'] if settled_daily else None)
    vs_50d = round(((ref_price - ma_50) / ma_50) * 100, 2) if ref_price and ma_50 else None
    vs_200d = round(((ref_price - ma_200) / ma_200) * 100, 2) if ref_price and ma_200 else None

    return {
        'level_at_pit': round(level_at_pit, 2) if level_at_pit else None,
        'open_to_pit': open_to_pit,
        'last_60m': last_60m,
        'overnight_gap': overnight_gap,
        'today_return': today_return,  # post_market only (session settled)
        'yesterday': yesterday_return,
        'change_5d': change_5d,
        'change_20d': change_20d,
        'change_ytd': change_ytd,
        'ma_50': ma_50,
        'ma_200': ma_200,
        'vs_50d': vs_50d,
        'vs_200d': vs_200d,
        'volume_5d_avg': vol_5d,
        'volume_20d_avg': vol_20d,
        'volume_ratio': round(vol_5d / vol_20d, 2) if vol_5d and vol_20d and vol_20d > 0 else None,
    }


# ── Indicator daily state ─────────────────────────────────────────────

def _compute_indicator_daily(daily_bars: list[dict], pit_date: str,
                             market_session: str = 'post_market') -> dict | None:
    """Compute indicator level + changes from daily bars.
    PIT-safe: for in_market/pre_market, excludes today's unsettled bar."""
    all_valid = [b for b in daily_bars if b['date'] <= pit_date]
    if market_session != 'post_market':
        settled = [b for b in all_valid if b['date'] < pit_date]
    else:
        settled = all_valid

    if not settled:
        return None

    level = settled[-1]['close']
    last_return = _pct(settled[-2]['close'], level) if len(settled) >= 2 else None
    d5 = _pct(settled[-6]['close'], level) if len(settled) >= 6 else None

    pit_year = pit_date[:4]
    ytd_bars = [b for b in settled if b['date'].startswith(pit_year)]
    ytd = _pct(ytd_bars[0]['close'], level) if ytd_bars and len(ytd_bars) >= 2 else None

    # Label: "today" for post_market (settled), "last close" for in/pre_market
    label = 'today' if market_session == 'post_market' else 'last close'

    return {'level': round(level, 2), 'last_return': last_return, 'return_label': label,
            'change_5d': d5, 'change_ytd': ytd}


# ── Main build ───────────────────────────────────────────────────────

INDICATOR_TICKERS = {
    'Volatility (VIXY)': 'VIXY',
    'Rates long (TLT)': 'TLT',
    'Rates short (SHY)': 'SHY',
    'Credit (HYG)': 'HYG',
    'Small Cap (IWM)': 'IWM',
    'Breadth (RSP)': 'RSP',
    'Oil (USO)': 'USO',
    'Dollar (UUP)': 'UUP',
    'Gold (GLD)': 'GLD',
}

# Broader channels for catalysts — catches Fed, economic data, macro events
BZ_CHANNELS = 'Macro Notification,Federal Reserve,Econ #s,Macro Economic Events'


def _infer_market_session(pit_cutoff: str) -> str:
    """Infer market session from PIT timestamp.
    Regular market: 9:30 AM - 4:00 PM ET."""
    try:
        import pytz
        ET = pytz.timezone('US/Eastern')
        pit_dt = datetime.fromisoformat(pit_cutoff.replace('Z', '+00:00'))
        pit_et = pit_dt.astimezone(ET)
        hour, minute = pit_et.hour, pit_et.minute
        market_open = 9 * 60 + 30   # 9:30 AM
        market_close = 16 * 60       # 4:00 PM
        pit_mins = hour * 60 + minute
        if pit_mins < market_open:
            return 'pre_market'
        elif pit_mins >= market_close:
            return 'post_market'
        else:
            return 'in_market'
    except Exception:
        return 'post_market'  # safe default


def build_macro_snapshot(ticker: str, pit_cutoff: str, market_session: str | None = None,
                          out_path: str | None = None, source: str = 'polygon') -> dict:
    if not market_session:
        market_session = _infer_market_session(pit_cutoff)

    pit_date = pit_cutoff[:10]

    try:
        pit_d = date_cls.fromisoformat(pit_date)
    except ValueError:
        pit_d = date_cls.today()

    year_start = f"{pit_d.year}-01-01"
    # 300 days back to cover 200-day MA + YTD
    daily_from = min((pit_d - timedelta(days=300)).isoformat(), year_start)

    use_yahoo = source == 'yahoo'
    api_key = '' if use_yahoo else _load_polygon_key()

    # For live yahoo mode, treat today's partial bar as settled so current
    # prices flow into all computations. Keep real market_session for display.
    effective_session = 'post_market' if use_yahoo else market_session

    # ── 1. SPY minute bars for MARKET NOW ──
    spy_minute = []
    if use_yahoo:
        spy_minute = _yahoo_minute('SPY', pit_date)
    elif api_key:
        spy_minute = _polygon_minute('SPY', pit_date, api_key)
        time.sleep(0.3)  # rate limit courtesy

    # ── 2. SPY daily bars ──
    spy_daily = []
    if use_yahoo:
        spy_daily = _yahoo_daily('SPY', daily_from, pit_date)
    elif api_key:
        spy_daily = _polygon_daily('SPY', daily_from, pit_date, api_key)
        time.sleep(0.3)

    spy_now = _compute_spy_now(spy_minute, spy_daily, pit_cutoff, effective_session)

    # ── 3. Other indicators (daily only) ──
    indicators = {}
    for label, ind_ticker in INDICATOR_TICKERS.items():
        if use_yahoo:
            bars = _yahoo_daily(ind_ticker, daily_from, pit_date)
        elif api_key:
            bars = _polygon_daily(ind_ticker, daily_from, pit_date, api_key)
        else:
            bars = []
        if bars:
            metric = _compute_indicator_daily(bars, pit_date, effective_session)
            if metric:
                indicators[label] = metric
        if not use_yahoo and api_key:
            time.sleep(0.3)

    # ── 3b. VIX level ──
    vix_level = None
    vix_label = 'last settled close'
    try:
        import yfinance as yf
        if use_yahoo:
            # Live mode: current VIX level
            vix_level = round(float(yf.Ticker('^VIX').fast_info.last_price), 2)
            vix_label = 'live'
        else:
            # PIT mode: previous day's settled close only.
            # VIX settles at 4:15 PM ET. Even post_market filings (e.g., 4:03 PM)
            # are before VIX settlement. ALWAYS use the previous day's close.
            vix_start = (pit_d - timedelta(days=7)).isoformat()
            vix_end = pit_d.isoformat()  # exclusive — excludes PIT date entirely
            vix_hist = yf.Ticker('^VIX').history(start=vix_start, end=vix_end)
            if not vix_hist.empty:
                vix_hist.index = vix_hist.index.tz_localize(None) if vix_hist.index.tz else vix_hist.index
                # Strictly before PIT date — previous day's settled close
                valid = vix_hist[vix_hist.index.date < pit_d]
                if not valid.empty:
                    vix_level = round(float(valid['Close'].iloc[-1]), 2)
    except Exception as e:
        print(f'VIX (yfinance) error: {e}', file=sys.stderr)

    # ── 4. Sector from Neo4j + Polygon intraday for sector ETF ──
    sector_info = None
    manager = get_manager()
    try:
        sector_rows = manager.execute_cypher_query_all(
            'MATCH (c:Company {ticker: $ticker}) '
            'RETURN c.sector AS sector, c.sector_etf AS sector_etf',
            {'ticker': ticker}
        )
        sector_name = sector_rows[0]['sector'] if sector_rows else None
        sector_etf = sector_rows[0].get('sector_etf') if sector_rows else None

        if sector_name:
            sec_rows = manager.execute_cypher_query_all('''
                MATCH (d:Date)-[hp:HAS_PRICE]->(s:Sector {name: $sector})
                WHERE d.date >= $from AND d.date <= $pit_date
                RETURN d.date AS date, hp.daily_return AS ret
                ORDER BY d.date
            ''', {'sector': sector_name, 'from': (pit_d - timedelta(days=10)).isoformat(), 'pit_date': pit_date})

            # PIT-safe: for in/pre_market, exclude today's unsettled bar
            # (live yahoo mode uses effective_session=post_market to include today)
            if sec_rows:
                if effective_session != 'post_market':
                    settled_sec = [r for r in sec_rows if r['date'] < pit_date]
                else:
                    settled_sec = sec_rows

                last_sec = round(settled_sec[-1]['ret'], 2) if settled_sec else None
                sec_5d = settled_sec[-5:] if len(settled_sec) >= 5 else settled_sec
                sum_5d = round(sum(r['ret'] for r in sec_5d if r['ret']), 2)
                # Only label "today" if the latest sector row is actually from today
                # (Neo4j sector data may lag behind live Yahoo market data)
                has_today = settled_sec and settled_sec[-1]['date'] == pit_date
                sec_label = 'today' if effective_session == 'post_market' and has_today else 'last close'
                # Sector ETF intraday for in_market (e.g., XLK for Technology)
                sec_open_to_pit = None
                if market_session == 'in_market' and sector_etf and (api_key or use_yahoo):
                    try:
                        _pit_dt = datetime.fromisoformat(pit_cutoff.replace('Z', '+00:00'))
                        _pit_ms = int(_pit_dt.timestamp() * 1000)
                    except ValueError:
                        _pit_ms = None
                    sec_minute = _yahoo_minute(sector_etf, pit_date) if use_yahoo else _polygon_minute(sector_etf, pit_date, api_key)
                    if sec_minute and _pit_ms:
                        sec_pit_bars = [b for b in sec_minute if b['ts_ms'] + 60_000 <= _pit_ms]
                        if sec_pit_bars and sec_minute:
                            sec_open_to_pit = _pct(sec_minute[0]['open'], sec_pit_bars[-1]['close'])

                sector_info = {
                    'name': sector_name,
                    'etf': sector_etf,
                    'last_return': last_sec,
                    'return_label': sec_label,
                    'open_to_pit': sec_open_to_pit,  # in_market only
                    'change_5d': sum_5d,
                    'vs_spy_5d': round(sum_5d - spy_now.get('change_5d', 0), 2) if spy_now.get('change_5d') is not None else None,
                }
    finally:
        manager.close()

    # ── 5. Benzinga catalysts (7 trading days, broader channels) ──
    headlines_by_day = {}  # date_str -> [headlines]
    bz_from = (pit_d - timedelta(days=10)).isoformat()  # 10 calendar days ≈ 7 trading days
    try:
        result = subprocess.run([
            sys.executable, PIT_FETCH,
            '--source', 'bz-news-api', '--tickers', 'SPY',
            '--channels', BZ_CHANNELS,
            '--date-from', bz_from, '--date-to', pit_date,
            '--pit', pit_cutoff, '--limit', '100',
        ], capture_output=True, text=True, timeout=60)

        if result.stdout:
            data_obj = json.loads(result.stdout)
            for item in data_obj.get('data', []):
                avail = item.get('available_at', '')
                # PIT filter: only headlines before PIT timestamp
                if avail and avail <= pit_cutoff:
                    day = avail[:10]
                    channels = item.get('channels', [])
                    headlines_by_day.setdefault(day, []).append({
                        'time': avail[11:16] if len(avail) > 16 else '',
                        'title': item.get('title', ''),
                        'bz_id': item.get('id', ''),
                        'channels': channels,
                    })
    except Exception as e:
        print(f'Benzinga error: {e}', file=sys.stderr)

    # Rank within each day by channel importance, then recency
    # Economic data > Fed > bellwether events > general macro
    CHANNEL_PRIORITY = {'Econ #s': 0, 'Federal Reserve': 1, 'Macro Notification': 2, 'Macro Economic Events': 3}

    def _headline_sort_key(h):
        chs = h.get('channels', [])
        best_priority = min((CHANNEL_PRIORITY.get(ch, 99) for ch in chs), default=99)
        return (best_priority, h.get('time', ''))  # priority first, then time

    for day in headlines_by_day:
        headlines_by_day[day].sort(key=_headline_sort_key)

    # Group: TODAY, YESTERDAY, EARLIER
    sorted_days = sorted(headlines_by_day.keys(), reverse=True)
    today_headlines = headlines_by_day.get(pit_date, [])[:5]  # cap: max 5 today

    # Yesterday = last trading day before PIT date
    yesterday_date = None
    yesterday_headlines = []
    earlier_items = []  # (date, headline)

    for d in sorted_days:
        if d == pit_date:
            continue
        if yesterday_date is None:
            yesterday_date = d
            yesterday_headlines = headlines_by_day[d][:5]  # cap: max 5 yesterday
        else:
            for h in headlines_by_day[d]:
                earlier_items.append((d, h))

    # Cap earlier to max 3
    earlier_items = earlier_items[:3]

    # ── Assemble ──
    packet = {
        'schema_version': 'macro_snapshot.v2',
        'ticker': ticker,
        'pit_cutoff': pit_cutoff,
        'pit_date': pit_date,
        'market_session': market_session,
        'source': source,

        'market_now': {
            'spy': spy_now,
            'vix_close': vix_level,
            'vix_label': vix_label,
            'indicators': indicators,
            'sector': sector_info,
        },

        'catalysts': {
            'today': {'date': pit_date, 'headlines': today_headlines},
            'yesterday': {'date': yesterday_date, 'headlines': yesterday_headlines},
            'earlier': earlier_items,
        },

        'assembled_at': datetime.utcnow().isoformat() + 'Z',
    }

    if out_path is None:
        out_path = f'/tmp/macro_snapshot_{ticker}_{pit_date}.json'
    tmp = out_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(packet, f, indent=2, default=str)
    os.replace(tmp, out_path)
    print(f'Wrote {out_path}', file=sys.stderr)

    return packet


# ── Render ────────────────────────────────────────────────────────────

def render_text(packet: dict) -> str:
    lines = []
    pit = packet.get('pit_cutoff', '?')[:16]
    ticker = packet.get('ticker', '?')
    session = packet.get('market_session', '?')

    is_live = packet.get('source') == 'yahoo'
    if is_live:
        session_note = {
            'post_market': 'live — session settled',
            'in_market': 'live — market open',
            'pre_market': 'live — pre-market',
        }.get(session, f'live — {session}')
    else:
        session_note = {
            'post_market': 'session settled',
            'in_market': 'session in progress — session so far from minute bars',
            'pre_market': 'session not started — yesterday is last session',
        }.get(session, session)

    lines.append(f'=== MACRO CONTEXT at {pit} ({ticker}, {session}) ===')
    lines.append('')

    # ── MARKET NOW ──
    lines.append(f'MARKET NOW ({session_note}):')

    spy = packet.get('market_now', {}).get('spy', {})
    if spy:
        level = f'{spy["level_at_pit"]:.2f}' if spy.get('level_at_pit') else '?'
        o2p = f'session so far {spy["open_to_pit"]:+.1f}%' if spy.get('open_to_pit') is not None else ''
        l60 = f'last 60m {spy["last_60m"]:+.1f}%' if spy.get('last_60m') is not None else ''
        gap = f'overnight gap {spy["overnight_gap"]:+.1f}%' if spy.get('overnight_gap') is not None else ''
        today = f'today {spy["today_return"]:+.1f}%' if spy.get('today_return') is not None else ''
        yest = f'yesterday {spy["yesterday"]:+.1f}%' if spy.get('yesterday') is not None else ''
        parts = [p for p in [o2p, l60, gap, today, yest] if p]
        lines.append(f'  SPY {level} | {" | ".join(parts)}')

        # Trend + Volume
        trend_parts = []
        if spy.get('vs_50d') is not None:
            pos = 'above' if spy['vs_50d'] >= 0 else 'below'
            trend_parts.append(f'{pos} 50d MA ({spy["vs_50d"]:+.1f}%)')
        if spy.get('vs_200d') is not None:
            pos = 'above' if spy['vs_200d'] >= 0 else 'below'
            trend_parts.append(f'{pos} 200d MA ({spy["vs_200d"]:+.1f}%)')
        if trend_parts:
            lines.append(f'  Trend: {" | ".join(trend_parts)}')

        vix = packet.get('market_now', {}).get('vix_close')
        vix_lbl = packet.get('market_now', {}).get('vix_label', 'last settled close')
        if vix is not None:
            lines.append(f'  VIX: {vix:.1f} ({vix_lbl})')

        vr = spy.get('volume_ratio')
        if vr:
            desc = 'elevated' if vr > 1.2 else 'normal' if vr > 0.8 else 'low'
            lines.append(f'  Volume: {vr:.1f}x 20d avg ({desc})')

    # Other indicators
    for label, ind in packet.get('market_now', {}).get('indicators', {}).items():
        level = f'{ind["level"]:.2f}'
        rl = ind.get('return_label', 'today')
        ret = f'{rl} {ind["last_return"]:+.1f}%' if ind.get('last_return') is not None else ''
        d5 = f'5d {ind["change_5d"]:+.1f}%' if ind.get('change_5d') is not None else ''
        parts = [p for p in [ret, d5] if p]
        lines.append(f'  {label}: {level} | {" | ".join(parts)}')

    # Sector
    sec = packet.get('market_now', {}).get('sector')
    if sec and sec.get('name'):
        parts = []
        etf_tag = f', {sec["etf"]}' if sec.get('etf') else ''
        if sec.get('open_to_pit') is not None:
            parts.append(f'session so far {sec["open_to_pit"]:+.1f}%')
        else:
            rl = sec.get('return_label', 'today')
            if sec.get('last_return') is not None:
                parts.append(f'{rl} {sec["last_return"]:+.1f}%')
        if sec.get('change_5d') is not None:
            parts.append(f'5d {sec["change_5d"]:+.1f}%')
        if sec.get('vs_spy_5d') is not None:
            parts.append(f'vs SPY {sec["vs_spy_5d"]:+.1f}%')
        lines.append(f'  Sector ({sec["name"]}{etf_tag}): {" | ".join(parts)}')

    # Derived regime clues (computed from existing data, no labels)
    indicators = packet.get('market_now', {}).get('indicators', {})
    regime_lines = []

    # Breadth: RSP vs SPY
    rsp = indicators.get('Breadth (RSP)', {})
    if rsp.get('last_return') is not None and spy and spy.get('today_return') is not None:
        rsp_vs_spy = round(rsp['last_return'] - spy['today_return'], 1)
        regime_lines.append(f'Breadth: RSP vs SPY {rsp_vs_spy:+.1f}%')
    elif rsp.get('last_return') is not None and spy and spy.get('yesterday') is not None:
        rsp_vs_spy = round(rsp['last_return'] - spy['yesterday'], 1)
        regime_lines.append(f'Breadth: RSP vs SPY {rsp_vs_spy:+.1f}%')

    # Small caps: IWM vs SPY
    iwm = indicators.get('Small Cap (IWM)', {})
    iwm_ret = iwm.get('last_return')
    spy_ret = (spy.get('today_return') if spy.get('today_return') is not None else spy.get('yesterday')) if spy else None
    if iwm_ret is not None and spy_ret is not None:
        iwm_vs_spy = round(iwm_ret - spy_ret, 1)
        regime_lines.append(f'Small caps: IWM vs SPY {iwm_vs_spy:+.1f}%')

    # Curve: SHY vs TLT direction
    shy_data = indicators.get('Rates short (SHY)', {})
    tlt_data = indicators.get('Rates long (TLT)', {})
    shy_ret = shy_data.get('last_return')
    tlt_ret = tlt_data.get('last_return')
    if shy_ret is not None and tlt_ret is not None:
        spread_chg = round(tlt_ret - shy_ret, 1)
        if spread_chg > 0.2:
            curve_dir = 'bull steepening' if tlt_ret > 0 else 'bear flattening'
        elif spread_chg < -0.2:
            curve_dir = 'bear steepening' if tlt_ret < 0 else 'bull flattening'
        else:
            curve_dir = 'stable'
        regime_lines.append(f'Curve proxy: {curve_dir} (TLT-SHY spread {spread_chg:+.1f}%)')

    if regime_lines:
        lines.append('')
        for rl in regime_lines:
            lines.append(f'  {rl}')

    # ── CATALYSTS ──
    catalysts = packet.get('catalysts', {})

    today_hl = catalysts.get('today', {}).get('headlines', [])
    lines.append('')
    if today_hl:
        lines.append(f'TODAY ({catalysts["today"]["date"]}):')
        for h in today_hl:
            tag = f' [bz:{h["bz_id"]}]' if h.get('bz_id') else ''
            lines.append(f'  {h.get("time", "")} {h["title"]}{tag}')
    else:
        lines.append(f'TODAY: (no macro catalysts)')

    yest_hl = catalysts.get('yesterday', {}).get('headlines', [])
    yest_date = catalysts.get('yesterday', {}).get('date', '?')
    if yest_hl:
        lines.append(f'YESTERDAY ({yest_date}):')
        for h in yest_hl:
            tag = f' [bz:{h["bz_id"]}]' if h.get('bz_id') else ''
            lines.append(f'  {h.get("time", "")} {h["title"]}{tag}')

    earlier = catalysts.get('earlier', [])
    if earlier:
        lines.append('EARLIER:')
        for date_str, h in earlier:
            tag = f' [bz:{h["bz_id"]}]' if h.get('bz_id') else ''
            lines.append(f'  {date_str} {h.get("time", "")} {h["title"]}{tag}')

    # ── REGIME ──
    lines.append('')
    lines.append('REGIME:')
    if spy:
        parts = []
        if spy.get('change_5d') is not None:
            parts.append(f'5d {spy["change_5d"]:+.1f}%')
        if spy.get('change_20d') is not None:
            parts.append(f'20d {spy["change_20d"]:+.1f}%')
        if spy.get('change_ytd') is not None:
            parts.append(f'YTD {spy["change_ytd"]:+.1f}%')
        if parts:
            lines.append(f'  SPY: {" | ".join(parts)}')

    for label, ind in packet.get('market_now', {}).get('indicators', {}).items():
        if ind.get('change_ytd') is not None:
            lines.append(f'  {label}: YTD {ind["change_ytd"]:+.1f}%')

    return '\n'.join(lines)


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print('Usage: macro_snapshot.py TICKER --pit ISO8601|now [--session post_market|in_market|pre_market]',
              file=sys.stderr)
        print('       [--source polygon|yahoo] [--out-path PATH]', file=sys.stderr)
        print('  --pit now     use current time + auto-select yahoo source', file=sys.stderr)
        print('  --source      polygon (default, PIT-safe) or yahoo (live, real-time)', file=sys.stderr)
        print('  --session     optional — inferred from PIT timestamp if omitted', file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    pit = session = out_path = source = None

    if '--pit' in sys.argv:
        idx = sys.argv.index('--pit')
        if idx + 1 < len(sys.argv):
            pit = sys.argv[idx + 1]
    if '--session' in sys.argv:
        idx = sys.argv.index('--session')
        if idx + 1 < len(sys.argv):
            session = sys.argv[idx + 1]
    if '--out-path' in sys.argv:
        idx = sys.argv.index('--out-path')
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]
    if '--source' in sys.argv:
        idx = sys.argv.index('--source')
        if idx + 1 < len(sys.argv):
            source = sys.argv[idx + 1]

    if not pit:
        print('Error: --pit required', file=sys.stderr)
        sys.exit(1)

    # --pit now: resolve to current timestamp in US/Eastern (market TZ),
    # not host-local TZ — avoids wrong trading date on UTC servers.
    if pit == 'now':
        import pytz
        pit = datetime.now(pytz.timezone('US/Eastern')).isoformat()
        if not source:
            source = 'yahoo'

    if not source:
        source = 'polygon'

    packet = build_macro_snapshot(ticker, pit, session, out_path, source)
    print(render_text(packet))


if __name__ == '__main__':
    main()
