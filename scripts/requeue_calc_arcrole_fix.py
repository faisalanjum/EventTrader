#!/usr/bin/env python3
"""
requeue_calc_arcrole_fix.py — Requeue ALL-YEARS 10-K/10-Q for summationItems arcrole fix.

Three operations (all no-ops unless --execute):

  Part 1: Reset xbrl_status COMPLETED → null for reports ALREADY IN the heavy
          OR medium queue. These were pushed without resetting status first,
          so the worker skips them. Fixing the Neo4j status is all that's
          needed — they're already in Redis.

  Part 2: Reset COMPLETED → null AND push to heavy queue for 10-K/10-K/A
          (any year) that have no CALCULATION_EDGE but DO have presentation
          edges (i.e., processing-gap, not genuinely linkbase-free) and
          aren't already queued.

  Part 3: Reset COMPLETED → null AND push to medium queue for 10-Q/10-Q/A
          (any year) that have no CALCULATION_EDGE but DO have presentation
          edges and aren't already queued.

Presentation-edge guard:
  Without a calc linkbase OR a pres linkbase, a filing is genuinely
  linkbase-free — reprocessing won't help. We require the pres linkbase to
  exist (via (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)<-[:PRESENTATION_EDGE]-(:Abstract))
  so we only touch real processing-gap candidates.

Safety:
  - Only touches xbrl_status = 'COMPLETED'. Never PROCESSING, QUEUED, or null.
  - Neo4j write happens before Redis push (no race window).
  - Idempotent: re-running is safe (COMPLETED filter prevents double-reset).
  - Scale note: the all-years cohort is ~1,000 filings. Heavy pod throughput
    is ~2 filings/90min, so draining will take days.

Usage:
  python scripts/requeue_calc_arcrole_fix.py           # dry-run
  python scripts/requeue_calc_arcrole_fix.py --execute # apply
"""

from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from redisDB.redisClasses import RedisClient
from redisDB.redis_constants import RedisKeys

warnings.filterwarnings("ignore", category=UserWarning, module="neo4j")
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DRY_RUN = "--execute" not in sys.argv

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

HEAVY = RedisKeys.XBRL_QUEUE_HEAVY   # reports:queues:xbrl:heavy
MEDIUM = RedisKeys.XBRL_QUEUE_MEDIUM  # reports:queues:xbrl:medium


def _redis() -> RedisClient:
    return RedisClient(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        prefix="",
        source_type=RedisKeys.SOURCE_REPORTS,
    )


def _queue_items(rc: RedisClient, queue: str) -> list[dict]:
    raw = rc.client.lrange(queue, 0, -1)
    return [json.loads(item) for item in raw]


def _job(row: dict) -> str:
    return json.dumps({
        "report_id": row["id"],
        "accession": row["id"],
        "cik": row["cik"],
        "form_type": row["form_type"],
    })


