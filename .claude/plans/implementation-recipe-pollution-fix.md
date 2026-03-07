# Implementation Recipe: TYPE × ASSET × PASS Separation

**Source Plan**: `.claude/plans/extraction-pipeline/transcript-guidancePollutionFix.md`
**Status**: VALIDATED — all 10 files successfully implemented for transcript
**Reusability**: FULLY REUSABLE for 8k, 10q, news with zero modifications to pattern
**Effort**: ~2-3 hours per asset type (file reading + copy-paste template application + verification)

---

## Overview

This recipe extracts the **validated implementation pattern** used to eliminate guidance/Q&A contamination from the transcript asset. It can be applied verbatim to any other asset type needing the same fix.

**Problem solved**: Generic infrastructure (enrichment-pass.md, guidance-queries.md) mixed with asset-specific content (Q&A vocabulary, interview extraction rules).

**Pattern**: Move asset-specific extraction rules into **intersection files** (`types/{TYPE}/assets/{ASSET}-{pass}.md`), leaving infrastructure purely generic. Result: zero file edits when adding a new asset type.

---

## 1. Intersection File Pattern

### Purpose
**Intersection files** ("assets-within-a-type") decouple:
- **TYPE** — the extraction method (guidance, analyst-estimates, sentiment)
- **ASSET** — the data source (transcript, 8k, 10q, news)
- **PASS** — the phase (primary, enrichment)

### File Locations
```
.claude/skills/extract/types/{TYPE}/assets/{ASSET}-{PASS}.md
```

**Primary pass file** (slot 4, primary agent):
```
.claude/skills/extract/types/guidance/assets/transcript-primary.md
```

**Enrichment pass file** (slot 4, enrichment agent):
```
.claude/skills/extract/types/guidance/assets/transcript-enrichment.md
```

### Structure Template — Primary Pass (~38 lines, transcript example)

```markdown
# Guidance x {ASSET} — Primary Pass

Rules for extracting guidance from {ASSET} primary section. Loaded at slot 4 by the primary agent.

## Scan Scope — {ASSET}

[ASSET-SPECIFIC: describe the primary/main section of this source]
[ASSET-SPECIFIC: identify richness/priority vs fallback]

When falling back to secondary data (primary empty/truncated per primary-pass.md),
apply your quality filters from the pass brief. Use quote prefix `[FALLBACK]` for any items
extracted from secondary fallback data. The enrichment agent handles specialized secondary extraction.

## Speaker Hierarchy (Guidance Priority)

[ASSET-SPECIFIC: table showing priority order]
[COPY FROM ASSET PROFILE if exists, or define fresh]

## Extraction Steps — {PRIMARY_SECTION}

[ASSET-SPECIFIC: 1-5 numbered steps for scanning primary section]

## What to Extract from {PRIMARY_SECTION}

[ASSET-SPECIFIC: table of signals, examples, extract/skip decisions]

## Quote Prefix — {PRIMARY_SECTION}

All guidance extracted from primary section MUST use quote prefix: `[PREFIX]`

Example: `[PREFIX] guidance text from source...`
```

**Key variance points**:
- `## Scan Scope` — adapt to the source (e.g., "prepared remarks" → "10-K MD&A")
- `## Speaker Hierarchy` or equivalent section ID logic
- `## Extraction Steps` — numbered workflow specific to this asset
- `## What to Extract` — signals/examples relevant to this source type
- Quote prefix — e.g., `[PR]` for prepared remarks, `[MD&A]` for 10-K, `[LEC]` for earnings call

### Structure Template — Enrichment Pass (~72 lines, transcript example)

