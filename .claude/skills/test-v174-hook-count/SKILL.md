---
name: test-v174-hook-count
description: Test skill hook double-fire fix (v2.1.72)
hooks:
  PostToolUse:
    - matcher: "Write"
      hooks:
        - type: command
          command: "/home/faisal/EventMarketDB/.claude/hooks/test-v174-hook-counter.sh"
---
You are a skill hook fire-count test. Your ONLY job:

1. First, delete any previous counter file: run `rm -f /home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v174-hook-fire-count.txt`
2. Write the text "HOOK_TEST_WRITE_1" to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v174-hook-trigger.txt`
3. Wait a moment, then read the counter file at `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v174-hook-fire-count.txt`
4. Count how many times HOOK_FIRED appears — it should be exactly 1 (the v2.1.72 fix prevents double-fire)
5. Write your final result to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-v174-hook-double-fire.txt`

Format:
```
HOOK_DOUBLE_FIRE_TEST_v2174
Date: [current date]
Hook fire count: [number of HOOK_FIRED lines]
Expected: 1
Double-fire bug fixed: [YES if count=1 / NO if count>1]
Raw counter contents: [paste contents]
```

Stop immediately after writing the result file.
