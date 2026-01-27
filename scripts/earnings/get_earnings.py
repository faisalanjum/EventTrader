#!/usr/bin/env python3
"""
Get 8-K earnings reports (Item 2.02) with trailing volatility.
Usage: python scripts/earnings/get_earnings.py TICKER
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, fmt, vol_status, parse_exception, calculate_fiscal_period
load_env()

QUERY = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker = $ticker AND r.formType = '8-K' AND r.items CONTAINS '2.02' AND pf.daily_stock IS NOT NULL
WITH r, pf, c ORDER BY r.created ASC
CALL (r, c) {
  MATCH (d:Date)-[pr:HAS_PRICE]->(c)
  WHERE date(d.date) >= date(datetime(r.created)) - duration('P365D') AND date(d.date) < date(datetime(r.created))
  MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
  WHERE pr.daily_return IS NOT NULL AND m.daily_return IS NOT NULL
  RETURN stdev(pr.daily_return - m.daily_return) AS trailing_vol, count(*) AS vol_days
}
RETURN r.accessionNo AS accession, r.created AS date, r.periodOfReport AS period,
       r.market_session AS market_session,
       pf.daily_stock AS daily_stock, (pf.daily_stock - pf.daily_macro) AS daily_adj,
       (pf.daily_stock - pf.daily_sector) AS sector_adj, (pf.daily_stock - pf.daily_industry) AS industry_adj,
       trailing_vol, vol_days,
       c.fiscal_year_end_month AS fye_month, c.fiscal_year_end_day AS fye_day
ORDER BY r.created ASC
"""

def get_earnings(ticker: str) -> str:
    with neo4j_session() as (session, err):
        if err: return err
        try:
            results = list(session.run(QUERY, ticker=ticker.upper()))
        except Exception as e:
            return parse_exception(e)

    if not results:
        return error("NO_DATA", f"No earnings (8-K 2.02) for {ticker}", "Check ticker or data availability")

    rows = []
    for r in results:
        period = r["period"] or "N/A"
        fye_month = r["fye_month"]
        fye_day = r["fye_day"]

        # Calculate fiscal year and quarter
        if period != "N/A" and fye_month and fye_day:
            fy, fq = calculate_fiscal_period(period, fye_month, fye_day)
            fiscal_year = str(fy)
            fiscal_quarter = fq
        else:
            fiscal_year = "N/A"
            fiscal_quarter = "N/A"

        rows.append("|".join([
            r["accession"] or "N/A",
            r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
            fiscal_year,
            fiscal_quarter,
            r["market_session"] or "N/A",
            fmt(r["daily_stock"]), fmt(r["daily_adj"]), fmt(r["sector_adj"]), fmt(r["industry_adj"]),
            fmt(r["trailing_vol"], 6), str(r["vol_days"] or 0), vol_status(r["vol_days"])
        ]))

    return "accession|date|fiscal_year|fiscal_quarter|market_session|daily_stock|daily_adj|sector_adj|industry_adj|trailing_vol|vol_days|vol_status\n" + "\n".join(rows)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(error("USAGE", "get_earnings.py TICKER"))
        sys.exit(1)
    print(get_earnings(sys.argv[1]))
