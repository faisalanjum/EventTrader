#!/usr/bin/env python3
"""Get guidance-related news for a ticker in date range [start, end).

Wrapper that combines results from:
- get_guidance_news_bz.py (Guidance channel)
- get_operational_news_bz.py (Industry/sector keyword matching)

Deduplicates by news_id and outputs content-level format for guidance extraction.
Output format matches other content-level scripts: report_id|date|source_type|source_key
"""
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

SCRIPTS_DIR = Path(__file__).parent

def run_script(script_name: str, ticker: str, start: str, end: str) -> dict:
    """Run a script and parse output into dict keyed by news_id."""
    result = subprocess.run(
        ["python", str(SCRIPTS_DIR / script_name), ticker, start, end],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent.parent)
    )
    news = {}
    for line in result.stdout.strip().split('\n'):
        # Skip comments, OK/ERROR lines, headers
        if line.startswith('#') or line.startswith('OK|') or line.startswith('ERROR|'):
            continue
        if line.startswith('id|'):  # header
            continue
        if '|' not in line:
            continue
        parts = line.split('|')
        if len(parts) >= 2 and parts[0]:
            news[parts[0]] = {'date': parts[1]}
    return news

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_guidance_news_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    # Run both scripts
    guidance_news = run_script("get_guidance_news_bz.py", ticker, start, end)
    operational_news = run_script("get_operational_news_bz.py", ticker, start, end)

    # Merge: union of both (Guidance channel and Operational keyword matches)
    all_news = {}
    for news_id, data in operational_news.items():
        all_news[news_id] = data
    for news_id, data in guidance_news.items():
        all_news[news_id] = data  # overwrites if exists (same date anyway)

    if not all_news:
        print(ok("NO_GUIDANCE_NEWS", f"0 guidance news {ticker} {start}->{end}"))
        sys.exit(0)

    # Sort by date and output in content-level format
    sorted_news = sorted(all_news.items(), key=lambda x: x[1].get('date', ''))

    # Output format: report_id|date|source_type|source_key
    print("report_id|date|source_type|source_key")
    for news_id, data in sorted_news:
        print(f"{news_id}|{data['date']}|news|full")
