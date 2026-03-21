#!/usr/bin/env python3
"""
Migrate Guidance Periods — Fix duplicate GuidancePeriod groups from FYE bug.

Dynamically discovers ALL tickers with duplicate GuidancePeriod groups
(multiple distinct period_u_ids for the same ticker/fiscal_year/fiscal_quarter),
then re-points GuidanceUpdate nodes to the correct SEC-exact period and rekeys
the guidance_update_id to match.

Prerequisites:
    1. Run sec_quarter_cache_loader.py first (SEC cache must be warm)
    2. Do NOT deploy new guidance_write_cli.py code until migration completes

Usage:
    python3 scripts/migrate_guidance_periods.py --dry-run  # preview changes
    python3 scripts/migrate_guidance_periods.py             # execute migration
"""
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".claude/skills/earnings-orchestrator/scripts"))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import redis
from neograph.Neo4jConnection import get_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("migrate_guidance_periods")

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.40.72")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "31379"))


def discover_affected_tickers(mgr):
    """Find tickers with duplicate duration quarter/annual GuidancePeriod groups.

    Restricts to standard duration guidance only — excludes instant, half,
    sentinel, long_range, monthly, and undefined period scopes which legitimately
    have different GuidancePeriod nodes for the same fiscal identity.
    """
    result = mgr.execute_cypher_query_all("""
        MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company)
        WHERE gu.fiscal_year IS NOT NULL
          AND gu.time_type = 'duration'
          AND (
            (gu.period_scope = 'quarter' AND gu.fiscal_quarter IS NOT NULL)
            OR
            (gu.period_scope = 'annual' AND gu.fiscal_quarter IS NULL)
          )
        MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
        WITH c.ticker AS ticker, gu.fiscal_year AS fy,
             gu.period_scope AS scope, gu.fiscal_quarter AS fq,
             collect(DISTINCT gp.u_id) AS period_ids
        WHERE size(period_ids) > 1
        RETURN DISTINCT ticker
        ORDER BY ticker
    """)
    return [row["ticker"] for row in result]


def get_duplicate_groups(mgr, ticker):
    """Get duplicate duration quarter/annual groups for a ticker."""
    result = mgr.execute_cypher_query_all("""
        MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
        WHERE gu.fiscal_year IS NOT NULL
          AND gu.time_type = 'duration'
          AND (
            (gu.period_scope = 'quarter' AND gu.fiscal_quarter IS NOT NULL)
            OR
            (gu.period_scope = 'annual' AND gu.fiscal_quarter IS NULL)
          )
        MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
        WITH gu.fiscal_year AS fy, gu.fiscal_quarter AS fq,
             gu.period_scope AS scope,
             collect(DISTINCT gp.u_id) AS period_ids,
             count(gu) AS update_count
        WHERE size(period_ids) > 1
        RETURN fy, fq, scope, period_ids, update_count
        ORDER BY fy, fq
    """, {"ticker": ticker})
    return result


def migrate_group(mgr, r, ticker, fy, fq, old_period_ids, dry_run):
    """Migrate one duplicate group to the correct SEC-exact period."""
    # Look up correct dates from SEC cache
    suffix = f"Q{fq}" if fq is not None else "FY"
    cache_key = f"fiscal_quarter:{ticker}:{fy}:{suffix}"
    cached = r.get(cache_key)
    if not cached:
        log.warning(f"  {ticker} FY{fy} {suffix}: no SEC cache — SKIPPING")
        return 0, 0

    dates = json.loads(cached)
    correct_period_id = f"gp_{dates['start']}_{dates['end']}"

    # Find duration quarter/annual GuidanceUpdate nodes on wrong periods.
    # Excludes instant, half, sentinel, long_range, monthly — those are legitimate.
    if fq is not None:
        updates = mgr.execute_cypher_query_all("""
            MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
            WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter = $fq
              AND gu.period_scope = 'quarter'
              AND gu.time_type = 'duration'
            MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
            WHERE gp.u_id <> $correct_pid
            RETURN gu.id AS gu_id, gp.u_id AS old_pid
        """, {"ticker": ticker, "fy": fy, "fq": fq, "correct_pid": correct_period_id})
    else:
        updates = mgr.execute_cypher_query_all("""
            MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
            WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter IS NULL
              AND gu.period_scope = 'annual'
              AND gu.time_type = 'duration'
            MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
            WHERE gp.u_id <> $correct_pid
            RETURN gu.id AS gu_id, gp.u_id AS old_pid
        """, {"ticker": ticker, "fy": fy, "correct_pid": correct_period_id})

    if not updates:
        return 0, 0

    migrated = 0
    collisions = 0
    for row in updates:
        old_gu_id = row["gu_id"]
        old_pid = row["old_pid"]

        # Compute new guidance_update_id: replace old period_u_id with correct one
        new_gu_id = old_gu_id.replace(old_pid, correct_period_id)

        if dry_run:
            log.info(f"    [DRY] {old_gu_id[:60]}... → rekey + re-point to {correct_period_id}")
            migrated += 1
            continue

        # Preflight: check for collision
        collision = mgr.execute_cypher_query_all(
            "MATCH (gu:GuidanceUpdate {id: $new_id}) RETURN gu.id AS id LIMIT 1",
            {"new_id": new_gu_id},
        )
        if collision:
            log.warning(f"    COLLISION: {new_gu_id[:60]}... already exists — SKIPPING")
            collisions += 1
            continue

        # Execute migration: MERGE correct period, re-point, rekey
        mgr.execute_cypher_query_all("""
            MATCH (gu:GuidanceUpdate {id: $old_id})
            MATCH (gu)-[old_rel:HAS_PERIOD]->(:GuidancePeriod)
            DELETE old_rel
            WITH gu
            MERGE (gp:GuidancePeriod {id: $correct_pid})
              ON CREATE SET gp.u_id = $correct_pid,
                            gp.start_date = $start_date,
                            gp.end_date = $end_date
            MERGE (gu)-[:HAS_PERIOD]->(gp)
            SET gu.id = $new_id
            RETURN gu.id AS id
        """, {
            "old_id": old_gu_id,
            "correct_pid": correct_period_id,
            "start_date": dates["start"],
            "end_date": dates["end"],
            "new_id": new_gu_id,
        })
        migrated += 1

    return migrated, collisions


