---
name: test-restrict-2026
description: Test if allowed-tools restriction is now enforced
allowed-tools: [Read]
context: fork
---
You have allowed-tools set to ONLY [Read]. Test if restriction is enforced:

1. Try using the Grep tool to search for "LAYER" in earnings-analysis/test-outputs/3layer-bottom.txt
2. Try using the Write tool to write "RESTRICTION_TEST" to earnings-analysis/test-outputs/restrict-2026.txt

Report for EACH tool:
- "GREP: ALLOWED" or "GREP: BLOCKED"
- "WRITE: ALLOWED" or "WRITE: BLOCKED"

If both work despite allowed-tools=[Read], say "RESTRICTION: NOT ENFORCED"
If they're blocked, say "RESTRICTION: ENFORCED"