```markdown
# Guidance x {ASSET} — Enrichment Pass

Rules for enriching/discovering guidance from {ASSET} secondary section.
Loaded at slot 4 by the enrichment agent.

## Scan Scope — {ASSET}

Process all secondary section content from {ASSET}. Do not skip any exchange/section.
[ASSET-SPECIFIC: why secondary is valuable]

## Speaker Hierarchy (Guidance Priority)

[COPY FROM PRIMARY FILE — identical]

## Why {SECONDARY_SECTION} Matters

[ASSET-SPECIFIC: 5-7 bullet points on secondary section richness]

## {SECONDARY_SECTION} Extraction Steps

[ASSET-SPECIFIC: 1-4 numbered steps]

## What to Extract from {SECONDARY_SECTION}

[ASSET-SPECIFIC: table of signals, examples, extract/skip decisions]

## {SECONDARY_SECTION} Quote Prefix

All guidance extracted from secondary section MUST use quote prefix: `[SECONDARY_PREFIX]`

Example: `[SECONDARY_PREFIX] guidance text...`

## Section Field Format

For secondary guidance, the `section` field should [ASSET-SPECIFIC FORMAT]

## Secondary Content Fetch

[ASSET-SPECIFIC: which query to use (e.g., 3F for Q&A)]
[ASSET-SPECIFIC: fallback query if primary empty (e.g., 3C)]
[ASSET-SPECIFIC: what constitutes "one piece" of secondary content]
If no secondary content found, return early with NO_SECONDARY_CONTENT.

## Quote Prefixes

- Primary content: `[PRIMARY_PREFIX]`
- Secondary content: `[SECONDARY_PREFIX]`
- Enriched items: `[PRIMARY_PREFIX] original text... [SECONDARY_PREFIX] additional detail...`

## Section Format

- Enriched items: `[ASSET-SPECIFIC SECTION NAMING]`
- source_refs: [ASSET-SPECIFIC FORMAT for referencing secondary units]

## Analysis Log Format

[ASSET-SPECIFIC: how to identify/name secondary content sources]

```
#1 (identifier): ENRICHES {metric} — reason
#2 (identifier): NO GUIDANCE — reason
#3 (identifier): NEW ITEM — reason
```
```

**Key variance points** (same as primary):
- `## Scan Scope` — describe secondary section
- `## Why X Matters` — explain secondary richness
- `## What to Extract` — signals specific to secondary
- Quote prefixes — match primary file convention
- `## Secondary Content Fetch` — which queries, which fallbacks
- `## Analysis Log Format` — how to identify sources (analyst names, exchange numbers, section references, etc.)

### Actual Implementation: Transcript Files

**Primary** (`.claude/skills/extract/types/guidance/assets/transcript-primary.md`):
- Scan Scope: "Process all **prepared remarks** content from the transcript"
- Speaker Hierarchy: 6-row table (CFO PR, CFO Q&A, CEO PR, CEO Q&A, others, skip operator)
- Extraction Steps: 5 steps identifying speaker sections, focusing CFO, skipping operator
- What to Extract: 6 signals (explicit range, point, YoY, corporate announcement, qualitative, past results)
- Quote Prefix: `[PR]` for prepared remarks, with note about `[Q&A]` fallback

**Enrichment** (`.claude/skills/extract/types/guidance/assets/transcript-enrichment.md`):
- Scan Scope: "Process all **Q&A content** from the transcript"
- Speaker Hierarchy: Same 6-row table (already in transcript)
- Why Q&A Matters: 7 bullets on analyst probing, segment breakdowns, GAAP vs non-GAAP, "comfortable" signals, conditional guidance, sensitivity bounds
- Q&A Extraction Steps: 4 steps (process every exchange, focus management, look for CFO, capture analyst name)
- What to Extract: 8 signals (specific numbers, consensus comfort, segment detail, conditional, clarification, capital announcement, analyst estimate, sentiment)
- Quote Prefix: `[Q&A]`
- Section Format: `Q&A #1`, `Q&A (analyst name)`, or both
- Secondary Content Fetch: "Query 3F for Q&A exchanges. If empty, try 3C fallback (QuestionAnswer nodes). If both empty, return NO_SECONDARY_CONTENT."
- Section Format (enriched items): `CFO Prepared Remarks + Q&A` or specific Q&A reference
- source_refs format: `{SOURCE_ID}_qa__{sequence}` (e.g., `AAPL_2023-11-03T17.00_qa__3`)
- Analysis Log Format: `#1 (analyst name): ENRICHES Revenue(iPhone) — CFO discusses supply-demand balance`

