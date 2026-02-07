---
name: test_memory_local
description: "Test: memory: local scope creates agent-memory-local directory"
memory: local
---
You are testing the `memory: local` feature.

1. Check if you have a memory directory or MEMORY.md content already in your system prompt
2. Write a file called MEMORY.md to your memory directory with content: "MEMORY_LOCAL_TEST=mango_2026_local"
3. Read back from your memory directory to confirm the file was written
4. Check if the directory `.claude/agent-memory-local/test-memory-local/` exists

Write your results to `earnings-analysis/test-outputs/test_memory_local.txt` with:
- "MEMORY_SCOPE: local"
- "MEMORY_PRELOAD: YES - [content]" or "MEMORY_PRELOAD: NO"
- "MEMORY_DIR_CREATED: YES" or "MEMORY_DIR_CREATED: NO"
- "MEMORY_WRITE: WORKS" or "MEMORY_WRITE: FAILED"
- "MEMORY_READ: [content]" or "MEMORY_READ: FAILED"
- "MEMORY_LOCAL: WORKS" or "MEMORY_LOCAL: NOT_WORKING"
