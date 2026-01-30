# Earnings Orchestrator Improvements Plan

**Created**: 2026-01-27
**Last Updated**: 2026-01-27
**Status**: Active

| Status | Count |
|--------|-------|
| Pending | 11 |
| Completed | 13 |
| **Total** | **24** |

---

## Phase 1: Foundation (Do First - Blocks Everything)

| # | Task | Why First | Status |
|---|------|-----------|--------|
| 14 | Clarify E1/E2 ordering (ASC vs DESC) | Must understand data order before any logic | **COMPLETED** |
| 15 | Standardize exhibit_number vs exhibit_type | Queries won't work until fixed | **COMPLETED** |
| 17 | Replace sigma with simple 5% cutoff | Core logic change - affects multiple files | **COMPLETED** |
| 3 | Fix PIT validation hook to extract correct date | Data integrity - wrong PIT = contaminated analysis | **COMPLETED** (verified working) |
| 18 | Add strict CSV output template for driver/confidence | Blocks all sub-agent output work | **COMPLETED** |

### Task Details

**#14 - Clarify E1/E2 ordering**
- Document whether E1 is oldest or newest filing
- Affects: orchestrator logic, date range calculations
- Files: `earnings-orchestrator/SKILL.md`

**#15 - Standardize exhibit_number vs exhibit_type**
- `guidance-inventory/QUERIES.md` uses `exhibit_type`
- `neo4j-report/SKILL.md` uses `exhibit_number`
- Pick one, update all queries

**#17 - Replace sigma with 5% cutoff** ✓ COMPLETED
- Change from: `threshold = SIGMA × trailing_vol`
- Change to: `threshold = 5%` for both `daily_adj` AND `daily_stock`
- Captures moves ≥+5% or ≤-5%
- Files updated:
  - `earnings-orchestrator/SKILL.md` (Step 2)
  - `scripts/earnings/get_significant_moves.py`
  - `.claude/skills/get-bz-news/SKILL.md`
  - `.claude/skills/news-impact/SKILL.md`
- Made #11 (volatility caching) obsolete

**#3 - Fix PIT validation hook**
- Current: extracts first date in command (may be wrong)
- Fix: use explicit `[PIT:DATE]` marker
- File: `.claude/hooks/validate_pit_hook.sh`

**#18 - CSV output template**
- Create strict template with exact columns:
  ```
  date|news_id|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
  ```
- Document data types and validation rules
- All sub-agents must follow same format

---

## Phase 2: Orchestrator Core (After Phase 1)

| # | Task | Blocked By | Status |
|---|------|------------|--------|
| 1 | Fix orchestrator to match tradeEarnings.md design | #14, #15 | pending |
| 2 | Add guidance-inventory invocation to orchestrator | #1 | pending |
| 13 | Add checkpoint/resume to orchestrator | #1 | pending |
| 21 | Fix permission prompts for Q2 file writes | #1 | **COMPLETED** |
| 22 | Show all orchestrator output in Obsidian | — | pending |

### Task Details

**#1 - Fix orchestrator design**
- Current: only does news analysis for Q1/Q2
- Should: run full prediction→attribution loop
- Reference: `tradeEarnings.md` for correct design

**#2 - Add guidance-inventory**
- Q1: call with BUILD mode (all historical)
- Q>=2: call with UPDATE mode (incremental)
- Currently never called

**#13 - Checkpoint/resume**
- Save state after each quarter processed
- Prevents lost work on interruption
- Store in: `earnings-analysis/orchestrator-state/{ticker}.json`

**#21 - Fix Q2 permission prompts (HANDS-FREE)**
- Q1 writes without asking, Q2 asks for permission
- Goal: COMPLETELY HANDS-FREE - no Enter key presses required
- Check `permissionMode` settings on orchestrator AND sub-agents
- Ensure `dontAsk` or `bypassPermissions` propagates to ALL file writes
- Test: run entire orchestrator without any user interaction

