#!/usr/bin/env python3
"""Get all news for a ticker in date range (exclusive), optionally filtered by channel."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
RETURN n.id AS id, left(n.created, 10) AS date, n.channels AS channels
ORDER BY n.created
"""

QUERY_CHANNEL = """
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
  AND n.channels CONTAINS $channel
RETURN n.id AS id, left(n.created, 10) AS date, n.channels AS channels
ORDER BY n.created
"""

if __name__ == "__main__":
    args, channel = sys.argv[1:], None
    i = 0
    positional = []
    while i < len(args):
        if args[i] == "--channel" and i + 1 < len(args):
            channel = args[i + 1]; i += 2
        else:
            positional.append(args[i]); i += 1
    if len(positional) < 3:
        print(error("USAGE", "get_news_range.py TICKER START END [--channel Guidance]")); sys.exit(1)
    ticker, start, end = positional[:3]
    with neo4j_session() as (s, e):
        if e: print(e); sys.exit(1)
        try:
            if channel:
                rows = [f"{r['id']}|{r['date']}|{r['channels'] or ''}" for r in s.run(QUERY_CHANNEL, ticker=ticker.upper(), start=start, end=end, channel=channel)]
            else:
                rows = [f"{r['id']}|{r['date']}|{r['channels'] or ''}" for r in s.run(QUERY, ticker=ticker.upper(), start=start, end=end)]
        except Exception as ex:
            print(parse_exception(ex)); sys.exit(1)
    print("id|date|channels\n" + "\n".join(rows) if rows else ok("NO_NEWS", f"0 news {ticker} {start}->{end}"))
