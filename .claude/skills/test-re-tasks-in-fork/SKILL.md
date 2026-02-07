---
name: test-re-tasks-in-fork
description: "Retest 2026-02-05: Can forked skill use TaskCreate/List/Get/Update?"
context: fork
---
# Test: Task management tools in fork

1. Call TaskList to see existing tasks
2. Call TaskCreate with subject "retest-from-fork" and description "created by forked skill"
3. Call TaskList again to confirm it was created
4. Write to earnings-analysis/test-outputs/test-re-tasks-in-fork.txt:
   - "TASKLIST: WORKS" or "TASKLIST: BLOCKED"
   - "TASKCREATE: WORKS" or "TASKCREATE: BLOCKED"
   - Number of tasks visible
   - The task ID of the one you created
