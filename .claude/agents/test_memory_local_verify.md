---
name: test_memory_local_verify
description: "Test: verify memory: local persists from previous invocation"
memory: local
---
You are verifying whether `memory: local` persisted from a previous agent invocation.

1. Check your system prompt for any MEMORY.md content (should be auto-loaded if previous agent wrote it)
2. Check if a file exists at `.claude/agent-memory-local/test-memory-local/MEMORY.md`
3. Also check `.claude/agent-memory-local/test-memory-local-verify/MEMORY.md`

Write your results to `earnings-analysis/test-outputs/test_memory_local_verify.txt` with:
- "MEMORY_SCOPE: local"
- "MEMORY_IN_PROMPT: YES - [content]" or "MEMORY_IN_PROMPT: NO"
- "OTHER_AGENT_MEMORY_FILE: YES - [content]" or "OTHER_AGENT_MEMORY_FILE: NO"
- "OWN_MEMORY_FILE: YES - [content]" or "OWN_MEMORY_FILE: NO"
- "LOCAL_MEMORY_PERSIST: WORKS" or "LOCAL_MEMORY_PERSIST: NOT_WORKING"
