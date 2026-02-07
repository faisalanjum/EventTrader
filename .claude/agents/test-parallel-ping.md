---
name: test-parallel-ping
description: "TEST: Minimal ping agent for parallel Task spawn timing."
tools:
  - Bash
permissionMode: dontAsk
---

# Parallel Ping Agent

Do a tiny amount of work so runtime is measurable.

## Steps

1. Capture start timestamp (ns).
2. Sleep for ~2 seconds.
3. Capture end timestamp (ns).
4. Output a single line:
   `TEST|PING|{START_NS}|{END_NS}`
