#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "neo4j>=5.0.0",
#   "python-dotenv>=1.0.0",
# ]
# ///

"""
Get 8-K earnings reports with matched 10-Q/10-K filings.
Usage: ./get_quarterly_filings.py TICKER [--all]

Matches each 8-K to the most recent 10-Q/10-K by periodOfReport before the 8-K filing date.
This is deterministic: the 10-Q/10-K represents the quarter whose results the 8-K announces.

Validation: Filters out records where 10-Q/10-K is missing or stale (lag > 45 days from 8-K).

Fiscal year/quarter calculation:
- FYE (fiscal year end month) is derived from 10-K period months, NOT from stored database field
- 10-K = Q4 (always), 10-Q = Q1/Q2/Q3
- Fiscal year = period.year + 1 if period_month > fye_month, else period.year
"""
import os
import sys
from datetime import datetime, date, timedelta
import calendar
from contextlib import contextmanager
from dotenv import load_dotenv
from neo4j import GraphDatabase

# --- Inlined from utils.py (exact same logic) ---
load_dotenv("/home/faisal/EventMarketDB/.env", override=True)

# Lightweight in-process caches for repeated period resolution calls.
_FYE_CACHE = {}
_PERIOD_SCAN_CACHE = {}

def error(code: str, msg: str, hint: str = "") -> str:
    return f"ERROR|{code}|{msg}|{hint}" if hint else f"ERROR|{code}|{msg}"

def parse_exception(e: Exception, uri: str = "") -> str:
    err_str = str(e).lower()
    if "connection" in err_str or "unavailable" in err_str or "refused" in err_str:
        return error("CONNECTION", "Database unavailable", f"Check Neo4j at {uri}")
    return error(type(e).__name__, str(e))

@contextmanager
def neo4j_session():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:30687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        yield None, error("CONFIG", "NEO4J_PASSWORD not set")
        return
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            yield session, None
        driver.close()
    except Exception as e:
        yield None, parse_exception(e, uri)
# --- End inlined utils ---


def period_to_fiscal(period_year: int, period_month: int, period_day: int, fye_month: int, form_type: str) -> tuple:
    """
    Calculate fiscal year and quarter from 10-Q/10-K period.

    Derived from empirical analysis of actual SEC filings:
    - 10-K is ALWAYS Q4 (annual report)
    - 10-Q is ALWAYS Q1, Q2, or Q3 (quarterly reports)
    - FYE month is derived from 10-K period months (ground truth)

    Week-based fiscal calendar adjustment:
    Companies using 52/53-week calendars (e.g., Apple, retail) have quarter-end
    dates that fall in the first 1-5 days of the next calendar month. For example,
    Apple's Q2 (March quarter) might end on April 1. If we use April to calculate,
    we get Q3 (wrong). The fix: if period_day <= 5, treat it as end of previous month.

    Remaining edge cases (unfixable with formula):
    - AAP (Advance Auto Parts): Extreme 52-week calendar, quarters shift by 2-3 weeks
    - ACI (Albertsons): Extreme 52-week calendar, quarters shift by 2-3 weeks
    These companies' fiscal quarters don't align with calendar months at all.
    The dedupe logic handles these by keeping first/last occurrence per fiscal_key.

    SEC XBRL metadata anomaly (not our bug):
    - ESTC (Elastic): Filing 0001707753-24-000038 (period 2024-07-31) has
      DocumentFiscalPeriodFocus="FY" instead of "Q1". Our Q1 calculation is correct
      (July is 3 months after April FYE). The exhibit filename confirms Q1 (a25q1ex311.htm).

    Validation: 549 filings across 73 companies checked against SEC's DocumentFiscalPeriodFocus.
    Match rate: 99.1% (544/549). Only mismatches: ACI (4, known edge case), ESTC (1, SEC error).

    Args:
        period_year: Year of period end date
        period_month: Month of period end date (1-12)
        period_day: Day of period end date (1-31)
        fye_month: Fiscal year end month derived from 10-K periods
        form_type: "10-K" or "10-Q"

    Returns:
        (fiscal_year: int, fiscal_quarter: str)
    """
    # Handle week-based fiscal calendars: if period ends in first 5 days,
    # it's the END of previous month's quarter, not the start of next month
    if period_day <= 5:
        adjusted_month = period_month - 1 if period_month > 1 else 12
        adjusted_year = period_year - 1 if period_month == 1 else period_year
    else:
        adjusted_month = period_month
        adjusted_year = period_year

    # RULE 1: 10-K is always Q4
    if form_type == '10-K':
        return adjusted_year, "Q4"

    # RULE 2: For 10-Q, calculate Q1/Q2/Q3
    months_after_fye = (adjusted_month - fye_month) % 12
    if months_after_fye == 0:
        months_after_fye = 12  # Edge case: period month == fye month for 10-Q

    if months_after_fye <= 3:
        quarter = 1
    elif months_after_fye <= 6:
        quarter = 2
    else:
        quarter = 3  # 10-Q is never Q4 by definition

    # RULE 3: Fiscal year - if past FYE month, we're in next fiscal year
    if adjusted_month > fye_month:
        fiscal_year = adjusted_year + 1
    else:
        fiscal_year = adjusted_year

    return fiscal_year, f"Q{quarter}"


