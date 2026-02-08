---
name: test-hook-stop-block
description: "Test: SubagentStop blocking with decision: block and stop_hook_active"
tools: [Read, Write]
hooks:
  Stop:
    - hooks:
        - type: command
          command: "/home/faisal/EventMarketDB/.claude/hooks/test_stop_block.sh"
---
You are testing whether Stop hooks can block an agent from stopping.

**Step 1:** Write the text "STEP_1_DONE" to /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-hook-stop-block.txt

After Step 1, when you try to finish responding, the Stop hook will BLOCK you and give you an instruction. Follow that instruction exactly.

After following the hook's instruction, you will be allowed to stop on your second attempt.
