#!/usr/bin/env python3
"""
Find significant moves: |stock| >= abs_floor AND |adj| >= max(sigma * vol, adj_floor)
Usage: get_significant_moves.py TICKER START END VOL [--abs X] [--adj X] [--sigma X]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, ok, parse_exception
load_env()

# Defaults
ABS_FLOOR, ADJ_FLOOR, SIGMA = 4.0, 3.0, 2.0

QUERY = """
MATCH (c:Company {ticker: $ticker})
MATCH (d:Date)-[r:HAS_PRICE]->(c)
WHERE date(d.date) >= date($start) AND date(d.date) < date($end)
  AND r.daily_return IS NOT NULL
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE m.daily_return IS NOT NULL
WITH d.date AS date, r.daily_return AS daily_stock, m.daily_return AS daily_macro,
     (r.daily_return - m.daily_return) AS daily_adj
WHERE abs(daily_stock) >= $abs_threshold AND abs(daily_adj) >= $adj_threshold
RETURN date, daily_stock, daily_macro, daily_adj
ORDER BY date
"""

def get_significant_moves(ticker: str, start: str, end: str, vol: float,
                          abs_floor: float = ABS_FLOOR, adj_floor: float = ADJ_FLOOR,
                          sigma: float = SIGMA) -> str:
    abs_t, adj_t = abs_floor, max(sigma * vol, adj_floor)
    with neo4j_session() as (session, err):
        if err: return err
        try:
            rows = [f"{r['date']}|{r['daily_stock']:.2f}|{r['daily_macro']:.2f}|{r['daily_adj']:.2f}"
                    for r in session.run(QUERY, ticker=ticker.upper(), start=start, end=end,
                                         abs_threshold=abs_t, adj_threshold=adj_t)]
        except Exception as e:
            return parse_exception(e)
    if not rows:
        return ok("NO_MOVES", f"0 moves (|stk|>={abs_t:.1f}%,|adj|>={adj_t:.1f}%) {ticker} {start}->{end}")
    return "date|daily_stock|daily_macro|daily_adj\n" + "\n".join(rows)

if __name__ == "__main__":
    a, opts = sys.argv[1:], {'abs': ABS_FLOOR, 'adj': ADJ_FLOOR, 'sigma': SIGMA}
    i = 4
    while i < len(a) - 1:
        if a[i] in ('--abs', '--adj', '--sigma'):
            opts[a[i][2:]] = float(a[i+1]); i += 2
        else: i += 1
    if len(a) < 4:
        print(error("USAGE", "get_significant_moves.py TICKER START END VOL [--abs X] [--adj X] [--sigma X]")); sys.exit(1)
    try:
        print(get_significant_moves(a[0], a[1], a[2], float(a[3]), opts['abs'], opts['adj'], opts['sigma']))
    except (ValueError, IndexError) as e:
        print(error("INVALID_ARG", str(e))); sys.exit(1)
