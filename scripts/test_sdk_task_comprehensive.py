#!/usr/bin/env python3
"""
Comprehensive SDK Task Tools Test

Tests multiple scenarios to understand why SDK might behave differently from CLI.
"""
import asyncio
import os
import sys
from datetime import datetime

os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions

async def test_1_direct_skill():
    """Test 1: Call the direct test skill that just CALLS tools without introspection"""
    print("\n" + "="*70)
    print("TEST 1: Direct skill test (no introspection)")
    print("="*70)

    output_file = "earnings-analysis/test-outputs/direct-test-SDK.txt"
    if os.path.exists(output_file):
        os.remove(output_file)

    async for message in query(
        prompt="Run /test-task-direct SDK",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=10,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            print(f"Output: {str(message.result)[:500]}")

    if os.path.exists(output_file):
        with open(output_file) as f:
            print(f"\n--- {output_file} ---")
            print(f.read())
    else:
        print(f"WARNING: {output_file} not created")


async def test_2_main_conversation_tasklist():
    """Test 2: Try to use TaskList directly in main SDK conversation (not forked)"""
    print("\n" + "="*70)
    print("TEST 2: TaskList in main SDK conversation (not forked skill)")
    print("="*70)

    async for message in query(
        prompt="""Use the TaskList tool to list all tasks.
Just call TaskList directly - don't check if it's available first.
If it works, tell me how many tasks you found.
If it fails, paste the exact error message.""",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=5,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            print(f"Output: {message.result}")


async def test_3_main_conversation_taskcreate():
    """Test 3: Try to use TaskCreate directly in main SDK conversation"""
    print("\n" + "="*70)
    print("TEST 3: TaskCreate in main SDK conversation")
    print("="*70)

    timestamp = datetime.now().strftime("%H%M%S")

    async for message in query(
        prompt=f"""Use the TaskCreate tool to create a task with:
- subject: "SDK-MAIN-TEST-{timestamp}"
- description: "Testing TaskCreate from SDK main conversation"

Just call TaskCreate directly. If it works, tell me the task ID.
If it fails, paste the exact error message.""",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=5,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            print(f"Output: {message.result}")


async def test_4_list_available_tools():
    """Test 4: Ask Claude to list what tools it has available"""
    print("\n" + "="*70)
    print("TEST 4: List available tools in SDK session")
    print("="*70)

    async for message in query(
        prompt="""List ALL the tools you have available in this session.
Specifically, do you have any of these tools?
- TaskCreate
- TaskList
- TaskGet
- TaskUpdate
- Task (the sub-agent spawner)
- TodoWrite

Just list what you actually have access to.""",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=3,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(message, 'result'):
            print(f"Output: {message.result}")


async def test_5_different_permission_mode():
    """Test 5: Try with different permission mode"""
    print("\n" + "="*70)
    print("TEST 5: TaskList with permission_mode='acceptEdits'")
    print("="*70)

    try:
        async for message in query(
            prompt="Use TaskList to list all tasks. Just call it directly.",
            options=ClaudeAgentOptions(
                model="claude-sonnet-4-20250514",
                setting_sources=["project"],
                max_turns=5,
                permission_mode="acceptEdits",
            )
        ):
            if hasattr(message, 'result'):
                print(f"Output: {message.result}")
    except Exception as e:
        print(f"Error: {e}")


async def main():
    print("="*70)
    print("COMPREHENSIVE SDK TASK TOOLS TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)

    await test_4_list_available_tools()  # First check what tools are available
    await test_2_main_conversation_tasklist()  # Then try in main conversation
    await test_3_main_conversation_taskcreate()  # Try TaskCreate in main
    await test_1_direct_skill()  # Try via forked skill
    # await test_5_different_permission_mode()  # Try different permission

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
