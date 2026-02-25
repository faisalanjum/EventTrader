# Q&A Synthesis Fix — Complete Plan

> **Status**: Single-agent two-phase (3a/3b/3c) was insufficient. Run 3 proved the agent collapses sub-steps into one thinking pass — no tool call boundary between 3a and 3b. Escalated to two-invocation approach per the Fallback section below. See `two-invocation-qa-fix.md` for the implementation plan.

## Problem Statement

In Run 2 (AAPL FQ1 FY2024 transcript extraction), all 11 guidance items came from Prepared Remarks only. Zero Q&A enrichment despite the agent reading all Q&A exchanges in Step 2. The `section` field was `"CFO Prepared Remarks"` and all quotes had `[PR]` prefix for every item. PROFILE_TRANSCRIPT.md §15C rule ("synthesize richest combined version") was ignored.

**Root cause**: Cognitive satisficing. When PR + Q&A arrive together (query 3B returns both), the agent extracts from the structured CFO remarks (clean numbers, explicit ranges) and treats extraction as "done." Q&A is conversational, noisy, and requires matching analyst questions to specific items. The agent takes the path of least resistance.

**Why prompt instructions alone failed**: The §15C rule is aspirational — it tells the agent WHAT to do ("synthesize richest combined version per metric") but doesn't structure the WORK to make it happen. Step 3 is one undifferentiated cognitive step. There's no procedural separation between "extract from PR" and "enrich from Q&A."

## Design Decision

**Single write, two-phase extraction.** Split Step 3 into explicit sub-steps (3a, 3b, 3c) that force the agent to process Q&A exchange-by-exchange against PR-derived items. Items are held in memory, enriched, then written once via CLI.

**Why not two writes (write after PR, then write after Q&A)?**
1. SET overwrites ALL properties — the Q&A enrichment write must include the complete merged item, not just deltas. If the agent forgets a field from Phase 1, it overwrites good data with null. Across thousands of docs, some fields would get dropped.
2. More tool calls, more context consumed.
3. Phase 1 items survive compaction better as the agent's own recent output than as tool results from a prior write.
4. Two-write remains a valid fallback (MERGE+SET supports it natively) — but single write with two-phase extraction is cleaner.

## Changes Required

### File 1: `.claude/agents/guidance-extract.md`

**What changes**: Replace monolithic Step 2 + Step 3 with structured sub-steps for transcript source type. Other source types unchanged.

#### Current Step 2 (replace):

```
### Step 2: Fetch Source Content

Route by `SOURCE_TYPE` to correct QUERIES.md section:

| Source Type | Primary | Fallbacks |
|-------------|---------|-----------|
| `transcript` | 3B (structured) | 3C (Q&A Section), 3D (full text) |
| `8k` | 4G (inventory) → 4C (exhibit) | 4E (section), 4F (filing text) |
| `10q` / `10k` | 5B (MD&A) | 5C (financial stmts), 4F (fallback) |
| `news` | 6A (single item) | 6B (channel-filtered batch) |

Apply empty-content rules from SKILL.md §17.
```

#### Proposed Step 2 (replacement):

```
### Step 2: Fetch Source Content

Route by `SOURCE_TYPE` to correct QUERIES.md section:

| Source Type | Primary | Fallbacks |
|-------------|---------|-----------|
| `transcript` | 3B (structured) | 3C (Q&A Section), 3D (full text) |
| `8k` | 4G (inventory) → 4C (exhibit) | 4E (section), 4F (filing text) |
| `10q` / `10k` | 5B (MD&A) | 5C (financial stmts), 4F (fallback) |
| `news` | 6A (single item) | 6B (channel-filtered batch) |

Apply empty-content rules from SKILL.md §17.

**Transcript note**: Query 3B returns BOTH `prepared_remarks` and `qa_exchanges`. Do NOT extract from both simultaneously. Hold the full 3B result and process in two phases (Step 3a, then Step 3b). If `qa_exchanges` is empty, try fallback 3C before concluding Q&A is missing.
```

#### Current Step 3 (replace):

```
### Step 3: LLM Extraction

This is the agent doing its core job — no external tool call.

- Apply per-source profile rules (loaded in auto-load step)
- Apply quality filters from SKILL.md §13
- For each guidance item, extract: `quote`, period intent (`fiscal_year`, `fiscal_quarter`, `period_type`), `basis_raw`, metric (`label`), numeric values (`low`/`mid`/`high`), `derivation`, `segment`, `conditions`, XBRL candidates
- Use existing Guidance tags (from Step 1) to reuse canonical metric names
```

