#!/usr/bin/env python3
"""
Guidance Trigger Daemon
========================
Reads trade_ready:entries from Redis, finds unprocessed data assets in Neo4j,
and pushes extraction jobs to extract:pipeline. Runs as an always-on K8s Deployment.

Handles both historical backfill (first sweep after ticker enters TradeReady)
and real-time detection (subsequent sweeps catch newly ingested assets).

Usage:
  python3 scripts/guidance_trigger_daemon.py              # Run daemon (60s loop)
  python3 scripts/guidance_trigger_daemon.py --list        # Dry run: show what would be queued
  python3 scripts/guidance_trigger_daemon.py --once        # Single sweep, then exit
  python3 scripts/guidance_trigger_daemon.py --ticker LULU # Scope to specific ticker(s)
"""
import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# ── Redis env must be captured BEFORE load_dotenv overrides them ──
REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))

# Now load .env for Neo4j credentials (override=True so .env wins for Neo4j)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("neo4j").setLevel(logging.ERROR)
log = logging.getLogger("guidance_trigger")

# ── Configuration ──

POLL_INTERVAL = 60           # seconds between sweeps
LEASE_TTL = 14400            # 4-hour enqueue lease (covers backfill burst + extraction)
ACTIVE_WINDOW_DAYS = int(os.environ.get("ACTIVE_WINDOW_DAYS", "1"))  # 1=upcoming only, 45=backfill
QUEUE_NAME = "extract:pipeline"
EXTRACTION_TYPE = "guidance"

ASSET_CONFIGS = {
    "transcript": {"label": "Transcript", "alias": "t", "extra_where": None,
                   "company_join": None, "item_filter": None},
    "8k":         {"label": "Report", "alias": "r", "extra_where": "r.formType = '8-K'",
                   "company_join": ("PRIMARY_FILER", "out"),
                   "item_filter": ["Item 2.02", "Item 7.01", "Item 8.01"]},
    "10q":        {"label": "Report", "alias": "r", "extra_where": "r.formType = '10-Q'",
                   "company_join": ("PRIMARY_FILER", "out"), "item_filter": None},
    "10k":        {"label": "Report", "alias": "r", "extra_where": "r.formType = '10-K'",
                   "company_join": ("PRIMARY_FILER", "out"), "item_filter": None},
}

# Future route table (only guidance enabled now)
ROUTES = [
    {"name": "guidance", "queue": QUEUE_NAME, "status_prop": "guidance_status",
     "assets": ASSET_CONFIGS},
]

# ── Graceful shutdown ──

_shutdown = False

def _handle_signal(signum, _frame):
    global _shutdown
    log.info("Received signal %s — shutting down after current sweep", signum)
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── Core functions ──

def get_redis():
    import redis as redis_lib
    return redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_active_tickers(r, override_tickers=None):
    """Read trade_ready:entries, filter to active window. Returns dict of ticker → earnings_date."""
    if override_tickers:
        today_str = date.today().isoformat()
        return {t.upper(): today_str for t in override_tickers}

    cutoff = (date.today() - timedelta(days=ACTIVE_WINDOW_DAYS)).isoformat()
    all_entries = r.hgetall("trade_ready:entries")
    active = {}
    for ticker, raw in all_entries.items():
        try:
            entry = json.loads(raw)
            ed = entry.get("earnings_date", "")
            if ed >= cutoff:
                active[ticker.upper()] = ed
        except (json.JSONDecodeError, TypeError):
            continue
    return active


def _company_join_clause(alias, company_join):
    """Build MATCH clause to reach Company node. Reuses trigger-extract.py pattern."""
    if company_join is None:
        return "", f"{alias}.symbol"
    rel, direction = company_join
    if direction == "out":
        match = f"MATCH ({alias})-[:{rel}]->(c:Company)"
    else:
        match = f"MATCH (c:Company)-[:{rel}]->({alias})"
    return match, "c.ticker"


def find_eligible(mgr, asset_name, asset_cfg, tickers, status_prop):
    """ONE batched Cypher query per asset. Returns [{id, symbol, status}]."""
    label = asset_cfg["label"]
    alias = asset_cfg["alias"]
    extra_where = asset_cfg["extra_where"]
    company_join = asset_cfg["company_join"]
    item_filter = asset_cfg["item_filter"]

    join_clause, ticker_expr = _company_join_clause(alias, company_join)

    where_clauses = []
    params = {"tickers": list(tickers)}

    # Ticker filter
    if company_join is None:
        where_clauses.append(f"{alias}.symbol IN $tickers")
    else:
        where_clauses.append("c.ticker IN $tickers")

    # Form type filter
    if extra_where:
        where_clauses.append(extra_where)

    # 8-K item filter
    if item_filter:
        item_conditions = " OR ".join(
            f"{alias}.items CONTAINS '{code}'" for code in item_filter
        )
        where_clauses.append(f"({item_conditions})")

    # Status filter: IS NULL OR in_progress (not failed)
    where_clauses.append(
        f"({alias}.{status_prop} IS NULL OR {alias}.{status_prop} = 'in_progress')"
    )

    where_str = "WHERE " + " AND ".join(where_clauses)
    query = (
        f"MATCH ({alias}:{label}) {join_clause} {where_str} "
        f"RETURN {alias}.id AS id, {ticker_expr} AS symbol, "
        f"{alias}.{status_prop} AS status "
        f"ORDER BY {ticker_expr}, {alias}.id"
    )

    try:
        return mgr.execute_cypher_query_all(query, params)
    except Exception as e:
        log.error(f"Neo4j query failed for {asset_name}: {e}")
        return []


