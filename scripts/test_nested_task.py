#!/usr/bin/env python3
"""
Test: Can a Task sub-agent spawn MORE Task sub-agents?

Chain: SDK → Task (sub-agent) → Task (nested?) → ???
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/nested-task-test.txt"

async def run_test():
    print("TEST: Can Task sub-agent spawn nested Tasks?")
    print("=" * 60)

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    prompt = f"""Test if Task sub-agents can spawn MORE Task sub-agents.

Use the Task tool to spawn a sub-agent with this prompt:
"You are a sub-agent. Try to use the Task tool to spawn ANOTHER sub-agent.
Write to '{OUTPUT_FILE}':
- SUBAGENT_HAS_TASK_TOOL: YES or NO
- If YES, try to spawn a nested task and report result
- List ALL tools you have available"

Report what happened."""

    start = time.time()

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
                    print(f"  [{time.time()-start:.1f}s] Tool: {block.name}")
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:600]}...")

    print("\n" + "=" * 60)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
            print(f"OUTPUT FILE:\n{content}")
            if "SUBAGENT_HAS_TASK_TOOL: NO" in content:
                print("\n❌ CONFIRMED: Sub-agents CANNOT spawn nested Tasks")
            elif "SUBAGENT_HAS_TASK_TOOL: YES" in content:
                print("\n✅ Sub-agents CAN spawn nested Tasks")
    else:
        print("❌ Output file not created")

asyncio.run(run_test())
