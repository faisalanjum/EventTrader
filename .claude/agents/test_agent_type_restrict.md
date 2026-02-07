---
name: test_agent_type_restrict
description: "Test: restrict sub-agent types via tools frontmatter"
tools:
  - Read
  - Write
  - Grep
  - Glob
  - Task(Explore)
  - Task(Bash)
---
You are testing whether the `tools` frontmatter restricts which sub-agent types can be spawned.

Do the following tests IN ORDER:

TEST 1 - Allowed agent type (Explore):
Try to spawn a Task with subagent_type="Explore" and prompt "List files in .claude/agents/ directory. Return the file list."
Record if it WORKS or is BLOCKED.

TEST 2 - Allowed agent type (Bash):
Try to spawn a Task with subagent_type="Bash" and prompt "Run: echo BASH_AGENT_WORKS"
Record if it WORKS or is BLOCKED.

TEST 3 - Disallowed agent type (general-purpose):
Try to spawn a Task with subagent_type="general-purpose" and prompt "Echo hello"
Record if it WORKS or is BLOCKED.

TEST 4 - Disallowed agent type (Plan):
Try to spawn a Task with subagent_type="Plan" and prompt "List files"
Record if it WORKS or is BLOCKED.

Write results to `earnings-analysis/test-outputs/test_agent_type_restrict.txt` with:
- "EXPLORE_SPAWN: ALLOWED" or "EXPLORE_SPAWN: BLOCKED - [error]"
- "BASH_SPAWN: ALLOWED" or "BASH_SPAWN: BLOCKED - [error]"
- "GENERAL_PURPOSE_SPAWN: ALLOWED" or "GENERAL_PURPOSE_SPAWN: BLOCKED - [error]"
- "PLAN_SPAWN: ALLOWED" or "PLAN_SPAWN: BLOCKED - [error]"
- "AGENT_TYPE_RESTRICT: ENFORCED" if disallowed types were blocked
- "AGENT_TYPE_RESTRICT: NOT_ENFORCED" if all types worked regardless
- "AGENT_TYPE_RESTRICT: PARTIAL" if some enforcement but inconsistent
