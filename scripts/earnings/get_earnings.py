#!/usr/bin/env python3
"""
Get 8-K earnings reports (Item 2.02) with trailing volatility.
Usage: python scripts/earnings/get_earnings.py TICKER [--all]

By default, returns only the actual earnings release per quarter (last 8-K 2.02 per fiscal quarter).
Use --all to return all 8-K 2.02 filings including preliminary updates.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.earnings.utils import load_env, neo4j_session, error, fmt, vol_status, parse_exception, calculate_fiscal_period
load_env()

# Companies where FIRST filing per quarter is the actual earnings (not LAST)
# Based on content analysis: FIRST contains "Results" more often than LAST
# Total: 183 companies
USE_FIRST_TICKERS = {
    'ADI', 'ADSK', 'AEE', 'AFL', 'AI', 'AJG', 'ALGT', 'ALK', 'ALSN', 'ALT', 'AMD', 'AME', 'AMRC', 'AMZN', 'APO',
    'BAH', 'BDX', 'BFAM', 'BILL', 'BLDR', 'BLMN', 'BOOT', 'BRBR', 'BSY', 'BWA',
    'CAKE', 'CARG', 'CAT', 'CC', 'CDLX', 'CDW', 'CGNX', 'CHGG', 'CHRW', 'CHWY', 'CIEN', 'CLX', 'CMCSA', 'COUR', 'CPB', 'CSTL', 'CTVA', 'CVNA', 'CWH',
    'DAL', 'DAN', 'DAR', 'DASH', 'DGX', 'DKS', 'DOCU', 'DOMO', 'DRI', 'DT', 'DV', 'DVN', 'DY',
    'ECL', 'EMN', 'ENPH', 'EPAM', 'ESTC', 'ETSY', 'EVER', 'EW', 'EXPE', 'EYE',
    'FCPT', 'FDS', 'FE', 'FLYW', 'FMC', 'FNKO', 'FRPT', 'FRSH', 'FSLY', 'FUN',
    'GDRX', 'GKOS', 'GLW', 'GM', 'GMS',
    'HAIN', 'HCAT', 'HII', 'HPP', 'HRMY', 'HUM', 'HXL',
    'IBM', 'IEX', 'IIPR', 'INTU', 'IRTC', 'ISRG',
    'JBLU',
    'KSS',
    'LII', 'LNC', 'LUV', 'LYV',
    'MAA', 'MASI', 'MDT', 'MET', 'MKTX', 'MMM', 'MOS', 'MPW', 'MPWR', 'MRCY', 'MTCH', 'MTW', 'MUR',
    'NBR', 'NCNO', 'NDAQ', 'NSC', 'NSP', 'NTNX', 'NUE', 'NWL',
    'O', 'OLLI', 'OLN', 'OMCL', 'OVV', 'OXM',
    'PANW', 'PATH', 'PFGC', 'PH', 'PHM', 'PHR', 'PK', 'PLAY', 'PLNT', 'PLTK', 'POR', 'PTEN', 'PX',
    'RBLX', 'RGA', 'RGEN', 'RIVN', 'RKLB', 'RSG', 'RVLV',
    'S', 'SFM', 'SHAK', 'SHLS', 'SNAP', 'SONO', 'SPR', 'SPT', 'SRE', 'SSTK', 'STT', 'SWK',
    'TEAM', 'TECH', 'TEX', 'TFX', 'TNDM', 'TREE', 'TROW', 'TRU', 'TSLA', 'TTD', 'TWST',
    'UPS', 'UTHR',
    'VFC', 'VICI', 'VNO',
    'WAT', 'WHR', 'WLK', 'WMG', 'WMS', 'WSO',
    'ZS',
}

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

def get_earnings(ticker: str, dedupe: bool = True) -> str:
    """
    Get 8-K earnings reports for a ticker.

    Args:
        ticker: Company ticker symbol
        dedupe: If True (default), keep only the last 8-K 2.02 per fiscal quarter
                (the actual earnings release, not preliminary updates).
                If False, return all 8-K 2.02 filings.
    """
    with neo4j_session() as (session, err):
        if err: return err
        try:
            results = list(session.run(QUERY, ticker=ticker.upper()))
        except Exception as e:
            return parse_exception(e)

    if not results:
        return error("NO_DATA", f"No earnings (8-K 2.02) for {ticker}", "Check ticker or data availability")

    # Process all results first
    processed = []
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

        processed.append({
            "fiscal_key": f"{fiscal_year}_{fiscal_quarter}",
            "row": "|".join([
                r["accession"] or "N/A",
                r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
                fiscal_year,
                fiscal_quarter,
                r["market_session"] or "N/A",
                fmt(r["daily_stock"]), fmt(r["daily_adj"]), fmt(r["sector_adj"]), fmt(r["industry_adj"]),
                fmt(r["trailing_vol"], 6), str(r["vol_days"] or 0), vol_status(r["vol_days"])
            ])
        })

    # Dedupe: keep only one filing per fiscal quarter
    if dedupe:
        seen = {}
        use_first = ticker.upper() in USE_FIRST_TICKERS
        for item in processed:
            key = item["fiscal_key"]
            if use_first:
                # Keep FIRST per quarter (don't overwrite if already seen)
                if key not in seen:
                    seen[key] = item["row"]
            else:
                # Keep LAST per quarter (later items overwrite earlier ones)
                seen[key] = item["row"]
        rows = list(seen.values())
    else:
        rows = [item["row"] for item in processed]

    return "accession|date|fiscal_year|fiscal_quarter|market_session|daily_stock|daily_adj|sector_adj|industry_adj|trailing_vol|vol_days|vol_status\n" + "\n".join(rows)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(error("USAGE", "get_earnings.py TICKER [--all]"))
        sys.exit(1)

    ticker = sys.argv[1]
    dedupe = "--all" not in sys.argv
    print(get_earnings(ticker, dedupe=dedupe))
