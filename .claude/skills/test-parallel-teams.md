---
name: test-parallel-teams
description: "Test: can primary agent create two teams in parallel via TeamCreate"
---

You are running a test. Follow these instructions EXACTLY:

## Step 1: Create two teams in PARALLEL (same message)

Call BOTH of these TeamCreate calls in a SINGLE message (parallel tool calls):

1. TeamCreate with team_name: "test-pteam-alpha", description: "Parallel team test alpha"
2. TeamCreate with team_name: "test-pteam-beta", description: "Parallel team test beta"

IMPORTANT: Both calls MUST be in the SAME message to test true parallelism.

## Step 2: Record results

After both calls return, check:
- Did TeamCreate #1 (alpha) succeed or fail? Record the exact response or error.
- Did TeamCreate #2 (beta) succeed or fail? Record the exact response or error.

## Step 3: Verify on disk

Use Bash to run:
```
ls -la ~/.claude/teams/test-pteam-alpha/ 2>&1 && echo "---ALPHA EXISTS---" || echo "---ALPHA MISSING---"
ls -la ~/.claude/teams/test-pteam-beta/ 2>&1 && echo "---BETA EXISTS---" || echo "---BETA MISSING---"
ls -la ~/.claude/tasks/test-pteam-alpha/ 2>&1 && echo "---ALPHA TASKS EXISTS---" || echo "---ALPHA TASKS MISSING---"
ls -la ~/.claude/tasks/test-pteam-beta/ 2>&1 && echo "---BETA TASKS EXISTS---" || echo "---BETA TASKS MISSING---"
```

## Step 4: Write results

Write ALL findings to: /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-parallel-teams.txt

Format:
```
TEST: Parallel TeamCreate from Primary Agent
DATE: <today>
METHOD: Skill (no context:fork) invoked from claude -p primary session

TEAMCREATE #1 (test-pteam-alpha):
RESULT: <SUCCESS or FAILED>
RESPONSE: <exact response or error text>

TEAMCREATE #2 (test-pteam-beta):
RESULT: <SUCCESS or FAILED>
RESPONSE: <exact response or error text>

DISK VERIFICATION:
<paste ls output here>

CONCLUSION: <Can or Cannot create two teams in parallel from primary agent>
```

## IMPORTANT
- Do NOT delete the teams. Leave them on disk for manual validation.
- Do NOT spawn any subagents or teammates. This tests the PRIMARY agent only.
