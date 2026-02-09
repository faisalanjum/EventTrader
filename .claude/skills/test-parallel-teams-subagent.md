---
name: test-parallel-teams-subagent
description: "Test: can a subagent create two teams in parallel via TeamCreate"
---

You are running a test. Follow these instructions EXACTLY:

## Step 1: Spawn a general-purpose subagent

Use the Task tool with subagent_type "general-purpose" and this prompt:

```
You are running a test. Follow these instructions EXACTLY:

1. Call TeamCreate TWICE in a SINGLE message (parallel tool calls):
   - TeamCreate with team_name: "test-pteam-sub-alpha", description: "Subagent parallel team test alpha"
   - TeamCreate with team_name: "test-pteam-sub-beta", description: "Subagent parallel team test beta"

2. After both calls return, record what happened for each:
   - Did it succeed? Record exact response.
   - Did it fail? Record exact error message.

3. Use Bash to check disk:
   ls -la ~/.claude/teams/test-pteam-sub-alpha/ 2>&1
   ls -la ~/.claude/teams/test-pteam-sub-beta/ 2>&1
   ls -la ~/.claude/tasks/test-pteam-sub-alpha/ 2>&1
   ls -la ~/.claude/tasks/test-pteam-sub-beta/ 2>&1

4. Return ALL findings as plain text. Include exact responses/errors and disk check output.

IMPORTANT: Do NOT delete any teams. Leave everything on disk.
```

## Step 2: Write results

Take the subagent's response and write it to:
/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-parallel-teams-subagent.txt

Format:
```
TEST: Parallel TeamCreate from Subagent
DATE: <today>
METHOD: general-purpose subagent spawned via Task tool from claude -p

SUBAGENT RESPONSE:
<paste exact subagent response here>

CONCLUSION: <summary of whether subagent can/cannot create teams, and if so, can it create two>
```

## IMPORTANT
- Do NOT clean up or delete any teams.
- Do NOT skip any steps.
