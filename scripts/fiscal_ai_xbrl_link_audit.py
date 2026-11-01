#!/usr/bin/env python3
"""Read-only Fiscal.ai KPI-to-XBRL link audit.

This audits how many Fiscal.ai Segment/KPI metrics can be linked to existing
Neo4j XBRL Concepts and/or Members. It intentionally does not write to Neo4j.

The matching posture mirrors guidance extraction:
  - use reviewed exact qname maps where available
  - use exact local-name concept candidates for reviewed financial labels
  - use exact normalized segment/member label matching
  - keep heuristic KPI-prefix member matches separate from strict matches
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/fiscal_ai_segments/fiscal_segments.sqlite"
DEFAULT_OUT = ROOT / "data/fiscal_ai_segments/xbrl_link_audit"
REVENUE_MAP = ROOT / "data/xbrl_maps/revenue_map_783.jsonl"
OPERATING_MAP = ROOT / "data/xbrl_maps/operating_map_783.jsonl"
GUIDANCE_SCRIPT_DIR = ROOT / ".claude/skills/earnings-orchestrator/scripts"


try:
    sys.path.insert(0, str(GUIDANCE_SCRIPT_DIR))
    from concept_resolver import CONCEPT_CANDIDATES as GUIDANCE_CONCEPT_CANDIDATES
    from fiscal_math import _compute_fiscal_dates, period_to_fiscal
    from guidance_ids import normalize_for_member_match, slug
except Exception:
    GUIDANCE_CONCEPT_CANDIDATES = {}
    _compute_fiscal_dates = None
    period_to_fiscal = None

    def slug(text: str) -> str:
        s = text.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s)
        return s.strip("_")

    def normalize_for_member_match(s: str) -> str:
        n = re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))
        n = n.replace("member", "").replace("segment", "")
        if n.endswith("s"):
            n = n[:-1]
        return n


EXTRA_CONCEPT_CANDIDATES = {
    "assets": ("Assets",),
    "capital_expenditures": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditure",
        "PaymentsToAcquireProductiveAssets",
    ),
    "ebt": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ),
    "income_before_tax": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ),
    "net_interest_income": (
        "InterestIncomeExpenseOperatingNet",
        "InterestIncomeExpenseNonOperatingNet",
    ),
    "net_premiums_earned": (
        "PremiumsEarnedNet",
        "PremiumsEarned",
    ),
    "net_premiums_written": (
        "PremiumsWrittenNet",
        "PremiumsWritten",
    ),
    "gross_premiums_earned": ("PremiumsEarned",),
    "gross_premiums_written": ("PremiumsWritten",),
}

CONCEPT_CANDIDATES = dict(GUIDANCE_CONCEPT_CANDIDATES)
for key, values in EXTRA_CONCEPT_CANDIDATES.items():
    existing = tuple(CONCEPT_CANDIDATES.get(key, ()))
    CONCEPT_CANDIDATES[key] = existing + tuple(v for v in values if v not in existing)


SECTION_RULES = {
    "Revenue": {
        "base": "revenue",
        "suffixes": ("Revenue", "Net Sales", "Sales"),
        "map": "revenue",
    },
    "Revenue by Geography": {
        "base": "revenue",
        "suffixes": ("Revenue by Geography", "Revenue", "Net Sales", "Sales"),
        "map": "revenue",
        "geography": True,
    },
    "Net Revenue": {
        "base": "revenue",
        "suffixes": ("Net Revenue", "Revenue"),
        "map": "revenue",
    },
    "Adjusted Revenue": {
        "base": "adjusted_revenue",
        "suffixes": ("Adjusted Revenue", "Revenue"),
    },
    "EBIT": {
        "base": "operating_income",
        "suffixes": (
            "Income from Operations",
            "Operating Income",
            "Operating Profit",
            "EBIT",
            "Income",
        ),
        "map": "operating",
    },
    "EBIT by Geography": {
        "base": "operating_income",
        "suffixes": ("Income from Operations", "Operating Income", "EBIT by Geography", "EBIT"),
        "map": "operating",
        "geography": True,
    },
    "Adjusted EBIT": {
        "base": "adjusted_ebit",
        "suffixes": ("Adjusted EBIT", "EBIT", "Adjusted Operating Income"),
    },
    "Adjusted EBIT by Geography": {
        "base": "adjusted_ebit",
        "suffixes": ("Adjusted EBIT by Geography", "Adjusted EBIT", "EBIT"),
        "geography": True,
    },
    "EBITDA": {
        "base": "ebitda",
        "suffixes": ("EBITDA",),
    },
    "Adjusted EBITDA": {
        "base": "adjusted_ebitda",
        "suffixes": ("Adjusted EBITDA", "EBITDA"),
    },
    "Adjusted EBITDA by Geography": {
        "base": "adjusted_ebitda",
        "suffixes": ("Adjusted EBITDA by Geography", "Adjusted EBITDA", "EBITDA"),
        "geography": True,
    },
    "EBT": {
        "base": "ebt",
        "suffixes": ("Income Before Tax", "Earnings Before Tax", "EBT"),
    },
    "Adjusted EBT": {
        "base": "adjusted_ebt",
        "suffixes": ("Adjusted EBT", "EBT"),
    },
    "EBT by Geography": {
        "base": "ebt",
        "suffixes": ("Income Before Tax", "Earnings Before Tax", "EBT by Geography", "EBT"),
        "geography": True,
    },
    "Gross Profit": {
        "base": "gross_profit",
        "suffixes": ("Gross Profit",),
    },
    "Gross Profit by Geography": {
        "base": "gross_profit",
        "suffixes": ("Gross Profit by Geography", "Gross Profit"),
        "geography": True,
    },
    "Adjusted Gross Profit": {
        "base": "adjusted_gross_profit",
        "suffixes": ("Adjusted Gross Profit", "Gross Profit"),
    },
    "Adjusted Gross Profit by Geography": {
        "base": "adjusted_gross_profit",
        "suffixes": ("Adjusted Gross Profit by Geography", "Adjusted Gross Profit", "Gross Profit"),
        "geography": True,
    },
    "Net Income": {
        "base": "net_income",
        "suffixes": ("Net Income", "Net Earnings"),
    },
    "Adjusted Net Income": {
        "base": "adjusted_net_income",
        "suffixes": ("Adjusted Net Income", "Net Income"),
    },
    "Net Income by Geography": {
        "base": "net_income",
        "suffixes": ("Net Income by Geography", "Net Income", "Net Earnings"),
        "geography": True,
    },
    "Capital Expenditures": {
        "base": "capital_expenditures",
        "suffixes": ("Capital Expenditures", "Capex", "Capital Spending"),
    },
    "Adjusted Capital Expenditures": {
        "base": "adjusted_capital_expenditures",
        "suffixes": ("Adjusted Capital Expenditures", "Capital Expenditures", "Capex"),
    },
    "Capital Expenditures by Geography": {
        "base": "capital_expenditures",
        "suffixes": ("Capital Expenditures by Geography", "Capital Expenditures", "Capex"),
        "geography": True,
    },
    "Assets": {
        "base": "assets",
        "suffixes": ("Assets",),
    },
    "Assets by Geography": {
        "base": "assets",
        "suffixes": ("Assets by Geography", "Assets"),
        "geography": True,
    },
    "Average Assets": {
        "base": "average_assets",
        "suffixes": ("Average Assets", "Assets"),
    },
    "Net Interest Income": {
        "base": "net_interest_income",
        "suffixes": ("Net Interest Income",),
    },
    "Non-Interest Income": {
        "base": "non_interest_income",
        "suffixes": ("Non-Interest Income",),
    },
    "Net Premiums Earned": {
        "base": "net_premiums_earned",
        "suffixes": ("Net Premiums Earned", "Premiums Earned"),
    },
    "Net Premiums Written": {
        "base": "net_premiums_written",
        "suffixes": ("Net Premiums Written", "Premiums Written"),
    },
    "Gross Premiums Earned": {
        "base": "gross_premiums_earned",
        "suffixes": ("Gross Premiums Earned", "Premiums Earned"),
    },
    "Gross Premiums Written": {
        "base": "gross_premiums_written",
        "suffixes": ("Gross Premiums Written", "Premiums Written"),
    },
    "Fee Related Earnings": {
        "base": "fee_related_earnings",
        "suffixes": ("Fee Related Earnings",),
    },
    "Distributable Earnings": {
        "base": "distributable_earnings",
        "suffixes": ("Distributable Earnings",),
    },
    "Funds From Operations": {
        "base": "funds_from_operations",
        "suffixes": ("Funds From Operations", "FFO"),
    },
}


KPI_BASE_SUFFIXES = (
    "Gross Booking Value",
    "Nights and Seats Booked",
    "Annualized Recurring Revenue",
    "Recurring Revenue",
    "Subscription Revenue",
    "Remaining Performance Obligations",
    "Remaining Performance Obligation",
    "RPO to be Recognized Over NTM",
    "Bookings",
    "Backlog",
    "Revenue",
    "Sales",
    "Shipments",
    "Production",
    "Subscribers",
    "Subscriptions",
    "Stores",
    "Branches",
    "Facilities",
    "Beds",
    "Assets",
    "Loans",
    "Deposits",
)

TOTAL_SEGMENT_VALUES = {"", "Total", "Consolidated", "Company", "Corporate Total"}
GENERIC_SEGMENT_VALUES = {"Other", "Eliminations", "Intersegment Eliminations"}
INSTANT_SECTIONS = {"Assets", "Assets by Geography"}


CONCEPT_CACHE_QUERY = """
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers AND rk.formType = '10-K'
WITH c, rk ORDER BY c.ticker, rk.created DESC
WITH c, collect(rk.created)[0] AS last_10k_date
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
WITH c.ticker AS ticker, con.qname AS qname, con.label AS label, count(f) AS usage
ORDER BY ticker, usage DESC
RETURN ticker, collect({qname:qname, label:label, usage:usage}) AS rows
"""


MEMBER_MAP_QUERY = """
MATCH (c:Company)
WHERE c.ticker IN $tickers
WITH c.ticker AS ticker, toString(c.cik) AS cik
WITH ticker, cik,
     CASE WHEN cik =~ '^0+[1-9].*'
          THEN toString(toInteger(cik))
          ELSE cik END AS cik_stripped
