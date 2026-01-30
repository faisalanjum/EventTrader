---
name: earnings-orchestrator
description: Master orchestrator for batch earnings analysis
# No context: fork - orchestrator is always entry point, enables Task tool for parallel execution
allowed-tools:
  - Task
  - TaskCreate
  - TaskList
  - TaskGet
  - TaskUpdate
  - Bash
  - Write
  - Read
  - Edit
  - EnterPlanMode
  - ExitPlanMode
permissionMode: dontAsk
---

# Earnings Orchestrator

## Input

`$ARGUMENTS` = `TICKER`

- TICKER: Company ticker (required)

## Task - MUST COMPLETE ALL STEPS

### Step 0: Record Start Time

```bash
echo "=== START: $(date '+%Y-%m-%d %H:%M:%S') ==="
```

### Step 1: Get Earnings Data

```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/scripts/earnings/get_earnings.py {TICKER}
```

**Output columns:** accession|date|fiscal_year|fiscal_quarter|market_session|daily_stock|daily_adj|sector_adj|industry_adj|trailing_vol|vol_days|vol_status

**Parse:** Extract E1 (first data row after header), E2 (second data row after header). The script returns data sorted oldest-to-newest, so E1 is the OLDEST quarter, E2 is the second oldest. Only process these two quarters. Note `trailing_vol` for each.

**If ERROR returned:** Stop and report error to user.

### Step 1b: Check News Cache

Check `earnings-analysis/news_processed.csv` for {TICKER}.

- Read CSV (format: `ticker|quarter|fiscal_year|processed_date`)
- Find row where `ticker={TICKER}` AND `quarter={E1.fiscal_quarter}` AND `fiscal_year=FY{E1.fiscal_year}`
- If row exists → Q1 already done, skip Steps 2-3b entirely
- If no matching row → continue to Step 2
- Repeat check for Q2

### Step 2: Get Significant Moves for Q1

Calculate:
- `START` = E1 date minus 3 months (or earliest available data)
- `END` = E1 date (just the date part, e.g., 2024-02-01)

```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/scripts/earnings/get_significant_moves.py {TICKER} {START} {END} {E1.trailing_vol}
```

**Output columns:** date|daily_stock|daily_macro|daily_adj

**Parse:** List of dates with significant moves.

**If OK|NO_MOVES returned:** No significant moves for Q1, skip to Step 4.

### Step 3: Concurrent News Analysis for Q1 (BZ → WEB → PPX → JUDGE)

**Phase 1: Create ALL tasks upfront with blockedBy dependencies**

For EACH significant date from Step 2, create all 4 tasks with dependency chain:

1. **Create BZ task** via TaskCreate:
   - `subject`: `"BZ-{QUARTER} {TICKER} {DATE}"` (e.g., "BZ-Q4_FY2022 NOG 2023-01-03")
   - `description`: `"pending"`
   - `activeForm`: `"Analyzing {TICKER} {DATE}"`
   - Note the task ID as `BZ_ID`

2. **Create WEB task** via TaskCreate:
   - `subject`: `"WEB-{QUARTER} {TICKER} {DATE}"`
   - `description`: `"{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ}"`
   - `activeForm`: `"Web research {TICKER} {DATE}"`
   - Then call TaskUpdate with `addBlockedBy: ["{BZ_ID}"]`
   - Note the task ID as `WEB_ID`

3. **Create PPX task** via TaskCreate:
   - `subject`: `"PPX-{QUARTER} {TICKER} {DATE}"`
   - `description`: `"{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ}"`
   - `activeForm`: `"Perplexity research {TICKER} {DATE}"`
   - Then call TaskUpdate with `addBlockedBy: ["{WEB_ID}"]`
   - Note the task ID as `PPX_ID`

4. **Create JUDGE task** via TaskCreate:
   - `subject`: `"JUDGE-{QUARTER} {TICKER} {DATE}"`
   - `description`: `"pending"`
   - `activeForm`: `"Validating {TICKER} {DATE}"`
   - Then call TaskUpdate with `addBlockedBy: ["{PPX_ID}"]`
   - Note the task ID as `JUDGE_ID`

**Phase 2: Spawn BZ agents with all task IDs**

For EACH significant date, spawn BZ agent with all 4 task IDs:
```
subagent_type: "news-driver-bz"
description: "BZ news {TICKER} {DATE}"
prompt: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ} TASK_ID={BZ_ID} WEB_TASK_ID={WEB_ID} PPX_TASK_ID={PPX_ID} JUDGE_TASK_ID={JUDGE_ID} QUARTER={E1.fiscal_quarter}_FY{E1.fiscal_year}"
```

