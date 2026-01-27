#!/usr/bin/env python3
"""
Test: Can Task tool run forked skills in PARALLEL?

Chain: SDK → 2x Task (parallel) → each calls context:fork skill
Expected: Both skills run simultaneously (3s sleep each, total ~6s not 10s+)
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

async def run_test():
    print("TEST: Task → parallel forked skills")
    print("=" * 60)

    # Clean up
    for f in ["/tmp/parallel-a-time.txt", "/tmp/parallel-b-time.txt",
              "/tmp/parallel-a-done.txt", "/tmp/parallel-b-done.txt"]:
        if os.path.exists(f):
            os.remove(f)

    prompt = """Execute TWO Task tool calls IN PARALLEL (both in the same message):

Task 1: "Call skill /test-parallel-a using the Skill tool. Wait for it to complete."
Task 2: "Call skill /test-parallel-b using the Skill tool. Wait for it to complete."

CRITICAL: Send BOTH Task calls in ONE message to run them in parallel.

After both complete, read these files and report their timestamps:
- /tmp/parallel-a-time.txt
- /tmp/parallel-b-time.txt

If parallel: timestamps should be within 1 second of each other
If sequential: timestamps should be 3+ seconds apart (due to sleep)"""

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
            print(f"\nResult: {message.result[:600]}...")

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")

    # Check timestamps
    print("\n" + "=" * 60)
    times = {}
    for name in ["a", "b"]:
        path = f"/tmp/parallel-{name}-time.txt"
        if os.path.exists(path):
            with open(path) as f:
                times[name] = float(f.read().strip())
                print(f"parallel-{name}-time.txt: {times[name]}")

    if "a" in times and "b" in times:
        diff = abs(times["a"] - times["b"])
        print(f"\nTimestamp difference: {diff:.2f} seconds")
        if diff < 2:
            print("✅ PARALLEL: Skills started within 2s of each other")
        else:
            print(f"❌ SEQUENTIAL: Skills started {diff:.1f}s apart")
    else:
        print("❌ Could not read both timestamp files")

asyncio.run(run_test())
