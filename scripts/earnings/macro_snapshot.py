#!/usr/bin/env python3
"""Macro Snapshot — regime assessment at the moment of earnings.

Combines Neo4j (SPY/sector returns), Polygon (VIX, rates, oil, dollar),
and Benzinga (last 2-3 days headlines) into a compact regime snapshot.

Usage:
    python3 scripts/earnings/macro_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00
    python3 scripts/earnings/macro_snapshot.py NOG --pit 2024-11-07T13:01:00-05:00 --out-path /tmp/macro.json

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (for SPY/sector data)
    POLYGON_API_KEY (for VIX, TLT, USO, DXY)
    BENZINGA_API_KEY (for recent headlines via pit_fetch.py)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, date as date_cls
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


def _polygon_daily(ticker: str, from_date: str, to_date: str, api_key: str) -> list[dict]:
    """Fetch daily bars from Polygon REST API."""
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
    from urllib.error import HTTPError

    # Polygon indices use I: prefix, ETFs use plain ticker
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
    params = urlencode({'adjusted': 'true', 'sort': 'asc', 'limit': '120', 'apiKey': api_key})
    full_url = f"{url}?{params}"

    try:
        req = Request(full_url)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get('results', [])
        # Convert timestamps to dates
        bars = []
        for r in results:
            ts = r.get('t', 0) / 1000  # ms to seconds
            d = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            bars.append({
                'date': d,
                'open': r.get('o'),
                'high': r.get('h'),
                'low': r.get('l'),
                'close': r.get('c'),
                'volume': r.get('v'),
            })
        return bars
    except HTTPError as e:
        print(f'Polygon error for {ticker}: {e}', file=sys.stderr)
        return []
    except Exception as e:
        print(f'Polygon error for {ticker}: {e}', file=sys.stderr)
        return []


def _compute_indicator(bars: list[dict], pit_date: str) -> dict | None:
    """Compute level + 1d/5d/YTD changes from daily bars up to pit_date."""
    # Filter to bars on or before PIT date
    valid = [b for b in bars if b['date'] <= pit_date]
    if not valid:
        return None

    current = valid[-1]
    level = current['close']

    # 1d change
    change_1d = None
    if len(valid) >= 2:
        prev = valid[-2]['close']
        if prev and prev != 0:
            change_1d = ((level - prev) / prev) * 100

    # 5d change
    change_5d = None
    if len(valid) >= 6:
        prev5 = valid[-6]['close']
        if prev5 and prev5 != 0:
            change_5d = ((level - prev5) / prev5) * 100

    # YTD change — find first trading day of the year
    pit_year = pit_date[:4]
    ytd_bars = [b for b in valid if b['date'].startswith(pit_year)]
    change_ytd = None
    if ytd_bars and len(ytd_bars) >= 2:
        first_close = ytd_bars[0]['close']
        if first_close and first_close != 0:
            change_ytd = ((level - first_close) / first_close) * 100

    return {
        'level': round(level, 2),
        'date': current['date'],
        'change_1d': round(change_1d, 2) if change_1d is not None else None,
        'change_5d': round(change_5d, 2) if change_5d is not None else None,
        'change_ytd': round(change_ytd, 2) if change_ytd is not None else None,
    }


# ── Main build ───────────────────────────────────────────────────────

def build_macro_snapshot(ticker: str, pit_cutoff: str, out_path: str | None = None) -> dict:
    """Build compact macro regime snapshot at earnings time."""

    pit_date = pit_cutoff[:10]  # "2025-02-26"

    # Date ranges for Polygon queries
    try:
        pit_d = date_cls.fromisoformat(pit_date)
    except ValueError:
        pit_d = date_cls.today()

    lookback_start = (pit_d - timedelta(days=30)).isoformat()
    year_start = f"{pit_d.year}-01-01"
    poly_from = min(lookback_start, year_start)

    api_key = _load_polygon_key()

    # ── Neo4j: SPY + Sector data ──
    manager = get_manager()
    try:
        # Get target's sector
        sector_rows = manager.execute_cypher_query_all(
            'MATCH (c:Company {ticker: $ticker})-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(s:Sector) RETURN s.name AS sector',
            {'ticker': ticker}
        )
        sector_name = sector_rows[0]['sector'] if sector_rows else None

        # SPY last 5 trading days + 20d for volume avg
        spy_rows = manager.execute_cypher_query_all('''
            MATCH (d:Date)-[hp:HAS_PRICE]->(mi:MarketIndex {ticker: 'SPY'})
            WHERE d.date >= $from AND d.date <= $pit_date
            RETURN d.date AS date, hp.daily_return AS daily_return,
                   hp.close AS close, hp.volume AS volume
            ORDER BY d.date
        ''', {'from': (pit_d - timedelta(days=35)).isoformat(), 'pit_date': pit_date})

        # Sector returns
        sector_data = None
        if sector_name:
            sec_rows = manager.execute_cypher_query_all('''
                MATCH (d:Date)-[hp:HAS_PRICE]->(s:Sector {name: $sector})
                WHERE d.date >= $from AND d.date <= $pit_date
                RETURN d.date AS date, hp.daily_return AS daily_return
                ORDER BY d.date
            ''', {'sector': sector_name, 'from': (pit_d - timedelta(days=10)).isoformat(), 'pit_date': pit_date})
            if sec_rows:
                sec_5d = sec_rows[-5:] if len(sec_rows) >= 5 else sec_rows
                sector_data = {
                    'name': sector_name,
                    'change_5d': round(sum(r['daily_return'] for r in sec_5d if r['daily_return']), 2),
                }
    finally:
        manager.close()

    # Compute SPY metrics from Neo4j
    spy_metric = None
    spy_vol_ratio = None
    if spy_rows:
        recent = spy_rows[-5:] if len(spy_rows) >= 5 else spy_rows
        spy_1d = spy_rows[-1]['daily_return'] if spy_rows else None
        spy_5d = round(sum(r['daily_return'] for r in recent if r['daily_return']), 2)
        spy_close = spy_rows[-1]['close']

        # Volume: 5d avg vs 20d avg
        vols = [r['volume'] for r in spy_rows if r['volume']]
        if len(vols) >= 5:
            vol_5d_avg = sum(vols[-5:]) / 5
            vol_20d_avg = sum(vols[-20:]) / min(20, len(vols)) if len(vols) >= 10 else None
            spy_vol_ratio = round(vol_5d_avg / vol_20d_avg, 2) if vol_20d_avg else None

        spy_metric = {
            'close': round(spy_close, 2) if spy_close else None,
            'date': spy_rows[-1]['date'],
            'change_1d': round(spy_1d, 2) if spy_1d is not None else None,
            'change_5d': spy_5d,
            'volume_ratio_5d_vs_20d': spy_vol_ratio,
        }

    # ── Polygon: VIX, TLT, USO, DXY ──
    indicators = {}
    # 5 indicators that capture the full macro regime:
    # VIX = fear, TLT = rates (inverse), USO = oil/inflation, UUP = dollar, GLD = safe haven
    poly_tickers = {
        'VIX (VIXY)': 'VIXY',
        'Rates (TLT)': 'TLT',
        'Oil (USO)': 'USO',
        'Dollar (UUP)': 'UUP',
        'Gold (GLD)': 'GLD',
    }

    if api_key:
        for label, poly_ticker in poly_tickers.items():
            bars = _polygon_daily(poly_ticker, poly_from, pit_date, api_key)
            if bars:
                metric = _compute_indicator(bars, pit_date)
                if metric:
                    indicators[label] = metric
    else:
        print('Warning: POLYGON_API_KEY not found, skipping VIX/TLT/USO/DXY', file=sys.stderr)

    # Sector relative to SPY
    sector_vs_spy = None
    if sector_data and spy_metric and spy_metric.get('change_5d') is not None:
        sector_vs_spy = round(sector_data['change_5d'] - spy_metric['change_5d'], 2)

    # ── Benzinga: last 3 days only ──
    headlines = []
    bz_from = (pit_d - timedelta(days=3)).isoformat()
    try:
        result = subprocess.run([
            sys.executable, PIT_FETCH,
            '--source', 'bz-news-api', '--tickers', 'SPY',
            '--channels', 'Macro Notification',
            '--date-from', bz_from, '--date-to', pit_date,
            '--pit', pit_cutoff, '--limit', '30',
        ], capture_output=True, text=True, timeout=30)

        if result.stdout:
            data_obj = json.loads(result.stdout)
            for item in data_obj.get('data', []):
                headlines.append({
                    'date': item.get('available_at', ''),
                    'title': item.get('title', ''),
                    'bz_id': item.get('id', ''),
                })
            headlines.sort(key=lambda h: h.get('date', ''), reverse=True)
    except Exception as e:
        print(f'Benzinga error: {e}', file=sys.stderr)

    # ── Assemble packet ──
    packet = {
        'schema_version': 'macro_snapshot.v1',
        'ticker': ticker,
        'pit_cutoff': pit_cutoff,
        'pit_date': pit_date,
        'spy': spy_metric,
        'sector': {
            'name': sector_name,
            'change_5d': sector_data['change_5d'] if sector_data else None,
            'vs_spy_5d': sector_vs_spy,
        } if sector_name else None,
        'indicators': indicators,
        'recent_headlines': headlines,
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


def render_text(packet: dict) -> str:
    lines = []
    pit = packet.get('pit_date', '?')
    ticker = packet.get('ticker', '?')

    lines.append(f'=== MACRO REGIME at {pit} ({ticker} earnings) ===')
    lines.append('')

    # Table header
    lines.append(f'{"":14s} {"Level":>10s} {"Today":>8s} {"5d":>8s} {"YTD":>8s}')
    lines.append(f'{"-"*14} {"-"*10} {"-"*8} {"-"*8} {"-"*8}')

    # SPY from Neo4j
    spy = packet.get('spy')
    if spy:
        level = f'{spy["close"]:.2f}' if spy.get('close') else '?'
        d1 = f'{spy["change_1d"]:+.1f}%' if spy.get('change_1d') is not None else '—'
        d5 = f'{spy["change_5d"]:+.1f}%' if spy.get('change_5d') is not None else '—'
        lines.append(f'{"SPY":14s} {level:>10s} {d1:>8s} {d5:>8s} {"—":>8s}')

    # Polygon indicators
    for label in packet.get('indicators', {}).keys():
        ind = packet.get('indicators', {}).get(label)
        if ind:
            level = f'{ind["level"]:.2f}'
            d1 = f'{ind["change_1d"]:+.1f}%' if ind.get('change_1d') is not None else '—'
            d5 = f'{ind["change_5d"]:+.1f}%' if ind.get('change_5d') is not None else '—'
            ytd = f'{ind["change_ytd"]:+.1f}%' if ind.get('change_ytd') is not None else '—'
            lines.append(f'{label:14s} {level:>10s} {d1:>8s} {d5:>8s} {ytd:>8s}')

    # Sector relative
    sec = packet.get('sector')
    if sec and sec.get('name'):
        d5 = f'{sec["change_5d"]:+.1f}%' if sec.get('change_5d') is not None else '—'
        vs = f'{sec["vs_spy_5d"]:+.1f}%' if sec.get('vs_spy_5d') is not None else '—'
        lines.append('')
        lines.append(f'Sector: {sec["name"]} 5d {d5} vs SPY → relative {vs}')

    # Volume
    if spy and spy.get('volume_ratio_5d_vs_20d'):
        ratio = spy['volume_ratio_5d_vs_20d']
        vol_desc = 'elevated' if ratio > 1.2 else 'normal' if ratio > 0.8 else 'low'
        lines.append(f'SPY volume: {ratio:.1f}x 20d avg ({vol_desc})')

    # Headlines
    headlines = packet.get('recent_headlines', [])
    if headlines:
        lines.append('')
        lines.append(f'Recent ({len(headlines)} headlines, last 3 days):')
        for h in headlines:
            d = h.get('date', '')[:16]
            title = h.get('title', '')
            bz_id = h.get('bz_id', '')
            tag = f' [bz:{bz_id}]' if bz_id else ''
            lines.append(f'  {d} {title}{tag}')

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print('Usage: macro_snapshot.py TICKER --pit ISO8601 [--out-path PATH]', file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    pit = None
    out_path = None

    if '--pit' in sys.argv:
        idx = sys.argv.index('--pit')
        if idx + 1 < len(sys.argv):
            pit = sys.argv[idx + 1]
    if '--out-path' in sys.argv:
        idx = sys.argv.index('--out-path')
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    if not pit:
        print('Error: --pit required', file=sys.stderr)
        sys.exit(1)

    packet = build_macro_snapshot(ticker, pit, out_path)
    print(render_text(packet))


if __name__ == '__main__':
    main()
