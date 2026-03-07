#!/usr/bin/env python3
"""Compute precise transcript gaps: which companies are missing which quarters.

Compares earningscall API inventory against Neo4j Transcript nodes
and writes a comprehensive gap analysis JSON.

Usage:
  source venv/bin/activate
  python3 scripts/transcript_gap_analysis.py
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import logging
logging.getLogger("neo4j").setLevel(logging.ERROR)

import redis
import earningscall
from earningscall import get_company
from neo4j import GraphDatabase


# ── Configuration ──────────────────────────────────────────────────────────
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://192.168.40.73:30687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD")
REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))
EARNINGS_API_KEY = os.environ.get("EARNINGS_CALL_API_KEY")
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "earnings-analysis" / "test-outputs" / "transcript-gap-analysis.json"


def month_to_quarter(month: int) -> int:
    """Convert month (1-12) to quarter (1-4)."""
    return (month - 1) // 3 + 1


def get_neo4j_transcripts() -> set:
    """Query Neo4j for all existing (symbol, year, quarter) tuples."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    query = """
    MATCH (t:Transcript)
    WHERE t.conference_datetime IS NOT NULL
    RETURN t.symbol AS symbol, t.id AS id, t.conference_datetime AS conf_dt,
           substring(t.conference_datetime, 0, 7) AS month
    """

    existing = set()
    records = []

    with driver.session() as session:
        result = session.run(query)
        for record in result:
            symbol = record["symbol"]
            conf_dt = record["conf_dt"]
            tid = record["id"]

            if not symbol or not conf_dt:
                continue

            # Parse year/quarter from conference_datetime string (format: 2025-01-30T...)
            try:
                year = int(conf_dt[:4])
                month = int(conf_dt[5:7])
                quarter = month_to_quarter(month)
                existing.add((symbol.upper(), year, quarter))
            except (ValueError, IndexError):
                pass

            records.append({
                "symbol": symbol,
                "id": tid,
                "conf_dt": conf_dt,
            })

    driver.close()
    print(f"[Neo4j] Found {len(records)} transcript records, {len(existing)} unique (symbol, year, quarter) tuples", flush=True)
    return existing, records


def get_universe_symbols() -> list:
    """Load tradable universe symbols from Redis."""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    raw = r.get("admin:tradable_universe:symbols")
    r.close()

    if not raw:
        print("[Redis] ERROR: No symbols found at admin:tradable_universe:symbols")
        sys.exit(1)

    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    print(f"[Redis] Loaded {len(symbols)} symbols from tradable universe", flush=True)
    return symbols


def get_api_events(symbols: list) -> dict:
    """Query earningscall API for all available events per symbol.

    Rate limit: 20 calls/min. The library uses requests_cache (stores HTTP
    responses on disk) so cached companies are instant. For uncached companies,
    the library's built-in exponential backoff retry handles 429s automatically.

    Returns dict: { symbol: [ (year, quarter, conference_date_str), ... ] }
    """
    earningscall.api_key = EARNINGS_API_KEY
    earningscall.enable_requests_cache = True
    earningscall.retry_strategy = {
        "strategy": "exponential",
        "base_delay": 2,
        "max_attempts": 10,
    }

    api_data = {}
    errors = []
    total = len(symbols)
    step_start = time.time()

    for i, symbol in enumerate(symbols, 1):
        if i % 50 == 0 or i == 1:
            elapsed = time.time() - step_start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f"[API] Progress: {i}/{total} ({100*i//total}%) — "
                  f"{len(api_data)} found, {len(errors)} errors — "
                  f"ETA: {eta/60:.0f}min", flush=True)

        try:
            company = get_company(symbol)
            if company is None:
                errors.append((symbol, "get_company returned None"))
                continue

            events = []
            for event in company.events():
                conf_date_str = None
                if event.conference_date:
                    conf_date_str = event.conference_date.isoformat()
                events.append((event.year, event.quarter, conf_date_str))

            if events:
                api_data[symbol] = events

        except Exception as e:
            errors.append((symbol, str(e)))

    print(f"[API] Done in {(time.time()-step_start)/60:.1f} min. "
          f"Found events for {len(api_data)} companies. {len(errors)} errors.", flush=True)
    if errors:
        # Show first few errors
        for sym, err in errors[:10]:
            print(f"  Error: {sym} -- {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    return api_data, errors


def compute_gaps(neo4j_existing: set, api_data: dict):
    """Compute what the API has that Neo4j doesn't."""
    # Total API events
    total_api_events = sum(len(events) for events in api_data.values())

    # Build the full set of (symbol, year, quarter) from API
    api_set = set()
    for symbol, events in api_data.items():
        for year, quarter, _ in events:
            api_set.add((symbol, year, quarter))

    # Gaps = in API but not in Neo4j
    missing = api_set - neo4j_existing
    total_missing = len(missing)

    # ── by_period ──
    by_period = defaultdict(list)
    for symbol, year, quarter in sorted(missing):
        period_key = f"{year}-Q{quarter}"
        by_period[period_key].append(symbol)

    by_period_out = {}
    for period in sorted(by_period.keys(), reverse=True):
        companies = sorted(by_period[period])
        by_period_out[period] = {
            "missing": len(companies),
            "companies": companies,
        }

    # ── by_company ──
    by_company = {}
    company_gaps = defaultdict(list)
    for symbol, year, quarter in missing:
        company_gaps[symbol].append(f"{year}Q{quarter}")

    for symbol in sorted(company_gaps.keys()):
        total_available = len(api_data.get(symbol, []))
        total_in_neo4j = sum(1 for s, y, q in neo4j_existing if s == symbol)
        missing_quarters = sorted(company_gaps[symbol])
        by_company[symbol] = {
            "total_available": total_available,
            "total_in_neo4j": total_in_neo4j,
            "missing_quarters": missing_quarters,
        }

    return {
        "total_missing": total_missing,
        "by_period": by_period_out,
        "by_company": by_company,
    }, api_set, total_api_events


