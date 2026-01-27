#!/usr/bin/env python3
"""
Test: Can we get TaskCreate/TaskList by changing CLAUDE_CODE_ENTRYPOINT?
"""
import asyncio
import os

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

async def test_entrypoint(entrypoint_value: str, output_file: str):
    print(f"\nTesting CLAUDE_CODE_ENTRYPOINT={entrypoint_value}")
    print("-" * 60)

    # Override the entrypoint
    os.environ["CLAUDE_CODE_ENTRYPOINT"] = entrypoint_value

    async for message in query(
        prompt=f"""Write to '{output_file}':
1. ENTRYPOINT: {entrypoint_value}
2. TaskList available? Try it and report YES/NO
3. TaskCreate available? Try it and report YES/NO
4. Count of available tools
Be concise.""",
        options=ClaudeAgentOptions(
            tools={"type": "preset", "preset": "claude_code"},
            permission_mode="bypassPermissions",
            max_turns=5,
            env={"CLAUDE_CODE_ENTRYPOINT": entrypoint_value},  # Also pass via env option
        )
    ):
        if hasattr(message, 'result'):
            print(f"Result: {message.result[:200]}...")

    if os.path.exists(output_file):
        with open(output_file) as f:
            content = f.read()
            print(f"Output:\n{content}")
            return "YES" in content and "TaskList" in content
    return False

async def main():
    tests = [
        ("cli", "earnings-analysis/test-outputs/entrypoint-cli.txt"),
        ("interactive", "earnings-analysis/test-outputs/entrypoint-interactive.txt"),
        ("terminal", "earnings-analysis/test-outputs/entrypoint-terminal.txt"),
        ("", "earnings-analysis/test-outputs/entrypoint-empty.txt"),
    ]

    results = {}
    for entrypoint, output_file in tests:
        try:
            results[entrypoint] = await test_entrypoint(entrypoint, output_file)
        except Exception as e:
            print(f"Error with {entrypoint}: {e}")
            results[entrypoint] = False

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    for entrypoint, has_tools in results.items():
        status = "✅ HAS TaskList" if has_tools else "❌ NO TaskList"
        print(f"  CLAUDE_CODE_ENTRYPOINT='{entrypoint}': {status}")

asyncio.run(main())
