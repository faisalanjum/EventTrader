# Enrichment Pass Working Brief — Guidance Extraction

This is your working brief. Follow it start to finish. core-contract.md is reference for schema details.

## Scope

Discover new items and enrich existing items from secondary content (per intersection file).

Discovery of secondary-only items is co-equal with enrichment — the secondary section often contains items not found in the primary section.

---

## Pipeline Steps

### STEP 1: FETCH CONTEXT — Load Context

| Action | Query |
|--------|-------|
| Company + CIK | QUERIES.md 1A |
| FYE from 10-K | QUERIES.md 1B — extract month from `periodOfReport` |
| Concept cache | `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER` → reads `/tmp/concept_cache_{TICKER}.json` |
| Member map + cache | (same command — runs 2A, 2B, and member map in one call) → member map used by CLI at write time, no agent read needed |
| Existing guidance tags | QUERIES.md 7A |

### STEP 2: LOAD EXISTING ITEMS — Readback Primary Pass Items

Query 7E with `source_id = $SOURCE_ID`. These are the items written by the primary pass.

7E returns: `period_u_id` (gp_ format), `gu.period_scope`, `gu.time_type`, `gp.start_date AS gp_start_date`, `gp.end_date AS gp_end_date`. No `period_node_type`.

**If 7E returns 0 items**: Return error `PHASE_DEPENDENCY_FAILED — no primary pass items found for source {SOURCE_ID}. Run primary pass first.`

Record `given_date` from existing items — all items from the same source share it. Use this for any new secondary-only items.

**Prior-source baseline (query 7F)**: Load all labels previously extracted from this company's sources of this asset type, with frequency and last-seen date. Pass `$source_type = {ASSET}`. Used in the completeness check (Step 5).

### STEP 3: LOAD SECONDARY CONTENT

Fetch secondary content using queries defined in your intersection file.

If no secondary content found: Return early with `NO_SECONDARY_CONTENT`.

### STEP 4: ENRICHMENT — Process Secondary Content

Process each piece of secondary content against the existing items from Step 2. For each, produce a verdict:

#### Verdict Taxonomy

| Verdict | Meaning | Action |
|---------|---------|--------|
| `ENRICHES {item}` | Secondary content adds detail to an existing item | Update `qualitative`, `conditions`, `quote`, and/or numeric fields. Append detail with quote prefix from intersection file. |
| `NEW ITEM` | Secondary content contains item not in any existing item | Create new item with quote prefix from intersection file. Apply metric decomposition — split qualified metrics into base `label` + `segment`. |
| `NO GUIDANCE` | Content has no forward-looking material | Skip silently. |

**Rule**: Never skip an ENRICHES verdict — all must be written even if idempotent. MERGE+SET handles idempotency safely.

Enrichment updates the item in place — do not create a second item for the same slot.

### STEP 5: COMPLETENESS CHECK — Compare vs 7F Baseline

Load 7F baseline (all labels from prior sources of this asset type, frequency + last-seen date). Compare against current extraction (primary pass items + any NEW ITEMs from Step 4).

For missing labels, re-scan secondary content for that metric. Append to the log:

- `NEW ITEM` — found in secondary content, created
- `DROPPED — {label} (last seen {date}, {N}x prior)` — company did not guide on this metric this quarter

### STEP 6: VALIDATE + WRITE — Only Changed/New Items

**ONLY** items that changed or are new. Do NOT re-write items that were not enriched.

For each enriched item: start from the FULL 7E readback item as your semantic base. Apply secondary enrichments to specific fields. Do NOT omit any existing semantic/write field from that base item — `SET` overwrites everything including null.

Preserve from 7E unless the Q&A changes it: `given_date`, `period_scope`, `time_type`, `fiscal_year`, `fiscal_quarter`, `segment`, `low`/`mid`/`high`, `basis_norm`, `basis_raw`, `derivation`, `qualitative`, `quote`, `section`, `source_key`, `source_type`, `conditions`, `xbrl_qname`, `unit_raw` (when present), `period_u_id`, `gp_start_date`, `gp_end_date`.

Exceptions:
- `member_u_ids`: always set `[]` in the payload — the CLI repopulates these deterministically
- `source_refs`: rebuild per the intersection file for the new secondary evidence; 7E does not return prior `source_refs`
- CLI-owned deterministic fields (`guidance_id`, `guidance_update_id`, `evhash16`, canonicalized numeric/unit fields): do NOT hand-maintain these from 7E

