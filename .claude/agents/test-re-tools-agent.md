---
name: test-re-tools-agent
description: "Retest: tools allowlist enforcement on AGENT"
tools:
  - Read
  - Grep
---
You are testing whether the tools allowlist is enforced for agents.

1. Try to use Read to read earnings-analysis/test-outputs/test-re-3layer-top.txt (should work - it's in your tools list)
2. Try to use Write to create earnings-analysis/test-outputs/test-re-tools-agent.txt with "WRITE_TEST" (NOT in your tools list)
3. Try to use Bash to run: echo hello (NOT in your tools list)

Reply with:
- "READ: ALLOWED" or "READ: BLOCKED"
- "WRITE: ALLOWED" or "WRITE: BLOCKED"
- "BASH: ALLOWED" or "BASH: BLOCKED"
- "AGENT_TOOLS: ENFORCED" if only Read/Grep worked
- "AGENT_TOOLS: NOT_ENFORCED" if Write or Bash also worked
