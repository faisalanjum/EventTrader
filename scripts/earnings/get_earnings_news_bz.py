#!/usr/bin/env python3
"""Get Benzinga Earnings news (beat/miss) for a ticker in date range (exclusive).

Channels: Earnings, Earnings Beats, Earnings Misses
Use get_guidance_news_bz.py for forward-looking guidance.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

CHANNELS = ["Earnings", "Earnings Beats", "Earnings Misses"]

QUERY = """
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE date(datetime(n.created)) > date($start) AND date(datetime(n.created)) < date($end)
  AND any(ch IN n.channels WHERE ch IN $channels)
  AND r.daily_stock IS NOT NULL
RETURN n.id AS id,
       left(n.created, 10) AS date,
       [ch IN n.channels WHERE ch IN $channels] AS channels,
       r.daily_stock AS daily_return,
       n.title AS title
ORDER BY n.created
"""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(error("USAGE", "get_earnings_news_bz.py TICKER START END"))
        sys.exit(1)
    ticker, start, end = sys.argv[1:4]
    with neo4j_session() as (s, e):
        if e:
            print(e)
            sys.exit(1)
        try:
            results = list(s.run(QUERY, ticker=ticker.upper(), start=start, end=end, channels=CHANNELS))
        except Exception as ex:
            print(parse_exception(ex))
            sys.exit(1)
    if not results:
        print(ok("NO_EARNINGS", f"0 earnings news {ticker} {start}->{end}"))
    else:
        print("id|date|channels|return|title")
        for r in results:
            chs = ",".join(r["channels"]) if r["channels"] else ""
            ret = f"{r['daily_return']:.2f}%" if r["daily_return"] else "N/A"
            title = (r["title"] or "")[:80].replace("|", "-")
            print(f"{r['id']}|{r['date']}|{chs}|{ret}|{title}")
