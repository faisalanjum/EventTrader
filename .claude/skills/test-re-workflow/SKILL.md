---
name: test-re-workflow
description: "Retest 2026-02-05: Does parent continue after child returns?"
allowed-tools:
  - Skill
  - Write
context: fork
---
# Test: Workflow continuation (GH #17351)

Execute these steps IN ORDER:
1. Write "STEP1" to earnings-analysis/test-outputs/test-re-workflow-step1.txt
2. Call /test-re-workflow-child
3. Write "STEP3: child returned=[what child said]" to earnings-analysis/test-outputs/test-re-workflow-step3.txt
4. Write "STEP4: WORKFLOW_COMPLETE" to earnings-analysis/test-outputs/test-re-workflow-step4.txt

This tests that you (parent) continue executing after child returns.
