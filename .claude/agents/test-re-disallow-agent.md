---
name: test-re-disallow-agent
description: "Retest: disallowedTools enforcement on AGENT (not skill)"
disallowedTools:
  - Write
  - Bash
---
You are testing whether disallowedTools is enforced for agents.

1. Try to use the Write tool to create earnings-analysis/test-outputs/test-re-disallow-agent.txt with "WRITE_TEST"
2. Try to use Bash to run: echo hello
3. Try to use Read to read earnings-analysis/test-outputs/test-re-3layer-top.txt

Reply with:
- "WRITE: ALLOWED" or "WRITE: BLOCKED"
- "BASH: ALLOWED" or "BASH: BLOCKED"
- "READ: ALLOWED" or "READ: BLOCKED"
- "AGENT_DISALLOW: ENFORCED" if Write and Bash were blocked but Read worked
- "AGENT_DISALLOW: NOT_ENFORCED" if Write or Bash still worked
