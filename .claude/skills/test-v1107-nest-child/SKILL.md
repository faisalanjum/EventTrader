---
name: test-v1107-nest-child
description: "Child skill for v2.1.107 nesting retest — writes marker and returns"
context: fork
---

Write to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-nest-child.txt`:
- Line 1: `CHILD_EXECUTED=YES`
- Line 2: `CHILD_TIMESTAMP=` followed by `date +%s.%N` output
- Line 3: `PARENT_CONTEXT_VISIBLE=<describe what you can see of the parent>`

Reply with: "CHILD_DONE_<timestamp>"