**#22 - Show all output in Obsidian**
- Route all orchestrator output to Obsidian for visibility
- News drivers, attribution reports, predictions, summaries
- May use existing `build-thinking-index.py` or create new integration

---

## Phase 3: Sub-agent Quality (Parallel with Phase 2)

| # | Task | Blocked By | Status |
|---|------|------------|--------|
| 4 | Standardize output formats across sub-agents | #18 | pending |
| 5 | Add structured error codes to sub-agents | #4 | pending |
| 16 | Add retry logic to filtered-data | — | pending |
| 19 | Add output verification for news driver attribution | #18 | pending |
| 20 | Add source URL field to CSV output | #18 | **COMPLETED** |
| 24 | Add market_session to external research output | #18 | pending |

### Task Details

**#4 - Standardize output formats**
- bz-news-driver, external-news-driver, news-impact, get-bz-news
- All should use template from #18

**#5 - Structured error codes**
- Format: `ERROR|CODE|MESSAGE|HINT`
- Examples:
  - `ERROR|BZ_NO_NEWS|No Benzinga news for AAPL 2024-01-15|Try external research`
  - `ERROR|PIT_VIOLATION|Source date 2024-01-20 > PIT 2024-01-15|Source discarded`

**#16 - Retry logic for filtered-data**
- Add retry with exponential backoff
- Max 3 retries, 1s/2s/4s delays

**#19 - Output verification**
- Validate: required fields present, confidence 0-100, dates valid, driver not empty
- Could be: hook, script, or inline validation

**#20 - Source URL field** ✓ COMPLETED
- Add `source_url` column to CSV
- Capture actual URLs from WebSearch/Perplexity
- Improves traceability and verification

**#24 - Market session for external research**
- External news driver leaves `market_session` field empty
- Should determine from source publication time if available
- Or mark as "unknown" rather than blank

---

## Phase 4: Data & Config Cleanup

| # | Task | Blocked By | Status |
|---|------|------------|--------|
| 7 | Normalize news_processed.csv structure | — | **COMPLETED** |
| 6 | Move USE_FIRST_TICKERS to config file | — | pending |
| 9 | Add rate limit handling for Perplexity | — | pending |

### Task Details

**#7 - Normalize CSV structure**
- Current: dynamic columns `Q1_FY2024, Q2_FY2025`
- Change to: normalized rows
  ```csv
  ticker,fiscal_quarter,fiscal_year,processed_date
  NOG,Q1,FY2025,2025-01-26
  ```

**#6 - USE_FIRST_TICKERS to config**
- Move 183 hardcoded tickers from `get_earnings.py`
- To: `earnings-analysis/ticker_configs.json`
- Easier maintenance without code changes

**#9 - Perplexity rate limits**
- Document in skills:
  - `perplexity_search`: ~100 req/min
  - `perplexity_research`: ~10 req/min
- Add retry logic: wait 60s on rate limit

---

## Phase 5: Documentation & Polish (Last)

| # | Task | Blocked By | Status |
|---|------|------------|--------|
| 8 | Add batching example to orchestrator docs | #1 | pending |
| 10 | Create automated evidence audit script | — | pending |
| 12 | Improve SDK trigger progress visibility | — | pending |
| 23 | Calculate and track Perplexity API cost per run | — | pending |

### Task Details

**#8 - Batching example**
```markdown
### Batching Example (15 dates)
Batch 1: Task calls for dates 1-10 (single message)
→ Wait for all 10 to complete
Batch 2: Task calls for dates 11-15 (single message)
→ Wait for all 5 to complete
```

**#10 - Evidence audit script**
- Python script to validate attribution reports
- Check against `evidence_audit.md` rules
- Auto-verify Evidence Ledger completeness

**#12 - SDK trigger visibility**
- Track sub-agent spawns
- Show significant moves count
- Better progress output

**#23 - Perplexity API cost tracking**
- Count calls to: `perplexity_search`, `perplexity_ask`, `perplexity_research`
- Calculate estimated cost based on Perplexity pricing
- Include cost summary in orchestrator run output
- Track per-ticker and cumulative costs

