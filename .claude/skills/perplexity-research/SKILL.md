---
name: perplexity-research
description: Exhaustive multi-source research reports. Use for deep investigation.
user-invocable: false
---

# Perplexity Research Query Patterns

Reference patterns for `.claude/agents/perplexity-research.md`.

## Core Rule

Use only:

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source perplexity --op research ...
```

Return the wrapper JSON envelope directly.

## PIT Mode (Historical)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op research \
  --query "Comprehensive analysis of AAPL Q1 2025 earnings" \
  --pit 2025-02-01T00:00:00-05:00 \
  --search-context-size high \
  --timeout 120
```

In PIT mode, the synthesis item is excluded from data[] (its `available_at` = now > PIT). Agent works from PIT-filtered `search_results` only.

## Open Mode (Live)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op research \
  --query "Comprehensive analysis of AAPL Q1 2025 earnings" \
  --search-context-size high \
  --timeout 120
```

In open mode, data[] includes search_results plus a synthesis item (`record_type: "synthesis"`) with `answer` and `citations`.

## Notes

- Uses Perplexity `sonar-deep-research` model via POST /chat/completions.
- **Slow**: Deep research takes 30+ seconds. Always use `--timeout 120`.
- `pit_fetch.py` normalizes each search_result with:
  - `available_at` (date-only -> start-of-day NY tz)
  - `available_at_source: "provider_metadata"`
- Synthesis item has `record_type: "synthesis"`, `answer`, `citations`, `available_at`, `available_at_source`.
- Authentication is handled by `pit_fetch.py` via `.env` (`PERPLEXITY_API_KEY`).
- Response is JSON-only (`data[]`, `gaps[]`) for deterministic hook validation.
