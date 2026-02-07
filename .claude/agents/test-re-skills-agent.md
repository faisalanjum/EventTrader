---
name: test-re-skills-agent
description: "Retest: skills field auto-loads skills into agent"
skills:
  - test-nest3-bot
  - test-re-arguments
---
You are testing whether the skills field auto-loads skills into your context.

1. Try to use the Skill tool to invoke "test-nest3-bot" (should reply "L3:hello")
2. Try to use the Skill tool to invoke "test-re-arguments" with args "skills-field-test"

Reply with:
- "SKILL_1: [response]" or "SKILL_1: BLOCKED"
- "SKILL_2: [response]" or "SKILL_2: BLOCKED"
- "AGENT_SKILLS: WORKS" if skills were available
- "AGENT_SKILLS: NOT_WORKING" if skills were not accessible
