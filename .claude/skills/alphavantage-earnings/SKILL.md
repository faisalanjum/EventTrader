---
name: alphavantage-earnings
description: Consensus estimates and earnings data from Alpha Vantage.
---

# Alpha Vantage Earnings

## Command patterns

```bash
# Quarterly + annual actuals (open mode)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op earnings --symbol AAPL

# Quarterly + annual actuals (PIT mode — date-only filter, annual cross-referenced)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op earnings --symbol AAPL \
  --pit 2024-11-01T10:00:00-05:00

# Consensus estimates (open mode — all forward + historical)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op estimates --symbol AAPL

# Consensus estimates (PIT mode — coarse PIT using revision buckets, forward gapped)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op estimates --symbol AAPL \
  --pit 2024-11-01T10:00:00-05:00

# Earnings calendar (open mode only — gapped in PIT)
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --op calendar --symbol AAPL --horizon 3month
```

## Response fields by op

### --op earnings (quarterly)
- `record_type`: "quarterly_earnings"
- `fiscalDateEnding`, `reportedDate`
- `reportedEPS`, `estimatedEPS`, `surprise`, `surprisePercentage`
- `available_at` derived from reportedDate (date-only, start-of-day NY)

### --op earnings (annual)
- `record_type`: "annual_earnings"
- `fiscalDateEnding`, `reportedEPS`
- `available_at` cross-referenced from matching Q4 quarterly `reportedDate` (`available_at_source: "cross_reference"`)
- Annual items without a matching quarterly are reported in `gaps[]` as unverifiable

### --op estimates
- `record_type`: "estimate"
- `fiscalDateEnding`, `horizon`
- EPS + revenue consensus (average/high/low/analyst_count)
- Revision tracking: `eps_estimate_average_7/30/60/90_days_ago`, `eps_estimate_revision_up/down_trailing_7/30_days`
- PIT mode (coarse): selects nearest revision bucket anchored to fiscal period end that doesn't exceed PIT. Returns `pit_consensus_eps` (the PIT-appropriate value) and `pit_bucket` (e.g., `7d_before_period_end`, `at_period_end`). `available_at_source: "coarse_pit"`. Forward-looking estimates gapped.

### --op calendar (open mode only)
- `record_type`: "earnings_calendar"
- `symbol`, `name`, `reportDate`, `fiscalDateEnding`, `estimate`, `currency`, `timeOfTheDay`

## Note
Free tier - use sparingly.
