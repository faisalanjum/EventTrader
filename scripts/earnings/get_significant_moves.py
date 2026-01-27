#!/usr/bin/env python3
"""
Find dates with significant price moves (|daily_adj| >= threshold).
Usage: python scripts/earnings/get_significant_moves.py TICKER START END THRESHOLD
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

QUERY = """
MATCH (c:Company {ticker: $ticker})
WITH c
MATCH (d:Date)-[r:HAS_PRICE]->(c)
WHERE date(d.date) >= date($start) AND date(d.date) < date($end) AND r.daily_return IS NOT NULL
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE m.daily_return IS NOT NULL
WITH d.date AS date, r.daily_return AS daily_stock, m.daily_return AS daily_macro,
     (r.daily_return - m.daily_return) AS daily_adj
WHERE abs(daily_adj) >= $threshold
RETURN date, daily_stock, daily_macro, daily_adj
ORDER BY date ASC
"""

def get_significant_moves(ticker: str, start: str, end: str, threshold: float) -> str:
    if threshold <= 0:
        return error("INVALID_ARG", "threshold must be positive", f"Received: {threshold}")
    with neo4j_session() as (session, err):
        if err: return err
        try:
            rows = [f"{r['date']}|{r['daily_stock']:.2f}|{r['daily_macro']:.2f}|{r['daily_adj']:.2f}"
                    for r in session.run(QUERY, ticker=ticker.upper(), start=start, end=end, threshold=threshold)]
        except Exception as e:
            return parse_exception(e)
    if not rows:
        return ok("NO_MOVES", f"0 moves >= {threshold:.2f}% for {ticker} ({start} to {end})", "Try lower threshold or check ticker/dates")
    return "date|daily_stock|daily_macro|daily_adj\n" + "\n".join(rows)

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(error("USAGE", "get_significant_moves.py TICKER START END THRESHOLD"))
        sys.exit(1)
    try:
        threshold = float(sys.argv[4])
    except ValueError:
        print(error("INVALID_ARG", "THRESHOLD must be a number", f"Received: {sys.argv[4]}"))
        sys.exit(1)
    print(get_significant_moves(sys.argv[1], sys.argv[2], sys.argv[3], threshold))
