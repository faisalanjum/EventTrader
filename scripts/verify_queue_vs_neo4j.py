#!/usr/bin/env python3
"""
Definitive verification of Redis heavy queue vs Neo4j state.

Uses raw Neo4j driver + OPTIONAL MATCH + UNWIND to guarantee one row per
input ID. Three independent check passes cross-validate results.

For each queue item, determines:
  - Does Report node exist in Neo4j?
  - Does it have CALCULATION_EDGE facts?
  - Does it have HAS_XBRL → XBRLNode?
  - What is xbrl_status?
  - Fact count?

Then categorizes into: safe-to-remove / must-reprocess / brand-new.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from redisDB.redis_constants import RedisKeys

warnings.filterwarnings("ignore")
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

HEAVY = RedisKeys.XBRL_QUEUE_HEAVY
BATCH = 50  # Small batches for reliable query execution


def fetch_queue() -> list[dict]:
    r = subprocess.run(
        ["kubectl", "exec", "-n", "infrastructure", "redis-79d9c8d68f-z256d", "--",
         "redis-cli", "LRANGE", HEAVY, "0", "-1"],
        capture_output=True, text=True, check=True,
    )
    return [json.loads(line) for line in r.stdout.strip().split("\n") if line.strip()]


def classify(driver, ids: list[str]) -> dict[str, dict]:
    """Returns {report_id: {exists, has_calc, has_xbrl_node, status, fact_count}}"""
    results: dict[str, dict] = {}

    with driver.session() as s:
        for i in range(0, len(ids), BATCH):
            batch = ids[i:i + BATCH]
            records = s.run(
                """
                UNWIND $ids AS rid
                OPTIONAL MATCH (r:Report {id: rid})
                OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)
                WITH rid, r, x,
                     CASE
                       WHEN r IS NULL THEN false
                       ELSE EXISTS {
                         MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:CALCULATION_EDGE]->(:Fact)
                       }
                     END AS has_calc
                OPTIONAL MATCH (x)<-[:REPORTS]-(f:Fact)
                WITH rid, r, x, has_calc, count(f) AS fact_count
                RETURN rid AS id,
                       r IS NOT NULL AS exists,
                       r.xbrl_status AS status,
                       x IS NOT NULL AS has_xbrl_node,
                       has_calc,
                       fact_count
                """,
                ids=batch,
            ).data()
            for rec in records:
                results[rec["id"]] = rec

    return results


def cross_check(driver, ids: list[str]) -> dict[str, int]:
    """Independent totals using different query shapes — must be internally consistent."""
    out: dict[str, int] = {}
    with driver.session() as s:
        out["exist_count"] = s.run(
            "UNWIND $ids AS rid MATCH (r:Report {id: rid}) RETURN count(r) AS n",
            ids=ids,
        ).single()["n"]
        out["calc_count"] = s.run(
            "UNWIND $ids AS rid "
            "MATCH (r:Report {id: rid}) "
            "WHERE EXISTS { MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:CALCULATION_EDGE]->(:Fact) } "
            "RETURN count(r) AS n",
            ids=ids,
        ).single()["n"]
        out["xbrl_node_count"] = s.run(
            "UNWIND $ids AS rid "
            "MATCH (r:Report {id: rid})-[:HAS_XBRL]->(x:XBRLNode) "
            "RETURN count(DISTINCT r) AS n",
            ids=ids,
        ).single()["n"]
    return out


def main() -> None:
    items = fetch_queue()
    ids = [i["report_id"] for i in items]
    print(f"Queue depth: {len(ids)}")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687"),
        auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )

    try:
        # ── Pass 1: per-ID classification ───────────────────────────────────
        per_id = classify(driver, ids)
        returned = len(per_id)
        print(f"Classify rows returned: {returned} (expected {len(ids)})")

        # ── Pass 2: independent aggregate cross-check ───────────────────────
        agg = cross_check(driver, ids)
        print(f"Cross-check: exists={agg['exist_count']} | has_calc={agg['calc_count']} | has_xbrl_node={agg['xbrl_node_count']}")

        # ── Categorize ──────────────────────────────────────────────────────
        cat_not_exist: list[str] = []
        cat_exist_with_calc: list[dict] = []
        cat_exist_no_calc_has_xbrl: list[dict] = []
        cat_exist_no_calc_no_xbrl: list[dict] = []

        for rid in ids:
            r = per_id.get(rid)
            if r is None:
                print(f"  WARN: per-ID query returned no row for {rid}")
                continue
            if not r["exists"]:
                cat_not_exist.append(rid)
            elif r["has_calc"]:
                cat_exist_with_calc.append(r)
            elif r["has_xbrl_node"]:
                cat_exist_no_calc_has_xbrl.append(r)
            else:
                cat_exist_no_calc_no_xbrl.append(r)

        print()
        print("=== DEFINITIVE CATEGORIZATION ===")
        print(f"  A) Don't exist in Neo4j (brand-new):        {len(cat_not_exist)}")
        print(f"  B) Exist WITH CALCULATION_EDGE (remove!):    {len(cat_exist_with_calc)}")
        print(f"  C) Exist, no CALCULATION_EDGE, HAS XBRLNode: {len(cat_exist_no_calc_has_xbrl)}")
        print(f"  D) Exist, no CALCULATION_EDGE, no XBRLNode:  {len(cat_exist_no_calc_no_xbrl)}")

        total = len(cat_not_exist) + len(cat_exist_with_calc) + len(cat_exist_no_calc_has_xbrl) + len(cat_exist_no_calc_no_xbrl)
        print(f"  TOTAL: {total} (queue depth was {len(ids)})")

        # ── Consistency validation ─────────────────────────────────────────
        print()
        print("=== CONSISTENCY VALIDATION ===")
        per_id_exist = len(ids) - len(cat_not_exist)
        per_id_calc = len(cat_exist_with_calc)
        per_id_xbrl = len(cat_exist_with_calc) + len(cat_exist_no_calc_has_xbrl)
        ok1 = per_id_exist == agg["exist_count"]
        ok2 = per_id_calc == agg["calc_count"]
        ok3 = per_id_xbrl == agg["xbrl_node_count"]
        print(f"  per-ID exist ({per_id_exist}) == aggregate exist ({agg['exist_count']}): {'✓' if ok1 else '✗ MISMATCH'}")
        print(f"  per-ID calc  ({per_id_calc}) == aggregate calc  ({agg['calc_count']}): {'✓' if ok2 else '✗ MISMATCH'}")
        print(f"  per-ID xbrl  ({per_id_xbrl}) == aggregate xbrl  ({agg['xbrl_node_count']}): {'✓' if ok3 else '✗ MISMATCH'}")

        # ── Detail on brand-new items (sample) ──────────────────────────────
        if cat_not_exist:
            print()
            print("=== SAMPLE: don't-exist items (first 5, last 5) ===")
            cat_not_exist.sort()
            for rid in cat_not_exist[:5]:
                item = next(i for i in items if i["report_id"] == rid)
                print(f"  {rid} form={item['form_type']} cik={item['cik']}")
            if len(cat_not_exist) > 10:
                print(f"  ... {len(cat_not_exist) - 10} more ...")
            for rid in cat_not_exist[-5:]:
                item = next(i for i in items if i["report_id"] == rid)
                print(f"  {rid} form={item['form_type']} cik={item['cik']}")

        # ── If any category B items exist, they shouldn't — flag ────────────
        if cat_exist_with_calc:
            print()
            print("!!! CATEGORY B — items WITH CALCULATION_EDGE still in queue !!!")
            for r in cat_exist_with_calc[:10]:
                print(f"  {r['id']} status={r['status']} facts={r['fact_count']}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
