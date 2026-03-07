# Full Pollution Fix: TYPE x ASSET x PASS Separation

## Context

The extraction pipeline has guidance-specific and transcript-specific content mixed into files that should be generic. This creates contamination risk when adding new extraction types or assets. This plan achieves 100% separation of concerns across all three axes (TYPE, ASSET, PASS) by:

1. Moving guidance content out of `transcript.md` (asset profile) into intersection files
2. Genericizing `enrichment-pass.md` (type pass file) to remove all transcript/Q&A vocabulary
3. Updating the enrichment gate in `SKILL.md` to use file-existence instead of sections metadata
4. Parameterizing query 7F in `guidance-queries.md` to work for any asset type
5. Cleaning guidance-flavored comments in `queries-common.md` (shared infrastructure)

**Result**: Zero contamination across all axes. Adding a new extraction type or asset requires ONLY creating new files — zero edits to existing files.

---

## Files Touched: 10 total (2 created + 8 edited)

| # | File | Action | Scope |
|---|------|--------|-------|
| 1 | `types/guidance/assets/transcript-primary.md` | CREATE | ~38 lines |
| 2 | `types/guidance/assets/transcript-enrichment.md` | CREATE | ~72 lines |
| 3 | `assets/transcript.md` | EDIT | -84 lines + 4 rewrites |
| 4 | `assets/transcript-queries.md` | EDIT | 1 line |
| 5 | `.claude/agents/extraction-primary-agent.md` | EDIT | +1 line, 4 text changes |
| 6 | `.claude/agents/extraction-enrichment-agent.md` | EDIT | +1 line, 5 text changes |
| 7 | `types/guidance/enrichment-pass.md` | EDIT | ~29 lines reworded |
| 8 | `SKILL.md` | EDIT | Remove Step 1, rewrite gate, fix result field |
| 9 | `types/guidance/guidance-queries.md` | EDIT | 5 lines (7F query + 7E description) |
| 10 | `queries-common.md` | EDIT | 3 lines (comment cleanup) |

All paths under `.claude/skills/extract/` unless noted. Agent shells under `.claude/agents/`.

Single commit. Single `git revert` rollback.

---

## FILE 1: CREATE `types/guidance/assets/transcript-primary.md` (~38 lines)

Content marked `[... — verbatim]` must be copied character-for-character from the specified transcript.md lines.

```markdown
# Guidance x Transcript — Primary Pass

Rules for extracting guidance from transcript prepared remarks. Loaded at slot 4 by the primary agent.

## Scan Scope — Transcript

Process all prepared remarks content from the transcript. Do not skip any speaker section.
Transcripts are the richest source for extraction.

When falling back to Q&A data (prepared remarks empty/truncated per primary-pass.md),
apply your quality filters from the pass brief. Use quote prefix `[Q&A]` for any items
extracted from Q&A fallback data. The enrichment agent handles specialized Q&A extraction.

## Speaker Hierarchy (Guidance Priority)

[table from transcript.md lines 50-59 — verbatim, all 6 rows + footer]

## Extraction Steps — Prepared Remarks

[steps from transcript.md lines 71-75 — verbatim]

## What to Extract from Prepared Remarks

[table from transcript.md lines 79-87 — verbatim]

## Quote Prefix — Prepared Remarks

[rule from transcript.md lines 91-93 — verbatim]
```

---

## FILE 2: CREATE `types/guidance/assets/transcript-enrichment.md` (~72 lines)

