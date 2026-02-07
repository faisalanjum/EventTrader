---
name: test-re-task-in-fork
description: "Retest 2026-02-05: Can forked skill use Task tool (sub-agent spawning)?"
context: fork
---
# Test: Task tool in forked context

Try to use the Task tool to spawn a sub-agent:
- Use the Task tool with subagent_type "general-purpose" and prompt "Reply with TASK_SPAWN_SUCCESS"
- If it works, write "TASK_IN_FORK: WORKS" to earnings-analysis/test-outputs/test-re-task-in-fork.txt
- If you don't have a Task tool (only TaskCreate/List/Get/Update), write "TASK_IN_FORK: BLOCKED" to the file

Also list every tool name you have access to (just names, one per line) in the same file.
