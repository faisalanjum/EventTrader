---
name: test-re-memory-agent
description: "Retest: memory field for persistent agent memory"
memory: project
---
You are testing the memory feature.

1. Check if you have a memory directory or MEMORY.md content in your system prompt
2. Write to your memory: "MEMORY_TEST_VALUE=banana_2026"
3. Read back from your memory to confirm it was written

Reply with:
- "MEMORY_DIR: [path if visible]" or "MEMORY_DIR: NOT_VISIBLE"
- "MEMORY_WRITE: WORKS" or "MEMORY_WRITE: FAILED"
- "MEMORY_READ: [content]" or "MEMORY_READ: FAILED"
- "AGENT_MEMORY: WORKS" or "AGENT_MEMORY: NOT_WORKING"
