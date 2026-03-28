#!/usr/bin/env python3
"""Prior-financials builder — XBRL Fact graph → FSC fallback → Yahoo opt-in.

Produces a `prior_financials.v1` packet with:
  - quarters: 4-8 prior quarters of exact-as-filed financial metrics
  - segment_inventory: member qnames + axis grouping for revenue & operating income
  - summary: coverage stats, source breakdown, derived metric count

Two modes:
  - Live  (no --pit): include all filings, no cutoff
  - Historical (--pit ISO): PIT-filtered by Report.created

Usage:
    python3 scripts/earnings/build_prior_financials.py CRM
    python3 scripts/earnings/build_prior_financials.py CRM --pit 2025-12-05T16:00:09-05:00
    python3 scripts/earnings/build_prior_financials.py CRM --period-of-report 2025-04-30
    python3 scripts/earnings/build_prior_financials.py CRM --allow-yahoo
    python3 scripts/earnings/build_prior_financials.py CRM --out-path /tmp/test.json

Orchestrator call:
    build_prior_financials(ticker, quarter_info, as_of_ts=None, out_path=None)

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (or .env file in project root)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# fiscal_math lives in the earnings-orchestrator skill directory
_FM_DIR = str(Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts")
if _FM_DIR not in sys.path:
    sys.path.insert(0, _FM_DIR)


# ── Constants ────────────────────────────────────────────────────────────

_HISTORY_QUARTERS = 8
_OVERFETCH_QUARTERS = 10  # Fetch extra to survive fiscal-key dedup dropping periods

ZERO_FACT_DENYLIST = {
    "0000885725-24-000073",
    "0001616707-24-000054",
}

# Balance sheet concepts — need instant period handling (not duration)
_BALANCE_SHEET_CONCEPTS = {
    "us-gaap:Assets",
    "us-gaap:CashAndCashEquivalentsAtCarryingValue",
    "us-gaap:CashCashEquivalentsAndShortTermInvestments",
    "us-gaap:LongTermDebt",
    "us-gaap:LongTermDebtNoncurrent",
    "us-gaap:LongTermDebtAndCapitalLeaseObligations",
    "us-gaap:StockholdersEquity",
}

# Cash flow concepts — need YTD derivation for Q2/Q3
_CASH_FLOW_YTD_CONCEPTS = {
    "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    "us-gaap:PaymentsForRepurchaseOfCommonStock",
}

# EPS/shares — NEVER derive by subtraction
_EPS_CONCEPTS = {
    "us-gaap:EarningsPerShareDiluted",
    "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
}

# Metric registry: (output_field, [concept_qnames_in_priority_order], statement_type)
METRIC_REGISTRY = [
    # Income Statement
    ("revenue", [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
        "us-gaap:RevenuesNetOfInterestExpense",
        "us-gaap:OperatingLeaseLeaseIncome",
        "us-gaap:RegulatedOperatingRevenue",
    ], "income"),
    ("cost_of_revenue", ["us-gaap:CostOfGoodsAndServicesSold", "us-gaap:CostOfRevenue"], "income"),
    ("gross_profit", ["us-gaap:GrossProfit"], "income"),
    ("sga", ["us-gaap:SellingGeneralAndAdministrativeExpense", "us-gaap:SellingAndMarketingExpense"], "income"),
    ("rd_expense", ["us-gaap:ResearchAndDevelopmentExpense"], "income"),
    ("depreciation_amortization", ["us-gaap:DepreciationAndAmortization", "us-gaap:DepreciationDepletionAndAmortization"], "income"),
    ("interest_expense", ["us-gaap:InterestExpense", "us-gaap:InterestExpenseNonoperating", "us-gaap:InterestExpenseDebt"], "income"),
    ("income_tax", ["us-gaap:IncomeTaxExpenseBenefit"], "income"),
    ("operating_income", ["us-gaap:OperatingIncomeLoss"], "income"),
    ("net_income", ["us-gaap:NetIncomeLoss", "us-gaap:ProfitLoss", "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic"], "income"),
    ("eps_diluted", ["us-gaap:EarningsPerShareDiluted"], "income"),
    ("diluted_shares", ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"], "income"),
    # Balance Sheet
    ("total_assets", ["us-gaap:Assets"], "balance"),
    ("cash_and_equivalents", ["us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:CashCashEquivalentsAndShortTermInvestments"], "balance"),
    ("long_term_debt", ["us-gaap:LongTermDebt", "us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebtAndCapitalLeaseObligations"], "balance"),
    ("stockholders_equity", ["us-gaap:StockholdersEquity"], "balance"),
    # Cash Flow
    ("operating_cash_flow", ["us-gaap:NetCashProvidedByUsedInOperatingActivities"], "cashflow"),
    ("capex", ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"], "cashflow"),
    ("buybacks", ["us-gaap:PaymentsForRepurchaseOfCommonStock"], "cashflow"),
    ("dividends_per_share", ["us-gaap:CommonStockDividendsPerShareDeclared"], "cashflow"),
]

# Flat list of all concept qnames for Cypher $concept_list parameter
ALL_CONCEPT_QNAMES = []
for _, qnames, _ in METRIC_REGISTRY:
    ALL_CONCEPT_QNAMES.extend(qnames)
ALL_CONCEPT_QNAMES = list(dict.fromkeys(ALL_CONCEPT_QNAMES))  # dedupe preserving order

# Map concept qname → output_field (first match wins for priority)
_CONCEPT_TO_FIELD = {}
for field, qnames, _ in METRIC_REGISTRY:
    for qn in qnames:
        if qn not in _CONCEPT_TO_FIELD:
            _CONCEPT_TO_FIELD[qn] = field

# Map output_field → ordered concept qnames
_FIELD_TO_CONCEPTS = {field: qnames for field, qnames, _ in METRIC_REGISTRY}

# Map output_field → statement type
_FIELD_TO_STMT = {field: stmt for field, _, stmt in METRIC_REGISTRY}

YAHOO_FIELD_MAP = {
    "revenue": "Total Revenue",
    "cost_of_revenue": "Cost Of Revenue",
    "gross_profit": "Gross Profit",
    "sga": "Selling General And Administration",
    "rd_expense": "Research And Development",
    "operating_income": "Operating Income",
    "net_income": "Net Income",
    "eps_diluted": "Diluted EPS",
    "diluted_shares": "Diluted Average Shares",
    "operating_cash_flow": "Operating Cash Flow",
    "capex": "Capital Expenditure",
}

STANDARD_MEMBER_AXIS = {
    "srt:AmericasMember": "srt:StatementGeographicalAxis",
    "srt:EuropeMember": "srt:StatementGeographicalAxis",
    "srt:AsiaPacificMember": "srt:StatementGeographicalAxis",
    "srt:NorthAmericaMember": "srt:StatementGeographicalAxis",
    "srt:LatinAmericaMember": "srt:StatementGeographicalAxis",
    "country:US": "srt:StatementGeographicalAxis",
    "us-gaap:ProductMember": "srt:ProductOrServiceAxis",
    "us-gaap:ServiceMember": "srt:ProductOrServiceAxis",
    "us-gaap:OperatingSegmentsMember": "srt:ConsolidationItemsAxis",
    "us-gaap:IntersegmentEliminationMember": "srt:ConsolidationItemsAxis",
    "us-gaap:CorporateNonSegmentMember": "srt:ConsolidationItemsAxis",
    "us-gaap:MaterialReconcilingItemsMember": "srt:ConsolidationItemsAxis",
    "us-gaap:AllOtherSegmentsMember": "us-gaap:StatementBusinessSegmentsAxis",
}

AXIS_KIND = {
    "srt:ProductOrServiceAxis": "product_service",
    "srt:StatementGeographicalAxis": "geography",
    "us-gaap:StatementBusinessSegmentsAxis": "business_segment",
    "srt:ConsolidationItemsAxis": "structural",
    "us-gaap:ContractWithCustomerSalesChannelAxis": "channel",
}


# ── Helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


def classify_period(period_start: str, period_end: str | None) -> str:
    """Classify XBRL period for selection logic.

    period_end = 'null' or None → instant (balance sheet)
    Otherwise compute duration in days → classify by month-equivalent range.
    """
    if period_end is None or period_end == "null":
        return "instant"

    days = (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days
    if days == 0:
        return "instant"
    if 60 <= days <= 120:
        return "quarterly"
    elif 150 <= days <= 210:
        return "semi_annual"
    elif 240 <= days <= 310:
        return "nine_month"
    elif 340 <= days <= 400:
        return "annual"
    return "other"


def is_target_period(fact_period_end: str, report_period_of_report: str) -> bool:
    """Accept fact if period_end is within 7 days of report's periodOfReport."""
    target = date.fromisoformat(report_period_of_report)
    actual = date.fromisoformat(fact_period_end)
    return abs((actual - target).days) <= 7