```markdown
# Guidance x Transcript — Enrichment Pass

Rules for enriching/discovering guidance from transcript Q&A exchanges.
Loaded at slot 4 by the enrichment agent.

## Scan Scope — Transcript

Process all Q&A content from the transcript. Do not skip any exchange.
Q&A often reveals guidance not present in prepared remarks.

## Speaker Hierarchy (Guidance Priority)

[table from transcript.md lines 50-59 — verbatim, all 6 rows + footer]

## Why Q&A Matters

[block from transcript.md lines 108-115 — verbatim]

## Q&A Extraction Steps

[steps from transcript.md lines 119-122 — verbatim]

## What to Extract from Q&A

[table from transcript.md lines 126-135 — verbatim]

## Q&A Quote Prefix

[rule from transcript.md lines 139-141 — verbatim]

## Section Field Format

[rules from transcript.md lines 145-148 — verbatim]

## Secondary Content Fetch

Fetch Q&A via query 3F. If empty, try 3C fallback (QuestionAnswer nodes —
~40 transcripts use HAS_QA_SECTION instead of HAS_QA_EXCHANGE).
Each piece of secondary content = one Q&A exchange.
If no Q&A content found, return early with NO_SECONDARY_CONTENT.

## Quote Prefixes

- Primary content (prepared remarks): `[PR]`
- Secondary content (Q&A): `[Q&A]`
- Enriched items: `[PR] original text... [Q&A] additional detail...`

## Section Format

- Enriched items: `CFO Prepared Remarks + Q&A` (or specific Q&A reference)
- source_refs: array of QAExchange node IDs.
  Format: `{SOURCE_ID}_qa__{sequence}` (e.g., `AAPL_2023-11-03T17.00_qa__3`)

## Analysis Log Format

Each entry uses analyst name as source identifier:
```
#1 (analyst name): ENRICHES Revenue(iPhone) — CFO discusses supply-demand balance
#2 (analyst name): NO GUIDANCE — asked about installed base size, historical not forward-looking
#3 (analyst name): NEW ITEM — CapEx guidance, CFO says "approximately $2 billion"
```
```

---

## FILE 3: EDIT `assets/transcript.md` (245 lines → ~161 lines)

### Remove (84 lines):
- Lines 44-59: scan scope + speaker hierarchy (16 lines)
- Lines 69-93: PR extraction steps + table + quote prefix (25 lines)
- Lines 106-148: Q&A everything (43 lines)

### Keep (all generic content):
- Lines 1-42: asset metadata, data structure documentation
- Lines 63-67: PR data format ("Structure" section — how PR data arrives)
- Lines 97-104: Q&A data format ("Structure" section — how Q&A data arrives)
- Lines 150-245: duplicate resolution, empty-content handling, fallbacks, period identification, calendar-to-fiscal mapping, basis traps, given_date, source_key

### Rewrite 4 lines:
| Line | Current | New |
|------|---------|-----|
| 3 | "extraction rules" | "profile" |
| 196 | "guidance statement" | "extracted item" |
| 226 | "See core-contract.md S6 (Basis Rules), S7 (Segment Rules), S13 (Quality Filters)." | "See your type's core-contract for basis, segment, and quality filter rules." |
| 238 | "guidance became public" | "content became public" |

---

## FILE 4: EDIT `assets/transcript-queries.md`

| Line | Current | New |
|------|---------|-----|
| 48 | "Both must be scanned for guidance. See PROFILE_TRANSCRIPT.md for extraction rules." | "Both contain extractable content. See transcript.md for source rules." |

---

## FILE 5: EDIT `.claude/agents/extraction-primary-agent.md`

| Line | Current | New |
|------|---------|-----|
| 25 | "it is your complete working brief" | "it is your working brief" |
| After 37 | (nothing) | INSERT: `4. .claude/skills/extract/types/{TYPE}/assets/{ASSET}-primary.md — TYPE x ASSET extraction rules (load if file exists)` |
| 38-41 | items 4-7 | Renumber to 5-8 |
| 43 | "primary-pass.md is your complete working brief. Follow it start to finish. core-contract.md is reference for schema details." | "primary-pass.md is your working brief — follow it start to finish. If an intersection file was loaded at slot 4, it provides additional asset-specific extraction rules. core-contract.md is reference for schema details." |
| 47 | "After loading all 7 files" | "After loading all files listed above" |

