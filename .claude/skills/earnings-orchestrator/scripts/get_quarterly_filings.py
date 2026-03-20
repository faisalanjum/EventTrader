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

Validation: Filters out records where 10-Q/10-K is missing or stale (lag > 90 days from 8-K).

Fiscal year/quarter calculation:
- FYE (fiscal year end month) is derived from 10-K period months, NOT from stored database field
- Prefer matched filing XBRL fiscal year/period focus when available
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


from fiscal_math import period_to_fiscal, _normalize_fiscal_quarter, _compute_fiscal_dates


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


def parse_xbrl_fiscal_identity(xbrl_year_focus, xbrl_period_focus):
    """
    Parse SEC XBRL fiscal identity from dei facts when available.

    Returns:
        (fiscal_year: int, fiscal_quarter: str) or None when values are missing/invalid.
    """
    if xbrl_year_focus is None or xbrl_period_focus is None:
        return None

    year_str = str(xbrl_year_focus).strip()
    if not year_str.isdigit():
        return None

    period = str(xbrl_period_focus).strip().upper()
    if period == "FY":
        quarter = "Q4"
    elif period in {"Q1", "Q2", "Q3", "Q4"}:
        quarter = period
    else:
        return None

    return int(year_str), quarter


def should_use_xbrl_fiscal(fallback_fiscal, xbrl_fiscal) -> bool:
    """
    Use XBRL fiscal identity only when it is plausibly close to the period-based fallback.

    This preserves the retailer/year-convention fixes (typically year delta = 1 or quarter delta = 1)
    while filtering obvious bad-XBRL outliers documented in test_fiscal_rootcause.py.
    """
    if xbrl_fiscal is None:
        return False

    q_num = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    fallback_year, fallback_quarter = fallback_fiscal
    xbrl_year, xbrl_quarter = xbrl_fiscal

    year_diff = xbrl_year - fallback_year
    quarter_diff = q_num[xbrl_quarter] - q_num[fallback_quarter]
    return abs(year_diff) <= 1 and abs(quarter_diff) <= 1

# Matched 10-Q/10-K filings whose XBRL fiscal identity is known-bad and
# still leaks through should_use_xbrl_fiscal().  Keyed by periodic filing
# accession (accession_10q), never by ticker.
XBRL_DENY_PERIODIC_ACCESSIONS = {
    # AES: stale FY2022 Q2 leaks through proximity guard on 2023 Q1-Q3
    "0000874761-23-000039",
    "0000874761-23-000071",
    "0000874761-23-000080",
    # WMS: stale/repeated quarter labels that still pass the proximity guard
    "0001604028-23-000050",
    "0001604028-24-000005",
    "0001604028-25-000030",
    # URBN: FY2024 labels on FY2025 periods (yd=-1, qd=0 leaks)
    "0000950170-24-104783",
    "0000950170-24-134967",
}

# Maximum allowed lag (hours) between 8-K and 10-Q filing dates
# Normal lag is 0-7 days; up to 90 days covers slow filers (e.g. Q4 10-K filed 60-67 days after 8-K)
MAX_LAG_HOURS = 90 * 24  # 90 days in hours


QUERY = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker = $ticker AND r.formType = '8-K' AND r.items CONTAINS '2.02' AND pf.daily_stock IS NOT NULL
WITH r, c ORDER BY r.created ASC
// Get most recent 10-Q/10-K before this 8-K (by periodOfReport, not filing date)
OPTIONAL CALL (r, c) {
  MATCH (q:Report)-[:PRIMARY_FILER]->(c)
  WHERE q.formType IN ['10-Q', '10-K'] AND date(q.periodOfReport) < date(datetime(r.created))
  WITH q ORDER BY q.periodOfReport DESC LIMIT 1
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
  WITH q, collect(DISTINCT fp.value) AS xbrl_periods
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
  WITH q, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
  RETURN q,
         CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period_focus,
         CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year_focus
}
RETURN r.accessionNo AS accession_8k, r.created AS filed_8k, r.market_session AS market_session_8k,
       q.accessionNo AS accession_10q, q.created AS filed_10q, q.market_session AS market_session_10q,
       q.formType AS form_type, q.periodOfReport AS period_10q,
       xbrl_period_focus, xbrl_year_focus
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

                # Valid if 10-Q/10-K filed within -24h to +90 days of 8-K
                if -24 <= lag_hours <= MAX_LAG_HOURS:
                    valid_10q = True
                    secs = abs(int(lag_hours * 3600))
                    lag_str = f"{'-' if lag_hours < 0 else ''}{secs//86400}d{secs%86400//3600}h{secs%3600//60}m{secs%60}s"
            except Exception:
                pass  # Invalid lag calculation -> treat as invalid match

        if valid_10q:
            # Valid 10-Q/10-K match: prefer XBRL fiscal identity, fall back to period math.
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
            fallback_fiscal = period_to_fiscal(period_year, period_month, period_day, derived_fye, form_type)
            xbrl_fiscal = parse_xbrl_fiscal_identity(r["xbrl_year_focus"], r["xbrl_period_focus"])
            periodic_accession = (r["accession_10q"] or "").strip()
            if periodic_accession in XBRL_DENY_PERIODIC_ACCESSIONS:
                fiscal_year, fiscal_quarter = fallback_fiscal
            elif should_use_xbrl_fiscal(fallback_fiscal, xbrl_fiscal):
                fiscal_year, fiscal_quarter = xbrl_fiscal
            else:
                fiscal_year, fiscal_quarter = fallback_fiscal
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
            "lag_hours": lag_hours if valid_10q else 99999.0,
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
        for item in processed:
            key = item["fiscal_key"]
            if key not in seen or abs(item["lag_hours"]) < abs(seen[key]["lag_hours"]):
                seen[key] = item
        rows = [item["row"] for item in seen.values()]
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
