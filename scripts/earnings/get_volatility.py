#!/usr/bin/env python3
"""
Calculate trailing adjusted volatility (stock - SPY).
Usage: python scripts/earnings/get_volatility.py TICKER START_DATE
       Uses 1 year before START_DATE for calculation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, parse_exception
load_env()

QUERY = """
MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE date(d.date) >= date($start) - duration('P365D') AND date(d.date) < date($start)
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE r.daily_return IS NOT NULL AND m.daily_return IS NOT NULL
RETURN stdev(r.daily_return - m.daily_return) AS adj_vol, count(*) AS days
"""

def get_volatility(ticker: str, start_date: str) -> str:
    with neo4j_session() as (session, err):
        if err: return err
        try:
            row = session.run(QUERY, ticker=ticker.upper(), start=start_date).single()
        except Exception as e:
            return parse_exception(e)
    if not row or row["days"] == 0:
        return error("NO_PRICE_DATA", f"No price data for {ticker} before {start_date}", "Check ticker or date")
    if row["days"] < 60:
        return error("INSUFFICIENT_HISTORY", f"{row['days']} days (need 60+)", "Data starts too late")
    return f"adj_vol|days\n{row['adj_vol']:.6f}|{row['days']}"

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(error("USAGE", "get_volatility.py TICKER START_DATE"))
        sys.exit(1)
    print(get_volatility(sys.argv[1], sys.argv[2]))
