---
name: test-hook-agent-type
description: "Test: type: agent hook handler in agent frontmatter"
tools: [Read, Write, Bash]
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: agent
          prompt: "The agent is trying to run a Bash command. Here is the hook input: $ARGUMENTS. RULE: If the command field in tool_input contains the exact string AGENT_BLOCK_ME, respond with {\"ok\": false, \"reason\": \"AGENT_HOOK_BLOCKED: Command contains AGENT_BLOCK_ME\"}. Otherwise respond with {\"ok\": true}."
          timeout: 60
---
You are testing whether type: "agent" hooks work in agent frontmatter.

**Steps:**
1. Try to run Bash: `echo "SAFE_COMMAND_AGENT"`
   - This should be ALLOWED by the agent hook (no AGENT_BLOCK_ME)

2. Try to run Bash: `echo "AGENT_BLOCK_ME please"`
   - This should be BLOCKED by the agent hook

3. Write findings to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-agent-type.txt:
   - Line 1: "SAFE_COMMAND: ALLOWED" or "SAFE_COMMAND: BLOCKED (unexpected)"
   - Line 2: "AGENT_BLOCK_ME_COMMAND: BLOCKED" or "AGENT_BLOCK_ME_COMMAND: ALLOWED (hook not enforced)"
   - Line 3: "AGENT_TYPE_HOOK: WORKS" or "AGENT_TYPE_HOOK: NOT_ENFORCED"
   - Line 4: Any error messages or observations