def main() -> None:
    mode = "DRY-RUN" if DRY_RUN else "EXECUTE"
    log.info(f"=== calc arcrole requeue — {mode} ===")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    rc = _redis()

    try:
        # ── Snapshot current queue state ────────────────────────────────────
        heavy_items = _queue_items(rc, HEAVY)
        medium_items = _queue_items(rc, MEDIUM)
        heavy_ids = [i["report_id"] for i in heavy_items]
        medium_ids = [i["report_id"] for i in medium_items]
        in_queue_ids = heavy_ids + medium_ids
        log.info(f"Current queue depths: heavy={len(heavy_ids)}, medium={len(medium_ids)}")

        # ── Part 1: In-queue COMPLETED → reset to null ──────────────────────
        with driver.session() as s:
            records = s.run(
                "MATCH (r:Report) WHERE r.id IN $ids AND r.xbrl_status = 'COMPLETED' "
                "RETURN r.id AS id ORDER BY r.id",
                ids=in_queue_ids,
            ).data()
        part1_ids = [r["id"] for r in records]
        log.info(f"Part 1 — in-queue COMPLETED to reset: {len(part1_ids)}")
        for rid in part1_ids:
            log.info(f"  reset (in-queue): {rid}")

        if not DRY_RUN and part1_ids:
            with driver.session() as s:
                n = s.run(
                    "UNWIND $ids AS rid "
                    "MATCH (r:Report {id: rid}) WHERE r.xbrl_status = 'COMPLETED' "
                    "SET r.xbrl_status = null "
                    "RETURN count(r) AS n",
                    ids=part1_ids,
                ).single()["n"]
            log.info(f"  ✓ Part 1: reset {n} Neo4j records to null")

        # ── Part 2: New heavy items (10-K, 10-K/A not in queue) ────────────
        # All years, COMPLETED-but-no-calc, presentation edges present (processing gap).
        with driver.session() as s:
            part2 = s.run(
                "MATCH (r:Report {xbrl_status: 'COMPLETED', is_xml: true}) "
                "WHERE r.formType IN ['10-K', '10-K/A'] "
                "  AND NOT EXISTS { "
                "    MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:CALCULATION_EDGE]->(:Fact) "
                "  } "
                "  AND EXISTS { "
                "    MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)<-[:PRESENTATION_EDGE]-(:Abstract) "
                "  } "
                "  AND NOT r.id IN $in_queue "
                "RETURN r.id AS id, r.cik AS cik, r.formType AS form_type "
                "ORDER BY r.id DESC",
                in_queue=in_queue_ids,
            ).data()
        log.info(f"Part 2 — all-years 10-K/10-K/A processing gaps to reset+push to heavy: {len(part2)}")

        for row in part2:
            log.info(f"  heavy: {row['id']} ({row['form_type']})")
            if not DRY_RUN:
                with driver.session() as s:
                    s.run(
                        "MATCH (r:Report {id: $id}) WHERE r.xbrl_status = 'COMPLETED' "
                        "SET r.xbrl_status = null",
                        id=row["id"],
                    )
                rc.push_to_queue(HEAVY, _job(row))

        if not DRY_RUN:
            log.info(f"  ✓ Part 2: reset+pushed {len(part2)} to heavy")

        # ── Part 3: New medium items (10-Q, 10-Q/A) ─────────────────────────
        # All years, COMPLETED-but-no-calc, presentation edges present (processing gap).
        with driver.session() as s:
            part3 = s.run(
                "MATCH (r:Report {xbrl_status: 'COMPLETED', is_xml: true}) "
                "WHERE r.formType IN ['10-Q', '10-Q/A'] "
                "  AND NOT EXISTS { "
                "    MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:CALCULATION_EDGE]->(:Fact) "
                "  } "
                "  AND EXISTS { "
                "    MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)<-[:PRESENTATION_EDGE]-(:Abstract) "
                "  } "
                "  AND NOT r.id IN $in_queue "
                "RETURN r.id AS id, r.cik AS cik, r.formType AS form_type "
                "ORDER BY r.id DESC",
                in_queue=in_queue_ids,
            ).data()
        log.info(f"Part 3 — all-years 10-Q/10-Q/A processing gaps to reset+push to medium: {len(part3)}")

        for row in part3:
            log.info(f"  medium: {row['id']} ({row['form_type']})")
            if not DRY_RUN:
                with driver.session() as s:
                    s.run(
                        "MATCH (r:Report {id: $id}) WHERE r.xbrl_status = 'COMPLETED' "
                        "SET r.xbrl_status = null",
                        id=row["id"],
                    )
                rc.push_to_queue(MEDIUM, _job(row))

        if not DRY_RUN:
            log.info(f"  ✓ Part 3: reset+pushed {len(part3)} to medium")

        # ── Final queue depths ───────────────────────────────────────────────
        if not DRY_RUN:
            h_depth = rc.client.llen(HEAVY)
            m_depth = rc.client.llen(MEDIUM)
            log.info(f"=== POST-EXECUTE queue depths: heavy={h_depth}, medium={m_depth} ===")

        log.info(
            f"=== SUMMARY ({mode}) ==="
            f"\n  Part 1 in-queue reset:  {len(part1_ids)}"
            f"\n  Part 2 new heavy:        {len(part2)}"
            f"\n  Part 3 new medium:       {len(part3)}"
            f"\n  Grand total:             {len(part1_ids) + len(part2) + len(part3)}"
        )
        if DRY_RUN:
            log.info("Pass --execute to apply.")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