---

## Completed Tasks

| # | Task | Completed Date | Notes |
|---|------|----------------|-------|
| 7 | Normalize news_processed.csv structure | 2026-01-27 | Changed to normalized rows |
| 11 | Add volatility caching/passthrough option | 2026-01-27 | Obsolete - no longer needed with 5% threshold |
| 17 | Replace sigma threshold with simple 5% cutoff | 2026-01-27 | 5% in addition to sigma; made #11 obsolete |
| 20 | Add source URL field to CSV output | 2026-01-27 | External URL now in output |
| 3 | Fix PIT validation hook | 2026-01-27 | Verified working |
| 14 | Clarify E1/E2 ordering | 2026-01-27 | Documented: oldest quarters first |
| 18 | CSV output template | 2026-01-27 | 10-field format (title removed) |
| 21 | Fix Q2 permission prompts | 2026-01-27 | Added Edit to allowed-tools |
| 15 | Standardize exhibit_number vs exhibit_type | 2026-01-27 | Fixed guidance-inventory to use exhibit_number |

---

## Dependency Graph

```
Phase 1 (Foundation)
├── #14 (E1/E2 ordering) ──┐
├── #15 (exhibit fields) ──┼──► #1 (orchestrator design)
├── #17 (5% threshold) ✓   │         │
├── #3 (PIT hook)          │         ├──► #2 (guidance-inventory)
└── #18 (CSV template) ────┤         ├──► #13 (checkpoint/resume)
                           │         ├──► #21 (Q2 permissions)
                           │         └──► #8 (batching docs)
                           │
                           ├──► #4 (output formats) ──► #5 (error codes)
                           ├──► #19 (output verification)
                           └──► #20 (source URL field)

Independent (any time)
├── #7 (normalize CSV)
├── #6 (ticker config)
├── #9 (rate limits)
├── #10 (audit script)
├── #12 (SDK trigger)
├── #16 (retry logic)
├── #22 (Obsidian output)
└── #23 (Perplexity cost)
```

---

## Quick Reference

**Completed**: #17 ✓
**Start with**: #14, #15, #3, #18 (can be parallel)
**Then**: #1 (unlocks Phase 2)
**Parallel work**: Phase 3 & 4 can run alongside Phase 2
**Last**: Phase 5 (polish)

---

## Full Task List

```
#1  - Fix orchestrator to match tradeEarnings.md design [blocked by #14, #15]
#2  - Add guidance-inventory invocation to orchestrator [blocked by #1, #15]
#3  - Fix PIT validation hook to extract correct date
#4  - Standardize output formats across sub-agents [blocked by #18]
#5  - Add structured error codes to sub-agents [blocked by #4, #18]
#6  - Move USE_FIRST_TICKERS to config file
#7  - Normalize news_processed.csv structure ✓ COMPLETED
#8  - Add batching example to orchestrator docs [blocked by #1]
#9  - Add rate limit handling for Perplexity
#10 - Create automated evidence audit script
#11 - Add volatility caching/passthrough option ✓ COMPLETED (obsolete)
#12 - Improve SDK trigger progress visibility
#13 - Add checkpoint/resume to orchestrator [blocked by #1]
#14 - Clarify E1/E2 ordering (ASC vs DESC)
#15 - Standardize exhibit_number vs exhibit_type
#16 - Add retry logic to filtered-data
#17 - Replace sigma threshold with simple 5% cutoff ✓ COMPLETED
#18 - Add strict CSV output template for driver/confidence
#19 - Add output verification for news driver attribution [blocked by #18]
#20 - Add source URL field to CSV output for external research ✓ COMPLETED
#21 - Fix permission prompts for Q2 file writes in orchestrator [blocked by #1]
#22 - Show all orchestrator output in Obsidian
#23 - Calculate and track Perplexity API cost per run
#24 - Add market_session to external research output [blocked by #18]
```

---

*Last updated: 2026-01-27*
