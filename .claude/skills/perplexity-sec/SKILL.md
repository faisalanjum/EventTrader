---
name: perplexity-sec
description: SEC EDGAR filings search. Use for official regulatory documents.
user-invocable: false
---

# Perplexity SEC Query Patterns

Reference patterns for `.claude/agents/perplexity-sec.md`.

## Core Rule

Use only:

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py --source perplexity --op search --search-mode sec ...
```

Return the wrapper JSON envelope directly.

## PIT Mode (Historical)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search --search-mode sec \
  --query "AAPL 10-K risk factors FY2024" \
  --pit 2025-02-01T00:00:00-05:00 \
  --max-results 10
```

## Open Mode (Live)

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search --search-mode sec \
  --query "AAPL 10-K risk factors FY2024" \
  --max-results 10
```

## Date Range

```bash
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source perplexity --op search --search-mode sec \
  --query "AAPL 10-K risk factors FY2024" \
  --date-from 2024-01-01 --date-to 2024-12-31 \
  --max-results 10
```

## Supported Filings

10-K (annual), 10-Q (quarterly), 8-K (current), S-1/S-4 (IPO/M&A)

## Content Extraction

Each search result includes a `snippet` field with extracted content from EDGAR filings.
- Default extraction: ~4K tokens per result, ~10K total.
- Use `--max-tokens <N>` (up to 1000000) and `--max-tokens-per-page <N>` for deeper extraction.
- For full filing content, hand off URLs to `neo4j-report` (if the filing is in Neo4j) or use a dedicated content extraction agent.

## Notes

- Uses `--search-mode sec` to target SEC EDGAR specifically.
- `pit_fetch.py` normalizes each result with:
  - `available_at` (date-only -> start-of-day NY tz)
  - `available_at_source: "provider_metadata"`
- Authentication is handled by `pit_fetch.py` via `.env` (`PERPLEXITY_API_KEY`).
- In PIT mode, date-only items from the PIT day or later are excluded (conservative).
- Response is JSON-only (`data[]`, `gaps[]`) for deterministic hook validation.
