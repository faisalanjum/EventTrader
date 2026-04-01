#!/usr/bin/env python3
"""
SEC Report Gap Analysis
=======================
Compares reports in Neo4j against SEC EDGAR to find missing filings.

For each company in our universe (~796), queries SEC EDGAR's free submissions
API and compares accession numbers against Neo4j. Outputs gaps as CSV.

Uses data.sec.gov (free, separate from sec-api.io used by backfill).
Rate limit: 10 req/sec with User-Agent header.

Usage:
    python scripts/report_gap_analysis.py [--start-date 2023-01-01] [--end-date 2026-03-28] [--resume]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

import requests
from neo4j import GraphDatabase

# --- Config ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.40.73:30687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "eventmarket")

EDGAR_BASE = "https://data.sec.gov/submissions"
USER_AGENT = "EventMarketDB gap-analysis admin@eventmarketdb.com"
RATE_LIMIT_DELAY = 0.12  # ~8 req/sec (conservative under 10/sec limit)

# Form types we track (from config/feature_flags.py VALID_FORM_TYPES)
VALID_FORM_TYPES = {
    '8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A',
    'SCHEDULE 13D', 'SCHEDULE 13D/A', 'SC TO-I', '425', 'SC 14D9', '6-K'
}

# Focus on the most important types for gap analysis
PRIMARY_FORM_TYPES = {'8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A'}

OUTPUT_DIR = Path("earnings-analysis/gap_analysis")
PROGRESS_FILE = OUTPUT_DIR / "progress.json"


def get_neo4j_companies(driver):
    """Get all companies with CIKs from Neo4j."""
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Company) WHERE c.cik IS NOT NULL "
            "RETURN c.ticker AS ticker, c.cik AS cik "
            "ORDER BY c.ticker"
        )
        companies = [{"ticker": r["ticker"], "cik": r["cik"]} for r in result]
    print(f"Found {len(companies)} companies with CIKs in Neo4j")
    return companies


def get_neo4j_accessions(driver, start_date, end_date):
    """Get all report accession numbers from Neo4j in date range."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (r:Report)
            WHERE r.created >= $start AND r.created < $end_plus
            RETURN r.accessionNo AS accession, r.formType AS formType,
                   r.cik AS cik, substring(r.created, 0, 10) AS filedDate,
                   r.symbols AS symbols
            """,
            start=start_date,
            end_plus=end_date + "T23:59:59"
        )
        reports = {}
        for r in result:
            acc = r["accession"]
            if acc:
                # Normalize accession number (remove dashes for comparison)
                acc_clean = acc.replace("-", "")
                reports[acc_clean] = {
                    "accession": acc,
                    "formType": r["formType"],
                    "cik": r["cik"],
                    "filedDate": r["filedDate"],
                    "symbols": r["symbols"]
                }
    print(f"Found {len(reports)} reports in Neo4j ({start_date} to {end_date})")
    return reports


def fetch_edgar_submissions(cik, session):
    """Fetch all submissions for a CIK from SEC EDGAR."""
    # Pad CIK to 10 digits
    cik_padded = cik.lstrip("0").zfill(10)
    url = f"{EDGAR_BASE}/CIK{cik_padded}.json"

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 404:
            return None, f"CIK {cik_padded} not found on EDGAR"
        resp.raise_for_status()
        data = resp.json()
        return data, None
    except Exception as e:
        return None, str(e)


def extract_filings(data, start_date, end_date, form_types):
    """Extract filings from EDGAR submissions JSON, filtered by date and form type."""
    filings = []
    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)

    def process_filing_set(recent):
        """Process a set of filings (recent or from additional files)."""
        if not recent or "accessionNumber" not in recent:
            return

        for i in range(len(recent["accessionNumber"])):
            form = recent["form"][i] if i < len(recent["form"]) else ""
            filing_date_str = recent["filingDate"][i] if i < len(recent["filingDate"]) else ""

            if form not in form_types:
                continue

            try:
                filing_dt = date.fromisoformat(filing_date_str)
            except (ValueError, TypeError):
                continue

            if filing_dt < start_dt or filing_dt > end_dt:
                continue

            acc = recent["accessionNumber"][i]
            filings.append({
                "accession": acc,
                "accession_clean": acc.replace("-", ""),
                "form": form,
                "filingDate": filing_date_str,
                "primaryDocument": recent.get("primaryDocument", [""])[i] if i < len(recent.get("primaryDocument", [])) else "",
            })

    # Process recent filings
    process_filing_set(data.get("filings", {}).get("recent", {}))

    # Process additional filing files (for companies with long histories)
    additional_files = data.get("filings", {}).get("files", [])
    return filings, additional_files


def fetch_additional_filings(cik, files, session, start_date, end_date, form_types):
    """Fetch older filings from additional submission files."""
    cik_padded = cik.lstrip("0").zfill(10)
    all_filings = []

    for file_info in files:
        name = file_info.get("name", "")
        if not name:
            continue

        url = f"{EDGAR_BASE}/{name}"
        time.sleep(RATE_LIMIT_DELAY)

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            start_dt = date.fromisoformat(start_date)
            end_dt = date.fromisoformat(end_date)

            if "accessionNumber" not in data:
                continue

            for i in range(len(data["accessionNumber"])):
                form = data["form"][i] if i < len(data["form"]) else ""
                filing_date_str = data["filingDate"][i] if i < len(data["filingDate"]) else ""

                if form not in form_types:
                    continue

                try:
                    filing_dt = date.fromisoformat(filing_date_str)
                except (ValueError, TypeError):
                    continue

                if filing_dt < start_dt or filing_dt > end_dt:
                    continue

                acc = data["accessionNumber"][i]
                all_filings.append({
                    "accession": acc,
                    "accession_clean": acc.replace("-", ""),
                    "form": form,
                    "filingDate": filing_date_str,
                })

            # Check if oldest filing in this file is before our start date
            # If so, no need to fetch more files
            if data.get("filingDate"):
                oldest = data["filingDate"][-1]
                try:
                    if date.fromisoformat(oldest) < start_dt:
                        break
                except (ValueError, TypeError):
                    pass

        except Exception as e:
            print(f"  Warning: Failed to fetch {name}: {e}")

    return all_filings


def load_progress():
    """Load progress from previous run."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_ciks": [], "started_at": datetime.now().isoformat()}


