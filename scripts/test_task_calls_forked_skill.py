#!/usr/bin/env python3
"""
Test: Can Task sub-agent call a Skill with context: fork?

This tests the EXACT chain your orchestrator would use:
SDK → Task (sub-agent) → Skill (context: fork) → nested skill calls
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/task-forked-skill.txt"

async def run_test():
    print("TEST: Can Task sub-agent call context:fork Skill?")
    print("=" * 60)

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    # news-impact is context: fork, and it calls /get-news internally
    prompt = f"""Test the EXACT chain for earnings workflow:

1. Use Task tool to spawn a sub-agent with this prompt:
   "Call /news-impact skill with args 'AAPL 2024-01-01 2024-01-31 3s'.
    Write 'TASK_CALLED_FORKED_SKILL: YES' to '{OUTPUT_FILE}' if /news-impact produces any output.
    Include first 10 lines of the skill output."

2. Report success/failure."""

    start = time.time()

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=20,
        )
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'name'):
                    print(f"  [{time.time()-start:.1f}s] Tool: {block.name}")
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:800]}...")

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")

    print("\n" + "=" * 60)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
            print(f"OUTPUT FILE:\n{content[:800]}")
            if "TASK_CALLED_FORKED_SKILL: YES" in content:
                print("\n✅ CONFIRMED: Task → Skill (context:fork) WORKS")
                return True
            else:
                print("\n⚠️ File exists but marker not found")
    else:
        print("❌ Output file not created")

    return False

asyncio.run(run_test())