def dedupe_facts(facts: list[dict]) -> list[dict]:
    """Dedupe by (qname, context_id, unit_ref). Highest decimals wins."""
    seen: dict[tuple, dict] = {}
    for f in facts:
        key = (f["concept"], f.get("context_id", ""), f.get("unit_ref", ""))
        if key not in seen:
            seen[key] = f
        else:
            existing_dec = _parse_decimals(seen[key].get("decimals"))
            new_dec = _parse_decimals(f.get("decimals"))
            if new_dec > existing_dec:
                seen[key] = f
            elif new_dec == existing_dec:
                # Tie-break: more significant digits in value string
                existing_sigfigs = len((seen[key].get("value") or "").replace("-", "").replace(".", "").lstrip("0"))
                new_sigfigs = len((f.get("value") or "").replace("-", "").replace(".", "").lstrip("0"))
                if new_sigfigs > existing_sigfigs:
                    seen[key] = f
    return list(seen.values())


def _parse_decimals(val) -> int:
    if val is None or val == "INF" or val == "inf":
        return 999
    try:
        return int(val)
    except (ValueError, TypeError):
        return -99


def _parse_value(val) -> float | None:
    """Parse XBRL fact value to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _get_fye_month(ticker: str, gaps: list) -> int | None:
    """Get fiscal year end month. Redis → SEC refresh → Yahoo fallback.

    The day<=5 adjustment handles 52-week calendars where the fiscal year
    end falls in the first few days of the next month (e.g., LULU Feb 1 → January).
    """
    ticker = ticker.upper()

    # Tier 1: Redis — already has day<=5 adjustment from sec_quarter_cache_loader
    try:
        import redis as redis_mod
        r = redis_mod.Redis(
            host=os.environ.get("REDIS_HOST", "192.168.40.72"),
            port=int(os.environ.get("REDIS_PORT", "31379")),
            decode_responses=True,
        )
        raw = r.get(f"fiscal_year_end:{ticker}")
        if raw:
            return json.loads(raw).get("month_adj")

        # Auto-refresh from SEC if not cached
        try:
            scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from sec_quarter_cache_loader import refresh_ticker
            refresh_ticker(r, ticker)
            raw = r.get(f"fiscal_year_end:{ticker}")
            if raw:
                return json.loads(raw).get("month_adj")
        except Exception:
            pass
    except Exception:
        pass

    # Tier 2: Yahoo info.lastFiscalYearEnd
    try:
        import yfinance as yf
        fye_ts = yf.Ticker(ticker).info.get("lastFiscalYearEnd")
        if fye_ts:
            dt = datetime.fromtimestamp(fye_ts, tz=timezone.utc)
            month = dt.month
            if dt.day <= 5:
                month = month - 1 if month > 1 else 12
            return month
    except Exception:
        pass

    gaps.append({"type": "fiscal_calendar_missing",
                 "reason": f"Could not determine FYE month for {ticker} (Redis + Yahoo both failed)"})
    return None


def _cli_get(args: list[str], flag: str) -> str | None:
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
        print(f"Error: {flag} requires an argument", file=sys.stderr)
        sys.exit(1)
    return None


# ── Neo4j Queries ────────────────────────────────────────────────────────

_XBRL_FACTS_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND r.periodOfReport < $current_period
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
WITH DISTINCT r.periodOfReport AS period ORDER BY period DESC LIMIT $limit
WITH collect(period) AS target_periods
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.xbrl_status = 'COMPLETED'
  AND r.periodOfReport IN target_periods
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE con.qname IN $concept_list
  AND NOT exists { (f)-[:FACT_MEMBER]->(:Member) }
  AND p.start_date IS NOT NULL
RETURN r.periodOfReport AS period,
       r.formType AS form,
       r.accessionNo AS accession,
       toString(r.created) AS filed,
       con.qname AS concept,
       f.value AS value,
       f.decimals AS decimals,
       f.context_id AS context_id,
       f.unit_ref AS unit_ref,
       p.start_date AS period_start,
       p.end_date AS period_end
ORDER BY r.periodOfReport DESC, r.created DESC, con.qname
"""

_ALL_PERIODS_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.periodOfReport < $current_period
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
RETURN DISTINCT r.periodOfReport AS period ORDER BY period DESC LIMIT $limit
"""

_FSC_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.periodOfReport IN $periods
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type IN ['StatementsOfIncome', 'StatementsOfCashFlows', 'BalanceSheets']
RETURN r.periodOfReport AS period,
       r.formType AS form,
       r.accessionNo AS accession,
       toString(r.created) AS filed,
       fs.statement_type AS statement_type,
       fs.value AS fs_value
ORDER BY r.periodOfReport DESC, r.created DESC
"""

_DEI_FISCAL_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.periodOfReport IN $periods
  AND ($as_of IS NULL OR datetime(r.created) <= datetime($as_of))
WITH r ORDER BY r.created DESC
WITH r LIMIT 50
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(fp:Fact)-[:HAS_CONCEPT]->(fpc:Concept {qname: 'dei:DocumentFiscalPeriodFocus'})
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x)<-[:REPORTS]-(fy:Fact)-[:HAS_CONCEPT]->(fyc:Concept {qname: 'dei:DocumentFiscalYearFocus'})
RETURN r.periodOfReport AS period,
       r.formType AS form,
       r.accessionNo AS accession,
       r.created AS filed,
       fp.value AS fiscal_period,
       fy.value AS fiscal_year
ORDER BY period DESC, filed DESC
"""

_PERIOD_OF_REPORT_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K' AND r.items CONTAINS 'Item 2.02'
RETURN r.periodOfReport ORDER BY r.created DESC LIMIT 1
"""

_SEGMENT_QUERY = """\
MATCH (r:Report {accessionNo: $accession})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:FACT_MEMBER]->(m:Member)
WHERE con.qname IN $concepts
RETURN DISTINCT con.qname AS concept, m.qname AS member_qname, m.label AS member_label
"""

_FSC_FOR_SEGMENTS_QUERY = """\
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type = 'StatementsOfIncome'
RETURN fs.value AS fs_value
LIMIT 1
"""


# ── XBRL Extraction ─────────────────────────────────────────────────────

def _extract_xbrl(manager, ticker: str, current_period: str, as_of: str | None,
                   gaps: list) -> dict[str, list[dict]]:
    """Run the main XBRL query, return facts grouped by periodOfReport.

    Returns: {period_str: [fact_dicts]} where each fact_dict has:
        concept, value, decimals, context_id, unit_ref, period_start, period_end,
        form, accession, filed
    """
    result = manager.execute_cypher_query_all(
        _XBRL_FACTS_QUERY,
        {"ticker": ticker, "current_period": current_period,
         "as_of": as_of, "concept_list": ALL_CONCEPT_QNAMES,
         "limit": _OVERFETCH_QUARTERS},
    )
    # Group by period
    by_period: dict[str, list[dict]] = {}
    for rec in result:
        period = rec["period"]
        by_period.setdefault(period, []).append({
            "concept": rec["concept"],
            "value": rec["value"],
            "decimals": rec["decimals"],
            "context_id": rec["context_id"],
            "unit_ref": rec["unit_ref"],
            "period_start": rec["period_start"],
            "period_end": rec["period_end"],
            "form": rec["form"],
            "accession": rec["accession"],
            "filed": rec["filed"],
        })

    # Dedupe within each (period, accession) — NOT across accessions.
    # Cross-accession dedupe would collapse original + amendment facts,
    # breaking the per-metric newest-first overlay.
    for period in by_period:
        by_acc: dict[str, list[dict]] = {}
        for f in by_period[period]:
            by_acc.setdefault(f["accession"], []).append(f)
        deduped = []
        for acc_facts in by_acc.values():
            deduped.extend(dedupe_facts(acc_facts))
        by_period[period] = deduped

    return by_period


