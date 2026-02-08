---
name: test-hook-post-failure
description: "Test: PostToolUseFailure hook event fires when tool fails"
tools: [Read, Write, Bash]
hooks:
  PostToolUseFailure:
    - hooks:
        - type: command
          command: "/home/faisal/EventMarketDB/.claude/hooks/test_post_failure.sh"
---
You are testing whether PostToolUseFailure hooks fire when a tool call fails.

**Steps:**
1. Try to run Bash: `cat /tmp/test_hook_nonexistent_xyz_99999.txt`
   - This WILL fail (file doesn't exist, exit code 1)
   - If PostToolUseFailure hook works, it will log to test-outputs/test-hook-post-failure.log

2. After the failure, Read: /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-post-failure.log

3. Write your findings to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-post-failure.txt:
   - Line 1: "POST_TOOL_USE_FAILURE_HOOK: FIRED" or "POST_TOOL_USE_FAILURE_HOOK: NOT_FIRED"
   - Line 2: Copy the STDIN JSON from the log (shows what fields the hook received)
   - Line 3: List which fields were present in the JSON (e.g., "FIELDS: hook_event_name, tool_name, tool_input, error, tool_use_id")