---

## 2. Asset Profile Cleanup Pattern

### Read the Current Profile
Example: `.claude/skills/extract/assets/transcript.md`

### Identify Content to Remove
Lines that are **TYPE-specific, not ASSET-specific**. For transcript:
- Lines 44-59: scan scope + speaker hierarchy (16 lines)
- Lines 69-93: prepared remarks extraction steps + table + quote prefix (25 lines)
- Lines 106-148: Q&A extraction everything (43 lines)

**Total to remove**: 84 lines

### Identify Content to Keep
Lines that describe **how the asset arrives, not how to extract from it**:
- Asset metadata (sections, label, neo4j_label)
- Data structure documentation (Node types, fields, JSON formats)
- Duplicate resolution strategy
- Empty content handling (which queries, fallbacks, error codes)
- Calendar-to-fiscal mapping
- Period identification logic
- Basis traps and special cases
- Given date resolution
- Source key logic

For transcript, keep ~161 lines (data structure, fallback details, duplicate resolution, empty handling).

### Make 4 Targeted Rewrites
Change **guidance-flavored** language to **generic extraction** language:

| Line | Context | Current | New |
|------|---------|---------|-----|
| 3 | Asset heading | "extraction rules" | "profile" |
| 196 | Duplicate resolution | "guidance statement" | "extracted item" |
| 226 | Cross-reference | "See core-contract.md S6 (Basis Rules), S7 (Segment Rules), S13 (Quality Filters)." | "See your type's core-contract for basis, segment, and quality filter rules." |
| 238 | Empty handling | "guidance became public" | "content became public" |

**Pattern**: Search for type-specific keywords in your asset profile:
- "guidance", "forward-looking", "guidance source", "guidance priority"
- Type-specific vocabulary: "prepared remarks", "Q&A", "conference call", "analyst question"
- "transcript", "10-K", "8-K", etc. (asset names)

Remove those lines or genericize them.

### One-File Reference Implementation
See: `.claude/skills/extract/assets/transcript.md` (245 → 161 lines)

---

## 3. Agent Shell Changes

### Where They Live
```
.claude/agents/extraction-primary-agent.md
.claude/agents/extraction-enrichment-agent.md
```

### Change 1: Slot 4 Line (Add)

**Location**: After step 3 in the file list.

**Primary agent** (after line 37 in original, becomes line 38):
```
4. .claude/skills/extract/types/{TYPE}/assets/{ASSET}-primary.md — TYPE x ASSET extraction rules (load if file exists)
```

**Enrichment agent** (after line 38 in original, becomes line 39):
```
4. .claude/skills/extract/types/{TYPE}/assets/{ASSET}-enrichment.md — TYPE x ASSET extraction rules (load if file exists)
```

### Change 2: Wording — "Complete" → "Working"

**Location**: Line ~25-26 (primary), line ~26-27 (enrichment)

Old:
```
it is your complete working brief
```

New:
```
it is your working brief
```

### Change 3: Intersection File Mention in Guidance

**Location**: Line ~43 (primary), line ~44 (enrichment)

Old:
```
primary-pass.md is your complete working brief. Follow it start to finish. core-contract.md is reference for schema details.
```

New:
```
primary-pass.md is your working brief — follow it start to finish. If an intersection file was loaded at slot 4, it provides additional asset-specific extraction rules. core-contract.md is reference for schema details.
```

(Same pattern for enrichment-pass.md)

### Change 4: Dynamic File Count

**Location**: Line ~47 (primary), line ~48 (enrichment)

Old:
```
After loading all 7 files, execute the pipeline...
```

New:
```
After loading all files listed above, execute the pipeline...
```

