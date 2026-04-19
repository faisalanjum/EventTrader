---
name: test-v1107-parallel-parent
description: "v2.1.107 retest: parallel skill execution - call two children simultaneously and measure gap"
allowed-tools:
  - Skill
  - Bash
  - Write
  - Read
context: fork
---

# Test: Parallel Skill execution (v2.1.107)

## Hypothesis
Per Infrastructure.md, Skill calls are SEQUENTIAL not parallel (still broken as of v2.1.100).
v2.1.101-107 changelogs do NOT mention fixing this.

## Steps

1. Invoke BOTH children IN THE SAME RESPONSE as separate Skill calls:
   - `Skill({skill:"test-v1107-parallel-a"})`
   - `Skill({skill:"test-v1107-parallel-b"})`
   
2. After both return, Read both output files:
   - `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-parallel-a.txt`
   - `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-parallel-b.txt`

3. Compute `GAP = |ts_b - ts_a|` in seconds (floats).

4. Write to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-parallel-parent.txt`:
   - Line 1: `TIMESTAMP_A=<ts_a>`
   - Line 2: `TIMESTAMP_B=<ts_b>`
   - Line 3: `GAP_SECONDS=<gap>`
   - Line 4: `VERDICT=PARALLEL` if gap < 2.0, else `VERDICT=SEQUENTIAL`
   - Line 5: `VERSION=v2.1.107`
