#!/usr/bin/env python3
"""
Clean parallel test - just check if two Task calls execute concurrently
"""
import asyncio
import os
import time
from datetime import datetime

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_DIR = "earnings-analysis/test-outputs"

async def run_test():
    print("CLEAN PARALLEL TEST")
    print("=" * 60)

    # Clean up
    for f in ["par-a.txt", "par-b.txt"]:
        path = f"{OUTPUT_DIR}/{f}"
        if os.path.exists(path):
            os.remove(path)

    prompt = f"""Execute these TWO Task tool calls IN PARALLEL (both in same response):

Task 1: subagent_type="Bash", prompt="sleep 5 && echo TASK_A_$(date +%H:%M:%S) > {OUTPUT_DIR}/par-a.txt"
Task 2: subagent_type="Bash", prompt="sleep 5 && echo TASK_B_$(date +%H:%M:%S) > {OUTPUT_DIR}/par-b.txt"

CRITICAL: Call BOTH Task tools in the SAME message to run them in parallel.

After both complete, read both files and report their timestamps."""

    start = time.time()

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            permission_mode="bypassPermissions",
            max_turns=10,
        )
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'name'):
                    print(f"  [{time.time()-start:.1f}s] Tool: {block.name}")

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")

    # Check files
    for f in ["par-a.txt", "par-b.txt"]:
        path = f"{OUTPUT_DIR}/{f}"
        if os.path.exists(path):
            with open(path) as file:
                print(f"{f}: {file.read().strip()}")

    print("\n" + "=" * 60)
    if elapsed < 12:
        print("✅ PARALLEL: Both 5s sleeps completed in < 12s total")
    else:
        print("❌ SEQUENTIAL: Took >= 12s (5s + 5s + overhead)")
    print("=" * 60)

asyncio.run(run_test())
