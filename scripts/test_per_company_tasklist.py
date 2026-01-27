#!/usr/bin/env python3
"""
Test per-company task list isolation using CLAUDE_CODE_TASK_LIST_ID

This tests if we can run separate SDK queries with different task list IDs
to achieve per-company isolation.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_task_list_for_company(ticker: str):
    """Run a query with company-specific task list ID"""

    # Set environment variable BEFORE importing SDK
    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = f"{ticker}-earnings"

    print(f"\n{'='*50}")
    print(f"Testing task list for: {ticker}")
    print(f"CLAUDE_CODE_TASK_LIST_ID = {os.environ.get('CLAUDE_CODE_TASK_LIST_ID')}")
    print(f"{'='*50}")

    try:
        from claude_agent_sdk import query, ClaudeAgentOptions

        # Simple query to create a task and list tasks
        prompt = f"""
        Do the following IN ORDER:
        1. Use TaskList to see current tasks
        2. Use TaskCreate to create a task with subject: "{ticker}-TEST-TASK"
        3. Use TaskList again to verify
        4. Report: How many tasks total? What are their subjects?

        Do NOT use any other tools. Only TaskList and TaskCreate.
        """

        result_text = ""
        async for event in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model="claude-sonnet-4-20250514",
                setting_sources=["project"],
                max_turns=10,
                permission_mode="bypassPermissions",
            )
        ):
            if hasattr(event, 'message') and hasattr(event.message, 'content'):
                for block in event.message.content:
                    if hasattr(block, 'text'):
                        result_text = block.text

        print(f"Result for {ticker}:")
        print(result_text[:500] if len(result_text) > 500 else result_text)
        return True

    except Exception as e:
        print(f"Error for {ticker}: {e}")
        return False

async def main():
    """Test task list isolation for multiple companies"""

    print("Testing per-company task list isolation...")
    print("Expected: Each company gets its own task list")

    # Test with two companies
    companies = ["AAPL", "MSFT"]

    for ticker in companies:
        await test_task_list_for_company(ticker)

    # Check task list directories created
    tasks_dir = Path.home() / ".claude" / "tasks"
    print(f"\n{'='*50}")
    print("Task list directories:")
    print(f"{'='*50}")

    if tasks_dir.exists():
        for d in tasks_dir.iterdir():
            if d.is_dir():
                print(f"  {d.name}")
    else:
        print("  No tasks directory found")

if __name__ == "__main__":
    asyncio.run(main())