def _normalize_fiscal_quarter(fiscal_quarter) -> str:
    """Normalize fiscal quarter input to one of: Q1, Q2, Q3, Q4, FY."""
    fq_raw = str(fiscal_quarter).strip().upper()
    if fq_raw in {"1", "Q1"}:
        return "Q1"
    if fq_raw in {"2", "Q2"}:
        return "Q2"
    if fq_raw in {"3", "Q3"}:
        return "Q3"
    if fq_raw in {"4", "Q4"}:
        return "Q4"
    if fq_raw in {"FY", "ANNUAL", "YEAR"}:
        return "FY"
    raise ValueError(f"Unsupported fiscal_quarter: {fiscal_quarter!r}")


def _compute_fiscal_dates(fye_month: int, fiscal_year: int, fiscal_quarter: str) -> tuple:
    """
    Pure deterministic fiscal→calendar computation from FYE month.
    No database needed. Gives standard month boundaries.

    Args:
        fye_month: Fiscal year end month (1-12)
        fiscal_year: e.g. 2025
        fiscal_quarter: "Q1", "Q2", "Q3", "Q4", or "FY"

    Returns:
        (start_date: str, end_date: str) in "YYYY-MM-DD" format
    """
    fq = _normalize_fiscal_quarter(fiscal_quarter)
    fy_start_month = (fye_month % 12) + 1
    fy_start_year = fiscal_year if fye_month == 12 else fiscal_year - 1

    if fq == "FY":
        start = date(fy_start_year, fy_start_month, 1)
        _, last_day = calendar.monthrange(fiscal_year, fye_month)
        end = date(fiscal_year, fye_month, last_day)
        return start.isoformat(), end.isoformat()

    quarter_num = int(fq[1])

    q_start_month = fy_start_month + (quarter_num - 1) * 3
    q_start_year = fy_start_year
    while q_start_month > 12:
        q_start_month -= 12
        q_start_year += 1

    q_end_month = q_start_month + 2
    q_end_year = q_start_year
    while q_end_month > 12:
        q_end_month -= 12
        q_end_year += 1

    _, last_day = calendar.monthrange(q_end_year, q_end_month)
    return date(q_start_year, q_start_month, 1).isoformat(), date(q_end_year, q_end_month, last_day).isoformat()


