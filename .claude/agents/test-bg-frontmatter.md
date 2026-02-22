---
name: test-bg-frontmatter
description: "Test: Does background: true in agent frontmatter run agent in background mode?"
background: true
model: haiku
---
You are testing whether `background: true` in agent frontmatter works.

Your ONLY job is to write a test report. Do this:

1. Write the following to `earnings-analysis/test-outputs/test-bg-frontmatter.txt`:

```
BG_FRONTMATTER_TEST=v2.1.50
AGENT_NAME=test-bg-frontmatter
BACKGROUND_FIELD=true
TIMESTAMP={current timestamp}
I_AM_RUNNING=YES
```

2. That's it. Just write the file and report "BG_FRONTMATTER: WORKS"
