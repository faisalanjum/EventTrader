#!/usr/bin/env python3
"""Concept Fallback Discovery — Safe Coverage Expansion for build_prior_financials.

Read-only analysis tool. Does NOT modify the builder, Neo4j, or Redis.
All outputs go to a timestamped directory under earnings-analysis/consensus_exploration/concept_fallbacks/.

Subcommands:
    universe          — capture company universe with reference quarters
    baseline          — run current builder, compute gap summary + null cases
    gap-scan          — find candidate concepts in null-case filings
    coexistence-audit — prove whether candidates are synonyms
    simulate          — test one candidate via builder monkey-patch + diff

Usage:
    python3 scripts/earnings/concept_fallback_discovery.py universe --out RUN/00_universe.json
    python3 scripts/earnings/concept_fallback_discovery.py baseline --universe RUN/00_universe.json ...
    python3 scripts/earnings/concept_fallback_discovery.py gap-scan --universe RUN/00_universe.json ...
    python3 scripts/earnings/concept_fallback_discovery.py coexistence-audit --universe RUN/00_universe.json ...
    python3 scripts/earnings/concept_fallback_discovery.py simulate --universe RUN/00_universe.json ...
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(ROOT / "scripts/earnings"))

# ── Unit families (from plan §18 clarification) ─────────────────────────

UNIT_FAMILY = {}
for _m in ("revenue", "cost_of_revenue", "gross_profit", "sga", "rd_expense",
           "depreciation_amortization", "interest_expense", "income_tax",
           "operating_income", "net_income", "total_assets", "cash_and_equivalents",
           "long_term_debt", "stockholders_equity", "operating_cash_flow", "capex", "buybacks"):
    UNIT_FAMILY[_m] = "currency"
for _m in ("eps_diluted", "dividends_per_share"):
    UNIT_FAMILY[_m] = "per_share"
UNIT_FAMILY["diluted_shares"] = "count"

# ── Statement family (for structural filtering) ─────────────────────────

STMT_FAMILY = {}
for _m in ("revenue", "cost_of_revenue", "gross_profit", "sga", "rd_expense",
           "depreciation_amortization", "interest_expense", "income_tax",
           "operating_income", "net_income", "eps_diluted", "diluted_shares"):
    STMT_FAMILY[_m] = "income"
for _m in ("total_assets", "cash_and_equivalents", "long_term_debt", "stockholders_equity"):
    STMT_FAMILY[_m] = "balance"
for _m in ("operating_cash_flow", "capex", "buybacks", "dividends_per_share"):
    STMT_FAMILY[_m] = "cashflow"

# ── Period class (for structural filtering) ──────────────────────────────

PERIOD_CLASS = {}
for _m in ("total_assets", "cash_and_equivalents", "long_term_debt", "stockholders_equity"):
    PERIOD_CLASS[_m] = "instant"
# Everything else is duration
for _m in UNIT_FAMILY:
    if _m not in PERIOD_CLASS:
        PERIOD_CLASS[_m] = "duration"


# ── Helpers ──────────────────────────────────────────────────────────────

def _load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _get_manager():
    from neograph.Neo4jConnection import get_manager
    return get_manager()


def _load_builder_registry():
    """Return the current METRIC_REGISTRY from the builder."""
    import build_prior_financials as bpf
    return bpf.METRIC_REGISTRY


def _builder_concepts_for_metric(metric: str) -> set[str]:
    """Return the set of concept qnames currently in the builder for a metric."""
    registry = _load_builder_registry()
    for field, qnames, _ in registry:
        if field == metric:
            return set(qnames)
    return set()


def _load_concept_candidates() -> dict[str, tuple[str, ...]]:
    """Load CONCEPT_CANDIDATES from concept_resolver.py."""
    from concept_resolver import CONCEPT_CANDIDATES
    return CONCEPT_CANDIDATES


# §18 recommended candidates — explicit mapping from plan
_PLAN_RECOMMENDED_CANDIDATES = {
    "operating_cash_flow": ["us-gaap:NetCashProvidedByOperatingActivities"],
    "revenue": ["us-gaap:SalesRevenueNet"],
    "cost_of_revenue": ["us-gaap:CostOfGoodsSold"],
    "capex": ["us-gaap:CapitalExpenditure", "us-gaap:PaymentsToAcquireProductiveAssets"],
    "dividends_per_share": ["us-gaap:CommonStockDividendsPerShareCashPaid"],
}


def _reviewed_candidates_for_metric(metric: str) -> list[str]:
    """Get reviewed candidate qnames for a builder metric.

    Two sources combined:
    1. concept_resolver.py CONCEPT_CANDIDATES families that overlap with builder concepts
    2. §18 explicit recommended candidates
    """
    cc = _load_concept_candidates()
    existing = _builder_concepts_for_metric(metric)
    existing_local = {qn.split(":")[-1] for qn in existing}

    candidates = set()

    # Source 1: concept_resolver family overlap
    for slug_key, concept_tuple in cc.items():
        family_local = set(concept_tuple)
        if family_local & existing_local:
            for c in concept_tuple:
                qn = f"us-gaap:{c}"
                if qn not in existing:
                    candidates.add(qn)

    # Source 2: §18 explicit recommendations
    for qn in _PLAN_RECOMMENDED_CANDIDATES.get(metric, []):
        if qn not in existing:
            candidates.add(qn)

    return sorted(candidates)


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: universe
# ═══════════════════════════════════════════════════════════════════════════

def cmd_universe(args):
    """Capture company universe with reference quarters."""
    _load_env()
    mgr = _get_manager()

    print("Querying universe...", file=sys.stderr)
    rows = mgr.execute_cypher_query_all("""
        MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
        WHERE r.xbrl_status = 'COMPLETED' AND r.formType IN ['10-Q', '10-K']
        WITH c.ticker AS ticker, count(DISTINCT r) AS filing_count
        RETURN ticker ORDER BY ticker
    """)
    tickers = [r["ticker"] for r in rows]
    print(f"  {len(tickers)} tickers with COMPLETED XBRL", file=sys.stderr)

    # For each ticker: latest 8-K Item 2.02 + latest periodic filing
    print("Resolving reference quarters...", file=sys.stderr)
    # Two separate efficient queries instead of one complex cross-join
    eight_k_rows = mgr.execute_cypher_query_all("""
        MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
        WHERE r.formType = '8-K' AND r.items CONTAINS 'Item 2.02'
        WITH c.ticker AS ticker, r ORDER BY r.created DESC
        WITH ticker, collect(r)[0] AS latest
        RETURN ticker,
               latest.periodOfReport AS latest_item_202_period,
               toString(latest.created) AS latest_item_202_filed
    """)
    eight_k_map = {r["ticker"]: r for r in eight_k_rows}
    print(f"  {len(eight_k_map)} tickers with 8-K Item 2.02", file=sys.stderr)

    print("Resolving periodic reference quarters...", file=sys.stderr)
    periodic_rows = mgr.execute_cypher_query_all("""
        MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
        WHERE r.formType IN ['10-Q', '10-K'] AND r.xbrl_status = 'COMPLETED'
        WITH c.ticker AS ticker, r ORDER BY r.periodOfReport DESC
        WITH ticker, collect(r)[0] AS latest
        RETURN ticker,
               latest.periodOfReport AS latest_periodic_period,
               latest.formType AS latest_periodic_form
    """)
    periodic_map = {r["ticker"]: r for r in periodic_rows}

    universe = []
    for ticker in tickers:
        ek = eight_k_map.get(ticker, {})
        pm = periodic_map.get(ticker, {})
        # Anchor quarter: prefer 8-K Item 2.02 period, fallback to latest periodic
        anchor = ek.get("latest_item_202_period") or pm.get("latest_periodic_period")
        if not anchor:
            continue  # No usable anchor — skip
        universe.append({
            "ticker": ticker,
            "latest_item_202_period": ek.get("latest_item_202_period", ""),
            "latest_item_202_filed": ek.get("latest_item_202_filed", ""),
            "latest_periodic_period": pm.get("latest_periodic_period", ""),
            "latest_periodic_form": pm.get("latest_periodic_form", ""),
            "anchor_period": anchor,  # The period_of_report to use for the builder
        })

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(universe, f, indent=2)

    n_8k = sum(1 for e in universe if e["latest_item_202_period"])
    n_periodic = sum(1 for e in universe if not e["latest_item_202_period"])
    print(f"Wrote {out_path} ({len(universe)} tickers: {n_8k} with 8-K, {n_periodic} periodic-only)", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: baseline
# ═══════════════════════════════════════════════════════════════════════════

def cmd_baseline(args):
    """Run current builder across universe, compute gap summary + null cases."""
    _load_env()

    with open(args.universe, encoding="utf-8") as f:
        universe = json.load(f)

    import build_prior_financials as bpf
    registry = bpf.METRIC_REGISTRY

    packet_dir = Path(args.packet_dir)
    packet_dir.mkdir(parents=True, exist_ok=True)

    # Collect null cases and coverage stats
    null_cases = []
    metric_stats: dict[str, dict] = {}
    for field, qnames, _ in registry:
        metric_stats[field] = {
            "total_quarters": 0, "filled_quarters": 0, "null_quarters": 0,
            "filled_tickers": set(), "null_tickers": set(),
            "current_qnames": qnames,
        }

    t0 = time.time()
    success = 0
    errors = 0

    for i, entry in enumerate(universe):
        ticker = entry["ticker"]
        period = entry.get("anchor_period") or entry["latest_item_202_period"]

        if i % 50 == 0:
            elapsed = time.time() - t0
            print(f"  {i}/{len(universe)} ({elapsed:.0f}s) ok={success} err={errors}", file=sys.stderr)

        try:
            qi = {"period_of_report": period, "filed_8k": "", "market_session": "", "quarter_label": ""}
            packet = bpf.build_prior_financials(ticker, qi, out_path=str(packet_dir / f"{ticker}.json"))
            success += 1

            # Scan for null cases
            for q in packet["quarters"]:
                for field, _, _ in registry:
                    metric_stats[field]["total_quarters"] += 1
                    val = q.get(field)
                    if val is not None:
                        metric_stats[field]["filled_quarters"] += 1
                        metric_stats[field]["filled_tickers"].add(ticker)
                    else:
                        metric_stats[field]["null_quarters"] += 1
                        metric_stats[field]["null_tickers"].add(ticker)
                        null_cases.append({
                            "metric": field,
                            "ticker": ticker,
                            "period": q["period"],
                            "fiscal_label": q.get("fiscal_label", ""),
                            "primary_form": q.get("primary_form", ""),
                            "primary_accession": q.get("primary_accession", ""),
                            "primary_source": q.get("primary_source", ""),
                        })

        except Exception as e:
            errors += 1
            if errors <= 10:
                print(f"  ERROR {ticker}: {e}", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"  Done: {success}/{len(universe)} in {elapsed:.0f}s, {errors} errors", file=sys.stderr)

    # Write gap summary
    summary = {}
    for field, stats in metric_stats.items():
        summary[field] = {
            "total_quarters": stats["total_quarters"],
            "filled_quarters": stats["filled_quarters"],
            "null_quarters": stats["null_quarters"],
            "filled_tickers": len(stats["filled_tickers"]),
            "null_tickers": len(stats["null_tickers"]),
            "current_qnames": stats["current_qnames"],
            "fill_rate_pct": round(100 * stats["filled_quarters"] / max(stats["total_quarters"], 1), 1),
        }

    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {summary_path}", file=sys.stderr)

    # Write null cases
    null_path = Path(args.null_cases_out)
    null_path.parent.mkdir(parents=True, exist_ok=True)
    with open(null_path, "w", encoding="utf-8") as f:
        for nc in null_cases:
            f.write(json.dumps(nc) + "\n")
    print(f"Wrote {null_path} ({len(null_cases)} null cases)", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: gap-scan
# ═══════════════════════════════════════════════════════════════════════════

_GAP_SCAN_QUERY = """\
MATCH (r:Report {accessionNo: $accession})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname STARTS WITH 'us-gaap:'
  AND con.qname IN $candidates
  AND NOT exists { (f)-[:FACT_MEMBER]->(:Member) }
  AND f.value IS NOT NULL
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE p.start_date IS NOT NULL
RETURN DISTINCT con.qname AS concept, f.value AS value, p.start_date AS period_start, p.end_date AS period_end
"""

_CORPUS_SCAN_QUERY = """\
MATCH (r:Report {accessionNo: $accession})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname STARTS WITH 'us-gaap:'
  AND NOT exists { (f)-[:FACT_MEMBER]->(:Member) }
  AND f.value IS NOT NULL
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE p.start_date IS NOT NULL
RETURN DISTINCT con.qname AS concept, f.value AS value, p.start_date AS period_start, p.end_date AS period_end
"""


def _is_numeric(val) -> bool:
    """Check if a value is numeric (not a text block)."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    s = str(val).replace(",", "").replace("-", "").replace(".", "")
    return s.isdigit() and len(str(val)) < 30  # text blocks are much longer


