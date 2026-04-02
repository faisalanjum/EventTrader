---
name: test-v185-thinking-skill
description: Test if effort:high enables thinking in forked skills (v2.1.85)
effort: high
context: fork
---

You are a test skill. Do these steps IN ORDER:

1. Write the file `earnings-analysis/test-outputs/test-v185-thinking-skill.txt` with:
   - Line 1: `SKILL_EXECUTED=true`
   - Line 2: `MODEL=` followed by your model name
   - Line 3: `THINKING_ACTIVE=` followed by YES if you have an internal thinking/reasoning scratchpad active for this turn, or NO if you do not
   - Line 4: `EFFORT_LEVEL=` followed by the effort level you're operating at (low/medium/high) if you can detect it

2. Now do a brief analytical task (2-3 sentences): "Why might a company that beats EPS consensus by 10% still see its stock drop 5%?"
   Write your analysis as line 5+.

3. Stop immediately after writing the file. Do not do anything else.