### Change 5: Secondary Content Loading (Enrichment Only)

**Location**: Line ~50 (enrichment agent)

Old:
```
LOAD secondary content (e.g., Q&A for transcripts)
```

New:
```
LOAD secondary content (per intersection file)
```

### Verification
After changes:
- Both shells mention slot 4 + file-exists logic
- Both say "working brief" (not "complete")
- Both reference "all files listed above" (not hardcoded 7)
- Enrichment shell doesn't mention "transcript" or "Q&A" specifically

**Reference implementations**:
- Primary: `.claude/agents/extraction-primary-agent.md` (lines 25, 38, 44, 48)
- Enrichment: `.claude/agents/extraction-enrichment-agent.md` (lines 26, 39, 45, 48, 51)

---

## 4. Enrichment Pass Genericization

### File Location
`.claude/skills/extract/types/guidance/enrichment-pass.md`

### Pattern
Replace **asset-specific vocabulary** with **generic terms**. The workflow stays identical; only descriptions change.

### Vocabulary Mappings (Transcript → Generic)

| Asset-Specific | Generic |
|---|---|
| Q&A | secondary content |
| prepared remarks | primary content |
| QAExchange | secondary content unit |
| "Q&A exchanges" | "secondary content items" |
| "Q&A-only items" | "secondary-only items" |
| "transcript" (in process context) | deleted or "this source" |
| "analyst name" | "source identifier" |
| "QAExchange node ID" | "secondary content reference" |

### Lines Changed (29 total, grouped by type)

**Content descriptions** (lines 7, 9):
- Line 7: "secondary content (Q&A for transcripts)" → "secondary content (per intersection file)"
- Line 9: "Discovery of Q&A-only items..." → "Discovery of secondary-only items..."

**Secondary loading** (lines 37-41):
- Line 37: "### STEP 3: LOAD SECONDARY CONTENT — Fetch Q&A" → "### STEP 3: LOAD SECONDARY CONTENT"
- Lines 39-41: Rewrite from query-specific to "using queries defined in your intersection file"

**Processing steps** (lines 43-53):
- Line 43: "### STEP 4: Q&A ENRICHMENT..." → "### STEP 4: ENRICHMENT..."
- Line 45: "Process EACH Q&A exchange" → "Process each piece of secondary content"
- Line 51: "Q&A adds detail" → "Secondary content adds detail" + "Append `[Q&A]`" → "Append detail with quote prefix from intersection file"
- Line 52: "Q&A contains guidance" → "Secondary content contains item" + "with `[Q&A]` quote prefix" → "with quote prefix from intersection file"
- Line 53: "Exchange has no" → "Content has no"

**Completeness check** (lines 61-65):
- Line 61: "all labels from prior transcripts" → "all labels from prior sources of this asset type"
- Line 63: "re-scan Q&A exchanges" → "re-scan secondary content"
- Line 65: "found in Q&A, created" → "found in secondary content, created"

**Apply enrichments** (lines 72-74):
- Line 72: "Apply Q&A enrichments" → "Apply secondary enrichments"
- Line 74: "For new Q&A-only items" → "For new secondary-only items"

**Output files** (lines 80, 98, 101):
- Old: `/tmp/gu_{TICKER}_{SOURCE_ID}_qa.json`
- New: `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json`

**Analysis log** (lines 106, 108, 111-115, 122-123, 126-127):
- Line 106: "## Q&A Analysis Log Format" → "## Secondary Content Analysis Log Format"
- Line 108: "You MUST produce a Q&A Analysis Log" → "You MUST produce a Secondary Content Analysis Log"
- Lines 111-115: Rewrite examples from Q&A-specific to generic `#{N} (source): VERDICT — topic summary`
- Line 122: Existing items: "use quote prefixes defined in your intersection file"
- Line 123: New items: "use secondary quote prefix from intersection file"

