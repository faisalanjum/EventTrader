---
name: test-re-agent-hooks
description: "Retest: hooks in agent frontmatter (PreToolUse, PostToolUse, Stop)"
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo '{\"decision\":\"block\",\"reason\":\"HOOK_BLOCKED_BASH\"}'"
  Stop:
    - hooks:
      - type: command
        command: "echo '{}' && echo 'STOP_HOOK_FIRED' >> /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-re-agent-hooks-stop.txt"
---
You are testing whether hooks defined in agent frontmatter work.

1. Try to use Bash to run: echo hello
   - If PreToolUse hook works, this should be BLOCKED with "HOOK_BLOCKED_BASH"
2. Use Read to read any small file (this should NOT be blocked)

Reply with:
- "BASH: BLOCKED_BY_HOOK" or "BASH: ALLOWED (hook not enforced)"
- "READ: ALLOWED"
- "AGENT_HOOKS: ENFORCED" or "AGENT_HOOKS: NOT_ENFORCED"
