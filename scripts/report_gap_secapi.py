#!/usr/bin/env python3
"""
SEC Report Gap Analysis — sec-api.io vs Neo4j
==============================================
Queries sec-api.io (our actual data source) for all 796 companies and compares
accession numbers against Neo4j AND the EDGAR gap analysis.

Three-way comparison: EDGAR (ground truth) vs sec-api.io (fetchable) vs Neo4j (what we have)

Uses the same QueryApi and ticker-based search as our backfill pipeline.
Rate limited to 5 req/sec to avoid interfering with running backfill.

Usage:
    python scripts/report_gap_secapi.py [--start-date 2023-01-01] [--end-date 2026-03-28]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from sec_api import QueryApi
from neo4j import GraphDatabase
from ratelimit import limits, sleep_and_retry

# --- Config ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.40.73:30687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "eventmarket")
SEC_API_KEY = os.getenv("SEC_API_KEY")

PRIMARY_FORM_TYPES = ['8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A']
MAX_PAGE_SIZE = 50

OUTPUT_DIR = Path("earnings-analysis/gap_analysis")
PROGRESS_FILE = OUTPUT_DIR / "secapi_progress.json"


@sleep_and_retry
@limits(calls=5, period=1)  # 5 req/sec — conservative to not interfere with backfill
def rate_limited_query(query_api, params):
    return query_api.get_filings(params)


def get_neo4j_companies(driver):
    """Get all companies with CIKs and tickers from Neo4j."""
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Company) WHERE c.cik IS NOT NULL "
            "RETURN c.ticker AS ticker, c.cik AS cik "
            "ORDER BY c.ticker"
        )
        return [{"ticker": r["ticker"], "cik": r["cik"]} for r in result]


def get_neo4j_accessions(driver, start_date, end_date):
    """Get all report accession numbers from Neo4j."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (r:Report)
            WHERE r.created >= $start AND r.created < $end_plus
            AND r.formType IN $forms
            RETURN r.accessionNo AS accession
            """,
            start=start_date,
            end_plus=end_date + "T23:59:59",
            forms=PRIMARY_FORM_TYPES
        )
        return {r["accession"].replace("-", "") for r in result if r["accession"]}


def load_edgar_accessions():
    """Load EDGAR accession numbers from previous gap analysis."""
    edgar_file = OUTPUT_DIR / "edgar_filings_2023-01-01_to_2026-03-28.csv"
    if not edgar_file.exists():
        print("WARNING: EDGAR filings file not found. Run report_gap_analysis.py first.")
        return {}, {}

    # ticker -> set of accession_clean
    edgar_by_ticker = {}
    # accession_clean -> {ticker, form, date}
    edgar_details = {}
    with open(edgar_file) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            ticker, cik, acc, form, filed_date, in_neo4j = row
            acc_clean = acc.replace("-", "")
            if ticker not in edgar_by_ticker:
                edgar_by_ticker[ticker] = set()
            edgar_by_ticker[ticker].add(acc_clean)
            edgar_details[acc_clean] = {
                "ticker": ticker, "accession": acc,
                "form": form, "filedDate": filed_date,
                "in_neo4j": in_neo4j.strip()
            }
    return edgar_by_ticker, edgar_details


def fetch_secapi_filings(query_api, ticker, form_type, date_from, date_to):
    """Fetch all filings for a ticker+formType from sec-api.io (same as our backfill)."""
    all_filings = []
    from_index = 0

    while True:
        search_query = (
            f'ticker:{ticker} AND '
            f'formType:"{form_type}" AND '
            f'filedAt:[{date_from} TO {date_to}]'
        )

        params = {
            "query": search_query,
            "from": str(from_index),
            "size": str(MAX_PAGE_SIZE),
            "sort": [{"filedAt": {"order": "desc"}}]
        }

        try:
            response = rate_limited_query(query_api, params)
        except Exception as e:
            print(f"  ERROR {ticker} {form_type}: {e}")
            break

        if not response or "filings" not in response:
            break

        filings = response["filings"]
        if not filings:
            break

        for f in filings:
            acc = f.get("accessionNo", "")
            if acc:
                all_filings.append({
                    "accession": acc,
                    "accession_clean": acc.replace("-", ""),
                    "form": f.get("formType", ""),
                    "filedAt": f.get("filedAt", "")[:10],
                    "ticker_in_response": f.get("ticker", ""),
                })

        total = response.get("total", {}).get("value", 0)
        from_index += MAX_PAGE_SIZE
        if from_index >= total:
            break

    return all_filings


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_tickers": [], "started_at": datetime.now().isoformat()}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def main():
    parser = argparse.ArgumentParser(description="SEC Report Gap Analysis — sec-api.io")
    parser.add_argument("--start-date", default="2023-01-01")
    parser.add_argument("--end-date", default="2026-03-28")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--ticker", help="Single ticker for debugging")
    args = parser.parse_args()

    if not SEC_API_KEY:
        print("ERROR: SEC_API_KEY not set")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    companies = get_neo4j_companies(driver)
    if args.ticker:
        companies = [c for c in companies if c["ticker"] == args.ticker.upper()]

    print(f"Loading Neo4j accessions...")
    neo4j_accessions = get_neo4j_accessions(driver, args.start_date, args.end_date)
    driver.close()
    print(f"  {len(neo4j_accessions)} accessions in Neo4j")

    # Load EDGAR data
    print("Loading EDGAR analysis...")
    edgar_by_ticker, edgar_details = load_edgar_accessions()
    print(f"  {len(edgar_details)} EDGAR filings loaded")

    # sec-api.io client
    query_api = QueryApi(api_key=SEC_API_KEY)

    # Progress
    progress = load_progress() if args.resume else {"completed_tickers": [], "started_at": datetime.now().isoformat()}

    # Output files
    secapi_file = OUTPUT_DIR / f"secapi_filings_{args.start_date}_to_{args.end_date}.csv"
    threeway_file = OUTPUT_DIR / f"threeway_comparison_{args.start_date}_to_{args.end_date}.csv"
    threeway_summary_file = OUTPUT_DIR / f"threeway_summary_{args.start_date}_to_{args.end_date}.csv"

    secapi_fh = open(secapi_file, "w", newline="")
    secapi_writer = csv.writer(secapi_fh)
    secapi_writer.writerow(["ticker", "accession", "formType", "filedAt", "in_neo4j", "in_edgar"])

    threeway_fh = open(threeway_file, "w", newline="")
    threeway_writer = csv.writer(threeway_fh)
    threeway_writer.writerow(["ticker", "accession", "formType", "filedAt", "in_secapi", "in_edgar", "in_neo4j", "gap_type"])

    # Stats
    stats = {
        "total_secapi": 0,
        "secapi_and_neo4j": 0,          # sec-api has it, we have it
        "secapi_not_neo4j": 0,           # sec-api has it, we DON'T (pipeline lost it)
        "edgar_not_secapi": 0,           # EDGAR has it, sec-api doesn't (data source gap)
        "edgar_not_secapi_not_neo4j": 0, # EDGAR has, sec-api doesn't, we don't (unfixable)
        "neo4j_not_secapi": 0,           # we have it, sec-api doesn't return it (mystery)
    }
    monthly_pipeline_gaps = {}  # gaps where sec-api HAS it but we don't
    monthly_source_gaps = {}    # gaps where sec-api DOESN'T have it

    all_secapi_accessions_by_ticker = {}

    try:
        for idx, company in enumerate(companies):
            ticker = company["ticker"]

            if ticker in progress["completed_tickers"]:
                continue

            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"\n[{idx+1}/{len(companies)}] Processing... "
                      f"(sec-api: {stats['total_secapi']}, "
                      f"pipeline_lost: {stats['secapi_not_neo4j']}, "
                      f"source_gap: {stats['edgar_not_secapi']})")

            # Fetch from sec-api.io (same as our backfill)
            ticker_filings = []
            for form_type in PRIMARY_FORM_TYPES:
                filings = fetch_secapi_filings(
                    query_api, ticker, form_type, args.start_date, args.end_date
                )
                ticker_filings.extend(filings)

            # Build set of sec-api accessions for this ticker
            secapi_accs = set()
            for f in ticker_filings:
                acc_clean = f["accession_clean"]
                secapi_accs.add(acc_clean)
                in_neo4j = acc_clean in neo4j_accessions
                in_edgar = acc_clean in edgar_details

                secapi_writer.writerow([
                    ticker, f["accession"], f["form"], f["filedAt"],
                    "YES" if in_neo4j else "NO",
                    "YES" if in_edgar else "NO"
                ])

                stats["total_secapi"] += 1
                if in_neo4j:
                    stats["secapi_and_neo4j"] += 1
                else:
                    stats["secapi_not_neo4j"] += 1
                    # This is a PIPELINE gap — sec-api has it, we should have it
                    month = f["filedAt"][:7]
                    if month not in monthly_pipeline_gaps:
                        monthly_pipeline_gaps[month] = {"8-K": 0, "10-Q": 0, "10-K": 0, "other": 0, "total": 0}
                    bucket = f["form"] if f["form"] in ["8-K", "10-Q", "10-K"] else "other"
                    monthly_pipeline_gaps[month][bucket] += 1
                    monthly_pipeline_gaps[month]["total"] += 1

                    threeway_writer.writerow([
                        ticker, f["accession"], f["form"], f["filedAt"],
                        "YES", "YES" if in_edgar else "NO", "NO", "PIPELINE_LOST"
                    ])

            all_secapi_accessions_by_ticker[ticker] = secapi_accs

            # Check EDGAR filings NOT in sec-api (data source gap)
            edgar_accs = edgar_by_ticker.get(ticker, set())
            edgar_only = edgar_accs - secapi_accs
            for acc_clean in edgar_only:
                detail = edgar_details.get(acc_clean, {})
                in_neo4j = acc_clean in neo4j_accessions
                stats["edgar_not_secapi"] += 1
                if not in_neo4j:
                    stats["edgar_not_secapi_not_neo4j"] += 1

                month = detail.get("filedDate", "")[:7]
                if month and not in_neo4j:
                    if month not in monthly_source_gaps:
                        monthly_source_gaps[month] = {"8-K": 0, "10-Q": 0, "10-K": 0, "other": 0, "total": 0}
                    bucket = detail.get("form", "other")
                    bucket = bucket if bucket in ["8-K", "10-Q", "10-K"] else "other"
                    monthly_source_gaps[month][bucket] += 1
                    monthly_source_gaps[month]["total"] += 1

                threeway_writer.writerow([
                    ticker, detail.get("accession", acc_clean),
                    detail.get("form", "?"), detail.get("filedDate", "?"),
                    "NO", "YES", "YES" if in_neo4j else "NO",
                    "SOURCE_GAP" if not in_neo4j else "SOURCE_GAP_BUT_HAVE"
                ])

            progress["completed_tickers"].append(ticker)
            if (idx + 1) % 50 == 0:
                save_progress(progress)
                secapi_fh.flush()
                threeway_fh.flush()

    except KeyboardInterrupt:
        print("\nInterrupted! Saving...")
        save_progress(progress)
    finally:
        secapi_fh.close()
        threeway_fh.close()

    # Write summary
    with open(threeway_summary_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["=== THREE-WAY COMPARISON SUMMARY ==="])
        w.writerow(["Date Range", f"{args.start_date} to {args.end_date}"])
        w.writerow(["Companies", len(progress["completed_tickers"])])
        w.writerow([])
        w.writerow(["=== TOTALS ==="])
        w.writerow(["sec-api.io filings found", stats["total_secapi"]])
        w.writerow(["sec-api + Neo4j (have it)", stats["secapi_and_neo4j"]])
        w.writerow(["sec-api but NOT Neo4j (PIPELINE LOST)", stats["secapi_not_neo4j"]])
        w.writerow(["EDGAR but NOT sec-api (SOURCE GAP)", stats["edgar_not_secapi"]])
        w.writerow(["EDGAR not sec-api not Neo4j (UNFIXABLE)", stats["edgar_not_secapi_not_neo4j"]])
        w.writerow([])
        w.writerow(["=== PIPELINE GAPS BY MONTH (sec-api HAS it, we DON'T) ==="])
        w.writerow(["Month", "8-K", "10-Q", "10-K", "Other", "Total"])
        for m in sorted(monthly_pipeline_gaps.keys()):
            g = monthly_pipeline_gaps[m]
            w.writerow([m, g["8-K"], g["10-Q"], g["10-K"], g["other"], g["total"]])
        w.writerow([])
        w.writerow(["=== SOURCE GAPS BY MONTH (EDGAR has, sec-api DOESN'T, we don't) ==="])
        w.writerow(["Month", "8-K", "10-Q", "10-K", "Other", "Total"])
        for m in sorted(monthly_source_gaps.keys()):
            g = monthly_source_gaps[m]
            w.writerow([m, g["8-K"], g["10-Q"], g["10-K"], g["other"], g["total"]])

    # Console output
    print(f"\n{'='*60}")
    print(f"THREE-WAY COMPARISON COMPLETE")
    print(f"{'='*60}")
    print(f"Companies: {len(progress['completed_tickers'])}")
    print(f"sec-api.io filings:      {stats['total_secapi']}")
    print(f"  Matched in Neo4j:      {stats['secapi_and_neo4j']}")
    print(f"  PIPELINE LOST:         {stats['secapi_not_neo4j']}  (sec-api has, we don't — FIXABLE)")
    print(f"  SOURCE GAP:            {stats['edgar_not_secapi']}  (EDGAR has, sec-api doesn't)")
    print(f"  UNFIXABLE:             {stats['edgar_not_secapi_not_neo4j']}  (neither sec-api nor Neo4j)")
    print(f"\nPipeline gaps by month (fixable — sec-api has, we lost):")
    for m in sorted(monthly_pipeline_gaps.keys()):
        g = monthly_pipeline_gaps[m]
        print(f"  {m}: {g['total']:4d} (8-K:{g['8-K']:3d} 10-Q:{g['10-Q']:3d} 10-K:{g['10-K']:3d})")
    print(f"\nSource gaps by month (unfixable — EDGAR has, sec-api doesn't):")
    for m in sorted(monthly_source_gaps.keys()):
        g = monthly_source_gaps[m]
        print(f"  {m}: {g['total']:4d} (8-K:{g['8-K']:3d} 10-Q:{g['10-Q']:3d} 10-K:{g['10-K']:3d})")
    print(f"\nFiles: {secapi_file}, {threeway_file}, {threeway_summary_file}")


if __name__ == "__main__":
    main()
