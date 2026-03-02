#!/usr/bin/env python3
"""Trigger guidance extraction for unprocessed transcripts.

Queries Neo4j for transcripts without GuidanceUpdate nodes and pushes
them to the earnings:trigger Redis queue for processing by claude-code-worker.

Usage:
  ./scripts/trigger-guidance.py CRM              # All unprocessed for CRM
  ./scripts/trigger-guidance.py ADBE MSFT CRM    # Multiple tickers
  ./scripts/trigger-guidance.py --all             # All unprocessed transcripts
  ./scripts/trigger-guidance.py --list CRM        # Show unprocessed, don't queue
  ./scripts/trigger-guidance.py --list --all      # Show all unprocessed
  ./scripts/trigger-guidance.py --mode dry_run CRM  # Queue with dry_run mode
  ./scripts/trigger-guidance.py --source-id CRM_2025-09-03T17.00.00-04.00  # Specific transcript
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Suppress Neo4j driver warnings (aggregation null warnings)
logging.getLogger("neo4j").setLevel(logging.ERROR)

import redis
from neograph.Neo4jConnection import get_manager


# Connection defaults — reads from env (matches .bashrc exports)
REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))
QUEUE_NAME = "earnings:trigger"


def find_unprocessed(mgr, tickers=None, source_id=None):
    """Query Neo4j for transcripts without GuidanceUpdate nodes."""
    if source_id:
        rows = mgr.execute_cypher_query_all(
            "MATCH (t:Transcript {id: $sid}) "
            "OPTIONAL MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t) "
            "RETURN t.id AS id, t.symbol AS symbol, "
            "       t.fiscal_year AS fy, t.fiscal_quarter AS fq, "
            "       count(gu) AS guidance_count",
            {"sid": source_id},
        )
        if not rows:
            print(f"Transcript not found: {source_id}", file=sys.stderr)
            return []
        if rows[0]["guidance_count"] > 0:
            print(f"Already processed ({rows[0]['guidance_count']} items): {source_id}")
            return []
        return [{"id": rows[0]["id"], "symbol": rows[0]["symbol"],
                 "fy": rows[0]["fy"], "fq": rows[0]["fq"]}]

    if tickers:
        where = "WHERE t.symbol IN $tickers"
        params = {"tickers": tickers}
    else:
        where = ""
        params = {}

    query = (
        f"MATCH (t:Transcript) {where} "
        "OPTIONAL MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t) "
        "WITH t, count(gu) AS gc "
        "WHERE gc = 0 "
        "RETURN t.id AS id, t.symbol AS symbol, "
        "       t.fiscal_year AS fy, t.fiscal_quarter AS fq "
        "ORDER BY t.symbol, t.id"
    )
    return mgr.execute_cypher_query_all(query, params)


def push_to_queue(transcripts, mode="write"):
    """Push transcript IDs to Redis earnings:trigger queue."""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.ping()

    pushed = 0
    for t in transcripts:
        ticker = t["symbol"] or t["id"].split("_")[0]
        payload = json.dumps({
            "ticker": ticker,
            "source_id": t["id"],
            "mode": mode,
        })
        r.lpush(QUEUE_NAME, payload)
        pushed += 1

    r.close()
    return pushed


def main():
    parser = argparse.ArgumentParser(description="Trigger guidance extraction")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols (e.g., CRM ADBE)")
    parser.add_argument("--all", action="store_true", help="All unprocessed transcripts")
    parser.add_argument("--list", action="store_true", help="List only, don't queue")
    parser.add_argument("--mode", default="write", choices=["write", "dry_run"],
                        help="Processing mode (default: write)")
    parser.add_argument("--source-id", help="Specific transcript ID")
    args = parser.parse_args()

    if not args.tickers and not args.all and not args.source_id:
        parser.print_help()
        sys.exit(1)

    mgr = get_manager()

    # Find unprocessed transcripts
    transcripts = find_unprocessed(
        mgr,
        tickers=[t.upper() for t in args.tickers] if args.tickers else None,
        source_id=args.source_id,
    )
    mgr.close()

    if not transcripts:
        print("No unprocessed transcripts found.")
        return

    # Display
    print(f"\nUnprocessed transcripts: {len(transcripts)}")
    print(f"{'ID':<50} {'Symbol':<8} {'FY':<6} {'FQ':<4}")
    print("-" * 70)
    for t in transcripts:
        print(f"{t['id']:<50} {t['symbol'] or '?':<8} {t['fy'] or '?':<6} {t['fq'] or '?':<4}")

    if args.list:
        return

    # Push to queue
    print(f"\nPushing {len(transcripts)} items to {QUEUE_NAME} (mode={args.mode})...")
    pushed = push_to_queue(transcripts, mode=args.mode)
    print(f"Queued {pushed} items. KEDA will scale pods automatically.")
    print(f"\nWatch progress: kubectl logs -f -l app=claude-code-worker -n processing")


if __name__ == "__main__":
    main()
