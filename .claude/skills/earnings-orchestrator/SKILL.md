---
name: earnings-orchestrator
description: Predict stock direction post 8-K earnings & refine using 10-Q/10-K outcomes
model: opus
permissionMode: dontAsk
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

**Goal**: Predict stock direction post 8-K earnings release & refine predictions using 10-Q/10-K filing and actual return outcomes.

---

## Triggers

Invoke when user asks about:
- "Run earnings prediction for {TICKER}"
- "Predict {TICKER} earnings reaction"

---

## Workflow (7 Steps)

### Step 1: Discovery
Run discovery scripts to identify earnings events and data sources.

### Step 2: Task Creation
Create all tasks upfront with proper blockedBy dependencies.

### Step 3: Parallel Spawn

### Step 4: Cross-Tier Polling

### Step 5: Validation Gate
TaskGet all expected tasks, validate format (18 fields guidance, 12 fields judge).

### Step 6: Aggregation
Write validated results to CSVs, update processed caches.

### Step 7: Completion
Echo ORCHESTRATOR_COMPLETE {TICKER} for thinking hook.

---

## Scripts

Available in `scripts/earnings/`:
- `get_earnings.py` - Get earnings events for ticker

---

## Hooks

- `PostToolUse`: `.claude/hooks/build-thinking-on-complete.sh` - Builds thinking files on completion

---

## Data Guardrails

See `.claude/filters/rules.json` for:
- Forbidden patterns (lookahead bias blockers)
- PIT date fields per data source

---

## Output

**Guidance**: `earnings-analysis/Companies/{TICKER}/guidance.csv`
**News**: `earnings-analysis/Companies/{TICKER}/news.csv`
**Processed Cache**: `earnings-analysis/guidance_processed.csv`, `earnings-analysis/news_processed.csv`

---

## Invariants (Must Always Hold)

- Every task has TASK_ID before spawning
- No `run_in_background` usage
- Caches update only after confirmed CSV writes
- Validation gate must pass before cache update

---

*Version 1.0 | 2026-02-04 | Initial structured format*