def _fact_source(f: dict) -> str:
    """Determine if a fact came from XBRL or FSC."""
    return "fsc" if f.get("context_id", "").startswith("fsc_") else "xbrl"


def _extract_metric_from_facts(facts: list[dict], concept_qnames: list[str],
                                report_period: str, stmt_type: str,
                                all_facts_for_derivation: list[dict] | None = None,
                                cross_period_facts: dict[str, list[dict]] | None = None,
                                ) -> tuple[float | None, str | None, dict | None, str]:
    """Extract a single metric value from a list of facts for one filing.

    Returns: (value, concept_used, derivation_info, source)
    source is "xbrl" or "fsc" for the matched fact.
    """
    is_balance = stmt_type == "balance"
    is_cashflow = stmt_type == "cashflow"
    is_eps = any(qn in _EPS_CONCEPTS for qn in concept_qnames)
    is_cashflow_ytd = any(qn in _CASH_FLOW_YTD_CONCEPTS for qn in concept_qnames)

    # Classify all facts by period type
    classified: dict[str, list[dict]] = {"quarterly": [], "instant": [],
                                          "semi_annual": [], "nine_month": [],
                                          "annual": [], "other": []}
    for f in facts:
        for qn in concept_qnames:
            if f["concept"] != qn:
                continue
            ptype = classify_period(f["period_start"], f["period_end"])
            classified[ptype].append(f)

    # --- Balance sheet: instant period matching report's periodOfReport ---
    if is_balance:
        for f in classified["instant"]:
            if f["period_start"] == report_period or is_target_period(f["period_start"], report_period):
                val = _parse_value(f["value"])
                if val is not None:
                    return val, f["concept"], None, _fact_source(f)
        return None, None, None, "xbrl"

    # --- Duration items: quarterly first ---
    # Filter quarterly facts to target period (within 7 days of report's periodOfReport)
    target_quarterly = []
    for f in classified["quarterly"]:
        pe = f["period_end"]
        if pe and pe != "null" and is_target_period(pe, report_period):
            target_quarterly.append(f)

    if target_quarterly:
        # Pick by concept priority
        for qn in concept_qnames:
            for f in target_quarterly:
                if f["concept"] == qn:
                    val = _parse_value(f["value"])
                    if val is not None:
                        return val, f["concept"], None, _fact_source(f)
        # Had quarterly but no parseable value
        return None, None, None, "xbrl"

    # --- No direct quarterly. For EPS: null (never derive by subtraction) ---
    if is_eps:
        return None, None, None, "xbrl"

    # --- Cash flow YTD derivation (Q2/Q3) ---
    if is_cashflow_ytd and all_facts_for_derivation:
        # Check if we have semi_annual (H1 YTD) or nine_month — derive quarterly
        val, concept, derivation = _derive_cashflow_quarterly(concept_qnames, report_period,
                                                               all_facts_for_derivation, cross_period_facts)
        return val, concept, derivation, "xbrl"

    # --- Income statement: no quarterly available (could be Q4 from 10-K) ---
    # Q4 derivation happens at a higher level after all periods are processed
    return None, None, None, "xbrl"


def _derive_cashflow_quarterly(concept_qnames: list[str], report_period: str,
                                all_facts: list[dict],
                                cross_period_facts: dict[str, list[dict]] | None,
                                ) -> tuple[float | None, str | None, dict | None]:
    """Derive quarterly cash flow from YTD periods in the same filing."""
    # Classify all facts for this concept
    by_type: dict[str, list[dict]] = {"quarterly": [], "semi_annual": [],
                                       "nine_month": [], "annual": [], "other": []}
    for f in all_facts:
        if f["concept"] not in concept_qnames:
            continue
        ptype = classify_period(f["period_start"], f["period_end"])
        if ptype in by_type:
            by_type[ptype].append(f)

    # Check for semi_annual (H1 YTD) — means this is Q2
    semi_vals = [f for f in by_type["semi_annual"]
                 if f["period_end"] and f["period_end"] != "null"
                 and is_target_period(f["period_end"], report_period)]
    if semi_vals:
        h1_fact = semi_vals[0]
        h1_val = _parse_value(h1_fact["value"])
        if h1_val is not None and cross_period_facts:
            q1_val, q1_acc, q1_form, q1_src = _find_cross_period_value(
                concept_qnames, report_period, cross_period_facts, "quarterly")
            if q1_val is not None:
                return (h1_val - q1_val, h1_fact["concept"],
                        {"method": "h1_ytd_minus_q1",
                         "inputs": [{"accession": h1_fact.get("accession", ""), "form": h1_fact.get("form", ""), "source": _fact_source(h1_fact), "role": "h1_ytd"},
                                    {"accession": q1_acc, "form": q1_form, "source": q1_src, "role": "q1"}]})

    # Check for nine_month (9M YTD) — means this is Q3
    nine_vals = [f for f in by_type["nine_month"]
                 if f["period_end"] and f["period_end"] != "null"
                 and is_target_period(f["period_end"], report_period)]
    if nine_vals:
        nine_fact = nine_vals[0]
        nine_val = _parse_value(nine_fact["value"])
        if nine_val is not None and cross_period_facts:
            h1_val, h1_acc, h1_form, h1_src = _find_cross_period_value(
                concept_qnames, report_period, cross_period_facts, "semi_annual")
            if h1_val is not None:
                return (nine_val - h1_val, nine_fact["concept"],
                        {"method": "9m_ytd_minus_h1",
                         "inputs": [{"accession": nine_fact.get("accession", ""), "form": nine_fact.get("form", ""), "source": _fact_source(nine_fact), "role": "9m_ytd"},
                                    {"accession": h1_acc, "form": h1_form, "source": h1_src, "role": "h1_ytd"}]})

    return None, None, None


def _find_cross_period_value(concept_qnames: list[str], current_period: str,
                              cross_period_facts: dict[str, list[dict]],
                              target_ptype: str,
                              delta_range: tuple[int, int] = (60, 120),
                              ) -> tuple[float | None, str, str, str]:
    """Find a value from a prior period, honoring newest-first filing overlay.

    Args:
        concept_qnames: concepts to search (priority order)
        current_period: current period's periodOfReport
        cross_period_facts: all facts keyed by periodOfReport
        target_ptype: period type to match ("quarterly", "semi_annual", etc.)
        delta_range: (min_days, max_days) between current and target period

    Returns: (value, accession, form, source)
    """
    current_date = date.fromisoformat(current_period)
    for period_str, facts in sorted(cross_period_facts.items(), reverse=True):
        period_date = date.fromisoformat(period_str)
        delta_days = (current_date - period_date).days
        if not (delta_range[0] <= delta_days <= delta_range[1]):
            continue

        # Group by accession, sort newest-first (same overlay logic as main extraction)
        by_acc: dict[str, list[dict]] = {}
        acc_filed: dict[str, str] = {}
        acc_form: dict[str, str] = {}
        for f in facts:
            a = f.get("accession", "")
            by_acc.setdefault(a, []).append(f)
            if a not in acc_filed:
                acc_filed[a] = f.get("filed", "")
                acc_form[a] = f.get("form", "")
        sorted_accs = sorted(by_acc.keys(), key=lambda a: acc_filed.get(a, ""), reverse=True)
        sorted_accs = [a for a in sorted_accs if a not in ZERO_FACT_DENYLIST]

        # Walk filings newest-first, concepts in priority order
        for acc in sorted_accs:
            for qn in concept_qnames:
                for f in by_acc[acc]:
                    if f["concept"] != qn:
                        continue
                    ptype = classify_period(f["period_start"], f["period_end"])
                    if ptype != target_ptype:
                        continue
                    pe = f["period_end"] if target_ptype != "instant" else f["period_start"]
                    if pe and pe != "null" and is_target_period(pe, period_str):
                        val = _parse_value(f["value"])
                        if val is not None:
                            return val, acc, acc_form.get(acc, ""), _fact_source(f)
    return None, "", "", "xbrl"


# ── Per-period metric extraction ─────────────────────────────────────────