def build_backfill_plan(gaps_by_period: dict):
    """Build a prioritized backfill plan."""
    priority_1_periods = []  # 2025-10 to 2026-03 (recent)
    priority_2_periods = []  # 2024-01 to 2024-12 (holes)
    priority_3_periods = []  # pre-2023

    p1_count = 0
    p2_count = 0
    p3_count = 0

    for period, info in gaps_by_period.items():
        # Parse period like "2025-Q4" -> year=2025, q=4
        parts = period.split("-Q")
        year = int(parts[0])
        quarter = int(parts[1])
        count = info["missing"]

        if (year == 2025 and quarter >= 4) or (year == 2026):
            priority_1_periods.append(period)
            p1_count += count
        elif year == 2024:
            priority_2_periods.append(period)
            p2_count += count
        elif year <= 2023:
            priority_3_periods.append(period)
            p3_count += count
        else:
            # 2025 Q1-Q3
            priority_2_periods.append(period)
            p2_count += count

    return {
        "priority_1_recent": {
            "period": "2025-Q4 to 2026-Q1",
            "missing_count": p1_count,
            "date_ranges": sorted(priority_1_periods),
        },
        "priority_2_2024_holes": {
            "period": "2024 + 2025-Q1-Q3",
            "missing_count": p2_count,
            "date_ranges": sorted(priority_2_periods),
        },
        "priority_3_pre2023": {
            "period": "pre-2024",
            "missing_count": p3_count,
            "date_ranges": sorted(priority_3_periods),
        },
    }


