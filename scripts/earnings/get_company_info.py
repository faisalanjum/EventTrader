#!/usr/bin/env python3
"""
Get company metadata including fiscal year end.
Usage: python scripts/earnings/get_company_info.py TICKER
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, parse_exception
load_env()

QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)-[:BELONGS_TO]->(sec:Sector)
RETURN c.ticker AS ticker, c.name AS name, c.cik AS cik,
       c.fiscal_year_end_month AS fye_month, c.fiscal_year_end_day AS fye_day,
       c.sector AS sector, c.industry AS industry,
       ind.name AS industry_class, sec.name AS sector_class,
       c.exchange AS exchange, c.mkt_cap AS mkt_cap
"""

def get_company_info(ticker: str) -> str:
    with neo4j_session() as (session, err):
        if err: return err
        try:
            result = session.run(QUERY, ticker=ticker.upper()).single()
        except Exception as e:
            return parse_exception(e)
    if not result:
        return error("NO_DATA", f"Company not found: {ticker}", "Check ticker")

    # Build output
    lines = [
        f"ticker|{result['ticker'] or 'N/A'}",
        f"name|{result['name'] or 'N/A'}",
        f"cik|{result['cik'] or 'N/A'}",
        f"fye_month|{result['fye_month'] or 'N/A'}",
        f"fye_day|{result['fye_day'] or 'N/A'}",
        f"sector|{result['sector'] or result['sector_class'] or 'N/A'}",
        f"industry|{result['industry'] or result['industry_class'] or 'N/A'}",
        f"exchange|{result['exchange'] or 'N/A'}",
        f"mkt_cap|{result['mkt_cap'] or 'N/A'}",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(error("USAGE", "get_company_info.py TICKER"))
        sys.exit(1)
    print(get_company_info(sys.argv[1]))