**Section handling** (lines 124-127):
- Line 126: "`section` for enriched items becomes `CFO Prepared Remarks + Q&A`..." → "see intersection file for section format"
- Line 125: "If Q&A gives more precise" → "If secondary content gives more precise"
- Line 127: "`source_refs`: array of QAExchange node IDs..." → "`source_refs`: see intersection file for source_ref format"

**Summaries** (lines 155, 164, 166):
- Line 155: "plus Q&A enrichments" → "plus secondary enrichments"
- Line 164: "New Q&A-only items: {count}" → "New secondary-only items: {count}"
- Line 166: "Q&A exchanges analyzed: {count}..." → "Secondary units analyzed: {count}..."

### What Stays Unchanged
- The 6-step workflow (fetch, load existing, load secondary, process, check completeness, validate+write)
- All logic (ENRICHES/NEW/NO_GUIDANCE verdicts, period routing, concept cache matching)
- Lines 124 (merge richer info from both sources) — already generic

### Reference
See: `.claude/skills/extract/types/guidance/enrichment-pass.md` (all ~29 lines successfully genericized)

---

## 5. SKILL.md Orchestrator Gate

### File Location
`.claude/skills/extract/SKILL.md`

### Change 1: Remove Dead Code

**Delete lines 9-14** (old Step 1):
```
## Step 1: Check asset for secondary sections

Read `.claude/skills/extract/assets/{ASSET}.md` and find `## Asset Metadata` section. Check the `sections:` field.

- If sections contains more than one entry (e.g., `prepared_remarks, qa`) → asset has secondary sections
- If sections is just `full` → asset has no secondary sections
```

**Reason**: Intersection files now gate enrichment — sections metadata no longer used.

### Change 2: Rewrite Enrichment Gate

**Old (lines 30-32, "Step 3")**:
```
Run enrichment ONLY IF both conditions are true:
1. Asset has secondary sections (from Step 1)
2. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`
```

**New (Step 2, after Step 1 deletion)**:
```
Run enrichment ONLY IF both conditions are true:
1. File exists: `.claude/skills/extract/types/{TYPE}/enrichment-pass.md`
2. File exists: `.claude/skills/extract/types/{TYPE}/assets/{ASSET}-enrichment.md`
```

**Logic**:
- Gate is now **explicit file-existence check** (no metadata parsing)
- Both files must exist: enrichment pass (type-level) + intersection file (asset-level)
- If either missing: no enrichment, skip to reporting

### Change 3: Result Field Rename

**Old (line 49)**:
```json
"new_qa_items": N
```

**New**:
```json
"new_secondary_items": N
```

**Reason**: Generic extraction — not all types/assets use "Q&A".

### Change 4: Renumber Steps

After deletion, steps shift:
- Old Step 2 (Run primary) → Step 1
- Old Step 3 (Check enrichment) → Step 2
- Old Step 4 (Report results) → Step 3

### Reference
See: `.claude/skills/extract/SKILL.md` (gates on lines 24-25)

---

## 6. Query Parameterization (7E + 7F)

### File Location
`.claude/skills/extract/types/guidance/guidance-queries.md`

### Change 1: Query 7E Description

**Line 56 (old line numbers)**:

Old:
```
Used by `guidance-qa-enrich` to load Phase 1 items as base for Q&A enrichment.
```

New:
```
Used by enrichment agent to load primary pass items as base for secondary enrichment.
```

**Reason**: Remove references to transcript-specific agent names and Q&A vocabulary.

### Change 2: Query 7F — Full Rework

This query loads the **prior baseline** for completeness checking. The key insight:

**Old approach** (hardcoded to Transcript nodes):
- Join via `(gu)-[:FROM_SOURCE]->(t:Transcript)`
- Only works for transcripts
- Transcript node label varies by source type

**New approach** (parameterized by source_type):
- Use `gu.source_type = $source_type` filter
- Works for any asset type
- No node label assumptions

**Old query** (lines 79-95):
```cypher
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

**New query**:
```cypher
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

