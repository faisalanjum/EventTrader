#!/usr/bin/env python3
"""
snapshot_xbrl_in_flight.py — Capture what XBRL workers are processing right now.

Two modes:
  --snapshot   Write a JSON file with in-flight accessions + queue depths.
  --verify <path>  After a Neo4j restart, check each snapshotted in-flight
                   accession in Neo4j and re-push anything that ended up
                   FAILED or stuck (status != COMPLETED OR missing calc edges).
                   Dry-run by default; --execute to actually requeue.

Typical use:
  # Before restart:
  python scripts/snapshot_xbrl_in_flight.py --snapshot

  # After restart:
  python scripts/snapshot_xbrl_in_flight.py --verify logs/neo4j_restart_snapshots/in_flight_*.json
  python scripts/snapshot_xbrl_in_flight.py --verify <path> --execute
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from redisDB.redisClasses import RedisClient
from redisDB.redis_constants import RedisKeys

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

NAMESPACE = "processing"
LABEL_SELECTOR = "app in (xbrl-worker-heavy,xbrl-worker-medium)"
POLL_RE = re.compile(r"Polled from queue \S+: \('[^']+', '(\{[^}]+\})'\)")
DONE_RE = re.compile(r"COMPLETED XBRL for accession: (\S+)")


def _neo4j_driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )


def _redis() -> RedisClient:
    return RedisClient(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        prefix="",
        source_type=RedisKeys.SOURCE_REPORTS,
    )


def snapshot(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = _redis()

    pods_out = subprocess.check_output(
        ["kubectl", "get", "pods", "-n", NAMESPACE, "-l", LABEL_SELECTOR, "-o", "name"],
        text=True,
    ).strip().splitlines()
    pod_names = [p.replace("pod/", "") for p in pods_out if p]

    in_flight = []
    for pod in pod_names:
        try:
            logs = subprocess.check_output(
                ["kubectl", "logs", "-n", NAMESPACE, pod, "--tail=3000"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            continue

        polled = list(POLL_RE.finditer(logs))
        completed = list(DONE_RE.finditer(logs))
        if not polled:
            continue

        last_polled_job = json.loads(polled[-1].group(1))
        last_polled_acc = last_polled_job.get("accession")
        last_completed = completed[-1].group(1) if completed else None

        if last_polled_acc != last_completed:
            # Determine which queue this pod belongs to (so we re-push correctly)
            queue = (
                RedisKeys.XBRL_QUEUE_HEAVY
                if "heavy" in pod
                else RedisKeys.XBRL_QUEUE_MEDIUM
            )
            in_flight.append({
                "pod": pod,
                "queue": queue,
                "accession": last_polled_acc,
                "cik": last_polled_job.get("cik"),
                "form_type": last_polled_job.get("form_type"),
                "report_id": last_polled_job.get("report_id"),
            })

    snapshot_obj = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "queue_depths": {
            "heavy": rc.client.llen(RedisKeys.XBRL_QUEUE_HEAVY),
            "medium": rc.client.llen(RedisKeys.XBRL_QUEUE_MEDIUM),
            "light": rc.client.llen(RedisKeys.XBRL_QUEUE_LIGHT),
        },
        "in_flight_count": len(in_flight),
        "in_flight": in_flight,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"in_flight_{ts}.json"
    path.write_text(json.dumps(snapshot_obj, indent=2))
    log.info(f"Wrote snapshot: {path}")
    log.info(json.dumps(snapshot_obj, indent=2))
    return path


def verify(snapshot_path: Path, execute: bool) -> None:
    data = json.loads(snapshot_path.read_text())
    in_flight = data.get("in_flight", [])
    if not in_flight:
        log.info("Snapshot has no in-flight items. Nothing to verify.")
        return

    driver = _neo4j_driver()
    rc = _redis()

    # Already-queued snapshot so we don't double-push
    def _queue_ids(q):
        raw = rc.client.lrange(q, 0, -1)
        return {json.loads(item)["report_id"] for item in raw}

    queued_heavy = _queue_ids(RedisKeys.XBRL_QUEUE_HEAVY)
    queued_medium = _queue_ids(RedisKeys.XBRL_QUEUE_MEDIUM)
    already_queued = queued_heavy | queued_medium

    needs_requeue = []
    ok_items = []

    with driver.session() as s:
        for item in in_flight:
            rid = item["accession"]
            rec = s.run(
                """
                MATCH (r:Report {id: $id})
                RETURN r.xbrl_status AS status,
                       EXISTS {
                         (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:CALCULATION_EDGE]->(:Fact)
                       } AS has_calc,
                       EXISTS {
                         (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)<-[:PRESENTATION_EDGE]-(:Abstract)
                       } AS has_pres
                """,
                id=rid,
            ).single()

            if rec is None:
                log.warning(f"  {rid}: Report node missing from Neo4j")
                continue

            status = rec["status"]
            has_calc = rec["has_calc"]
            has_pres = rec["has_pres"]

            # Successful = COMPLETED + (has_calc OR is stub amendment)
            # Stub = form_type ends /A and no pres edges (or very few — but we can't count here easily)
            stub_likely = item.get("form_type", "").endswith("/A") and not has_calc and has_pres is False

            if status == "COMPLETED" and has_calc:
                ok_items.append({**item, "status": status, "has_calc": True})
            elif status == "COMPLETED" and stub_likely:
                ok_items.append({**item, "status": status, "has_calc": False, "note": "stub"})
            else:
                needs_requeue.append({
                    **item,
                    "status": status,
                    "has_calc": has_calc,
                    "has_pres": has_pres,
                })

    log.info(f"Verified {len(in_flight)} in-flight items:")
    log.info(f"  OK (COMPLETED + calc or stub): {len(ok_items)}")
    log.info(f"  Needs requeue:                  {len(needs_requeue)}")

    for item in needs_requeue:
        log.info(
            f"  REQUEUE: {item['accession']} ({item['form_type']}) "
            f"status={item['status']} has_calc={item['has_calc']} → {item['queue']}"
        )

    if not needs_requeue:
        log.info("Nothing to requeue. Done.")
        driver.close()
        return

    if not execute:
        log.info("DRY-RUN — pass --execute to reset status and requeue.")
        driver.close()
        return

    # Execute: reset status + push
    for item in needs_requeue:
        rid = item["accession"]
        if rid in already_queued:
            log.info(f"  {rid}: already in queue — skip requeue, just reset status")
        else:
            pass

        with driver.session() as s:
            s.run(
                "MATCH (r:Report {id: $id}) SET r.xbrl_status = null",
                id=rid,
            )

        if rid not in already_queued:
            job = json.dumps({
                "report_id": rid,
                "accession": rid,
                "cik": item["cik"],
                "form_type": item["form_type"],
            })
            rc.push_to_queue(item["queue"], job)
            log.info(f"  ✓ {rid}: reset + pushed to {item['queue']}")
        else:
            log.info(f"  ✓ {rid}: reset (already in queue)")

    driver.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="Capture in-flight state")
    ap.add_argument("--verify", metavar="PATH", help="Verify snapshot after restart")
    ap.add_argument("--execute", action="store_true", help="Apply requeue (not dry-run)")
    args = ap.parse_args()

    if args.snapshot:
        out = Path(__file__).resolve().parent.parent / "logs" / "neo4j_restart_snapshots"
        snapshot(out)
    elif args.verify:
        verify(Path(args.verify), args.execute)
    else:
        ap.error("Provide --snapshot or --verify <path>")


if __name__ == "__main__":
    main()
