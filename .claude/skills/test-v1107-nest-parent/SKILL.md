---
name: test-v1107-nest-parent
description: "v2.1.107 retest: parent skill invokes child skill (Skill→Skill nesting, sequential workflow continuation)"
allowed-tools:
  - Skill
  - Bash
  - Write
  - Read
context: fork
---

# Test: Skill→Skill nesting + workflow continuation

## Hypothesis
- Skill can invoke another Skill sequentially.
- Parent continues after child returns.

## Steps

1. Write pre-child marker `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-nest-pre.txt` with content "PRE_CHILD_<timestamp>".
2. Invoke `Skill({skill:"test-v1107-nest-child"})`.
3. AFTER child returns, write post-child marker `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-nest-post.txt` with content "POST_CHILD_<timestamp>".
4. Read `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-nest-child.txt` to confirm child wrote its output.
5. Write final result to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v1107-nest-parent.txt`:
   - Line 1: `PRE_MARKER_WRITTEN=YES`
   - Line 2: `CHILD_FILE_EXISTS=YES/NO`
   - Line 3: `CHILD_OUTPUT_FIRST_LINE=<first line>`
   - Line 4: `POST_MARKER_WRITTEN=YES`
   - Line 5: `PARENT_CONTINUED_AFTER_CHILD=YES/NO`
   - Line 6: `VERDICT=PASS` if all YES, else FAIL
   - Line 7: `VERSION=v2.1.107`
