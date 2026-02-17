---
name: pit-envelope
description: PIT envelope contract for all data sub-agents. Defines the standard JSON envelope, field mappings, forbidden keys, and retry rules.
user-invocable: false
---

# PIT Envelope Contract

Standard JSON envelope for all data sub-agent responses. Validated by `pit_gate.py` PostToolUse hook.

## Envelope Schema

```json
{
  "data": [
    {
      "available_at": "<ISO8601 datetime+tz>",
      "available_at_source": "<canonical source tag>",
      "...domain-specific fields..."
    }
  ],
  "gaps": [
    {"type": "no_data|pit_excluded|unverifiable", "reason": "...", "query": "..."}
  ]
}
```

- `data[]`: Array of result items. Each MUST have `available_at` (full ISO8601 datetime with timezone) and `available_at_source`.
- `gaps[]`: Array explaining missing data. Always present (use `[]` if no gaps).

## `available_at_source` Canonical Values

| Value | Meaning |
|-------|---------|
| `neo4j_created` | Node's `created` timestamp from Neo4j (News, Transcript) |
| `edgar_accepted` | SEC EDGAR acceptance datetime (Report nodes) |
| `time_series_timestamp` | Per-datapoint timestamp from time series data |
| `provider_metadata` | External provider metadata timestamp |

## Field Mapping Table

| Agent | Source Field | Maps to `available_at` | `available_at_source` | Notes |
|-------|-------------|------------------------|----------------------|-------|
| neo4j-news | `n.created` | direct | `neo4j_created` | Full datetime+tz |
| neo4j-report | `r.created` | direct | `edgar_accepted` | Full datetime+tz |
| neo4j-transcript | `t.conference_datetime` | direct | `neo4j_created` | Full datetime+tz |
| neo4j-xbrl | parent Report `r.created` | join | `edgar_accepted` | Requires MATCH to parent Report |
| neo4j-entity (price) | `Date.market_close_current_day` | normalize to ISO8601 | `time_series_timestamp` | Hybrid: temporal via Date node close time |
| neo4j-entity (div) | `Date.market_close_current_day` | normalize to ISO8601 | `time_series_timestamp` | 65 gaps (44 orphan + 21 NULL close = 1.48% of 4,405) |
| neo4j-entity (split) | `Date.market_close_current_day` | normalize to ISO8601 | `time_series_timestamp` | 0 gaps (100% coverage) |
| neo4j-entity (metadata) | — | open mode pass-through | — | Company properties: no `pit` in params → gate allows |
| perplexity-* (search) | result `date` | YYYY-MM-DD -> start-of-day NY tz | `provider_metadata` | PIT: exclude PIT day entirely (prior-day items pass) |
| perplexity-* (chat) | `search_results[].date` | same | `provider_metadata` | Chat ops add synthesis item (`record_type: "synthesis"`) in open mode (appended separately from `--limit`); excluded in PIT mode |
| alphavantage EARNINGS | `reportedDate` | **date-only: verify or gap** | `provider_metadata` | See Date-Only Sources |
| alphavantage (series) | per-datapoint timestamp | direct | `time_series_timestamp` | Full datetime |

## Forbidden Keys (NEVER include in PIT mode output)

`daily_stock`, `hourly_stock`, `session_stock`, `daily_return`, `daily_macro`, `daily_industry`, `daily_sector`, `hourly_macro`, `hourly_industry`, `hourly_sector`

**Where these live by relationship type**:
- `INFLUENCES` (News/Transcript → Company): `daily_stock`, `hourly_stock`, `session_stock`, `daily_macro`, `daily_industry`, `daily_sector`, `hourly_macro`, `hourly_industry`, `hourly_sector`
- `PRIMARY_FILER` (Report → Company): same return fields
- `HAS_PRICE` (Date → Company): `daily_return`

## PIT Propagation Rule

When PIT is active, pass the PIT timestamp as a Cypher parameter named `pit` in the `params` dict. Example:
```
params: {ticker: 'NOG', pit: '2024-02-15T16:00:00-05:00'}
```
The PostToolUse hook reads `tool_input.params.pit` for validation.

## Neo4j Envelope Query Pattern

```cypher
-- Template: wrap results into envelope via collect()
MATCH (...)
WHERE ... AND <source_field> <= $pit
WITH ... ORDER BY ...
WITH collect({
  available_at: <source_field>,
  available_at_source: '<tag>',
  ...domain fields (NO forbidden keys)...
}) AS items
RETURN items AS data, [] AS gaps
```

## Retry Rules

- On `PIT_VIOLATION_GT_CUTOFF`: tighten WHERE clause
- On `PIT_FORBIDDEN_FIELD`: remove offending RETURN columns
- On `PIT_MISSING_AVAILABLE_AT`: alias the correct source field
- Max 2 retries. If still blocked → return `{"data":[],"gaps":[{"type":"pit_excluded","reason":"..."}]}`

## Fail-Closed Rule

If you cannot produce a reliable `available_at` for an item in PIT mode, drop it from `data[]` and record it in `gaps[]`. Never return "maybe-clean" data.

## Date-Only Sources

Date-only fields (e.g., `d.date`, `declaration_date`) cannot produce a full ISO8601 datetime+tz. These must be handled per-agent when their rework occurs. Options:
- Derive datetime from known market close time (e.g., 4PM ET for US equities)
- Use as locator only and gap if PIT-critical
- Document chosen approach per agent
