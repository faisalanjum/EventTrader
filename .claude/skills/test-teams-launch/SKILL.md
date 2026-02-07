---
name: test-teams-launch
description: One-button test team launcher. Creates a team and spawns teammates automatically.
disable-model-invocation: false
---

# Launch Test Team

Create a team and spawn teammates in one shot. This tests if skills can orchestrate team creation.

## Steps

1. Use the `Teammate` tool with operation `spawnTeam`, team_name `skill-team`, description `Team created by skill`
2. Create two tasks using TaskCreate:
   - Subject: "TASK-A research", Description: "Research task for worker-a"
   - Subject: "TASK-B analysis", Description: "Analysis task for worker-b, depends on A"
   - Set TASK-B as blocked by TASK-A using TaskUpdate addBlockedBy
3. Spawn two teammates using the Task tool with team_name `skill-team`:
   - Name: `worker-a`, subagent_type: `general-purpose`, prompt: "You are worker-a. Call TaskList to find your task (TASK-A research). Mark it in_progress. Write 'WORKER-A DONE' to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/team-test-skill-launch-a.txt. Mark the task completed. Message team-lead when done."
   - Name: `worker-b`, subagent_type: `general-purpose`, prompt: "You are worker-b. Call TaskList to find your task (TASK-B analysis). It may be blocked — if so, wait and check again. When unblocked, mark it in_progress. Write 'WORKER-B DONE' to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/team-test-skill-launch-b.txt. Mark the task completed. Message team-lead when done."
4. Wait for both teammates to message you back
5. Write final results to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/team-test-skill-launch.txt:
   - SKILL_TEAM_LAUNCH
   - team_created: YES/NO
   - tasks_created: (count)
   - teammates_spawned: (count)
   - worker_a_result: (message from worker-a)
   - worker_b_result: (message from worker-b)
6. Shut down both teammates and clean up the team