def _extract_period_metrics(period: str, period_facts: list[dict],
                             cross_period_facts: dict[str, list[dict]],
                             ) -> tuple[dict, dict, list[dict]]:
    """Extract all metrics for a single period from XBRL facts.

    Returns: (metrics_dict, provenance_dict, derived_metrics_list)
    """
    # Group facts by (accession, filed) → newest first
    filings: dict[str, list[dict]] = {}
    filing_meta: dict[str, dict] = {}  # accession → {form, filed}
    for f in period_facts:
        acc = f["accession"]
        filings.setdefault(acc, []).append(f)
        if acc not in filing_meta:
            filing_meta[acc] = {"form": f["form"], "filed": f["filed"]}

    # Sort filings newest-first (by filed timestamp)
    sorted_accessions = sorted(filing_meta.keys(),
                                key=lambda a: filing_meta[a]["filed"],
                                reverse=True)

    # Filter out denylist
    sorted_accessions = [a for a in sorted_accessions if a not in ZERO_FACT_DENYLIST]

    metrics: dict[str, float | None] = {}
    provenance: dict[str, dict] = {}
    derived_list: list[dict] = []
    concept_used: dict[str, str | None] = {}  # field → concept qname used

    # Per-metric amendment overlay: walk filings newest-first
    for field, qnames, stmt_type in METRIC_REGISTRY:
        found = False
        for acc in sorted_accessions:
            facts = filings[acc]
            val, concept, derivation, fact_source = _extract_metric_from_facts(
                facts, qnames, period, stmt_type,
                all_facts_for_derivation=facts,
                cross_period_facts=cross_period_facts,
            )
            if val is not None:
                metrics[field] = val
                concept_used[field] = concept
                if derivation:
                    # Derived value — provenance must reflect derivation, not direct extraction
                    provenance[field] = {"derived": True, **derivation}
                    derived_list.append({"metric": field, **derivation})
                else:
                    provenance[field] = {"accession": acc, "form": filing_meta[acc]["form"], "source": fact_source}
                found = True
                break
        if not found:
            metrics[field] = None
            concept_used[field] = None

    return metrics, provenance, derived_list


def _derive_q4(q4_period: str, q4_facts: list[dict],
               all_period_facts: dict[str, list[dict]],
               q4_metrics: dict, q4_provenance: dict, q4_derived: list,
               sorted_periods: list[str], gaps: list) -> None:
    """Attempt Q4 derivation for missing income/cash flow metrics.

    Modifies q4_metrics, q4_provenance, q4_derived in place.
    """
    # Find the 10-K accession for annual values
    q4_filings: dict[str, list[dict]] = {}
    q4_filing_meta: dict[str, dict] = {}
    for f in q4_facts:
        acc = f["accession"]
        q4_filings.setdefault(acc, []).append(f)
        if acc not in q4_filing_meta:
            q4_filing_meta[acc] = {"form": f["form"], "filed": f["filed"]}

    sorted_q4_accs = sorted(q4_filing_meta.keys(),
                             key=lambda a: q4_filing_meta[a]["filed"],
                             reverse=True)
    sorted_q4_accs = [a for a in sorted_q4_accs if a not in ZERO_FACT_DENYLIST]

    # Find Q3 period (the period just before Q4 in sorted_periods)
    q4_idx = None
    for i, p in enumerate(sorted_periods):
        if p == q4_period:
            q4_idx = i
            break
    q3_period = sorted_periods[q4_idx + 1] if q4_idx is not None and q4_idx + 1 < len(sorted_periods) else None

    for field, qnames, stmt_type in METRIC_REGISTRY:
        if q4_metrics.get(field) is not None:
            continue  # Already has a value
        if stmt_type == "balance":
            continue  # Balance sheet uses instant — no derivation needed
        if any(qn in _EPS_CONCEPTS for qn in qnames):
            continue  # EPS handled separately below

        is_cashflow_ytd = any(qn in _CASH_FLOW_YTD_CONCEPTS for qn in qnames)

        # Try FY MINUS 9M YTD first
        annual_val = None
        annual_acc = None
        annual_src = "xbrl"
        annual_form = ""
        for acc in sorted_q4_accs:
            for qn in qnames:
                for f in q4_filings.get(acc, []):
                    if f["concept"] != qn:
                        continue
                    ptype = classify_period(f["period_start"], f["period_end"])
                    if ptype == "annual":
                        # Annual period_end must be within 7 days of the Q4 report's periodOfReport
                        # (10-K has multiple annual facts: current FY + prior FY comparatives)
                        pe = f["period_end"]
                        if not pe or pe == "null" or not is_target_period(pe, q4_period):
                            continue
                        v = _parse_value(f["value"])
                        if v is not None:
                            annual_val = v
                            annual_acc = acc
                            annual_src = _fact_source(f)
                            annual_form = q4_filing_meta.get(acc, {}).get("form", "")
                            break
                if annual_val is not None:
                    break
            if annual_val is not None:
                break

        if annual_val is None:
            continue  # No annual value — can't derive

        # Try 9M YTD from Q3 period (newest-first filing overlay via helper)
        nine_month_val = None
        nine_month_acc = ""
        nine_month_form = ""
        nine_month_src = "xbrl"
        if q3_period and q3_period in all_period_facts:
            # Build a single-period dict for the helper
            q3_lookup = {q3_period: all_period_facts[q3_period]}
            nine_month_val, nine_month_acc, nine_month_form, nine_month_src = (
                _find_cross_period_value(qnames, q4_period, q3_lookup, "nine_month",
                                         delta_range=(0, 200)))  # Q3→Q4 gap varies

        if nine_month_val is not None:
            q4_val = annual_val - nine_month_val
            q4_metrics[field] = q4_val
            derivation_inputs = [
                {"accession": annual_acc, "form": annual_form, "source": annual_src, "role": "annual"},
                {"accession": nine_month_acc, "form": nine_month_form, "source": nine_month_src, "role": "9m_ytd"},
            ]
            q4_provenance[field] = {"derived": True, "method": "fy_minus_9m_ytd", "inputs": derivation_inputs}
            q4_derived.append({"metric": field, "method": "fy_minus_9m_ytd", "inputs": derivation_inputs})
            continue

        # Fallback: FY MINUS Q1+Q2+Q3 (newest-first overlay per prior period)
        prior_q_vals = []
        prior_q_inputs = []
        if q4_idx is not None:
            for offset in range(1, 4):
                pi = q4_idx + offset
                if pi >= len(sorted_periods):
                    break
                prior_period = sorted_periods[pi]
                if prior_period not in all_period_facts:
                    break
                prior_lookup = {prior_period: all_period_facts[prior_period]}
                fval, facc, fform, fsrc = _find_cross_period_value(
                    qnames, q4_period, prior_lookup, "quarterly",
                    delta_range=(0, 400))  # wide range — we already know the period
                if fval is not None:
                    prior_q_vals.append(fval)
                    prior_q_inputs.append({"accession": facc, "form": fform, "source": fsrc, "role": f"q{offset}"})
                else:
                    break

        if len(prior_q_vals) == 3:
            q4_val = annual_val - sum(prior_q_vals)
            q4_metrics[field] = q4_val
            inputs = [{"accession": annual_acc, "form": annual_form, "source": annual_src, "role": "annual"}] + prior_q_inputs
            q4_provenance[field] = {"derived": True, "method": "fy_minus_q1q2q3", "inputs": inputs}
            q4_derived.append({"metric": field, "method": "fy_minus_q1q2q3", "inputs": inputs})
        else:
            gaps.append({"type": "missing_metric", "period": q4_period, "metric": field,
                         "reason": f"Q4 derivation failed: annual={annual_val is not None}, 9m_ytd={nine_month_val is not None}, prior_q_count={len(prior_q_vals)}"})

    # Q4 EPS special handling
    if q4_metrics.get("eps_diluted") is None:
        net_income = q4_metrics.get("net_income")
        # Check for direct Q4 diluted_shares (quarterly fact, not annual)
        q4_shares = None
        shares_acc = ""
        shares_form = ""
        shares_src = "xbrl"
        for acc in sorted_q4_accs:
            for f in q4_filings.get(acc, []):
                if f["concept"] == "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding":
                    ptype = classify_period(f["period_start"], f["period_end"])
                    if ptype == "quarterly":
                        pe = f["period_end"]
                        if pe and pe != "null" and is_target_period(pe, q4_period):
                            q4_shares = _parse_value(f["value"])
                            shares_acc = acc
                            shares_form = q4_filing_meta.get(acc, {}).get("form", "")
                            shares_src = _fact_source(f)
                            break
            if q4_shares is not None:
                break

        if net_income is not None and q4_shares is not None and q4_shares != 0:
            q4_metrics["eps_diluted"] = round(net_income / q4_shares, 4)
            q4_metrics["diluted_shares"] = q4_shares
            # Provenance — trace both inputs fully
            ni_prov = q4_provenance.get("net_income", {})
            ni_acc = ni_prov.get("accession", "")
            ni_form = ni_prov.get("form", "")
            ni_src = ni_prov.get("source", "xbrl")
            # net_income may itself be derived — extract accession/form/source from first input
            if ni_prov.get("derived") and ni_prov.get("inputs"):
                ni_acc = ni_prov["inputs"][0].get("accession", "")
                ni_form = ni_prov["inputs"][0].get("form", "")
                ni_src = ni_prov["inputs"][0].get("source", "xbrl")
            eps_derivation = {"method": "net_income_div_shares",
                              "inputs": [
                                  {"metric": "net_income", "accession": ni_acc, "form": ni_form, "source": ni_src, "role": "numerator"},
                                  {"metric": "diluted_shares", "accession": shares_acc, "form": shares_form, "source": shares_src, "role": "denominator"},
                              ]}
            q4_provenance["eps_diluted"] = {"derived": True, **eps_derivation}
            q4_derived.append({"metric": "eps_diluted", **eps_derivation})


