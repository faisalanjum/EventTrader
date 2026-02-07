---
name: test-disallow-2026
description: Test if disallowedTools blocks tools
disallowedTools: [Write, Bash]
context: fork
---
You have disallowedTools set to [Write, Bash]. Test if blocking works:

1. Try using Write to create earnings-analysis/test-outputs/disallow-2026.txt with content "DISALLOW_TEST"
2. Try using Bash to run "echo hello"

Report for EACH:
- "WRITE: BLOCKED" or "WRITE: ALLOWED"
- "BASH: BLOCKED" or "BASH: ALLOWED"

If both work despite disallowedTools, say "DISALLOWED_TOOLS: NOT ENFORCED"
If they're blocked, say "DISALLOWED_TOOLS: ENFORCED"
