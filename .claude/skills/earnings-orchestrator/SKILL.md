---
name: earnings-orchestrator
description: Predict stock direction post 8-K earnings & refine using 10-Q/10-K outcomes
model: opus
permissionMode: dontAsk
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/build_orchestrator_event_json.py"
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
  - EnterPlanMode
  - ExitPlanMode
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
skills:
  - earnings-prediction
  - earnings-attribution
---

# Earnings Orchestrator

**Goal**: Predict stock direction post 8-K earnings release & refine predictions methodology using 10-Q/10-K filing, news & analysis, transcripts, presentations, web search and actual return outcomes.

**Two phases per quarter:**
1. **Prediction** (after 8-K): Predict direction/magnitude before market reacts
2. **Attribution** (after 10-Q/10-K): Analyze actual outcome, score prediction accuracy, learn

---

## Triggers

Invoke when user asks about:
- "Run earnings prediction for {TICKER}"
- "Predict {TICKER} earnings reaction"

---

## Workflow (8 Steps)

### Step 1: Discovery
Run discovery script:
```bash
get_quarterly_filings {TICKER}
```
Output columns: `accession_8k|filed_8k|market_session_8k|accession_10q|filed_10q|market_session_10q|form_type|fiscal_year|fiscal_quarter|lag`

Events manifest is built automatically at:
`earnings-analysis/Companies/{TICKER}/events/event.json`

Each row becomes:
- `quarter_label`: `{fiscal_quarter}_FY{fiscal_year}`
- `accession_no`: `accession_8k`
- `filing_datetime`: `filed_8k`

### Step 2: Filter Events
Read `earnings-analysis/Companies/{TICKER}/events/event.json` and process events in the order listed.

Filter logic (minimal):
```text
for event in event.json.events:
  q = event.quarter_label
  result = earnings-analysis/Companies/{TICKER}/events/{q}/prediction/result.json
  if result exists: skip
  else: enqueue event for prediction
```

Output: list of queued events (at least `quarter_label`, `accession_8k`, `filed_8k`, `market_session_8k`).

### Step 3: Task Creation
Placeholder (later): create deterministic task graph / resume-safe plan per event.

### Step 4: Run Predictions
For each queued event (same order as `event.json`):

1) Ensure `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/prediction/` exists.

2) If `prediction/context.json` is missing, write it ONCE (do not overwrite if it exists):
Context file (written only if missing):
```json
{
  "schema_version": 1,
  "ticker": "{TICKER}",
  "quarter_label": "{quarter_label}",
  "accession_8k": "{accession_8k}",
  "filed_8k": "{filed_8k}",
  "market_session_8k": "{market_session_8k}",
  "pit_datetime": "{filed_8k}"
}
```

3) Run the prediction skill:
```text
Skill: earnings-prediction
Args (minimal): ticker={TICKER} quarter_label={quarter_label} accession_no={accession_8k} filing_datetime={filed_8k}
```

Completion signal: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/prediction/result.json` exists.

### Step 5: Cross-Tier Polling
Placeholder (later): poll tasks / spawn downstream work when unblocked.

### Step 6: Validation Gate
Placeholder (later): validate all per-event outputs are present + schema-valid before marking complete.

### Step 7: Aggregation
Placeholder (later): build cumulative CSVs / indices from per-event outputs.

### Step 8: Completion
Echo `ORCHESTRATOR_COMPLETE {TICKER}`.

---

## Scripts

Available in `scripts/earnings/`:
- `get_quarterly_filings.py` - Get 8-K earnings events with matched 10-Q/10-K filings

---

## Hooks

- Skill hook (PostToolUse Bash): `python3 $CLAUDE_PROJECT_DIR/.claude/hooks/build_orchestrator_event_json.py` → rebuilds `events/event.json` after discovery

---

## Data Guardrails

See `.claude/filters/rules.json` for:
- Forbidden patterns (lookahead bias blockers)
- PIT date fields per data source

---

## Output

**Events manifest**: `earnings-analysis/Companies/{TICKER}/events/event.json` (rebuilt every run)
**Prediction**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/prediction/{context.json,result.json}`
**Attribution**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/attribution/{context.json,result.json}`

---

## Invariants (Must Always Hold)

- If `prediction/result.json` exists, prediction is skipped.
- `prediction/context.json` is written only if missing (never overwritten by orchestrator).
- If `attribution/result.json` exists, attribution is skipped.

---

*Version 1.0 | 2026-02-04 | Initial structured format*
