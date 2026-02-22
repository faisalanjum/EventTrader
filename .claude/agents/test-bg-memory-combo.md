---
name: test-bg-memory-combo
description: "Test: Does memory work combined with background: true? (v2.1.50)"
background: true
memory: project
model: haiku
---
You are testing whether `memory` and `background: true` can coexist in the same agent.

1. Check if memory instructions appear in your system prompt
2. Check if `.claude/agent-memory/test-bg-memory-combo/` exists or gets created
3. Write to `.claude/agent-memory/test-bg-memory-combo/MEMORY.md`:
   ```
   BG_MEMORY_CANARY=banana_bg_v250
   ```
4. Read it back

Write results to `earnings-analysis/test-outputs/test-bg-memory-combo.txt`:
```
BG_MEMORY_COMBO_TEST=v2.1.50
BACKGROUND=true
MEMORY_SCOPE=project
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO
MEMORY_DIR_CREATED=YES|NO
MEMORY_WRITE=WORKS|FAILED
MEMORY_READ=[content or FAILED]
BG_MEMORY_COMBO=WORKS|NOT_WORKING
```
