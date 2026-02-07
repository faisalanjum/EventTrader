---
name: test-at-session-id
description: "Test ${CLAUDE_SESSION_ID} substitution in skill content"
context: fork
---

# Session ID Substitution Test

The session ID for this execution is: "${CLAUDE_SESSION_ID}"

Write the following to `earnings-analysis/test-outputs/test-at-session-id.txt`:

```
SESSION_ID: ${CLAUDE_SESSION_ID}
IS_EMPTY: <true if the value above is literally "${CLAUDE_SESSION_ID}" or empty, false if it's a real ID>
ID_LENGTH: <character count of the session ID>
TIMESTAMP: <current ISO timestamp>
```

Then return "SESSION_ID_TEST_COMPLETE".