**Key changes**:
- Title: "Prior-Transcript" → "Prior-Source"
- Join: remove `(gu)-[:FROM_SOURCE]->(t:Transcript)` entirely
- Filter: add `gu.source_type = $source_type`
- Description: "via transcripts" → "from this asset type", "Q&A processing" → "secondary content processing"
- Usage note: "Q&A exchanges" → "secondary content"

**Rationale**: `source_type` is confirmed in core-contract.md as the canonical differentiation. Works for all asset types: transcript (source_type=transcript), 8-K (8k), 10-Q (10q), news (news), etc.

### Reference
See: `.claude/skills/extract/types/guidance/guidance-queries.md` (7E at line 56, 7F at lines 79-94)

---

## 7. Shared Infrastructure Cleanup (queries-common.md)

### File Location
`.claude/skills/extract/queries-common.md`

### Changes (3 lines, comment-only)

| Line | Context | Current | New |
|------|---------|---------|-----|
| 55 | XBRL period comment | "Not required for guidance extraction (guidance uses calendar-based GuidancePeriod nodes via `build_guidance_period_id()` instead)." | "Not required for all extraction types. Some types use calendar-based period nodes instead." |
| 112 | Concept cache usage | "For each guidance metric, pattern-match against this cache to set `xbrl_qname`." | "For each extracted metric, pattern-match against this cache to set `xbrl_qname`." |
| 206 | Recall queries purpose | "Supplementary recall queries for finding guidance-related content across fulltext indexes." | "Supplementary recall queries for finding extractable content across fulltext indexes." |

### Lines to Keep As-Is
- Line 208: "Search Q&A Exchanges" — accurate literal description, not pollution
- Line 306: "3C if Q&A missing" — accurate literal query name, not pollution

**Reason**: These describe what the queries literally do, not how guidance uses them. Not contamination.

### Reference
See: `.claude/skills/extract/queries-common.md` (lines 55, 112, 206)

---

## 8. Verification Checklist + Hard Gates

### Pre-Implementation Checks
- [ ] Plan document read in full
- [ ] All 10 actual files exist and match plan specs
- [ ] Understand the 6 sections above (intersection pattern, asset cleanup, agents, enrichment pass, SKILL gate, queries)

### Content Purity Checks (After Implementation)

**Asset profile cleanup**:
- [ ] Asset profile has zero "guidance", "forward-looking", "guidance source", "guidance priority" references
- [ ] Asset profile is purely about data structure: arriving node types, fields, formats, fallbacks
- [ ] Cross-references genericized: "your type's core-contract" instead of hardcoded

**Enrichment pass genericization**:
- [ ] Zero "Q&A", "transcript", "prepared remarks", "QAExchange", "conference_datetime" references
- [ ] All secondary/primary vocabulary used instead
- [ ] Lines changed: only description/comment updates, zero workflow logic changes
- [ ] Handling references point to "intersection file" instead of asset-specific detail

**Query parameterization**:
- [ ] 7F uses `gu.source_type = $source_type`, NOT node labels like `Transcript`
- [ ] 7E description mentions "enrichment agent", not "guidance-qa-enrich"
- [ ] No hardcoded asset references in query logic

**SKILL.md gate**:
- [ ] No sections check (Step 1 deleted)
- [ ] Gate uses file existence only: `enrichment-pass.md` AND `{ASSET}-enrichment.md`
- [ ] Result field: `new_secondary_items` not `new_qa_items`
- [ ] Steps renumbered: 1 (primary), 2 (enrichment), 3 (results)

**Agent shells**:
- [ ] Both shells: "working brief" not "complete working brief"
- [ ] Both shells: mention slot 4 intersection file existence check
- [ ] Both shells: "all files listed above" not hardcoded "7 files"
- [ ] Enrichment shell: no "Q&A for transcripts" example (says "per intersection file")

