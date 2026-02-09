#!/usr/bin/env python3
"""Get Benzinga Guidance news for a ticker in date range [start, end)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(n.created) >= datetime($start) AND datetime(n.created) < datetime($end)
  AND n.channels CONTAINS 'Guidance'
RETURN n.id AS id, left(n.created, 10) AS date, n.channels AS channels
ORDER BY n.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_guidance_news_bz.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = [f"{r['id']}|{r['date']}|{r['channels'] or ''}" for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)
    print("id|date|channels\n" + "\n".join(rows) if rows else ok("NO_GUIDANCE", f"0 guidance news {ticker} {start}->{end}"))
