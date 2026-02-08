---
name: test-hook-prompt-type
description: "Test: type: prompt hook handler in agent frontmatter"
tools: [Read, Write, Bash]
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: prompt
          prompt: "The agent is trying to run a Bash command. Here is the hook input: $ARGUMENTS. RULE: If the command field in tool_input contains the exact string BLOCK_ME, respond with {\"ok\": false, \"reason\": \"PROMPT_HOOK_BLOCKED: Command contains BLOCK_ME\"}. Otherwise respond with {\"ok\": true}."
          timeout: 30
---
You are testing whether type: "prompt" hooks work in agent frontmatter.

**Steps:**
1. Try to run Bash: `echo "SAFE_COMMAND"`
   - This should be ALLOWED by the prompt hook (no BLOCK_ME in command)
   - Record whether it succeeded or was blocked

2. Try to run Bash: `echo "BLOCK_ME please"`
   - This should be BLOCKED by the prompt hook (contains BLOCK_ME)
   - Record whether it succeeded or was blocked

3. Write findings to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-prompt-type.txt:
   - Line 1: "SAFE_COMMAND: ALLOWED" or "SAFE_COMMAND: BLOCKED (unexpected)"
   - Line 2: "BLOCK_ME_COMMAND: BLOCKED" or "BLOCK_ME_COMMAND: ALLOWED (hook not enforced)"
   - Line 3: "PROMPT_TYPE_HOOK: WORKS" or "PROMPT_TYPE_HOOK: NOT_ENFORCED" or "PROMPT_TYPE_HOOK: PARTIALLY_WORKS"
   - Line 4: Any error messages or additional observations
