---
name: test-v176-stop-on-agent
description: Test whether SubagentStop fires for Task-spawned agent
tools:
  - Write
  - Read
  - Bash
---

Write the text "AGENT_DONE" to `/tmp/test_agent_output.txt`. Then stop.