#### Proposed Step 3 (replacement):

```
### Step 3: LLM Extraction

Apply per-source profile rules (loaded in auto-load step), quality filters from SKILL.md §13, and existing Guidance tags (from Step 1) to reuse canonical metric names.

For each guidance item, extract: `quote`, period intent (`fiscal_year`, `fiscal_quarter`, `period_type`), `basis_raw`, metric (`label`), numeric values (`low`/`mid`/`high`), `derivation`, `segment`, `conditions`, XBRL candidates.

**For transcripts, extraction is two-phase (3a → 3b → 3c). For all other source types, extract in a single pass.**

#### Step 3a: Extract from Prepared Remarks ONLY (transcript)

Process the `prepared_remarks` content from Step 2. Ignore `qa_exchanges` for now.

Output: **Phase 1 items list** — one item per guidance metric found in PR, with all extraction fields populated. Every quote prefixed with `[PR]`.

This is your working item list. You will enrich it in Step 3b.

#### Step 3b: Q&A Enrichment Pass (transcript — MANDATORY)

Process EACH Q&A exchange from the Step 2 result, one at a time. For every exchange, compare the management response against Phase 1 items and produce a verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `ENRICHES {item}` | Q&A adds detail to a Phase 1 item | Update that item's `qualitative`, `conditions`, or `quote` fields. Append Q&A detail with `[Q&A]` prefix in quote. |
| `NEW ITEM` | Q&A contains guidance for a metric/segment NOT in Phase 1 | Create a new item with `[Q&A]` quote prefix. |
| `NO GUIDANCE` | Exchange has no forward-looking content | Skip. |

**You MUST produce a Q&A Analysis Log** before proceeding to Step 3c. Every entry MUST include a brief topic summary of what the management response discussed — this is required even for NO GUIDANCE verdicts. Format:

```
Q&A Analysis Log:
#1 (analyst name): ENRICHES Revenue(iPhone) — CFO discusses supply-demand balance, normalized YoY growth excluding launch timing
#2 (analyst name): NO GUIDANCE — asked about installed base size, CEO cited 2.2B active devices (historical, not forward-looking)
#3 (analyst name): NEW ITEM — CapEx guidance, CFO says "approximately $2 billion" for next fiscal year
#4 (analyst name): ENRICHES Gross Margin — CFO explains commodity cost tailwinds and mix shift toward services
...
```

Rules:
- Process ALL exchanges. Do not stop early.
- Enrichment updates the item in place — do not create a second item for the same slot.
- When enriching `quote`, append the Q&A quote after the PR quote: `[PR] original quote... [Q&A] additional detail...`
- When enriching `qualitative` or `conditions`, merge the richer information from both sources.
- If Q&A gives more precise numbers than PR for the same metric, update `low`/`mid`/`high` and change `derivation` if appropriate.
- `section` for enriched items becomes `CFO Prepared Remarks + Q&A` (or specific Q&A reference for the enrichment source).

#### Step 3c: Final Item List (transcript)

Produce the final merged items:
- Phase 1 items enriched by Step 3b (with combined PR + Q&A data)
- Plus any new Q&A-only items from Step 3b

This is the item list that proceeds to Step 4.
```

#### Output section addition (guidance-extract.md)

Add one line to the existing structured output template for transcript source types:

```
Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})
```

This is the final checkpoint — to produce this line, the agent needs the log data from Step 3b. A missing line or `Q&A exchanges analyzed: 0` for a transcript with 15 exchanges is an obvious red flag.

### File 2: `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md`

**What changes**: Update the Duplicate Resolution section to reference the new two-phase pipeline instead of the aspirational "synthesize" rule.

#### Current Duplicate Resolution section (replace):

```
## Duplicate Resolution

**RULE: One write per slot. Read ALL sections (PR + Q&A) first, synthesize the richest combined version per metric, then write once. Neither PR nor Q&A takes precedence — use the best information from both.**

When the same metric appears in BOTH prepared remarks and Q&A:

1. **Synthesize from both** — combine the most specific values, richest qualitative detail, and clearest conditions from PR AND Q&A into ONE extraction per metric. Neither section takes precedence; use whichever has better data for each field.
   - Example: PR gives a numeric range, Q&A adds a condition → extract the range WITH the condition
   - Example: PR says "mid-40s gross margin", Q&A says "46% to 47%" → use the more precise numbers (46-47%) but keep any qualitative context from PR
   - Example: Q&A reveals a segment breakdown not in PR → include it

2. **If values directly conflict** → use the more precise or more recent statement, but combine any non-conflicting detail from both

3. **Never skip detail from either section** — if PR has context that Q&A lacks (or vice versa), fold it into the extraction
```