---

## FILE 6: EDIT `.claude/agents/extraction-enrichment-agent.md`

| Line | Current | New |
|------|---------|-----|
| 26 | "it is your complete working brief" | "it is your working brief" |
| After 38 | (nothing) | INSERT: `4. .claude/skills/extract/types/{TYPE}/assets/{ASSET}-enrichment.md — TYPE x ASSET extraction rules (load if file exists)` |
| 39-42 | items 4-7 | Renumber to 5-8 |
| 44 | "enrichment-pass.md is your complete working brief. Follow it start to finish. core-contract.md is reference for schema details." | "enrichment-pass.md is your working brief — follow it start to finish. If an intersection file was loaded at slot 4, it provides additional asset-specific extraction rules. core-contract.md is reference for schema details." |
| 48 | "After loading all 7 files" | "After loading all files listed above" |
| 50 | "LOAD secondary content (e.g., Q&A for transcripts)" | "LOAD secondary content (per intersection file)" |

---

## FILE 7: EDIT `types/guidance/enrichment-pass.md` (~29 lines reworded)

All changes are vocabulary only. Zero workflow changes. The enrichment algorithm (6 steps) stays identical.

| Line(s) | Current | New |
|---------|---------|-----|
| 7 | "secondary content (Q&A for transcripts)" | "secondary content (per intersection file)" |
| 9 | "Discovery of Q&A-only items is co-equal with enrichment — management regularly reveals guidance in Q&A that never appears in prepared remarks." | "Discovery of secondary-only items is co-equal with enrichment — the secondary section often contains items not found in the primary section." |
| 27 | "These are the PR-extracted items written by the primary pass." | "These are the items written by the primary pass." |
| 33 | "Record `given_date` from existing items — all items share the same `conference_datetime`. Use this for any new Q&A-only items." | "Record `given_date` from existing items — all items from the same source share it. Use this for any new secondary-only items." |
| 35 | "**Prior-transcript baseline (query 7F)**: Load all labels previously extracted from this company's transcripts, with frequency and last-seen date. Used in the completeness check (Step 5)." | "**Prior-source baseline (query 7F)**: Load all labels previously extracted from this company's sources of this asset type, with frequency and last-seen date. Used in the completeness check (Step 5)." |
| 37 | "### STEP 3: LOAD SECONDARY CONTENT — Fetch Q&A" | "### STEP 3: LOAD SECONDARY CONTENT" |
| 39-41 | "Query 3F to get Q&A exchanges. If 3F returns empty, try 3C fallback (QuestionAnswer nodes — ~40 transcripts use `HAS_QA_SECTION` instead of `HAS_QA_EXCHANGE`).\n\nIf both return empty: Return early with `NO_QA_CONTENT`." | "Fetch secondary content using queries defined in your intersection file.\n\nIf no secondary content found: Return early with `NO_SECONDARY_CONTENT`." |
| 43 | "### STEP 4: Q&A ENRICHMENT — Process Each Exchange" | "### STEP 4: ENRICHMENT — Process Secondary Content" |
| 45 | "Process EACH Q&A exchange against the existing items from Step 2. For every exchange, produce a verdict:" | "Process each piece of secondary content against the existing items from Step 2. For each, produce a verdict:" |
| 51 | "Q&A adds detail to an existing item \| Update `qualitative`, `conditions`, `quote`, and/or numeric fields. Append `[Q&A]` detail in quote." | "Secondary content adds detail to an existing item \| Update `qualitative`, `conditions`, `quote`, and/or numeric fields. Append detail with quote prefix from intersection file." |
| 52 | "Q&A contains guidance not in any existing item \| Create new item with `[Q&A]` quote prefix. Apply metric decomposition..." | "Secondary content contains item not in any existing item \| Create new item with quote prefix from intersection file. Apply metric decomposition..." |
| 53 | "Exchange has no forward-looking content" | "Content has no forward-looking material" |
| 61 | "Load 7F baseline (all labels from prior transcripts, frequency + last-seen date)." | "Load 7F baseline (all labels from prior sources of this asset type, frequency + last-seen date)." |
| 63 | "For missing labels, re-scan Q&A exchanges for that metric." | "For missing labels, re-scan secondary content for that metric." |
| 65 | "found in Q&A, created" | "found in secondary content, created" |
| 72 | "Apply Q&A enrichments to specific fields." | "Apply secondary enrichments to specific fields." |
| 74 | "For new Q&A-only items" | "For new secondary-only items" |
| 80 | `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json` | `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json` |
| 98 | `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json` | `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json` |
| 101 | `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json` | `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json` |
| 106 | "## Q&A Analysis Log Format (MANDATORY)" | "## Secondary Content Analysis Log Format (MANDATORY)" |
| 108 | "You MUST produce a Q&A Analysis Log. Every entry MUST include a topic summary:" | "You MUST produce a Secondary Content Analysis Log. Format per intersection file. Every entry MUST include a verdict and topic summary:" |
| 111-115 | Q&A Analysis Log examples with analyst names | Generic format: `#{N} (source): VERDICT — topic summary` (see intersection file for source identifier) |
| 122 | "Existing items enriched: `[PR] original text... [Q&A] additional detail...`" | "Existing items enriched: use quote prefixes defined in your intersection file." |
| 123 | "New Q&A-only items: `[Q&A] guidance text...`" | "New secondary-only items: use secondary quote prefix from intersection file." |
| 126 | "`section` for enriched items becomes `CFO Prepared Remarks + Q&A` (or specific Q&A reference)." | "`section` for enriched items: see intersection file for section format." |
| 125 | "If Q&A gives more precise numbers than PR, update `low`/`mid`/`high` and change `derivation` if appropriate." | "If secondary content gives more precise numbers than primary, update `low`/`mid`/`high` and change `derivation` if appropriate." |
| 127 | "`source_refs`: array of QAExchange node IDs that contributed. Build each ID as `{SOURCE_ID}_qa__{sequence}`..." | "`source_refs`: see intersection file for source_ref format." |
| 155 | "every item written must include ALL fields from the 7E readback plus Q&A enrichments" | "every item written must include ALL fields from the 7E readback plus secondary enrichments" |
| 164 | "New Q&A-only items: {count}" | "New secondary-only items: {count}" |
| 166 | "Q&A exchanges analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})" | "Secondary units analyzed: {count} (enriched: {n}, new: {n}, no_guidance: {n})" |

