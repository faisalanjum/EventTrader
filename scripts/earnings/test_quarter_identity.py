#!/usr/bin/env python3
"""Validate quarter identity resolution against XBRL ground truth.

Runs the exact logic that resolve_quarter_info() will use against all 8,805+
8-K earnings filings with XBRL fiscal identity in Neo4j.

Two paths tested independently:
  Path A (PIT-safe):  filed_8k → FYE month → fiscal_math quarter-end mapping
  Path B (matched):   matched 10-Q/10-K periodOfReport → period_to_fiscal()

Both compared against XBRL dei:DocumentFiscalPeriodFocus + dei:DocumentFiscalYearFocus.

Usage:
    python3 scripts/earnings/test_quarter_identity.py
    python3 scripts/earnings/test_quarter_identity.py --ticker CRM
    python3 scripts/earnings/test_quarter_identity.py --mismatches-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(str(_PROJECT_ROOT / ".env"), override=True)

from fiscal_math import period_to_fiscal
from get_quarterly_filings import (
    parse_xbrl_fiscal_identity,
    should_use_xbrl_fiscal,
    XBRL_DENY_PERIODIC_ACCESSIONS,
)
import quarter_identity
from earnings_orchestrator import enforce_quarter_identity_write_guard


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def single(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeSession:
    def __init__(self, metadata_by_accession, priors_by_accession, xbrl_by_accession=None):
        self.metadata_by_accession = metadata_by_accession
        self.priors_by_accession = priors_by_accession
        self.xbrl_by_accession = dict(xbrl_by_accession or {})

    def run(self, query, **params):
        if "prev_8k_ts" in query:
            row = self.metadata_by_accession.get(params["accession"])
            return _FakeResult([row] if row else [])
        if "$accession" in query and "accession_8k" not in params:
            row = self.xbrl_by_accession.get(params["accession"])
            return _FakeResult([row] if row else [])
        rows = self.priors_by_accession.get(params["accession_8k"], [])
        return _FakeResult(rows)


def _fake_resolve(
    monkeypatch,
    *,
    ticker,
    accession,
    filed,
    fye_month,
    priors,
    prev_8k_ts="2025-01-01T16:00:00-05:00",
    xbrl_by_accession=None,
):
    quarter_identity._PRIOR_CACHE.clear()
    quarter_identity._FYE_CACHE.clear()
    quarter_identity._XBRL_CACHE.clear()
    quarter_identity._CONTEXT_CACHE.clear()
    quarter_identity._TICKER_CONTEXT_PRELOADED.clear()
    monkeypatch.setattr(
        quarter_identity,
        "get_fye_month",
        lambda _ticker, gaps=None: fye_month,
    )
    session = _FakeSession(
        {
            accession: {
                "accession_8k": accession,
                "filed_8k": filed,
                "market_session": "post_market",
                "fye_month": fye_month,
                "prev_8k_ts": prev_8k_ts,
            }
        },
        {accession: priors},
        xbrl_by_accession=xbrl_by_accession,
    )
    return quarter_identity.resolve_quarter_info(ticker, accession, session=session)


def _prior(accession, created, period, form, xbrl_year=None, xbrl_period=None):
    return {
        "accession": accession,
        "created": created,
        "period": period,
        "form": form,
        "xbrl_year": xbrl_year,
        "xbrl_period": xbrl_period,
    }


def test_rule_f_fcx_calendar_q4_to_q1(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="FCX",
        accession="0000831259-26-000021",
        filed="2026-04-23T16:10:00-05:00",
        fye_month=12,
        priors=[
            _prior("0000831259-26-000010", "2026-02-14T08:00:00-05:00", "2025-12-31", "10-K"),
        ],
    )
    assert qi["quarter_label"] == "Q1_FY2026"
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "prior_periodic_projection_q4_to_q1"


@pytest.mark.parametrize(
    "ticker,accession,filed,period,xbrl_year,xbrl_period,expected",
    [
        ("PEP", "0000077476-26-000019", "2026-04-24T08:30:00-05:00", "2026-03-21", 2026, "Q1", "Q1_FY2026"),
        ("LEVI", "0000094845-24-000059", "2024-10-03T08:30:00-05:00", "2024-08-25", 2024, "Q3", "Q3_FY2024"),
    ],
)
def test_rule_f_direct_recent_prior(monkeypatch, ticker, accession, filed, period, xbrl_year, xbrl_period, expected):
    qi = _fake_resolve(
        monkeypatch,
        ticker=ticker,
        accession=accession,
        filed=filed,
        fye_month=12,
        priors=[
            _prior("prior-recent", filed.replace("08:30:00", "08:00:00"), period, "10-Q", xbrl_year, xbrl_period),
        ],
    )
    assert qi["quarter_label"] == expected
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "rule_f_direct_recent_prior"


@pytest.mark.parametrize(
    "ticker,accession,expected",
    [
        ("AAP", "0001158449-24-000236", "Q3_FY2024"),
        ("PSTG", "0001628280-23-040217", "Q3_FY2024"),
    ],
)
def test_rule_f_advances_xbrl_for_non_recent_odd_prior(monkeypatch, ticker, accession, expected):
    qi = _fake_resolve(
        monkeypatch,
        ticker=ticker,
        accession=accession,
        filed="2024-11-20T16:10:00-05:00",
        fye_month=12,
        priors=[
            _prior("prior-odd", "2024-08-01T06:00:00-05:00", "2024-06-15", "10-Q", 2024, "Q2"),
        ],
    )
    assert qi["quarter_label"] == expected
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "rule_f_advance_xbrl"


@pytest.mark.parametrize(
    "ticker,accession",
    [
        ("KR", "0001104659-25-019465"),
        ("NTAP", "0001193125-25-297164"),
    ],
)
def test_rule_f_fail_closed_on_fy_disagreement(monkeypatch, ticker, accession):
    qi = _fake_resolve(
        monkeypatch,
        ticker=ticker,
        accession=accession,
        filed="2025-06-01T16:10:00-05:00",
        fye_month=12,
        priors=[
            _prior("prior-odd", "2025-02-01T06:00:00-05:00", "2024-06-15", "10-Q", 2025, "Q2"),
        ],
    )
    assert qi["quarter_label"] is None
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "rule_f_fail_closed_fy_disagreement"


def test_prior_periodic_projection_long_gap_fail_closed(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-long-gap",
        filed="2026-07-15T16:10:00-05:00",
        fye_month=12,
        priors=[
            _prior("prior-calendar", "2026-01-01T06:00:00-05:00", "2025-12-31", "10-K"),
        ],
    )
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "prior_periodic_projection_long_gap_fail_closed"


def test_prior_periodic_projection_denylist_fail_closed(monkeypatch):
    denied = next(iter(XBRL_DENY_PERIODIC_ACCESSIONS))
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-deny",
        filed="2026-03-01T16:10:00-05:00",
        fye_month=12,
        priors=[
            _prior(denied, "2026-02-01T06:00:00-05:00", "2025-12-31", "10-K"),
        ],
    )
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "prior_periodic_projection_denylisted_prior_fail_closed"


def test_prior_periodic_projection_cold_start_fail_closed(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-cold-start",
        filed="2026-03-01T16:10:00-05:00",
        fye_month=12,
        priors=[],
    )
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "prior_periodic_projection_no_prior"


def test_rule_g_strict_direct_recent_prior_calendar(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-calendar-recent",
        filed="2026-04-23T08:09:07-04:00",
        fye_month=12,
        priors=[
            _prior(
                "prior-calendar-recent",
                "2026-04-23T08:00:00-04:00",
                "2026-03-31",
                "10-Q",
                2026,
                "Q1",
            ),
        ],
    )
    assert qi["quarter_label"] == "Q1_FY2026"
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "rule_g_strict_direct_recent_prior_calendar"
    assert qi["accession_periodic"] == "prior-calendar-recent"


def test_rule_g_strict_recent_disagreement_calendar_fail_closed(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-calendar-recent-disagreement",
        filed="2026-04-23T08:09:07-04:00",
        fye_month=12,
        priors=[
            _prior(
                "prior-calendar-recent-bad-xbrl",
                "2026-04-23T08:00:00-04:00",
                "2026-03-31",
                "10-Q",
                2025,
                "Q1",
            ),
        ],
    )
    assert qi["quarter_label"] is None
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert (
        qi["quarter_identity_source"]
        == "rule_g_strict_fail_closed_recent_disagreement_calendar"
    )


def test_rule_g_non_recent_fy_disagreement_calendar_fail_closed(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="ANF",
        accession="synthetic-anf-like-fy-disagreement",
        filed="2024-06-01T16:10:00-04:00",
        fye_month=1,
        priors=[
            _prior(
                "prior-anf-like-annual",
                "2024-03-15T06:00:00-04:00",
                "2024-02-03",
                "10-K",
                2023,
                "FY",
            ),
        ],
    )
    assert qi["quarter_label"] is None
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "rule_g_fail_closed_fy_disagreement_calendar"


def test_rule_g_no_prev_8k_short_gap_calendar_fail_closed(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-no-prev-short-gap",
        filed="2026-04-23T16:10:00-04:00",
        fye_month=12,
        prev_8k_ts=None,
        priors=[
            _prior(
                "prior-calendar-no-prev",
                "2026-02-14T08:00:00-05:00",
                "2025-12-31",
                "10-K",
                2025,
                "FY",
            ),
        ],
    )
    assert qi["quarter_label"] is None
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert qi["quarter_identity_source"] == "rule_g_fail_closed_no_prev_short_gap_calendar"


def test_rule_g_same_filing_cycle_short_gap_calendar_branch(monkeypatch):
    monkeypatch.setattr(
        quarter_identity,
        "_same_filing_cycle_indicator",
        lambda **_kwargs: True,
    )
    qi = _fake_resolve(
        monkeypatch,
        ticker="SYN",
        accession="synthetic-same-filing-short-gap",
        filed="2026-04-23T16:10:00-04:00",
        fye_month=12,
        prev_8k_ts="2026-01-10T16:00:00-05:00",
        priors=[
            _prior(
                "prior-calendar-same-cycle",
                "2026-02-14T08:00:00-05:00",
                "2025-12-31",
                "10-K",
                2025,
                "FY",
            ),
        ],
    )
    assert qi["quarter_label"] is None
    assert qi["safety_action"] == "FAIL_CLOSED"
    assert (
        qi["quarter_identity_source"]
        == "rule_g_fail_closed_same_filing_short_gap_calendar"
    )


def test_rule_g_same_filing_cycle_indicator_uses_recent_prior_ordering():
    filed = quarter_identity._parse_datetime("2026-04-23T08:09:07-04:00")
    prior_created = quarter_identity._parse_datetime("2026-04-23T08:00:00-04:00")
    assert quarter_identity._same_filing_cycle_indicator(
        prev_8k_ts="2026-04-22T16:00:00-04:00",
        prior_created=prior_created,
        filed=filed,
    )


def test_rule_g_cleaned_nr_adm_representative_matches_measurement(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="ADM",
        accession="0000007084-24-000010",
        filed="2024-01-25T08:09:07-05:00",
        fye_month=12,
        priors=[
            _prior(
                "adm-prior-2023-q4",
                "2024-01-25T08:00:00-05:00",
                "2023-12-31",
                "10-K",
                2023,
                "FY",
            ),
        ],
    )
    assert qi["quarter_label"] == "Q4_FY2023"
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "rule_g_strict_direct_recent_prior_calendar"


def test_rule_g_cleaned_nr_ok_has_representative_preserved(monkeypatch):
    qi = _fake_resolve(
        monkeypatch,
        ticker="HAS",
        accession="0000046080-26-000016",
        filed="2026-04-24T08:30:00-04:00",
        fye_month=12,
        priors=[
            _prior(
                "has-prior-2025-q4",
                "2026-02-20T08:00:00-05:00",
                "2025-12-31",
                "10-K",
                2025,
                "FY",
            ),
        ],
    )
    assert qi["quarter_label"] == "Q1_FY2026"
    assert qi["safety_action"] == "AUTO_OK"
    assert qi["quarter_identity_source"] == "prior_periodic_projection_q4_to_q1"


def test_write_guard_refuses_fail_closed_and_writes_quarantine(tmp_path):
    save_dir = tmp_path / "event_dir"
    quarter_info = {
        "accession_8k": "0000831259-26-000021",
        "safety_action": "FAIL_CLOSED",
        "quarter_identity_source": "prior_periodic_projection_long_gap_fail_closed",
    }

    with pytest.raises(RuntimeError, match="write guard refused"):
        enforce_quarter_identity_write_guard("FCX", quarter_info, str(save_dir))

    assert not save_dir.exists()
    quarantine = (
        tmp_path
        / "_quarter_identity_quarantine"
        / "event_dir"
        / "0000831259-26-000021.json"
    )
    payload = json.loads(quarantine.read_text(encoding="utf-8"))
    assert payload["ticker"] == "FCX"
    assert payload["accession_8k"] == "0000831259-26-000021"
    assert payload["quarter_info"]["safety_action"] == "FAIL_CLOSED"


def test_write_guard_allows_auto_ok_without_quarantine(tmp_path):
    save_dir = tmp_path / "event_dir"
    quarter_info = {
        "accession_8k": "0000831259-26-000021",
        "safety_action": "AUTO_OK",
        "quarter_identity_source": "prior_periodic_projection_q4_to_q1",
    }
    assert enforce_quarter_identity_write_guard("FCX", quarter_info, str(save_dir)) is None
    assert not save_dir.exists()


# ── Cypher: one query to get everything ──────────────────────────────

QUERY = """
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
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
// Get FYE month from 10-K periods for this company
OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}
RETURN c.ticker AS ticker,
       r.accessionNo AS accession_8k,
       r.created AS filed_8k,
       period_of_report,
       form_type_periodic,
       accession_periodic,
       xbrl_period, xbrl_year,
       fye_month
