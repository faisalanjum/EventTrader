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
    python3 scripts/earnings/macro_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00 --session post_market
    python3 scripts/earnings/macro_snapshot.py NOG --pit 2024-11-07T13:01:00-05:00 --session in_market

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    POLYGON_API_KEY
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
from neograph.Neo4jConnection import get_manager

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

    # Daily bars: yesterday, 5d, 20d, YTD
    valid_daily = [b for b in daily_bars if b['date'] <= pit_date]
    yesterday_return = None
    yesterday_close = None
    change_5d = None
    change_20d = None
    change_ytd = None
    vol_5d = None
    vol_20d = None

    if len(valid_daily) >= 2:
        yesterday_close = valid_daily[-2]['close'] if market_session != 'post_market' else valid_daily[-1]['close']
        if market_session == 'post_market':
            yesterday_return = _pct(valid_daily[-2]['close'], valid_daily[-1]['close']) if len(valid_daily) >= 2 else None
        else:
            yesterday_return = _pct(valid_daily[-3]['close'], valid_daily[-2]['close']) if len(valid_daily) >= 3 else None

    if len(valid_daily) >= 6:
        change_5d = _pct(valid_daily[-6]['close'], valid_daily[-1]['close'])
    if len(valid_daily) >= 21:
        change_20d = _pct(valid_daily[-21]['close'], valid_daily[-1]['close'])

    # YTD
    pit_year = pit_date[:4]
    ytd_bars = [b for b in valid_daily if b['date'].startswith(pit_year)]
    if ytd_bars and len(ytd_bars) >= 2:
        change_ytd = _pct(ytd_bars[0]['close'], ytd_bars[-1]['close'])

    # Volume
    vols = [b['volume'] for b in valid_daily if b['volume']]
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
        pit_bars = [b for b in minute_bars if b['ts_ms'] <= pit_ms]

        if pit_bars:
            level_at_pit = pit_bars[-1]['close']
            today_open = minute_bars[0]['open'] if minute_bars else None

            if today_open and today_open != 0:
                open_to_pit = _pct(today_open, level_at_pit)

            # Last 60 min
            sixty_min_ago = pit_ms - (60 * 60 * 1000)
            bars_60m_ago = [b for b in pit_bars if b['ts_ms'] <= sixty_min_ago]
            if bars_60m_ago:
                last_60m = _pct(bars_60m_ago[-1]['close'], level_at_pit)

    # For post_market: today's close IS the level (session settled)
    if market_session == 'post_market' and valid_daily:
        today_bar = valid_daily[-1]
        if today_bar['date'] == pit_date:
            level_at_pit = level_at_pit or today_bar['close']
            if not open_to_pit and today_bar['open']:
                open_to_pit = _pct(today_bar['open'], today_bar['close'])

    return {
        'level_at_pit': round(level_at_pit, 2) if level_at_pit else None,
        'open_to_pit': open_to_pit,
        'last_60m': last_60m,
        'yesterday': yesterday_return,
        'change_5d': change_5d,
        'change_20d': change_20d,
        'change_ytd': change_ytd,
        'volume_5d_avg': vol_5d,
        'volume_20d_avg': vol_20d,
        'volume_ratio': round(vol_5d / vol_20d, 2) if vol_5d and vol_20d and vol_20d > 0 else None,
    }


# ── Indicator daily state ─────────────────────────────────────────────

def _compute_indicator_daily(daily_bars: list[dict], pit_date: str) -> dict | None:
    """Compute indicator level + today/5d/YTD from daily bars."""
    valid = [b for b in daily_bars if b['date'] <= pit_date]
    if not valid:
        return None

    level = valid[-1]['close']
    today = _pct(valid[-2]['close'], level) if len(valid) >= 2 else None
    d5 = _pct(valid[-6]['close'], level) if len(valid) >= 6 else None

    pit_year = pit_date[:4]
    ytd_bars = [b for b in valid if b['date'].startswith(pit_year)]
    ytd = _pct(ytd_bars[0]['close'], level) if ytd_bars and len(ytd_bars) >= 2 else None

    return {'level': round(level, 2), 'today': today, 'change_5d': d5, 'change_ytd': ytd}