def print_summary(result: dict):
    """Print a human-readable summary table."""
    print("\n" + "=" * 80)
    print("TRANSCRIPT GAP ANALYSIS SUMMARY")
    print("=" * 80)

    print(f"\nRun date:          {result['run_date']}")
    print(f"Universe size:     {result['universe_size']} symbols")
    print(f"API coverage:      {result['api_coverage']['total_companies_found']} companies, {result['api_coverage']['total_events_available']} events")
    print(f"Neo4j existing:    {result['neo4j_existing']['total_transcripts']} unique (symbol, year, quarter)")
    print(f"Total missing:     {result['gaps']['total_missing']}")

    print(f"\n{'─' * 80}")
    print("GAPS BY PERIOD (most recent first)")
    print(f"{'─' * 80}")
    print(f"{'Period':<12} {'Missing':>8}   Companies (first 10)")
    print(f"{'─' * 12} {'─' * 8}   {'─' * 50}")

    by_period = result["gaps"]["by_period"]
    for period in list(by_period.keys())[:20]:  # Show top 20 periods
        info = by_period[period]
        companies_preview = ", ".join(info["companies"][:10])
        if len(info["companies"]) > 10:
            companies_preview += f" ... (+{len(info['companies']) - 10} more)"
        print(f"{period:<12} {info['missing']:>8}   {companies_preview}")

    if len(by_period) > 20:
        print(f"  ... and {len(by_period) - 20} more periods")

    print(f"\n{'─' * 80}")
    print("BACKFILL PLAN")
    print(f"{'─' * 80}")
    bp = result["backfill_plan"]
    print(f"  Priority 1 (recent):  {bp['priority_1_recent']['missing_count']:>6} missing  [{bp['priority_1_recent']['period']}]")
    print(f"  Priority 2 (2024):    {bp['priority_2_2024_holes']['missing_count']:>6} missing  [{bp['priority_2_2024_holes']['period']}]")
    print(f"  Priority 3 (pre-2024):{bp['priority_3_pre2023']['missing_count']:>6} missing  [{bp['priority_3_pre2023']['period']}]")

    # Top 10 companies with most gaps
    by_company = result["gaps"]["by_company"]
    if by_company:
        sorted_companies = sorted(by_company.items(), key=lambda x: len(x[1]["missing_quarters"]), reverse=True)
        print(f"\n{'─' * 80}")
        print("TOP 20 COMPANIES WITH MOST GAPS")
        print(f"{'─' * 80}")
        print(f"{'Symbol':<8} {'Available':>10} {'In Neo4j':>10} {'Missing':>8}   Missing quarters")
        print(f"{'─' * 8} {'─' * 10} {'─' * 10} {'─' * 8}   {'─' * 30}")
        for symbol, info in sorted_companies[:20]:
            quarters_preview = ", ".join(info["missing_quarters"][:5])
            if len(info["missing_quarters"]) > 5:
                quarters_preview += f" ... (+{len(info['missing_quarters']) - 5})"
            print(f"{symbol:<8} {info['total_available']:>10} {info['total_in_neo4j']:>10} {len(info['missing_quarters']):>8}   {quarters_preview}")

    print(f"\n{'=' * 80}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"{'=' * 80}\n")


def main():
    start_time = time.time()

    print("=" * 80)
    print("TRANSCRIPT GAP ANALYSIS")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: Get existing transcripts from Neo4j
    print("\n[Step 1] Querying Neo4j for existing transcripts...")
    neo4j_existing, neo4j_records = get_neo4j_transcripts()

    # Step 2: Load universe from Redis
    print("\n[Step 2] Loading tradable universe from Redis...")
    symbols = get_universe_symbols()

    # Step 3: Query earningscall API for all companies
    print("\n[Step 3] Querying earningscall API for all available events...")
    print(f"  This may take a while ({len(symbols)} companies, rate limited)...")
    api_data, api_errors = get_api_events(symbols)

    # Step 4: Compute gaps
    print("\n[Step 4] Computing gaps...")
    gaps, api_set, total_api_events = compute_gaps(neo4j_existing, api_data)

    # Step 5: Build backfill plan
    backfill_plan = build_backfill_plan(gaps["by_period"])

    # Build final result
    result = {
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "universe_size": len(symbols),
        "api_coverage": {
            "total_companies_found": len(api_data),
            "total_events_available": total_api_events,
            "companies_not_found": len(api_errors),
            "errors": [{"symbol": s, "error": e} for s, e in api_errors[:50]],
        },
        "neo4j_existing": {
            "total_transcripts": len(neo4j_existing),
        },
        "gaps": gaps,
        "backfill_plan": backfill_plan,
        "elapsed_seconds": round(time.time() - start_time, 1),
    }

    # Save to JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Print summary
    print_summary(result)

    elapsed = time.time() - start_time
    print(f"Completed in {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
