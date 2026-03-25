#!/usr/bin/env python3
"""Macro Headlines — fetch SPY-tagged macro news from Benzinga API.

NOT a default pre-assembled input. Use when:
- Planner triggers macro research via fetch_plan (bz-news-api agent)
- Manual exploration of macro context for a quarter
- Orchestrator optionally pre-fetches for quarters with volatile SPY

Usage:
    python3 scripts/earnings/macro_headlines.py --date-from 2024-12-04 --date-to 2025-02-26 --pit 2025-02-26T16:03:55-05:00
    python3 scripts/earnings/macro_headlines.py --date-from 2024-12-04 --date-to 2025-02-26 --pit 2025-02-26T16:03:55-05:00 --limit 200 --out-path /tmp/macro.json

Calls Benzinga API via pit_fetch.py (same wrapper as bz-news-api agent).
Requires BENZINGA_API_KEY in .env.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[2] / '.claude' / 'skills' / 'earnings-orchestrator' / 'scripts'
PIT_FETCH = str(SCRIPT_DIR / 'pit_fetch.py')


def fetch_macro_headlines(date_from: str, date_to: str, pit: str,
                          limit: int = 200, out_path: str | None = None) -> dict:
    """Fetch SPY + Macro Notification headlines via pit_fetch.py."""

    cmd = [
        sys.executable, PIT_FETCH,
        '--source', 'bz-news-api',
        '--tickers', 'SPY',
        '--channels', 'Macro Notification',
        '--date-from', date_from,
        '--date-to', date_to,
        '--pit', pit,
        '--limit', str(limit),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f'pit_fetch.py error: {result.stderr}', file=sys.stderr)
        return {'error': result.stderr, 'headlines': []}

    # pit_fetch.py: metadata → stderr, data → stdout
    try:
        data_obj = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f'Failed to parse pit_fetch.py stdout: {result.stdout[:200]}', file=sys.stderr)
        return {'error': 'json parse error', 'headlines': []}

    meta = {}
    if result.stderr:
        try:
            meta = json.loads(result.stderr)
        except json.JSONDecodeError:
            pass  # metadata is optional

    items = data_obj.get('data', [])
    gaps = data_obj.get('gaps', [])

    # Extract just what the planner needs: date, title, channels
    headlines = []
    for item in items:
        headlines.append({
            'date': item.get('available_at', item.get('created', '')),
            'title': item.get('title', ''),
            'channels': item.get('channels', []),
        })

    # Sort chronologically (oldest first)
    headlines.sort(key=lambda h: h.get('date', ''))

    packet = {
        'schema_version': 'macro_headlines.v1',
        'date_from': date_from,
        'date_to': date_to,
        'pit': pit,
        'total_headlines': len(headlines),
        'gaps': len(gaps),
        'headlines': headlines,
        'assembled_at': datetime.utcnow().isoformat() + 'Z',
    }

    # Write
    if out_path is None:
        out_path = f'/tmp/macro_headlines_{date_from}_{date_to}.json'

    tmp = out_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(packet, f, indent=2, default=str)
    os.replace(tmp, out_path)
    print(f'Wrote {out_path} ({len(headlines)} headlines)', file=sys.stderr)

    return packet


def render_text(packet: dict) -> str:
    """Render macro headlines as planner-friendly text."""
    lines = []
    headlines = packet.get('headlines', [])

    lines.append(f'=== MACRO HEADLINES (SPY, Macro Notification) ===')
    lines.append(f'Window: {packet.get("date_from", "?")} → {packet.get("date_to", "?")} | PIT: {packet.get("pit", "?")[:10]}')
    lines.append(f'{len(headlines)} headlines')
    lines.append('')

    current_date = None
    for h in headlines:
        date_str = h.get('date', '')[:10]
        time_str = h.get('date', '')[11:16] if len(h.get('date', '')) > 16 else ''

        if date_str != current_date:
            if current_date is not None:
                lines.append('')
            lines.append(f'--- {date_str} ---')
            current_date = date_str

        title = h.get('title', '')
        lines.append(f'  {time_str} {title}')

    return '\n'.join(lines)


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    date_from = date_to = pit = None
    limit = 200
    out_path = None

    if '--date-from' in sys.argv:
        idx = sys.argv.index('--date-from')
        if idx + 1 < len(sys.argv):
            date_from = sys.argv[idx + 1]
    if '--date-to' in sys.argv:
        idx = sys.argv.index('--date-to')
        if idx + 1 < len(sys.argv):
            date_to = sys.argv[idx + 1]
    if '--pit' in sys.argv:
        idx = sys.argv.index('--pit')
        if idx + 1 < len(sys.argv):
            pit = sys.argv[idx + 1]
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    if '--out-path' in sys.argv:
        idx = sys.argv.index('--out-path')
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    if not all([date_from, date_to, pit]):
        print('Usage: macro_headlines.py --date-from ISO --date-to ISO --pit ISO [--limit N] [--out-path PATH]',
              file=sys.stderr)
        sys.exit(1)

    packet = fetch_macro_headlines(date_from, date_to, pit, limit, out_path)
    print(render_text(packet))


if __name__ == '__main__':
    main()