def save_progress(progress):
    """Save progress for resume capability."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def main():
    parser = argparse.ArgumentParser(description="SEC Report Gap Analysis")
    parser.add_argument("--start-date", default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2026-03-28", help="End date (YYYY-MM-DD)")
    parser.add_argument("--resume", action="store_true", help="Resume from last progress")
    parser.add_argument("--primary-only", action="store_true", default=True,
                        help="Only check primary form types (8-K, 10-K, 10-Q + amendments)")
    parser.add_argument("--ticker", help="Analyze single ticker (for debugging)")
    args = parser.parse_args()

    form_types = PRIMARY_FORM_TYPES if args.primary_only else VALID_FORM_TYPES

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Step 1: Get companies
    companies = get_neo4j_companies(driver)
    if args.ticker:
        companies = [c for c in companies if c["ticker"] == args.ticker.upper()]
        if not companies:
            print(f"Ticker {args.ticker} not found")
            return

    # Step 2: Get all Neo4j accession numbers
    print(f"Fetching Neo4j reports ({args.start_date} to {args.end_date})...")
    neo4j_accessions = get_neo4j_accessions(driver, args.start_date, args.end_date)
    driver.close()

    # Step 3: Load progress for resume
    progress = load_progress() if args.resume else {"completed_ciks": [], "started_at": datetime.now().isoformat()}

    # Step 4: Set up HTTP session for EDGAR
    http_session = requests.Session()
    http_session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    })

    # Step 5: Output files
    gaps_file = OUTPUT_DIR / f"gaps_{args.start_date}_to_{args.end_date}.csv"
    summary_file = OUTPUT_DIR / f"summary_{args.start_date}_to_{args.end_date}.csv"
    all_edgar_file = OUTPUT_DIR / f"edgar_filings_{args.start_date}_to_{args.end_date}.csv"

    gaps_writer = None
    gaps_fh = None
    all_edgar_writer = None
    all_edgar_fh = None

    # Open output files
    gaps_fh = open(gaps_file, "w", newline="")
    gaps_writer = csv.writer(gaps_fh)
    gaps_writer.writerow(["ticker", "cik", "accession", "formType", "filingDate", "status"])

    all_edgar_fh = open(all_edgar_file, "w", newline="")
    all_edgar_writer = csv.writer(all_edgar_fh)
    all_edgar_writer.writerow(["ticker", "cik", "accession", "formType", "filingDate", "in_neo4j"])

    # Stats
    total_edgar = 0
    total_missing = 0
    total_matched = 0
    company_gaps = {}
    monthly_gaps = {}
    errors = []

    try:
        for idx, company in enumerate(companies):
            ticker = company["ticker"]
            cik = company["cik"]

            # Skip if already done (resume mode)
            if cik in progress["completed_ciks"]:
                continue

            if (idx + 1) % 50 == 0 or idx == 0:
                print(f"\n[{idx+1}/{len(companies)}] Processing... "
                      f"(EDGAR: {total_edgar}, Missing: {total_missing}, Matched: {total_matched})")

            time.sleep(RATE_LIMIT_DELAY)

            # Fetch from EDGAR
            data, error = fetch_edgar_submissions(cik, http_session)
            if error:
                errors.append({"ticker": ticker, "cik": cik, "error": error})
                if "not found" not in error.lower():
                    print(f"  ERROR {ticker} ({cik}): {error}")
                progress["completed_ciks"].append(cik)
                continue

            # Extract filings in date range
            filings, additional_files = extract_filings(
                data, args.start_date, args.end_date, form_types
            )

            # Fetch additional filing history if needed
            if additional_files:
                older = fetch_additional_filings(
                    cik, additional_files, http_session,
                    args.start_date, args.end_date, form_types
                )
                filings.extend(older)

            # Compare against Neo4j
            company_missing = 0
            company_matched = 0

            for filing in filings:
                acc_clean = filing["accession_clean"]
                in_neo4j = acc_clean in neo4j_accessions

                # Write to all-filings CSV
                all_edgar_writer.writerow([
                    ticker, cik, filing["accession"], filing["form"],
                    filing["filingDate"], "YES" if in_neo4j else "NO"
                ])

                if in_neo4j:
                    company_matched += 1
                    total_matched += 1
                else:
                    company_missing += 1
                    total_missing += 1

                    # Write gap
                    gaps_writer.writerow([
                        ticker, cik, filing["accession"], filing["form"],
                        filing["filingDate"], "MISSING"
                    ])

                    # Track monthly gaps
                    month_key = filing["filingDate"][:7]  # YYYY-MM
                    if month_key not in monthly_gaps:
                        monthly_gaps[month_key] = {"8-K": 0, "10-Q": 0, "10-K": 0, "other": 0, "total": 0}
                    form_bucket = filing["form"] if filing["form"] in ["8-K", "10-Q", "10-K"] else "other"
                    monthly_gaps[month_key][form_bucket] += 1
                    monthly_gaps[month_key]["total"] += 1

                total_edgar += 1

            if company_missing > 0:
                company_gaps[ticker] = {
                    "cik": cik,
                    "missing": company_missing,
                    "matched": company_matched,
                    "total_edgar": company_missing + company_matched,
                    "pct_missing": round(100 * company_missing / (company_missing + company_matched), 1) if (company_missing + company_matched) > 0 else 0
                }

            progress["completed_ciks"].append(cik)

            # Save progress every 50 companies
            if (idx + 1) % 50 == 0:
                save_progress(progress)
                gaps_fh.flush()
                all_edgar_fh.flush()

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
        save_progress(progress)

    finally:
        gaps_fh.close()
        all_edgar_fh.close()

    # Write summary
    with open(summary_file, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["=== GAP ANALYSIS SUMMARY ==="])
        writer.writerow(["Date Range", f"{args.start_date} to {args.end_date}"])
        writer.writerow(["Companies Analyzed", len(progress["completed_ciks"])])
        writer.writerow(["Total EDGAR Filings", total_edgar])
        writer.writerow(["Matched in Neo4j", total_matched])
        writer.writerow(["MISSING from Neo4j", total_missing])
        writer.writerow(["Match Rate", f"{round(100 * total_matched / total_edgar, 1)}%" if total_edgar > 0 else "N/A"])
        writer.writerow([])

        writer.writerow(["=== MONTHLY GAPS ==="])
        writer.writerow(["Month", "8-K", "10-Q", "10-K", "Other", "Total Missing"])
        for month in sorted(monthly_gaps.keys()):
            g = monthly_gaps[month]
            writer.writerow([month, g["8-K"], g["10-Q"], g["10-K"], g["other"], g["total"]])
        writer.writerow([])

        writer.writerow(["=== TOP COMPANIES WITH GAPS ==="])
        writer.writerow(["Ticker", "CIK", "Missing", "Matched", "Total EDGAR", "% Missing"])
        for ticker in sorted(company_gaps.keys(), key=lambda t: company_gaps[t]["missing"], reverse=True)[:50]:
            g = company_gaps[ticker]
            writer.writerow([ticker, g["cik"], g["missing"], g["matched"], g["total_edgar"], g["pct_missing"]])

        if errors:
            writer.writerow([])
            writer.writerow(["=== ERRORS ==="])
            writer.writerow(["Ticker", "CIK", "Error"])
            for e in errors:
                writer.writerow([e["ticker"], e["cik"], e["error"]])

    # Print summary to console
    print(f"\n{'='*60}")
    print(f"GAP ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Companies analyzed: {len(progress['completed_ciks'])}")
    print(f"Total EDGAR filings: {total_edgar}")
    print(f"Matched in Neo4j:   {total_matched}")
    print(f"MISSING from Neo4j: {total_missing}")
    if total_edgar > 0:
        print(f"Match rate:         {round(100 * total_matched / total_edgar, 1)}%")
    print(f"\nMonthly gaps:")
    for month in sorted(monthly_gaps.keys()):
        g = monthly_gaps[month]
        print(f"  {month}: {g['total']:4d} missing (8-K:{g['8-K']:3d} 10-Q:{g['10-Q']:3d} 10-K:{g['10-K']:3d})")
    print(f"\nTop 10 companies with most gaps:")
    for ticker in sorted(company_gaps.keys(), key=lambda t: company_gaps[t]["missing"], reverse=True)[:10]:
        g = company_gaps[ticker]
        print(f"  {ticker:6s}: {g['missing']:4d} missing / {g['total_edgar']:4d} total ({g['pct_missing']}%)")
    print(f"\nOutput files:")
    print(f"  Gaps:    {gaps_file}")
    print(f"  Summary: {summary_file}")
    print(f"  All:     {all_edgar_file}")


if __name__ == "__main__":
    main()
