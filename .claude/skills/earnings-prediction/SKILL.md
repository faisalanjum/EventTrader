---
name: earnings-prediction
description: Predicts stock direction/magnitude at T=0 (report release). Uses PIT data only. Run before earnings-attribution.
allowed-tools: Read, Write, Grep, Glob, Bash, TodoWrite, Task, Skill
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
- Consensus estimates from Perplexity (filtered by article date)

**NOT Allowed**:
- Return data (daily_stock, hourly_stock) — that's what we're predicting
- Post-filing news reactions
- Post-filing analyst commentary

---

## Data Isolation Architecture

**ALL data queries go through the filter agent.** This includes Neo4j AND Perplexity.

```
YOU (earnings-prediction)
        │
        │ /filtered-data --agent {source} --query "[PIT: X] ..."
        ▼
┌─────────────────────────────────────┐
│       FILTER AGENT                  │
│                                     │
│  Sources: neo4j-*, perplexity-search│
│                                     │
│  Validates:                         │
│  1. Forbidden patterns              │
│  2. PIT compliance (dates <= PIT)   │
│                                     │
│  You NEVER see contaminated data    │
└─────────────────────────────────────┘
        │
        │ Clean data only
        ▼
YOU (continue with clean data)
```

### Why This Matters

Return data (daily_stock, hourly_stock, etc.) is what we're trying to predict. Post-filing articles mention stock reactions. If either enters your context, the prediction is contaminated. The filter agent ensures you never see it.

---

## Workflow (5 Steps)

Use TodoWrite to track progress. Mark each step `in_progress` before starting, `completed` immediately after.

### Step 1: Get Filing Metadata

```
/filtered-data --agent neo4j-report --query "8-K {accession} metadata only (ticker, filed datetime, items)"
```

Extract: ticker, filing_datetime (this becomes your PIT).

### Step 2: Get Actual Results from Filing

```
/filtered-data --agent neo4j-report --query "EX-99.1 content for {accession}"
```

Extract: Actual EPS, actual revenue, any guidance.

### Step 3: Get Historical Context (PIT)

| Data | Command |
|------|---------|
| Prior financials | `/filtered-data --agent neo4j-xbrl --query "[PIT: {filing_datetime}] Last 4 quarters EPS/Revenue for {ticker}"` |
| Prior transcripts | `/filtered-data --agent neo4j-transcript --query "[PIT: {filing_datetime}] Last 2 transcripts for {ticker}"` |
| Pre-filing news | `/filtered-data --agent neo4j-news --query "[PIT: {filing_datetime}] News for {ticker} past 30 days"` |
| Corporate actions | `/filtered-data --agent neo4j-entity --query "[PIT: {filing_datetime}] Dividends/splits for {ticker} past 90 days"` |

### Step 4: Get Consensus Estimates

Route through filter to catch post-dated articles:

```
/filtered-data --agent perplexity-search --query "[PIT: {filing_datetime}] {ticker} Q{quarter} FY{year} EPS revenue estimate consensus"
```

The filter will reject any articles dated after your PIT.

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

## To Disable Data Isolation

Set `"enabled": false` in `/home/faisal/EventMarketDB/.claude/filters/rules.json`

The filter agent becomes a pure passthrough (no validation, no retries).

---

*Version 1.7 | 2026-01-14 | Restricted to perplexity-search only (other Perplexity tools lack structured dates for PIT validation)*
