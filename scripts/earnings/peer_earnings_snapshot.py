#!/usr/bin/env python3
"""Peer Earnings Snapshot — standalone script.

Fetches top N same-industry peers' recent earnings results from Neo4j.
Returns 8-K 2.02 filings + Benzinga headlines + stock reactions.

Usage:
    python3 scripts/earnings/peer_earnings_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00
    python3 scripts/earnings/peer_earnings_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00 --window-start 2024-12-04
    python3 scripts/earnings/peer_earnings_snapshot.py CRM --pit 2025-02-26T16:03:55-05:00 --top 5 --out-path /tmp/peer_snapshot.json

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (or .env file)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ── Neo4j connection (reuses project's get_manager) ──────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from neograph.Neo4jConnection import get_manager

# ── Query ─────────────────────────────────────────────────────────────

QUERY_PEER_EARNINGS = """
MATCH (target:Company {ticker: $ticker})-[:BELONGS_TO]->(ind:Industry)

MATCH (peer:Company)-[:BELONGS_TO]->(ind)
WHERE peer.ticker <> $ticker AND peer.mkt_cap IS NOT NULL

MATCH (r:Report)-[pf:PRIMARY_FILER]->(peer)
WHERE r.created > $window_start
  AND r.created < $pit_cutoff
  AND r.items CONTAINS 'Item 2.02'

OPTIONAL MATCH (n:News)-[:INFLUENCES]->(peer)
WHERE datetime(n.created) >= datetime(r.created) - duration('PT18H')
  AND toString(n.created) < $pit_cutoff
WITH target, ind, peer, r, pf, n,
     CASE WHEN n IS NOT NULL THEN apoc.convert.fromJsonList(n.channels) ELSE [] END AS chList
WHERE n IS NULL OR ANY(ch IN chList WHERE ch IN ['Earnings Beats', 'Earnings Misses', 'Earnings', 'Guidance'])

WITH ind.name AS industry,
     peer.ticker AS ticker, peer.name AS name, peer.mkt_cap AS mkt_cap,
     r.created AS filed, r.market_session AS session,
     r.periodOfReport AS period_of_report, r.returns_schedule AS returns_schedule,
     pf.daily_stock AS daily_stock, pf.hourly_stock AS hourly_stock,
     pf.session_stock AS session_stock,
     pf.daily_sector AS daily_sector, pf.daily_macro AS daily_macro,
     pf.hourly_sector AS hourly_sector, pf.hourly_macro AS hourly_macro,
     collect(DISTINCT {
       date: toString(n.created),
       title: n.title,
       channels: [ch IN chList WHERE ch IN ['Earnings Beats','Earnings Misses','Earnings','Guidance']]
     }) AS raw_headlines
ORDER BY toInteger(replace(peer.mkt_cap, ',', '')) DESC, r.created

RETURN industry, ticker, name, mkt_cap, filed, session, period_of_report,
       returns_schedule,
       daily_stock, hourly_stock, session_stock,
       daily_sector, daily_macro, hourly_sector, hourly_macro,
       raw_headlines
