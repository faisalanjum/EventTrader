---
name: test-re-parallel-parent
description: "Retest 2026-02-05: Are Skill calls parallel or sequential?"
allowed-tools:
  - Skill
  - Write
  - Bash
context: fork
---
# Test: Parallel Skill execution

Call BOTH children in the SAME response (try to make them parallel):
1. Call /test-re-parallel-a
2. Call /test-re-parallel-b

After both complete, write to earnings-analysis/test-outputs/test-re-parallel-parent.txt:
- Child A timestamp
- Child B timestamp
- Time gap between them
- "PARALLEL: YES" if gap < 2 seconds
- "PARALLEL: NO (SEQUENTIAL)" if gap > 2 seconds
