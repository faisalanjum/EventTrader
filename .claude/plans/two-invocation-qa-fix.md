# Two-Invocation Q&A Enrichment — Implementation Plan

## Problem

Single-agent two-phase extraction (3a/3b/3c) failed to reliably produce Q&A enrichment. Run 3 showed the agent collapses all sub-steps into one thinking pass — there's no tool call boundary between 3a and 3b. The Q&A Analysis Log was produced post-hoc, not as a working artifact. Result: 3/10 items enriched (up from 0/11 in Run 2, but not reliable).

**Root cause**: All three sub-steps (3a, 3b, 3c) are "LLM thinking" with no physical boundary. The agent reads content (tool call), thinks about everything at once (ultrathink), writes JSON (tool call). Two-phase structure lives entirely inside reasoning, where we have no enforcement.

**Fix**: Same principle as removing the write MCP tool — structural enforcement. Split transcript extraction into two separate agent invocations. Invocation 2's entire purpose is Q&A enrichment. It can't skip it.

## Architecture

```
Orchestrator (session agent or SDK)
  │
  ├── Invocation 1: guidance-extract (PR only)
  │     Input:  AAPL transcript AAPL_2023-11-03T17.00.00-04.00 MODE=write
  │     Scope:  Prepared Remarks only. Ignore Q&A.
  │     Output: 10 items written to graph via CLI
  │
  └── Invocation 2: guidance-qa-enrich (Q&A only)
        Input:  AAPL transcript AAPL_2023-11-03T17.00.00-04.00 MODE=write
        Scope:  Read Q&A (3F) + existing items (7E) → enrich/add → write via CLI
        Output: Updated items + new Q&A-only items written (MERGE+SET)
```

## Changes Required

### 1. New agent: `.claude/agents/guidance-qa-enrich.md`

**Purpose**: Q&A enrichment only. Reads existing PR-extracted items from graph, reads Q&A exchanges, enriches items, writes back via CLI.

**Tools** (same as guidance-extract):
```yaml
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - Write
  - Read
```

**Pipeline**:

1. **Auto-Load** — Read SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md (same 3 files)

2. **Load context** — Query 1A (Company/CIK), 1B (FYE), 2A (concepts), 2B (members), 7A (existing guidance tags). Needed for new Q&A-only items: `build_period_u_id()` requires CIK, fiscal mapping requires FYE, XBRL/member matching requires 2A/2B, canonical label reuse requires 7A.

3. **Load existing items** — Query 7E (new query, see below) to get ALL fields of items already written by Invocation 1. These are the base items to enrich. Copy `given_date` from existing items for any new Q&A-only items (all items share the same conference_datetime). **If 7E returns 0 items, return error: `PHASE_DEPENDENCY_FAILED` — no Phase 1 items found for this source. Run guidance-extract first.**

4. **Load Q&A content** — Query 3F to get Q&A exchanges only. If 3F returns empty, try 3C fallback (QuestionAnswer nodes — ~40 transcripts use `HAS_QA_SECTION` instead of `HAS_QA_EXCHANGE`).

5. **Q&A Enrichment** — For EACH Q&A exchange, compare management response against existing items. Produce verdict:
   - `ENRICHES {item}` → update qualitative/conditions/quote. Append `[Q&A]` to quote.
   - `NEW ITEM` → create new item with `[Q&A]` prefix
   - `NO GUIDANCE` → skip

   Produce Q&A Analysis Log with topic summaries. **Implementation note**: Copy the Q&A Analysis Log format, enrichment rules, and examples from guidance-extract.md Step 3b (lines 98-133) into guidance-qa-enrich.md BEFORE removing 3b from guidance-extract. That content is the source of truth and will not exist elsewhere after Change 3.

6. **Assemble complete items** — ONLY for items that changed or are new. Do NOT re-write items that were not enriched. For each enriched item: start from the FULL item read in step 3, apply Q&A enrichments. For new items: build from scratch using CIK/FYE from step 2. **CRITICAL**: every enriched item must include ALL fields from the existing item — do not omit any field.

7. **Validate + Write** — Same Step 4/5 as guidance-extract (guidance_ids.py, CLI write). MERGE+SET updates existing nodes, creates new ones.

**Output**:
```
Items from Phase 1: {count}
Items enriched: {count}
New Q&A-only items: {count}
Items written: {count}
Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})
```

### 2. New query: 7E — Full GuidanceUpdate Readback for Source (QUERIES.md)

Current 7D returns a subset of fields. The enrichment agent needs ALL fields plus Period and edge data to produce complete items for MERGE+SET.

```cypher
MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(src)
WHERE src.id = $source_id
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(p:Period)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(c:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(m:Member)
RETURN g.label, g.id AS guidance_id,
       gu.id, gu.evhash16, gu.given_date, gu.period_type,
       gu.fiscal_year, gu.fiscal_quarter, gu.segment,
       gu.low, gu.mid, gu.high, gu.canonical_unit,
       gu.basis_norm, gu.basis_raw, gu.derivation,
       gu.qualitative, gu.quote, gu.section,
       gu.source_key, gu.source_type, gu.conditions,
       gu.xbrl_qname, gu.unit_raw,
       p.u_id AS period_u_id, p.period_type AS period_node_type,
       collect(DISTINCT m.u_id) AS member_u_ids
ORDER BY g.label, gu.segment
```