**Lines that stay as-is** (already generic): 124 (merge richer info from both sources).

---

## FILE 8: EDIT `SKILL.md` (`.claude/skills/extract/SKILL.md`)

### Change 1: Remove Step 1 (dead code — sections check no longer used)

DELETE lines 9-14:
```
## Step 1: Check asset for secondary sections

Read `.claude/skills/extract/assets/{ASSET}.md` and find `## Asset Metadata` section. Check the `sections:` field.

- If sections contains more than one entry (e.g., `prepared_remarks, qa`) → asset has secondary sections
- If sections is just `full` → asset has no secondary sections
```

### Change 2: Rewrite enrichment gate (was Step 3, becomes Step 2)

Current (lines 30-32):
```
Run enrichment ONLY IF both conditions are true:
1. Asset has secondary sections (from Step 1)
2. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`
```

New:
```
Run enrichment ONLY IF both conditions are true:
1. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`
2. File exists: `.claude/skills/extract/types/{TYPE}/assets/{ASSET}-enrichment.md`
```

### Change 3: Result format (line 49)

| Current | New |
|---------|-----|
| `"new_qa_items": N` | `"new_secondary_items": N` |

### Change 4: Renumber steps

- Step 2 (Run primary) → Step 1
- Step 3 (Check enrichment) → Step 2
- Step 4 (Report results) → Step 3

---

## FILE 9: EDIT `types/guidance/guidance-queries.md`

### Change 1: Query 7E description (line 56)

| Current | New |
|---------|-----|
| "Used by `guidance-qa-enrich` to load Phase 1 items as base for Q&A enrichment." | "Used by enrichment agent to load primary pass items as base for secondary enrichment." |

### Change 2: Query 7F — full rework (lines 79-95)

Current:
```
### 7F. Prior-Transcript Guidance Baseline (Completeness Check)

