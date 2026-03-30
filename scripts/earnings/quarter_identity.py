#!/usr/bin/env python3
"""Quarter identity resolver — single canonical source of truth.

Given an 8-K accession, resolves the full quarter_info dict that all
builder adapters expect. One Neo4j query, deterministic fiscal math,
XBRL-preferred labeling.

Usage:
    from quarter_identity import resolve_quarter_info
    qi = resolve_quarter_info("CRM", "0001108524-25-000002")

    # Or with an existing Neo4j session:
    qi = resolve_quarter_info("CRM", "0001108524-25-000002", session=session)
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))

from fiscal_math import period_to_fiscal, _compute_fiscal_dates
from fye_month import get_fye_month
from get_quarterly_filings import (
    parse_xbrl_fiscal_identity,
    should_use_xbrl_fiscal,
    XBRL_DENY_PERIODIC_ACCESSIONS,
)

# Max days between period_of_report and filed_8k before flagging stale match
_STALE_MATCH_DAYS = 150

# ── Single query: 8-K metadata + matched periodic + XBRL + FYE + prev 8-K ──

_QUERY = """
MATCH (r:Report {accessionNo: $accession})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K' AND r.items CONTAINS '2.02'
WITH r, c

OPTIONAL CALL (r, c) {
  MATCH (q:Report)-[:PRIMARY_FILER]->(c)
  WHERE q.formType IN ['10-Q', '10-K'] AND date(q.periodOfReport) < date(datetime(r.created))
  WITH q ORDER BY q.periodOfReport DESC LIMIT 1
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
  WITH q, collect(DISTINCT fp.value) AS xbrl_periods
  OPTIONAL MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
  WITH q, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
  RETURN q.accessionNo AS accession_periodic,
         q.periodOfReport AS period_of_report,
         q.formType AS form_type_periodic,
         CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period,
         CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year
}

OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}

OPTIONAL CALL (r, c) {
  MATCH (prev:Report)-[:PRIMARY_FILER]->(c)
  WHERE prev.formType = '8-K' AND prev.items CONTAINS '2.02'
        AND datetime(prev.created) < datetime(r.created)
  RETURN prev.created AS prev_8k_ts
  ORDER BY datetime(prev.created) DESC LIMIT 1
}

RETURN r.created AS filed_8k,
       r.market_session AS market_session,
       period_of_report, form_type_periodic, accession_periodic,
       xbrl_period, xbrl_year,
       fye_month,
       prev_8k_ts
"""


def _to_str(val) -> str | None:
    """Convert Neo4j value to ISO string."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _map_event_to_quarter_end(filed_8k_str: str, fye_month: int) -> tuple[str, int, str] | None:
    """Derive quarter-end date from 8-K filing date + FYE month.

    Live-safe: no dependency on future filings. Uses fiscal_math to generate
    quarter-end dates, finds the nearest one within a reasonable window.
    Handles COST-style early reporters via 7-day forward window.

    Returns: (period_of_report, fiscal_year, fiscal_quarter) or None.
    """
    try:
        filed_date = date.fromisoformat(str(filed_8k_str)[:10])
    except (ValueError, TypeError):
        return None

    best = None
    best_gap = None
    for fy in range(filed_date.year - 1, filed_date.year + 2):
        for q_label in ("Q1", "Q2", "Q3", "Q4"):
            _, end_str = _compute_fiscal_dates(fye_month, fy, q_label)
            end_date = date.fromisoformat(end_str)
            # filed_8k is typically 20-90 days after quarter-end.
            # Allow -7 (COST early reporters) to +120 days.
            gap = (filed_date - end_date).days
            if -7 <= gap <= 120:
                if best_gap is None or gap < best_gap:
                    best_gap = gap
                    best = (end_str, fy, q_label)

    return best


def _resolve_fiscal_label(period_of_report: str, form_type: str,
                          fye_month: int, accession_periodic: str,
                          xbrl_year, xbrl_period) -> tuple[int, str]:
    """XBRL-preferred fiscal label with denylist + proximity guard.

    Same cascade as build_prior_financials._get_fiscal_labels() and
    get_quarterly_filings.get_earnings_with_10q().
    """
    d = date.fromisoformat(period_of_report[:10])
    base_form = (form_type or "10-Q").replace("/A", "")

    fallback = period_to_fiscal(d.year, d.month, d.day, fye_month, base_form)
    xbrl = parse_xbrl_fiscal_identity(xbrl_year, xbrl_period)

    if accession_periodic and accession_periodic in XBRL_DENY_PERIODIC_ACCESSIONS:
        return fallback
    if should_use_xbrl_fiscal(fallback, xbrl):
        return xbrl
    return fallback