**Why all fields**: MERGE+SET overwrites ALL properties. If the enrichment agent produces an item missing `low`/`high` from Phase 1, SET writes null. Reading all fields + Period ensures the agent has the complete baseline for a valid CLI payload.

### 3. Modify: `.claude/agents/guidance-extract.md`

**For transcripts only**: Remove Steps 3b/3c and the Q&A Analysis Log requirement. The agent now does PR extraction only for transcripts.

Specifically:
- Remove the transcript note in Step 2 ("Do NOT extract from both simultaneously...")
- Replace the two-phase Step 3 section with: **"For transcripts, extract from Prepared Remarks ONLY. Q&A enrichment is handled by a separate agent invocation (guidance-qa-enrich). Ignore `qa_exchanges` from query 3B."**
- Remove Steps 3a/3b/3c sub-structure (revert to single Step 3 for all source types)
- Remove `Q&A exchanges analyzed:` from Output template
- Keep everything else unchanged (Steps 1, 4, 5, CLI invocation, etc.)

**Non-transcript source types**: Unchanged. Single-pass extraction as before.

### 4. Modify: `PROFILE_TRANSCRIPT.md`

Update Duplicate Resolution section:
- Current: References Step 3a/3b/3c (two-phase within one agent)
- New: "PR extraction handled by guidance-extract agent. Q&A enrichment handled by guidance-qa-enrich agent. Two separate invocations, two writes. MERGE+SET ensures second write safely updates existing nodes."

Keep all the enrichment rules (same metric → enrich in place, new metric → new item, values conflict → use more precise, never skip detail). These move to guidance-qa-enrich's prompt.

### 5. Modify: `SKILL.md §12 Dedup Rule`

Update transcript reference:
- Current: "Two-phase extraction — PR first (Step 3a), then Q&A enrichment exchange-by-exchange (Step 3b)."
- New: "Two-invocation extraction — PR via guidance-extract, Q&A enrichment via guidance-qa-enrich. MERGE+SET handles second write safely."

### 6. Modify: `qa-synthesis-fix.md`

Update status: single-agent two-phase was insufficient. Escalated to two-invocation approach per the plan's own Fallback section.

## What Does NOT Change

- **guidance_write_cli.py / guidance_writer.py / guidance_write.sh**: No code changes. Concept inheritance still runs.
- **guidance_ids.py**: No code changes.
- **QUERIES.md queries 1A-3E, 4-6, 7A-7D**: Unchanged.
- **Non-transcript source types**: Unchanged. Single-pass extraction.
- **CLI JSON format**: Same payload structure for both invocations.
- **MERGE+SET semantics**: Same pattern. Invocation 2 writes to same slot IDs → updates nodes.

## SET Overwrite Risk Mitigation

The main risk: Invocation 2 produces an enriched item but drops a field from Phase 1 (e.g., forgets `low`/`high`). SET writes null.

Mitigations:
1. **7E query**: Agent reads ALL fields from existing nodes before enriching. Complete baseline in context.
2. **Prompt instruction**: "Start from the complete item as returned by 7E. Apply Q&A enrichments to specific fields. Do NOT omit any field from the existing item."
3. **CLI validation**: `guidance_write_cli.py` already validates required fields. Items missing required fields fail validation.
4. **Acceptable tradeoff**: Occasional field-dropping on a few items across thousands of runs is a lesser failure than zero Q&A enrichment across all runs.

## Orchestration

**For manual runs** (current): The session agent spawns two Task calls sequentially:
```
Task 1: guidance-extract → AAPL transcript AAPL_... MODE=write
Task 2: guidance-qa-enrich → AAPL transcript AAPL_... MODE=write
```
Task 2 must wait for Task 1 to complete (sequential, not parallel).

**For SDK**: SDK triggers guidance-extract, then guidance-qa-enrich in sequence. Same parameters.

**For non-transcript sources**: Only guidance-extract runs. No Invocation 2 needed.

## Verification Plan

**Dry-run dependency**: Invocation 2 reads existing items from the graph (query 7E). For Invocation 2 to work — even in dry_run mode — Invocation 1 must have already run with `MODE=write` so items exist in the graph. There is no dry_run-only path for testing both invocations end-to-end.

1. Delete any existing Run 3 dry-run data (if written)
2. Run Invocation 1: `guidance-extract AAPL transcript AAPL_2023-11-03T17.00.00-04.00 MODE=write`
3. Verify items written (expect ~10 PR-only items)
4. Run Invocation 2: `guidance-qa-enrich AAPL transcript AAPL_2023-11-03T17.00.00-04.00 MODE=dry_run`
5. Check:
   - Q&A Analysis Log present with per-exchange verdicts + topic summaries
   - Items enriched with `[Q&A]` in quotes and `section` containing `+ Q&A`
   - No fields dropped from Phase 1 items (compare before/after)
   - Any new Q&A-only items created
6. Compare against Run 2 (0 enrichments) and Run 3 (3 enrichments)
