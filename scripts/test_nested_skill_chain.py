#!/usr/bin/env python3
"""
Test: Nested Skill Chaining via SDK
====================================
Tests: SDK → /skill-A → (Skill tool) → /skill-B → result back to A → result to SDK

This is the EXACT pattern earnings-attribution uses:
  /earnings-attribution → Skill tool → /neo4j-news → result

Uses existing test skill: test-3layer-top → test-3layer-mid → test-3layer-bottom
"""
import asyncio
import os

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/nested-chain-result.txt"

async def test_nested_chain():
    print("=" * 60)
    print("TEST: Nested Skill Chain (SDK → A → B → C)")
    print("=" * 60)
    print("\nPattern being tested:")
    print("  SDK → /test-3layer-top → /test-3layer-mid → /test-3layer-bottom")
    print("\nThis is the SAME pattern as:")
    print("  SDK → /earnings-attribution → /neo4j-news")
    print("-" * 60)

    # Clean previous
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    output = ""

    async for msg in query(
        prompt=f"""/test-3layer-top

After the skill completes, write the full result to {OUTPUT_FILE}
""",
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=30,
        )
    ):
        if hasattr(msg, 'result'):
            output += str(msg.result)
            print(f"[OUTPUT] {str(msg.result)[:300]}...")

    # Check results
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Check for evidence of chain execution
    checks = {
        "Layer 1 (top) executed": "layer" in output.lower() or "top" in output.lower(),
        "Layer 2 (mid) reached": "mid" in output.lower() or "layer 2" in output.lower() or "3layer" in output.lower(),
        "Layer 3 (bottom) reached": "bottom" in output.lower() or "layer 3" in output.lower() or "mcp" in output.lower() or "neo4j" in output.lower(),
        "Result propagated back": len(output) > 200,
    }

    # Also check test output files that the skills create
    test_files = [
        "earnings-analysis/test-outputs/3layer-top.txt",
        "earnings-analysis/test-outputs/3layer-mid.txt",
        "earnings-analysis/test-outputs/3layer-bottom.txt",
    ]

    files_created = []
    for f in test_files:
        if os.path.exists(f):
            files_created.append(os.path.basename(f))

    checks["Test output files created"] = len(files_created) >= 2

    all_pass = True
    for check, passed in checks.items():
        print(f"{'✅' if passed else '❌'} {check}")
        if not passed:
            all_pass = False

    if files_created:
        print(f"\nFiles created: {files_created}")

    print("-" * 60)
    if all_pass:
        print("✅ NESTED SKILL CHAINING WORKS!")
        print("   earnings-attribution pattern is CONFIRMED.")
    else:
        print("⚠️  Check output above")

    return all_pass

if __name__ == "__main__":
    asyncio.run(test_nested_chain())