# ── Main build ───────────────────────────────────────────────────────

INDICATOR_TICKERS = {
    'Vol proxy (VIXY)': 'VIXY',
    'Rates proxy (TLT)': 'TLT',
    'Oil proxy (USO)': 'USO',
    'Dollar proxy (UUP)': 'UUP',
    'Gold proxy (GLD)': 'GLD',
}

# Broader channels for catalysts — catches Fed, economic data, macro events
BZ_CHANNELS = 'Macro Notification,Federal Reserve,Econ #s,Macro Economic Events'


def build_macro_snapshot(ticker: str, pit_cutoff: str, market_session: str,
                          out_path: str | None = None) -> dict:
    pit_date = pit_cutoff[:10]

    try:
        pit_d = date_cls.fromisoformat(pit_date)
    except ValueError:
        pit_d = date_cls.today()

    year_start = f"{pit_d.year}-01-01"
    daily_from = min((pit_d - timedelta(days=30)).isoformat(), year_start)
    api_key = _load_polygon_key()

    # ── 1. SPY minute bars for MARKET NOW ──
    spy_minute = []
    if api_key and market_session in ('in_market', 'post_market'):
        spy_minute = _polygon_minute('SPY', pit_date, api_key)
        time.sleep(0.3)  # rate limit courtesy

    # ── 2. SPY daily bars ──
    spy_daily = []
    if api_key:
        spy_daily = _polygon_daily('SPY', daily_from, pit_date, api_key)
        time.sleep(0.3)

    spy_now = _compute_spy_now(spy_minute, spy_daily, pit_cutoff, market_session)

    # ── 3. Other indicators (daily only) ──
    indicators = {}
    if api_key:
        for label, poly_ticker in INDICATOR_TICKERS.items():
            bars = _polygon_daily(poly_ticker, daily_from, pit_date, api_key)
            if bars:
                metric = _compute_indicator_daily(bars, pit_date)
                if metric:
                    indicators[label] = metric
            time.sleep(0.3)

    # ── 4. Sector from Neo4j ──
    sector_info = None
    manager = get_manager()
    try:
        sector_rows = manager.execute_cypher_query_all(
            'MATCH (c:Company {ticker: $ticker})-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(s:Sector) '
            'RETURN s.name AS sector, s.ticker AS sector_etf',
            {'ticker': ticker}
        )
        sector_name = sector_rows[0]['sector'] if sector_rows else None

        if sector_name:
            sec_rows = manager.execute_cypher_query_all('''
                MATCH (d:Date)-[hp:HAS_PRICE]->(s:Sector {name: $sector})
                WHERE d.date >= $from AND d.date <= $pit_date
                RETURN d.date AS date, hp.daily_return AS ret
                ORDER BY d.date
            ''', {'sector': sector_name, 'from': (pit_d - timedelta(days=10)).isoformat(), 'pit_date': pit_date})

            if sec_rows:
                today_sec = sec_rows[-1]['ret'] if sec_rows[-1]['date'] == pit_date else None
                sec_5d = sec_rows[-5:] if len(sec_rows) >= 5 else sec_rows
                sum_5d = round(sum(r['ret'] for r in sec_5d if r['ret']), 2)
                sector_info = {
                    'name': sector_name,
                    'today': round(today_sec, 2) if today_sec is not None else None,
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
                    headlines_by_day.setdefault(day, []).append({
                        'time': avail[11:16] if len(avail) > 16 else '',
                        'title': item.get('title', ''),
                        'bz_id': item.get('id', ''),
                    })
    except Exception as e:
        print(f'Benzinga error: {e}', file=sys.stderr)

    # Sort within each day (newest first)
    for day in headlines_by_day:
        headlines_by_day[day].sort(key=lambda h: h.get('time', ''), reverse=True)

    # Group: TODAY, YESTERDAY, EARLIER
    sorted_days = sorted(headlines_by_day.keys(), reverse=True)
    today_headlines = headlines_by_day.get(pit_date, [])

    # Yesterday = last trading day before PIT date
    yesterday_date = None
    yesterday_headlines = []
    earlier_items = []  # (date, headline)

    for d in sorted_days:
        if d == pit_date:
            continue
        if yesterday_date is None:
            yesterday_date = d
            yesterday_headlines = headlines_by_day[d]
        else:
            for h in headlines_by_day[d]:
                earlier_items.append((d, h))

    # Cap earlier to most significant 5
    earlier_items = earlier_items[:5]

    # ── Assemble ──
    packet = {
        'schema_version': 'macro_snapshot.v2',
        'ticker': ticker,
        'pit_cutoff': pit_cutoff,
        'pit_date': pit_date,
        'market_session': market_session,

        'market_now': {
            'spy': spy_now,
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

    session_note = {
        'post_market': 'session settled',
        'in_market': 'session in progress — open→PIT from minute bars',
        'pre_market': 'session not started — yesterday is last session',
    }.get(session, session)

    lines.append(f'=== MACRO CONTEXT at {pit} ({ticker}, {session}) ===')
    lines.append('')

    # ── MARKET NOW ──
    lines.append(f'MARKET NOW ({session_note}):')

    spy = packet.get('market_now', {}).get('spy', {})
    if spy:
        level = f'{spy["level_at_pit"]:.2f}' if spy.get('level_at_pit') else '?'
        o2p = f'open→PIT {spy["open_to_pit"]:+.1f}%' if spy.get('open_to_pit') is not None else ''
        l60 = f'last 60m {spy["last_60m"]:+.1f}%' if spy.get('last_60m') is not None else ''
        yest = f'yesterday {spy["yesterday"]:+.1f}%' if spy.get('yesterday') is not None else ''
        parts = [p for p in [o2p, l60, yest] if p]
        lines.append(f'  SPY {level} | {" | ".join(parts)}')

        # Volume
        vr = spy.get('volume_ratio')
        if vr:
            desc = 'elevated' if vr > 1.2 else 'normal' if vr > 0.8 else 'low'
            lines.append(f'  Volume: {vr:.1f}x 20d avg ({desc})')

    # Other indicators
    for label, ind in packet.get('market_now', {}).get('indicators', {}).items():
        level = f'{ind["level"]:.2f}'
        today = f'today {ind["today"]:+.1f}%' if ind.get('today') is not None else ''
        d5 = f'5d {ind["change_5d"]:+.1f}%' if ind.get('change_5d') is not None else ''
        parts = [p for p in [today, d5] if p]
        lines.append(f'  {label}: {level} | {" | ".join(parts)}')

    # Sector
    sec = packet.get('market_now', {}).get('sector')
    if sec and sec.get('name'):
        parts = []
        if sec.get('today') is not None:
            parts.append(f'today {sec["today"]:+.1f}%')
        if sec.get('change_5d') is not None:
            parts.append(f'5d {sec["change_5d"]:+.1f}%')
        if sec.get('vs_spy_5d') is not None:
            parts.append(f'vs SPY {sec["vs_spy_5d"]:+.1f}%')
        lines.append(f'  Sector ({sec["name"]}): {" | ".join(parts)}')

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
        print('Usage: macro_snapshot.py TICKER --pit ISO8601 --session post_market|in_market|pre_market [--out-path PATH]',
              file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    pit = session = out_path = None

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

    if not pit:
        print('Error: --pit required', file=sys.stderr)
        sys.exit(1)
    if not session:
        print('Error: --session required (post_market|in_market|pre_market)', file=sys.stderr)
        sys.exit(1)

    packet = build_macro_snapshot(ticker, pit, session, out_path)
    print(render_text(packet))


if __name__ == '__main__':
    main()