"""

# ── Helpers ───────────────────────────────────────────────────────────

def _parse_mkt_cap(s: str | None) -> float:
    if not s:
        return 0.0
    return float(s.replace(',', ''))


def _parse_returns_schedule(raw: str | None) -> dict | None:
    """Parse returns_schedule JSON string from Report node.
    Returns dict with hourly/session/daily end timestamps, or None."""
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _pick_best_headlines(raw_headlines: list[dict]) -> list[dict]:
    """Pick best earnings + guidance headlines with fallback chain.

    Coverage across 8,762 reports (verified 2026-03-25):
      Earnings Beats/Misses: 55.4%  — best quality ("EPS $X Beats $Y")
      Broad Earnings:        94.3%  — fallback ("Q4 Earnings Assessment")
      Guidance:              69.7%  — separate channel
      Zero news at all:       1.0%  — row still exists without headlines

    Fallback chain for earnings headline:
      1. Earnings Beats / Earnings Misses (has estimate vs actual in title)
      2. Plain Earnings (may be preview/recap — less structured)
      3. None — row keeps filing + reaction data, headline_coverage = 'none'
    """
    strict_headline = None
    broad_headline = None
    guidance_headline = None

    # Sort by date so we get the earliest (closest to filing)
    valid = [h for h in raw_headlines if h.get('title')]
    valid.sort(key=lambda h: h.get('date') or '')

    for h in valid:
        chs = h.get('channels', [])
        if not strict_headline and ('Earnings Beats' in chs or 'Earnings Misses' in chs):
            strict_headline = h
        if not broad_headline and 'Earnings' in chs:
            broad_headline = h
        if not guidance_headline and 'Guidance' in chs:
            guidance_headline = h

    # Pick best earnings headline: strict > broad > none
    earnings_headline = strict_headline or broad_headline

    # Determine coverage level
    if earnings_headline and guidance_headline:
        coverage = 'full'
    elif earnings_headline or guidance_headline:
        coverage = 'partial'
    else:
        coverage = 'none'

    out = []
    if earnings_headline:
        out.append(earnings_headline)
    if guidance_headline and guidance_headline != earnings_headline:
        out.append(guidance_headline)

    return out, coverage


def build_peer_earnings_snapshot(ticker: str, pit_cutoff: str,
                                  window_start: str | None = None,
                                  top_n: int = 5,
                                  out_path: str | None = None) -> dict:
    """Build peer earnings snapshot. Returns the packet dict."""

    # Default window: 45 days before PIT cutoff (covers current earnings season)
    # 120 days would pull previous-season earnings (stale for sector mood gauging)
    if not window_start:
        from datetime import timedelta
        try:
            pit_dt = datetime.fromisoformat(pit_cutoff)
        except ValueError:
            pit_dt = datetime.fromisoformat(pit_cutoff.replace('Z', '+00:00'))
        ws_dt = pit_dt - timedelta(days=45)
        window_start = ws_dt.strftime('%Y-%m-%d')

    manager = get_manager()
    try:
        rows = manager.execute_cypher_query_all(
            QUERY_PEER_EARNINGS,
            {'ticker': ticker, 'window_start': window_start, 'pit_cutoff': pit_cutoff}
        )
    finally:
        manager.close()

    if not rows:
        packet = {
            'schema_version': 'peer_earnings_snapshot.v1',
            'ticker': ticker,
            'pit_cutoff': pit_cutoff,
            'window_start': window_start,
            'industry': None,
            'peers': [],
            'summary': {'total_peers': 0, 'total_filings': 0},
            'assembled_at': datetime.utcnow().isoformat() + 'Z'
        }
    else:
        industry = rows[0].get('industry')

        # Keep only the MOST RECENT filing per peer (= current earnings season)
        # This prevents pulling previous-quarter earnings when window is wide
        latest_by_ticker = {}  # ticker -> row with latest filed date
        for row in rows:
            t = row['ticker']
            filed = str(row.get('filed', ''))
            if t not in latest_by_ticker or filed > str(latest_by_ticker[t].get('filed', '')):
                latest_by_ticker[t] = row

        # Rank by mkt_cap, take top_n
        ranked = sorted(latest_by_ticker.values(),
                        key=lambda r: _parse_mkt_cap(r.get('mkt_cap')),
                        reverse=True)[:top_n]

        peers = []
        for row in ranked:
            headlines, coverage = _pick_best_headlines(row.get('raw_headlines', []))

            # PIT-safe return nulling using exact returns_schedule timestamps.
            # Same approach as _build_forward_returns() in warmup_cache.py:
            # if a horizon's measurement window end > pit_cutoff, null it.
            hourly = row.get('hourly_stock')
            session_ret = row.get('session_stock')
            daily = row.get('daily_stock')
            daily_sector = row.get('daily_sector')
            daily_macro = row.get('daily_macro')
            hourly_sector = row.get('hourly_sector')
            hourly_macro = row.get('hourly_macro')

            rs = _parse_returns_schedule(row.get('returns_schedule'))
            if rs:
                if rs.get('daily') and str(rs['daily']) > pit_cutoff:
                    daily = None
                    daily_sector = None
                    daily_macro = None
                if rs.get('session') and str(rs['session']) > pit_cutoff:
                    session_ret = None
                if rs.get('hourly') and str(rs['hourly']) > pit_cutoff:
                    hourly = None
                    hourly_sector = None
                    hourly_macro = None

            # Best available horizon for context (daily > hourly)
            best_sector = daily_sector if daily_sector is not None else hourly_sector
            best_macro = daily_macro if daily_macro is not None else hourly_macro
            context_horizon = 'daily' if daily_sector is not None else ('hourly' if hourly_sector is not None else None)

            peers.append({
                'ticker': row['ticker'],
                'name': row['name'],
                'mkt_cap': row.get('mkt_cap'),
                'filed': row['filed'],
                'period_of_report': row.get('period_of_report'),
                'market_session': row.get('session'),
                'daily_stock_pct': daily,
                'hourly_stock_pct': hourly,
                'session_stock_pct': session_ret,
                'daily_sector_pct': daily_sector,
                'daily_macro_pct': daily_macro,
                'hourly_sector_pct': hourly_sector,
                'hourly_macro_pct': hourly_macro,
                'best_sector_pct': best_sector,
                'best_macro_pct': best_macro,
                'context_horizon': context_horizon,
                'headlines': headlines,
                'headline_coverage': coverage,
            })

        # Sort final output: by mkt_cap desc
        peers.sort(key=lambda p: -_parse_mkt_cap(p.get('mkt_cap')))

        unique_peer_tickers = list(dict.fromkeys(p['ticker'] for p in peers))

        packet = {
            'schema_version': 'peer_earnings_snapshot.v1',
            'ticker': ticker,
            'pit_cutoff': pit_cutoff,
            'window_start': window_start,
            'industry': industry,
            'peers': peers,
            'summary': {
                'total_peers': len(unique_peer_tickers),
                'total_filings': len(peers),
                'peer_tickers': unique_peer_tickers,
            },
            'assembled_at': datetime.utcnow().isoformat() + 'Z'
        }

    # ── Write ──
    if out_path is None:
        out_path = f'/tmp/peer_earnings_snapshot_{ticker}.json'

    tmp = out_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(packet, f, indent=2, default=str)
    os.replace(tmp, out_path)
    print(f'Wrote {out_path} ({len(packet.get("peers", []))} filings from {packet["summary"]["total_peers"]} peers)')

    return packet


# ── Render ────────────────────────────────────────────────────────────

def render_text(packet: dict) -> str:
    """Render peer earnings snapshot as planner-friendly text."""
    lines = []
    industry = packet.get('industry', '?')
    ticker = packet['ticker']
    peers = packet.get('peers', [])
    summary = packet.get('summary', {})

    lines.append(f'=== PEER EARNINGS: {industry} (top {summary.get("total_peers", 0)} by market cap, PIT {packet["pit_cutoff"][:10]}) ===')
    lines.append(f'Target: {ticker} | Window: {packet.get("window_start", "?")} → {packet["pit_cutoff"][:10]}')
    lines.append('')

    current_ticker = None
    for p in peers:
        t = p['ticker']
        if t != current_ticker:
            cap_str = p.get('mkt_cap', '?')
            lines.append(f'{t} ({p.get("name", "")}, ${cap_str})')
            current_ticker = t

        filed = p.get('filed', '?')
        filed_short = str(filed)[:16] if filed else '?'
        session = p.get('market_session', '?')
        daily = p.get('daily_stock_pct')
        hourly = p.get('hourly_stock_pct')
        best_sector = p.get('best_sector_pct')
        best_macro = p.get('best_macro_pct')
        ctx_horizon = p.get('context_horizon')

        # Relative timing: T-3d, T-0d, etc.
        t_minus = ''
        try:
            filed_dt = datetime.fromisoformat(str(filed).replace('Z', '+00:00'))
            pit_dt = datetime.fromisoformat(packet['pit_cutoff'].replace('Z', '+00:00'))
            days_before = (pit_dt - filed_dt).days
            t_minus = f' (T-{days_before}d)' if days_before > 0 else ' (T-0d)'
        except (ValueError, TypeError):
            pass

        daily_s = f'{daily:+.1f}%' if daily is not None else 'n/a (PIT)'
        hourly_s = f'{hourly:+.1f}%' if hourly is not None else 'n/a (PIT)'

        lines.append(f'  Filed: {filed_short} {session}{t_minus}')
        lines.append(f'  Reaction: hourly {hourly_s} → daily {daily_s}')

        if best_sector is not None or best_macro is not None:
            parts = []
            if best_sector is not None:
                parts.append(f'sector {best_sector:+.1f}%')
            if best_macro is not None:
                parts.append(f'SPY {best_macro:+.1f}%')
            # Adjusted return: stock-specific move after removing sector/macro
            adj_parts = []
            if daily is not None and best_sector is not None:
                adj_vs_sector = daily - best_sector
                adj_parts.append(f'vs sector {adj_vs_sector:+.1f}%')
            elif hourly is not None and best_sector is not None:
                adj_vs_sector = hourly - best_sector
                adj_parts.append(f'vs sector {adj_vs_sector:+.1f}%')
            if daily is not None and best_macro is not None:
                adj_vs_macro = daily - best_macro
                adj_parts.append(f'vs SPY {adj_vs_macro:+.1f}%')
            elif hourly is not None and best_macro is not None:
                adj_vs_macro = hourly - best_macro
                adj_parts.append(f'vs SPY {adj_vs_macro:+.1f}%')
            horizon_label = f' ({ctx_horizon})' if ctx_horizon else ''
            ctx_line = ' | '.join(parts)
            adj_line = ' | '.join(adj_parts) if adj_parts else ''
            if adj_line:
                lines.append(f'  Context{horizon_label}: {ctx_line} → adj: {adj_line}')
            else:
                lines.append(f'  Context{horizon_label}: {ctx_line}')

        coverage = p.get('headline_coverage', 'none')
        if coverage != 'none':
            for h in p.get('headlines', []):
                date_s = str(h.get('date', ''))[:16] if h.get('date') else ''
                title = h.get('title', '')
                lines.append(f'  → {date_s} {title}')
        else:
            lines.append(f'  (no earnings/guidance headlines available)')

        lines.append('')

    return '\n'.join(lines)


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('Usage: peer_earnings_snapshot.py TICKER --pit ISO8601 [--window-start ISO8601] [--top N] [--out-path PATH]',
              file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()

    pit_cutoff = None
    if '--pit' in sys.argv:
        idx = sys.argv.index('--pit')
        if idx + 1 < len(sys.argv):
            pit_cutoff = sys.argv[idx + 1]
    if not pit_cutoff:
        print('Error: --pit required', file=sys.stderr)
        sys.exit(1)

    window_start = None
    if '--window-start' in sys.argv:
        idx = sys.argv.index('--window-start')
        if idx + 1 < len(sys.argv):
            window_start = sys.argv[idx + 1]

    top_n = 5
    if '--top' in sys.argv:
        idx = sys.argv.index('--top')
        if idx + 1 < len(sys.argv):
            top_n = int(sys.argv[idx + 1])

    out_path = None
    if '--out-path' in sys.argv:
        idx = sys.argv.index('--out-path')
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    packet = build_peer_earnings_snapshot(ticker, pit_cutoff, window_start, top_n, out_path)

    # Print rendered text to stdout
    print()
    print(render_text(packet))


if __name__ == '__main__':
    main()