def fiscal_to_dates(session, ticker: str, fiscal_year: int, fiscal_quarter: str) -> tuple:
    """
    Resolve fiscal label → calendar dates.

    Phase 1: Lookup existing XBRL Period nodes for this company,
             classify each via period_to_fiscal(), return exact dates if match found.
             Best for 52/53-week calendars where dates don't align to month boundaries.
    Phase 2: Deterministic fallback via _compute_fiscal_dates() for future periods
             not yet in XBRL. Uses standard month boundaries.

    Args:
        session: Neo4j session
        ticker: Company ticker
        fiscal_year: e.g. 2025
        fiscal_quarter: "Q1", "Q2", "Q3", "Q4", or "FY"

    Returns:
        (start_date: str, end_date: str) in "YYYY-MM-DD" format
    """
    ticker = ticker.upper()
    if ticker in _FYE_CACHE:
        fye_month = _FYE_CACHE[ticker]
    else:
        fye_month = get_derived_fye(session, ticker)
        _FYE_CACHE[ticker] = fye_month
    fq = _normalize_fiscal_quarter(fiscal_quarter)
    fiscal_year = int(fiscal_year)

    fallback_start_str, fallback_end_str = _compute_fiscal_dates(fye_month, fiscal_year, fq)
    fallback_start = date.fromisoformat(fallback_start_str)
    fallback_end = date.fromisoformat(fallback_end_str)
    expected_days = (fallback_end - fallback_start).days + 1

    # Phase 1: Lookup from existing XBRL Period nodes (ground truth for 52/53-week calendars)
    cache_key = (ticker, fye_month)
    periods = _PERIOD_SCAN_CACHE.get(cache_key)
    if periods is None:
        rows = list(session.run("""
            MATCH (co:Company {ticker: $ticker})<-[:FOR_COMPANY]-(ctx:Context)-[:HAS_PERIOD]->(p:Period)
            WHERE p.period_type = 'duration'
              AND p.start_date IS NOT NULL
              AND p.end_date IS NOT NULL
              AND (ctx.u_id IS NULL OR NOT ctx.u_id STARTS WITH 'guidance_')
            RETURN DISTINCT p.u_id AS u_id, p.start_date AS s, p.end_date AS e
        """, ticker=ticker))

        periods = []
        for r in rows:
            try:
                s = date.fromisoformat(r["s"])
                e = date.fromisoformat(r["e"])
            except (TypeError, ValueError):
                continue
            if e < s:
                continue
            days = (e - s).days + 1
            fy_10q, fq_10q = period_to_fiscal(e.year, e.month, e.day, fye_month, "10-Q")
            fy_10k, fq_10k = period_to_fiscal(e.year, e.month, e.day, fye_month, "10-K")
            periods.append({
                "u_id": r["u_id"],
                "s": s,
                "e": e,
                "days": days,
                "fy_10q": fy_10q,
                "fq_10q": fq_10q,
                "fy_10k": fy_10k,
                "fq_10k": fq_10k,
            })
        _PERIOD_SCAN_CACHE[cache_key] = periods

    quarter_like = [p for p in periods if 75 <= p["days"] <= 120]
    year_like = [p for p in periods if 340 <= p["days"] <= 380]

    def pick_best(candidates):
        if not candidates:
            return None
        # Deterministic tie-break: nearest to fallback dates, then nearest duration, then latest end.
        return min(
            candidates,
            key=lambda p: (
                abs((p["e"] - fallback_end).days),
                abs((p["s"] - fallback_start).days),
                abs(p["days"] - expected_days),
                -p["e"].toordinal(),
                p["u_id"] or "",
            ),
        )

    # FY lookup
    if fq == "FY":
        fy_candidates = [p for p in year_like if p["fy_10k"] == fiscal_year]
        best = pick_best(fy_candidates)
        if best:
            return best["s"].isoformat(), best["e"].isoformat()

    # Q1/Q2/Q3 lookup
    if fq in {"Q1", "Q2", "Q3"}:
        q_candidates = [
            p for p in quarter_like
            if p["fy_10q"] == fiscal_year and p["fq_10q"] == fq
        ]
        best = pick_best(q_candidates)
        if best:
            return best["s"].isoformat(), best["e"].isoformat()

    # Q4 lookup:
    # 1) try quarter-like periods ending on FY end date
    # 2) else derive from (Q3 end + 1 day) to FY end if both exist
    if fq == "Q4":
        fy_candidates = [p for p in year_like if p["fy_10k"] == fiscal_year]
        best_fy = pick_best(fy_candidates)
        if best_fy:
            q4_candidates = [
                p for p in quarter_like
                if p["e"] == best_fy["e"] and p["s"] >= best_fy["s"]
            ]
            best_q4 = pick_best(q4_candidates)
            if best_q4:
                return best_q4["s"].isoformat(), best_q4["e"].isoformat()

            q3_candidates = [
                p for p in quarter_like
                if p["fy_10q"] == fiscal_year and p["fq_10q"] == "Q3" and p["e"] < best_fy["e"]
            ]
            if q3_candidates:
                # Pick Q3 closest to expected Q3 end (not latest — period_to_fiscal
                # can misclassify Q4 as Q3, and max(end) would pick the wrong one)
                _, exp_q3_end_str = _compute_fiscal_dates(fye_month, fiscal_year, "Q3")
                exp_q3_end = date.fromisoformat(exp_q3_end_str)
                q3 = min(q3_candidates, key=lambda p: abs((p["e"] - exp_q3_end).days))
                q4_start = q3["e"] + timedelta(days=1)
                q4_end = best_fy["e"]
                q4_days = (q4_end - q4_start).days
                if q4_start <= q4_end and q4_days >= 60:
                    return q4_start.isoformat(), q4_end.isoformat()

            # If no clean Q3/Q4 quarter candidates exist, still anchor Q4 to FY end.
            # Infer quarter length from available quarter-like periods in same FY,
            # else from FY length / 4.
            same_fy_quarters = [
                p["days"] for p in quarter_like
                if p["s"] >= best_fy["s"] and p["e"] <= best_fy["e"]
            ]
            if same_fy_quarters:
                q_len = round(sum(same_fy_quarters) / len(same_fy_quarters))
            else:
                q_len = round(best_fy["days"] / 4)
            q_len = max(75, min(120, q_len))

            q4_end = best_fy["e"]
            q4_start = q4_end - timedelta(days=q_len - 1)
            if q4_start < best_fy["s"]:
                q4_start = best_fy["s"]
            return q4_start.isoformat(), q4_end.isoformat()

    # Phase 2: Deterministic fallback for missing/future periods
    out_start, out_end = fallback_start_str, fallback_end_str

    # Round-trip guard on fallback output
    out_end_date = date.fromisoformat(out_end)
    form_type = "10-K" if fq in {"Q4", "FY"} else "10-Q"
    rfy, rfq = period_to_fiscal(out_end_date.year, out_end_date.month, out_end_date.day, fye_month, form_type)
    if rfy != fiscal_year:
        raise ValueError(
            f"fiscal_to_dates round-trip year mismatch for {ticker} {fiscal_year} {fq}: got {rfy} {rfq}"
        )
    if fq in {"Q1", "Q2", "Q3"} and rfq != fq:
        raise ValueError(
            f"fiscal_to_dates round-trip quarter mismatch for {ticker} {fiscal_year} {fq}: got {rfy} {rfq}"
        )

    return out_start, out_end


