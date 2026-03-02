#!/usr/bin/env python3
"""Trigger guidance extraction for unprocessed transcripts.

Queries Neo4j Transcript.guidance_status to find transcripts not yet processed,
then pushes batched-per-company payloads to the earnings:trigger Redis queue.
KEDA scales claude-code-worker pods automatically.

Usage:
  python3 scripts/trigger-guidance.py CRM              # All unprocessed for CRM
  python3 scripts/trigger-guidance.py ADBE MSFT CRM    # Multiple tickers (parallel pods)
  python3 scripts/trigger-guidance.py --all             # All unprocessed transcripts
  python3 scripts/trigger-guidance.py --list CRM        # Show unprocessed, don't queue
  python3 scripts/trigger-guidance.py --list --all      # Show all unprocessed
  python3 scripts/trigger-guidance.py --mode dry_run CRM  # Queue with dry_run mode
  python3 scripts/trigger-guidance.py --source-id CRM_2025-09-03T17.00.00-04.00
  python3 scripts/trigger-guidance.py --force CRM       # Re-process even if completed
  python3 scripts/trigger-guidance.py --retry-failed CRM  # Re-process only failed items
"""

import argparse
from collections import defaultdict
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logging.getLogger("neo4j").setLevel(logging.ERROR)

import redis
from neograph.Neo4jConnection import get_manager

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))
QUEUE_NAME = "earnings:trigger"


def find_unprocessed(mgr, tickers=None, source_id=None, force=False, retry_failed=False):
    """Query Neo4j for transcripts needing processing, based on guidance_status property.

    guidance_status IS NULL = not yet processed.
    """

    if source_id:
        # Single transcript lookup
        rows = mgr.execute_cypher_query_all(
            "MATCH (t:Transcript {id: $sid}) "
            "RETURN t.id AS id, t.symbol AS symbol, "
            "       t.fiscal_year AS fy, t.fiscal_quarter AS fq, "
            "       t.guidance_status AS status",
            {"sid": source_id},
        )
        if not rows:
            print(f"Transcript not found: {source_id}", file=sys.stderr)
            return []
        row = rows[0]
        if row["status"] == "completed" and not force:
            print(f"Already processed: {source_id}")
            print("Use --force to re-process.")
            return []
        if row["status"] == "in_progress" and not force:
            print(f"Currently in progress: {source_id}")
            print("Use --force to re-trigger.")
            return []
        return [{"id": row["id"], "symbol": row["symbol"],
                 "fy": row["fy"], "fq": row["fq"]}]

    # Bulk query — direct property check on Transcript node
    ticker_filter = "WHERE t.symbol IN $tickers " if tickers else ""
    params = {}
    if tickers:
        params["tickers"] = tickers

    if force:
        query = (
            f"MATCH (t:Transcript) {ticker_filter}"
            "RETURN t.id AS id, t.symbol AS symbol, "
            "       t.fiscal_year AS fy, t.fiscal_quarter AS fq "
            "ORDER BY t.symbol, t.id"
        )
    elif retry_failed:
        failed_filter = "WHERE t.guidance_status = 'failed' " if not tickers else "AND t.guidance_status = 'failed' "
        query = (
            f"MATCH (t:Transcript) {ticker_filter}{failed_filter}"
            "RETURN t.id AS id, t.symbol AS symbol, "
            "       t.fiscal_year AS fy, t.fiscal_quarter AS fq "
            "ORDER BY t.symbol, t.id"
        )
    else:
        # Default: not yet processed or failed
        status_filter = "AND (" if tickers else "WHERE ("
        status_filter += (
            "t.guidance_status IS NULL "
            "OR t.guidance_status = 'failed'"
            ")"
        )
        query = (
            f"MATCH (t:Transcript) {ticker_filter}{status_filter} "
            "RETURN t.id AS id, t.symbol AS symbol, "
            "       t.fiscal_year AS fy, t.fiscal_quarter AS fq "
            "ORDER BY t.symbol, t.id"
        )
    return mgr.execute_cypher_query_all(query, params)


def push_to_queue(transcripts, mode="write"):
    """Bundle transcripts per company, push one queue item per company."""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.ping()

    # Group by ticker
    by_ticker = defaultdict(list)
    for t in transcripts:
        ticker = t["symbol"] or t["id"].split("_")[0]
        by_ticker[ticker].append(t["id"])

    pushed = 0
    for ticker, source_ids in sorted(by_ticker.items()):
        payload = json.dumps({
            "ticker": ticker,
            "source_ids": source_ids,
            "mode": mode,
        })
        r.lpush(QUEUE_NAME, payload)
        pushed += 1

    r.close()
    return pushed, dict(by_ticker)


def main():
    parser = argparse.ArgumentParser(
        description="Trigger guidance extraction for unprocessed transcripts")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols (e.g., CRM ADBE)")
    parser.add_argument("--all", action="store_true", help="All unprocessed transcripts")
    parser.add_argument("--list", action="store_true", help="List only, don't queue")
    parser.add_argument("--mode", default="write", choices=["write", "dry_run"],
                        help="Processing mode (default: write)")
    parser.add_argument("--source-id", help="Specific transcript ID")
    parser.add_argument("--force", action="store_true",
                        help="Re-process even if already completed")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Re-process only failed items")
    args = parser.parse_args()

    if not args.tickers and not args.all and not args.source_id:
        parser.print_help()
        sys.exit(1)

    mgr = get_manager()

    transcripts = find_unprocessed(
        mgr,
        tickers=[t.upper() for t in args.tickers] if args.tickers else None,
        source_id=args.source_id,
        force=args.force,
        retry_failed=args.retry_failed,
    )
    mgr.close()

    if not transcripts:
        print("No transcripts to process.")
        return

    # Display
    print(f"\nTranscripts to process: {len(transcripts)}")
    print(f"{'ID':<50} {'Symbol':<8} {'FY':<6} {'FQ':<4}")
    print("-" * 70)
    for t in transcripts:
        print(f"{t['id']:<50} {t['symbol'] or '?':<8} {t['fy'] or '?':<6} {t['fq'] or '?':<4}")

    if args.list:
        return

    # Push to queue (bundled per company)
    pushed, by_ticker = push_to_queue(transcripts, mode=args.mode)
    print(f"\nQueued {pushed} company batches (mode={args.mode}):")
    for ticker, sids in sorted(by_ticker.items()):
        print(f"  {ticker}: {len(sids)} transcript(s)")
    print(f"\nWatch progress: kubectl logs -f -l app=claude-code-worker -n processing")


if __name__ == "__main__":
    main()