#### Proposed Duplicate Resolution section (replacement):

```
## Duplicate Resolution (Two-Phase — see guidance-extract.md Step 3a/3b/3c)

**RULE: One write per slot. Extract from PR first (Step 3a), then enrich from Q&A exchange-by-exchange (Step 3b), then write the merged result once (Step 5).**

Extraction is two-phase for transcripts. Do NOT extract from PR and Q&A simultaneously.

### Phase 1 (Step 3a): PR Extraction
Extract all guidance items from prepared remarks. These are your base items.

### Phase 2 (Step 3b): Q&A Enrichment
For EACH Q&A exchange, check management responses against Phase 1 items:

1. **Same metric, additional detail** → enrich the Phase 1 item in place:
   - PR gives a numeric range, Q&A adds a condition → update `conditions` with the Q&A detail
   - PR says "mid-40s gross margin", Q&A says "46% to 47%" → update to more precise numbers (46-47%), keep any qualitative context from PR
   - Q&A clarifies basis ("that's on a non-GAAP basis") → update `basis_norm` and `basis_raw`
   - Append Q&A quote after PR quote: `[PR] original... [Q&A] additional...`

2. **New metric/segment from Q&A** → create a new item with `[Q&A]` prefix

3. **Values conflict** → use the more precise or more recent statement, combine non-conflicting detail

4. **Never skip detail from either section** — if PR has context that Q&A lacks (or vice versa), fold it in

### Merge Result (Step 3c)
Final items = enriched Phase 1 items + new Q&A-only items. One write per slot.
```

### File 3: `.claude/skills/guidance-inventory/SKILL.md`

**What changes**: Update §12 Source Processing dedup rule to reference two-phase extraction for transcripts.

#### Current line (SKILL.md §12, Dedup Rule):

```
### Dedup Rule

Deterministic slot-based `GuidanceUpdate.id` enforces dedup. Same slot = same ID → MERGE + SET updates properties. No section of a source takes precedence — read ALL content first, synthesize the richest combined version per metric from every section, then write once per slot.
```

#### Proposed replacement:

```
### Dedup Rule

Deterministic slot-based `GuidanceUpdate.id` enforces dedup. Same slot = same ID → MERGE + SET updates properties.

**Transcripts**: Two-phase extraction — PR first (Step 3a), then Q&A enrichment exchange-by-exchange (Step 3b). See guidance-extract.md Step 3 and PROFILE_TRANSCRIPT.md Duplicate Resolution.

**All other source types**: Read all content first, extract the richest version per metric, write once per slot.
```

## What Does NOT Change

- **Step 1** (Load Context): Unchanged.
- **Step 2** (Fetch Source Content): Query 3B still fetches both PR and Q&A. Only the processing order changes.
- **Step 4** (Deterministic Validation): Unchanged. Runs on the final merged items from Step 3c.
- **Step 5** (Write to Graph): Unchanged. Single batch write via CLI. All items (PR-enriched + Q&A-only) written in one batch.
- **guidance_write_cli.py / guidance_writer.py / guidance_write.sh**: No code changes.
- **guidance_ids.py**: No code changes.
- **QUERIES.md**: No query changes.
- **Non-transcript source types** (8-K, news, 10-Q, 10-K): Unchanged. Single-pass extraction.

## Verification Plan

1. **Re-run AAPL FQ1 FY2024 transcript** (`AAPL_2023-11-03T17.00.00-04.00`) in dry_run mode
2. Check output for:
   - Q&A Analysis Log present with per-exchange verdicts
   - At least some items have `[Q&A]` content in quotes
   - Items that should be enriched (iPhone supply constraints, Gross Margin drivers) show combined PR+Q&A data
   - Any Q&A-only items are captured
