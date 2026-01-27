#!/usr/bin/env python3
"""
Test: When sub-agent calls multiple context:fork skills, are they SEQUENTIAL?

Uses test-parallel-a and test-parallel-b (both context: fork, each has 3s sleep)
If sequential: total time ~6+ seconds (3s + 3s)
If parallel: total time ~3 seconds
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/subagent-forked-timing.txt"

async def run_test():
    print("TEST: Are context:fork skills SEQUENTIAL inside sub-agent?")
    print("=" * 60)

    # Clean up
    for f in [OUTPUT_FILE, "/tmp/parallel-a-time.txt", "/tmp/parallel-b-time.txt",
              "/tmp/parallel-a-done.txt", "/tmp/parallel-b-done.txt"]:
        if os.path.exists(f):
            os.remove(f)

    prompt = f"""Use the Task tool to spawn a sub-agent with this prompt:

"Test if context:fork skills run sequentially or parallel inside a sub-agent.

1. Record start time: date +%s.%N > /tmp/subagent-start.txt
2. Call Skill /test-parallel-a (this has context:fork and 3s sleep)
3. Call Skill /test-parallel-b (this has context:fork and 3s sleep)
4. Record end time: date +%s.%N > /tmp/subagent-end.txt

Write to '{OUTPUT_FILE}':
- START_TIME: (from /tmp/subagent-start.txt)
- END_TIME: (from /tmp/subagent-end.txt)
- ELAPSED: (end - start)
- VERDICT: SEQUENTIAL if elapsed >= 6s, PARALLEL if elapsed < 5s"

Report the timing results."""

    start = time.time()

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=25,
        )
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'name'):
                    print(f"  [{time.time()-start:.1f}s] Tool: {block.name}")
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:800]}...")

    elapsed = time.time() - start
    print(f"\nTotal wall time: {elapsed:.1f}s")

    print("\n" + "=" * 60)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            print(f"OUTPUT FILE:\n{f.read()}")

    # Also check the timestamp files
    for f in ["/tmp/subagent-start.txt", "/tmp/subagent-end.txt",
              "/tmp/parallel-a-time.txt", "/tmp/parallel-b-time.txt"]:
        if os.path.exists(f):
            with open(f) as file:
                print(f"{f}: {file.read().strip()}")

asyncio.run(run_test())
