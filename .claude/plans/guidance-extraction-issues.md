# Guidance Extraction Issues — AAPL Transcript (AAPL_2023-11-03T17.00.00-04.00)

## Open Items

| # | Issue | Priority | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Agent bypassed CLI write path — constructed raw Cypher via MCP write tool | CRITICAL | **Fixed** | Removed `write_neo4j_cypher` from tools. Needs rerun to verify. |
| 2 | Wrong MERGE pattern (ON CREATE SET for all props instead of SET) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 3 | 20 MCP write calls instead of 2 (Write JSON + Bash CLI) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 4 | Feature flag ENABLE_GUIDANCE_WRITES completely bypassed | Medium | **Fixed** | Auto-fixed by #1 |
| 5 | WHA missing MAPS_TO_MEMBER edge (should link to WHAMember) | Medium | **Improved** | Prompt rewritten with explicit matching instruction. LLM-dependent — accept occasional misses. |
| 6 | Segment Revenue items (5/6) missing MAPS_TO_CONCEPT edges | Medium | **Fixed** | Concept inheritance in `guidance_write_cli.py` (4 tests). Same label = same concept. |
| 7 | No Q&A synthesis — all 11 quotes from PR only, §15C ignored | Medium | **Fixed** | Two-phase extraction (3a/3b/3c) with mandatory Q&A Analysis Log. See `qa-synthesis-fix.md`. |
| 8 | iPad/WHA share evhash (f611c8fee63e3f44) — identical qualitative text | Low | **Closed** | By design — same directional guidance, null numerics, similar conditions → same value fingerprint. Separate nodes via segment in ID. |
| 9 | Peak context 105k tokens (81% window) — compaction risk on larger transcripts | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 10 | FX Impact extracted as standalone item instead of Revenue condition | Low | **Fixed** | Added quality filter to SKILL.md §13: factors affecting a metric go in `conditions`, not as standalone items. |

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

---

## What went RIGHT

- Auto-loaded all 3 mandatory files (SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md)
- Step 1 context loading: company, FYE, concept cache, member cache, existing tags, prior extractions — all correct
- Step 2: Read ALL transcript sections (PR + Q&A) before extracting
- Step 3: Good extraction quality — 11 items, captured all key metrics
- Step 4: Used Bash to call guidance_ids.py for ID computation (8 Bash calls)
- No context compaction occurred (stayed at 81%)
- Faster than previous run (5 min vs 8.5 min)

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

**Fix applied** (detailed plan: `qa-synthesis-fix.md`):
- Split Step 3 into two-phase extraction for transcripts: 3a (PR only), 3b (Q&A enrichment, MANDATORY), 3c (merged items)
- Step 3b requires per-exchange verdict (ENRICHES / NEW ITEM / NO GUIDANCE) with mandatory topic summary describing what management discussed — forces content engagement before verdict (chain-of-thought principle)
- Output template adds `Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})` as final checkpoint
- PROFILE_TRANSCRIPT.md Duplicate Resolution rewritten to reference 3a/3b/3c (procedural, not aspirational)
- SKILL.md §12 Dedup Rule updated: two-phase for transcripts, single-pass for all other source types
- Zero code changes. Three files updated: `guidance-extract.md`, `PROFILE_TRANSCRIPT.md`, `SKILL.md`
- **Pending:** Rerun AAPL transcript to verify Q&A Analysis Log appears with enrichments

### ISSUE 8 (Low → Closed): iPad/WHA share evhash

Both share `f611c8fee63e3f44`. Qualitative text identical ("decelerate significantly from Sept quarter"), both have null numerics. Quotes differ but evhash doesn't include quote field. Conditions also very similar. **By design** — evhash fingerprints the value signal, and these two items genuinely carry the same directional guidance. They remain separate nodes because the slot-based ID includes segment (`revenue:ipad` vs `revenue:wha`).

### ISSUE 9 (CRITICAL): Peak context 81% — compaction risk

105k/130k tokens used. For larger transcripts (MSFT 30+ Q&A, AMZN multi-segment), this would trigger compaction mid-extraction — exactly RC-1 from Run 1. **Auto-fixed by #1** — CLI path saves ~14k tokens, bringing peak to ~58%.

### ISSUE 10 (Low → Fixed): FX Impact extracted as standalone item

Agent created a standalone `FX Impact` guidance item (-1.0 percent_points) when the CFO's statement ("we expect a negative year-over-year revenue impact of about one percentage point") was a condition on Revenue, not an independent metric. The same information was already in Revenue(Total)'s conditions field (`-1pp FX`), creating redundancy. Previous run correctly folded FX into conditions only.

**Fix applied:** Added quality filter to SKILL.md §13: "If a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count, commodity cost tailwind), capture it in that metric's `conditions` field — not as a standalone item."

---

## Extraction Results (11 items)

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

---

## Edge Summary

| Edge Type | Count | Details |
|---|---|---|
| UPDATES → Guidance | 11/11 | 6 unique Guidance parents (Revenue, Gross Margin, OpEx, OINE, Tax Rate, FX Impact) |
| FROM_SOURCE → Transcript | 11/11 | All linked to AAPL_2023-11-03T17.00.00-04.00 |
| FOR_COMPANY → Company | 11/11 | All linked to AAPL |
| HAS_PERIOD → Period | 11/11 | All linked to guidance_period_320193_duration_FY2024_Q1 (FY2024 Q1) |
| MAPS_TO_CONCEPT → Concept | 6/11 | Revenue(Total), Gross Margin, OpEx, OINE, Tax Rate. Segment Revenue items missing. |
| MAPS_TO_MEMBER → Member | 4/11 | iPhone, Mac, iPad, Services. WHA missing. |
