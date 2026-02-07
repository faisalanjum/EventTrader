---
name: test-re-skill-tries-task
description: "Retest 2026-02-05: Child skill tries to use Task tool"
context: fork
---
# Test: Can a forked skill use the Task tool (sub-agent spawning)?

Try to use the Task tool (NOT TaskCreate — the one that spawns sub-agents with subagent_type parameter) to spawn a general-purpose agent with prompt "Reply with NESTED_TASK_SUCCESS".

- If Task tool works: reply "SKILL_TASK: WORKS - [agent response]"
- If Task tool is not available: reply "SKILL_TASK: BLOCKED - Task tool not in my tool list"

Also list every tool name you have (just names, comma-separated).
