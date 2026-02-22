---
name: test-mem-same-agent-verify
description: "Test: Does memory auto-preload for the SAME agent on second invocation? (v2.1.50)"
memory: project
model: opus
---
You are testing whether the `memory: project` field auto-preloads MEMORY.md into your system prompt.

A PRIOR invocation of THIS EXACT AGENT wrote a canary value to your memory directory.

CRITICAL TEST: Check for auto-preloaded content

1. Search your ENTIRE context/system prompt for the string "SAME_AGENT_CANARY"
2. Search for "watermelon_same_v250"
3. Search for ANY mention of "agent-memory" in your instructions
4. Search for ANY instructions about reading/writing memory
5. Do you see a memory directory path mentioned anywhere?
6. Check if `.claude/agent-memory/test-mem-same-agent-verify/MEMORY.md` exists

If the file DOES NOT exist yet (first run), write the canary:
7. Write to `.claude/agent-memory/test-mem-same-agent-verify/MEMORY.md`:
```
SAME_AGENT_CANARY=watermelon_same_v250
WRITTEN_AT=first_invocation
PURPOSE=Test auto-preload on second invocation of SAME agent
```

Write results to `earnings-analysis/test-outputs/test-mem-same-agent-verify.txt`:
```
MEM_SAME_AGENT_TEST=v2.1.50
MEMORY_SCOPE=project
INVOCATION=FIRST|SECOND
CANARY_IN_PROMPT=YES|NO
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO - [exact text if any]
MEMORY_FILE_EXISTS=YES|NO
MEMORY_FILE_CONTENT=[content if exists]
AUTOPRELOAD=CONFIRMED_WORKING|STILL_BROKEN|FIRST_RUN_WROTE_CANARY
```
