# Enrichment Pass Working Brief — Guidance Extraction

This is your complete working brief. Follow it start to finish. core-contract.md is reference for schema details.

## Scope

Discover new items and enrich existing items from secondary content (Q&A for transcripts).

Discovery of Q&A-only items is co-equal with enrichment — management regularly reveals guidance in Q&A that never appears in prepared remarks.

---

## Pipeline Steps

### STEP 1: FETCH CONTEXT — Load Context

| Action | Query |
|--------|-------|
| Company + CIK | QUERIES.md 1A |
| FYE from 10-K | QUERIES.md 1B — extract month from `periodOfReport` |
| Concept cache | QUERIES.md 2A |
| Member cache | QUERIES.md 2B |
| Existing guidance tags | QUERIES.md 7A |

### STEP 2: LOAD EXISTING ITEMS — Readback Primary Pass Items

Query 7E with `source_id = $SOURCE_ID`. These are the PR-extracted items written by the primary pass.

7E returns: `period_u_id` (gp_ format), `gu.period_scope`, `gu.time_type`, `gp.start_date AS gp_start_date`, `gp.end_date AS gp_end_date`. No `period_node_type`.

**If 7E returns 0 items**: Return error `PHASE_DEPENDENCY_FAILED — no primary pass items found for source {SOURCE_ID}. Run primary pass first.`

Record `given_date` from existing items — all items share the same `conference_datetime`. Use this for any new Q&A-only items.

**Prior-transcript baseline (query 7F)**: Load all labels previously extracted from this company's transcripts, with frequency and last-seen date. Used in the completeness check (Step 5).

### STEP 3: LOAD SECONDARY CONTENT — Fetch Q&A

Query 3F to get Q&A exchanges. If 3F returns empty, try 3C fallback (QuestionAnswer nodes — ~40 transcripts use `HAS_QA_SECTION` instead of `HAS_QA_EXCHANGE`).

If both return empty: Return early with `NO_QA_CONTENT`.

### STEP 4: Q&A ENRICHMENT — Process Each Exchange

Process EACH Q&A exchange against the existing items from Step 2. For every exchange, produce a verdict:

#### Verdict Taxonomy

| Verdict | Meaning | Action |
|---------|---------|--------|
| `ENRICHES {item}` | Q&A adds detail to an existing item | Update `qualitative`, `conditions`, `quote`, and/or numeric fields. Append `[Q&A]` detail in quote. |
| `NEW ITEM` | Q&A contains guidance not in any existing item | Create new item with `[Q&A]` quote prefix. Apply metric decomposition — split qualified metrics into base `label` + `segment`. |
| `NO GUIDANCE` | Exchange has no forward-looking content | Skip silently. |

**Rule**: Never skip an ENRICHES verdict — all must be written even if idempotent. MERGE+SET handles idempotency safely.

Enrichment updates the item in place — do not create a second item for the same slot.

### STEP 5: COMPLETENESS CHECK — Compare vs 7F Baseline

Load 7F baseline (all labels from prior transcripts, frequency + last-seen date). Compare against current extraction (primary pass items + any NEW ITEMs from Step 4).

For missing labels, re-scan Q&A exchanges for that metric. Append to the log:

- `NEW ITEM` — found in Q&A, created
- `DROPPED — {label} (last seen {date}, {N}x prior)` — company did not guide on this metric this quarter

### STEP 6: VALIDATE + WRITE — Only Changed/New Items

**ONLY** items that changed or are new. Do NOT re-write items that were not enriched.

For each enriched item: start from the FULL item read in Step 2. Apply Q&A enrichments to specific fields. Do NOT omit any field from the existing item — SET overwrites everything including null.

For new Q&A-only items: build from scratch using CIK/FYE from Step 1. Use `given_date` from Step 2.

1. **Period routing** (new items only — enriched items already have `period_u_id` from 7E): include LLM period fields (`fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_start_year`, `long_range_end_year`, `calendar_override`, `sentinel_class`, `time_type`) in the item. The CLI computes `period_u_id` (gp_ format) via `build_guidance_period_id()` automatically.

2. **Resolve xbrl_qname** against concept cache, **member match** for segment items (same as primary pass validation).

3. **Assemble JSON payload** and write to `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json`. Same JSON payload format as primary pass. Items do NOT need pre-computed IDs or `period_u_id` — the CLI calls `build_guidance_period_id()` and `build_guidance_ids()` internally.

4. **Invoke CLI** — same invocation as primary pass:

```bash
# dry_run / shadow
bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}_qa.json --dry-run

# write
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}_qa.json --write
```

---

## Q&A Analysis Log Format (MANDATORY)

You MUST produce a Q&A Analysis Log. Every entry MUST include a topic summary:

```
Q&A Analysis Log:
#1 (analyst name): ENRICHES Revenue(iPhone) — CFO discusses supply-demand balance, normalized YoY growth excluding launch timing
#2 (analyst name): NO GUIDANCE — asked about installed base size, CEO cited 2.2B active devices (historical, not forward-looking)
#3 (analyst name): NEW ITEM — CapEx guidance, CFO says "approximately $2 billion" for next fiscal year
...
```

---

## Quote Enrichment Format

- Existing items enriched: `[PR] original text... [Q&A] additional detail...`
- New Q&A-only items: `[Q&A] guidance text...`
- When enriching `qualitative` or `conditions`, merge the richer information from both sources.
- If Q&A gives more precise numbers than PR, update `low`/`mid`/`high` and change `derivation` if appropriate.
- `section` for enriched items becomes `CFO Prepared Remarks + Q&A` (or specific Q&A reference).
- `source_refs`: array of QAExchange node IDs that contributed. Build each ID as `{SOURCE_ID}_qa__{sequence}` where `sequence` is the exchange number. Example: `"source_refs": ["AAPL_2023-11-03T17.00_qa__3", "AAPL_2023-11-03T17.00_qa__7"]`.

---

## Extraction Rules

### Quality / Acceptance Filters

- **Forward-looking only** — target period must be after source date. Past-period results are actuals, not guidance.
- **Specificity required** — qualitative guidance needs a quantitative anchor: "low single digits", "double-digit", "mid-teens". Skip vague terms ("significant", "strong") without magnitude.
- **No fabricated numbers** — if guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values.
- **Quote max 500 chars** — truncate at sentence boundary with "..." if needed. No citation = no node.
- **100% recall priority** — when in doubt, extract it. False positives > missed guidance.
- **Corporate announcements ARE extractable** — management decisions that allocate specific capital or change shareholder returns.

### Metric Decomposition (for new items)

Split qualified metrics into base `label` + `segment`. Business dimensions (product, geography, business unit) become `segment`; the base metric stays as `label`. Accounting modifiers stay part of `label`.

**Simple test**: Could you have this metric for iPhone AND for Total? If yes, the prefix is a segment — decompose.

---

## Write Rules

- ONLY write changed/new items (not unchanged existing items)
- Same CLI invocation as primary pass
- Same JSON payload format
- Complete items only — every item written must include ALL fields from the 7E readback plus Q&A enrichments

---

## Output Format

```
Items from Phase 1: {count}
Items enriched: {count}
New Q&A-only items: {count}
Items written: {count}
Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})
```

If team task assigned, update via TaskUpdate with enrichment summary.

---

## Result File

Write `/tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json` with status, counts.