MATCH (m:Member)
WHERE m.u_id STARTS WITH cik_stripped + ':' OR m.u_id STARTS WITH cik + ':'
OPTIONAL MATCH (d:Domain)-[:HAS_MEMBER]->(m)
WITH ticker, m.label AS label, m.qname AS qname,
     collect(DISTINCT m.u_id) AS u_ids,
     collect(DISTINCT d.qname) AS domain_qnames
RETURN ticker, label, qname, u_ids[0] AS u_id, domain_qnames[0] AS domain_qname
"""


COMPANY_INFO_QUERY = """
MATCH (c:Company)
WHERE c.ticker IN $tickers
RETURN c.ticker AS ticker,
       c.cik AS cik,
       c.fiscal_year_end_month AS fye_month,
       c.fiscal_year_end_day AS fye_day
"""


XBRL_PERIOD_QUERY = """
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company)
WHERE c.ticker IN $tickers
WITH c.ticker AS ticker, ctx.period_u_id AS period_u_id, count(*) AS usage
RETURN ticker, collect({period_u_id: period_u_id, usage: usage}) AS rows
"""


GUIDANCE_PERIOD_QUERY = """
MATCH (gp:GuidancePeriod)<-[:HAS_PERIOD]-(gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company)
WHERE c.ticker IN $tickers
WITH c.ticker AS ticker, gp.u_id AS u_id, gp.start_date AS start_date,
     gp.end_date AS end_date, gp.period_scope AS period_scope, count(*) AS usage