def resolve_quarter_info(ticker: str, accession_8k: str, *,
                         session=None) -> dict:
    """Resolve canonical quarter_info from an 8-K accession.

    Returns:
        {accession_8k, filed_8k, market_session, period_of_report,
         prev_8k_ts, quarter_label, form_type_periodic, accession_periodic,
         fye_month, quarter_identity_source, gaps}
    """
    ticker = ticker.upper()
    gaps = []

    # ── Query ──
    if session is not None:
        row = session.run(_QUERY, accession=accession_8k, ticker=ticker).single()
    else:
        from dotenv import load_dotenv
        from neo4j import GraphDatabase
        load_dotenv(str(_PROJECT_ROOT / ".env"), override=True)
        uri = os.getenv("NEO4J_URI", "bolt://localhost:30687")
        user = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise RuntimeError("NEO4J_PASSWORD not set")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            with driver.session() as s:
                row = s.run(_QUERY, accession=accession_8k, ticker=ticker).single()
        finally:
            driver.close()

    if not row:
        raise ValueError(f"8-K {accession_8k} not found for {ticker}")

    filed_8k = _to_str(row["filed_8k"])
    market_session = row["market_session"] or "post_market"
    prev_8k_ts = _to_str(row["prev_8k_ts"])
    period_of_report_raw = row["period_of_report"]
    form_type_periodic = row["form_type_periodic"]
    accession_periodic = row["accession_periodic"] or ""
    xbrl_period = row["xbrl_period"]
    xbrl_year = row["xbrl_year"]

    # FYE month: prefer Redis (adjusted for 52-week), fall back to raw Neo4j
    fye_month = get_fye_month(ticker, gaps)
    if fye_month is None:
        fye_month = row["fye_month"]  # raw Neo4j fallback

    # ── Check matched periodic: present and not stale? ──
    matched_is_valid = False
    if period_of_report_raw is not None:
        period_of_report_matched = str(period_of_report_raw)[:10]
        try:
            gap_days = (date.fromisoformat(filed_8k[:10]) -
                        date.fromisoformat(period_of_report_matched)).days
        except (ValueError, TypeError):
            gap_days = 999
        if gap_days <= _STALE_MATCH_DAYS:
            matched_is_valid = True
        else:
            gaps.append({"type": "stale_matched_periodic",
                         "reason": f"Matched periodic {accession_periodic} is {gap_days}d stale "
                                   f"(period={period_of_report_matched}, filed_8k={filed_8k[:10]})"})

    # ─�� Resolve period_of_report + quarter_label ──
    period_of_report = None
    quarter_label = None
    source = "none"

    if matched_is_valid:
        # Primary path: matched periodic filing (historical / backfill)
        period_of_report = period_of_report_matched
        source = "matched_periodic"

        if fye_month is not None:
            fy, q = _resolve_fiscal_label(
                period_of_report, form_type_periodic, fye_month,
                accession_periodic, xbrl_year, xbrl_period,
            )
            quarter_label = f"{q}_FY{fy}"
            # Track whether XBRL was actually used (not just present)
            xbrl_fiscal = parse_xbrl_fiscal_identity(xbrl_year, xbrl_period)
            fallback = period_to_fiscal(
                date.fromisoformat(period_of_report).year,
                date.fromisoformat(period_of_report).month,
                date.fromisoformat(period_of_report).day,
                fye_month,
                (form_type_periodic or "10-Q").replace("/A", ""),
            )
            used_xbrl = (xbrl_fiscal is not None
                         and accession_periodic not in XBRL_DENY_PERIODIC_ACCESSIONS
                         and should_use_xbrl_fiscal(fallback, xbrl_fiscal))
            source = "matched_periodic_xbrl" if used_xbrl else "matched_periodic_fiscal_math"
        else:
            gaps.append({"type": "no_fye_month",
                         "reason": f"No 10-K data to derive FYE month for {ticker}"})

    elif fye_month is not None:
        # Fallback path: live-safe fiscal math (no matched periodic or stale)
        result = _map_event_to_quarter_end(filed_8k, fye_month)
        if result:
            period_of_report, fy, q = result
            quarter_label = f"{q}_FY{fy}"
            source = "fiscal_math"
        else:
            gaps.append({"type": "fiscal_math_failed",
                         "reason": f"Could not map filed_8k={filed_8k} to quarter-end with fye_month={fye_month}"})
    else:
        gaps.append({"type": "no_resolution",
                     "reason": f"No matched periodic and no FYE month for {ticker}"})

    if not prev_8k_ts:
        gaps.append({"type": "no_prev_8k",
                     "reason": f"No previous 8-K 2.02 found for {ticker} before {filed_8k}"})

    return {
        "accession_8k": accession_8k,
        "filed_8k": filed_8k,
        "market_session": market_session,
        "period_of_report": period_of_report,
        "prev_8k_ts": prev_8k_ts,
        "quarter_label": quarter_label,
        "form_type_periodic": form_type_periodic,
        "accession_periodic": accession_periodic,
        "fye_month": fye_month,
        "quarter_identity_source": source,
        "gaps": gaps if gaps else None,
    }


# ── CLI ──

if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        print("Usage: python quarter_identity.py TICKER ACCESSION")
        sys.exit(1)
    qi = resolve_quarter_info(sys.argv[1], sys.argv[2])
    print(json.dumps(qi, indent=2, default=str))
