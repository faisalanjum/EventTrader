#!/usr/bin/env python3
"""
Get Benzinga news that influenced a company on a specific date.
Usage: python scripts/earnings/get_news_for_dates.py TICKER DATE [THRESHOLD]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, ok, fmt, parse_exception
load_env()

QUERY = """
MATCH (c:Company {ticker: $ticker})
WITH c
MATCH (n:News)-[r:INFLUENCES]->(c)
WHERE date(datetime(n.created)) >= date($date) - duration('P3D')
  AND date(datetime(n.created)) <= date($date)
  AND r.daily_stock IS NOT NULL AND r.daily_macro IS NOT NULL
  AND abs(r.daily_stock - r.daily_macro) >= $threshold
RETURN n.id AS news_id,
       n.title AS title,
       n.body AS body,
       n.teaser AS teaser,
       n.created AS created,
       n.updated AS updated,
       n.url AS url,
       n.authors AS authors,
       n.tags AS tags,
       n.channels AS channels,
       n.market_session AS market_session,
       n.returns_schedule AS returns_schedule,
       r.symbol AS symbol,
       r.created_at AS rel_created_at,
       r.daily_stock AS daily_stock,
       r.daily_macro AS daily_macro,
       r.daily_sector AS daily_sector,
       r.daily_industry AS daily_industry,
       r.session_stock AS session_stock,
       r.session_macro AS session_macro,
       r.session_sector AS session_sector,
       r.session_industry AS session_industry,
       r.hourly_stock AS hourly_stock,
       r.hourly_macro AS hourly_macro,
       r.hourly_sector AS hourly_sector,
       r.hourly_industry AS hourly_industry
ORDER BY n.created ASC
"""

COLS = "news_id|title|body|teaser|created|updated|url|authors|tags|channels|market_session|returns_schedule|symbol|rel_created_at|daily_stock|daily_macro|daily_sector|daily_industry|session_stock|session_macro|session_sector|session_industry|hourly_stock|hourly_macro|hourly_sector|hourly_industry"

def clean(val):
    """Clean value for pipe-delimited output."""
    if val is None:
        return "N/A"
    if isinstance(val, list):
        return ";".join(str(v) for v in val)
    s = str(val)
    if hasattr(val, "isoformat"):
        s = val.isoformat()
    return s.replace("|", "-").replace("\n", " ").replace("\r", "")

def get_news_for_date(ticker: str, date: str, threshold: float = 0) -> str:
    if threshold < 0:
        return error("INVALID_ARG", "threshold cannot be negative", f"Received: {threshold}")
    with neo4j_session() as (session, err):
        if err: return err
        try:
            rows = ["|".join([
                clean(r["news_id"]),
                clean(r["title"]),
                clean(r["body"])[:3000],
                clean(r["teaser"]),
                clean(r["created"]),
                clean(r["updated"]),
                clean(r["url"]),
                clean(r["authors"]),
                clean(r["tags"]),
                clean(r["channels"]),
                clean(r["market_session"]),
                clean(r["returns_schedule"]),
                clean(r["symbol"]),
                clean(r["rel_created_at"]),
                fmt(r["daily_stock"]), fmt(r["daily_macro"]), fmt(r["daily_sector"]), fmt(r["daily_industry"]),
                fmt(r["session_stock"]), fmt(r["session_macro"]), fmt(r["session_sector"]), fmt(r["session_industry"]),
                fmt(r["hourly_stock"]), fmt(r["hourly_macro"]), fmt(r["hourly_sector"]), fmt(r["hourly_industry"])
            ]) for r in session.run(QUERY, ticker=ticker.upper(), date=date, threshold=threshold)]
        except Exception as e:
            return parse_exception(e)
    if not rows:
        return ok("NO_NEWS", f"No news for {ticker} on {date}" + (f" with |daily_adj|>={threshold:.2f}%" if threshold else ""), "Check date or lower threshold")
    return COLS + "\n" + "\n".join(rows)

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(error("USAGE", "get_news_for_dates.py TICKER DATE [THRESHOLD]"))
        sys.exit(1)
    threshold = 0
    if len(sys.argv) == 4:
        try:
            threshold = float(sys.argv[3])
        except ValueError:
            print(error("INVALID_ARG", "THRESHOLD must be a number", f"Received: {sys.argv[3]}"))
            sys.exit(1)
    print(get_news_for_date(sys.argv[1], sys.argv[2], threshold))
