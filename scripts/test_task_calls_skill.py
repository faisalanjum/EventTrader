#!/usr/bin/env python3
"""
Test: Can Task sub-agent call Skills (context: fork)?

Chain: SDK → Task sub-agent → Skill (/neo4j-schema) → result
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/task-calls-skill.txt"

async def run_test():
    print("TEST: Can Task sub-agent call a Skill?")
    print("=" * 60)

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    prompt = f"""Test if Task sub-agents can call Skills.

1. Use the Task tool to spawn a sub-agent with this prompt:
   "Call the /neo4j-schema skill using the Skill tool. Write the first 5 lines of output to '{OUTPUT_FILE}' with header 'TASK_SUBAGENT_CALLED_SKILL: YES' if it worked."

2. Wait for the Task to complete.

3. Report what happened."""

    start = time.time()

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            setting_sources=["project"],  # Load skills from .claude/skills/
            permission_mode="bypassPermissions",
            max_turns=15,
        )
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'name'):
                    print(f"  [{time.time()-start:.1f}s] Tool: {block.name}")
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:500]}...")

    print("\n" + "=" * 60)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
            print(f"OUTPUT FILE:\n{content[:500]}")
            if "TASK_SUBAGENT_CALLED_SKILL: YES" in content:
                print("\n✅ CONFIRMED: Task sub-agent CAN call Skills")
                return True
    else:
        print("❌ Output file not created")

    return False

asyncio.run(run_test())
