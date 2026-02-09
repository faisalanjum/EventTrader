---
name: test-parallel-teams-split
description: "Test: two teams in parallel — primary leads one, subagent leads the other"
---

You are running a test. Follow these instructions EXACTLY:

## Step 1: Primary creates Team A

Call TeamCreate with team_name: "test-pteam-split-a", description: "Split test team A (led by primary)"

Record the result (success or error).

## Step 2: Spawn a subagent that creates Team B

Use the Task tool with subagent_type "general-purpose" and this prompt:

```
You are running a test. Follow these instructions EXACTLY:

1. Call TeamCreate with team_name: "test-pteam-split-b", description: "Split test team B (led by subagent)"

2. Record if it succeeded or failed (exact response or error).

3. If it succeeded, use Bash to verify:
   ls -la ~/.claude/teams/test-pteam-split-b/ 2>&1
   cat ~/.claude/teams/test-pteam-split-b/config.json 2>&1

4. Also check if team A exists alongside:
   ls -la ~/.claude/teams/test-pteam-split-a/ 2>&1

5. Return ALL findings as plain text. Include exact responses.

IMPORTANT: Do NOT delete any teams.
```

## Step 3: Verify both teams exist simultaneously

After the subagent returns, use Bash to check:
```
echo "=== TEAM A ===" && ls -la ~/.claude/teams/test-pteam-split-a/ 2>&1 && cat ~/.claude/teams/test-pteam-split-a/config.json 2>&1
echo "=== TEAM B ===" && ls -la ~/.claude/teams/test-pteam-split-b/ 2>&1 && cat ~/.claude/teams/test-pteam-split-b/config.json 2>&1
echo "=== TASK DIRS ===" && ls -la ~/.claude/tasks/test-pteam-split-a/ 2>&1 && ls -la ~/.claude/tasks/test-pteam-split-b/ 2>&1
```

## Step 4: Write results

Write ALL findings to: /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-parallel-teams-split.txt

Format:
```
TEST: Two Parallel Teams via Split Leadership (Primary + Subagent)
DATE: <today>
METHOD: Primary creates Team A via TeamCreate. Subagent (general-purpose via Task) creates Team B.

PRIMARY TEAMCREATE (test-pteam-split-a):
RESULT: <SUCCESS or FAILED>
RESPONSE: <exact response>

SUBAGENT TEAMCREATE (test-pteam-split-b):
RESULT: <SUCCESS or FAILED>
RESPONSE: <exact subagent response>

SIMULTANEOUS EXISTENCE CHECK:
Team A on disk: <YES/NO + details>
Team B on disk: <YES/NO + details>
Both config.json present: <YES/NO>

CONCLUSION: <Can or Cannot run two teams in parallel via split leadership>
```

## IMPORTANT
- Do NOT delete any teams. Leave everything on disk.
- Do NOT skip any steps.
