---
name: test-memory-autopreload-verify
description: "Test: Verify MEMORY.md auto-preload on second invocation (v2.1.50)"
memory: project
model: haiku
---
You are verifying whether the `memory` field auto-preloads MEMORY.md from a PREVIOUS invocation.

A prior agent (test-memory-autopreload) wrote "AUTOPRELOAD_CANARY=pineapple_2026_v250" to `.claude/agent-memory/test-memory-autopreload/MEMORY.md`.

Since YOUR memory scope is also `project`, your memory dir is `.claude/agent-memory/test-memory-autopreload-verify/`.

But the key test is: Does the memory SYSTEM work at all? Check:

1. Search your ENTIRE system prompt for "AUTOPRELOAD_CANARY" or "pineapple_2026"
2. Search your system prompt for any mention of "memory" instructions, "agent-memory", "MEMORY.md"
3. Check if you have ANY content that was auto-injected about memory
4. Do you see instructions telling you to read/write to a memory directory?
5. Read `.claude/agent-memory/test-memory-autopreload/MEMORY.md` manually to confirm the file exists
6. Read `.claude/agent-memory/test-memory-autopreload-verify/MEMORY.md` if it exists
7. Write a NEW canary: Write to `.claude/agent-memory/test-memory-autopreload-verify/MEMORY.md`:
   ```
   VERIFY_CANARY=mango_verify_2026
   ```

Write results to `earnings-analysis/test-outputs/test-memory-autopreload-verify.txt`:
```
MEMORY_VERIFY_TEST=v2.1.50
MEMORY_SCOPE=project
CANARY_IN_SYSTEM_PROMPT=YES|NO
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO - [exact text if yes]
MEMORY_DIR_REFERENCED=YES|NO - [path if yes]
PRIOR_CANARY_FILE_EXISTS=YES|NO - [content]
OWN_MEMORY_DIR_EXISTS=YES|NO
MEMORY_WRITE=WORKS|FAILED
AUTOPRELOAD=CONFIRMED_WORKING|STILL_BROKEN
```
