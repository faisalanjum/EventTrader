#!/usr/bin/env python3
"""Get guidance-related news for a ticker in date range (exclusive).

Wrapper that combines results from:
- get_guidance_news_bz.py (Guidance channel)
- get_operational_news_bz.py (Industry/sector keyword matching)

Deduplicates by news_id and outputs standardized format.
"""
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

SCRIPTS_DIR = Path(__file__).parent

def run_script(script_name: str, ticker: str, start: str, end: str, channel: str) -> dict:
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
            title = parts[2] if len(parts) > 2 else ''
            news[parts[0]] = {'date': parts[1], 'title': title, 'channel': channel}
    return news

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_guidance_news_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]

    # Run both scripts
    guidance_news = run_script("get_guidance_news_bz.py", ticker, start, end, "Guidance")
    operational_news = run_script("get_operational_news_bz.py", ticker, start, end, "Operational")

    # Merge: Guidance channel takes priority over Operational
    all_news = {}
    for news_id, data in operational_news.items():
        all_news[news_id] = data
    for news_id, data in guidance_news.items():
        all_news[news_id] = data  # overwrites if exists

    if not all_news:
        print(ok("NO_GUIDANCE_NEWS", f"0 guidance news {ticker} {start}->{end}"))
        sys.exit(0)

    # Get titles for news from guidance script (it doesn't return titles)
    news_ids_need_title = [nid for nid, data in all_news.items() if not data.get('title')]

    if news_ids_need_title:
        with neo4j_session() as (s, e):
            if e: print(e); sys.exit(1)
            try:
                query = """
                MATCH (n:News) WHERE n.id IN $ids
                RETURN n.id AS id, n.title AS title
                """
                for r in s.run(query, ids=news_ids_need_title):
                    if r['id'] in all_news:
                        all_news[r['id']]['title'] = (r['title'] or '')[:80].replace('|', '-')
            except Exception as ex:
                print(parse_exception(ex)); sys.exit(1)

    # Sort by date and output
    sorted_news = sorted(all_news.items(), key=lambda x: x[1].get('date', ''))

    print("id|date|title|channel")
    for news_id, data in sorted_news:
        title = (data.get('title') or '')[:80].replace('|', '-')
        print(f"{news_id}|{data['date']}|{title}|{data['channel']}")
