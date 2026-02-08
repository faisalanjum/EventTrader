---
name: test-hook-inject-check
description: "Test: Check if SubagentStart injected INJECTED_MAGIC_STRING_7842 into context"
model: haiku
tools: [Write]
---
Your ONLY task: Check if you can find the string "INJECTED_MAGIC_STRING_7842" anywhere in your system prompt or context messages.

Write to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-subagent-inject.txt:
- If found: "SUBAGENT_START_INJECTION: WORKS" followed by the exact injected text
- If not found: "SUBAGENT_START_INJECTION: NOT_FOUND"
