---
name: test-re-skill-nests-task
description: "Retest 2026-02-05: L1 skill calls L2 skill that tries Task tool"
allowed-tools:
  - Skill
  - Write
context: fork
---
# Test: Skill → Skill → Task (3-level mixing)

1. Call /test-re-skill-tries-task (a child skill that will attempt to use the Task tool)
2. Write to earnings-analysis/test-outputs/test-re-skill-nests-task.txt:
   - What child returned
   - "SKILL_NEST_TASK: WORKS" if the child's Task call succeeded
   - "SKILL_NEST_TASK: BLOCKED" if the child couldn't use Task