def get_derived_fye(session, ticker: str) -> int:
    """
    Derive fiscal year end month from company's 10-K filing periods.

    This is the ground truth - actual 10-K periods, not stored database field.
    Returns 12 (December) as default if no 10-K data available.
    """
    result = session.run("""
        MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
        WHERE r.formType = '10-K' AND r.periodOfReport IS NOT NULL
        WITH date(r.periodOfReport).month AS m, count(*) AS cnt
        RETURN m ORDER BY cnt DESC LIMIT 1
    """, ticker=ticker)
    row = result.single()
    return row['m'] if row else 12  # Default to December if no 10-K data

# Maximum allowed lag (hours) between 8-K and 10-Q filing dates
# Normal lag is 0-7 days; >45 days indicates missing 10-Q data
MAX_LAG_HOURS = 45 * 24  # 45 days in hours

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
    'JBLU', 'KSS',
    'LII', 'LNC', 'LUV', 'LYV',
    'MAA', 'MASI', 'MDT', 'MET', 'MKTX', 'MMM', 'MOS', 'MPW', 'MPWR', 'MRCY', 'MTCH', 'MTW', 'MUR',
    'NBR', 'NCNO', 'NDAQ', 'NSC', 'NSP', 'NTNX', 'NUE', 'NWL',
    'O', 'OLLI', 'OLN', 'OMCL', 'OVV', 'OXM',
    'PANW', 'PATH', 'PFGC', 'PH', 'PHM', 'PHR', 'PK', 'PLAY', 'PLNT', 'PLTK', 'POR', 'PTEN', 'PX',
    'RBLX', 'RGA', 'RGEN', 'RIVN', 'RKLB', 'RSG', 'RVLV',
    'S', 'SFM', 'SHAK', 'SHLS', 'SNAP', 'SONO', 'SPR', 'SPT', 'SRE', 'SSTK', 'STT', 'SWK',
    'TEAM', 'TECH', 'TEX', 'TFX', 'TNDM', 'TREE', 'TROW', 'TRU', 'TSLA', 'TTD', 'TWST',
    'UPS', 'UTHR', 'VFC', 'VICI', 'VNO',
    'WAT', 'WHR', 'WLK', 'WMG', 'WMS', 'WSO', 'ZS',
}

QUERY = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker = $ticker AND r.formType = '8-K' AND r.items CONTAINS '2.02' AND pf.daily_stock IS NOT NULL
WITH r, c ORDER BY r.created ASC
// Get most recent 10-Q/10-K before this 8-K (by periodOfReport, not filing date)
OPTIONAL CALL (r, c) {
  MATCH (q:Report)-[:PRIMARY_FILER]->(c)
  WHERE q.formType IN ['10-Q', '10-K'] AND date(q.periodOfReport) < date(datetime(r.created))
  RETURN q ORDER BY q.periodOfReport DESC LIMIT 1
}
RETURN r.accessionNo AS accession_8k, r.created AS filed_8k, r.market_session AS market_session_8k,
       q.accessionNo AS accession_10q, q.created AS filed_10q, q.market_session AS market_session_10q,
       q.formType AS form_type, q.periodOfReport AS period_10q
