---
name: test-re-memory-verify
description: "Retest: verify memory persists from previous invocation"
memory: project
---
You are verifying whether memory persisted from a previous agent invocation.

1. Check your system prompt for any MEMORY.md content
2. Check if a file exists at .claude/agent-memory/test-re-memory-agent/MEMORY.md
3. Also check .claude/agent-memory/test-re-memory-verify/MEMORY.md

Reply with:
- "MEMORY_IN_PROMPT: YES - [content]" or "MEMORY_IN_PROMPT: NO"
- "MEMORY_FILE_EXISTS: YES - [content]" or "MEMORY_FILE_EXISTS: NO"
- "MEMORY_PERSIST: WORKS" or "MEMORY_PERSIST: NOT_WORKING"
