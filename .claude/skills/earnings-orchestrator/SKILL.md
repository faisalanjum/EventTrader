---
name: earnings-orchestrator
description: Master orchestrator for batch earnings analysis
# No context: fork - orchestrator is always entry point, enables Task tool for parallel execution
allowed-tools:
  - Task
  - Bash
  - Write
  - Read
permissionMode: dontAsk
---

# Earnings Orchestrator

## Input

`$ARGUMENTS` = `TICKER [SIGMA]`

- TICKER: Company ticker (required)
- SIGMA: Threshold multiplier (default: `2` meaning 2σ)

## Task - MUST COMPLETE ALL STEPS

### Step 1: Get Earnings Data

```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/scripts/earnings/get_earnings.py {TICKER}
```

**Output columns:** accession|date|fiscal_year|fiscal_quarter|market_session|daily_stock|daily_adj|sector_adj|industry_adj|trailing_vol|vol_days|vol_status

**Parse:** Extract E1 (first row), E2 (second row), etc. Note `trailing_vol` for each.

**If ERROR returned:** Stop and report error to user.

### Step 1b: Check News Cache

Check `earnings-analysis/news_processed.csv` for {TICKER} row.

- Read CSV, find row where `ticker={TICKER}`
- Check column `{E1.fiscal_quarter}_FY{E1.fiscal_year}` (e.g., `Q1_FY2024`)
- If column has a date → Q1 already done, skip Steps 2-3c entirely
- If column empty or row missing → continue to Step 2
- Repeat check for Q2 column

### Step 2: Get Significant Moves for Q1

Calculate:
- `START` = E1 date minus 3 months (or earliest available data)
- `END` = E1 date (just the date part, e.g., 2024-02-01)
- `THRESHOLD` = SIGMA × E1.trailing_vol (e.g., 2 × 0.92 = 1.84)

```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/scripts/earnings/get_significant_moves.py {TICKER} {START} {END} {THRESHOLD}
```

**Output columns:** date|daily_stock|daily_macro|daily_adj

**Parse:** List of dates with significant moves.

**If OK|NO_MOVES returned:** No significant moves for Q1, skip to Step 4.

### Step 3a: Benzinga News Analysis (PARALLEL)

For EACH significant date from Step 2, spawn a `bz-news-driver` sub-agent.

**Task tool call for each date:**
```
subagent_type: "bz-news-driver"
description: "BZ news {TICKER} {DATE}"
prompt: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ}"
```

**IMPORTANT:**
- Max 10 sub-agents in parallel. If >10 dates, batch: first 10 → wait → next 10
- All sub-agents return: `date|news_id|title|driver|confidence|daily_stock|daily_adj|market_session|source|external_research`

**Collect all results. Separate into:**
- `explained`: where `external_research=false`
- `needs_research`: where `external_research=true`

### Step 3b: External Research for Q1 Gaps (PARALLEL)

For EACH date in `needs_research` from Step 3a, spawn an `external-news-driver` sub-agent.

**Task tool call for each gap date:**
```
subagent_type: "external-news-driver"
description: "External research {TICKER} {DATE}"
prompt: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ}"
```

**IMPORTANT:**
- Max 10 sub-agents in parallel. If >10 dates, batch: first 10 → wait → next 10
- Returns same format with `source=websearch` or `source=perplexity`

**Merge results:** Replace `needs_research` items with researched results.

### Step 3c: Save Q1 Results

1. Create directory if needed: `earnings-analysis/Companies/{TICKER}/`
2. Append Q1 results to `earnings-analysis/Companies/{TICKER}/news.csv`:
   - Add `quarter` column with value `{E1.fiscal_quarter}_FY{E1.fiscal_year}` (e.g., `Q1_FY2024`)
   - Format: `quarter|date|news_id|title|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date`
   - Create file with header if it doesn't exist
