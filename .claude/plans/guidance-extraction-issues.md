# Guidance Extraction Issues — AAPL Transcripts (All 5 Runs)

## Open Items

| # | Issue | Priority | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Agent bypassed CLI write path — constructed raw Cypher via MCP write tool | CRITICAL | **Fixed** | Removed `write_neo4j_cypher` from tools. Needs rerun to verify. |
| 2 | Wrong MERGE pattern (ON CREATE SET for all props instead of SET) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 3 | 20 MCP write calls instead of 2 (Write JSON + Bash CLI) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 4 | Feature flag ENABLE_GUIDANCE_WRITES completely bypassed | Medium | **Fixed** | Auto-fixed by #1 |
| 5 | WHA missing MAPS_TO_MEMBER edge (should link to WHAMember) | Medium | **Fixed** | Prompt rewrite worked. Run 4 confirmed: WHA correctly linked to `WearablesHomeandAccessoriesMember`. All 5 segment items have MAPS_TO_MEMBER. |
| 6 | Segment Revenue items (5/6) missing MAPS_TO_CONCEPT edges | Medium | **Fixed** | Concept inheritance in `guidance_write_cli.py` (4 tests). Same label = same concept. |
| 7 | No Q&A synthesis — all 11 quotes from PR only, §15C ignored | Medium | **Fixed** | Single-agent 3a/3b/3c failed (Run 3: 3/10). Escalated to two-invocation: `guidance-extract` (PR) → `guidance-qa-enrich` (Q&A). Run 4: 5/10 enriched. See `two-invocation-qa-fix.md`. |
| 8 | iPad/WHA share evhash (f611c8fee63e3f44) — identical qualitative text | Low | **Closed** | By design — same directional guidance, null numerics, similar conditions → same value fingerprint. Separate nodes via segment in ID. |
| 9 | Peak context 105k tokens (81% window) — compaction risk on larger transcripts | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 10 | FX Impact extracted as standalone item instead of Revenue condition | Low | **Fixed** | Added quality filter to SKILL.md §13: factors affecting a metric go in `conditions`, not as standalone items. |
| 11 | 3B query result too large for direct tool result — agent falls back to Bash+Python parsing | Low | **Open** | Large transcripts overflow MCP tool result. Agent persists output to file and parses via Bash (3-4 extra calls). Minor inefficiency, unavoidable with large transcripts. Potential fix: split 3B into separate PR and Q&A queries, or paginate. |
| 12 | Agent modified `config/feature_flags.py` directly with `sed -i` to enable writes | Medium | **Fixed** | Env var override added to `guidance_writer.py`. Agents now use `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write`. Process-scoped, no config file editing. |
| 13 | Phase 2 re-discovers feature flag toggle (~60s, 8 extra tool calls) | Low | **Fixed** | Auto-fixed by #12 — env var in Bash command, no discovery needed. |
| 14 | Stale /tmp JSON file collision in Phase 1 | Low | **Open** | Phase 1 wrote to `/tmp/gu_AAPL_*.json` but a stale file from a prior run already existed. Agent detected it, deleted, and rewrote (+15s overhead). Fix: use unique filenames with timestamp or PID, or always overwrite without checking. |
| 15 | Phase 2 skipped readback verification after write | Low | **Won't-fix** | CLI already returns structured JSON with `was_created`, edge linking results, and errors — agent parses this in Step 6. A post-write readback query is redundant (verifying the verifier). Phase 1's readback was agent improvisation, not a prompted step. No observed failure mode where CLI exit 0 was wrong across all 5 runs. |
| 16 | Guidance periods share `:Period` label with XBRL periods despite different schemas | Low | **Open** | Both use `:Period` but have completely disjoint schemas: XBRL periods have `start_date`/`end_date` (calendar dates), guidance periods have `fiscal_year`/`fiscal_quarter`/`cik` (with null dates). No cross-linking — 9,919 XBRL vs 1 guidance period, zero overlap. `MATCH (p:Period)` returns both mixed. Fix: add `:GuidancePeriod` as additional label (`:Period:GuidancePeriod`) so queries are unambiguous. Requires update to `guidance_writer.py` MERGE pattern and 7E query. Also add `updated` timestamp to write pipeline (currently null — can't distinguish Phase 1 vs Phase 2 writes via graph alone). |
| 17 | Phase 2 gave up on feature flag — Q&A enrichment computed but not persisted (DATA LOSS) | **CRITICAL** | **Fixed** | Escalation of #12/#13. Agents improvised different workarounds (sed-i, Python override, or gave up). Fixed: env var check in `guidance_writer.py` (lines 26-35), both agent prompts updated to `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write`. 62 tests pass. |
| 18 | Truncated PreparedRemarks node — CFO guidance section cut off mid-sentence | Medium | **Open** | Observed on AAPL FY25Q3 (FQ3 FY2025) transcript. CFO prepared remarks end mid-sentence right before specific guidance numbers. Q&A Exchange #10 references "June quarter guide of low to mid single-digit revenue growth" — confirming guidance was given but missing from PR node. Agent recovered partial numbers from Q&A exchanges. This is an upstream data quality issue in the Transcript node, not an extraction bug. Affects Phase 1 (PR-only) extraction — items may have qualitative-only when numerics existed in the original call. Phase 2 (Q&A enrichment) partially compensates by finding guidance references in analyst questions. Scope: unknown how many transcripts are affected. Fix: audit PreparedRemarks nodes for truncation (check if last sentence ends mid-word or without punctuation). |

---

## All AAPL Transcript Runs — Two-Invocation Pipeline

### Summary

| # | Transcript | Period | P1 Items | P2 Enriched | P2 New | Total Items | P1 Time | P2 Time | Total Time |
|---|---|---|---|---|---|---|---|---|---|
| 1 | AAPL_2023-11-03 | Q1 FY2024 | 10 | 5 (50%) | 0 | 10 | 4m42s | 5m01s | 9m43s |
| 2 | AAPL_2024-10-31 | Q1 FY2025 | 6 | 2 (33%) | 0 | 6 | 3m44s | 3m26s | 7m10s |
| 3 | AAPL_2025-01-30 | Q2 FY2025 | 6 | 1 (17%) | 0 | 6 | 3m31s | 2m32s | 6m03s |
| 4 | AAPL_2025-05-01 | Q3 FY2025 | 1 | 0 (0%) | 0 | 1 | 4m19s | 1m50s | 6m09s |
| 5 | AAPL_2025-07-31 | Q4 FY2025 | 6 | 3 (50%) | 1 | 7 | 3m06s | 3m31s | 6m37s |
| **Total** | | | **29** | **11 (38%)** | **1** | **30** | **19m22s** | **16m20s** | **~35m42s** |

### Token Usage

| # | P1 Tokens | P2 Tokens | Total Tokens | P1 Tool Calls | P2 Tool Calls |
|---|---|---|---|---|---|
| 1 | 98k | 104k | 202k | 31 | 40 |
| 2 | 91k | 91k | 182k | — | — |
| 3 | 89k | 81k | 170k | — | — |
| 4 | — | — | — | — | — |
| 5 | 82k | 91k | 173k | 22 | 23 |

### Graph Verification (Neo4j)

| # | Items in Graph | Q&A Enriched | PR-Only | Q&A-Only New | UPDATES | FROM_SOURCE | FOR_COMPANY | HAS_PERIOD | MAPS_TO_CONCEPT | MAPS_TO_MEMBER |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 5 | 5 | 0 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 5/10 |
| 2 | 6 | 2 | 4 | 0 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 |
| 3 | 6 | 1 | 5 | 0 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 0/6 |
| 4 | 1 | 0 | 1 | 0 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| 5 | 7 | 3 | 3 | 1 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0/7 |
| **Total** | **30** | **11** | **18** | **1** | **30/30** | **30/30** | **30/30** | **30/30** | **30/30** | **6/30** |

All 5 core edges (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT) at 100%. MAPS_TO_MEMBER only applies to segment-level items (Run 1 had 5 segment Revenue items; Run 2 had 1 Services; Runs 3-5 had no segment breakdowns).

### Per-Run Notes

**Run 1 (Q1 FY2024)** — Richest transcript. 5 segment Revenue items (iPhone, Mac, iPad, WH&A, Services) + 5 Total items. Phase 2 enriched Revenue, iPhone Revenue, Mac Revenue, Services Revenue, Gross Margin from 23 Q&A exchanges. Feature flag resolved via sed-i (pre-fix). Stale /tmp file collision (Issue #14).

**Run 2 (Q1 FY2025)** — Apple dropped per-segment guidance. 6 Total-level items only. Phase 2 enriched Revenue and Gross Margin from Q&A. Existing guidance labels reused from Run 1 (no new Guidance parent nodes created). Feature flag resolved via Python module override.

**Run 3 (Q2 FY2025)** — Kevan Parekh as new CFO. Phase 2 found 1 Gross Margin enrichment from 3 Q&A exchanges. **Phase 2 write BLOCKED** — agent gave up on feature flag (Issue #17 — data loss). Manually written via CLI. Feature flag fix applied after this run.

**Run 4 (Q3 FY2025)** — Outlier: only 1 item (Revenue). **Truncated PreparedRemarks** — CFO section cut at 6,782 chars before specific guidance numbers (Issue #18). Agent recovered Revenue guidance from Q&A exchange #10 and cross-referenced 8-K press release. Tariff $900M correctly classified as condition (Issue #10 quality filter). Phase 2: 0 enrichments (genuinely sparse tariff-dominated call). Feature flag env var fix worked — much faster resolution.

**Run 5 (Q4 FY2025)** — Cleanest run. 6 PR items + 1 new CapEx from Q&A ("grow substantially, not exponentially", AI-driven, medium-term). Phase 2 enriched Revenue (tariff pull-ahead ~1pt, iPad comp), Gross Margin (tariff cost dynamics QoQ), Services Revenue (Google court ruling as key assumption). 20 Q&A exchanges analyzed. Feature flag resolved instantly via env var. Phase 2 did readback verification (unlike earlier runs).

### Cross-Run Observations

- **Q&A enrichment rate**: 38% overall (11/29 PR items enriched) + 1 new Q&A-only item
- **Run 4 was the outlier** — upstream data quality (truncated PR), not extraction quality
- **Feature flag evolution**: sed-i (Run 1) → Python override (Run 2) → gave up / data loss (Run 3) → env var fix (Runs 4-5, instant resolution)
- **Two-invocation pipeline validated**: Phase 2 always processes Q&A (structural guarantee). Never skipped.
- **Apple guidance density declining**: FY2024 had per-segment breakdowns; FY2025 quarters are Total-level only
- **CapEx first appeared as Q&A-only item in Run 5** — demonstrates Phase 2's value beyond enrichment

### Historical Development Stats

Prior to the two-invocation pipeline, the same first transcript (AAPL_2023-11-03) was run multiple times to debug the extraction system:

| Attempt | Approach | Items | Q&A Enriched | Time | Tokens | Key Issue |
|---|---|---|---|---|---|---|
| Dev Run 1 | Single-pass, raw Cypher | 10 | 0 (0%) | 8m41s | 127k | Bypassed CLI (#1) |
| Dev Run 2 | Single-pass, CLI write | 11 | 0 (0%) | 5m12s | 107k | FX as standalone (#10) |
| Dev Run 3 | Single-agent 3a/3b/3c | 10 | 3 (30%) | ~6m | ~110k | Collapsed phases (#7) |
| Prod Run 1 | Two-invocation | 10 | 5 (50%) | 9m43s | 202k | Feature flag (#12/#13) |

---

## What went RIGHT (All 5 Production Runs)

**Consistent across all runs:**
- Both agents auto-loaded all 3 reference files in parallel
- Phase 1: PR-only compliance — never leaked Q&A content
- Phase 1: All XBRL concepts resolved, member matches where applicable
- Phase 2: Full Q&A Analysis Log with per-exchange verdicts (ENRICHES/NEW/NO GUIDANCE)
- Phase 2: Only wrote changed/new items — never re-wrote untouched PR items
- Phase 2: No fields nulled on enriched items — all Phase 1 values preserved via MERGE+SET
- Phase 2: Quote format consistently `[PR] ... [Q&A] ...` with section citing exact Q&A exchange numbers
- All 5 core edges at 100% (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT)
- FX Impact correctly excluded in all runs (Issue #10 fix held)
- Tariff costs correctly classified as conditions, not standalone items

**Standout moments:**
- Run 1: Multi-exchange aggregation (Gross Margin enriched from 3 separate Q&A exchanges)
- Run 4: Agent resourcefully recovered guidance from Q&A + 8-K press release when PR was truncated
- Run 5: Discovered CapEx as new Q&A-only item (medium-term, AI-driven) — first non-PR item across all runs
- Run 5: Cleanest run — env var fix instant, readback verification done, zero wasted turns

---

## Issue Details

### ISSUE 1 (CRITICAL): Agent bypassed the CLI write path

The agent constructed raw Cypher MERGE queries and wrote via `mcp__neo4j-cypher__write_neo4j_cypher` — directly violating Step 5's instruction: "Do NOT construct Cypher manually." It should have used Write tool (JSON) + Bash (`guidance_write.sh`).

**Impact:** The CLI's ID computation, validation, feature flag enforcement, and batch atomicity were all bypassed. Issues #2, #3, #4, and #9 are all direct consequences — fixing #1 auto-fixes all of them.

**Root cause:** The agent has the old Cypher template pattern in its training context. Even though guidance-extract.md now says "use CLI", the agent still has `mcp__neo4j-cypher__write_neo4j_cypher` in its tools and defaulted to raw Cypher construction. The Step 5 instruction ("Do NOT construct Cypher manually") was not strong enough to override the agent's learned behavior.

**Why keep `mcp__neo4j-cypher__write_neo4j_cypher` in tools:**
1. DELETE queries — CLI only handles MERGE writes, not cleanup/deletes
2. SDK self-healing — ad-hoc recovery for partial failures
3. Constraint creation — DDL-like Cypher (`CREATE CONSTRAINT ... IF NOT EXISTS`)
4. The fix is stronger prompt language, not removing the tool

**Fix applied (Option A — remove the tool entirely):**
- Removed `mcp__neo4j-cypher__write_neo4j_cypher` from `guidance-extract.md` tools list
- Removed `mcp__neo4j-cypher__write_neo4j_cypher` from `SKILL.md` allowed-tools
- Added top-level WRITE PROHIBITION banner in agent prompt (survives context compaction)
- Strengthened Step 5: "You do NOT have `mcp__neo4j-cypher__write_neo4j_cypher`" + batch instruction
- Verified: SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md have zero Cypher write templates — agent invented the MERGE from training knowledge
- **Pending:** Delete Run 2 data, rerun with fixed prompt to verify

### ISSUE 2 (CRITICAL): Wrong MERGE pattern on GuidanceUpdate

Agent used `ON CREATE SET` for ALL properties. Correct pattern: `ON CREATE SET gu.created = $created_ts` + `SET` for everything else. Re-runs won't update properties. **Auto-fixed by #1** — CLI uses correct MERGE pattern from `guidance_writer.py`.

### ISSUE 3 (CRITICAL): 20 MCP write calls instead of 2

CLI batch: 1 Write (JSON) + 1 Bash = 2 tool calls, ~2k tokens.
Actual: 20 MCP writes, ~16k tokens wasted. **Auto-fixed by #1.**

### ISSUE 4 (Medium): Feature flag bypassed

Agent never went through `guidance_writer.py`, so `ENABLE_GUIDANCE_WRITES` was never checked. Global kill switch dead. **Auto-fixed by #1.**

### ISSUE 5 (Medium): Missing WHA MAPS_TO_MEMBER edge

WHA item has no `MAPS_TO_MEMBER` edge. Previous run (Run 1) correctly linked to `WHAMember`. Agent likely didn't resolve the member match this time. Need to check if WHAMember exists in member cache results.

### ISSUE 6 (Medium): Segment Revenue items missing MAPS_TO_CONCEPT

5 of 6 Revenue segment items have `xbrl_concept: null` and no MAPS_TO_CONCEPT edge. Only Revenue(Total) got `RevenueFromContractWithCustomerExcludingAssessedTax`. Per §11, segment items use the segment Member's concept if available. These items DID get member edges (iPhone, Mac, iPad, Services) but not concept edges.

### ISSUE 7 (Medium → Fixed): No Q&A synthesis

All 11 items have `section: "CFO Prepared Remarks"` and quotes prefixed with `[PR]`. Agent read all Q&A exchanges in Step 2 but didn't synthesize any Q&A enrichments. Root cause: cognitive satisficing — PR has clean, explicit guidance; Q&A is conversational and noisy. The aspirational "synthesize richest combined version" rule in PROFILE_TRANSCRIPT.md was not structurally enforced.

**Fix attempt 1** (single-agent 3a/3b/3c — `qa-synthesis-fix.md`):
- Split Step 3 into two-phase extraction: 3a (PR only), 3b (Q&A enrichment), 3c (merged items)
- Run 3 result: 3/10 enriched. Agent collapsed 3a/3b into one thinking pass — no tool call boundary to enforce separation. Insufficient.

**Fix attempt 2** (two-invocation — `two-invocation-qa-fix.md`):
- Separate agents: `guidance-extract` (PR-only) → `guidance-qa-enrich` (Q&A enrichment)
- Physical invocation boundary makes it impossible to skip Q&A — Phase 2's entire purpose is Q&A
- Created `guidance-qa-enrich.md` agent, Query 7E for readback, `guidance-extractor.md` orchestrator skill
- Run 4 result: **5/10 items enriched** from Q&A (up from 0/11 Run 2, 3/10 Run 3)
- Full Q&A Analysis Log produced: 23 exchanges analyzed (5 enriched, 0 new, 18 no_guidance)
- **Verified working.** FX Impact correctly excluded (10 items, not 11).

### ISSUE 8 (Low → Closed): iPad/WHA share evhash

Both share `f611c8fee63e3f44`. Qualitative text identical ("decelerate significantly from Sept quarter"), both have null numerics. Quotes differ but evhash doesn't include quote field. Conditions also very similar. **By design** — evhash fingerprints the value signal, and these two items genuinely carry the same directional guidance. They remain separate nodes because the slot-based ID includes segment (`revenue:ipad` vs `revenue:wha`).

### ISSUE 9 (CRITICAL): Peak context 81% — compaction risk

105k/130k tokens used. For larger transcripts (MSFT 30+ Q&A, AMZN multi-segment), this would trigger compaction mid-extraction — exactly RC-1 from Run 1. **Auto-fixed by #1** — CLI path saves ~14k tokens, bringing peak to ~58%.

### ISSUE 10 (Low → Fixed): FX Impact extracted as standalone item

Agent created a standalone `FX Impact` guidance item (-1.0 percent_points) when the CFO's statement ("we expect a negative year-over-year revenue impact of about one percentage point") was a condition on Revenue, not an independent metric. The same information was already in Revenue(Total)'s conditions field (`-1pp FX`), creating redundancy. Previous run correctly folded FX into conditions only.

**Fix applied:** Added quality filter to SKILL.md §13: "If a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count, commodity cost tailwind), capture it in that metric's `conditions` field — not as a standalone item."

---

## Extraction Results — All 5 Runs (Two-Invocation Pipeline)

### Run 1: AAPL_2023-11-03 — Q1 FY2024 (10 items, 5 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A #4 | -- | -- | m_usd |
| 2 | Revenue | iPhone | **Yes** | CFO PR + Q&A #4, #19 | -- | -- | m_usd |
| 3 | Revenue | Mac | **Yes** | CFO PR + Q&A #1 | -- | -- | m_usd |
| 4 | Revenue | iPad | -- | CFO PR | -- | -- | m_usd |
| 5 | Revenue | WH&A | -- | CFO PR | -- | -- | m_usd |
| 6 | Revenue | Services | **Yes** | CFO PR + Q&A #9 | -- | -- | m_usd |
| 7 | Gross Margin | Total | **Yes** | CFO PR + Q&A #3, #7, #16 | 45.0 | 46.0 | percent |
| 8 | OpEx | Total | -- | CFO PR | 14,400 | 14,600 | m_usd |
| 9 | OINE | Total | -- | CFO PR | -200 | -200 | m_usd |
| 10 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

### Run 2: AAPL_2024-10-31 — Q1 FY2025 (6 items, 2 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.5 | 47.5 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,300 | 15,500 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -50 | -50 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

No segment breakdowns — Apple dropped per-segment guidance starting FY2025.

### Run 3: AAPL_2025-01-30 — Q2 FY2025 (6 items, 1 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.5 | 47.5 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,400 | 15,600 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -50 | -50 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

Phase 2 write was BLOCKED (Issue #17). Gross Margin enrichment manually written via CLI.

### Run 4: AAPL_2025-05-01 — Q3 FY2025 (1 item, 0 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |

Outlier: PreparedRemarks truncated (Issue #18). Only Revenue recovered from Q&A cross-reference. Tariff $900M in conditions.

### Run 5: AAPL_2025-07-31 — Q4 FY2025 (7 items, 3 enriched + 1 new)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.0 | 47.0 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,600 | 15,800 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -25 | -25 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 17.0 | 17.0 | percent |
| 7 | **CapEx** | Total | **NEW** | Q&A #17 (Aaron Rekers) | -- | -- | m_usd |

First Q&A-only item across all runs. CapEx: "grow substantially, not exponentially" (medium-term, AI-driven).
