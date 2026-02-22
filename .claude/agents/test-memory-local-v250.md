---
name: test-memory-local-v250
description: "Test: Does memory: local scope work and auto-preload? (v2.1.50 retest)"
memory: local
model: haiku
---
You are testing the `memory: local` scope (stores at .claude/agent-memory-local/).

This is a RETEST of a feature that was BROKEN in v2.1.34-v2.1.45. The official docs now claim it works.

1. FIRST: Search your ENTIRE system prompt / context for:
   - Any mention of "memory" or "MEMORY.md" or "agent-memory"
   - Any instructions about reading/writing to a memory directory
   - Any auto-preloaded content
   - The string "MEMORY_LOCAL_TEST" (from a previous test that wrote this)

2. Check if `.claude/agent-memory-local/test-memory-local-v250/` exists
3. Check if `.claude/agent-memory-local/test-memory-local-v250/MEMORY.md` exists
4. Also check the OLD test's memory: `.claude/agent-memory-local/test_memory_local/MEMORY.md`
5. Write to `.claude/agent-memory-local/test-memory-local-v250/MEMORY.md`:
   ```
   LOCAL_SCOPE_CANARY=kiwi_local_v250
   ```
6. Read it back

Write results to `earnings-analysis/test-outputs/test-memory-local-v250.txt`:
```
MEMORY_LOCAL_SCOPE_TEST=v2.1.50
MEMORY_SCOPE=local
MEMORY_DIR_PATH=[path]
MEMORY_DIR_EXISTS=YES|NO
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO - [exact text]
OLD_CANARY_IN_PROMPT=YES|NO
NEW_DIR_CREATED=YES|NO
MEMORY_WRITE=WORKS|FAILED
MEMORY_READ=[content or FAILED]
OLD_MEMORY_EXISTS=YES|NO - [content of old test memory]
LOCAL_SCOPE=WORKS|NOT_WORKING
AUTOPRELOAD_STATUS=WORKING|STILL_BROKEN
```