ORDER BY c.ticker, r.created
"""

QUERY_SINGLE = QUERY.replace(
    "WHERE r.formType = '8-K' AND r.items CONTAINS '2.02'",
    "WHERE r.formType = '8-K' AND r.items CONTAINS '2.02' AND c.ticker = $ticker",
)


# ── Path A: PIT-safe mapping (filed_8k → quarter-end via FYE + fiscal_math) ─

def map_event_to_quarter_end(filed_8k_str: str, fye_month: int) -> tuple[str, int, str] | None:
    """Map an 8-K filing date to the fiscal quarter-end it reports on.

    Uses FYE month to generate quarter-end dates, then finds the nearest one
    to filed_8k within a forward window (handles COST-style early reporters).

    Returns: (period_of_report, fiscal_year, fiscal_quarter) or None.
    """
    try:
        # Parse filed_8k to a date
        filed_str = str(filed_8k_str)[:10]
        filed_date = date.fromisoformat(filed_str)
    except (ValueError, TypeError):
        return None

    from fiscal_math import _compute_fiscal_dates

    # Generate quarter-ends for a window around the filing date
    best = None
    best_gap = None
    for fy in range(filed_date.year - 1, filed_date.year + 2):
        for q_label in ["Q1", "Q2", "Q3", "Q4"]:
            _, end_str = _compute_fiscal_dates(fye_month, fy, q_label)
            end_date = date.fromisoformat(end_str)
            # Quarter-end must be within: (filed_8k - 120 days) to (filed_8k + 7 days)
            # - Lower bound: earnings are reported within ~90 days of quarter-end
            # - Upper bound: COST-style early reporters (report 2-5 days before quarter ends)
            gap = (filed_date - end_date).days
            if -7 <= gap <= 120:
                if best_gap is None or gap < best_gap:
                    best_gap = gap
                    form_hint = "10-K" if q_label == "Q4" else "10-Q"
                    d = end_date
                    adj_month = (d.month - 1 if d.month > 1 else 12) if d.day <= 5 else d.month
                    best = (end_str, fy, q_label)

    return best


# ── Path B: matched periodic filing → period_to_fiscal() ────────────

def resolve_from_matched(period_of_report_str: str, form_type: str,
                         fye_month: int, accession_periodic: str,
                         xbrl_year_raw, xbrl_period_raw) -> tuple[int, str] | None:
    """Resolve fiscal label from matched periodic filing.

    Same cascade as build_prior_financials._get_fiscal_labels():
    1. Compute fallback via period_to_fiscal()
    2. Parse XBRL fiscal identity
    3. Apply denylist + proximity guard
    """
    try:
        d = date.fromisoformat(str(period_of_report_str)[:10])
    except (ValueError, TypeError):
        return None

    base_form = form_type.replace("/A", "") if form_type else "10-Q"

    # Step 1: fallback from period_to_fiscal
    fallback_fiscal = period_to_fiscal(d.year, d.month, d.day, fye_month, base_form)

    # Step 2: XBRL fiscal identity
    xbrl_fiscal = parse_xbrl_fiscal_identity(xbrl_year_raw, xbrl_period_raw)

    # Step 3: choose — exact logic from get_quarterly_filings.py
    if accession_periodic and accession_periodic in XBRL_DENY_PERIODIC_ACCESSIONS:
        return fallback_fiscal
    elif should_use_xbrl_fiscal(fallback_fiscal, xbrl_fiscal):
        return xbrl_fiscal
    else:
        return fallback_fiscal


# ── Main validation ──────────────────────────────────────────────────

def run_validation(ticker: str | None = None, mismatches_only: bool = False):
    uri = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        print("ERROR: NEO4J_PASSWORD not set")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            if ticker:
                print(f"Querying 8-K filings for {ticker.upper()}...")
                results = list(session.run(QUERY_SINGLE, ticker=ticker.upper()))
            else:
                print("Querying all 8-K 2.02 filings (may take ~10s)...")
                results = list(session.run(QUERY))
    finally:
        driver.close()

    print(f"Fetched {len(results)} rows\n")

    # Coverage counters (independent of XBRL)
    total = 0
    has_periodic = 0
    has_xbrl = 0
    has_fye = 0
    in_denylist = 0

    # Skip counters (for accuracy testing, which requires XBRL ground truth)
    skipped_no_xbrl = 0
    skipped_no_periodic = 0
    skipped_no_fye = 0

    # Gap sanity check (period_of_report to filed_8k)
    gap_days_list = []
    suspicious_gaps = []

    path_a_match = 0
    path_a_mismatch = 0
    path_a_no_result = 0

    path_b_match = 0
    path_b_mismatch = 0
    path_b_no_result = 0

    # Path B fallback-only (period_to_fiscal without XBRL — independent test)
    path_b_fallback_match = 0
    path_b_fallback_mismatch = 0
    mismatches_b_fallback = []

    # XBRL rescue counter (fallback wrong, XBRL fixed it)
    xbrl_rescued = 0

    both_match = 0
    both_mismatch = 0

    mismatches_a = []
    mismatches_b = []

    for row in results:
        total += 1
        tk = row["ticker"]
        filed_8k = row["filed_8k"]
        period_of_report = row["period_of_report"]
        form_type_periodic = row["form_type_periodic"]
        accession_periodic = row["accession_periodic"] or ""
        xbrl_period = row["xbrl_period"]
        xbrl_year = row["xbrl_year"]
        fye_month = row["fye_month"]

        # ── Coverage accounting (independent of XBRL) ──
        if period_of_report is not None:
            has_periodic += 1
        if fye_month is not None:
            has_fye += 1
        if xbrl_period is not None or xbrl_year is not None:
            has_xbrl += 1
        if accession_periodic in XBRL_DENY_PERIODIC_ACCESSIONS:
            in_denylist += 1

        # ── Gap sanity check ──
        if period_of_report is not None and filed_8k is not None:
            try:
                por_date = date.fromisoformat(str(period_of_report)[:10])
                filed_date = date.fromisoformat(str(filed_8k)[:10])
                gap = (filed_date - por_date).days
                gap_days_list.append(gap)
                if gap < 0 or gap > 150:
                    suspicious_gaps.append({
                        "ticker": tk, "filed_8k": str(filed_8k)[:10],
                        "period_of_report": str(period_of_report)[:10],
                        "gap_days": gap, "accession_periodic": accession_periodic,
                    })
            except (ValueError, TypeError):
                pass

        # ── Accuracy testing (requires XBRL ground truth) ──
        xbrl_truth = parse_xbrl_fiscal_identity(xbrl_year, xbrl_period)
        if xbrl_truth is None:
            skipped_no_xbrl += 1
            continue

        truth_fy, truth_q = xbrl_truth
        # Normalize: FY → Q4
        if truth_q == "Q4" or truth_q == "FY":
            truth_q = "Q4"
        truth_label = f"{truth_q}_FY{truth_fy}"

        if period_of_report is None:
            skipped_no_periodic += 1
            continue

        if fye_month is None:
            skipped_no_fye += 1
            continue

        filed_8k_str = str(filed_8k)

        # ── Path A: PIT-safe mapping ──
        result_a = map_event_to_quarter_end(filed_8k_str, fye_month)
        if result_a:
            _, a_fy, a_q = result_a
            a_label = f"{a_q}_FY{a_fy}"
            if a_label == truth_label:
                path_a_match += 1
                a_ok = True
            else:
                path_a_mismatch += 1
                a_ok = False
                mismatches_a.append({
                    "ticker": tk, "filed_8k": filed_8k_str,
                    "period_of_report": str(period_of_report),
                    "fye_month": fye_month,
                    "computed": a_label, "truth": truth_label,
                })
        else:
            path_a_no_result += 1
            a_ok = False

        # ── Path B: matched periodic filing ──
        result_b = resolve_from_matched(
            str(period_of_report), form_type_periodic or "10-Q",
            fye_month, accession_periodic, xbrl_year, xbrl_period,
        )
        if result_b:
            b_fy, b_q = result_b
            b_label = f"{b_q}_FY{b_fy}"
            if b_label == truth_label:
                path_b_match += 1
                b_ok = True
            else:
                path_b_mismatch += 1
                b_ok = False
                mismatches_b.append({
                    "ticker": tk, "filed_8k": filed_8k_str,
                    "period_of_report": str(period_of_report),
                    "form_type": form_type_periodic,
                    "accession_periodic": accession_periodic,
                    "fye_month": fye_month,
                    "computed": b_label, "truth": truth_label,
                    "xbrl_raw": f"{xbrl_year}/{xbrl_period}",
                })
        else:
            path_b_no_result += 1
            b_ok = False

        # ── Path B fallback-only (no XBRL — independent accuracy) ──
        result_b_fallback = resolve_from_matched(
            str(period_of_report), form_type_periodic or "10-Q",
            fye_month, accession_periodic,
            None, None,  # suppress XBRL
        )
        if result_b_fallback:
            bf_fy, bf_q = result_b_fallback
            bf_label = f"{bf_q}_FY{bf_fy}"
            if bf_label == truth_label:
                path_b_fallback_match += 1
            else:
                path_b_fallback_mismatch += 1
                mismatches_b_fallback.append({
                    "ticker": tk, "filed_8k": filed_8k_str,
                    "period_of_report": str(period_of_report),
                    "form_type": form_type_periodic,
                    "accession_periodic": accession_periodic,
                    "fye_month": fye_month,
                    "computed": bf_label, "truth": truth_label,
                    "xbrl_raw": f"{xbrl_year}/{xbrl_period}",
                })
                # Check if XBRL hybrid rescued this one
                if b_ok:
                    xbrl_rescued += 1

        if a_ok and b_ok:
            both_match += 1
        elif not a_ok and not b_ok:
            both_mismatch += 1

    # ── Report ───────────────────────────────────────────────────────
    tested = total - skipped_no_xbrl - skipped_no_periodic - skipped_no_fye
    print("=" * 70)
    print(f"QUARTER IDENTITY VALIDATION — {'ALL TICKERS' if not ticker else ticker.upper()}")
    print("=" * 70)

    print(f"\n── Coverage ──")
    print(f"Total 8-K 2.02:       {total}")
    print(f"Has matched periodic: {has_periodic}  ({has_periodic/total*100:.1f}%)" if total else "  N/A")
    print(f"Has XBRL tags:        {has_xbrl}  ({has_xbrl/total*100:.1f}%)" if total else "  N/A")
    print(f"Has FYE month:        {has_fye}  ({has_fye/total*100:.1f}%)" if total else "  N/A")
    print(f"In denylist:          {in_denylist}")
    print(f"No periodic:          {total - has_periodic}")
    print(f"No XBRL (skipped):    {skipped_no_xbrl}")
    print(f"Testable (has all):   {tested}")

    if gap_days_list:
        import statistics
        print(f"\n── Gap: filed_8k minus period_of_report (days) ──")
        print(f"  Count:    {len(gap_days_list)}")
        print(f"  Mean:     {statistics.mean(gap_days_list):.1f}")
        print(f"  Median:   {statistics.median(gap_days_list):.0f}")
        print(f"  Min:      {min(gap_days_list)}")
        print(f"  Max:      {max(gap_days_list)}")
        print(f"  P5/P95:   {sorted(gap_days_list)[len(gap_days_list)//20]}/{sorted(gap_days_list)[len(gap_days_list)*19//20]}")
        print(f"  Suspicious (<0 or >150 days): {len(suspicious_gaps)}")
        if suspicious_gaps:
            print(f"  ── Suspicious gaps (first 20 of {len(suspicious_gaps)}) ──")
            for g in suspicious_gaps[:20]:
                print(f"    {g['ticker']:6s}  filed={g['filed_8k']}  period={g['period_of_report']}  "
                      f"gap={g['gap_days']:4d}d  acc={g['accession_periodic']}")
    print()
    print()
    print(f"Path A (PIT-safe: filed_8k → FYE → fiscal_math):")
    print(f"  Match:     {path_a_match}  ({path_a_match/tested*100:.2f}%)" if tested else "  N/A")
    print(f"  Mismatch:  {path_a_mismatch}")
    print(f"  No result: {path_a_no_result}")
    print()
    print(f"Path B FALLBACK-ONLY (period_to_fiscal, NO XBRL — independent test):")
    print(f"  Match:     {path_b_fallback_match}  ({path_b_fallback_match/tested*100:.2f}%)" if tested else "  N/A")
    print(f"  Mismatch:  {path_b_fallback_mismatch}")
    print()
    print(f"Path B HYBRID (period_to_fiscal + XBRL override):")
    print(f"  Match:     {path_b_match}  ({path_b_match/tested*100:.2f}%)" if tested else "  N/A")
    print(f"  Mismatch:  {path_b_mismatch}")
    print(f"  No result: {path_b_no_result}")
    print(f"  XBRL rescued: {xbrl_rescued}  (fallback wrong → XBRL fixed)")
    print()
    print(f"Both match:    {both_match}")
    print(f"Both mismatch: {both_mismatch}")
    print()

    if mismatches_a and not mismatches_only:
        print(f"── Path A mismatches (first 20 of {len(mismatches_a)}) ──")
        for m in mismatches_a[:20]:
            print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                  f"fye={m['fye_month']:2d}  computed={m['computed']:12s}  truth={m['truth']}")
        print()

    if mismatches_b_fallback and not mismatches_only:
        print(f"── Path B FALLBACK-ONLY mismatches (first 30 of {len(mismatches_b_fallback)}) ──")
        for m in mismatches_b_fallback[:30]:
            rescued = " ← XBRL rescued" if m['computed'] != m['truth'] else ""
            print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                  f"form={m['form_type'] or '?':5s}  fye={m['fye_month']:2d}  "
                  f"computed={m['computed']:12s}  truth={m['truth']:12s}  xbrl={m['xbrl_raw']}{rescued}")
        print()

    if mismatches_b and not mismatches_only:
        print(f"── Path B HYBRID mismatches (first 20 of {len(mismatches_b)}) ──")
        for m in mismatches_b[:20]:
            print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                  f"form={m['form_type'] or '?':5s}  fye={m['fye_month']:2d}  "
                  f"computed={m['computed']:12s}  truth={m['truth']:12s}  xbrl={m['xbrl_raw']}")
        print()

    if mismatches_only:
        # Dump ALL mismatches
        if mismatches_a:
            print(f"── ALL Path A mismatches ({len(mismatches_a)}) ──")
            for m in mismatches_a:
                print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                      f"fye={m['fye_month']:2d}  computed={m['computed']:12s}  truth={m['truth']}")
            print()
        if mismatches_b_fallback:
            print(f"── ALL Path B FALLBACK-ONLY mismatches ({len(mismatches_b_fallback)}) ──")
            for m in mismatches_b_fallback:
                print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                      f"form={m['form_type'] or '?':5s}  fye={m['fye_month']:2d}  "
                      f"computed={m['computed']:12s}  truth={m['truth']:12s}  xbrl={m['xbrl_raw']}")
            print()
        if mismatches_b:
            print(f"── ALL Path B HYBRID mismatches ({len(mismatches_b)}) ──")
            for m in mismatches_b:
                print(f"  {m['ticker']:6s} filed={m['filed_8k'][:10]}  period={m['period_of_report'][:10]}  "
                      f"form={m['form_type'] or '?':5s}  fye={m['fye_month']:2d}  "
                      f"computed={m['computed']:12s}  truth={m['truth']:12s}  xbrl={m['xbrl_raw']}")
            print()

    # Mismatch ticker distribution
    if mismatches_a:
        dist_a = defaultdict(int)
        for m in mismatches_a:
            dist_a[m["ticker"]] += 1
        print(f"Path A mismatch tickers: {dict(sorted(dist_a.items(), key=lambda x: -x[1]))}")
    if mismatches_b_fallback:
        dist_bf = defaultdict(int)
        for m in mismatches_b_fallback:
            dist_bf[m["ticker"]] += 1
        print(f"Path B fallback-only mismatch tickers: {dict(sorted(dist_bf.items(), key=lambda x: -x[1]))}")
    if mismatches_b:
        dist_b = defaultdict(int)
        for m in mismatches_b:
            dist_b[m["ticker"]] += 1
        print(f"Path B hybrid mismatch tickers: {dict(sorted(dist_b.items(), key=lambda x: -x[1]))}")


def main():
    parser = argparse.ArgumentParser(description="Validate quarter identity against XBRL ground truth")
    parser.add_argument("--ticker", default=None, help="Single ticker (default: all)")
    parser.add_argument("--mismatches-only", action="store_true", help="Show all mismatches (not just first 20)")
    args = parser.parse_args()
    run_validation(ticker=args.ticker, mismatches_only=args.mismatches_only)


if __name__ == "__main__":
    main()