# ── FSC Extraction ───────────────────────────────────────────────────────

def _extract_fsc(manager, ticker: str, periods: list[str], as_of: str | None,
                  gaps: list) -> dict[str, list[dict]]:
    """Extract facts from FinancialStatementContent for given periods.

    Returns: {period_str: [fact_dicts]} in same format as XBRL extraction.
    """
    result = manager.execute_cypher_query_all(
        _FSC_QUERY,
        {"ticker": ticker, "periods": periods, "as_of": as_of},
    )

    # Group by period → accession → statements
    by_period_acc: dict[str, dict[str, dict]] = {}
    for rec in result:
        period = rec["period"]
        acc = rec["accession"]
        by_period_acc.setdefault(period, {}).setdefault(acc, {
            "form": rec["form"], "filed": rec["filed"], "statements": {}
        })
        by_period_acc[period][acc]["statements"][rec["statement_type"]] = rec["fs_value"]

    # Convert FSC JSON into fact-like dicts
    by_period: dict[str, list[dict]] = {}
    for period, accessions in by_period_acc.items():
        facts = []
        for acc, meta in accessions.items():
            for stmt_type, fs_json_str in meta["statements"].items():
                try:
                    fs_data = json.loads(fs_json_str) if isinstance(fs_json_str, str) else fs_json_str
                except (json.JSONDecodeError, TypeError):
                    continue
                for concept_key, entries in fs_data.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        # Consolidated filter: skip entries with segment
                        if "segment" in entry:
                            continue
                        # Map unqualified concept to qualified
                        qualified = f"us-gaap:{concept_key}"
                        if qualified not in _CONCEPT_TO_FIELD:
                            continue

                        # Parse period
                        period_info = entry.get("period", {})
                        if "instant" in period_info:
                            p_start = period_info["instant"]
                            p_end = None
                        else:
                            p_start = period_info.get("startDate")
                            p_end = period_info.get("endDate")
                        if not p_start:
                            continue

                        # Include period in synthetic context_id so dedupe
                        # distinguishes quarterly vs YTD vs annual rows
                        fsc_ctx = f"fsc_{acc}_{concept_key}_{p_start}_{p_end}"
                        facts.append({
                            "concept": qualified,
                            "value": entry.get("value"),
                            "decimals": entry.get("decimals"),
                            "context_id": fsc_ctx,
                            "unit_ref": entry.get("unitRef", ""),
                            "period_start": p_start,
                            "period_end": p_end,
                            "form": meta["form"],
                            "accession": acc,
                            "filed": meta["filed"],
                        })

        if facts:
            # Dedupe per-accession (same rationale as XBRL path)
            by_acc: dict[str, list[dict]] = {}
            for f in facts:
                by_acc.setdefault(f["accession"], []).append(f)
            deduped = []
            for acc_facts in by_acc.values():
                deduped.extend(dedupe_facts(acc_facts))
            by_period[period] = deduped

    return by_period


# ── Fiscal Labeling ──────────────────────────────────────────────────────

def _get_fiscal_labels(manager, ticker: str, periods: list[str], as_of: str | None,
                        fye_month: int | None) -> dict[str, str]:
    """Get fiscal labels for periods using the exact guidance extractor pattern.

    Logic from get_quarterly_filings.py:
    1. Compute fallback via period_to_fiscal(period, fye_month, form_type)
    2. Parse XBRL DEI identity via parse_xbrl_fiscal_identity()
    3. Check XBRL_DENY_PERIODIC_ACCESSIONS denylist
    4. Use should_use_xbrl_fiscal() proximity guard to choose XBRL vs fallback
    5. Dedup by fiscal_key (keep newest period per key)

    Returns: {period_str: "Q1_FY2026"}
    """
    # Import the exact functions from the guidance extractor
    try:
        from get_quarterly_filings import (
            parse_xbrl_fiscal_identity,
            should_use_xbrl_fiscal,
            XBRL_DENY_PERIODIC_ACCESSIONS,
        )
    except ImportError:
        # Fallback: define locally if import fails (shouldn't happen — same sys.path)
        parse_xbrl_fiscal_identity = _parse_xbrl_fiscal_identity_fallback
        should_use_xbrl_fiscal = _should_use_xbrl_fiscal_fallback
        XBRL_DENY_PERIODIC_ACCESSIONS = set()

    try:
        from fiscal_math import period_to_fiscal
    except ImportError:
        period_to_fiscal = None

    # Query DEI facts — returns per-filing (period, form, accession, fiscal_period, fiscal_year)
    dei_rows = manager.execute_cypher_query_all(
        _DEI_FISCAL_QUERY,
        {"ticker": ticker, "periods": periods, "as_of": as_of},
    )

    # Build per-period label: newest filing first (query ORDER BY filed DESC)
    labels: dict[str, str] = {}
    for rec in dei_rows:
        period = rec["period"]
        if period in labels:
            continue  # Already resolved (newest filing wins)

        form_type = rec.get("form", "10-Q")
        accession = rec.get("accession", "")

        # Step 1: Compute fallback from period_to_fiscal
        fallback_fiscal = None
        if period_to_fiscal and fye_month is not None:
            d = date.fromisoformat(period)
            # Use actual form_type from the filing (not a heuristic)
            base_form = form_type.replace("/A", "")  # 10-Q/A → 10-Q, 10-K/A → 10-K
            fy, q = period_to_fiscal(d.year, d.month, d.day, fye_month, base_form)
            fallback_fiscal = (fy, q)

        # Step 2: Parse XBRL DEI identity
        xbrl_fiscal = parse_xbrl_fiscal_identity(
            rec.get("fiscal_year"), rec.get("fiscal_period"))

        # Step 3: Choose — exact logic from get_quarterly_filings.py
        # Guard: fallback_fiscal can be None when fye_month is unavailable
        if accession in XBRL_DENY_PERIODIC_ACCESSIONS:
            chosen = fallback_fiscal
        elif fallback_fiscal is not None and should_use_xbrl_fiscal(fallback_fiscal, xbrl_fiscal):
            chosen = xbrl_fiscal
        elif fallback_fiscal is None and xbrl_fiscal is not None:
            chosen = xbrl_fiscal  # No fallback available, trust XBRL
        else:
            chosen = fallback_fiscal

        if chosen:
            fiscal_year, fiscal_quarter = chosen
            labels[period] = f"{fiscal_quarter}_FY{fiscal_year}"

    # Handle periods not in DEI results (FSC-only periods with no XBRL filings)
    if period_to_fiscal and fye_month is not None:
        for period in periods:
            if period in labels:
                continue
            d = date.fromisoformat(period)
            # No filing metadata available — use FYE heuristic for form_type
            adj_month = (d.month - 1 if d.month > 1 else 12) if d.day <= 5 else d.month
            form_hint = "10-K" if adj_month == fye_month else "10-Q"
            fy, q = period_to_fiscal(d.year, d.month, d.day, fye_month, form_hint)
            labels[period] = f"{q}_FY{fy}"

    # Step 5: Dedup by fiscal_key — keep the chronologically newest period per key.
    # This handles 52-week edge cases where two periods map to the same label.
    # Tiebreaker rationale: the newer period has the more recent filing data,
    # matching the guidance extractor's "smallest lag" preference (newest period
    # from the current earnings cycle is closest to the actual fiscal quarter end).
    fiscal_key_to_period: dict[str, str] = {}
    for period in sorted(labels.keys(), reverse=True):  # newest first
        fk = labels[period]
        if fk not in fiscal_key_to_period:
            fiscal_key_to_period[fk] = period
        # else: older period with same key is dropped (newest wins)

    # Rebuild labels with only deduplicated entries
    deduped_labels = {period: labels[period] for period in fiscal_key_to_period.values()}
    return deduped_labels