3. Compare item count and quality against Run 2 (11 items, all PR-only)
4. If successful, run on 2-3 more transcripts (MSFT, AMZN) to verify across different Q&A volumes

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Agent still skips Step 3b | Low — numbered step with mandatory log output is harder to skip than an aspirational rule | Q&A Analysis Log absence = red flag. Output summary line (`Q&A exchanges analyzed: ...`) is a final checkpoint — missing or zero = visible red flag |
| Agent produces shallow 3b log ("NO GUIDANCE" for everything) | Low (was Medium) — topic summary requirement forces content engagement before verdict | Agent must summarize what management discussed — writing "CFO discusses margin outlook" + stamping NO GUIDANCE is self-contradictory. Keyword scan on NO GUIDANCE entries flags suspects automatically |
| Context compaction during 3b | Low for typical transcripts; medium for MSFT (30+ Q&A) | Phase 1 items are agent's own recent output — survive compaction better than tool results |
| Q&A enrichment degrades PR data | Very low — enrichment only adds/refines, doesn't remove | Items are held in memory and merged before write; no overwrite risk |
| Two-phase adds latency | Negligible — no additional tool calls, same data, same write | N/A |

## Review Notes (independent assessment)

### Why the Q&A Analysis Log is the critical piece

Without this log, "two-phase extraction" is still just an instruction the agent could satisfy superficially. With it, skipping Q&A becomes visibly detectable. The log works because:

- The agent can't skip Q&A without the log being visibly empty — auditable
- It creates a per-exchange checklist the agent must work through — procedural, not aspirational
- "NO GUIDANCE" is a legitimate verdict — the agent isn't forced to fabricate enrichments
- It's in the agent's own output — survives compaction

The verdict table (ENRICHES / NEW ITEM / NO GUIDANCE) gives three clear categories with concrete actions. No ambiguity about what the agent should do in each case.

### Risk mitigations

**Risk 1: Shallow log** (was Medium, now Low). The topic summary requirement forces the agent to read and summarize each exchange before stamping a verdict. This is preventive, not reactive — the agent must engage with the content to produce the summary. If it writes "CFO discusses gross margin expectations for next quarter" and stamps `NO GUIDANCE`, that's a self-evident contradiction. The correct verdict follows naturally from the forced reasoning step (same principle as chain-of-thought). For automated auditing, a keyword scan (revenue, margin, expects, guidance, outlook, range) on `NO GUIDANCE` entries flags suspect verdicts instantly.

**Risk 2: Agent skips 3b entirely** (Low). The output summary line (`Q&A exchanges analyzed: {count}`) is a final checkpoint in the Output template — the last thing produced. To fill in the counts, the agent needs log data from 3b. A missing line or `Q&A exchanges analyzed: 0` for a transcript with 15 exchanges is an obvious red flag. If skipping persists at scale, the fallback (two separate agent invocations) is the nuclear option.

### Minor observations (not flaws)

1. **Multi-item enrichment from one exchange.** An analyst asks "break down the revenue outlook by segment" and the CFO discusses iPhone, Mac, and Services in one response. The log format shows one verdict per exchange. The agent would naturally write `ENRICHES Revenue(iPhone), Revenue(Mac), Revenue(Services)` — it works, just not explicitly shown in the example.

2. **Quote length after merging.** `[PR] original... [Q&A] additional...` could exceed 500 chars. The existing "Quote max 500 chars — truncate at sentence boundary" rule already covers this. No change needed.

### Why not two-write (Approach B)?

The strongest argument against two-write: our MERGE+SET pattern does `SET gu.low = $low, gu.qualitative = $qualitative, ...` — it overwrites ALL properties with whatever the item contains, including null. In a two-write approach, Phase 2 must reproduce the complete merged item (all Phase 1 fields + Q&A enrichments). If the agent in Phase 2 only includes Q&A-specific fields and forgets to carry over `low`/`high` from Phase 1, those values get nulled. Across thousands of runs, this would happen. Fixing with `COALESCE($field, gu.field)` changes write semantics globally and adds CLI complexity — not worth it.

### Three-file consistency

- `guidance-extract.md` — the pipeline (3a/3b/3c structure)
- `PROFILE_TRANSCRIPT.md` — the duplicate resolution rule (references 3a/3b/3c)
- `SKILL.md §12` — the dedup rule (references two-phase for transcripts, single-pass for others)

## Fallback

If two-phase single-write proves insufficient (agent still skips 3b systematically), escalate to:
- **Two separate agent invocations**: One for PR extraction + write, one for Q&A enrichment + write. This is the nuclear option — physically impossible to skip Q&A because it's a separate agent run. MERGE+SET handles the second write safely. Only pursue if prompt-level fix fails at scale.