**IMPORTANT:**
- Create ALL tasks for ALL dates first, THEN spawn ALL BZ agents in parallel
- BZ agents mark WEB+PPX as SKIPPED if they find answer (external_research=false)
- DO NOT WAIT for BZ agents - proceed immediately to Phase 3

**Phase 3: Concurrent escalation loop**

Immediately after spawning BZ agents, enter this loop:

```
WHILE any Q1 tasks (BZ-*, WEB-*, PPX-*, JUDGE-*) are pending or in_progress:
  1. Check TaskList for WEB-{QUARTER} {TICKER} tasks that are:
     - status = "pending" AND blockedBy is empty (auto-unblocked when BZ completed)
     - NOT already spawned
     → For each such WEB task:
       - Get task via TaskGet to read description: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ}"
       - Extract QUARTER from task subject
       - Find corresponding PPX and JUDGE task IDs from TaskList
       - Spawn:
         subagent_type: "news-driver-web"
         prompt: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ} TASK_ID={WEB_ID} PPX_TASK_ID={PPX_ID} JUDGE_TASK_ID={JUDGE_ID} QUARTER={QUARTER}"
     → WEB agents mark PPX as SKIPPED if confidence >= 50

  2. Check TaskList for PPX-{QUARTER} {TICKER} tasks that are:
     - status = "pending" AND blockedBy is empty (auto-unblocked when WEB completed)
     - NOT already spawned
     → For each such PPX task:
       - Get task via TaskGet to read description
       - Extract QUARTER from task subject
       - Find corresponding JUDGE task ID from TaskList
       - Spawn:
         subagent_type: "news-driver-ppx"
         prompt: "{TICKER} {DATE} {DAILY_STOCK} {DAILY_ADJ} TASK_ID={PPX_ID} JUDGE_TASK_ID={JUDGE_ID} QUARTER={QUARTER}"
     → PPX agents always update JUDGE with result (final tier)

  3. Check TaskList for JUDGE-{QUARTER} {TICKER} tasks that are:
     - status = "pending" AND blockedBy is empty (auto-unblocked when PPX completed or skipped)
     - NOT already spawned
     - description starts with "READY:" (has result to validate)
     → For each such JUDGE task:
       - Spawn:
         subagent_type: "news-driver-judge"
         prompt: "TASK_ID={JUDGE_ID}"
     → JUDGE agents validate and update task with final confidence

  4. Brief pause (2-3 seconds), then repeat
END WHILE
```

Track which task IDs you've already spawned agents for to avoid duplicates.

**Note on SKIPPED tasks:** When BZ or WEB finds a confident answer, they mark downstream tasks as "completed" with description="SKIPPED: {tier} found answer". This auto-unblocks the next task in chain (JUDGE for BZ skip, JUDGE for WEB skip).

**Phase 4: Collect all results**

When all Q1 tasks are completed, collect results from JUDGE-* tasks via TaskGet. Read the `description` field — it contains the validated 12-field pipe-delimited result line (with attr_confidence, pred_confidence, and judge_notes).

**Note:** Each date has exactly one JUDGE task with the final validated result. BZ/WEB/PPX tasks contain intermediate results.

### Step 3b: Save Q1 Results

1. Create directory if needed: `earnings-analysis/Companies/{TICKER}/`
2. Append Q1 results to `earnings-analysis/Companies/{TICKER}/news.csv`:
   - Add `quarter` column with value `{E1.fiscal_quarter}_FY{E1.fiscal_year}` (e.g., `Q1_FY2024`)
   - Format: `quarter|date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes`
   - Create file with header if it doesn't exist
3. Update `earnings-analysis/news_processed.csv`:
   - Format: `ticker|quarter|fiscal_year|processed_date`
   - Append row: `{TICKER}|{E1.fiscal_quarter}|FY{E1.fiscal_year}|{today YYYY-MM-DD}`
   - Create file with header if it doesn't exist

### Step 4: Concurrent News Analysis for Q2 (BZ → WEB → PPX → JUDGE)

Calculate:
- `START` = E1 date + 1 day (exclude E1 earnings reaction)
- `END` = E2 date (exclusive, excludes E2 earnings reaction)

Run `get_significant_moves.py {TICKER} {START} {END} {E2.trailing_vol}` then follow the same concurrent pattern as Step 3:
- Phase 1: Create ALL 4 tasks (BZ, WEB, PPX, JUDGE) per date with blockedBy dependencies
- Phase 2: Spawn BZ agents with all 4 task IDs
- Phase 3: Concurrent escalation loop - spawn WEB/PPX/JUDGE as they auto-unblock
- Phase 4: Collect all Q2 results when complete