def _parse_xbrl_fiscal_identity_fallback(xbrl_year_focus, xbrl_period_focus):
    """Local fallback — identical to get_quarterly_filings.parse_xbrl_fiscal_identity."""
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


def _should_use_xbrl_fiscal_fallback(fallback_fiscal, xbrl_fiscal) -> bool:
    """Local fallback — identical to get_quarterly_filings.should_use_xbrl_fiscal."""
    if xbrl_fiscal is None:
        return False
    if fallback_fiscal is None:
        return False
    q_num = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    fallback_year, fallback_quarter = fallback_fiscal
    xbrl_year, xbrl_quarter = xbrl_fiscal
    year_diff = xbrl_year - fallback_year
    quarter_diff = q_num[xbrl_quarter] - q_num[fallback_quarter]
    return abs(year_diff) <= 1 and abs(quarter_diff) <= 1


# ── Segment Inventory ────────────────────────────────────────────────────

def _build_segment_inventory(manager, accession: str, revenue_concept: str | None,
                              gaps: list) -> dict | None:
    """Build segment inventory for the most recent quarter."""
    if not accession:
        return None

    concepts_to_query = []
    if revenue_concept:
        concepts_to_query.append(revenue_concept)
    concepts_to_query.append("us-gaap:OperatingIncomeLoss")
    concepts_to_query = list(dict.fromkeys(concepts_to_query))

    # Step 1: Get member qnames + labels from XBRL
    result = manager.execute_cypher_query_all(
        _SEGMENT_QUERY,
        {"accession": accession, "concepts": concepts_to_query},
    )

    if not result:
        return None

    # Group by concept → members
    concept_members: dict[str, list[dict]] = {}
    for rec in result:
        concept = rec["concept"]
        concept_members.setdefault(concept, []).append({
            "qname": rec["member_qname"],
            "label": rec["member_label"],
        })

    if not concept_members:
        return None

    # Step 2: Get axis grouping from FSC (primary) or standard map (fallback)
    fsc_axis_map = _get_fsc_axis_map(manager, accession)

    # Build inventory
    inventory: dict[str, dict] = {}
    for concept, members in concept_members.items():
        # Determine the output key
        if concept == "us-gaap:OperatingIncomeLoss":
            inv_key = "operating_income"
        else:
            inv_key = "revenue"

        axes: dict[str, dict] = {}
        for m in members:
            mqn = m["qname"]
            # Tier 1: FSC axis
            axis = fsc_axis_map.get(mqn)
            # Tier 2: Standard map
            if not axis:
                axis = STANDARD_MEMBER_AXIS.get(mqn)
            # Tier 3: Unknown
            if not axis:
                axis = "unknown_axis"

            kind = AXIS_KIND.get(axis, "business")
            axes.setdefault(axis, {"kind": kind, "members": []})
            # Avoid duplicates
            if not any(em["qname"] == mqn for em in axes[axis]["members"]):
                axes[axis]["members"].append(m)

        inventory[inv_key] = {"concept": concept, "axes": axes}

    return inventory


def _get_fsc_axis_map(manager, accession: str) -> dict[str, str]:
    """Parse FSC JSON to extract member → axis mapping."""
    result = manager.execute_cypher_query_all(
        _FSC_FOR_SEGMENTS_QUERY,
        {"accession": accession},
    )
    axis_map: dict[str, str] = {}
    for rec in result:
        try:
            fs_data = json.loads(rec["fs_value"]) if isinstance(rec["fs_value"], str) else rec["fs_value"]
        except (json.JSONDecodeError, TypeError):
            continue
        for concept_key, entries in fs_data.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                seg = entry.get("segment")
                if not seg or not isinstance(seg, dict):
                    continue
                em = seg.get("explicitMember")
                if not em:
                    continue
                # Handle both single and list of explicitMembers
                if isinstance(em, dict):
                    em = [em]
                elif not isinstance(em, list):
                    continue
                for member_info in em:
                    dim = member_info.get("dimension", "")
                    member_val = member_info.get("$t", "")
                    if dim and member_val:
                        axis_map[member_val] = dim
    return axis_map


# ── Computed metrics ─────────────────────────────────────────────────────

def _compute_derived(m: dict) -> None:
    """Compute derived ratios in place."""
    rev = m.get("revenue")
    ni = m.get("net_income")
    ocf = m.get("operating_cash_flow")
    capex = m.get("capex")

    # Free cash flow
    if ocf is not None and capex is not None:
        m["free_cash_flow"] = ocf - capex
    else:
        m["free_cash_flow"] = None

    # Gross margin
    gp = m.get("gross_profit")
    if gp is not None and rev is not None and rev != 0:
        m["gross_margin_pct"] = round(gp / rev * 100, 1)
    else:
        m["gross_margin_pct"] = None

    # Operating margin
    oi = m.get("operating_income")
    if oi is not None and rev is not None and rev != 0:
        m["operating_margin_pct"] = round(oi / rev * 100, 1)
    else:
        m["operating_margin_pct"] = None

    # Net margin
    if ni is not None and rev is not None and rev != 0:
        m["net_margin_pct"] = round(ni / rev * 100, 1)
    else:
        m["net_margin_pct"] = None

    # R&D % revenue
    rd = m.get("rd_expense")
    if rd is not None and rev is not None and rev != 0:
        m["rd_pct_revenue"] = round(rd / rev * 100, 1)
    else:
        m["rd_pct_revenue"] = None

    # Effective tax rate
    tax = m.get("income_tax")
    if tax is not None and ni is not None and (ni + tax) != 0:
        m["effective_tax_rate"] = round(tax / (ni + tax) * 100, 1)
    else:
        m["effective_tax_rate"] = None

    # Debt-to-equity
    ltd = m.get("long_term_debt")
    eq = m.get("stockholders_equity")
    if ltd is not None and eq is not None and eq != 0:
        m["debt_to_equity"] = round(ltd / eq, 2)
    else:
        m["debt_to_equity"] = None


# ── Main Builder ─────────────────────────────────────────────────────────

