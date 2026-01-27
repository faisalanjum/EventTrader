#!/usr/bin/env python3
"""
Test if Task tool sub-agents spawned from SDK have TaskCreate/List/Get/Update.
"""

import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions

async def test_subagent_tasks():
    print("=== Testing Task tools via Sub-agent from SDK ===")

    os.environ["CLAUDE_CODE_TASK_LIST_ID"] = "custom-shared-list"

    results = []
    async for msg in query(
        prompt="""Use the Task tool to spawn a general-purpose sub-agent with this prompt:

"Check if you have access to TaskList, TaskCreate, TaskGet, TaskUpdate tools.
If you do, use TaskList to show all tasks.
If you see a task with subject 'MANUAL-TASK-FOR-CROSS-SESSION-TEST', report SUCCESS.
Write your findings to earnings-analysis/test-outputs/task-sharing-test/subagent-task-tools.txt"

Report what the sub-agent found.""",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            setting_sources=["project"],
            max_turns=10,
            permission_mode="bypassPermissions",
        )
    ):
        if hasattr(msg, 'content'):
            results.append(str(msg.content))

    print("=== SDK Output ===")
    for r in results[-3:]:  # Last 3 messages
        print(r[:1000] if len(r) > 1000 else r)
        print("---")

if __name__ == "__main__":
    asyncio.run(test_subagent_tasks())