**Intersection files**:
- [ ] Primary file has: scan scope, speaker/section hierarchy, extraction steps, what-to-extract table, quote prefix, fallback note
- [ ] Enrichment file has: scan scope, hierarchy, why-secondary-matters, extraction steps, what-to-extract table, quote prefix, section format, secondary fetch queries, source_ref format, analysis log format
- [ ] Both follow template structure (same sections, similar formatting)

### Hard Gate 1: Prompt-Stream Diff

**Goal**: Verify zero content loss, only planned text changes.

**Process**:
1. Concatenate files read by agents in order (7 files before, 8 files after)
2. Diff the concatenations
3. Verify all original content is present (only added slot 4)
4. Verify moved content is identical except planned text changes

**Planned text changes** (any other diff = bug):
1. transcript.md L3: "extraction rules" → "profile"
2. transcript.md L196: "guidance statement" → "extracted item"
3. transcript.md L226: "See core-contract.md S6/S7/S13" → "See your type's core-contract..."
4. transcript.md L238: "guidance became public" → "content became public"
5. transcript-queries.md L48: "scanned for guidance. See PROFILE_TRANSCRIPT.md" → "extractable content. See transcript.md"

**Expected additions** (not counted as diffs — new-file content):
- Intersection file titles, descriptions, section headings
- Primary fallback note (1 sentence about secondary fallback)
- Agent slot 4 line + wording updates
- Secondary content fetch/format sections in enrichment file

### Hard Gate 2: Dry-Run Regression

**Goal**: Verify extraction output is identical before/after.

**Setup**:
```bash
# Before implementation
python3 scripts/trigger-extract.py --source-id AAPL_2025-07-31T17.00 --type guidance --force

# Wait for worker completion
# Save /tmp/gu_AAPL_*.json and dry-run output

# Implement changes (create intersection files, edit 8 files)

# After implementation
python3 scripts/trigger-extract.py --source-id AAPL_2025-07-31T17.00 --type guidance --force

# Wait for worker completion
# Diff JSON payload field-by-field
```

**Test cases**:
1. **Normal PR+secondary** (e.g., `AAPL_2025-07-31T17.00`):
   Expected: identical JSON output

2. **Secondary fallback** (e.g., 40 transcripts with `HAS_QA_SECTION` instead of `HAS_QA_EXCHANGE`):
   Expected: identical JSON output

3. **Secondary only, no primary** (e.g., `UBER_2026-02-04T08.00`):
   Expected: items produced (not zero). Fallback prefix may differ slightly (agent now has explicit rule). Key: items ARE extracted.

4. **Implicit basis switch** (assets with 2+ bases):
   Expected: identical JSON output

**Verification**: Every field matches exactly. If not, investigate why (likely unintended text change).

---

## 9. Rollback Plan

**Single command undoes all changes**:
```bash
git revert <commit_hash>
```

**What's reverted**:
1. DELETE types/guidance/assets/{ASSET}-primary.md
2. DELETE types/guidance/assets/{ASSET}-enrichment.md
3. RESTORE assets/{ASSET}.md (84 lines back + 4 rewrites undone)
4. RESTORE assets/{ASSET}-queries.md (1 line back)
5. RESTORE .claude/agents/extraction-primary-agent.md (slot 4 removed)
6. RESTORE .claude/agents/extraction-enrichment-agent.md (slot 4 removed)
7. RESTORE types/guidance/enrichment-pass.md (secondary vocabulary → Q&A)
8. RESTORE SKILL.md (sections gate back)
9. RESTORE types/guidance/guidance-queries.md (7F/7E back)
10. RESTORE queries-common.md (guidance comments back)

**Single atomic operation**: All 10 changes commit together, all revert together.

---

## 10. Reapplication to Other Assets (8K, News, 10Q)

### Step-by-Step for One New Asset (e.g., 8K)

1. **Read the asset profile** (`.claude/skills/extract/assets/8k.md`):
   - Identify guidance-specific sections (scan scope, extraction steps, vocabulary)
   - Mark lines to remove or rewrite (follow transcript.md pattern)
   - Plan the 4 rewrite lines (like transcript.md did)