def build_prior_financials(ticker: str, quarter_info: dict,
                           as_of_ts: str | None = None,
                           out_path: str | None = None,
                           allow_yahoo: bool = False) -> dict:
    """Build prior_financials.v1 packet.

    Args:
        ticker: company ticker
        quarter_info: dict with 'period_of_report', 'filed_8k', 'market_session', 'quarter_label'
        as_of_ts: ISO8601 timestamp for PIT (None = live mode)
        out_path: output file path (None = /tmp/prior_financials_{TICKER}.json)
        allow_yahoo: enable Yahoo Finance as Fallback 2

    Returns:
        prior_financials.v1 dict
    """
    _load_env()
    ticker = ticker.upper()
    mode = "historical" if as_of_ts else "live"
    current_period = quarter_info.get("period_of_report", "")
    gaps: list[dict] = []

    if not current_period:
        raise ValueError("period_of_report is required in quarter_info")

    # Connect to Neo4j
    try:
        from neograph.Neo4jConnection import get_manager
        manager = get_manager()
    except Exception as e:
        gaps.append({"type": "connection_failure", "source": "neo4j",
                     "reason": f"Neo4j connection failed: {e}"})
        return _assemble_packet(ticker, current_period, as_of_ts, mode, [], {}, gaps, None, out_path)

    # Get FYE month for fiscal labeling
    fye_month = _get_fye_month(ticker, gaps)

    # ── Step 1: XBRL extraction ──
    print(f"  Querying XBRL facts for {ticker}...", file=sys.stderr)
    xbrl_facts = _extract_xbrl(manager, ticker, current_period, as_of_ts, gaps)
    xbrl_periods = set(xbrl_facts.keys())
    print(f"  Found {len(xbrl_periods)} XBRL periods: {sorted(xbrl_periods, reverse=True)}", file=sys.stderr)

    # ── Step 2: FSC period discovery + extraction ──
    # Discover ALL periods (including those without COMPLETED XBRL)
    all_periods_result = manager.execute_cypher_query_all(
        _ALL_PERIODS_QUERY,
        {"ticker": ticker, "current_period": current_period,
         "as_of": as_of_ts, "limit": _OVERFETCH_QUARTERS},
    )
    all_periods = {rec["period"] for rec in all_periods_result}
    fsc_only_periods = all_periods - xbrl_periods

    # Fetch FSC for ALL target periods — not just fsc_only_periods.
    # Reason: within an XBRL period, an amendment (10-Q/A) may lack COMPLETED XBRL
    # but have FSC data. The per-metric amendment overlay needs these FSC facts
    # alongside the XBRL facts from the original filing.
    all_target_periods = sorted(all_periods | xbrl_periods, reverse=True)[:_OVERFETCH_QUARTERS]
    fsc_facts: dict[str, list[dict]] = {}
    if all_target_periods:
        fsc_facts = _extract_fsc(manager, ticker, all_target_periods, as_of_ts, gaps)
        fsc_period_count = sum(1 for p in fsc_facts if p in fsc_only_periods)
        if fsc_only_periods:
            print(f"  FSC-only periods: {sorted(fsc_only_periods, reverse=True)}", file=sys.stderr)
        fsc_supplemental = sum(1 for p in fsc_facts if p in xbrl_periods and fsc_facts[p])
        if fsc_supplemental:
            print(f"  FSC supplemental for {fsc_supplemental} XBRL periods", file=sys.stderr)

    # ── Step 3: Merge periods and extract metrics ──
    # Combine XBRL + FSC facts per period. Both sources available for
    # per-metric amendment overlay (newest-first across all filings).
    all_period_facts: dict[str, list[dict]] = {}
    for p, facts in xbrl_facts.items():
        all_period_facts[p] = list(facts)  # copy to avoid mutation
    for p, facts in fsc_facts.items():
        all_period_facts.setdefault(p, []).extend(facts)

    sorted_periods = sorted(all_period_facts.keys(), reverse=True)

    # Keep overfetch pool — fiscal-key dedup in Step 7 may drop periods,
    # and we cap to _HISTORY_QUARTERS after dedup, not before.
    sorted_periods = sorted_periods[:_OVERFETCH_QUARTERS]

    quarters: list[dict] = []
    revenue_concept_found: str | None = None  # For segment inventory

    for period in sorted_periods:
        facts = all_period_facts[period]
        if not facts:
            gaps.append({"type": "missing_period", "period": period,
                         "reason": "No COMPLETED XBRL or FSC for this period"})
            continue

        metrics, provenance, derived = _extract_period_metrics(period, facts, all_period_facts)

        # Determine primary filing (newest)
        filing_dates: dict[str, str] = {}
        filing_forms: dict[str, str] = {}
        for f in facts:
            acc = f.get("accession", "")
            if acc and acc not in filing_dates:
                filing_dates[acc] = f.get("filed", "")
                filing_forms[acc] = f.get("form", "")
        if filing_dates:
            primary_acc = max(filing_dates.keys(), key=lambda a: filing_dates.get(a, ""))
        else:
            primary_acc = ""

        # Determine primary source from actual provenance (not period membership).
        # Direct entries have top-level "source"; derived entries have source inside "inputs[]".
        source_counts: dict[str, int] = {"xbrl": 0, "fsc": 0}
        for pv in provenance.values():
            if not isinstance(pv, dict):
                continue
            if pv.get("derived") and pv.get("inputs"):
                # Derived: count the dominant source across all inputs
                for inp in pv["inputs"]:
                    s = inp.get("source", "xbrl")
                    source_counts[s] = source_counts.get(s, 0) + 1
            else:
                src = pv.get("source", "xbrl")
                source_counts[src] = source_counts.get(src, 0) + 1
        source = max(source_counts, key=lambda s: source_counts[s]) if any(source_counts.values()) else ("fsc" if period in fsc_only_periods else "xbrl")

        # Track revenue concept for segment inventory (from most recent quarter)
        if revenue_concept_found is None:
            for field, qnames, _ in METRIC_REGISTRY:
                if field == "revenue":
                    for qn in qnames:
                        for f in facts:
                            if f["concept"] == qn and _parse_value(f["value"]) is not None:
                                revenue_concept_found = qn
                                break
                        if revenue_concept_found:
                            break
                    break

        quarters.append({
            "period": period,
            "metrics": metrics,
            "provenance": provenance,
            "derived": derived,
            "primary_accession": primary_acc,
            "primary_form": filing_forms.get(primary_acc, ""),
            "primary_filed": filing_dates.get(primary_acc, ""),
            "primary_source": source,
        })

    # ── Step 4: Q4 derivation ──
    # Identify Q4 quarters (10-K filings) that need derivation
    for q in quarters:
        if q["primary_form"] in ("10-K", "10-K/A"):
            q4_facts = all_period_facts.get(q["period"], [])
            _derive_q4(q["period"], q4_facts, all_period_facts,
                       q["metrics"], q["provenance"], q["derived"],
                       sorted_periods, gaps)

    # ── Step 5: Cash flow YTD derivation for non-Q4 quarters ──
    for q in quarters:
        if q["primary_form"] in ("10-K", "10-K/A"):
            continue  # Q4 handled above
        period = q["period"]
        facts = all_period_facts.get(period, [])
        for field, qnames, stmt_type in METRIC_REGISTRY:
            if stmt_type != "cashflow":
                continue
            if not any(qn in _CASH_FLOW_YTD_CONCEPTS for qn in qnames):
                continue
            if q["metrics"].get(field) is not None:
                continue  # Already has a value

            # Try cash flow YTD derivation
            val, concept, derivation = _derive_cashflow_quarterly(
                qnames, period, facts, all_period_facts)
            if val is not None:
                q["metrics"][field] = val
                if derivation:
                    q["derived"].append({"metric": field, **derivation})
                    # Also populate provenance for this derived metric
                    q["provenance"][field] = {"derived": True, **derivation}

    # ── Step 6: Compute derived ratios ──
    for q in quarters:
        _compute_derived(q["metrics"])

    # ── Step 7: Fiscal labels (exact guidance extractor logic + dedup by fiscal_key) ──
    fiscal_labels = _get_fiscal_labels(manager, ticker, sorted_periods, as_of_ts, fye_month)

    # Filter out quarters whose periods were dropped by fiscal-key dedup,
    # then cap at _HISTORY_QUARTERS. This handles 52-week edge cases where
    # two raw periods collapse to the same fiscal key.
    valid_periods = set(fiscal_labels.keys())
    quarters = [q for q in quarters if q["period"] in valid_periods]
    quarters = quarters[:_HISTORY_QUARTERS]

    # ── Step 8: Provenance cleanup ──
    for q in quarters:
        q["fiscal_label"] = fiscal_labels.get(q["period"], "")
        # Check if all metrics came from same filing
        accs_used = {v.get("accession") for v in q["provenance"].values()
                     if isinstance(v, dict) and "accession" in v and not v.get("derived")}
        has_derived = any(isinstance(v, dict) and v.get("derived") for v in q["provenance"].values()) or len(q["derived"]) > 0
        if len(accs_used) <= 1 and not has_derived:
            q["provenance"] = {}

    # ── Step 9: Yahoo fallback for missing periods ──
    if allow_yahoo and len(quarters) < _HISTORY_QUARTERS:
        yahoo_quarters = _yahoo_fallback(ticker, current_period, as_of_ts,
                                          {q["period"] for q in quarters},
                                          fye_month, gaps)
        quarters.extend(yahoo_quarters)
        # Re-sort
        quarters.sort(key=lambda q: q["period"], reverse=True)
        quarters = quarters[:_HISTORY_QUARTERS]

    # ── Step 10: Segment inventory ──
    seg_inv = None
    if quarters:
        most_recent = quarters[0]
        if most_recent["primary_source"] == "xbrl" and most_recent["primary_accession"]:
            seg_inv = _build_segment_inventory(manager, most_recent["primary_accession"],
                                                revenue_concept_found, gaps)
            if seg_inv:
                seg_inv["source_quarter"] = most_recent["period"]

    # ── Assemble output ──
    return _assemble_packet(ticker, current_period, as_of_ts, mode,
                            quarters, fiscal_labels, gaps, seg_inv, out_path)