def cleanup_orphaned_periods(mgr, dry_run):
    """Delete GuidancePeriod nodes with no HAS_PERIOD relationships."""
    orphans = mgr.execute_cypher_query_all("""
        MATCH (gp:GuidancePeriod)
        WHERE NOT ()-[:HAS_PERIOD]->(gp)
        RETURN gp.u_id AS u_id
    """)
    if not orphans:
        log.info("No orphaned GuidancePeriod nodes found.")
        return 0
    if dry_run:
        log.info(f"[DRY] Would delete {len(orphans)} orphaned GuidancePeriod nodes")
        return len(orphans)
    mgr.execute_cypher_query_all("""
        MATCH (gp:GuidancePeriod)
        WHERE NOT ()-[:HAS_PERIOD]->(gp)
        DETACH DELETE gp
    """)
    log.info(f"Deleted {len(orphans)} orphaned GuidancePeriod nodes")
    return len(orphans)


def verify_no_duplicates(mgr):
    """Verify zero duplicate duration quarter/annual period groups remain."""
    result = mgr.execute_cypher_query_all("""
        MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company)
        WHERE gu.fiscal_year IS NOT NULL
          AND gu.time_type = 'duration'
          AND (
            (gu.period_scope = 'quarter' AND gu.fiscal_quarter IS NOT NULL)
            OR
            (gu.period_scope = 'annual' AND gu.fiscal_quarter IS NULL)
          )
        MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
        WITH c.ticker AS ticker, gu.fiscal_year AS fy,
             gu.period_scope AS scope, gu.fiscal_quarter AS fq,
             collect(DISTINCT gp.u_id) AS period_ids
        WHERE size(period_ids) > 1
        RETURN ticker, fy, scope,
               CASE WHEN fq IS NOT NULL THEN 'Q' + toString(fq) ELSE 'FY' END AS label,
               size(period_ids) AS dup_count
    """)
    if result:
        log.error(f"VERIFICATION FAILED: {len(result)} duplicate groups remain!")
        for row in result[:10]:
            log.error(f"  {row['ticker']} FY{row['fy']} {row['scope']}: {row['dup_count']} periods")
        return False
    log.info("VERIFICATION PASSED: zero duplicate period groups")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate guidance periods to SEC-exact dates")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
    mgr = get_manager()

    # Step 1: Discover affected tickers dynamically
    tickers = discover_affected_tickers(mgr)
    log.info(f"Found {len(tickers)} tickers with duplicate period groups: {tickers}")

    if not tickers:
        log.info("Nothing to migrate.")
        return

    # Step 2: Migrate each ticker
    total_migrated = 0
    total_collisions = 0
    for ticker in tickers:
        groups = get_duplicate_groups(mgr, ticker)
        log.info(f"\n{ticker}: {len(groups)} duplicate groups")
        for group in groups:
            fy = group["fy"]
            fq = group["fq"]
            suffix = f"Q{fq}" if fq is not None else "FY"
            log.info(f"  FY{fy} {suffix}: {len(group['period_ids'])} periods, "
                     f"IDs: {group['period_ids'][:3]}...")
            migrated, collisions = migrate_group(
                mgr, r, ticker, fy, fq, group["period_ids"], args.dry_run)
            total_migrated += migrated
            total_collisions += collisions

    log.info(f"\nMigration complete: {total_migrated} updates migrated, "
             f"{total_collisions} collisions skipped")

    # Step 3: Cleanup orphaned periods
    cleanup_orphaned_periods(mgr, args.dry_run)

    # Step 4: Verify
    if not args.dry_run:
        verify_no_duplicates(mgr)

    mgr.close()


if __name__ == "__main__":
    main()
