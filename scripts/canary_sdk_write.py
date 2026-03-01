#!/usr/bin/env python3
"""SDK Write Canary — full 2-phase guidance extraction with Neo4j writes.

Validates the complete production write path in K8s:
  Phase 1: PR extraction → guidance_write.sh --write → Neo4j MERGE
  Phase 2: Q&A enrichment → reads Phase 1 items → enriches → writes back

Then verifies items exist in Neo4j and cleans up.

Requirements:
  - hostNetwork: true (MCP stdio + Bolt at localhost:30687)
  - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD env vars
  - ENABLE_GUIDANCE_WRITES=true
  - HOME=/home/faisal, SHELL=/bin/bash, runAsUser=1000
"""

import asyncio
import json
import os
import sys
import time

TICKER = "CRM"
SOURCE_ID = "CRM_2025-09-03T17.00.00-04.00"


def log(msg: str):
    print(f"[write-canary] {time.strftime('%H:%M:%S')} {msg}", flush=True)


def cypher(mgr, query: str, params: dict | None = None) -> list[dict]:
    """Run Cypher, always return list[dict]."""
    return mgr.execute_cypher_query_all(query, params or {})


async def phase_full_extraction():
    """Run full 2-phase guidance extraction with MODE=write."""
    from claude_agent_sdk import query, ClaudeAgentOptions

    options = ClaudeAgentOptions(
        setting_sources=["project"],
        cwd="/home/faisal/EventMarketDB",
        permission_mode="bypassPermissions",
        max_turns=100,
    )

    prompt = f"/guidance-extractor {TICKER} transcript {SOURCE_ID} MODE=write"
    log(f"Prompt: {prompt}")

    result_text = None
    start = time.time()
    async for msg in query(prompt=prompt, options=options):
        if hasattr(msg, "result"):
            result_text = msg.result
    elapsed = time.time() - start

    if result_text is None:
        log(f"ERROR: No result returned (elapsed: {elapsed:.0f}s)")
        return None

    log(f"Elapsed: {elapsed:.0f}s")
    log(f"Result:\n{result_text[:1500]}")
    return result_text


def verify_neo4j_writes(mgr) -> int:
    """Verify guidance items were written to Neo4j via direct Bolt."""
    log("VERIFY: Checking Neo4j for written guidance items...")

    rows = cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "RETURN gu.label AS label, gu.period_scope AS scope, gu.source_refs AS refs",
        {"sid": SOURCE_ID})
    total = len(rows)
    labels = [r["label"] for r in rows]
    scopes = list({r["scope"] for r in rows})
    refs_count = sum(1 for r in rows if r.get("refs") and len(r["refs"]) > 0)
    log(f"  GuidanceUpdate nodes: {total}")
    log(f"  Labels: {labels}")
    log(f"  Scopes: {scopes}")
    log(f"  Items with source_refs: {refs_count}")

    # Guidance parent nodes
    parents = cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "MATCH (gu)-[:UPDATES]->(g:Guidance) "
        "RETURN count(DISTINCT g) AS cnt",
        {"sid": SOURCE_ID})
    log(f"  Guidance parent nodes: {parents[0]['cnt'] if parents else 0}")

    # GuidancePeriod nodes (correct relationship: HAS_PERIOD)
    periods = cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod) "
        "RETURN count(DISTINCT gp) AS cnt, collect(DISTINCT gp.u_id) AS ids",
        {"sid": SOURCE_ID})
    if periods:
        log(f"  GuidancePeriod nodes: {periods[0]['cnt']}")
        log(f"  Period IDs: {periods[0]['ids']}")

    return total


def cleanup_neo4j(mgr) -> bool:
    """Remove all guidance items written by this test."""
    log("CLEANUP: Removing CRM guidance items from Neo4j...")

    # Delete GuidanceUpdate nodes and their edges
    cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "DETACH DELETE gu",
        {"sid": SOURCE_ID})
    log("  Deleted GuidanceUpdate nodes")

    # Note: Guidance parent nodes are shared across companies (e.g., guidance:revenue).
    # Don't delete them — they're idempotent MERGE targets and may be linked by other sources.
    # Only GuidanceUpdate nodes are source-specific and safe to delete.

    # Verify cleanup
    remaining = cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "RETURN count(gu) AS cnt",
        {"sid": SOURCE_ID})
    rem = remaining[0]["cnt"] if remaining else 0
    log(f"  Remaining after cleanup: {rem}")
    return rem == 0


async def main():
    log("=" * 60)
    log("Claude SDK Write Canary — Full 2-Phase Extraction")
    log(f"Ticker: {TICKER}")
    log(f"Source: {SOURCE_ID}")
    log(f"Mode: WRITE (real Neo4j writes)")
    log(f"NEO4J_URI: {os.getenv('NEO4J_URI', 'NOT SET')}")
    log(f"ENABLE_GUIDANCE_WRITES: {os.getenv('ENABLE_GUIDANCE_WRITES', 'NOT SET')}")
    log("=" * 60)

    # Setup Neo4j connection
    sys.path.insert(0, "/home/faisal/EventMarketDB")
    from neograph.Neo4jConnection import get_manager
    mgr = get_manager()

    # Pre-check: Bolt connectivity
    try:
        test = cypher(mgr, "RETURN 1 AS ok")
        log("PRE-CHECK: Neo4j Bolt connection OK")
    except Exception as e:
        log(f"PRE-CHECK FAIL: {e}")
        sys.exit(1)

    # Pre-check: clean slate
    existing = cypher(mgr,
        "MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $sid}) "
        "RETURN count(gu) AS cnt",
        {"sid": SOURCE_ID})
    if existing and existing[0]["cnt"] > 0:
        log(f"PRE-CHECK: Found {existing[0]['cnt']} existing items — cleaning first")
        cleanup_neo4j(mgr)

    # Phase 1+2: Full extraction with writes
    log("")
    log("PHASE 1+2: Running guidance-extractor with MODE=write...")
    result = await phase_full_extraction()
    if result is None:
        log("EXTRACTION FAILED")
        mgr.close()
        sys.exit(1)

    # Verify writes landed in Neo4j
    log("")
    total = verify_neo4j_writes(mgr)
    if total == 0:
        log("VERIFY FAIL: No items found in Neo4j after write")
        mgr.close()
        sys.exit(1)
    log(f"VERIFY PASS: {total} items confirmed in Neo4j")

    # Cleanup
    log("")
    clean = cleanup_neo4j(mgr)
    mgr.close()
    if not clean:
        log("CLEANUP FAIL: Items remain")
        sys.exit(1)
    log("CLEANUP PASS: Zero residue in Neo4j")

    # Summary
    log("")
    log("=" * 60)
    log("ALL PASSED")
    log(f"  Items written + verified: {total}")
    log(f"  Cleanup: complete")
    log("=" * 60)

    with open("/tmp/write_canary_result.json", "w") as f:
        json.dump({"status": "PASS", "items_written": total, "cleanup": "complete"}, f)


if __name__ == "__main__":
    asyncio.run(main())
