#!/usr/bin/env python3
"""
Empirical test: Can SDK use Task tool for parallel execution?
"""
import asyncio
import os
import time
from datetime import datetime

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_DIR = "earnings-analysis/test-outputs"
OUTPUT_FILE = f"{OUTPUT_DIR}/parallel-task-test.txt"

async def run_test():
    print("=" * 70)
    print("TEST: Can SDK use Task tool for PARALLEL execution?")
    print("=" * 70)

    start_time = time.time()

    prompt = f"""You are testing parallel execution via Task tool.

DO THIS EXACTLY:

1. First, write to '{OUTPUT_FILE}':
   ```
   PARALLEL TASK TEST
   START: {{current timestamp}}
   ```

2. Launch TWO Task agents IN PARALLEL (in the SAME message, not sequential):

   Task A: "Write 'TASK_A_DONE' with timestamp to file '{OUTPUT_DIR}/task-a.txt' and wait 3 seconds before finishing"
   Task B: "Write 'TASK_B_DONE' with timestamp to file '{OUTPUT_DIR}/task-b.txt' and wait 3 seconds before finishing"

   CRITICAL: Send BOTH Task tool calls in ONE message to run them in parallel.

3. After both complete, append to '{OUTPUT_FILE}':
   ```
   END: {{current timestamp}}
   TASK_A_FILE_EXISTS: YES/NO
   TASK_B_FILE_EXISTS: YES/NO
   ```

4. Return summary of what happened.

If parallel works: total time should be ~3-4 seconds (tasks run simultaneously)
If sequential: total time should be ~6+ seconds (tasks run one after another)
"""

    task_calls_seen = []

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            permission_mode="bypassPermissions",
            max_turns=15,
        )
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'name'):
                    print(f"  Tool: {block.name}")
                    if block.name == "Task":
                        task_calls_seen.append(datetime.now().isoformat())
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:500]}...")

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("ANALYSIS:")
    print("=" * 70)
    print(f"Total elapsed time: {elapsed:.1f} seconds")
    print(f"Task tool calls seen: {len(task_calls_seen)}")

    # Check output files
    for f in ["task-a.txt", "task-b.txt", "parallel-task-test.txt"]:
        path = f"{OUTPUT_DIR}/{f}"
        if os.path.exists(path):
            with open(path) as file:
                content = file.read()
                print(f"\n{f}:\n{content}")

    # Verdict
    print("\n" + "=" * 70)
    if elapsed < 8:
        print("VERDICT: ✅ PARALLEL execution likely worked (< 8 seconds)")
    else:
        print("VERDICT: ❌ SEQUENTIAL execution (>= 8 seconds)")
    print("=" * 70)

    return elapsed < 8

if __name__ == "__main__":
    # Clean up previous test files
    for f in ["task-a.txt", "task-b.txt", "parallel-task-test.txt"]:
        path = f"earnings-analysis/test-outputs/{f}"
        if os.path.exists(path):
            os.remove(path)

    result = asyncio.run(run_test())
    print(f"\nPARALLEL WORKS: {result}")
