---
name: test-memory-autopreload
description: "Test: Does memory auto-preload MEMORY.md into system prompt? (v2.1.50 retest)"
memory: project
model: haiku
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---
You are testing whether the `memory` field now auto-preloads MEMORY.md into your system prompt.

The official docs (Feb 2026) NOW say:
- "The subagent's system prompt includes instructions for reading and writing to the memory directory."
- "The subagent's system prompt also includes the first 200 lines of MEMORY.md"
- "Read, Write, and Edit tools are automatically enabled"

Previously (v2.1.34-v2.1.45) this was NOT working. Let's retest.

PHASE 1 — Check for auto-preloaded content:

1. Search your ENTIRE system prompt / context for the string "AUTOPRELOAD_CANARY"
2. Search for any mention of "agent-memory" or "memory directory" or "MEMORY.md" in your instructions
3. Check if you were given explicit instructions about reading/writing memory
4. Check if you can see a memory directory path

PHASE 2 — Write a canary value:

5. Write to `.claude/agent-memory/test-memory-autopreload/MEMORY.md`:
```
AUTOPRELOAD_CANARY=pineapple_2026_v250
WRITTEN_AT={timestamp}
PURPOSE=Testing if this content appears in system prompt on next invocation
```

6. Read it back to confirm the write worked.

PHASE 3 — Report:

7. Write to `earnings-analysis/test-outputs/test-memory-autopreload.txt`:
```
MEMORY_AUTOPRELOAD_TEST=v2.1.50
MEMORY_SCOPE=project
MEMORY_DIR_PATH=[path if visible]
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO - [what you see]
AUTOPRELOAD_CANARY_IN_PROMPT=YES|NO
MEMORY_DIR_MENTIONED=YES|NO
MEMORY_WRITE=WORKS|FAILED
MEMORY_READ=[content or FAILED]
PHASE=1_WRITE_CANARY
NEXT_STEP=Run test-memory-autopreload-verify to check if canary appears
```
