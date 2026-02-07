---
name: test-re-3layer-top
description: "Retest 2026-02-05: 3-layer nesting L1"
allowed-tools:
  - Skill
  - Write
context: fork
---
# Layer 1 (Top)

1. SECRET = "alpha"
2. Call /test-re-3layer-mid
3. Write to earnings-analysis/test-outputs/test-re-3layer-top.txt:
   - L1_SECRET: alpha
   - L2_RETURNED: [what mid returned]
   - "3LAYER: WORKS" or "3LAYER: FAILED"
