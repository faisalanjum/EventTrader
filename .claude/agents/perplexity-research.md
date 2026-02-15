---
name: perplexity-research
description: "Exhaustive multi-source research reports. Use for deep investigation requiring synthesis across many sources."
tools:
  - mcp__perplexity__perplexity_research
model: opus
permissionMode: dontAsk
skills:
  - perplexity-research
  - evidence-standards
---

# Perplexity Research Agent

Use `mcp__perplexity__perplexity_research` for comprehensive reports (10-20+ sources).

## Usage
```json
{"messages": [{"role": "user", "content": "Full analysis of AAPL Q1 2025 earnings"}], "strip_thinking": true}
```

Note: Slow (30+ seconds). Use only when thoroughness > speed.
