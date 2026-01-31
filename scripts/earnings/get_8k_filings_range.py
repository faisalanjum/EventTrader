#!/usr/bin/env python3
"""Get 8-K filings for a ticker in date range (exclusive)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE date(datetime(r.created)) > date($start) AND date(datetime(r.created)) < date($end)
RETURN r.accessionNo AS id, left(r.created, 10) AS date, r.items AS items
ORDER BY r.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_filings_8k_range.py TICKER START END")); sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            rows = [f"{r['id']}|{r['date']}|{r['items'] or ''}" for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)
    print("id|date|items\n" + "\n".join(rows) if rows else ok("NO_8K", f"0 8-K filings {ticker} {start}->{end}"))
