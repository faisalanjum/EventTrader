---
name: test-memory-user-scope
description: "Test: Does memory: user scope work and auto-preload? (v2.1.50)"
memory: user
model: opus
---
You are testing the `memory: user` scope (stores at ~/.claude/agent-memory/).

1. Search your system prompt for any memory-related instructions or content
2. Check if `~/.claude/agent-memory/test-memory-user-scope/` exists
3. Check if `~/.claude/agent-memory/test-memory-user-scope/MEMORY.md` exists
4. Write to `~/.claude/agent-memory/test-memory-user-scope/MEMORY.md`:
   ```
   USER_SCOPE_CANARY=grape_user_2026
   ```
5. Read it back to confirm

Write results to `earnings-analysis/test-outputs/test-memory-user-scope.txt`:
```
MEMORY_USER_SCOPE_TEST=v2.1.50
MEMORY_SCOPE=user
MEMORY_DIR_PATH=[path]
MEMORY_DIR_EXISTS=YES|NO
MEMORY_INSTRUCTIONS_IN_PROMPT=YES|NO - [details]
CANARY_IN_PROMPT=YES|NO
MEMORY_WRITE=WORKS|FAILED
MEMORY_READ=[content or FAILED]
USER_SCOPE=WORKS|NOT_WORKING
```
