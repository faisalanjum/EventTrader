---
name: bz-news-api-queries
description: Query patterns for the bz-news-api data subagent. Uses scripts/pit_fetch.py against Benzinga News API with PIT-safe envelope output.
user-invocable: false
---

# bz-news-api Query Patterns

Reference patterns for `.claude/agents/bz-news-api.md`.

## Reference First

Before building `--channels` / `--tags` filters, read:

- `.claude/references/neo4j-news-fields.md`

Use exact channel/tag strings from that reference to avoid near-match misses.

## Core Rule

Use only:

```bash
python3 scripts/pit_fetch.py --source bz-news-api ...
```

Return the wrapper JSON envelope directly.

## PIT Mode (Historical)

Pass `--pit` on every retrieval command.

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --pit 2025-01-01T00:00:00-05:00 \
  --tickers NOG \
  --date-from 2024-10-01 \
  --date-to 2025-01-01 \
  --limit 50
```

## Open Mode (Live / On-Demand)

No `--pit`.

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --themes macro \
  --lookback-minutes 720 \
  --limit 50
```

## Macro Theme Pull

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --themes macro \
  --channels Macro \
  --keywords fed,inflation,cpi,rates \
  --lookback-minutes 1440 \
  --limit 100
```

## Oil Theme Pull

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --themes oil \
  --keywords opec,wti,brent,crude \
  --date-from 2025-01-01 \
  --date-to 2025-01-31 \
  --limit 100
```

## Channel / Tag-Driven Pull

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --channels Energy,Macro \
  --tags Oil,Inflation \
  --lookback-minutes 10080 \
  --limit 100
```

## Ticker + Theme Combined

```bash
python3 scripts/pit_fetch.py \
  --source bz-news-api \
  --tickers XOM,CVX \
  --themes oil \
  --lookback-minutes 4320 \
  --limit 100
```

## Notes

- `pit_fetch.py` normalizes each item with:
  - `available_at`
  - `available_at_source: "provider_metadata"`
- Authentication is handled by `pit_fetch.py` via `.env`:
  - `BENZINGANEWS_API_KEY` (preferred)
  - `BENZINGA_API_KEY` (fallback)
- Never attempt manual auth flows in the agent prompt path.
- In PIT mode, items after `--pit` are dropped before output.
- If provider timestamps are missing/unparseable, items are dropped and explained in `gaps[]`.
- Response is JSON-only (`data[]`, `gaps[]`) for deterministic hook validation.
