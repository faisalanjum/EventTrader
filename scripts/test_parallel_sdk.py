#!/usr/bin/env python3
"""
Test if Task tool (parallel subagent spawning) works in SDK context.
"""
import asyncio
import os

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    print("=" * 70)
    print("TEST: Task tool (parallel subagents) in SDK context")
    print("=" * 70)

    output_file = "earnings-analysis/test-outputs/parallel-test-SDK.txt"
    if os.path.exists(output_file):
        os.remove(output_file)

    async for message in query(
        prompt="Run /test-parallel-sdk SDK",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=15,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            print(f"Output: {str(message.result)[:500]}")

    # Check result
    if os.path.exists(output_file):
        with open(output_file) as f:
            print(f"\n--- {output_file} ---")
            print(f.read())
    else:
        print(f"WARNING: {output_file} not created")

if __name__ == "__main__":
    asyncio.run(main())