RETURN ticker, collect({
  u_id: u_id,
  start_date: start_date,
  end_date: end_date,
  period_scope: period_scope,
  usage: usage
}) AS rows
"""


@dataclass
class FiscalMetric:
    symbol: str
    company_slug: str
    company_name: str
    universe_exchange: str
    cik: str
    section: str
    section_key: str
    metric_key: str
    metric_name: str
    period_types: str
    row_count: int
    valued_row_count: int
    first_period_end: str
    last_period_end: str


@dataclass
class FiscalPeriod:
    symbol: str
    company_slug: str
    section: str
    metric_key: str
    metric_name: str
    period_type: str
    period_label: str
    period_end_date: str
    row_count: int
    valued_row_count: int


def metric_identity(company_slug: str, section: str, metric_key: str, metric_name: str) -> tuple[str, str, str, str]:
    return (company_slug, section or "", metric_key, metric_name or metric_key)


def metric_identity_from_metric(metric: FiscalMetric) -> tuple[str, str, str, str]:
    return metric_identity(metric.company_slug, metric.section, metric.metric_key, metric.metric_name)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def local_name(qname: str | None) -> str:
    if not qname:
        return ""
    return qname.split(":", 1)[1] if ":" in qname else qname


def norm_compact(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clean_metric_text(text: str | None, *, drop_all_parentheticals: bool = False) -> str:
    if not text:
        return ""
    out = text.strip()
    out = re.sub(r"\s*\((?:Pre|Post)-[^)]*Reporting\)", "", out, flags=re.I)
    out = re.sub(r"\s*\((?:Latest Currency Rates|Constant Currency)\)", "", out, flags=re.I)
    if drop_all_parentheticals:
        out = re.sub(r"\s*\([^)]*\)", "", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def strip_suffix_segment(metric_name: str, suffixes: Iterable[str]) -> tuple[str, str, str]:
    clean = clean_metric_text(metric_name, drop_all_parentheticals=True)
    for suffix in sorted(set(suffixes), key=len, reverse=True):
        if not suffix:
            continue
        patterns = (
            f"Total {suffix}",
            f"Consolidated {suffix}",
            suffix,
        )
        if any(clean.lower() == p.lower() for p in patterns):
            return "Total", suffix, "section_suffix"
        if clean.lower().endswith(" " + suffix.lower()):
            seg = clean[: -len(suffix)].strip(" -:_")
            if seg.lower() == "total":
                seg = "Total"
            return seg or "Total", suffix, "section_suffix"
    return "", "", ""


def derive_kpi_segment(metric_name: str) -> tuple[str, str, str]:
    clean = clean_metric_text(metric_name, drop_all_parentheticals=True)
    if " - " in clean:
        left, right = clean.split(" - ", 1)
        if left and right:
            return left.strip(), right.strip(), "kpi_dash_prefix"
    for suffix in sorted(KPI_BASE_SUFFIXES, key=len, reverse=True):
        if clean.lower() == f"total {suffix}".lower():
            return "Total", suffix, "kpi_suffix"
        if clean.lower().endswith(" " + suffix.lower()):
            seg = clean[: -len(suffix)].strip(" -:_")
            if seg and seg.lower() != "total":
                return seg, suffix, "kpi_suffix"
    return "", "", ""


def load_jsonl_map(path: Path) -> dict[str, dict]:
    rows = {}
    if not path.exists():
        return rows
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ticker = row.get("ticker")
            if ticker:
                rows[ticker] = row
    return rows


def load_fiscal_metrics(db_path: Path, period_type: str) -> list[FiscalMetric]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    where = ""
    params = []
    if period_type != "all":
        where = "WHERE period_type = ?"
        params.append(period_type)
    query = f"""
    SELECT
      symbol,
      company_slug,
      max(company_name) AS company_name,
      max(universe_exchange) AS universe_exchange,
      max(cik) AS cik,
      coalesce(section, '') AS section,
      coalesce(section_key, '') AS section_key,
      metric_key,
      coalesce(metric_name, metric_key) AS metric_name,
      group_concat(DISTINCT period_type) AS period_types,
      count(*) AS row_count,
      sum(CASE WHEN value_millions_usd IS NOT NULL THEN 1 ELSE 0 END) AS valued_row_count,
      min(period_end_date) AS first_period_end,
      max(period_end_date) AS last_period_end
    FROM fiscal_segments
    {where}
    GROUP BY company_slug, section, metric_key, metric_name
    ORDER BY symbol, section, metric_name, metric_key
    """
    rows = []
    for row in conn.execute(query, params):
        rows.append(
            FiscalMetric(
                symbol=row["symbol"],
                company_slug=row["company_slug"],
                company_name=row["company_name"] or "",
                universe_exchange=row["universe_exchange"] or "",
                cik=row["cik"] or "",
                section=row["section"] or "",
                section_key=row["section_key"] or "",
                metric_key=row["metric_key"],
                metric_name=row["metric_name"] or row["metric_key"],
                period_types=row["period_types"] or "",
                row_count=int(row["row_count"] or 0),
                valued_row_count=int(row["valued_row_count"] or 0),
                first_period_end=row["first_period_end"] or "",
                last_period_end=row["last_period_end"] or "",
            )
        )
    conn.close()
    return rows


def load_fiscal_metric_periods(db_path: Path, period_type: str) -> dict[tuple[str, str, str, str], list[FiscalPeriod]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    where = ""
    params = []
    if period_type != "all":
        where = "WHERE period_type = ?"
        params.append(period_type)
    query = f"""
    SELECT
      symbol,
      company_slug,
      coalesce(section, '') AS section,
      metric_key,
      coalesce(metric_name, metric_key) AS metric_name,
      period_type,
      coalesce(period_label, '') AS period_label,
      period_end_date,
      count(*) AS row_count,
      sum(CASE WHEN value_millions_usd IS NOT NULL THEN 1 ELSE 0 END) AS valued_row_count
    FROM fiscal_segments
    {where}
    GROUP BY company_slug, section, metric_key, metric_name, period_type, period_label, period_end_date
    ORDER BY symbol, section, metric_name, period_type, period_end_date
    """
    out: dict[tuple[str, str, str, str], list[FiscalPeriod]] = defaultdict(list)
    for row in conn.execute(query, params):
        period = FiscalPeriod(
            symbol=row["symbol"],
            company_slug=row["company_slug"],
            section=row["section"] or "",
            metric_key=row["metric_key"],
            metric_name=row["metric_name"] or row["metric_key"],
            period_type=row["period_type"],
            period_label=row["period_label"] or "",
            period_end_date=row["period_end_date"],
            row_count=int(row["row_count"] or 0),
            valued_row_count=int(row["valued_row_count"] or 0),
        )
        out[metric_identity(period.company_slug, period.section, period.metric_key, period.metric_name)].append(period)
    conn.close()
    return dict(out)


def load_annual_period_ends(db_path: Path) -> dict[str, set[str]]:
    conn = sqlite3.connect(db_path)
    out: dict[str, set[str]] = defaultdict(set)
    query = """
    SELECT DISTINCT symbol, period_end_date
    FROM fiscal_segments
    WHERE period_type = 'annual'
      AND coalesce(period_label, '') != 'LTM'
      AND period_end_date IS NOT NULL
    """
    for symbol, period_end in conn.execute(query):
        out[symbol].add(period_end)
    conn.close()
    return dict(out)


def fetch_concept_caches(driver, tickers: list[str], batch_size: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
    with driver.session() as session:
        for batch_no, batch in enumerate(chunks(tickers, batch_size), start=1):
            started = time.time()
            for record in session.run(CONCEPT_CACHE_QUERY, tickers=batch):
                out[record["ticker"]] = [dict(row) for row in record["rows"]]
            print(
                f"concept batch {batch_no}: {len(batch)} tickers in {time.time() - started:.1f}s",
                flush=True,
            )
    return out


def fetch_member_maps(driver, tickers: list[str], batch_size: int) -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = {ticker: defaultdict(list) for ticker in tickers}
    with driver.session() as session:
        for batch_no, batch in enumerate(chunks(tickers, batch_size), start=1):
            started = time.time()
            for record in session.run(MEMBER_MAP_QUERY, tickers=batch):
                entry = {
                    "label": record["label"] or "",
                    "qname": record["qname"] or "",
                    "u_id": record["u_id"] or "",
                    "domain_qname": record["domain_qname"] or "",
                }
                label_norm = normalize_for_member_match(entry["label"])
                if label_norm:
                    out[record["ticker"]][label_norm].append({**entry, "match_key_source": "label"})
                qname_norm = normalize_for_member_match(local_name(entry["qname"]))
                if qname_norm and qname_norm != label_norm:
                    out[record["ticker"]][qname_norm].append({**entry, "match_key_source": "qname"})
            print(
                f"member batch {batch_no}: {len(batch)} tickers in {time.time() - started:.1f}s",
                flush=True,
            )
    return {ticker: dict(values) for ticker, values in out.items()}


def fetch_company_info(driver, tickers: list[str], batch_size: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with driver.session() as session:
        for batch_no, batch in enumerate(chunks(tickers, batch_size), start=1):
            started = time.time()
            for record in session.run(COMPANY_INFO_QUERY, tickers=batch):
                out[record["ticker"]] = {
                    "cik": record["cik"],
                    "fye_month": int(record["fye_month"]) if record["fye_month"] is not None else None,
                    "fye_day": int(record["fye_day"]) if record["fye_day"] is not None else None,
                }
            print(
                f"company batch {batch_no}: {len(batch)} tickers in {time.time() - started:.1f}s",
                flush=True,
            )
    return out


def fetch_xbrl_periods(driver, tickers: list[str], batch_size: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
    with driver.session() as session:
        for batch_no, batch in enumerate(chunks(tickers, batch_size), start=1):
            started = time.time()
            for record in session.run(XBRL_PERIOD_QUERY, tickers=batch):
                out[record["ticker"]] = [dict(row) for row in record["rows"]]
            print(
                f"xbrl period batch {batch_no}: {len(batch)} tickers in {time.time() - started:.1f}s",
                flush=True,
            )
    return out


def fetch_guidance_periods(driver, tickers: list[str], batch_size: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
    with driver.session() as session:
        for batch_no, batch in enumerate(chunks(tickers, batch_size), start=1):
            started = time.time()
            for record in session.run(GUIDANCE_PERIOD_QUERY, tickers=batch):
                out[record["ticker"]] = [dict(row) for row in record["rows"]]
            print(
                f"guidance period batch {batch_no}: {len(batch)} tickers in {time.time() - started:.1f}s",
                flush=True,
            )
    return out


def build_concept_indexes(concept_caches: dict[str, list[dict]]) -> dict[str, dict[str, list[dict]]]:
    indexes: dict[str, dict[str, list[dict]]] = {}
    for ticker, rows in concept_caches.items():
        by_norm: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            qname = row.get("qname") or ""
            label = row.get("label") or ""
            usage = int(row.get("usage") or 0)
            entry = {"qname": qname, "label": label, "usage": usage}
            for key in {norm_compact(local_name(qname)), norm_compact(label)}:
                if key and len(key) > 3:
                    by_norm[key].append(entry)
        indexes[ticker] = dict(by_norm)
    return indexes


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_xbrl_period_uid(period_u_id: str | None) -> dict | None:
    if not period_u_id:
        return None
    if period_u_id.startswith("duration_"):
        parts = period_u_id.split("_", 2)
        if len(parts) != 3:
            return None
        start = parse_date(parts[1])
        exclusive_end = parse_date(parts[2])
        if not start or not exclusive_end:
            return None
        inclusive_end = exclusive_end - timedelta(days=1)
        return {
            "period_u_id": period_u_id,
            "time_type": "duration",
            "start_date": start.isoformat(),
            "end_date": inclusive_end.isoformat(),
            "exclusive_end_date": exclusive_end.isoformat(),
            "days": (inclusive_end - start).days + 1,
        }
    if period_u_id.startswith("instant_"):
        parts = period_u_id.split("_", 1)
        if len(parts) != 2:
            return None
        exclusive_instant = parse_date(parts[1])
        if not exclusive_instant:
            return None
        instant = exclusive_instant - timedelta(days=1)
        return {
            "period_u_id": period_u_id,
            "time_type": "instant",
            "start_date": instant.isoformat(),
            "end_date": instant.isoformat(),
            "exclusive_end_date": exclusive_instant.isoformat(),
            "days": 1,
        }
    return None


def build_xbrl_period_index(xbrl_periods: dict[str, list[dict]]) -> dict[str, dict[str, dict[str, list[dict]]]]:
    index: dict[str, dict[str, dict[str, list[dict]]]] = {}
    for ticker, rows in xbrl_periods.items():
        ticker_index: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            parsed = parse_xbrl_period_uid(row.get("period_u_id"))
            if not parsed:
                continue
            parsed["usage"] = int(row.get("usage") or 0)
            ticker_index[parsed["end_date"]][parsed["time_type"]].append(parsed)
        for end_date, by_type in ticker_index.items():
            for time_type, values in by_type.items():
                values.sort(key=lambda item: (-item["usage"], item["period_u_id"]))
        index[ticker] = {end: dict(by_type) for end, by_type in ticker_index.items()}
    return index


def build_guidance_period_index(guidance_periods: dict[str, list[dict]]) -> dict[str, dict[str, list[dict]]]:
    index: dict[str, dict[str, list[dict]]] = {}
    for ticker, rows in guidance_periods.items():
        ticker_index: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            end_date = str(row.get("end_date") or "")
            if not end_date:
                continue
            entry = {
                "u_id": row.get("u_id") or "",
                "start_date": str(row.get("start_date") or ""),
                "end_date": end_date,
                "period_scope": row.get("period_scope") or "",
                "usage": int(row.get("usage") or 0),
            }
            ticker_index[end_date].append(entry)
        for values in ticker_index.values():
            values.sort(key=lambda item: (-item["usage"], item["u_id"]))
        index[ticker] = dict(ticker_index)
    return index


def fetch_redis_periods(tickers: list[str]) -> dict[str, dict[str, list[dict]]]:
    try:
        import redis
    except Exception:
        return {}
    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "31379"))
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
        client.ping()
    except Exception:
        return {}

    wanted = set(tickers)
    out: dict[str, dict[str, list[dict]]] = {ticker: defaultdict(list) for ticker in tickers}
    try:
        key_iter = client.scan_iter("fiscal_quarter:*", count=1000)
        for key in key_iter:
            parts = key.split(":")
            if len(parts) != 4:
                continue
            _, ticker, fiscal_year, suffix = parts
            if ticker not in wanted or not (suffix.startswith("Q") or suffix == "FY"):
                continue
            raw = client.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            start = data.get("start")
            end = data.get("end")
            if not start or not end:
                continue
            out[ticker][end].append(
                {
                    "redis_key": key,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": suffix,
                    "start_date": start,
                    "end_date": end,
                }
            )
    except Exception:
        return {}
    return {ticker: dict(values) for ticker, values in out.items()}


def fetch_redis_period_support(tickers: list[str]) -> tuple[dict[str, dict[tuple[str, str], dict]], dict[str, dict[str, int]]]:
    try:
        import redis
    except Exception:
        return {}, {}
    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "31379"))
    try:
        client = redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
        client.ping()
    except Exception:
        return {}, {}

    wanted = set(tickers)
    by_identity: dict[str, dict[tuple[str, str], dict]] = {ticker: {} for ticker in tickers}
    lengths: dict[str, dict[str, int]] = {ticker: {} for ticker in tickers}
    try:
        for key in client.scan_iter("fiscal_quarter:*", count=1000):
            parts = key.split(":")
            if len(parts) != 4:
                continue
            _, ticker, fiscal_year, suffix = parts
            if ticker not in wanted or not (suffix.startswith("Q") or suffix == "FY"):
                continue
            raw = client.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("start") and data.get("end"):
                by_identity[ticker][(fiscal_year, suffix)] = {
                    "redis_key": key,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": suffix,
                    "start_date": data["start"],
                    "end_date": data["end"],
                }

        for key in client.scan_iter("fiscal_quarter_length:*", count=1000):
            parts = key.split(":")
            if len(parts) != 3:
                continue
            _, ticker, quarter = parts
            if ticker not in wanted:
                continue
            try:
                lengths[ticker][quarter] = int(client.get(key))
            except (TypeError, ValueError):
                continue
    except Exception:
        return {}, {}
    return by_identity, lengths


def predict_redis_period(
    ticker: str,
    fiscal_year: str,
    fiscal_period: str,
    redis_identity_index: dict[str, dict[tuple[str, str], dict]],
    redis_length_index: dict[str, dict[str, int]],
) -> dict:
    if not fiscal_year or not fiscal_period.startswith("Q"):
        return {}
    try:
        fy = int(fiscal_year)
        quarter = int(fiscal_period[1])
    except ValueError:
        return {}
    prev_q = quarter - 1 if quarter > 1 else 4
    prev_fy = fy if quarter > 1 else fy - 1
    prev = redis_identity_index.get(ticker, {}).get((str(prev_fy), f"Q{prev_q}"))
    length = redis_length_index.get(ticker, {}).get(fiscal_period)
    if not prev or not length:
        return {}
    prev_end = parse_date(prev.get("end_date"))
    if not prev_end:
        return {}
    start = prev_end + timedelta(days=1)
    end = start + timedelta(days=length - 1)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "period_u_id": f"gp_{start.isoformat()}_{end.isoformat()}",
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "source": "sec_cache_prediction",
    }


def preferred_xbrl_period(by_type: dict[str, list[dict]], expected_time_type: str, period_type: str) -> dict | None:
    expected = by_type.get(expected_time_type) or []
    if expected_time_type == "duration":
        if period_type == "quarterly":
            preferred = [row for row in expected if 70 <= row.get("days", 0) <= 110]
        elif period_type == "annual":
            preferred = [row for row in expected if 330 <= row.get("days", 0) <= 390]
        else:
            preferred = expected
        if preferred:
            return preferred[0]
    if expected:
        return expected[0]
    for fallback_type in ("duration", "instant"):
        values = by_type.get(fallback_type) or []
        if values:
            return values[0]
    return None


def infer_period_identity(
    period: FiscalPeriod,
    company_info: dict,
    annual_period_ends: dict[str, set[str]],
    redis_matches: list[dict],
) -> tuple[str, str, str]:
    for match in redis_matches:
        suffix = match.get("fiscal_period") or ""
        if period.period_type == "quarterly" and suffix.startswith("Q"):
            return str(match.get("fiscal_year") or ""), suffix, "sec_cache"
        if period.period_type == "annual" and suffix == "FY" and period.period_label != "LTM":
            return str(match.get("fiscal_year") or ""), "FY", "sec_cache"

    if period.period_label == "LTM":
        return "", "LTM", "fiscal_ai_label"

    fye_month = company_info.get("fye_month")
    end = parse_date(period.period_end_date)
    if not fye_month or not end or period_to_fiscal is None:
        return "", "", ""

    try:
        if period.period_type == "annual":
            fiscal_year, _ = period_to_fiscal(end.year, end.month, end.day, fye_month, "10-K")
            return str(fiscal_year), "FY", "fye_period_to_fiscal"

        if period.period_type == "quarterly":
            if period.period_end_date in annual_period_ends.get(period.symbol, set()):
                fiscal_year, _ = period_to_fiscal(end.year, end.month, end.day, fye_month, "10-K")
                return str(fiscal_year), "Q4", "annual_end_q4"
            fiscal_year, fiscal_quarter = period_to_fiscal(end.year, end.month, end.day, fye_month, "10-Q")
            return str(fiscal_year), fiscal_quarter, "fye_period_to_fiscal"
    except Exception:
        return "", "", ""
    return "", "", ""


def fye_math_period(
    fiscal_year: str,
    fiscal_period: str,
    fye_month: int | None,
    expected_time_type: str,
) -> dict:
    if not fiscal_year or not fiscal_period or not fye_month or _compute_fiscal_dates is None:
        return {}
    if fiscal_period == "LTM":
        return {}
    quarter = "FY" if fiscal_period == "FY" else fiscal_period
    try:
        start, end = _compute_fiscal_dates(fye_month, int(fiscal_year), quarter)
    except Exception:
        return {}
    if expected_time_type == "instant":
        return {
            "period_u_id": f"gp_{end}_{end}",
            "start_date": end,
            "end_date": end,
            "time_type": "instant",
        }
    return {
        "period_u_id": f"gp_{start}_{end}",
        "start_date": start,
        "end_date": end,
        "time_type": "duration",
    }


def resolve_period_instance(
    period: FiscalPeriod,
    *,
    company_info: dict,
    annual_period_ends: dict[str, set[str]],
    xbrl_period_index: dict[str, dict[str, dict[str, list[dict]]]],
    guidance_period_index: dict[str, dict[str, list[dict]]],
    redis_period_index: dict[str, dict[str, list[dict]]],
    redis_identity_index: dict[str, dict[tuple[str, str], dict]],
    redis_length_index: dict[str, dict[str, int]],
) -> dict:
    expected_time_type = "instant" if period.section.strip() in INSTANT_SECTIONS else "duration"
    xbrl_by_type = xbrl_period_index.get(period.symbol, {}).get(period.period_end_date, {})
    xbrl_best = preferred_xbrl_period(xbrl_by_type, expected_time_type, period.period_type)
    guidance_matches = guidance_period_index.get(period.symbol, {}).get(period.period_end_date, [])
    redis_matches = redis_period_index.get(period.symbol, {}).get(period.period_end_date, [])
    fiscal_year, fiscal_period, fiscal_source = infer_period_identity(
        period, company_info, annual_period_ends, redis_matches
    )
    predicted_period = predict_redis_period(
        period.symbol, fiscal_year, fiscal_period, redis_identity_index, redis_length_index
    )
    math_period = fye_math_period(
        fiscal_year, fiscal_period, company_info.get("fye_month"), expected_time_type
    )

    xbrl_expected = bool(xbrl_by_type.get(expected_time_type))
    xbrl_any = bool(xbrl_best)
    guidance_any = bool(guidance_matches)
    sec_any = bool(redis_matches)
    sec_prediction_exact = bool(
        not sec_any and predicted_period and predicted_period.get("end_date") == period.period_end_date
    )
    fye_exact = bool(math_period and math_period.get("end_date") == period.period_end_date)

    resolved_source = ""
    resolved_period_u_id = ""
    resolved_start = ""
    resolved_end = ""
    if sec_any:
        chosen = redis_matches[0]
        resolved_source = "sec_cache"
        resolved_period_u_id = f"gp_{chosen['start_date']}_{chosen['end_date']}"
        resolved_start = chosen["start_date"]
        resolved_end = chosen["end_date"]
    elif sec_prediction_exact:
        resolved_source = "sec_cache_prediction"
        resolved_period_u_id = predicted_period["period_u_id"]
        resolved_start = predicted_period["start_date"]
        resolved_end = predicted_period["end_date"]
    elif guidance_any:
        chosen = guidance_matches[0]
        resolved_source = "existing_guidance_period"
        resolved_period_u_id = chosen["u_id"]
        resolved_start = chosen["start_date"]
        resolved_end = chosen["end_date"]
    elif xbrl_best:
        resolved_source = "xbrl_context"
        resolved_period_u_id = f"gp_{xbrl_best['start_date']}_{xbrl_best['end_date']}"
        resolved_start = xbrl_best["start_date"]
        resolved_end = xbrl_best["end_date"]
    elif math_period:
        resolved_source = "fye_math_exact" if fye_exact else "fye_math_fallback"
        resolved_period_u_id = math_period["period_u_id"]
        resolved_start = math_period["start_date"]
        resolved_end = math_period["end_date"]

    period_exact_any = bool(sec_any or sec_prediction_exact or guidance_any or xbrl_any or fye_exact)
    return {
        "symbol": period.symbol,
        "company_slug": period.company_slug,
        "section": period.section,
        "metric_key": period.metric_key,
        "metric_name": period.metric_name,
        "period_type": period.period_type,
        "period_label": period.period_label,
        "period_end_date": period.period_end_date,
        "period_expected_time_type": expected_time_type,
        "period_fiscal_year": fiscal_year,
        "period_fiscal_period": fiscal_period,
        "period_fiscal_source": fiscal_source,
        "period_resolved_u_id": resolved_period_u_id,
        "period_resolved_start_date": resolved_start,
        "period_resolved_end_date": resolved_end,
        "period_resolved_source": resolved_source,
        "period_sec_cache_exact": int(sec_any),
        "period_sec_cache_prediction_exact": int(sec_prediction_exact),
        "period_guidance_existing_exact": int(guidance_any),
        "period_xbrl_context_exact_any": int(xbrl_any),
        "period_xbrl_context_expected_type": int(xbrl_expected),
        "period_fye_math_exact": int(fye_exact),
        "period_exact_any": int(period_exact_any),
        "period_fye_math_fallback": int(bool(math_period and not fye_exact and not period_exact_any)),
        "period_xbrl_period_u_id": (xbrl_best or {}).get("period_u_id", ""),
        "period_xbrl_start_date": (xbrl_best or {}).get("start_date", ""),
        "period_xbrl_end_date": (xbrl_best or {}).get("end_date", ""),
        "period_xbrl_time_type": (xbrl_best or {}).get("time_type", ""),
        "period_xbrl_context_count": sum(row.get("usage", 0) for values in xbrl_by_type.values() for row in values),
        "period_row_count": period.row_count,
        "period_valued_row_count": period.valued_row_count,
    }


def resolve_metric_periods(
    metric_periods: dict[tuple[str, str, str, str], list[FiscalPeriod]],
    *,
    company_info: dict[str, dict],
    annual_period_ends: dict[str, set[str]],
    xbrl_period_index: dict[str, dict[str, dict[str, list[dict]]]],
    guidance_period_index: dict[str, dict[str, list[dict]]],
    redis_period_index: dict[str, dict[str, list[dict]]],
    redis_identity_index: dict[str, dict[tuple[str, str], dict]],
    redis_length_index: dict[str, dict[str, int]],
) -> tuple[dict[tuple[str, str, str, str], dict], list[dict]]:
    period_rows: list[dict] = []
    by_metric: dict[tuple[str, str, str, str], list[dict]] = {}
    for key, periods in metric_periods.items():
        resolved = []
        for period in periods:
            row = resolve_period_instance(
                period,
                company_info=company_info.get(period.symbol, {}),
                annual_period_ends=annual_period_ends,
                xbrl_period_index=xbrl_period_index,
                guidance_period_index=guidance_period_index,
                redis_period_index=redis_period_index,
                redis_identity_index=redis_identity_index,
                redis_length_index=redis_length_index,
            )
            resolved.append(row)
            period_rows.append(row)
        by_metric[key] = resolved

    summaries: dict[tuple[str, str, str, str], dict] = {}
    for key, rows in by_metric.items():
        total = len(rows)
        exact_any = sum(int(row["period_exact_any"]) for row in rows)
        expected = sum(int(row["period_xbrl_context_expected_type"]) for row in rows)
        summaries[key] = {
            "period_instance_count": total,
            "period_exact_any_count": exact_any,
            "period_xbrl_expected_type_count": expected,
            "period_xbrl_any_count": sum(int(row["period_xbrl_context_exact_any"]) for row in rows),
            "period_sec_cache_count": sum(int(row["period_sec_cache_exact"]) for row in rows),
            "period_sec_cache_prediction_count": sum(
                int(row["period_sec_cache_prediction_exact"]) for row in rows
            ),
            "period_guidance_existing_count": sum(int(row["period_guidance_existing_exact"]) for row in rows),
            "period_fye_math_exact_count": sum(int(row["period_fye_math_exact"]) for row in rows),
            "period_all_exact_any": int(total > 0 and exact_any == total),
            "period_all_xbrl_expected_type": int(total > 0 and expected == total),
            "period_sample_resolved_uids": ";".join(
                row["period_resolved_u_id"] for row in rows[:4] if row["period_resolved_u_id"]
            ),
            "period_unmatched": ";".join(
                f"{row['period_label']}={row['period_end_date']}"
                for row in rows
                if not int(row["period_exact_any"])
            )[:500],
        }
    return summaries, period_rows


def resolve_candidate_qname(base_slug: str, concept_rows: list[dict]) -> tuple[str, str]:
    candidates = CONCEPT_CANDIDATES.get(base_slug)
    if not candidates:
        return "", ""
    for candidate in candidates:
        hits = [row for row in concept_rows if local_name(row.get("qname")) == candidate]
        if not hits:
            continue
        hits.sort(key=lambda row: (-int(row.get("usage") or 0), row.get("qname") or ""))
        if len(hits) > 1 and int(hits[0].get("usage") or 0) == int(hits[1].get("usage") or 0):
            return "", ""
        return hits[0].get("qname") or "", f"candidate:{candidate}"
    return "", ""


def resolve_exact_text_qname(
    ticker: str,
    texts: Iterable[str],
    concept_index: dict[str, dict[str, list[dict]]],
) -> tuple[str, str]:
    ticker_index = concept_index.get(ticker, {})
    for text in texts:
        key = norm_compact(text)
        if not key or len(key) <= 3:
            continue
        hits = ticker_index.get(key, [])
        if not hits:
            continue
        by_qname = {}
        for hit in hits:
            qname = hit["qname"]
            if qname not in by_qname or hit["usage"] > by_qname[qname]["usage"]:
                by_qname[qname] = hit
        ranked = sorted(by_qname.values(), key=lambda row: (-row["usage"], row["qname"]))
        if len(ranked) > 1 and ranked[0]["usage"] == ranked[1]["usage"]:
            continue
        return ranked[0]["qname"], f"exact_concept_text:{text}"
    return "", ""


def reviewed_map_qname(metric: FiscalMetric, rule: dict, revenue_map: dict, operating_map: dict) -> tuple[str, str]:
    map_name = rule.get("map")
    if map_name == "revenue":
        row = revenue_map.get(metric.symbol)
        if not row or not row.get("qname"):
            return "", ""
        if rule.get("geography") and not row.get("works_for_geography"):
            return "", ""
        if not rule.get("geography"):
            if not (
                row.get("works_for_segments")
                or row.get("works_for_product_service")
                or row.get("works_for_geography")
            ):
                return "", ""
        return row["qname"], "reviewed_revenue_map"
    if map_name == "operating":
        row = operating_map.get(metric.symbol)
        if not row or not row.get("qname"):
            return "", ""
        if rule.get("geography") and not row.get("works_for_geography"):
            return "", ""
        if not rule.get("geography"):
            if not (row.get("works_for_segments") or row.get("works_for_geography")):
                return "", ""
        return row["qname"], "reviewed_operating_map"
    return "", ""


def pick_member(member_map: dict[str, list[dict]], segment: str) -> tuple[str, str, str, str, str]:
    norm = normalize_for_member_match(segment)
    if not norm:
        return "", "", "", "", ""
    hits = member_map.get(norm, [])
    if not hits:
        return "", "", "", "", ""
    label_hits = [hit for hit in hits if hit.get("match_key_source") == "label"]
    chosen = (label_hits or hits)[0]
    return (
        chosen.get("u_id", ""),
        chosen.get("qname", ""),
        chosen.get("label", ""),
        chosen.get("domain_qname", ""),
        "member_label_exact" if label_hits else "member_qname_exact",
    )


def prefix_member_candidate(member_map: dict[str, list[dict]], metric_name: str) -> tuple[str, str, str, str, str, str]:
    clean_norm = normalize_for_member_match(clean_metric_text(metric_name, drop_all_parentheticals=True))
    if not clean_norm:
        return "", "", "", "", "", ""
    candidates = []
    for norm, hits in member_map.items():
        if len(norm) < 4:
            continue
        if clean_norm.startswith(norm) and clean_norm != norm:
            candidates.append((len(norm), norm, hits))
    if not candidates:
        return "", "", "", "", "", ""
    candidates.sort(reverse=True, key=lambda item: item[0])
    _, norm, hits = candidates[0]
    label_hits = [hit for hit in hits if hit.get("match_key_source") == "label"]
    chosen = (label_hits or hits)[0]
    return (
        chosen.get("u_id", ""),
        chosen.get("qname", ""),
        chosen.get("label", ""),
        chosen.get("domain_qname", ""),
        "member_prefix_candidate",
        norm,
    )


def audit_metric(
    metric: FiscalMetric,
    concept_rows: list[dict],
    concept_index: dict[str, dict[str, list[dict]]],
    member_maps: dict[str, dict[str, list[dict]]],
    revenue_map: dict,
    operating_map: dict,
    period_summary: dict,
) -> dict:
    section = metric.section.strip()
    rule = SECTION_RULES.get(section)
    segment = ""
    base_label = ""
    segment_source = ""
    base_slug = ""

    if rule:
        base_slug = rule["base"]
        segment, base_label, segment_source = strip_suffix_segment(metric.metric_name, rule["suffixes"])
    elif section == "Key Performance Indicators":
        segment, base_label, segment_source = derive_kpi_segment(metric.metric_name)
        base_slug = slug(base_label) if base_label else slug(clean_metric_text(metric.metric_name, drop_all_parentheticals=True))
    else:
        base_slug = slug(section) if section else ""

    is_total_segment = segment in TOTAL_SEGMENT_VALUES
    explicit_segment = bool(segment) and not is_total_segment

    concept_qname = ""
    concept_source = ""
    if rule:
        concept_qname, concept_source = reviewed_map_qname(metric, rule, revenue_map, operating_map)
        if not concept_qname:
            concept_qname, concept_source = resolve_candidate_qname(base_slug, concept_rows)

    text_candidates = [
        metric.metric_name,
        clean_metric_text(metric.metric_name),
        clean_metric_text(metric.metric_name, drop_all_parentheticals=True),
    ]
    if base_label and (rule or segment_source == "kpi_dash_prefix"):
        text_candidates.extend([base_label, clean_metric_text(base_label, drop_all_parentheticals=True)])
    if not concept_qname:
        concept_qname, concept_source = resolve_exact_text_qname(metric.symbol, text_candidates, concept_index)

    member_u_id = ""
    member_qname = ""
    member_label = ""
    member_domain_qname = ""
    member_source = ""
    matched_segment = segment
    member_map = member_maps.get(metric.symbol, {})
    if explicit_segment:
        member_u_id, member_qname, member_label, member_domain_qname, member_source = pick_member(member_map, segment)

    prefix_u_id = prefix_qname = prefix_label = prefix_domain = prefix_source = prefix_norm = ""
    if section == "Key Performance Indicators" and not member_u_id:
        (
            prefix_u_id,
            prefix_qname,
            prefix_label,
            prefix_domain,
            prefix_source,
            prefix_norm,
        ) = prefix_member_candidate(member_map, metric.metric_name)

    strict_member = bool(member_u_id)
    candidate_member = bool(prefix_u_id)
    concept_exact = bool(concept_qname)
    strict_any = concept_exact or strict_member
    candidate_any = strict_any or candidate_member
    complete_financial_split = concept_exact and (not explicit_segment or strict_member)
    period_all_exact_any = bool(period_summary.get("period_all_exact_any"))
    period_all_expected_type = bool(period_summary.get("period_all_xbrl_expected_type"))
    strict_any_with_period = strict_any and period_all_exact_any
    complete_financial_split_with_period = complete_financial_split and period_all_exact_any

    row = {
        "symbol": metric.symbol,
        "company_slug": metric.company_slug,
        "company_name": metric.company_name,
        "exchange": metric.universe_exchange,
        "cik": metric.cik,
        "section": section,
        "section_key": metric.section_key,
        "metric_key": metric.metric_key,
        "metric_name": metric.metric_name,
        "period_types": metric.period_types,
        "row_count": metric.row_count,
        "valued_row_count": metric.valued_row_count,
        "first_period_end": metric.first_period_end,
        "last_period_end": metric.last_period_end,
        "base_slug": base_slug,
        "segment": matched_segment,
        "segment_source": segment_source,
        "is_total_segment": int(is_total_segment),
        "has_explicit_segment": int(explicit_segment),
        "xbrl_qname": concept_qname,
        "concept_source": concept_source,
        "member_u_id": member_u_id,
        "member_qname": member_qname,
        "member_label": member_label,
        "member_domain_qname": member_domain_qname,
        "member_source": member_source,
        "candidate_member_u_id": prefix_u_id,
        "candidate_member_qname": prefix_qname,
        "candidate_member_label": prefix_label,
        "candidate_member_domain_qname": prefix_domain,
        "candidate_member_source": prefix_source,
        "candidate_member_norm": prefix_norm,
        "concept_exact": int(concept_exact),
        "member_exact": int(strict_member),
        "member_candidate": int(candidate_member),
        "linked_strict_any": int(strict_any),
        "linked_with_candidate": int(candidate_any),
        "complete_financial_split": int(complete_financial_split),
        "period_instance_count": int(period_summary.get("period_instance_count", 0)),
        "period_exact_any_count": int(period_summary.get("period_exact_any_count", 0)),
        "period_xbrl_expected_type_count": int(period_summary.get("period_xbrl_expected_type_count", 0)),
        "period_xbrl_any_count": int(period_summary.get("period_xbrl_any_count", 0)),
        "period_sec_cache_count": int(period_summary.get("period_sec_cache_count", 0)),
        "period_sec_cache_prediction_count": int(period_summary.get("period_sec_cache_prediction_count", 0)),
        "period_guidance_existing_count": int(period_summary.get("period_guidance_existing_count", 0)),
        "period_fye_math_exact_count": int(period_summary.get("period_fye_math_exact_count", 0)),
        "period_all_exact_any": int(period_all_exact_any),
        "period_all_xbrl_expected_type": int(period_all_expected_type),
        "period_sample_resolved_uids": period_summary.get("period_sample_resolved_uids", ""),
        "period_unmatched": period_summary.get("period_unmatched", ""),
        "linked_strict_any_with_period": int(strict_any_with_period),
        "complete_financial_split_with_period": int(complete_financial_split_with_period),
    }
    return row


def summarize(rows: list[dict], period_type: str, started_at: float) -> dict:
    total = len(rows)
    valued_total = sum(1 for row in rows if int(row["valued_row_count"]) > 0)
    by_section = defaultdict(lambda: Counter())
    for row in rows:
        section = row["section"] or "(blank)"
        by_section[section]["total"] += 1
        if int(row["valued_row_count"]) > 0:
            by_section[section]["valued_total"] += 1
        for field in (
            "concept_exact",
            "member_exact",
            "member_candidate",
            "linked_strict_any",
            "linked_with_candidate",
            "complete_financial_split",
            "linked_strict_any_with_period",
            "complete_financial_split_with_period",
            "period_instance_count",
            "period_exact_any_count",
            "period_xbrl_expected_type_count",
            "period_xbrl_any_count",
            "period_sec_cache_count",
            "period_sec_cache_prediction_count",
            "period_guidance_existing_count",
            "period_fye_math_exact_count",
            "period_all_exact_any",
            "period_all_xbrl_expected_type",
        ):
            by_section[section][field] += int(row[field])

    def pct(value: int, denom: int) -> float:
        return round((value / denom * 100.0), 2) if denom else 0.0

    summary = {
        "period_type": period_type,
        "generated_at_epoch": int(time.time()),
        "elapsed_seconds": round(time.time() - started_at, 1),
        "denominator_unique_metric_defs": total,
        "denominator_unique_metric_defs_with_value": valued_total,
        "concept_exact": sum(int(row["concept_exact"]) for row in rows),
        "member_exact": sum(int(row["member_exact"]) for row in rows),
        "member_candidate_prefix": sum(int(row["member_candidate"]) for row in rows),
        "linked_strict_any": sum(int(row["linked_strict_any"]) for row in rows),
        "linked_with_candidate_prefix": sum(int(row["linked_with_candidate"]) for row in rows),
        "complete_financial_split": sum(int(row["complete_financial_split"]) for row in rows),
        "linked_strict_any_with_period": sum(int(row["linked_strict_any_with_period"]) for row in rows),
        "complete_financial_split_with_period": sum(int(row["complete_financial_split_with_period"]) for row in rows),
        "period_instances": sum(int(row["period_instance_count"]) for row in rows),
        "period_exact_any": sum(int(row["period_exact_any_count"]) for row in rows),
        "period_xbrl_expected_type": sum(int(row["period_xbrl_expected_type_count"]) for row in rows),
        "period_xbrl_any": sum(int(row["period_xbrl_any_count"]) for row in rows),
        "period_sec_cache": sum(int(row["period_sec_cache_count"]) for row in rows),
        "period_sec_cache_prediction": sum(int(row["period_sec_cache_prediction_count"]) for row in rows),
        "period_guidance_existing": sum(int(row["period_guidance_existing_count"]) for row in rows),
        "period_fye_math_exact": sum(int(row["period_fye_math_exact_count"]) for row in rows),
        "period_all_exact_any_metric_defs": sum(int(row["period_all_exact_any"]) for row in rows),
        "period_all_xbrl_expected_type_metric_defs": sum(int(row["period_all_xbrl_expected_type"]) for row in rows),
        "sections": {},
    }
    for key in (
        "concept_exact",
        "member_exact",
        "member_candidate_prefix",
        "linked_strict_any",
        "linked_with_candidate_prefix",
        "complete_financial_split",
        "linked_strict_any_with_period",
        "complete_financial_split_with_period",
        "period_all_exact_any_metric_defs",
        "period_all_xbrl_expected_type_metric_defs",
    ):
        summary[f"{key}_pct"] = pct(summary[key], total)
    summary["period_exact_any_pct"] = pct(summary["period_exact_any"], summary["period_instances"])
    summary["period_xbrl_expected_type_pct"] = pct(
        summary["period_xbrl_expected_type"], summary["period_instances"]
    )
    summary["period_xbrl_any_pct"] = pct(summary["period_xbrl_any"], summary["period_instances"])

    for section, counts in sorted(by_section.items(), key=lambda item: (-item[1]["total"], item[0])):
        section_total = counts["total"]
        summary["sections"][section] = {
            "total": section_total,
            "valued_total": counts["valued_total"],
            "concept_exact": counts["concept_exact"],
            "member_exact": counts["member_exact"],
            "member_candidate_prefix": counts["member_candidate"],
            "linked_strict_any": counts["linked_strict_any"],
            "linked_with_candidate_prefix": counts["linked_with_candidate"],
            "complete_financial_split": counts["complete_financial_split"],
            "linked_strict_any_with_period": counts["linked_strict_any_with_period"],
            "complete_financial_split_with_period": counts["complete_financial_split_with_period"],
            "period_instances": counts["period_instance_count"],
            "period_exact_any": counts["period_exact_any_count"],
            "period_xbrl_expected_type": counts["period_xbrl_expected_type_count"],
            "period_xbrl_any": counts["period_xbrl_any_count"],
            "period_sec_cache": counts["period_sec_cache_count"],
            "period_sec_cache_prediction": counts["period_sec_cache_prediction_count"],
            "period_guidance_existing": counts["period_guidance_existing_count"],
            "period_fye_math_exact": counts["period_fye_math_exact_count"],
            "period_all_exact_any_metric_defs": counts["period_all_exact_any"],
            "period_all_xbrl_expected_type_metric_defs": counts["period_all_xbrl_expected_type"],
            "linked_strict_any_pct": pct(counts["linked_strict_any"], section_total),
            "complete_financial_split_pct": pct(counts["complete_financial_split"], section_total),
            "period_exact_any_pct": pct(counts["period_exact_any_count"], counts["period_instance_count"]),
            "period_xbrl_expected_type_pct": pct(
                counts["period_xbrl_expected_type_count"], counts["period_instance_count"]
            ),
        }
    return summary


def write_outputs(rows: list[dict], period_rows: list[dict], summary: dict, out_dir: Path, period_type: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    detail_path = out_dir / f"kpi_xbrl_link_audit_{period_type}.csv"
    period_path = out_dir / f"period_link_audit_{period_type}.csv"
    summary_path = out_dir / f"coverage_summary_{period_type}.json"
    fields = list(rows[0].keys()) if rows else []
    with detail_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    period_fields = list(period_rows[0].keys()) if period_rows else []
    with period_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=period_fields)
        writer.writeheader()
        writer.writerows(period_rows)
    with summary_path.open("w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {detail_path}", flush=True)
    print(f"wrote {period_path}", flush=True)
    print(f"wrote {summary_path}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--period-type", choices=("quarterly", "annual", "all"), default="quarterly")
    parser.add_argument("--symbols", help="Comma-separated ticker allowlist for canaries")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    started_at = time.time()
    load_env(ROOT / ".env")
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not password:
        raise SystemExit("Missing Neo4j credentials in environment/.env")

    metrics = load_fiscal_metrics(args.db, args.period_type)
    metric_periods = load_fiscal_metric_periods(args.db, args.period_type)
    annual_period_ends = load_annual_period_ends(args.db)
    if args.symbols:
        allowed = {part.strip().upper() for part in args.symbols.split(",") if part.strip()}
        metrics = [metric for metric in metrics if metric.symbol.upper() in allowed]
        annual_period_ends = {ticker: values for ticker, values in annual_period_ends.items() if ticker.upper() in allowed}
    tickers = sorted({metric.symbol for metric in metrics})
    metric_keys = {metric_identity_from_metric(metric) for metric in metrics}
    metric_periods = {key: value for key, value in metric_periods.items() if key in metric_keys}
    print(f"loaded {len(metrics)} Fiscal metric definitions for {len(tickers)} tickers", flush=True)

    revenue_map = load_jsonl_map(REVENUE_MAP)
    operating_map = load_jsonl_map(OPERATING_MAP)
    redis_period_index = fetch_redis_periods(tickers)
    redis_identity_index, redis_length_index = fetch_redis_period_support(tickers)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        company_info = fetch_company_info(driver, tickers, args.batch_size)
        concept_caches = fetch_concept_caches(driver, tickers, args.batch_size)
        member_maps = fetch_member_maps(driver, tickers, args.batch_size)
        xbrl_periods = fetch_xbrl_periods(driver, tickers, args.batch_size)
        guidance_periods = fetch_guidance_periods(driver, tickers, args.batch_size)
    finally:
        driver.close()

    concept_index = build_concept_indexes(concept_caches)
    xbrl_period_index = build_xbrl_period_index(xbrl_periods)
    guidance_period_index = build_guidance_period_index(guidance_periods)
    period_summaries, period_rows = resolve_metric_periods(
        metric_periods,
        company_info=company_info,
        annual_period_ends=annual_period_ends,
        xbrl_period_index=xbrl_period_index,
        guidance_period_index=guidance_period_index,
        redis_period_index=redis_period_index,
        redis_identity_index=redis_identity_index,
        redis_length_index=redis_length_index,
    )
    rows = [
        audit_metric(
            metric,
            concept_caches.get(metric.symbol, []),
            concept_index,
            member_maps,
            revenue_map,
            operating_map,
            period_summaries.get(metric_identity_from_metric(metric), {}),
        )
        for metric in metrics
    ]
    summary = summarize(rows, args.period_type, started_at)
    write_outputs(rows, period_rows, summary, args.out_dir, args.period_type)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