For new secondary-only items: build from scratch using CIK/FYE from Step 1. Use `given_date` from Step 2.

1. **Period routing** (new items only — enriched items already have `period_u_id` from 7E): include LLM period fields (`fiscal_year`, `fiscal_quarter`, `half`, `month`, `long_range_start_year`, `long_range_end_year`, `calendar_override`, `sentinel_class`, `time_type`) in the item. The CLI computes `period_u_id` (gp_ format) via `build_guidance_period_id()` automatically.

2. **Resolve xbrl_qname** against concept cache. Set `member_u_ids: []` — the CLI resolves members from precomputed CIK-based maps at write time.

### Member Resolution Note

The CLI (`guidance_write_cli.py`) is the sole authority for member resolution. Always set `member_u_ids: []` in the JSON payload — the CLI populates it from precomputed CIK-based maps (or live fallback in write mode).

3. **Assemble JSON payload** and write to `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json`. **Use the exact same top-level envelope as primary pass** — the CLI requires `source_id`, `source_type`, `ticker`, and `fye_month` at top level:

```json
{
    "source_id": "{SOURCE_ID}",
    "source_type": "{ASSET}",
    "ticker": "{TICKER}",
    "fye_month": {FYE_MONTH from Step 1},
    "items": [ ... ]
}
```

Do NOT wrap items in a `company` object.

For enrichment, prefer this pattern:
- Existing items: reuse `period_u_id` from 7E when the period is unchanged, but let the CLI recompute deterministic IDs/hash/canonical fields from the updated payload
- New secondary-only items: items do NOT need pre-computed IDs or `period_u_id` — the CLI calls `build_guidance_period_id()` and `build_guidance_ids()` internally

Do NOT rely on pre-computed `guidance_update_id`/`evhash16` from 7E as authoritative. Enrichment may change slot-defining fields (`basis_norm`, `segment`, `label`, `period_u_id`) or evidence-hash inputs (`low`/`mid`/`high`, unit, `qualitative`, `conditions`), so the CLI must remain the authority for recomputation.

4. **Invoke CLI** — same invocation as primary pass:

```bash
# dry_run / shadow
bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json --dry-run

# write
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json --write
```

---

## Secondary Content Analysis Log Format (MANDATORY)

You MUST produce a Secondary Content Analysis Log. Format per intersection file. Every entry MUST include a verdict and topic summary:

```
Secondary Content Analysis Log:
#{N} (source): VERDICT — topic summary
```
(see intersection file for source identifier)

---

## Quote Enrichment Format

- Existing items enriched: use quote prefixes defined in your intersection file.
- New secondary-only items: use secondary quote prefix from intersection file.
- When enriching `qualitative` or `conditions`, merge the richer information from both sources.
- If secondary content gives more precise numbers than primary, update `low`/`mid`/`high` and change `derivation` if appropriate.
- `section` for enriched items: see intersection file for section format.
- `source_refs`: see intersection file for source_ref format.

---

## Extraction Rules

### Quality / Acceptance Filters

- **Forward-looking only** — target period must be after source date. Past-period results are actuals, not guidance.
- **Specificity required** — qualitative guidance needs a quantitative anchor: "low single digits", "double-digit", "mid-teens". Skip vague terms ("significant", "strong") without magnitude.
- **No fabricated numbers** — if guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values.
- **Quote max 500 chars** — truncate at sentence boundary with "..." if needed. No citation = no node.
- **100% recall priority** — when in doubt, extract it. False positives > missed guidance.
- **Corporate announcements** — Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans). These belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable.

### Metric Decomposition (for new items)

Split qualified metrics into base `label` + `segment`. Business dimensions (product, geography, business unit) become `segment`; the base metric stays as `label`. Accounting modifiers stay part of `label`.

**Simple test**: Could you have this metric for iPhone AND for Total? If yes, the prefix is a segment — decompose.

---

## Write Rules

- ONLY write changed/new items (not unchanged existing items)
- Same CLI invocation as primary pass
- Same JSON payload format
- Complete items only — every item written must include ALL fields from the 7E readback plus secondary enrichments

---

## Output Format

```
Items from Phase 1: {count}
Items enriched: {count}
New secondary-only items: {count}
Items written: {count}
Secondary units analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})
```

If team task assigned, update via TaskUpdate with enrichment summary.

---

## Result File

Write `/tmp/extract_pass_{TYPE}_enrichment_{SOURCE_ID}.json` with status, counts.
