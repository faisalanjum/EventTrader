#!/usr/bin/env python3
"""
Quick test: Verify skill chaining works (the core of earnings flow)
Tests: Skill invocation → MCP query → Sub-skill call → File output
"""
import asyncio
import os

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

async def test():
    print("=" * 60)
    print("Quick Skill Chain Test")
    print("=" * 60)

    tools_used = []
    output = ""

    async for msg in query(
        prompt="""Do these 3 things to prove skill chaining works:

1. Call /neo4j-report to get ONE 8-K for AAPL (just accessionNo and formType)
2. Call /neo4j-entity to get AAPL's company name
3. Write results to earnings-analysis/test-outputs/skill-chain-proof.txt

Format the file as:
SKILL_CHAIN_TEST
Report: [accessionNo from step 1]
Company: [name from step 2]
""",
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=25,
        )
    ):
        if hasattr(msg, 'data') and msg.data.get('type') == 'tool_use':
            tools_used.append(msg.data.get('name', ''))

        if hasattr(msg, 'result'):
            output += str(msg.result)

    print(f"\nTools used: {[t for t in tools_used if t]}")

    # Check output file
    test_file = "earnings-analysis/test-outputs/skill-chain-proof.txt"
    file_exists = os.path.exists(test_file)
    file_content = ""
    if file_exists:
        with open(test_file) as f:
            file_content = f.read()
        print(f"\nFile created: {test_file}")
        print(f"Content:\n{file_content}")

    # Verify
    checks = {
        "Skills invoked": "skill" in str(tools_used).lower() or "neo4j" in output.lower(),
        "MCP query worked": "aapl" in output.lower() or "apple" in output.lower(),
        "File written": file_exists and "SKILL_CHAIN_TEST" in file_content,
        "Got report data": "0000" in file_content or "8-k" in output.lower(),
        "Got company data": "apple" in file_content.lower() or "apple" in output.lower(),
    }

    print("\n" + "-" * 60)
    all_pass = True
    for check, passed in checks.items():
        print(f"{'✅' if passed else '❌'} {check}")
        if not passed:
            all_pass = False

    print("-" * 60)
    print(f"{'✅ SKILL CHAINING WORKS' if all_pass else '⚠️ PARTIAL'}")

    return all_pass

if __name__ == "__main__":
    asyncio.run(test())
