---
name: test-re-sibling-b
description: "Retest 2026-02-05: Sibling B - writes secret, checks for A"
context: fork
---
# Sibling B

1. Write "SIBLING_B_SECRET=mango" to earnings-analysis/test-outputs/test-re-sibling-b-secret.txt
2. Check if earnings-analysis/test-outputs/test-re-sibling-a-secret.txt exists and read it
3. Write to earnings-analysis/test-outputs/test-re-sibling-b.txt:
   - "B_WROTE: YES"
   - "B_SAW_A_FILE: YES" or "B_SAW_A_FILE: NO"
   - If YES, include A's secret content
   - "B_SAW_A_CONTEXT: YES" or "B_SAW_A_CONTEXT: NO"
