#!/usr/bin/env python3
"""
Test: Can Task sub-agent call MULTIPLE Skills with different arguments?
And do results come back to the sub-agent?
"""
import asyncio
import os
import time

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

OUTPUT_FILE = "earnings-analysis/test-outputs/subagent-multi-skill.txt"

async def run_test():
    print("TEST: Can Task sub-agent call multiple Skills?")
    print("=" * 60)

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    prompt = f"""Use the Task tool to spawn a sub-agent with this prompt:

"You are testing if you can call multiple Skills with different arguments.

1. Call /neo4j-entity skill with args 'AAPL' - note the result
2. Call /neo4j-entity skill with args 'MSFT' - note the result
3. Call /neo4j-entity skill with args 'GOOGL' - note the result

Write to '{OUTPUT_FILE}':
- SKILL_CALL_1: YES/NO (and ticker found)
- SKILL_CALL_2: YES/NO (and ticker found)
- SKILL_CALL_3: YES/NO (and ticker found)
- TOTAL_SKILLS_CALLED: count
- ALL_RESULTS_RETURNED_TO_ME: YES/NO"

Report the sub-agent's findings."""

    start = time.time()
    skill_calls = 0

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
                    tool_name = block.name
                    print(f"  [{time.time()-start:.1f}s] Tool: {tool_name}")
                    if tool_name == "Skill":
                        skill_calls += 1
        if hasattr(message, 'result'):
            print(f"\nResult: {message.result[:800]}...")

    print(f"\nTotal Skill calls observed: {skill_calls}")
    print("\n" + "=" * 60)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            content = f.read()
            print(f"OUTPUT FILE:\n{content}")
    else:
        print("❌ Output file not created")

asyncio.run(run_test())