def _classify_period_class(period_start, period_end) -> str:
    """Classify as 'instant' or 'duration'."""
    if period_end is None or period_end == "null":
        return "instant"
    if period_start == period_end:
        return "instant"
    return "duration"


def cmd_gap_scan(args):
    """Find candidate concepts in null-case filings."""
    _load_env()
    mgr = _get_manager()

    with open(args.null_cases, encoding="utf-8") as f:
        null_cases = [json.loads(line) for line in f if line.strip()]

    # Group null cases by (metric, accession) for efficient querying
    by_accession: dict[str, list[dict]] = {}
    for nc in null_cases:
        acc = nc.get("primary_accession", "")
        if acc:
            by_accession.setdefault(acc, []).append(nc)

    # Determine candidate list based on source
    candidate_source = args.candidate_source
    reviewed_candidates: dict[str, list[str]] = {}  # metric → [candidate qnames]

    if candidate_source == "reviewed":
        print("Loading reviewed candidates from concept_resolver.py...", file=sys.stderr)
        registry = _load_builder_registry()
        for field, _, _ in registry:
            candidates = _reviewed_candidates_for_metric(field)
            if candidates:
                reviewed_candidates[field] = candidates
                print(f"  {field}: {len(candidates)} candidates — {candidates}", file=sys.stderr)

    # If --metrics specified, filter to only those metrics
    target_metrics = set(args.metrics) if args.metrics else None

    occurrences = []
    candidate_summary: dict[tuple[str, str], dict] = {}  # (metric, qname) → stats
    min_companies = args.min_company_count

    t0 = time.time()
    total_accs = len(by_accession)

    for i, (acc, nc_list) in enumerate(by_accession.items()):
        if i % 100 == 0 and i > 0:
            elapsed = time.time() - t0
            print(f"  {i}/{total_accs} accessions ({elapsed:.0f}s)", file=sys.stderr)

        # Determine which metrics are null in this accession
        null_metrics = {}
        for nc in nc_list:
            metric = nc["metric"]
            if target_metrics and metric not in target_metrics:
                continue
            null_metrics[metric] = nc

        if not null_metrics:
            continue

        # Build candidate list for this accession
        if candidate_source == "reviewed":
            candidates_for_query = set()
            for metric in null_metrics:
                for c in reviewed_candidates.get(metric, []):
                    candidates_for_query.add(c)
            if not candidates_for_query:
                continue
            query = _GAP_SCAN_QUERY
            params = {"accession": acc, "candidates": sorted(candidates_for_query)}
        else:
            # corpus mode — scan all us-gaap concepts
            query = _CORPUS_SCAN_QUERY
            params = {"accession": acc}

        try:
            results = mgr.execute_cypher_query_all(query, params)
        except Exception:
            continue

        # Check each result against structural filters
        for row in results:
            concept = row["concept"]
            value = row["value"]
            period_start = row["period_start"]
            period_end = row["period_end"]

            if not _is_numeric(value):
                continue

            fact_period_class = _classify_period_class(period_start, period_end)

            # Check which null metrics this candidate could fill
            for metric, nc in null_metrics.items():
                # Skip if already in builder registry
                existing = _builder_concepts_for_metric(metric)
                if concept in existing:
                    continue

                # In reviewed mode, only allow reviewed candidates
                if candidate_source == "reviewed":
                    if concept not in reviewed_candidates.get(metric, []):
                        continue

                # Structural filters
                if PERIOD_CLASS.get(metric) != fact_period_class:
                    continue

                # Unit family check — we can't verify unit from the fact alone,
                # but the concept being us-gaap: and having the right period class
                # is sufficient structural evidence for gap-scan.
                # The coexistence audit will verify value compatibility.

                occurrences.append({
                    "metric": metric,
                    "ticker": nc["ticker"],
                    "period": nc["period"],
                    "accession": acc,
                    "candidate_qname": concept,
                    "value": str(value),
                    "period_start": period_start,
                    "period_end": period_end,
                })

                key = (metric, concept)
                if key not in candidate_summary:
                    candidate_summary[key] = {"metric": metric, "candidate_qname": concept,
                                               "occurrence_count": 0, "companies": set()}
                candidate_summary[key]["occurrence_count"] += 1
                candidate_summary[key]["companies"].add(nc["ticker"])

    # Filter by min company count
    candidate_summary = {k: v for k, v in candidate_summary.items()
                         if len(v["companies"]) >= min_companies}

    # Write occurrences
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with open(out_path, mode, encoding="utf-8") as f:
        for occ in occurrences:
            if (occ["metric"], occ["candidate_qname"]) in candidate_summary:
                f.write(json.dumps(occ) + "\n")
    print(f"Wrote {out_path} ({len(occurrences)} occurrences, {mode})", file=sys.stderr)

    # Write summary CSV
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "candidate_qname", "occurrence_count", "company_count", "companies"])
        for (metric, qname), stats in sorted(candidate_summary.items()):
            writer.writerow([
                metric, qname, stats["occurrence_count"],
                len(stats["companies"]),
                ";".join(sorted(stats["companies"])),
            ])
    print(f"Wrote {summary_path} ({len(candidate_summary)} candidates)", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: coexistence-audit
# ═══════════════════════════════════════════════════════════════════════════

_COEXISTENCE_QUERY = """\
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-Q', '10-K', '10-Q/A', '10-K/A']
  AND r.xbrl_status = 'COMPLETED'
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname IN $concepts
  AND NOT exists { (f)-[:FACT_MEMBER]->(:Member) }
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:HAS_PERIOD]->(p:Period)
WHERE p.start_date IS NOT NULL
RETURN r.periodOfReport AS period, r.accessionNo AS accession,
       con.qname AS concept, f.value AS value, f.decimals AS decimals,
       p.start_date AS period_start, p.end_date AS period_end
ORDER BY r.periodOfReport DESC, r.created DESC
"""


def _round_to_decimals(value: float, decimals: int) -> float:
    """Round value to the given XBRL decimals precision."""
    if decimals >= 0:
        return round(value, decimals)
    else:
        factor = 10 ** abs(decimals)
        return round(value / factor) * factor


def _parse_decimals_safe(val) -> int | None:
    """Parse XBRL decimals field. Returns None if unusable."""
    if val is None or val == "INF" or val == "inf":
        return None  # INF means exact — no rounding needed, treat as exact match
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _values_match(val1: float, dec1: int | None, val2: float, dec2: int | None) -> bool:
    """Check if two values match under the coexistence rounding rules.

    - If both have usable decimals: round both to the less precise, require equality.
    - If either lacks decimals: require exact numeric equality.
    - If both are INF (None): require exact equality.
    """
    if dec1 is not None and dec2 is not None:
        # Both have usable decimals — round to less precise
        less_precise = min(dec1, dec2)
        return _round_to_decimals(val1, less_precise) == _round_to_decimals(val2, less_precise)
    else:
        # Either lacks decimals — require exact equality
        return val1 == val2


def cmd_coexistence_audit(args):
    """Find filings where primary and candidate coexist, compare values."""
    _load_env()
    mgr = _get_manager()

    with open(args.universe, encoding="utf-8") as f:
        universe = json.load(f)
    ticker_set = {e["ticker"] for e in universe}

    # Load candidates from summary CSV
    candidates: dict[str, list[str]] = {}  # metric → [candidate qnames]
    with open(args.candidates, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric = row["metric"]
            qname = row["candidate_qname"]
            candidates.setdefault(metric, []).append(qname)

    print(f"Auditing {sum(len(v) for v in candidates.values())} candidates across {len(candidates)} metrics", file=sys.stderr)

    from build_prior_financials import classify_period, is_target_period, _parse_value

    pairs = []
    summary_stats: dict[tuple[str, str], dict] = {}

    t0 = time.time()
    tickers_checked = 0

    for ticker_entry in universe:
        ticker = ticker_entry["ticker"]
        tickers_checked += 1
        if tickers_checked % 50 == 0:
            elapsed = time.time() - t0
            print(f"  {tickers_checked}/{len(universe)} ({elapsed:.0f}s)", file=sys.stderr)

        for metric, cand_list in candidates.items():
            primary_concepts = sorted(_builder_concepts_for_metric(metric))
            if not primary_concepts:
                continue

            all_concepts = primary_concepts + cand_list
            try:
                results = mgr.execute_cypher_query_all(
                    _COEXISTENCE_QUERY,
                    {"ticker": ticker, "concepts": all_concepts},
                )
            except Exception:
                continue

            if not results:
                continue

            # Group facts by (period, accession) → concept → fact
            by_period_acc: dict[tuple[str, str], dict[str, list[dict]]] = {}
            for row in results:
                key = (row["period"], row["accession"])
                by_period_acc.setdefault(key, {}).setdefault(row["concept"], []).append(row)

            # For each (period, accession), check if primary AND candidate coexist
            for (period, accession), concept_facts in by_period_acc.items():
                # Find primary value (builder-style: concept priority, target-period, quarterly/instant)
                primary_val = None
                primary_dec = None
                primary_concept = None
                target_ptype = PERIOD_CLASS.get(metric, "duration")

                for pc in primary_concepts:
                    for f in concept_facts.get(pc, []):
                        if not _is_numeric(f["value"]):
                            continue
                        pclass = _classify_period_class(f["period_start"], f["period_end"])
                        if target_ptype == "instant" and pclass == "instant":
                            if f["period_start"] == period or is_target_period(f["period_start"], period):
                                v = _parse_value(f["value"])
                                if v is not None:
                                    primary_val = v
                                    primary_dec = _parse_decimals_safe(f["decimals"])
                                    primary_concept = pc
                                    break
                        elif target_ptype == "duration" and pclass == "duration":
                            cp = classify_period(f["period_start"], f["period_end"])
                            if cp == "quarterly":
                                pe = f["period_end"]
                                if pe and pe != "null" and is_target_period(pe, period):
                                    v = _parse_value(f["value"])
                                    if v is not None:
                                        primary_val = v
                                        primary_dec = _parse_decimals_safe(f["decimals"])
                                        primary_concept = pc
                                        break
                    if primary_val is not None:
                        break

                if primary_val is None:
                    continue

                # Check each candidate
                for cand_qname in cand_list:
                    cand_val = None
                    cand_dec = None
                    for f in concept_facts.get(cand_qname, []):
                        if not _is_numeric(f["value"]):
                            continue
                        pclass = _classify_period_class(f["period_start"], f["period_end"])
                        if target_ptype == "instant" and pclass == "instant":
                            if f["period_start"] == period or is_target_period(f["period_start"], period):
                                v = _parse_value(f["value"])
                                if v is not None:
                                    cand_val = v
                                    cand_dec = _parse_decimals_safe(f["decimals"])
                                    break
                        elif target_ptype == "duration" and pclass == "duration":
                            cp = classify_period(f["period_start"], f["period_end"])
                            if cp == "quarterly":
                                pe = f["period_end"]
                                if pe and pe != "null" and is_target_period(pe, period):
                                    v = _parse_value(f["value"])
                                    if v is not None:
                                        cand_val = v
                                        cand_dec = _parse_decimals_safe(f["decimals"])
                                        break

                    if cand_val is None:
                        continue

                    # We have a coexistence pair!
                    match = _values_match(primary_val, primary_dec, cand_val, cand_dec)
                    pair = {
                        "metric": metric,
                        "ticker": ticker,
                        "period": period,
                        "accession": accession,
                        "primary_concept": primary_concept,
                        "primary_value": primary_val,
                        "primary_decimals": primary_dec,
                        "candidate_qname": cand_qname,
                        "candidate_value": cand_val,
                        "candidate_decimals": cand_dec,
                        "match": match,
                    }
                    pairs.append(pair)

                    key = (metric, cand_qname)
                    if key not in summary_stats:
                        summary_stats[key] = {"metric": metric, "candidate_qname": cand_qname,
                                               "match_count": 0, "mismatch_count": 0,
                                               "tickers": set(), "match_tickers": set()}
                    summary_stats[key]["tickers"].add(ticker)
                    if match:
                        summary_stats[key]["match_count"] += 1
                        summary_stats[key]["match_tickers"].add(ticker)
                    else:
                        summary_stats[key]["mismatch_count"] += 1

    elapsed = time.time() - t0
    print(f"  Done: {len(pairs)} pairs in {elapsed:.0f}s", file=sys.stderr)

    # Write pairs
    pairs_path = Path(args.pairs_out)
    pairs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pairs_path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    print(f"Wrote {pairs_path}", file=sys.stderr)

    # Classify and write summary
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "candidate_qname", "match_count", "mismatch_count",
                         "total_pairs", "ticker_count", "match_ticker_count", "classification"])
        for (metric, qname), stats in sorted(summary_stats.items()):
            total = stats["match_count"] + stats["mismatch_count"]
            ticker_count = len(stats["tickers"])
            match_ticker_count = len(stats["match_tickers"])

            if stats["mismatch_count"] > 0:
                classification = "different_metric"
            elif total == 0:
                classification = "cannot_prove"
            elif total >= 5 and match_ticker_count >= 3:
                classification = "safe_synonym"
            else:
                classification = "conditional"

            writer.writerow([metric, qname, stats["match_count"], stats["mismatch_count"],
                             total, ticker_count, match_ticker_count, classification])
            print(f"  {metric:30s} {qname:60s} {classification:16s} ({total} pairs, {ticker_count} tickers)", file=sys.stderr)

    # Also classify candidates with zero coexistence
    for metric, cand_list in candidates.items():
        for qname in cand_list:
            key = (metric, qname)
            if key not in summary_stats:
                print(f"  {metric:30s} {qname:60s} {'cannot_prove':16s} (0 pairs)", file=sys.stderr)

    print(f"Wrote {summary_path}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# SUBCOMMAND: simulate
# ═══════════════════════════════════════════════════════════════════════════

def cmd_simulate(args):
    """Test one candidate by monkey-patching the builder registry and diffing."""
    _load_env()

    metric = args.candidate[0]
    candidate_qname = args.candidate[1]

    with open(args.universe, encoding="utf-8") as f:
        universe = json.load(f)

    import build_prior_financials as bpf

    baseline_dir = Path(args.baseline_dir)
    out_dir = Path(args.out_dir)
    before_dir = out_dir / "before"
    after_dir = out_dir / "after"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    # Find the metric's entry in the registry
    original_registry = copy.deepcopy(bpf.METRIC_REGISTRY)
    patched = False
    for i, (field, qnames, stmt_type) in enumerate(bpf.METRIC_REGISTRY):
        if field == metric:
            if candidate_qname not in qnames:
                bpf.METRIC_REGISTRY[i] = (field, qnames + [candidate_qname], stmt_type)
                patched = True
            break

    if not patched:
        print(f"Candidate {candidate_qname} already in {metric} or metric not found", file=sys.stderr)
        return

    # Rebuild derived constants
    bpf.ALL_CONCEPT_QNAMES = []
    for _, qn, _ in bpf.METRIC_REGISTRY:
        bpf.ALL_CONCEPT_QNAMES.extend(qn)
    bpf.ALL_CONCEPT_QNAMES = list(dict.fromkeys(bpf.ALL_CONCEPT_QNAMES))

    bpf._CONCEPT_TO_FIELD = {}
    for f, qn, _ in bpf.METRIC_REGISTRY:
        for q in qn:
            if q not in bpf._CONCEPT_TO_FIELD:
                bpf._CONCEPT_TO_FIELD[q] = f

    print(f"Simulating: {metric} += {candidate_qname}", file=sys.stderr)
    print(f"  Running patched builder across {len(universe)} tickers...", file=sys.stderr)

    diffs = []
    t0 = time.time()

    for idx, entry in enumerate(universe):
        ticker = entry["ticker"]
        period = entry.get("anchor_period") or entry["latest_item_202_period"]

        if idx % 50 == 0 and idx > 0:
            elapsed = time.time() - t0
            print(f"  {idx}/{len(universe)} ({elapsed:.0f}s) diffs={len(diffs)}", file=sys.stderr)

        # Load baseline
        baseline_path = baseline_dir / f"{ticker}.json"
        if not baseline_path.exists():
            continue
        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)

        # Run patched builder
        try:
            qi = {"period_of_report": period, "filed_8k": "", "market_session": "", "quarter_label": ""}
            patched_packet = bpf.build_prior_financials(ticker, qi, out_path=str(after_dir / f"{ticker}.json"))
        except Exception as e:
            diffs.append({"ticker": ticker, "change_type": "error", "error": str(e)})
            continue

        # Copy baseline to before dir for reference
        with open(before_dir / f"{ticker}.json", "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)

        # Diff quarters
        baseline_quarters = {q["period"]: q for q in baseline.get("quarters", [])}
        patched_quarters = {q["period"]: q for q in patched_packet.get("quarters", [])}

        for period_key in set(baseline_quarters.keys()) | set(patched_quarters.keys()):
            bq = baseline_quarters.get(period_key, {})
            pq = patched_quarters.get(period_key, {})

            # Check quarter identity
            if (period_key in baseline_quarters) != (period_key in patched_quarters):
                diffs.append({
                    "ticker": ticker, "period": period_key,
                    "change_type": "quarter_identity_change",
                    "detail": "present_in_baseline" if period_key in baseline_quarters else "present_in_patched",
                })
                continue

            # Check metric values
            bval = bq.get(metric)
            pval = pq.get(metric)

            if bval is None and pval is not None:
                diffs.append({
                    "ticker": ticker, "period": period_key,
                    "change_type": "null_to_value",
                    "metric": metric,
                    "new_value": pval,
                    "fiscal_label": pq.get("fiscal_label", ""),
                })
            elif bval is not None and pval is not None and bval != pval:
                diffs.append({
                    "ticker": ticker, "period": period_key,
                    "change_type": "value_changed",
                    "metric": metric,
                    "old_value": bval,
                    "new_value": pval,
                    "fiscal_label": pq.get("fiscal_label", ""),
                })

    # Restore original registry
    bpf.METRIC_REGISTRY[:] = original_registry
    bpf.ALL_CONCEPT_QNAMES = []
    for _, qn, _ in bpf.METRIC_REGISTRY:
        bpf.ALL_CONCEPT_QNAMES.extend(qn)
    bpf.ALL_CONCEPT_QNAMES = list(dict.fromkeys(bpf.ALL_CONCEPT_QNAMES))
    bpf._CONCEPT_TO_FIELD = {}
    for f, qn, _ in bpf.METRIC_REGISTRY:
        for q in qn:
            if q not in bpf._CONCEPT_TO_FIELD:
                bpf._CONCEPT_TO_FIELD[q] = f

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.0f}s", file=sys.stderr)

    # Write diffs
    diff_path = out_dir / "diff.jsonl"
    with open(diff_path, "w", encoding="utf-8") as f:
        for d in diffs:
            f.write(json.dumps(d) + "\n")

    # Summarize
    null_to_value = sum(1 for d in diffs if d["change_type"] == "null_to_value")
    value_changed = sum(1 for d in diffs if d["change_type"] == "value_changed")
    identity_changed = sum(1 for d in diffs if d["change_type"] == "quarter_identity_change")
    errors = sum(1 for d in diffs if d["change_type"] == "error")

    print(f"\nSimulation results for {metric} += {candidate_qname}:", file=sys.stderr)
    print(f"  null_to_value:    {null_to_value}", file=sys.stderr)
    print(f"  value_changed:    {value_changed} {'⚠ FORBIDDEN' if value_changed else '✓'}", file=sys.stderr)
    print(f"  identity_changed: {identity_changed} {'⚠ FORBIDDEN' if identity_changed else '✓'}", file=sys.stderr)
    print(f"  errors:           {errors}", file=sys.stderr)
    print(f"Wrote {diff_path}", file=sys.stderr)

    if value_changed > 0 or identity_changed > 0:
        print(f"\n⚠ CANDIDATE FAILED: forbidden diff outcomes detected", file=sys.stderr)
    elif null_to_value > 0:
        print(f"\n✓ CANDIDATE PASSED: {null_to_value} null→value recoveries, 0 regressions", file=sys.stderr)
    else:
        print(f"\n— CANDIDATE NO-OP: no effect on any ticker", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Concept Fallback Discovery — Safe Coverage Expansion")
    sub = parser.add_subparsers(dest="command", required=True)

    # universe
    p_uni = sub.add_parser("universe", help="Capture company universe")
    p_uni.add_argument("--out", required=True, help="Output JSON path")

    # baseline
    p_base = sub.add_parser("baseline", help="Run current builder, compute gaps")
    p_base.add_argument("--universe", required=True, help="Universe JSON")
    p_base.add_argument("--packet-dir", required=True, help="Directory for builder packets")
    p_base.add_argument("--summary-out", required=True, help="Gap summary JSON")
    p_base.add_argument("--null-cases-out", required=True, help="Null cases JSONL")

    # gap-scan
    p_gap = sub.add_parser("gap-scan", help="Find candidate concepts")
    p_gap.add_argument("--universe", required=True)
    p_gap.add_argument("--null-cases", required=True)
    p_gap.add_argument("--candidate-source", required=True, choices=["reviewed", "corpus"])
    p_gap.add_argument("--reviewed-source", help="Path to concept_resolver.py (for reviewed mode)")
    p_gap.add_argument("--out", required=True)
    p_gap.add_argument("--summary-out", required=True)
    p_gap.add_argument("--min-company-count", type=int, default=3)
    p_gap.add_argument("--namespace", default="us-gaap")
    p_gap.add_argument("--consolidated-only", action="store_true", default=True)
    p_gap.add_argument("--numeric-only", action="store_true", default=True)
    p_gap.add_argument("--metrics", nargs="*", help="Limit to specific metrics")
    p_gap.add_argument("--append", action="store_true", help="Append to existing output")

    # coexistence-audit
    p_coex = sub.add_parser("coexistence-audit", help="Audit candidate coexistence")
    p_coex.add_argument("--universe", required=True)
    p_coex.add_argument("--candidates", required=True, help="Candidate summary CSV")
    p_coex.add_argument("--pairs-out", required=True)
    p_coex.add_argument("--summary-out", required=True)

    # simulate
    p_sim = sub.add_parser("simulate", help="Test candidate via monkey-patch")
    p_sim.add_argument("--universe", required=True)
    p_sim.add_argument("--candidate", nargs=2, required=True, metavar=("METRIC", "QNAME"))
    p_sim.add_argument("--baseline-dir", required=True)
    p_sim.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    if args.command == "universe":
        cmd_universe(args)
    elif args.command == "baseline":
        cmd_baseline(args)
    elif args.command == "gap-scan":
        cmd_gap_scan(args)
    elif args.command == "coexistence-audit":
        cmd_coexistence_audit(args)
    elif args.command == "simulate":
        cmd_simulate(args)


if __name__ == "__main__":
    main()