Returns all labels this company has ever guided on via transcripts, with frequency
and recency. Used by `guidance-qa-enrich` to detect missing items after Q&A processing.

MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance),
      (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker}),
      (gu)-[:FROM_SOURCE]->(t:Transcript)
WHERE gu.given_date < $current_given_date
...

**Usage**: After Step 4 Q&A processing, compare current extraction labels against this
baseline. Any previously-guided label absent from the current set triggers a targeted
re-scan of Q&A exchanges for that metric.
```

New:
```
### 7F. Prior-Source Guidance Baseline (Completeness Check)

Returns all labels this company has ever guided on from this asset type, with frequency
and recency. Used by enrichment agent to detect missing items after secondary content processing.

MATCH (gu:GuidanceUpdate)-[:UPDATES]->(g:Guidance),
      (gu)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE gu.source_type = $source_type
  AND gu.given_date < $current_given_date
WITH g.label AS label,
     max(gu.given_date) AS last_seen,
     count(DISTINCT gu.given_date) AS frequency
RETURN label, last_seen, frequency
ORDER BY frequency DESC

**Usage**: After Step 4 enrichment processing, compare current extraction labels against
this baseline. Any previously-guided label absent from the current set triggers a targeted
re-scan of secondary content for that metric.
```

Uses `gu.source_type` (confirmed in core-contract.md L127) instead of `labels(s)` — because 8K/10Q/10K all use `Report` nodes, so label-based filtering would collapse them.

---

## FILE 10: EDIT `queries-common.md`

| Line | Current | New |
|------|---------|-----|
| 55 | "Not required for guidance extraction (guidance uses calendar-based GuidancePeriod nodes via `build_guidance_period_id()` instead)." | "Not required for all extraction types. Some types use calendar-based period nodes instead." |
| 112 | "For each guidance metric, pattern-match against this cache to set `xbrl_qname`." | "For each extracted metric, pattern-match against this cache to set `xbrl_qname`." |
| 206 | "Supplementary recall queries for finding guidance-related content across fulltext indexes." | "Supplementary recall queries for finding extractable content across fulltext indexes." |

Lines 208 ("Search Q&A Exchanges") and 306 ("3C if Q&A missing") are **kept as-is** — they're accurate descriptions of what those queries literally do (search QAExchange nodes, fallback to query 3C). Not pollution.

---

## Verification Checklist

### Content Integrity
- [ ] transcript.md: zero "guidance", "guidance source", "guidance priority", "forward guidance" references
- [ ] enrichment-pass.md: zero "Q&A", "transcript", "prepared remarks", "QAExchange", "conference_datetime" references
- [ ] guidance-queries.md 7F: no `Transcript` node label, uses `$source_type` parameter
- [ ] guidance-queries.md 7E: no `guidance-qa-enrich` or "Q&A enrichment" references
- [ ] queries-common.md: zero "guidance extraction", "guidance metric", "guidance-related" references
- [ ] SKILL.md: no sections check, gate uses file existence only, no `new_qa_items`

### Agent Shell Consistency
- [ ] Both shells: say "working brief" not "complete working brief"
- [ ] Both shells: mention intersection file at slot 4
- [ ] Both shells: say "all files listed above" not hardcoded number
- [ ] Enrichment shell L50: no transcript example

### Intersection Files
- [ ] transcript-primary.md has: scan scope (PR), speaker hierarchy, PR extraction steps, what-to-extract table, [PR] quote prefix, [Q&A] fallback prefix note
- [ ] transcript-enrichment.md has: scan scope (Q&A), speaker hierarchy, why Q&A matters, Q&A extraction steps, what-to-extract table, [Q&A] quote prefix, section format, secondary content fetch (3F/3C), quote prefixes ([PR]/[Q&A]), source_ref format, analysis log format

### Pass File Purity
- [ ] primary-pass.md: **UNCHANGED** — zero edits
- [ ] enrichment-pass.md: contains only generic workflow vocabulary ("secondary content", "intersection file")
- [ ] Both pass files: TYPE-level routing that mentions transcript (routing tables, parenthetical examples) is expected and stays — these are pass-workflow instructions, not asset extraction rules

### Boundary Rules
- [ ] A hypothetical "analyst-estimates" type could use transcript.md without seeing guidance rules
- [ ] A hypothetical 8-K enrichment would NOT see Q&A vocabulary in enrichment-pass.md
- [ ] SKILL.md would NOT auto-trigger enrichment for an asset without an intersection file

---

## Hard Gates

### Gate 1: Prompt-stream diff

Concatenate the files each agent reads in order (7 before the change, 8 after — slot 4 does not exist before) and diff them. Verify:

- All content present in the before stream is present in the after stream (zero content loss)
- Content that moved between files is identical (no accidental rewrites beyond planned text changes)

**Planned text changes** (any other diff in moved content = accidental):
1. transcript.md L3: "extraction rules" → "profile"
2. transcript.md L196: "guidance statement" → "extracted item"
3. transcript.md L226: "See core-contract.md S6/S7/S13" → "See your type's core-contract..."
4. transcript.md L238: "guidance became public" → "content became public"
5. transcript-queries.md L48: "scanned for guidance. See PROFILE_TRANSCRIPT.md" → "extractable content. See transcript.md"
6. transcript-primary.md scan scope: "Process all prepared remarks content..." (replaces removed L46)
7. transcript-enrichment.md scan scope: "Process all Q&A content..." (replaces removed L46)

**Expected additions** (not counted as text changes — new-file scaffolding):
- Intersection file titles, description lines, section headings
- Primary fallback note (1 sentence about Q&A fallback with [Q&A] prefix)
- Agent shell slot 4 line + wording updates
- Secondary content fetch/format sections in transcript-enrichment.md (absorbed from enrichment-pass.md)

**enrichment-pass.md vocabulary changes** (~29 lines): These change descriptions/comments but NOT the workflow. Gate 2 validates behavioral equivalence.

### Gate 2: Dry-run regression

Run the same extraction on known transcripts before AND after. Use `--force` to re-process. Wait for async worker completion. If worker runs in K8s, retrieve `/tmp` files via `kubectl cp` or `kubectl exec`.

```bash
# Before change
python3 scripts/trigger-extract.py --source-id AAPL_2025-07-31T17.00 --type guidance --mode dry_run --force
# Wait for worker, save /tmp/gu_AAPL_*.json and dry-run output

