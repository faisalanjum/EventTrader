---
name: earnings-prediction
description: Predict stock direction post 8-K earnings release using PIT data only
model: claude-opus-4-5
context: fork
permissionMode: dontAsk
user-invocable: false
disable-model-invocation: false
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskGet
  - TaskUpdate
  - Skill
  - Bash
  - Write
  - Read
  - Edit
  - Glob
  - Grep
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
skills: []
---

# Earnings Prediction

**Goal**: Predict stock direction and magnitude before market reacts, using point-in-time data only.

---

## Triggers

Called by earnings-orchestrator (not user-invocable).

---

## Input

- `accession_no` - 8-K earnings filing accession number
- `ticker` - Company ticker symbol
- `quarter_label` - Fiscal quarter (e.g., Q1_FY2024)

---

## Output

**result.json structure:**
```json
{
  "direction": "up",
  "magnitude": "extreme",
  "confidence_pct": 85,
  "primary_reason": "Beat EPS by 12%, raised FY guidance"
}
```

| Field | Type | Values |
|-------|------|--------|
| direction | string | `up` / `down` |
| magnitude | string | `tiny` (0-1%) / `small` (1-3%) / `medium` (3-5%) / `large` (5-8%) / `extreme` (8%+) |
| confidence_pct | integer | 0-100 |
| primary_reason | string | Brief explanation |

---

## Workflow (2 Steps)

### Step 1: Load Context
Read `prediction/context.json` for the event and treat `pit_datetime` as the hard cutoff for all fetched data.

### Step 2: Write Prediction Output
Produce `prediction/result.json` with the required fields (`direction`, `magnitude`, `confidence_pct`, `primary_reason`) using only PIT-safe context.

---

## Scripts

No mandatory script calls. This skill is bundle/context-driven and writes the prediction result file.

---

## Hooks

- `PostToolUse`: `.claude/hooks/build-thinking-on-complete.sh` - Builds thinking files on completion

---

## Data Guardrails

See `.claude/filters/rules.json` for:
- Forbidden patterns (lookahead bias blockers)
- PIT date fields per data source

---

## Folder Structure

```
earnings-analysis/Companies/{TICKER}/
├── cumulative/
│   ├── guidance.csv              # Full history (orchestrator only)
│   └── news.csv                  # Full history (orchestrator only)
└── events/
    └── {quarter_label}/
        ├── prediction/
        │   ├── context.json      # PIT = 8-K filing_datetime
        │   └── result.json       # Prediction output
        └── attribution/
            ├── context.json      # PIT = 10-Q filing_datetime
            └── result.json       # Attribution output
```

## Output Files

**Context**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/prediction/context.json`
**Result**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/prediction/result.json`

---

## Invariants (Must Always Hold)

- All data queries must be PIT-filtered
- Never access return data (daily_stock, hourly_stock)
- Consensus must come from pre-filing sources only

---

*Version 1.0 | 2026-02-04 | Fresh rebuild from template*
