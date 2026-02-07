---
name: earnings-prediction
description: Predicts stock direction/magnitude at T=0 (report release). Uses PIT data only. Run before earnings-attribution.
context: fork
allowed-tools: Read, Write, Grep, Glob, Bash, TodoWrite, Skill
model: claude-opus-4-5
permissionMode: dontAsk
---

# Earnings Prediction

**Goal**: Predict stock direction and magnitude before market reacts, using point-in-time data only.

**Thinking**: ALWAYS use `ultrathink` for maximum reasoning depth.

**Input**: Accession number of 8-K earnings filing

**When called by earnings-orchestrator (required in pipeline)**:
- `ticker` (from metadata)
- `filing_datetime` (PIT anchor)
- `quarter_label` (format: `Q{N}_FY{YYYY}`) — used to set `{quarter}` and `{year}` in consensus queries

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

## Workflow (6 Steps)

Use TodoWrite to track progress. Mark each step `in_progress` before starting, `completed` immediately after.

**IMPORTANT**: Read `./QUERIES.md` and execute the exact commands shown there. Do not modify them.

### Preflight: Enforce PIT Filtering (MANDATORY)

Before Step 1:
1. Read `./QUERIES.md`
2. **If it does not contain `[PIT:`**, STOP and report: "PIT filtering is disabled. Run `./enable-filter.sh` and retry."

### Step 1: Get Filing Metadata

Execute the `metadata` query from QUERIES.md.

Extract: ticker, filing_datetime (this becomes your PIT).

**Pipeline rule**: If `ticker`, `filing_datetime`, or `quarter_label` were provided by the orchestrator:
- Use them as authoritative inputs.
- Verify the metadata query matches; if it does not, compare **date-only (YYYY-MM-DD)**.  
  - If date-only matches, proceed.  
  - If date-only still differs, **STOP** and report the mismatch.
- Parse `{quarter}` and `{year}` from `quarter_label` (e.g., `Q2_FY2023` → quarter=2, year=2023).

Set `PIT = filing_datetime` (from orchestrator or metadata).

### Step 2: Load Guidance + News Context (PIT)

Read these files:
- `earnings-analysis/Companies/{TICKER}/guidance.csv`
- `earnings-analysis/Companies/{TICKER}/news.csv`

Filter (PIT‑safe):
- Guidance rows where `given_date <= filing_datetime` **and** `quarter == quarter_label`
- News rows where `source_pub_date <= filing_datetime` **and** `quarter == quarter_label`
  - If `source_pub_date` is empty, fall back to `date`

Summarize relevant guidance/news for use in prediction reasoning (do not change the data).

**If either file is missing**: STOP and report (the orchestrator must create header‑only files when no data exists).

### Step 3: Get Actual Results from Filing

Execute the `exhibit` query from QUERIES.md.

Extract: Actual EPS, actual revenue, any guidance.

### Step 4: Get Historical Context (PIT)

Execute these queries from QUERIES.md: `xbrl`, `transcript`, `news`, `entity`

### Step 5: Get Consensus Estimates (AV Earnings + PIT)

1) **Alpha Vantage EARNINGS (primary for EPS)**  
Execute the `consensus_av_earnings` query from QUERIES.md.

Use AV **EPS consensus** only if:
- The quarterly record has `reportedDate <= filing_datetime`, and
- The record is the closest match to the filing date.

2) **Perplexity (PIT‑safe)**
Execute the `consensus_ppx` query from QUERIES.md.

Use Perplexity for:
- **Revenue consensus** (always), and
- **EPS consensus** if AV EARNINGS is missing or ambiguous.

**If EPS consensus is missing from both**, STOP and report missing EPS consensus.

### Step 6: Make Prediction

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

## After Prediction (REQUIRED STEPS)

### Step 7: Save Report & Append to CSV
Save the full analysis (metadata, actuals, historical context, consensus, surprise calculations, rationale, and prediction) to `earnings-analysis/Companies/{TICKER}/pre_{accession_no}.md`, then append prediction to `earnings-analysis/predictions.csv` (see CSV Output section).

### Step 8: Build Thinking Index (MANDATORY - DO NOT SKIP)

**This step is REQUIRED.** Execute this exact command:

```bash
python3 scripts/build-thinking-index.py {accession_no}
```

Replace `{accession_no}` with the actual accession number from your analysis (e.g., `0001234567-24-000001`).

This extracts thinking from all sessions and sub-agents and saves to Obsidian.

### Step 9: Attribution (Later)
Run `/earnings-attribution` separately to fill actual_* columns and verify prediction.

---

## Toggle Filtering

```bash
# In .claude/skills/earnings-prediction/
./enable-filter.sh   # PIT filtering ON (default)
./disable-filter.sh  # Direct mode (no filtering)
```

State persists until you run the other script.

---

## Session & Subagent History (Shared CSV)

**History file**: `.claude/shared/earnings/subagent-history.csv` (shared with earnings-attribution)

**Format**: See [subagent-history.md](../../shared/earnings/subagent-history.md) for full documentation.

```csv
accession_no,skill,created_at,primary_session_id,agent_type,agent_id,resumed_from
0001514416-24-000020,prediction,2026-01-13T09:00:00,aaa11111,primary,,
0001514416-24-000020,prediction,2026-01-13T09:01:05,aaa11111,neo4j-entity,abc12345,
```

**On analysis start**:
1. Read CSV (create with header if doesn't exist)
2. Append `primary` row: `{accession},prediction,{timestamp},{session_id},primary,,`

**Before calling a subagent**:
1. Query latest agent ID: `grep "{accession}" | grep ",{agent_type}," | tail -1 | cut -d',' -f6`
2. If agent ID exists → can use `resume: <id>` in Task call
3. If want fresh session → proceed without resume

**After each subagent completes**:
1. Extract `agentId` from Task response
2. Append row: `{accession},prediction,{timestamp},{session_id},{agent_type},{agent_id},{resumed_from}`

---

*Version 2.2 | 2026-01-16 | Made thinking index build mandatory (Step 7)*
