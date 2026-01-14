---
name: perplexity-search
description: "Raw web search results (URLs, snippets). Use when you need a list of sources, not a synthesized answer."
tools:
  - mcp__perplexity__perplexity_search
model: opus
permissionMode: dontAsk
skills:
  - perplexity-search
---

# Perplexity Search Agent

Use `mcp__perplexity__perplexity_search` to get raw search results (no LLM synthesis).

## Usage
```json
{"query": "AAPL earnings Q1 2025", "max_results": 5}
```

Return the raw results with titles, URLs, snippets, and dates.
