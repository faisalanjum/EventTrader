#!/usr/bin/env python3
"""
Test if a FORKED SKILL called from SDK has TaskCreate/List/Get/Update tools.

This is the critical test for K8s workflow:
K8s Pod → SDK query() → /skill (forked) → Does it have task tools?
"""

import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions

async def test_forked_skill_tasks():
    print("=== Testing Task Tools in Forked Skill Called from SDK ===")
    print()

    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = "sdk-forked-test"

    results = []
    async for msg in query(
        prompt="Run the /test-sdk-task-tools skill. This skill will check if TaskCreate/List/Get/Update tools are available in a forked skill context when called from SDK.",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=15,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(msg, 'content'):
            results.append(str(msg.content))

    print("=== SDK Output (last 3 messages) ===")
    for r in results[-3:]:
        print(r[:1500] if len(r) > 1500 else r)
        print("---")

    # Check the output file
    print("\n=== Checking output file ===")
    try:
        with open("earnings-analysis/test-outputs/sdk-task-tools-verify.txt") as f:
            print(f.read())
    except FileNotFoundError:
        print("Output file not created - checking alternate path")
        try:
            with open("earnings-analysis/test-outputs/task-sharing-test/sdk-forked-skill-task-tools.txt") as f:
                print(f.read())
        except FileNotFoundError:
            print("No output file found")

if __name__ == "__main__":
    asyncio.run(test_forked_skill_tasks())