def enqueue_with_lease(r, source_id, asset, ticker, status, queue, dry_run=False):
    """Atomic lease-based dedup + LPUSH. Returns True if enqueued."""
    lease_key = f"guidance_lease:{asset}:{source_id}"

    if status is None:  # NULL in Neo4j → None in Python
        # Normal path: acquire lease, then push
        if dry_run:
            return not r.exists(lease_key)  # Faithful: check lease even in dry-run
        acquired = r.set(lease_key, "1", ex=LEASE_TTL, nx=True)
        if not acquired:
            return False  # Lease exists → already queued
    else:
        # in_progress: stale recovery — only re-enqueue if lease is ABSENT
        if r.exists(lease_key):
            return False  # Lease exists → worker is active or recently queued
        if dry_run:
            return True
        # Stale: atomic SET NX to prevent duplicate re-enqueue during rolling updates
        acquired = r.set(lease_key, "1", ex=LEASE_TTL, nx=True)
        if not acquired:
            return False  # Another pod beat us

    payload = json.dumps({
        "asset": asset,
        "ticker": ticker,
        "source_id": source_id,
        "type": EXTRACTION_TYPE,
        "mode": "write",
    })
    r.lpush(queue, payload)
    return True


def sweep_once(r, mgr, tickers, route, dry_run=False):
    """One full sweep: query all 4 assets, sort by earnings date (nearest first), enqueue. Returns count."""
    queue = route["queue"]
    status_prop = route["status_prop"]
    assets = route["assets"]

    # Collect all eligible items across all assets
    to_enqueue = []
    for asset_name, asset_cfg in assets.items():
        for item in find_eligible(mgr, asset_name, asset_cfg, tickers, status_prop):
            to_enqueue.append((item, asset_name))

    if not to_enqueue:
        return 0

    # Sort by earnings_date — nearest first gets LPUSH'd first = BRPOP'd first (FIFO)
    to_enqueue.sort(key=lambda x: tickers.get(
        x[0]["symbol"] or x[0]["id"].split("_")[0], "9999-12-31"))

    # Enqueue in priority order, track per-asset stats
    total = 0
    stats = {}  # asset_name → [queued, skipped, stale]
    for item, asset_name in to_enqueue:
        sid = item["id"]
        sym = item["symbol"] or sid.split("_")[0]
        st = item["status"]

        enqueued = enqueue_with_lease(r, sid, asset_name, sym, st, queue, dry_run)
        s = stats.setdefault(asset_name, [0, 0, 0])
        if enqueued:
            s[0] += 1
            if st == "in_progress":
                s[2] += 1
            total += 1
        else:
            s[1] += 1

    # Log per-asset stats (same format as before)
    for asset_name in assets:
        s = stats.get(asset_name)
        if s and (s[0] > 0 or s[1] > 0):
            stale_str = f" ({s[2]} stale recovery)" if s[2] else ""
            action = "would queue" if dry_run else "queued"
            log.info(f"  [{asset_name}] {action}: {s[0]}{stale_str}, skipped (lease active): {s[1]}")

    return total


def main():
    parser = argparse.ArgumentParser(description="Guidance Trigger Daemon")
    parser.add_argument("--list", action="store_true", help="Dry run: show what would be queued")
    parser.add_argument("--once", action="store_true", help="Single sweep, then exit")
    parser.add_argument("--ticker", nargs="+", help="Scope to specific ticker(s)")
    args = parser.parse_args()

    dry_run = args.list

    # Connect
    r = get_redis()
    try:
        r.ping()
        log.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        log.error(f"Redis connection failed: {e}")
        sys.exit(1)

    from neograph.Neo4jConnection import get_manager
    mgr = get_manager()
    log.info("Neo4j connected")

    if args.once or dry_run:
        # Single sweep
        tickers = get_active_tickers(r, args.ticker)
        if not tickers:
            log.info("No active tickers")
            return
        log.info(f"Active tickers ({len(tickers)}): {sorted(tickers)}")
        for route in ROUTES:
            total = sweep_once(r, mgr, tickers, route, dry_run=dry_run)
            action = "Would queue" if dry_run else "Queued"
            log.info(f"[{route['name']}] {action} {total} total items")
        mgr.close()
        return

    # Daemon loop
    log.info(f"Starting daemon: poll={POLL_INTERVAL}s, lease={LEASE_TTL}s, window={ACTIVE_WINDOW_DAYS}d")
    log.info(f"Queue: {QUEUE_NAME}, routes: {[r['name'] for r in ROUTES]}")

    while not _shutdown:
        try:
            tickers = get_active_tickers(r, args.ticker)
            if tickers:
                for route in ROUTES:
                    total = sweep_once(r, mgr, tickers, route)
                    if total > 0:
                        log.info(f"[{route['name']}] Queued {total} items for {len(tickers)} active tickers")
            else:
                log.debug("No active tickers in window")
        except Exception as e:
            log.error(f"Sweep failed: {e}")

        # Sleep in small increments for responsive shutdown
        for _ in range(POLL_INTERVAL):
            if _shutdown:
                break
            time.sleep(1)

    log.info("Shutdown complete")
    mgr.close()


if __name__ == "__main__":
    main()
