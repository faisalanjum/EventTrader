# Guidance Extraction Run — Handoff Document (2026-03-01)

**Purpose**: Pass to a new session that will run `/guidance-transcript` on AAPL transcripts, monitor in real-time (every 30s), and log issues to `guidance-extraction-issues.md`.

---

## AAPL Transcripts — Sorted (5 unique, 1 duplicate)

Run these in order. `AAPL_2025_3` is a KNOWN DUPLICATE of #5 (Issue #35 — upstream ingestion bug, short-format vs long-format ID). Skip it or run last for duplicate testing.

| # | Transcript ID | FY | FQ | Fiscal Label | Invocation |
|---|---|---|---|---|---|
| 1 | `AAPL_2023-11-03T17.00.00-04.00` | 2023 | Q4 | Q1 FY2024 (Oct-Dec 2023) | `/guidance-transcript AAPL transcript AAPL_2023-11-03T17.00.00-04.00 MODE=write` |
| 2 | `AAPL_2024-10-31T17.00.00-04.00` | 2024 | Q4 | Q1 FY2025 (Oct-Dec 2024) | `/guidance-transcript AAPL transcript AAPL_2024-10-31T17.00.00-04.00 MODE=write` |
| 3 | `AAPL_2025-01-30T17.00.00-05.00` | 2025 | Q1 | Q2 FY2025 (Jan-Mar 2025) | `/guidance-transcript AAPL transcript AAPL_2025-01-30T17.00.00-05.00 MODE=write` |
| 4 | `AAPL_2025-05-01T17.00.00-04.00` | 2025 | Q2 | Q3 FY2025 (Apr-Jun 2025) | `/guidance-transcript AAPL transcript AAPL_2025-05-01T17.00.00-04.00 MODE=write` |
| 5 | `AAPL_2025-07-31T17.00.00-04.00` | 2025 | Q3 | Q4 FY2025 (Jul-Sep 2025) | `/guidance-transcript AAPL transcript AAPL_2025-07-31T17.00.00-04.00 MODE=write` |
| 6 | `AAPL_2025_3` (DUPLICATE of #5) | 2025 | Q3 | Q4 FY2025 (duplicate) | SKIP — known Issue #35 |

**AAPL FYE month = 9 (September)**

---

## Guidance Extraction Pipeline — How It Works

### Architecture: Two-Phase, Two-Agent Pipeline

The `/guidance-transcript` skill (`.claude/skills/guidance-transcript/SKILL.md`) is an orchestrator that spawns TWO sequential sub-agents via the Task tool:

```
/guidance-transcript AAPL transcript {SOURCE_ID} MODE=write
  |
  +-- Phase 1: Task(guidance-extract)     -- Extracts from Prepared Remarks ONLY
  |     Agent: .claude/agents/guidance-extract.md
  |     Model: opus, permissionMode: dontAsk
  |     Tools: neo4j read, Bash, Write, Read (NO neo4j write)
  |
  +-- Phase 2: Task(guidance-qa-enrich)   -- Enriches using Q&A exchanges
        Agent: .claude/agents/guidance-qa-enrich.md
        Model: opus, permissionMode: dontAsk
        Tools: neo4j read, Bash, Write, Read (NO neo4j write)
```

### Phase 1: `guidance-extract` Agent

**Steps:**
1. **Auto-Load**: Reads 3 reference files (SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md)
2. **Load Context**: Company/CIK (1A), FYE from 10-K (1B), concept cache (2A), member cache (2B), existing tags (7A), prior extractions (7D)
3. **Fetch Source**: Query 3B (structured transcript — PreparedRemarks + Q&A). For this phase, only PreparedRemarks are used. Q&A is fallback only when PR is truncated.
4. **LLM Extraction**: Extracts guidance items with all fields: label, segment, numerics, derivation, basis, conditions, quote, XBRL candidates, and LLM period fields (fiscal_year, fiscal_quarter, half, month, sentinel_class, etc.)
5. **Deterministic Validation**: Calls `guidance_ids.py` via Bash for ID computation, unit canonicalization, period routing (gp_ format)
6. **Write**: Assembles JSON payload -> Write to `/tmp/gu_AAPL_{SOURCE_ID}.json` -> `guidance_write.sh --write` (or `--dry-run`)

**Write path**: JSON -> `guidance_write.sh` -> `guidance_write_cli.py` -> `guidance_writer.py` -> Neo4j (Bolt). Two gates: MODE flag + ENABLE_GUIDANCE_WRITES env var.

### Phase 2: `guidance-qa-enrich` Agent

**Steps:**
1. **Auto-Load**: Same 3 reference files
2. **Load Context**: Same as Phase 1, PLUS Query 7E to load Phase 1's written items, PLUS Query 7F for cross-transcript baseline
3. **Load Q&A Content**: Query 3F (Q&A exchanges), fallback 3C
4. **Q&A Analysis**: Every exchange gets a verdict: ENRICHES / NEW ITEM / NO GUIDANCE. Produces a Q&A Analysis Log.
5. **Completeness Check**: Compares against 7F baseline for missed labels
6. **Validate + Write**: Only changed/new items. Enriched items preserve all Phase 1 fields.

### Graph Schema Created

```
(Guidance)          -- canonical metric parent (e.g., guidance:aapl:revenue)
    ^
    |  UPDATES
    |
(GuidanceUpdate)    -- per-source, per-period data point
    |-- FOR_COMPANY     --> (Company)
    |-- FROM_SOURCE     --> (Transcript)
    |-- HAS_PERIOD      --> (GuidancePeriod)   -- calendar-based, company-agnostic
    |-- MAPS_TO_CONCEPT --> (Concept)          -- XBRL concept link
    |-- MAPS_TO_MEMBER  --> (Member)           -- segment member link (when segment != Total)
```

### GuidancePeriod Design (NEW — redesigned)

Calendar-based, company-agnostic nodes. Format: `gp_{start_date}_{end_date}` or sentinel `gp_ST/MT/LT/UNDEF`.

Python routing: LLM period fields -> `build_guidance_period_id()` -> calendar dates + period_scope + u_id.

4 sentinel nodes pre-created via `create_guidance_constraints()` on every write batch.

---

## All Resolved Issues (Issues That Were Fixed)

These are the defects found and fixed across Runs 1-7. The new session should verify each fix holds.

### CRITICAL Fixes

| # | Issue | Fix Summary |
|---|---|---|
| 1 | Agent bypassed CLI write path — raw Cypher via MCP write tool | Removed `write_neo4j_cypher` from agent tools. Write prohibition banner. |
| 2 | Wrong MERGE pattern (ON CREATE SET for all props) | Auto-fixed by #1 — CLI uses correct MERGE+SET |
| 3 | 20 MCP write calls instead of 2 (Write JSON + Bash CLI) | Auto-fixed by #1 |
| 9 | Peak context 105k tokens (81% window) — compaction risk | Auto-fixed by #1 — CLI saves ~14k tokens |
| 17 | Phase 2 feature flag data loss — Q&A enrichment computed but not persisted | Env var check in `guidance_writer.py`. Agents use `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write` |

### Medium Fixes

| # | Issue | Fix Summary |
|---|---|---|
| 4 | Feature flag ENABLE_GUIDANCE_WRITES bypassed | Auto-fixed by #1 |
| 5 | WHA missing MAPS_TO_MEMBER edge | Prompt rewrite. All 5 segment items have member links. |
| 6 | Segment Revenue items missing MAPS_TO_CONCEPT edges | Concept inheritance in `guidance_write_cli.py`. Same label = same concept. |
| 7 | No Q&A synthesis — all quotes from PR only | Two-invocation pipeline: `guidance-extract` (PR) -> `guidance-qa-enrich` (Q&A). Run 4: 5/10 enriched. |
| 12 | Agent modified `config/feature_flags.py` with `sed -i` | Env var override. Process-scoped, no config file editing. |
| 16 | Guidance periods share `:Period` label with XBRL | GuidancePeriod redesign. New `:GuidancePeriod` label with calendar-based `gp_` IDs. |
| 20 | Unit double-scaling — pre-scales values AND sets unit_raw to "billion" | Prompt rule "Copy number and unit exactly as printed". Code guard in `canonicalize_value()`. |
| 21 | Tariff Cost Impact as standalone (§13 regression) | Updated §13 factors rule to eliminate conflict with recall priority. |
| 22 | P2 dropped Revenue enrichment — false "already enriched" claim | Added rule: "Never skip an ENRICHES verdict. MERGE+SET handles idempotency." |
| 24 | 2 of 3 guidance uniqueness constraints missing | Ran all 7 constraint statements. 3 constraints confirmed. |
| 26 | Segment-qualified labels produce separate Guidance parents | Rewrote §4 Metric Decomposition. Added §4/§7 reference to agent prompts. |
| 28 | `PER_SHARE_LABELS` too narrow — adjusted_eps gets m_usd instead of usd | Pattern function `_is_per_share_label()` + fail-closed guards in `_validate_item()`. |
| 38 | `guidance-qa-enrich` hardcodes `--write` even in dry_run | MODE->flag mapping table + both examples. |
| 44 | Sentinel GuidancePeriod nodes missing after wipe (Issue #25 regression) | CLI now calls `create_guidance_constraints()` at start of every write batch. Idempotent. |
| 53 | `label` and `label_slug` null on all GuidanceUpdate nodes | Added denormalized properties to writer SET block + params. |

### Low Fixes

| # | Issue | Fix Summary |
|---|---|---|
| 10 | FX Impact extracted as standalone instead of Revenue condition | Quality filter in SKILL.md §13. |
| 13 | Phase 2 re-discovers feature flag (~60s, 8 extra tool calls) | Auto-fixed by #12. |
| 19 | `/guidance-transcript` skill not invocable | Moved to `guidance-transcript/SKILL.md` directory format. |
| 25 | 3 of 4 sentinel GuidancePeriod nodes missing | Fixed, tracked as active #44. |
| 27 | Services Revenue segment="Total" inconsistency | Fixed by #26 — §7 rules in prompt. |
| 29 | PROFILE_TRANSCRIPT.md wrong derivation example | One-word doc fix. |
| 30 | Batch summary undercounts member/concept links on re-runs | Moved counter outside `was_created` conditional. |
| 31 | `derivation` silently defaults to `implied` | Changed default to `unknown` (not a valid value, flags bugs). |
| 36 | No sub-source linking for Q&A | Added `source_refs` array on GuidanceUpdate. |
| 55 | `segment_raw` and `segment_slug` null | Added denormalized properties alongside #53. |
| 60 | No indexes on `label_slug` / `segment_slug` | Added 2 indexes to `create_guidance_constraints()`. |

### Closed (Won't-Fix / Not-a-Bug / Design)

| # | Issue | Resolution |
|---|---|---|
| 8 | iPad/WHA share evhash | By design — same directional guidance produces same fingerprint. Separate via segment in ID. |
| 11 | 3B query too large for MCP tool | Agent self-heals via Bash+Python. Can't split 3B. |
| 14 | Stale /tmp JSON collision | One-time. Write tool overwrites. |
| 15 | Phase 2 skipped readback verification | CLI already returns structured results. Redundant. |
| 23 | P2 verdict inconsistency between analysis and report | Self-corrected. Final verdict more accurate. |
| 32 | Tariff Cost Impact as standalone (§13 regression v2) | LLM judgment on ambiguous edge case. Downstream handles. |
| 33 | DPS / Share Repurchase as guidance | Capital allocation items clearly labeled. Downstream filters. |
| 34 | Transcript #4 took 8m01s | Root cause: truncated PR (#18). Expected recovery behavior. |
| 45 | Run 7 totals inconsistent | Stale draft description. Actual data correct. |
| 46 | Non-deterministic sentinel classification | Resolves with #35 (duplicate transcripts). |
| 52 | `u_id` null on GuidanceUpdate | Not in spec. GU uses `id`. |
| 54 | `direction` null on GuidanceUpdate | Never designed/specified. |
| 56 | `evhash` null | Correct property is `evhash16`. Audit queried wrong name. |
| 57 | Numeric fields null | Correct names are `low`/`mid`/`high`. Audit queried wrong names. |
| 58 | `basis_raw` null on OINE items | Spec-compliant. Forecast scope != accounting basis. |
| 59 | `canonical_low/mid/high` null on early-return | Fail-safe. Crashes with KeyError before DB write. |

---

## Still Open Issues

### Extraction-level (monitor during runs)

| # | Issue | Severity | What to Watch For |
|---|---|---|---|
| 18 | Truncated PreparedRemarks on AAPL_2025-05-01 | Medium | Transcript #4 will extract few items. Agent should recover from Q&A. Only 1-2 items expected. |
| 35 | Duplicate transcript IDs (AAPL_2025_3 = duplicate of AAPL_2025-07-31) | HIGH | SKIP `AAPL_2025_3`. If run, creates duplicate GuidanceUpdate nodes. |

### K8s/Infrastructure (not relevant to this run — local execution)

| # | Summary |
|---|---|
| 37 | Write path default Neo4j URI `bolt://localhost:30687` |
| 39 | Container SHELL=/bin/bash requirement |
| 40 | K8s non-root requirement |
| 41 | MCP `--strict-mcp-config` |
| 42 | GHCR image pull strategy |
| 43 | No pre-prod canary for full two-phase path |
| 47 | Plaintext password in `guidance_write.sh` |
| 48 | Write-mode Python import chain dependencies |
| 49 | K8s MCP server must be named `neo4j-cypher` |
| 50 | Hardcoded absolute path in `guidance_write_cli.py` |
| 51 | `CLAUDE_PROJECT_DIR` env var |

---

## Real-Time Monitoring Protocol

The next session should follow this protocol while running each transcript:

### Every 30 seconds during each Phase:

1. **Check Task output** — use `TaskOutput` (non-blocking) to see latest agent activity
2. **Watch for these patterns:**
   - Agent loading 3 reference files (SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md) — should happen first
   - Cypher queries to Neo4j (1A, 1B, 2A, 2B, 7A, 7D for P1; add 7E, 7F for P2)
   - Source content fetch (3B for P1; 3F for P2)
   - `guidance_ids.py` calls via Bash (Step 4 validation)
   - JSON write to `/tmp/gu_AAPL_*.json`
   - `guidance_write.sh` invocation (dry-run or write)
3. **Red flags to note immediately:**
   - Any `mcp__neo4j-cypher__write_neo4j_cypher` call = CRITICAL regression of Issue #1
   - Any `sed -i` on config files = Issue #12 regression
   - Agent not loading reference files = will produce poor extractions
   - P2 claiming "already enriched" without evidence = Issue #22 regression
   - Context > 100k tokens = compaction risk (Issue #9)
   - Unit values > 999 with unit_raw "billion" = Issue #20 double-scaling

### After Each Transcript Completes:

1. **Verify in Neo4j:**
```cypher
// Count items for this source
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $SOURCE_ID})
RETURN count(gu) AS items

// Check all 5 edge types
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript {id: $SOURCE_ID})
OPTIONAL MATCH (gu)-[:UPDATES]->(g:Guidance)
OPTIONAL MATCH (gu)-[:FOR_COMPANY]->(c:Company)
OPTIONAL MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(con:Concept)
RETURN gu.id, gu.label, gu.segment, gu.period_scope,
       g.id IS NOT NULL AS has_guidance,
       c.ticker AS company,
       gp.u_id AS period,
       con.name AS concept
```

2. **Check period format**: All `period_u_id` should be `gp_` format (not old `guidance_period_` format)
3. **Check label/label_slug populated** (Issue #53 fix)
4. **Check units**: per-share items should be `usd`, not `m_usd` (Issue #28 fix)

### Expected Results Per Transcript (from Run 7 baseline):

| # | Transcript | Expected P1 Items | Expected P2 Enriched | Expected P2 New | Notes |
|---|---|---|---|---|---|
| 1 | AAPL_2023-11-03 (Q1 FY2024) | ~10 | ~4-5 | 0 | Richest. 5 segment Revenue items. |
| 2 | AAPL_2024-10-31 (Q1 FY2025) | ~6 | ~1-2 | 0 | Total-level only. |
| 3 | AAPL_2025-01-30 (Q2 FY2025) | ~6 | ~1 | 0 | Kevan Parekh as new CFO. |
| 4 | AAPL_2025-05-01 (Q3 FY2025) | ~5 | ~2 | 0 | OUTLIER: truncated PR (#18). May extract fewer. Slow P1 (~8min). |
| 5 | AAPL_2025-07-31 (Q4 FY2025) | ~8 | ~3 | ~2 | CapEx + US Investment from Q&A. |

---

## Issue Logging Instructions

After each run (or when issues are spotted in real-time), append to:
**`/home/faisal/EventMarketDB/.claude/plans/guidance-extraction-issues.md`**

### Section format:

```markdown
## Run 8 — GuidancePeriod Redesign Re-extraction (2026-03-01, MODE=write)

**Session**: {start} – {end} UTC ({duration})
**Mode**: write
**Context**: Clean slate after deleting all 65 Guidance/GuidanceUpdate/GuidancePeriod nodes. First run with GuidancePeriod redesign (gp_ format).

| # | Transcript ID | FY/Q | P1 Items | P1 Time | P2 Enriched | P2 New | P2 Time | Total Time | Issues |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### New Issues Found

| # | Issue | Severity | Transcripts Affected | Details |
|---|---|---|---|---|

### Prior Issue Regression Check

| Prior # | Check | Result |
|---|---|---|
| 1 | No write_neo4j_cypher calls | ... |
| 5 | WHA member linked | ... |
| 7 | Q&A synthesis working | ... |
| 16 | GuidancePeriod (not Period) used | ... |
| 20 | No unit double-scaling | ... |
| 22 | No false "already enriched" | ... |
| 26 | Segment decomposition correct | ... |
| 28 | Per-share units = usd | ... |
| 44 | Sentinel nodes created | ... |
| 53 | label/label_slug populated | ... |
```

---

## Key File Locations

| File | Purpose |
|---|---|
| `.claude/skills/guidance-transcript/SKILL.md` | Orchestrator skill (invoked by `/guidance-transcript`) |
| `.claude/agents/guidance-extract.md` | Phase 1 agent (PR extraction) |
| `.claude/agents/guidance-qa-enrich.md` | Phase 2 agent (Q&A enrichment) |
| `.claude/skills/guidance-inventory/SKILL.md` | Full spec (schema, fields, validation, quality filters) |
| `.claude/skills/guidance-inventory/QUERIES.md` | All Cypher queries |
| `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md` | Transcript extraction profile |
| `.claude/skills/earnings-orchestrator/scripts/guidance_write.sh` | Write path entry point |
| `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` | CLI (ID computation, validation, batch write) |
| `.claude/skills/earnings-orchestrator/scripts/guidance_writer.py` | Neo4j writer (MERGE template, params) |
| `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` | ID + period routing functions |
| `.claude/plans/guidance-extraction-issues.md` | Issue tracker (append new section here) |
| `.claude/plans/guidance-period-redesign.md` | GuidancePeriod redesign spec |
| `.claude/plans/guidanceInventory.md` | Full guidance system spec (v3.1) |

---

## Pre-Run Checklist

Before starting the first transcript:

- [ ] Confirm 0 Guidance/GuidanceUpdate/GuidancePeriod nodes in Neo4j (clean slate)
- [ ] Confirm AAPL Company node exists (`MATCH (c:Company {ticker:'AAPL'}) RETURN c.cik`)
- [ ] Run one transcript in `MODE=dry_run` first to verify pipeline works end-to-end without writing
- [ ] Then switch to `MODE=write` for all 5 transcripts
- [ ] After first write-mode transcript, verify sentinel nodes exist: `MATCH (gp:GuidancePeriod) WHERE gp.id IN ['gp_ST','gp_MT','gp_LT','gp_UNDEF'] RETURN gp.id`