2. **Read/create intersection files**:
   - Template from transcript-primary.md and transcript-enrichment.md
   - Replace "prepared remarks" with "Item 1" (8-K structure) or equivalent
   - Replace "Q&A" with whatever secondary section exists for 8-K (some 8-Ks have exhibits, some don't)
   - Replace speaker hierarchy with section hierarchy if applicable
   - Adapt extraction signals and examples to 8-K vocabulary

3. **Verify agent shells don't change** (they already support 8K via slot 4)

4. **Verify enrichment-pass.md doesn't change** (already generic)

5. **Verify SKILL.md gate works** (gate checks file existence, works for any asset)

6. **Verify queries don't change** (7F already parameterized by source_type)

7. **Run purity checks** (content checklist from section 8)

8. **Run regression tests** (dry-run before/after on known 8-Ks)

### Summary
**Files touched for a new asset**:
- CREATE: 2 intersection files (primary + enrichment)
- EDIT: asset profile + asset-queries (cleanup 2 files)
- NO CHANGE: agent shells, enrichment-pass, SKILL, queries

**Total**: ~4 files. Single commit. Single revert.

### Special Cases

**Asset with NO secondary section** (e.g., news-only headlines, no enrichment):
- Still create intersection files (as documentation/template)
- Don't create enrichment intersection file if no enrichment happens
- SKILL gate naturally skips enrichment if enrichment file missing

**Asset with multiple secondary types** (e.g., 10-K with both MD&A segments AND financial statements):
- Enrichment intersection file documents all secondary types
- Secondary fetch section lists all queries (fallback chain)
- Analysis log format identifies which secondary type each item came from

---

## Appendix: File Locations Reference

### Core Files (No Change)
```
.claude/skills/extract/types/guidance/primary-pass.md          (UNCHANGED)
.claude/skills/extract/types/guidance/core-contract.md         (UNCHANGED)
.claude/skills/extract/queries-common.md                        (3 comment lines only)
```

### Template Files (Reference for New Assets)
```
.claude/skills/extract/types/guidance/assets/transcript-primary.md        (TEMPLATE)
.claude/skills/extract/types/guidance/assets/transcript-enrichment.md     (TEMPLATE)
```

### Asset Files (Edit for New Assets)
```
.claude/skills/extract/assets/{ASSET}.md                  (remove ~84 lines + 4 rewrites)
.claude/skills/extract/assets/{ASSET}-queries.md         (minor reference updates if needed)
```

### Orchestration (No Change for New Assets)
```
.claude/skills/extract/SKILL.md                            (gates work for any asset)
.claude/agents/extraction-primary-agent.md                (slot 4 already in place)
.claude/agents/extraction-enrichment-agent.md             (slot 4 already in place)
```

### Type-Level Infrastructure (Parameterized for Any Asset)
```
.claude/skills/extract/types/guidance/enrichment-pass.md      (already generic, no change)
.claude/skills/extract/types/guidance/guidance-queries.md     (7F/7E already parameterized)
```

---

## Summary: The 3-Step Recipe

### For Each New Asset (8K, News, 10Q):

1. **Create 2 intersection files** (~110 lines total):
   - `types/guidance/assets/{ASSET}-primary.md` (~38 lines)
   - `types/guidance/assets/{ASSET}-enrichment.md` (~72 lines)
   - Use transcript files as template; replace asset-specific vocabulary

2. **Edit asset profile + queries** (~2 files, ~90 lines):
   - Remove extraction rules from `.assets/{ASSET}.md` (~84 lines)
   - Rewrite 4 lines to genericize language
   - Update reference lines in `assets/{ASSET}-queries.md` if present

3. **Verify purity + test** (~3 hours):
   - Run purity checklist (section 8)
   - Run dry-run regression (section 8)
   - Single commit, ready to ship

**No other files change**. The infrastructure (SKILL, agents, enrichment-pass, queries) is already generic — it was cleaned in the transcript implementation.

