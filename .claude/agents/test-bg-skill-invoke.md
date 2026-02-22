---
name: test-bg-skill-invoke
description: "Test: Can background: true agents invoke forked skills? (v2.1.50)"
background: true
model: haiku
---
You are testing whether a `background: true` agent can invoke Skills.

1. Try to invoke the Skill tool with skill name "test-re-arguments" and args "BG_SKILL_TEST_BANANA"
2. Report whether the Skill tool is available and whether the invocation succeeded

Write results to `earnings-analysis/test-outputs/test-bg-skill-invoke.txt`:
```
BG_SKILL_INVOKE_TEST=v2.1.50
BACKGROUND=true
SKILL_TOOL_AVAILABLE=YES|NO
SKILL_INVOCATION=WORKS|BLOCKED|ERROR - [details]
SKILL_RESULT=[result or error message]
```
