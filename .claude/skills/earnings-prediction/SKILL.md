---
name: earnings-prediction
description: Predicts stock direction/magnitude at T=0 (report release). Uses PIT data only. Run before earnings-attribution.
allowed-tools: Read, Write, Grep, Glob, Bash, TodoWrite, Task, mcp__perplexity__perplexity_search, mcp__perplexity__perplexity_ask, mcp__perplexity__perplexity_reason, mcp__perplexity__perplexity_research
model: claude-opus-4-5
---

# Earnings Prediction

**Goal**: Predict stock direction and magnitude before market reacts, using point-in-time data only.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth.

**Input**: Accession number of 8-K earnings filing

---

## Prediction Output

| Field | Values |
|-------|--------|
| Direction | up / down |
| Magnitude | small (0-2%) / medium (2-5%) / large (5%+) |
| Confidence | high / medium / low |

**Tiny surprises (<1%)**: Predict small_up or small_down based on sign, use low confidence.

---

## PIT Rules (Critical)

All sub-agent queries MUST use PIT filtering: `[PIT: {filing_datetime}]`

**Allowed**:
- 8-K filing content (the actual results)
- Historical financials (prior 10-K/10-Q via XBRL)
- Prior earnings transcripts
- Pre-filing news
- Consensus estimates from Perplexity

**NOT Allowed**:
- Return data (daily_stock, hourly_stock) — that's what we're predicting
- Post-filing news reactions
- Post-filing analyst commentary

---

## Leakage Prevention

**Critical**: Return data must never enter the prediction context.

1. **Select test cases from** `predictions_queue.csv` (no returns), NOT `8k_fact_universe.csv`
2. **Fresh conversation**: If universe file was shown earlier, results may be contaminated
3. **Neo4j-report prompt**: Always include "NO returns" - agent must exclude pf.daily_stock, pf.hourly_stock
4. **Perplexity limitation**: May return post-hoc articles mentioning stock movement - note in confidence assessment if detected

---

## Workflow (5 Steps)

Use TodoWrite to track progress. Mark each step `in_progress` before starting, `completed` immediately after.

### Step 1: Get Filing Metadata

Use `neo4j-report` to get filing info (NO returns):

```
8-K {accession} metadata only (ticker, filed datetime, items)
```

Extract: ticker, filing_datetime (this becomes your PIT).

### Step 2: Get Actual Results from Filing

Use `neo4j-report` to get exhibit content:

```
EX-99.1 content for {accession}
```

Extract: Actual EPS, actual revenue, any guidance.

### Step 3: Get Historical Context (PIT)

Spawn sub-agents with PIT prefix:

| Data | Agent | Prompt |
|------|-------|--------|
| Prior financials | neo4j-xbrl | `[PIT: {filing_datetime}]` Last 4 quarters EPS/Revenue for {ticker} |
| Prior transcripts | neo4j-transcript | `[PIT: {filing_datetime}]` Last 2 transcripts for {ticker} |
| Pre-filing news | neo4j-news | `[PIT: {filing_datetime}]` News for {ticker} past 30 days |
| Corporate actions | neo4j-entity | `[PIT: {filing_datetime}]` Dividends/splits for {ticker} past 90 days |

### Step 4: Get Consensus Estimates

Query Perplexity for pre-filing consensus:

```
mcp__perplexity__search:
  query: "{ticker} Q{quarter} FY{year} EPS revenue estimate consensus before {filing_date}"
```

### Step 5: Make Prediction

Calculate surprise:
```
Surprise % = ((Actual - Consensus) / |Consensus|) × 100
```

Reason from the data. Consider: surprise magnitude, guidance direction, historical patterns, sector context. Output prediction with reasoning.

---

## CSV Output

**File**: `earnings-analysis/predictions.csv`

**Columns**:
```csv
accession_no,ticker,filing_datetime,prediction_datetime,predicted_direction,predicted_magnitude,confidence,primary_reason,actual_direction,actual_magnitude,actual_return,correct
```

**Append** each prediction as a new row. Leave actual_* columns empty (filled by attribution later).

### CSV Append

1. Read existing CSV with Read tool
2. Append new row with Write tool (rewrite full file)
3. Escape commas in primary_reason with quotes: `"reason with, comma"`

**First run**: If CSV doesn't exist, create it with header row first.

---

## After Prediction

1. **Append to CSV** with prediction details
2. **Run attribution later** to fill actual_* columns and verify

---

*Version 1.3 | 2026-01-13 | Added leakage prevention*
