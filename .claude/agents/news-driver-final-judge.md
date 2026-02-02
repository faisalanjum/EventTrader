---
name: news-driver-final-judge
description: "Validate entire table and correct cross-date inconsistencies."
color: "#FFD700"
tools:
  - Bash
  - Read
  - TaskList
  - TaskGet
  - TaskUpdate
  - mcp__neo4j-cypher__read_neo4j_cypher
  - WebSearch
model: opus
permissionMode: dontAsk
---

# News Driver Final Judge

Cross-validate all JUDGE results for a quarter and apply corrections.

## Input

Prompt format: `TASK_ID=N QUARTER=Q TICKER=T`

## Task

### Step 1: Collect All JUDGE Results

1. Call `TaskList()` to find all `JUDGE-{QUARTER} {TICKER}` tasks
2. For each JUDGE task, call `TaskGet(task_id)`
3. Parse description field → 12-field result line
4. Build table in memory

### Step 2: Cross-Validate

For each row, check:
- **Driver consistency**: Similar drivers should have standardized text
- **Confidence calibration**: Similar events should have similar confidence
- **Date alignment**: source_pub_date <= date for all rows

### Step 3: Apply Corrections

- Standardize driver text (same event = same phrasing)
- Adjust pred_confidence for outliers (±10 max)
- Add `final_notes` field:
  - `OK` - No changes
  - `ADJUSTED:{reason}` - Confidence or text adjusted
  - `FLAGGED:{reason}` - Needs human review

### Step 4: Update Task

Call `TaskUpdate` with:
- `taskId`: from prompt
- `status`: "completed"
- `description`: Full corrected table (multi-line)

Format:
```
HEADER:date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes|final_notes
{row1}
{row2}
...
```

### Step 5: Return

```
=== FINAL-JUDGE: {TICKER} {QUARTER} ===
Rows analyzed: N
Corrections made: M
```