# After change
python3 scripts/trigger-extract.py --source-id AAPL_2025-07-31T17.00 --type guidance --mode dry_run --force
# Wait for worker. Diff JSON payload field-for-field. Every field must match exactly.
```

**Test cases:**
- Normal PR+Q&A transcript: `AAPL_2025-07-31T17.00`
- 3C fallback: `MATCH (t:Transcript)-[:HAS_QA_SECTION]->(qa:QuestionAnswer) RETURN t.id LIMIT 3`
- QAExchange_only (no PR): `UBER_2026-02-04T08.00` — **Expected diff**: primary fallback may show minor quote prefix differences since agent now has explicit [Q&A] fallback rule. Key check: items ARE produced (not zero).
- Implicit basis switch: `MATCH ... WHERE size(bases) = 2 RETURN tid LIMIT 3`

---

## Rollback Plan

```
git revert <commit>   # one command undoes all 10 files
```

Files reverted:
1. DELETE types/guidance/assets/transcript-primary.md
2. DELETE types/guidance/assets/transcript-enrichment.md
3. RESTORE transcript.md (84 lines back)
4. RESTORE transcript-queries.md (1 line back)
5. RESTORE extraction-primary-agent.md (slot 4 removed)
6. RESTORE extraction-enrichment-agent.md (slot 4 removed)
7. RESTORE enrichment-pass.md (Q&A vocabulary back)
8. RESTORE SKILL.md (sections gate back)
9. RESTORE guidance-queries.md (7F/7E back)
10. RESTORE queries-common.md (guidance comments back)

---

## Git Workflow

```
1. Ensure pre-fix state is committed (if uncommitted changes exist, commit or stash them first)
2. Make all changes in a SINGLE commit:
   - Create types/guidance/assets/transcript-primary.md (NEW)
   - Create types/guidance/assets/transcript-enrichment.md (NEW)
   - Edit extraction-primary-agent.md (add slot 4 + wording)
   - Edit extraction-enrichment-agent.md (add slot 4 + wording)
   - Edit transcript.md (remove 84 lines + 4 rewrites)
   - Edit transcript-queries.md (1 line rewrite)
   - Edit enrichment-pass.md (~29 lines genericized)
   - Edit SKILL.md (remove Step 1, rewrite gate, fix result field)
   - Edit guidance-queries.md (7F parameterized + 7E description)
   - Edit queries-common.md (3 comment cleanups)
   Commit message: "Full pollution fix: TYPE x ASSET x PASS separation with generic enrichment"