def _assemble_packet(ticker: str, current_period: str, as_of_ts: str | None,
                      mode: str, quarters: list[dict], fiscal_labels: dict,
                      gaps: list, seg_inv: dict | None,
                      out_path: str | None = None) -> dict:
    """Assemble the final prior_financials.v1 packet and write to disk."""
    # Build output quarter rows
    output_quarters = []
    for q in quarters:
        row = {
            "period": q["period"],
            "fiscal_label": q.get("fiscal_label", fiscal_labels.get(q["period"], "")),
            "primary_form": q["primary_form"],
            "primary_accession": q["primary_accession"],
            "primary_filed": q["primary_filed"],
            "primary_source": q["primary_source"],
            "_provenance": q["provenance"],
        }
        # Add all metric fields
        m = q["metrics"]
        for field, _, _ in METRIC_REGISTRY:
            row[field] = m.get(field)
        # Add computed fields
        for computed_field in ("free_cash_flow", "gross_margin_pct", "operating_margin_pct",
                                "net_margin_pct", "rd_pct_revenue", "effective_tax_rate",
                                "debt_to_equity"):
            row[computed_field] = m.get(computed_field)
        row["derived_metrics"] = q["derived"]
        output_quarters.append(row)

    # Build summary
    source_breakdown: dict[str, int] = {"xbrl": 0, "fsc": 0, "yahoo": 0}
    derived_count = 0
    metrics_coverage: dict[str, int] = {}
    for field, _, _ in METRIC_REGISTRY:
        metrics_coverage[field] = 0

    for q in output_quarters:
        src = q["primary_source"]
        source_breakdown[src] = source_breakdown.get(src, 0) + 1
        derived_count += len(q["derived_metrics"])
        for field, _, _ in METRIC_REGISTRY:
            if q.get(field) is not None:
                metrics_coverage[field] += 1

    summary = {
        "quarter_count": len(output_quarters),
        "primary_source_breakdown": source_breakdown,
        "derived_metric_count": derived_count,
        "metrics_coverage": metrics_coverage,
    }

    packet = {
        "schema_version": "prior_financials.v1",
        "ticker": ticker,
        "period_of_report": current_period,
        "as_of_ts": as_of_ts,
        "source_mode": mode,
        "quarters": output_quarters,
        "summary": summary,
        "gaps": gaps,
        "segment_inventory": seg_inv,
        "assembled_at": _now_iso(),
    }

    # Atomic write
    if out_path is None:
        out_path = f"/tmp/prior_financials_{ticker}.json"
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, ensure_ascii=False)
    os.replace(tmp, out_path)

    return packet


# ── Yahoo Fallback ───────────────────────────────────────────────────────

def _yahoo_fallback(ticker: str, current_period: str, as_of_ts: str | None,
                     existing_periods: set[str], fye_month: int | None,
                     gaps: list) -> list[dict]:
    """Fetch missing quarters from Yahoo Finance."""
    try:
        import yfinance as yf
    except ImportError:
        gaps.append({"type": "yahoo_unavailable", "reason": "yfinance not installed"})
        return []

    try:
        t = yf.Ticker(ticker)
        inc = t.quarterly_income_stmt
        cf = t.quarterly_cashflow
    except Exception as e:
        gaps.append({"type": "yahoo_error", "reason": str(e)})
        return []

    quarters = []
    current_date = date.fromisoformat(current_period)

    if inc is not None and not inc.empty:
        for col in inc.columns:
            col_date = col.date() if hasattr(col, "date") else date.fromisoformat(str(col)[:10])
            period_str = col_date.isoformat()

            if period_str >= current_period:
                continue
            if period_str in existing_periods:
                continue

            # PIT filter for Yahoo
            if as_of_ts:
                as_of_date = date.fromisoformat(as_of_ts[:10])
                # Conservative: exclude if within 45 days of as_of
                if (as_of_date - col_date).days < 45:
                    continue

            metrics: dict[str, float | None] = {}
            for field, yahoo_key in YAHOO_FIELD_MAP.items():
                try:
                    if yahoo_key in ("Operating Cash Flow", "Capital Expenditure") and cf is not None:
                        val = cf.loc[yahoo_key, col] if yahoo_key in cf.index else None
                    else:
                        val = inc.loc[yahoo_key, col] if yahoo_key in inc.index else None
                    if val is not None and not (hasattr(val, "__float__") and str(val) == "nan"):
                        metrics[field] = float(val)
                    else:
                        metrics[field] = None
                except (KeyError, TypeError, ValueError):
                    metrics[field] = None

            # Fill remaining registry fields with None
            for field, _, _ in METRIC_REGISTRY:
                if field not in metrics:
                    metrics[field] = None

            _compute_derived(metrics)

            # Fiscal label
            fiscal_label = ""
            if fye_month:
                try:
                    from fiscal_math import period_to_fiscal
                    fy, q = period_to_fiscal(col_date.year, col_date.month, col_date.day,
                                              fye_month, "10-Q")
                    fiscal_label = f"{q}_FY{fy}"
                except ImportError:
                    pass

            quarters.append({
                "period": period_str,
                "metrics": metrics,
                "provenance": {},
                "derived": [],
                "primary_accession": "",
                "primary_form": "",
                "primary_filed": "",
                "primary_source": "yahoo",
                "fiscal_label": fiscal_label,
            })

    return quarters


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print("Usage: build_prior_financials.py TICKER [--pit ISO8601] [--period-of-report DATE] [--out-path PATH] [--allow-yahoo]",
              file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    ticker = args[0]

    pit = _cli_get(args, "--pit")
    period = _cli_get(args, "--period-of-report")
    out_path = _cli_get(args, "--out-path")
    allow_yahoo = "--allow-yahoo" in args

    _load_env()

    # Auto-resolve period_of_report if not provided
    if not period:
        try:
            from neograph.Neo4jConnection import get_manager
            manager = get_manager()
            result = manager.execute_cypher_query_all(
                _PERIOD_OF_REPORT_QUERY,
                {"ticker": ticker.upper()},
            )
            if result:
                period = result[0]["r.periodOfReport"]
                print(f"  Auto-resolved period_of_report: {period}", file=sys.stderr)
            else:
                print(f"Error: No 8-K Item 2.02 found for {ticker}. Use --period-of-report.", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error resolving period_of_report: {e}", file=sys.stderr)
            sys.exit(1)

    quarter_info = {
        "period_of_report": period,
        "filed_8k": pit or _now_iso(),
        "market_session": "",
        "quarter_label": "",
    }

    packet = build_prior_financials(ticker, quarter_info, as_of_ts=pit,
                                     out_path=out_path, allow_yahoo=allow_yahoo)

    path = out_path or f"/tmp/prior_financials_{ticker.upper()}.json"
    s = packet["summary"]
    g = len(packet["gaps"])
    print(f"Wrote {path}")
    print(f"  {s['quarter_count']} quarters | "
          f"sources: {s['primary_source_breakdown']} | "
          f"{s['derived_metric_count']} derived | {g} gaps")
    # Print coverage for key metrics
    cov = s["metrics_coverage"]
    print(f"  revenue={cov.get('revenue', 0)}/{s['quarter_count']} "
          f"net_income={cov.get('net_income', 0)}/{s['quarter_count']} "
          f"eps={cov.get('eps_diluted', 0)}/{s['quarter_count']} "
          f"ocf={cov.get('operating_cash_flow', 0)}/{s['quarter_count']}")


if __name__ == "__main__":
    main()
