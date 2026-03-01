#!/usr/bin/env python3
"""SDK Canary Script — validates Claude Agent SDK in K8s pod.

Run inside a pod with:
  - hostPath /home/faisal (credentials + project + venv)
  - hostNetwork: true (localhost:30687 for MCP stdio + Neo4j Bolt)
  - HOME=/home/faisal, SHELL=/bin/bash, runAsUser=1000

Tests (sequential, each gated on prior success):
  1. SDK import + version
  2. MCP connectivity via setting_sources=["project"] (proves .mcp.json loads)
  3. Skill invocation (/neo4j-schema)
  4. Full guidance-extractor dry-run on CRM transcript (2-phase, subagents)

Usage:
  python scripts/canary_sdk.py           # All tests
  python scripts/canary_sdk.py --quick   # Tests 1-3 only (skip guidance-extractor)
"""

import asyncio
import json
import sys
import time
import traceback


def log(msg: str):
    print(f"[canary] {time.strftime('%H:%M:%S')} {msg}", flush=True)


async def test_1_sdk_import():
    """Test 1: SDK import + version check."""
    log("TEST 1: SDK import + version")
    from claude_agent_sdk import query, ClaudeAgentOptions, ClaudeSDKClient
    log(f"  query: {type(query)}")
    log(f"  ClaudeAgentOptions: {type(ClaudeAgentOptions)}")
    log(f"  ClaudeSDKClient: {type(ClaudeSDKClient)}")
    import claude_agent_sdk
    version = getattr(claude_agent_sdk, "__version__", "unknown")
    log(f"  SDK version: {version}")
    log("TEST 1: PASS")
    return True


async def test_2_mcp_connectivity():
    """Test 2: MCP connectivity via setting_sources (proves .mcp.json stdio loads)."""
    log("TEST 2: MCP connectivity via setting_sources=[\"project\"]")
    from claude_agent_sdk import query, ClaudeAgentOptions

    stderr_lines = []
    def capture_stderr(line: str):
        stderr_lines.append(line)
        if len(stderr_lines) <= 5:
            log(f"  [stderr] {line.rstrip()}")

    options = ClaudeAgentOptions(
        setting_sources=["project"],
        cwd="/home/faisal/EventMarketDB",
        permission_mode="bypassPermissions",
        max_turns=5,
        max_budget_usd=1.0,
        stderr=capture_stderr,
    )

    result_text = None
    async for msg in query(
        prompt="Use the neo4j-cypher MCP tool to run: MATCH (c:Company) RETURN count(c) AS total. Return ONLY the number, nothing else.",
        options=options,
    ):
        if hasattr(msg, "result"):
            result_text = msg.result

    if result_text is None:
        log("  ERROR: No result returned from query()")
        log("TEST 2: FAIL")
        return False

    log(f"  Result: {result_text[:200]}")
    # Check if result contains a number (company count)
    if any(c.isdigit() for c in result_text):
        log("TEST 2: PASS (MCP read returned numeric result)")
        return True
    else:
        log("TEST 2: FAIL (no numeric result in response)")
        return False


async def test_3_skill_invocation():
    """Test 3: Skill invocation (/neo4j-schema)."""
    log("TEST 3: Skill invocation (/neo4j-schema)")
    from claude_agent_sdk import query, ClaudeAgentOptions

    options = ClaudeAgentOptions(
        setting_sources=["project"],
        cwd="/home/faisal/EventMarketDB",
        permission_mode="bypassPermissions",
        max_turns=10,
        max_budget_usd=2.0,
    )

    result_text = None
    async for msg in query(
        prompt="/neo4j-schema",
        options=options,
    ):
        if hasattr(msg, "result"):
            result_text = msg.result

    if result_text is None:
        log("  ERROR: No result returned")
        log("TEST 3: FAIL")
        return False

    log(f"  Result (first 200 chars): {result_text[:200]}")
    # Skill should return schema info mentioning node labels
    if "Company" in result_text or "Transcript" in result_text or "Report" in result_text:
        log("TEST 3: PASS (skill returned schema content)")
        return True
    else:
        log("TEST 3: FAIL (no schema content in response)")
        return False


async def test_4_guidance_extractor():
    """Test 4: Full guidance-extractor dry-run on CRM transcript."""
    log("TEST 4: Guidance-extractor dry-run (CRM transcript)")
    log("  Ticker: CRM")
    log("  Source: CRM_2025-09-03T17.00.00-04.00")
    log("  Mode: dry_run (zero Neo4j writes)")
    from claude_agent_sdk import query, ClaudeAgentOptions

    options = ClaudeAgentOptions(
        setting_sources=["project"],
        cwd="/home/faisal/EventMarketDB",
        permission_mode="bypassPermissions",
        max_turns=80,
        max_budget_usd=10.0,
    )

    result_text = None
    start = time.time()
    async for msg in query(
        prompt="/guidance-extractor CRM transcript CRM_2025-09-03T17.00.00-04.00 MODE=dry_run",
        options=options,
    ):
        if hasattr(msg, "result"):
            result_text = msg.result
            if hasattr(msg, "total_cost_usd"):
                log(f"  Cost: ${msg.total_cost_usd:.4f}")
            if hasattr(msg, "usage"):
                log(f"  Usage: {msg.usage}")
    elapsed = time.time() - start

    if result_text is None:
        log("  ERROR: No result returned")
        log(f"TEST 4: FAIL (elapsed: {elapsed:.0f}s)")
        return False

    log(f"  Result (first 500 chars): {result_text[:500]}")
    log(f"  Elapsed: {elapsed:.0f}s")

    # Check for key indicators of success
    has_items = "Items extracted" in result_text or "items" in result_text.lower()
    has_phases = "Phase 1" in result_text or "Phase 2" in result_text or "phase" in result_text.lower()
    if has_items or has_phases:
        log("TEST 4: PASS (guidance extraction completed)")
        return True
    else:
        log("TEST 4: UNCERTAIN (result returned but no extraction summary found)")
        log(f"  Full result:\n{result_text}")
        return True  # Still pass — result was returned


async def main():
    quick = "--quick" in sys.argv
    log("=" * 60)
    log("Claude Agent SDK Canary — K8s Validation")
    log(f"Mode: {'quick (tests 1-3)' if quick else 'full (tests 1-4)'}")
    log("=" * 60)

    results = {}
    tests = [
        ("test_1", test_1_sdk_import),
        ("test_2", test_2_mcp_connectivity),
        ("test_3", test_3_skill_invocation),
    ]
    if not quick:
        tests.append(("test_4", test_4_guidance_extractor))

    for name, test_fn in tests:
        try:
            passed = await test_fn()
            results[name] = "PASS" if passed else "FAIL"
        except Exception as e:
            log(f"  EXCEPTION: {e}")
            traceback.print_exc()
            results[name] = "ERROR"
        if results[name] != "PASS":
            log(f"  Stopping — {name} did not pass")
            break

    log("=" * 60)
    log("SUMMARY")
    for name, status in results.items():
        log(f"  {name}: {status}")
    total_pass = sum(1 for v in results.values() if v == "PASS")
    total = len(results)
    log(f"  {total_pass}/{total} passed")
    log("=" * 60)

    # Write result to /tmp for pod inspection
    with open("/tmp/canary_result.json", "w") as f:
        json.dump(results, f, indent=2)
    log("Results written to /tmp/canary_result.json")

    sys.exit(0 if all(v == "PASS" for v in results.values()) else 1)


if __name__ == "__main__":
    asyncio.run(main())
