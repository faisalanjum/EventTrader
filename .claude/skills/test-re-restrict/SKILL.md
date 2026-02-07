---
name: test-re-restrict
description: "Retest 2026-02-05: Does allowed-tools restrict tool access?"
allowed-tools:
  - Read
context: fork
---
# Test: allowed-tools restriction

Your allowed-tools is set to ONLY [Read]. Test if other tools work:

1. Try Grep for "LAYER3" in earnings-analysis/test-outputs/3layer-bottom.txt
2. Try Write to create earnings-analysis/test-outputs/test-re-restrict.txt

Write results:
- "GREP: ALLOWED" or "GREP: BLOCKED"
- "WRITE: ALLOWED" or "WRITE: BLOCKED"
- "RESTRICTION: ENFORCED" if tools were blocked, "RESTRICTION: NOT ENFORCED" if they worked