3. Update `earnings-analysis/news_processed.csv`:
   - Add column `{E1.fiscal_quarter}_FY{E1.fiscal_year}` if missing
   - Add row for {TICKER} if missing
   - Set cell to today's date (YYYY-MM-DD)

### Step 4a: Repeat Benzinga Analysis for Q2

Calculate:
- `START` = E1 date
- `END` = E2 date
- `THRESHOLD` = SIGMA × E2.trailing_vol

Run `get_significant_moves.py` and spawn `bz-news-driver` sub-agents for Q2 dates (same as Step 3a).

### Step 4b: External Research for Q2 Gaps (PARALLEL)

For dates where `external_research=true` from Step 4a, spawn `external-news-driver` sub-agents (same as Step 3b).

### Step 4c: Save Q2 Results

Same as Step 3c but for Q2:
1. Append to `earnings-analysis/Companies/{TICKER}/news.csv` with `quarter={E2.fiscal_quarter}_FY{E2.fiscal_year}`
2. Update `news_processed.csv` with Q2 column marked done

### Step 5: Return Combined Results

```
=== EARNINGS ORCHESTRATOR: {TICKER} ===

SIGMA: {SIGMA}σ

--- EARNINGS DATA ---
E1: {accession} | {date} | FY{fiscal_year} {fiscal_quarter} | {daily_adj}% adj | vol={trailing_vol} ({vol_days}d) {vol_status}
E2: {accession} | {date} | FY{fiscal_year} {fiscal_quarter} | {daily_adj}% adj | vol={trailing_vol} ({vol_days}d) {vol_status}
...

--- Q1 ANALYSIS ({START} to {E1}) ---
Threshold: {THRESHOLD}% ({SIGMA}σ × {trailing_vol})
Significant dates: {count}

date|news_id|title|driver|confidence|daily_stock|daily_adj|market_session|source|external_research
...

--- Q2 ANALYSIS ({E1} to {E2}) ---
Threshold: {THRESHOLD}% ({SIGMA}σ × {trailing_vol})
Significant dates: {count}

date|news_id|title|driver|confidence|daily_stock|daily_adj|market_session|source|external_research
...

--- SUMMARY ---
Total dates analyzed: {N}
Explained by Benzinga: {B}
Explained by WebSearch/Perplexity: {W}
Still unknown (confidence=0): {U}

=== COMPLETE ===
```

## Rules

- **Always run get_earnings.py first** - need trailing_vol to calculate threshold
- **Skip if done** - check news_processed.csv, skip quarters already processed
- **Threshold formula:** SIGMA × trailing_vol (not fixed percentage)
- **Max 10 parallel sub-agents** - batch if more dates
- **Q1 complete before Q2** - finish bz + external + save for Q1, then Q2
- **Extract date only** - E1 date "2024-02-01T16:30:33-05:00" → use "2024-02-01"
- **Pass through raw output** - don't summarize or lose data
- **Always save results** - append to news.csv and mark done in news_processed.csv

## Error Handling

Script errors return structured format: `ERROR|CODE|MESSAGE|HINT`

If any script returns ERROR:
1. Log the error in output
2. Try to continue with remaining steps if possible
3. Report all errors in summary

## Example

Input: `AAPL 2`

Flow:
1. get_earnings.py AAPL → E1=2024-02-01 (Q1_FY2024, vol=0.90), E2=2024-05-02 (Q2_FY2024, vol=0.99)
2. Check news_processed.csv → Q1_FY2024 empty → process Q1
3. Q1 threshold = 2 × 0.90 = 1.80%
4. get_significant_moves.py AAPL 2023-11-01 2024-02-01 1.80 → 5 dates
5. Spawn 5 bz-news-driver agents → 3 explained, 2 need research
6. Spawn 2 external-news-driver agents for gaps → 1 found, 1 unknown
7. Save Q1 to Companies/AAPL/news.csv, mark Q1_FY2024 done
8. Check news_processed.csv → Q2_FY2024 has date → skip Q2
9. Return results (Q1 only, Q2 was cached)