3. Run Gate 1 (prompt-stream diff) — verify content preservation
4. Run Gate 2 (dry-run regression) — verify extraction output matches
5. If regression → git revert <commit> (one command undoes everything)
```

---

## What This Achieves

| Axis | Before | After |
|------|--------|-------|
| transcript.md (ASSET) | 77+ guidance-specific lines | Pure asset profile, zero guidance content |
| enrichment-pass.md (TYPE+PASS) | ~29 lines of transcript/Q&A vocabulary | Pure generic workflow, zero asset content |
| guidance-queries.md (TYPE) | 7F hardcoded to Transcript nodes | Parameterized by source_type, works for any asset |
| queries-common.md (SHARED) | 3 guidance-flavored comments | Generic extraction vocabulary |
| SKILL.md (ORCHESTRATOR) | Gate uses sections metadata | Gate uses file existence (explicit opt-in) |
| Agent shells | "complete working brief", hardcoded "7 files" | "working brief" + slot 4 mention, dynamic file count |

**Adding a new extraction type** (e.g., analyst-estimates): Create `types/analyst-estimates/` directory with core-contract, primary-pass, queries. Zero edits to existing files.

**Adding enrichment for a new asset** (e.g., 10-K with MD&A + Financial Statements): Create `types/guidance/assets/10k-enrichment.md`. The generic enrichment-pass.md works unchanged. SKILL.md gate auto-activates.

**Adding a new asset type**: Create `assets/{asset}.md` + `assets/{asset}-queries.md`. Zero edits to existing files.

---

## Extending to Other Assets

The transcript-specific classifications (which block is generic, which is guidance) don't transfer to 8K/10Q/news — do fresh audits of those files. What you need:

1. **The 3 boundary rules** — in this plan's verification checklist ("Boundary Rules" section)
2. **The intersection file pattern** — this plan IS the template: create `types/{TYPE}/assets/{ASSET}-{pass}.md`, add slot 4, gate on file existence
3. **The verification approach** — Gates 1 & 2 are reusable as-is

Once implemented, the file structure itself documents the pattern. Anyone looking at `types/guidance/assets/transcript-primary.md` sees exactly how to create `types/guidance/assets/8k-primary.md`.
