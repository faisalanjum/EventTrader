#!/usr/bin/env python3
"""
Test if CLAUDE_CODE_TASK_LIST_ID works with Claude Agent SDK.

Expected: Session should see the manually created task in custom-shared-list.
"""

import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions

async def test_custom_task_list():
    print("=== Testing CLAUDE_CODE_TASK_LIST_ID with SDK ===")
    print("Task list ID: custom-shared-list")
    print()

    # Set env var before SDK call
    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = "custom-shared-list"

    results = []
    async for msg in query(
        prompt="Use TaskList to show all tasks. Report what you see. If you see a task with subject 'MANUAL-TASK-FOR-CROSS-SESSION-TEST', then the cross-session sharing works!",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=5,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(msg, 'content'):
            results.append(str(msg.content))

    # Print results
    print("=== SDK Session Output ===")
    for r in results:
        print(r[:500] if len(r) > 500 else r)

    # Also write to file for verification
    with open("earnings-analysis/test-outputs/task-sharing-test/sdk-task-list-result.txt", "w") as f:
        f.write("CLAUDE_CODE_TASK_LIST_ID=custom-shared-list\n\n")
        f.write("\n".join(results))

    print("\n=== Output written to sdk-task-list-result.txt ===")

if __name__ == "__main__":
    asyncio.run(test_custom_task_list())
