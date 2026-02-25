# Guidance Extraction Issues — AAPL Transcript (AAPL_2023-11-03T17.00.00-04.00)

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
| 12 | Agent modified `config/feature_flags.py` directly with `sed -i` to enable writes | Medium | **Escalated→#17** | Agent toggled `ENABLE_GUIDANCE_WRITES` via sed instead of using env var or CLI flag. Claims it will restore after writing — verify it actually does. Risk: if agent crashes mid-run, flag stays flipped. Should use env var override or CLI `--write` flag instead of modifying source. |
| 13 | Phase 2 re-discovers feature flag toggle (~60s, 8 extra tool calls) | Low | **Escalated→#17** | Phase 2 independently discovers `ENABLE_GUIDANCE_WRITES=False`, toggles via `sed -i`, then restores. Same work Phase 1 already did. Phases don't share state. Fix: pass `--write` flag to CLI or set env var in agent prompt so neither phase touches source. |
| 14 | Stale /tmp JSON file collision in Phase 1 | Low | **Open** | Phase 1 wrote to `/tmp/gu_AAPL_*.json` but a stale file from a prior run already existed. Agent detected it, deleted, and rewrote (+15s overhead). Fix: use unique filenames with timestamp or PID, or always overwrite without checking. |
| 15 | Phase 2 skipped readback verification after write | Low | **Open** | Phase 1 ran 7D readback query to verify written items. Phase 2 did not — went straight to summary after `guidance_write.sh` succeeded. Minor: CLI exit code 0 is sufficient, but readback confirms MERGE+SET actually updated fields. Add 7D readback to `guidance-qa-enrich.md` Step 6 as optional verification. |
| 16 | Guidance periods share `:Period` label with XBRL periods despite different schemas | Low | **Open** | Both use `:Period` but have completely disjoint schemas: XBRL periods have `start_date`/`end_date` (calendar dates), guidance periods have `fiscal_year`/`fiscal_quarter`/`cik` (with null dates). No cross-linking — 9,919 XBRL vs 1 guidance period, zero overlap. `MATCH (p:Period)` returns both mixed. Fix: add `:GuidancePeriod` as additional label (`:Period:GuidancePeriod`) so queries are unambiguous. Requires update to `guidance_writer.py` MERGE pattern and 7E query. Also add `updated` timestamp to write pipeline (currently null — can't distinguish Phase 1 vs Phase 2 writes via graph alone). |
| 17 | Phase 2 gave up on feature flag — Q&A enrichment computed but not persisted (DATA LOSS) | **CRITICAL** | **Open** | Escalation of #12/#13. On FY25Q1 run, Phase 2 (guidance-qa-enrich) analyzed all Q&A exchanges correctly, produced the log, assembled the payload, but abandoned the write after one `writes_disabled` rejection instead of toggling the flag like Phase 1 did. Required manual CLI invocation with Python override to persist. The sed-based workaround is non-deterministic — agent may or may not attempt it depending on context pressure, model temperature, or prompt interpretation. **Fix**: Remove the feature flag from the agent's critical path entirely. Options: (a) `guidance_write.sh --force-write` CLI flag that bypasses the Python flag check, (b) env var `ENABLE_GUIDANCE_WRITES=true` set by the orchestrator skill before spawning agents, (c) add explicit instruction in both agent prompts: "If writes_disabled, run `sed -i 's/ENABLE_GUIDANCE_WRITES = False/ENABLE_GUIDANCE_WRITES = True/' config/feature_flags.py` and retry." Option (b) is cleanest — no source modification, no agent improvisation. |
| 17 | Phase 2 agent gave up on feature flag — enrichment computed but NOT written | **High** | **Open** | FY25Q2 run: `guidance-qa-enrich` analyzed 23 Q&A exchanges, enriched 1 item (Gross Margin from 3 exchanges), assembled JSON payload, but **failed to persist**. Agent attempted `guidance_write.sh --write` once, got `writes_disabled`, investigated the flag, but never applied a workaround (no sed-i, no Python module override). Reported results as if successful. Required manual CLI invocation to write. This is a **data loss** escalation of #12/#13 — previous runs wasted time rediscovering the flag but eventually wrote; this run didn't write at all. Inconsistent across runs: FY24Q1 Phase 2 wrote (sed-i), FY25Q1 Phase 2 wrote (Python override), FY25Q2 Phase 2 did not. Root cause: no deterministic write path — each agent improvises a different workaround. Fix: add env var check (`os.environ.get('ENABLE_GUIDANCE_WRITES')`) to `guidance_writer.py` as OR condition with config flag, then document `ENABLE_GUIDANCE_WRITES=true` in both agent prompts. |

---

## Run 2 Stats (Post-CLI Write Path Implementation)

| Metric | Run 2 | Run 1 | Delta |
|---|---|---|---|
| Duration | 5 min 12 sec | 8 min 41 sec | 40% faster |
| Total tool calls | 41 | 72 | 43% fewer |
| MCP write calls | 20 | ~40 | Should be 0 with CLI path |
| Total tokens | 107,540 | 127,000 | 15% less |
| Peak context | 105,382 (81%) | 83,516 (then compacted) | **DANGER ZONE** |
| Items extracted | 11 | 10 | +1 (FX Impact added) |
| Items written | 11 | 9 written + 1 merged | |
| Errors | 0 | multiple | |

**Context budget projection if CLI write path used:**
- Remove 20 MCP write calls (~800 tokens each = ~16k tokens): 105k → ~89k (69%)
- Replace with 2 CLI calls (~2k tokens): ~75k (58%)
- **Safe headroom for larger transcripts** (MSFT has 30+ Q&A exchanges)

## Run 4 Stats (Two-Invocation Pipeline)

| Metric | Phase 1 (PR) | Phase 2 (Q&A) | Combined |
|---|---|---|---|
| Duration | 4m42s | 5m01s | 9m43s |
| Token usage | 98,393 | 104,210 | 202,603 |
| Tool calls | 31 | 40 | 71 |
| Items extracted/enriched | 10 | 5 enriched | 10 total (5 enriched) |
| Items written | 10 (all created) | 5 (all updated) | 15 write ops |
| Errors | 0 | 0 | 0 |
| Q&A exchanges analyzed | — | 23 (5 enriched, 18 no_guidance) | — |

**Comparison vs prior runs:**
- Run 2 (single-pass, raw Cypher): 5m12s, 107k tokens, 41 calls, 0/11 Q&A enriched
- Run 3 (single-agent 3a/3b/3c): ~6m, ~110k tokens, 3/10 Q&A enriched
- Run 4 (two-invocation): 9m43s, 202k tokens, 71 calls, **5/10 Q&A enriched**
- Trade-off: ~2x tokens/time for 5x better Q&A enrichment. Acceptable — Q&A quality was the goal.

**Post-run verification (JSON payload analysis):**
- Phase 1 payload (`/tmp/gu_AAPL_..._04.00.json`): 10 items, **0/10 have Q&A** — all sections "CFO Prepared Remarks". PR-only confirmed.
- Phase 2 payload (`/tmp/gu_AAPL_..._04.00_qa.json`): 5 items, **5/5 have Q&A** — sections all "CFO PR + Q&A #N". Enrichment confirmed.
- MERGE+SET overwrote Phase 1 data for enriched items. `created` timestamps preserved (ON CREATE SET). No `updated` field in write pipeline — can't distinguish writes via graph alone; JSON payloads serve as audit trail.
- WH&A now has MAPS_TO_MEMBER edge (Issue #5 → Fixed). All 5 segment items have correct member mappings.

**Overhead breakdown:**
- Feature flag re-discovery in Phase 2: ~60s, ~8 tool calls (Issue #13)
- Stale /tmp file in Phase 1: ~15s (Issue #14)
- Large 3B transcript parsing: 3-4 extra Bash calls (Issue #11)

---

## What went RIGHT (Run 2)

- Auto-loaded all 3 mandatory files (SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md)
- Step 1 context loading: company, FYE, concept cache, member cache, existing tags, prior extractions — all correct
- Step 2: Read ALL transcript sections (PR + Q&A) before extracting
- Step 3: Good extraction quality — 11 items, captured all key metrics
- Step 4: Used Bash to call guidance_ids.py for ID computation (8 Bash calls)
- No context compaction occurred (stayed at 81%)
- Faster than previous run (5 min vs 8.5 min)

## What went RIGHT (Run 4 — Two-Invocation)

- Both agents auto-loaded all 3 reference files in parallel
- Phase 1: PR-only compliance — explicitly stated "Q&A enrichment handled by separate agent"
- Phase 1: FX Impact correctly excluded (10 items vs 11 in Run 2) — Issue #10 fix working
- Phase 1: All 10 XBRL concepts resolved, 5 member matches — Issue #6 fix working
- Phase 1: Dry-run validation before write, readback verification after write
- Phase 1: Feature flag restored after write
- Phase 2: 7E readback loaded all 10 items with full fields (SET overwrite protection)
- Phase 2: Full Q&A Analysis Log — 23 exchanges, all with verdicts + topic summaries
- Phase 2: No shallow NO GUIDANCE verdicts — every skip well-justified
- Phase 2: Multi-exchange aggregation (Gross Margin enriched from 3 separate exchanges)
- Phase 2: Only wrote 5 changed items (not all 10) — correct behavior
- Phase 2: No fields nulled on enriched items — all Phase 1 values preserved
- Graph verified: [PR] + [Q&A] quote format, section fields cite exact Q&A exchange numbers

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

## Extraction Results — Run 2 (11 items, single-pass, no Q&A)

| # | Metric | Segment | Derivation | Low | Mid | High | Unit | Qualitative | XBRL Concept | Member | Conditions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | comparative | -- | -- | -- | m_usd | similar to last year | RevenueFromContract... | -- | macro outlook; -1pp FX; 13 vs 14 weeks |
| 2 | Revenue | iPhone | implied | -- | -- | -- | m_usd | grow YoY on absolute basis; also grow after normalizing | -- | IPhoneMember | supply-demand balance by end of quarter |
| 3 | Revenue | Mac | comparative | -- | -- | -- | m_usd | significantly accelerate from Sept quarter | -- | MacMember | -- |
| 4 | Revenue | iPad | comparative | -- | -- | -- | m_usd | decelerate significantly from Sept quarter | -- | IPadMember | different timing; iPad Pro + iPad 10th gen launched last year |
| 5 | Revenue | WHA | comparative | -- | -- | -- | m_usd | decelerate significantly from Sept quarter | -- | **MISSING** | different timing; AirPods Pro 2, Watch SE, Watch Ultra last year |
| 6 | Revenue | Services | implied | -- | -- | -- | m_usd | similar strong double digit rate as Sept quarter | -- | ServiceMember | -- |
| 7 | Gross Margin | Total | explicit | 45.0 | 45.5 | 46.0 | percent | -- | GrossProfit | -- | -- |
| 8 | OpEx | Total | explicit | 14,400 | 14,500 | 14,600 | m_usd | -- | OperatingExpenses | -- | -- |
| 9 | OINE | Total | point | -200 | -200 | -200 | m_usd | -- | NonoperatingIncomeExpense | -- | excl. mark-to-market of minority investments |
| 10 | Tax Rate | Total | point | 16.0 | 16.0 | 16.0 | percent | -- | EffectiveIncomeTaxRate... | -- | -- |
| 11 | FX Impact | Total | point | -1.0 | -1.0 | -1.0 | percent_points | -- | -- | -- | -- |

## Extraction Results — Run 4 (10 items, two-invocation, 5 Q&A-enriched)

| # | Metric | Segment | Enriched? | Section | Conditions (final) |
|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A #4 | FX -1pp; 13 vs 14 weeks; Pro/Pro Max constraints |
| 2 | Revenue | iPhone | **Yes** | CFO PR + Q&A #4, #19 | Supply constraints; 7pp extra week; normalized growth |
| 3 | Revenue | Mac | **Yes** | CFO PR + Q&A #1 | Q4 inflated compare from disruption fill; M3 lineup |
| 4 | Revenue | iPad | -- | CFO PR | different timing; iPad Pro + iPad 10th gen launched last year |
| 5 | Revenue | WH&A | -- | CFO PR | different timing; AirPods Pro 2, Watch SE, Watch Ultra last year |
| 6 | Revenue | Services | **Yes** | CFO PR + Q&A #9 | -- |
| 7 | Gross Margin | Total | **Yes** | CFO PR + Q&A #3, #7, #16 | FX drag; commodity favorable; lifecycle costs |
| 8 | OpEx | Total | -- | CFO PR | -- |
| 9 | OINE | Total | -- | CFO PR | excl. mark-to-market of minority investments |
| 10 | Tax Rate | Total | -- | CFO PR | -- |

FX Impact correctly excluded (folded into Revenue conditions per Issue #10 fix).

---

## Edge Summary (Run 4)

| Edge Type | Count | Details |
|---|---|---|
| UPDATES → Guidance | 10/10 | 5 unique Guidance parents (Revenue, Gross Margin, OpEx, OINE, Tax Rate) |
| FROM_SOURCE → Transcript | 10/10 | All linked to AAPL_2023-11-03T17.00.00-04.00 |
| FOR_COMPANY → Company | 10/10 | All linked to AAPL |
| HAS_PERIOD → Period | 10/10 | All linked to guidance_period_320193_duration_FY2024_Q1 (FY2024 Q1) |
| MAPS_TO_CONCEPT → Concept | 10/10 | All items mapped (concept inheritance fix — Issue #6) |
| MAPS_TO_MEMBER → Member | 5/10 | iPhone, Mac, iPad, WH&A, Services. Total-segment items have no member. |
