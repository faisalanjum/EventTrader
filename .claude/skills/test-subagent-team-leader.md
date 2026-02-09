---
name: test-subagent-team-leader
description: "Test: can a subagent lead a full team lifecycle (create, spawn teammate, message, task)"
---

You are running a test. Follow these instructions EXACTLY:

IMPORTANT: You (the primary) must NOT call TeamCreate. You only spawn ONE subagent that does everything.

## Step 1: Spawn a single general-purpose subagent

Use the Task tool with subagent_type "general-purpose" and this prompt:

```
You are running a test of subagent team leadership. Follow these instructions EXACTLY in order:

## 1. Create a team
Call TeamCreate with team_name: "test-sub-led-team", description: "Team led by a subagent"
Record success or failure.

## 2. Create a task on the shared task list
Call TaskCreate with subject: "SUB-LED-TASK-1", description: "Task created by subagent team leader"
Record the task ID.

## 3. Spawn a teammate
Use the Task tool with:
- subagent_type: "general-purpose"
- team_name: "test-sub-led-team"
- name: "sub-worker"
- prompt: "You are a teammate on team test-sub-led-team, led by a subagent. Do the following: 1) Use TaskList to see available tasks. 2) Claim any task with SUB-LED in the subject by setting yourself as owner via TaskUpdate. 3) Send a message to the team lead using SendMessage with type 'message', recipient 'team-lead', content 'WORKER_REPORTING: I claimed the task and I am alive.' 4) Write the text 'SUB_WORKER_ALIVE' to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-subagent-team-worker.txt 5) Mark the task as completed via TaskUpdate."

Record if the spawn succeeded or failed.

## 4. Wait for the teammate
Wait up to 60 seconds. Check for messages from sub-worker. Check TaskList to see if the task was completed.

## 5. Verify on disk
Use Bash to run:
ls -la ~/.claude/teams/test-sub-led-team/ 2>&1
cat ~/.claude/teams/test-sub-led-team/config.json 2>&1
cat /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-subagent-team-worker.txt 2>&1

## 6. Return ALL findings
Return a detailed plain text report covering:
- TeamCreate: success/failure + exact response
- TaskCreate: success/failure + task ID
- Teammate spawn: success/failure + any error
- Message received from worker: yes/no + content
- Task completed by worker: yes/no
- Disk verification: config.json contents, worker file exists?
- OVERALL: Can a subagent lead a full team lifecycle?

IMPORTANT: Do NOT delete the team or any files.
```

## Step 2: Write results

Take the subagent's full response and write it to:
/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-subagent-team-leader.txt

Format:
```
TEST: Subagent as Full Team Leader
DATE: <today>
METHOD: Primary spawns general-purpose subagent. Subagent creates team, creates task, spawns teammate, receives message, verifies task completion.

SUBAGENT REPORT:
<paste entire subagent response here>

CONCLUSION: <Can or Cannot a subagent lead a full team lifecycle>
```

## IMPORTANT
- The PRIMARY must NOT call TeamCreate or interact with the team at all.
- Do NOT delete any teams or files.