Use `QUARTER={E2.fiscal_quarter}_FY{E2.fiscal_year}` for all Q2 tasks.

### Step 4b: Save Q2 Results

Same as Step 3b but for Q2:
1. Append to `earnings-analysis/Companies/{TICKER}/news.csv` with `quarter={E2.fiscal_quarter}_FY{E2.fiscal_year}`
2. Append to `news_processed.csv`: `{TICKER}|{E2.fiscal_quarter}|FY{E2.fiscal_year}|{today YYYY-MM-DD}`

### Step 5: Return Combined Results

```
=== EARNINGS ORCHESTRATOR: {TICKER} ===

--- EARNINGS DATA ---
E1: {accession} | {date} | FY{fiscal_year} {fiscal_quarter} | {daily_adj}% adj | vol={trailing_vol}% ({vol_days}d) {vol_status}
E2: {accession} | {date} | FY{fiscal_year} {fiscal_quarter} | {daily_adj}% adj | vol={trailing_vol}% ({vol_days}d) {vol_status}
...

--- Q1 ANALYSIS ({START} to {E1}) ---
Filter: |stock|>=4%, |adj|>=max(2×{trailing_vol}%,3%)
Significant dates: {count}

date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes
...

--- Q2 ANALYSIS ({E1} to {E2}) ---
Filter: |stock|>=4%, |adj|>=max(2×{trailing_vol}%,3%)
Significant dates: {count}

date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes
...

--- SUMMARY ---
Total dates analyzed: {N}
Explained by Benzinga: {B}
Explained by WebSearch: {W}
Explained by Perplexity: {P}
Still unknown (confidence=0): {U}
Validated by Judge: {J}

=== COMPLETE ===
```

### Step 6: Build Thinking Files

After completing all analysis, generate thinking files for Obsidian:

```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/scripts/earnings/build-news-thinking.py --ticker {TICKER}
```

The script auto-detects the most recent session for this ticker. Output:
- `Companies/{TICKER}/thinking/{QUARTER}/_timeline.md`
- `Companies/{TICKER}/thinking/{QUARTER}/news/{date}.md` for each date

### Step 7: Record End Time

```bash
echo "=== END: $(date '+%Y-%m-%d %H:%M:%S') ==="
```

## Rules

- **Full row replacement** - When a later tier returns a result, use its COMPLETE output. PPX replaces WEB, WEB replaces BZ. Never mix fields across tiers. Judge outputs 12-field line.
- **Always run get_earnings.py first** - provides trailing_vol for each quarter
- **Skip if done** - check news_processed.csv, skip quarters already processed
- **All sub-agents in parallel** - spawn one per date, no cap
- **Q1 complete before Q2** - finish all 4 tiers (BZ → WEB → PPX → JUDGE) + save for Q1, then Q2
- **Extract date only** - E1 date "2024-02-01T16:30:33-05:00" → use "2024-02-01"
- **Preserve news_id EXACTLY** - Copy URLs verbatim. NEVER shorten, summarize, or create short IDs. If sub-agent returns a URL, save the full URL exactly as returned.
- **Pass through raw output** - don't summarize or lose data
- **Always save results** - append to news.csv and mark done in news_processed.csv

## Error Handling

Script errors return structured format: `ERROR|CODE|MESSAGE|HINT`

If any script returns ERROR:
1. Log the error in output
2. Try to continue with remaining steps if possible
3. Report all errors in summary

## Example

Input: `AAPL`

Flow:
1. get_earnings.py AAPL → E1=2024-02-01 (Q1_FY2024, vol=0.90), E2=2024-05-02 (Q2_FY2024, vol=0.99)
2. Check news_processed.csv → no row for AAPL|Q1|FY2024 → process Q1
3. get_significant_moves.py AAPL 2023-11-01 2024-02-01 0.90 → internally: |stock|>=4%, |adj|>=max(2×0.90,3)=3%
4. Spawn news-driver-bz for each significant date → some explained (create JUDGE), some create WEB tasks
5. Spawn news-driver-web for each WEB task → some explained (create JUDGE), some create PPX tasks
6. Spawn news-driver-ppx for each PPX task → all create JUDGE tasks
7. Spawn news-driver-judge for each JUDGE task → validates and returns final confidence
8. Save Q1 to Companies/AAPL/news.csv (from JUDGE results), mark Q1_FY2024 done
9. Check news_processed.csv → row exists for AAPL|Q2|FY2024 → skip Q2
10. Return results (Q1 only, Q2 was cached)