ORDER BY r.created ASC
"""

def get_earnings_with_10q(ticker: str, dedupe: bool = True) -> str:
    with neo4j_session() as (session, err):
        if err: return err
        try:
            # First, derive actual FYE from 10-K periods (ground truth)
            derived_fye = get_derived_fye(session, ticker.upper())
            results = list(session.run(QUERY, ticker=ticker.upper()))
        except Exception as e:
            return parse_exception(e)

    if not results:
        return error("NO_DATA", f"No earnings (8-K 2.02) for {ticker}", "Check ticker or data availability")

    processed = []

    for r in results:
        filed_8k = r["filed_8k"]
        filed_10q = r["filed_10q"]
        period_10q = r["period_10q"]

        # 8-K fields (always present)
        filed_8k_str = filed_8k.isoformat() if hasattr(filed_8k, "isoformat") else str(filed_8k) if filed_8k else "N/A"
        market_session_8k = r["market_session_8k"] or "N/A"

        # Check if 10-Q match is valid
        valid_10q = False
        if period_10q and filed_10q:
            try:
                dt_8k = filed_8k if hasattr(filed_8k, 'timestamp') else datetime.fromisoformat(str(filed_8k).replace('Z', '+00:00'))
                dt_10q = filed_10q if hasattr(filed_10q, 'timestamp') else datetime.fromisoformat(str(filed_10q).replace('Z', '+00:00'))

                # Handle neo4j DateTime objects
                if hasattr(dt_8k, 'to_native'):
                    dt_8k = dt_8k.to_native()
                if hasattr(dt_10q, 'to_native'):
                    dt_10q = dt_10q.to_native()

                lag_hours = (dt_10q - dt_8k).total_seconds() / 3600

                # Valid if 10-Q filed within -24h to +45 days of 8-K
                if -24 <= lag_hours <= MAX_LAG_HOURS:
                    valid_10q = True
                    secs = abs(int(lag_hours * 3600))
                    lag_str = f"{'-' if lag_hours < 0 else ''}{secs//86400}d{secs%86400//3600}h{secs%3600//60}m{secs%60}s"
            except Exception:
                pass  # Invalid lag calculation -> treat as invalid match

        if valid_10q:
            # Valid 10-Q match: calculate fiscal year/quarter
            filed_10q_str = filed_10q.isoformat() if hasattr(filed_10q, "isoformat") else str(filed_10q)

            if hasattr(period_10q, 'year'):
                period_year = period_10q.year
                period_month = period_10q.month
                period_day = period_10q.day
            else:
                period_str = str(period_10q)[:10]
                period_date = date.fromisoformat(period_str)
                period_year = period_date.year
                period_month = period_date.month
                period_day = period_date.day

            form_type = r["form_type"] or "10-Q"
            fiscal_year, fiscal_quarter = period_to_fiscal(period_year, period_month, period_day, derived_fye, form_type)
            fiscal_year = str(fiscal_year)

            accession_10q = r["accession_10q"] or "N/A"
            market_session_10q = r["market_session_10q"] or "N/A"
            form_type = r["form_type"] or "N/A"
        else:
            # Invalid 10-Q match: set 10-Q fields to N/A
            accession_10q = "N/A"
            filed_10q_str = "N/A"
            market_session_10q = "N/A"
            form_type = "N/A"
            fiscal_year = "N/A"
            fiscal_quarter = "N/A"
            lag_str = "N/A"

        # Use 8-K accession as fiscal_key for N/A rows so they aren't deduped
        fiscal_key = r["accession_8k"] if fiscal_year == "N/A" else f"{fiscal_year}_{fiscal_quarter}"

        processed.append({
            "fiscal_key": fiscal_key,
            "row": "|".join([
                r["accession_8k"] or "N/A",
                filed_8k_str,
                market_session_8k,
                accession_10q,
                filed_10q_str,
                market_session_10q,
                form_type,
                fiscal_year,
                fiscal_quarter,
                lag_str,
            ])
        })

    if dedupe:
        seen = {}
        use_first = ticker.upper() in USE_FIRST_TICKERS
        for item in processed:
            key = item["fiscal_key"]
            if use_first:
                if key not in seen:
                    seen[key] = item["row"]
            else:
                seen[key] = item["row"]
        rows = list(seen.values())
    else:
        rows = [item["row"] for item in processed]

    return "accession_8k|filed_8k|market_session_8k|accession_10q|filed_10q|market_session_10q|form_type|fiscal_year|fiscal_quarter|lag\n" + "\n".join(rows)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(error("USAGE", "get_quarterly_filings.py TICKER [--all]"))
        sys.exit(1)

    output = get_earnings_with_10q(sys.argv[1], dedupe="--all" not in sys.argv)

    import subprocess
    result = subprocess.run(['column', '-t', '-s', '|'], input=output, text=True, capture_output=True)
    print(result.stdout.rstrip())
