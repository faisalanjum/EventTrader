---
name: perplexity-search
description: Raw web search results (URLs, snippets). Use when you need a list of sources, not a synthesized answer.
user-invocable: false
---

# Perplexity Search Query Patterns

Reference patterns for `.claude/agents/perplexity-search.md`.

## Core Rule

Use only:

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source perplexity --op search ...
```

Return the wrapper JSON envelope directly.

## PIT Mode (Historical)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search \
  --query "AAPL earnings Q1 2025" \
  --pit 2025-02-01T00:00:00-05:00 \
  --max-results 10 --limit 10
```

## Open Mode (Live)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search \
  --query "AAPL earnings" \
  --max-results 10
```

## With Filters

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search \
  --query "AAPL earnings guidance" \
  --search-recency month \
  --search-domains sec.gov,reuters.com \
  --max-results 10
```

## Multi-Pass Search

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search \
  --query "AAPL Q1 2025 earnings beat" \
  --query "AAPL Q1 2025 revenue guidance" \
  --max-results 5
```

## Date Range

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search \
  --query "AAPL earnings" \
  --date-from 2024-10-01 --date-to 2025-01-31 \
  --max-results 10
```

## Notes

- `pit_fetch.py` normalizes each item with:
  - `available_at` (date-only -> start-of-day NY tz)
  - `available_at_source: "provider_metadata"`
- Authentication is handled by `pit_fetch.py` via `.env` (`PERPLEXITY_API_KEY`).
- In PIT mode, date-only items from the PIT day or later are excluded (conservative).
- Items without a `date` field are dropped and explained in `gaps[]`.
- Response is JSON-only (`data[]`, `gaps[]`) for deterministic hook validation.
