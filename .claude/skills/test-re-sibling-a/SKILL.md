---
name: test-re-sibling-a
description: "Retest 2026-02-05: Sibling A - writes secret, checks for B"
context: fork
---
# Sibling A

1. Write "SIBLING_A_SECRET=pineapple" to earnings-analysis/test-outputs/test-re-sibling-a-secret.txt
2. Check if earnings-analysis/test-outputs/test-re-sibling-b-secret.txt exists
3. Write to earnings-analysis/test-outputs/test-re-sibling-a.txt:
   - "A_WROTE: YES"
   - "A_SAW_B_FILE: YES" or "A_SAW_B_FILE: NO"
   - "A_SAW_B_CONTEXT: YES" or "A_SAW_B_CONTEXT: NO" (do you know any variable from sibling B's context?)
