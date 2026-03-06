#!/usr/bin/env python3
"""Trigger extraction pipeline for unprocessed data assets.

Queries Neo4j to find assets not yet processed for a given extraction type,
then pushes one message per (type, asset, source_id) to the extract:pipeline
Redis queue. KEDA scales claude-code-worker pods automatically.

Usage:
  python3 scripts/trigger-extract.py CRM                        # guidance/transcript for CRM
  python3 scripts/trigger-extract.py ADBE MSFT CRM              # Multiple tickers
  python3 scripts/trigger-extract.py --all                       # All unprocessed
  python3 scripts/trigger-extract.py --list CRM                  # Show unprocessed, don't queue
  python3 scripts/trigger-extract.py --list --all                # Show all unprocessed
  python3 scripts/trigger-extract.py --mode dry_run CRM          # Queue with dry_run mode
  python3 scripts/trigger-extract.py --source-id CRM_2025-09-03T17.00
  python3 scripts/trigger-extract.py --force CRM                 # Re-process even if completed
  python3 scripts/trigger-extract.py --retry-failed CRM          # Re-process only failed items
  python3 scripts/trigger-extract.py --type guidance --asset 8k CRM   # guidance extraction on 8-K filings
  python3 scripts/trigger-extract.py --type all --asset all --all     # All types x all assets
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import logging
logging.getLogger("neo4j").setLevel(logging.ERROR)

import redis
from neograph.Neo4jConnection import get_manager

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))
QUEUE_NAME = "extract:pipeline"

# --- Asset config: label, alias, extra WHERE, company join ---
# company_join: (relationship, direction) to reach Company node for ticker resolution.
# Transcript has .symbol directly; Report/News need a JOIN.
ASSET_QUERIES = {
    #              label         alias  extra_where                               company_join
    "transcript": ("Transcript", "t",   None,                                     None),
    "8k":         ("Report",     "r",   "r.formType = '8-K'",                     ("PRIMARY_FILER", "out")),
    "10q":        ("Report",     "r",   "r.formType IN ['10-Q', '10-K']",         ("PRIMARY_FILER", "out")),
    "news":       ("News",       "n",   None,                                     ("INFLUENCES", "out")),
}

# Only extraction types that are actually implemented.
# Defense-in-depth: reject anything not in this set before building queries.
ALLOWED_TYPES = {"guidance"}


def _company_join_clause(alias, company_join):
    """Build MATCH clause to reach Company node from asset node.

    Returns (match_fragment, ticker_expr) where ticker_expr is the Cypher
    expression that yields the ticker string for this asset row.
    Transcript has .symbol directly; Report/News need a relationship JOIN.
    """
    if company_join is None:
        # Asset node has .symbol directly (e.g., Transcript)
        return "", f"{alias}.symbol"

    rel, direction = company_join
    if direction == "out":
        match = f"MATCH ({alias})-[:{rel}]->(c:Company)"
    else:
        match = f"MATCH (c:Company)-[:{rel}]->({alias})"
    return match, "c.ticker"


def find_unprocessed(mgr, asset, extraction_type, tickers=None, source_id=None,
                     force=False, retry_failed=False):
    """Query Neo4j for assets needing processing, based on {type}_status property."""

    label, alias, extra_where, company_join = ASSET_QUERIES[asset]
    status_prop = f"{extraction_type}_status"
    join_clause, ticker_expr = _company_join_clause(alias, company_join)

    if source_id:
        # Single asset lookup
        query = (
            f"MATCH ({alias}:{label} {{id: $sid}}) {join_clause} "
            f"RETURN {alias}.id AS id, {ticker_expr} AS symbol, "
            f"       {alias}.{status_prop} AS status"
        )
        rows = mgr.execute_cypher_query_all(query, {"sid": source_id})
        if not rows:
            print(f"{label} not found: {source_id}", file=sys.stderr)
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
        return [{"id": row["id"], "symbol": row["symbol"]}]

    # --- Bulk query ---
    where_clauses = []
    params = {}

    if tickers:
        # Filter by ticker — use the correct expression for this asset type
        if company_join is None:
            where_clauses.append(f"{alias}.symbol IN $tickers")
        else:
            where_clauses.append("c.ticker IN $tickers")
        params["tickers"] = tickers

    if extra_where:
        where_clauses.append(extra_where)

    if force:
        pass  # no status filter — include everything
    elif retry_failed:
        where_clauses.append(f"{alias}.{status_prop} = 'failed'")
    else:
        # Default: not yet processed or failed
        where_clauses.append(
            f"({alias}.{status_prop} IS NULL OR {alias}.{status_prop} = 'failed')"
        )

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = (
        f"MATCH ({alias}:{label}) {join_clause} {where_str} "
        f"RETURN {alias}.id AS id, {ticker_expr} AS symbol "
        f"ORDER BY {ticker_expr}, {alias}.id"
    )
    return mgr.execute_cypher_query_all(query, params)


def push_to_queue(items, asset, extraction_type, mode="write"):
    """Push one queue message per source_id."""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.ping()

    pushed = 0
    for item in items:
        ticker = item["symbol"] or item["id"].split("_")[0]
        payload = json.dumps({
            "asset": asset,
            "ticker": ticker,
            "source_id": item["id"],
            "type": extraction_type,
            "mode": mode,
        })
        r.lpush(QUEUE_NAME, payload)
        pushed += 1

    r.close()
    return pushed


def resolve_types(type_arg):
    """Expand 'all' to every allowed type, or validate a single type."""
    if type_arg == "all":
        return sorted(ALLOWED_TYPES)
    if type_arg not in ALLOWED_TYPES:
        print(f"Error: type '{type_arg}' is not in ALLOWED_TYPES {ALLOWED_TYPES}",
              file=sys.stderr)
        sys.exit(1)
    return [type_arg]


def resolve_assets(asset_arg):
    """Expand 'all' to every known asset, or validate a single asset."""
    if asset_arg == "all":
        return sorted(ASSET_QUERIES.keys())
    if asset_arg not in ASSET_QUERIES:
        print(f"Error: asset '{asset_arg}' is not in ASSET_QUERIES {set(ASSET_QUERIES.keys())}",
              file=sys.stderr)
        sys.exit(1)
    return [asset_arg]


def main():
    parser = argparse.ArgumentParser(
        description="Trigger extraction pipeline for unprocessed data assets")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols (e.g., CRM ADBE)")
    parser.add_argument("--all", action="store_true", help="All unprocessed assets")
    parser.add_argument("--list", action="store_true", help="List only, don't queue")
    parser.add_argument("--mode", default="write", choices=["write", "dry_run"],
                        help="Processing mode (default: write)")
    parser.add_argument("--source-id", help="Specific asset ID")
    parser.add_argument("--force", action="store_true",
                        help="Re-process even if already completed")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Re-process only failed items")
    parser.add_argument("--type", default="guidance",
                        choices=sorted(ALLOWED_TYPES) + ["all"],
                        help="Extraction type (default: guidance)")
    parser.add_argument("--asset", default="transcript",
                        choices=sorted(ASSET_QUERIES.keys()) + ["all"],
                        help="Data asset to extract from (default: transcript)")
    args = parser.parse_args()

    if not args.tickers and not args.all and not args.source_id:
        parser.print_help()
        sys.exit(1)

    types = resolve_types(args.type)
    assets = resolve_assets(args.asset)

    mgr = get_manager()
    total_queued = 0

    for extraction_type in types:
        for asset in assets:
            items = find_unprocessed(
                mgr,
                asset=asset,
                extraction_type=extraction_type,
                tickers=[t.upper() for t in args.tickers] if args.tickers else None,
                source_id=args.source_id,
                force=args.force,
                retry_failed=args.retry_failed,
            )

            if not items:
                print(f"\n[{extraction_type}/{asset}] No items to process.")
                continue

            # Display
            print(f"\n[{extraction_type}/{asset}] Items to process: {len(items)}")
            print(f"  {'ID':<55} {'Symbol':<8}")
            print(f"  {'-' * 55} {'-' * 8}")
            for item in items:
                print(f"  {item['id']:<55} {item['symbol'] or '?':<8}")

            if args.list:
                continue

            # Push to queue — one message per source_id
            pushed = push_to_queue(items, asset, extraction_type, mode=args.mode)
            total_queued += pushed
            print(f"  Queued {pushed} message(s) (mode={args.mode})")

    mgr.close()

    if not args.list and total_queued > 0:
        print(f"\nTotal queued: {total_queued} message(s) -> {QUEUE_NAME}")
        print(f"Watch progress: kubectl logs -f -l app=claude-code-worker -n processing")


if __name__ == "__main__":
    main()
