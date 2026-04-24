#!/usr/bin/env python3
"""
Reconcile Redis SET 'reports:confirmed_in_neo4j' against actual Neo4j Report nodes.

Identifies two classes of discrepancy:
  PHANTOM  — accessionNo in Redis SET but NO matching Report node in Neo4j.
             DANGEROUS: gap-fill SISMEMBER check would skip these, leaving gaps unfilled.
  MISSING  — accessionNo on a Neo4j Report node but NOT in the Redis SET.
             SAFE but wasteful: gap-fill would re-process an already-ingested filing.

Usage:
  python scripts/reconcile_redis_neo4j_set.py              # dry-run (default)
  python scripts/reconcile_redis_neo4j_set.py --fix        # apply corrections
  python scripts/reconcile_redis_neo4j_set.py --verbose    # show all discrepancies (not just samples)
"""

import argparse
import os
import sys
import json
import time
from datetime import datetime, timezone

import redis
from neo4j import GraphDatabase


# ── connection helpers ──────────────────────────────────────────────

def get_redis_client() -> redis.Redis:
    """Connect to Redis via NodePort."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "31379"))
    client = redis.Redis(host=host, port=port, decode_responses=True)
    client.ping()
    return client


def get_neo4j_driver():
    """Connect to Neo4j using env vars."""
    uri = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        print("ERROR: NEO4J_PASSWORD env var not set", file=sys.stderr)
        sys.exit(1)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


# ── data extraction ─────────────────────────────────────────────────

def fetch_neo4j_accessions(driver) -> dict[str, dict]:
    """
    Return {accessionNo: {formType, symbols, created}} for every Report node.
    Skips nodes where accessionNo is null.
    """
    query = """
    MATCH (r:Report)
    WHERE r.accessionNo IS NOT NULL
    RETURN r.accessionNo AS accNo,
           r.formType    AS formType,
           r.symbols     AS symbols,
           r.created     AS created
    """
    result = {}
    with driver.session() as session:
        records = session.run(query)
        for rec in records:
            acc = rec["accNo"]
            if acc:  # skip empty strings too
                result[acc] = {
                    "formType": rec["formType"],
                    "symbols": rec["symbols"],
                    "created": rec["created"],
                }
    return result


def fetch_redis_set_members(client: redis.Redis) -> set[str]:
    """Return all members of the confirmed SET."""
    return client.smembers("reports:confirmed_in_neo4j")


# ── analysis ────────────────────────────────────────────────────────

def analyze(neo4j_map: dict, redis_set: set) -> tuple[set, set]:
    """
    Returns (phantoms, missing).
      phantoms = in Redis but NOT in Neo4j   (dangerous)
      missing  = in Neo4j but NOT in Redis   (safe/wasteful)
    """
    neo4j_keys = set(neo4j_map.keys())
    phantoms = redis_set - neo4j_keys
    missing = neo4j_keys - redis_set
    return phantoms, missing


def form_type_breakdown(accessions: set, neo4j_map: dict) -> dict[str, int]:
    """Count form types for a set of accession numbers (only those in neo4j_map)."""
    counts: dict[str, int] = {}
    for acc in accessions:
        info = neo4j_map.get(acc)
        ft = info["formType"] if info else "(not in Neo4j)"
        counts[ft] = counts.get(ft, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# ── fix operations ──────────────────────────────────────────────────

def remove_phantoms(client: redis.Redis, phantoms: set) -> int:
    """SREM phantom accessions from the Redis SET. Returns count removed."""
    if not phantoms:
        return 0
    # Pipeline for efficiency
    pipe = client.pipeline()
    for acc in phantoms:
        pipe.srem("reports:confirmed_in_neo4j", acc)
    results = pipe.execute()
    return sum(results)


def add_missing(client: redis.Redis, missing: set) -> int:
    """SADD missing accessions to the Redis SET. Returns count added."""
    if not missing:
        return 0
    pipe = client.pipeline()
    for acc in missing:
        pipe.sadd("reports:confirmed_in_neo4j", acc)
    results = pipe.execute()
    return sum(results)


# ── reporting ───────────────────────────────────────────────────────

def print_report(
    neo4j_count: int,
    redis_count: int,
    phantoms: set,
    missing: set,
    neo4j_map: dict,
    verbose: bool,
):
    overlap = redis_count - len(phantoms)
    print("=" * 70)
    print("  RECONCILIATION REPORT")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    print()
    print(f"  Neo4j Report nodes (with accessionNo):  {neo4j_count:,}")
    print(f"  Redis SET members:                       {redis_count:,}")
    print(f"  Overlap (consistent):                    {overlap:,}")
    print()

    # ── Phantoms ────────────────────────────────────────────────────
    if phantoms:
        print(f"  ⚠️  PHANTOMS (in Redis, NOT in Neo4j):   {len(phantoms):,}  ← DANGEROUS")
        print(f"      These accessions will be SKIPPED by gap-fill SISMEMBER check")
        print(f"      even though they are NOT actually in Neo4j.")
        print()
        sample = sorted(phantoms)[:20] if not verbose else sorted(phantoms)
        label = "All" if verbose else "Sample (first 20)"
        print(f"      {label}:")
        for acc in sample:
            print(f"        {acc}")
        if not verbose and len(phantoms) > 20:
            print(f"        ... and {len(phantoms) - 20} more")
    else:
        print(f"  ✅  PHANTOMS: 0  — Redis SET is clean (no false entries)")
    print()

    # ── Missing ─────────────────────────────────────────────────────
    if missing:
        print(f"  ℹ️  MISSING (in Neo4j, NOT in Redis):    {len(missing):,}  ← safe but wasteful")
        print(f"      These filings exist in Neo4j but gap-fill would re-process them.")
        print()
        breakdown = form_type_breakdown(missing, neo4j_map)
        print(f"      Form type breakdown:")
        for ft, cnt in breakdown.items():
            print(f"        {ft:20s}  {cnt:,}")
        print()
        sample = sorted(missing)[:20] if not verbose else sorted(missing)
        label = "All" if verbose else "Sample (first 20)"
        print(f"      {label}:")
        for acc in sample:
            info = neo4j_map.get(acc, {})
            ft = info.get("formType", "?")
            sym = info.get("symbols", "?")
            if isinstance(sym, list):
                sym = ",".join(sym[:3])
            print(f"        {acc}  [{ft}] {sym}")
        if not verbose and len(missing) > 20:
            print(f"        ... and {len(missing) - 20} more")
    else:
        print(f"  ✅  MISSING: 0  — all Neo4j reports are tracked in Redis SET")
    print()

    # ── Summary ─────────────────────────────────────────────────────
    print("-" * 70)
    if not phantoms and not missing:
        print("  RESULT: PERFECT SYNC — Redis SET and Neo4j are 100% consistent.")
    elif not phantoms:
        print(f"  RESULT: SET IS SAFE for gap-fill (0 phantoms).")
        print(f"          {len(missing):,} missing entries would cause harmless re-processing.")
    else:
        print(f"  RESULT: ⚠️  {len(phantoms):,} PHANTOM(S) FOUND — gap-fill may skip valid gaps!")
        print(f"          Run with --fix to remove phantoms and add missing entries.")
    print("-" * 70)


# ── main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reconcile Redis dedup SET vs Neo4j Reports")
    parser.add_argument("--fix", action="store_true", help="Apply corrections (remove phantoms, add missing)")
    parser.add_argument("--verbose", action="store_true", help="Show all discrepancies, not just samples")
    args = parser.parse_args()

    print("Connecting to Redis...", end=" ", flush=True)
    rclient = get_redis_client()
    print("OK")

    print("Connecting to Neo4j...", end=" ", flush=True)
    driver = get_neo4j_driver()
    print("OK")

    print()
    print("Fetching Neo4j Report accession numbers...", end=" ", flush=True)
    t0 = time.time()
    neo4j_map = fetch_neo4j_accessions(driver)
    neo4j_time = time.time() - t0
    print(f"{len(neo4j_map):,} reports in {neo4j_time:.1f}s")

    print("Fetching Redis SET members...", end=" ", flush=True)
    t0 = time.time()
    redis_set = fetch_redis_set_members(rclient)
    redis_time = time.time() - t0
    print(f"{len(redis_set):,} members in {redis_time:.1f}s")

    print("Comparing...", end=" ", flush=True)
    phantoms, missing = analyze(neo4j_map, redis_set)
    print("done")
    print()

    print_report(
        neo4j_count=len(neo4j_map),
        redis_count=len(redis_set),
        phantoms=phantoms,
        missing=missing,
        neo4j_map=neo4j_map,
        verbose=args.verbose,
    )

    # ── Fix mode ────────────────────────────────────────────────────
    if args.fix:
        print()
        if phantoms:
            print(f"FIX: Removing {len(phantoms):,} phantoms from Redis SET...", end=" ", flush=True)
            removed = remove_phantoms(rclient, phantoms)
            print(f"removed {removed:,}")
        if missing:
            print(f"FIX: Adding {len(missing):,} missing accessions to Redis SET...", end=" ", flush=True)
            added = add_missing(rclient, missing)
            print(f"added {added:,}")

        # Verify
        new_size = rclient.scard("reports:confirmed_in_neo4j")
        expected = len(redis_set) - len(phantoms) + len(missing)
        print()
        print(f"  Post-fix SET size: {new_size:,}  (expected: {expected:,})")
        if new_size == expected:
            print("  ✅ Verification passed")
        else:
            print(f"  ⚠️  Size mismatch — expected {expected:,}, got {new_size:,}")
            print(f"      (Possible: pipeline added entries during fix window)")

        # Write audit log
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pre_redis_count": len(redis_set),
            "pre_neo4j_count": len(neo4j_map),
            "phantoms_removed": len(phantoms),
            "missing_added": len(missing),
            "post_set_size": new_size,
            "phantom_accessions": sorted(phantoms),
            "missing_accessions": sorted(missing),
        }
        audit_path = os.path.join(os.path.dirname(__file__), "..", "logs", "reconcile_audit.json")
        audit_path = os.path.normpath(audit_path)
        with open(audit_path, "w") as f:
            json.dump(audit, f, indent=2)
        print(f"  Audit log: {audit_path}")
    elif phantoms or missing:
        print()
        print("  (dry-run mode — no changes made. Use --fix to apply corrections)")

    driver.close()


if __name__ == "__main__":
    main()
