#!/usr/bin/env python3
"""
Claude Agent SDK Compatibility Test
====================================
Run this to verify SDK can trigger your .claude/ skills.

Tested: 2026-01-16
SDK Version: 0.1.19

Usage:
    source venv/bin/activate
    python scripts/test_sdk_compatibility.py

Expected output:
    ✅ Skills loaded: 61
    ✅ MCP servers: ['alphavantage', 'neo4j-cypher', 'perplexity']
    ✅ Skill invocation: PASS
    ✅ File writing: PASS
    ✅ ALL TESTS PASSED
"""
import asyncio
import os
import sys
from datetime import datetime

# Must run from project root
os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

TEST_FILE = "earnings-analysis/test-outputs/sdk-compatibility-test.txt"


async def run_test():
    """Single comprehensive test that verifies all SDK capabilities"""

    print("=" * 60)
    print("Claude Agent SDK Compatibility Test")
    print("=" * 60)

    # Clean previous test file
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

    timestamp = datetime.now().isoformat()
    results = {
        "skills_loaded": 0,
        "mcp_servers": [],
        "skill_invoked": False,
        "file_written": False,
    }

    # Run single query that tests everything
    async for message in query(
        prompt=f"""Do these 2 things:

1. Use /neo4j-report skill to find ONE 8-K report for ticker AAPL.
   Report: accessionNo, formType, ticker

2. Write a file to {TEST_FILE} with content:
   SDK_TEST_PASSED
   Timestamp: {timestamp}
   Skill: neo4j-report invoked successfully
""",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=15,
            permission_mode="bypassPermissions",
        )
    ):
        # Capture init data
        if hasattr(message, 'data'):
            data = message.data
            if data.get('type') == 'system' and data.get('subtype') == 'init':
                results["skills_loaded"] = len(data.get('slash_commands', []))
                results["mcp_servers"] = [
                    s['name'] for s in data.get('mcp_servers', [])
                    if s.get('status') == 'connected'
                ]

        # Capture final output
        if hasattr(message, 'result'):
            output = str(message.result).lower()
            if 'aapl' in output or 'apple' in output or '8-k' in output:
                results["skill_invoked"] = True

    # Check if file was written
    if os.path.exists(TEST_FILE):
        with open(TEST_FILE) as f:
            content = f.read()
        if "SDK_TEST_PASSED" in content:
            results["file_written"] = True

    # Report results
    print()
    print("Results:")
    print("-" * 60)

    # Skills
    skills_ok = results["skills_loaded"] >= 50
    print(f"{'✅' if skills_ok else '❌'} Skills loaded: {results['skills_loaded']}")

    # MCP
    mcp_ok = len(results["mcp_servers"]) >= 2
    print(f"{'✅' if mcp_ok else '❌'} MCP servers: {results['mcp_servers']}")

    # Skill invocation
    print(f"{'✅' if results['skill_invoked'] else '❌'} Skill invocation: {'PASS' if results['skill_invoked'] else 'FAIL'}")

    # File writing
    print(f"{'✅' if results['file_written'] else '❌'} File writing: {'PASS' if results['file_written'] else 'FAIL'}")

    # Overall
    all_passed = skills_ok and mcp_ok and results["skill_invoked"] and results["file_written"]
    print("-" * 60)
    print(f"{'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print()

    if all_passed:
        print("Your .claude/ directory works with the SDK.")
        print("You can use earnings_trigger.py for event-driven automation.")

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(run_test())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
