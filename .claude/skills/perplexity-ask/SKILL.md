---
name: perplexity-ask
description: Quick factual Q&A with citations. Use for simple lookups and single facts.
user-invocable: false
---

# Perplexity Ask Query Patterns

Reference patterns for `.claude/agents/perplexity-ask.md`.

## Core Rule

Use only:

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source perplexity --op ask ...
```

Return the wrapper JSON envelope directly.

## PIT Mode (Historical)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op ask \
  --query "What was AAPL's Q1 2025 EPS vs consensus?" \
  --pit 2025-02-01T00:00:00-05:00 \
  --search-context-size medium
```

In PIT mode, the synthesis item is excluded from data[] (its `available_at` = now > PIT). Agent works from PIT-filtered `search_results` only.

## Open Mode (Live)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op ask \
  --query "What was AAPL's Q1 2025 EPS vs consensus?" \
  --search-context-size medium
```

In open mode, data[] includes search_results plus a synthesis item (`record_type: "synthesis"`) with `answer` and `citations`.

## With Filters

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op ask \
  --query "AAPL revenue guidance FY2025" \
  --search-recency month \
  --search-context-size high
```

## Notes

- Uses Perplexity `sonar-pro` model via POST /chat/completions.
- `pit_fetch.py` normalizes each search_result with:
  - `available_at` (date-only -> start-of-day NY tz)
  - `available_at_source: "provider_metadata"`
- Synthesis item has `record_type: "synthesis"`, `answer`, `citations`, `available_at`, `available_at_source`.
- Authentication is handled by `pit_fetch.py` via `.env` (`PERPLEXITY_API_KEY`).
- Response is JSON-only (`data[]`, `gaps[]`) for deterministic hook validation.
