# Total Contagion Fix — Extraction Pipeline

Eliminate ALL prompt-layer contamination across the extraction pipeline. Four categories by scope: A (common files), B (type-level files), C (cross-type), E (asset profiles).

**Prerequisite**: Land the 10-K asset split first (`virtual-splashing-treehouse.md`). This plan assumes `10k` is already a first-class asset with its own `10k.md`, `10k-queries.md`, and the `SOURCE_TYPE` parameter is removed.

**Zero behavioral regression guarantee**: For every current TYPE×ASSET×PASS combination, the agent's concatenated prompt (slots 1-8) contains identical content before and after. Content removed from higher-scope files is relocated to lower-scope files the same agent already loads.

**Agent load order (8 slots)**:
1. `types/{TYPE}/core-contract.md` — type-level schema reference
2. `types/{TYPE}/primary-pass.md` or `enrichment-pass.md` — type+pass working brief
3. `assets/{ASSET}.md` — asset profile (how to read this data source)
4. `types/{TYPE}/assets/{ASSET}-{pass}.md` — intersection file (optional, TYPE×ASSET rules)
5. `queries-common.md` — shared Cypher queries
6. `assets/{ASSET}-queries.md` — asset-specific fetch queries
7. `types/{TYPE}/{TYPE}-queries.md` — type-specific lookup queries
8. `evidence-standards.md` — universal evidence guardrails

**Content removed from slots 1-2 lands in slot 4 (intersection files). Content removed from slot 5 is renamed in-place or moved to slots 6-7.**

---

## Implementation Order

| Phase | Scope | Files | Depends On |
|-------|-------|-------|------------|
| 1 | Create 4 intersection files (receive relocated content) | 4 creates | 10k split landed |
| 2 | Clean 4 asset profiles (Category E) | 4 edits | Phase 1 |
| 3 | Clean type-level pass files (Category B subset) | 2 edits | Phase 1 |
| 4 | Clean core-contract.md (Category B subset) | 1 edit | Phase 1 |
| 5 | Clean common files + query descriptions (Category A) | 4 edits | — |
| 6 | Remove corporate announcement rules (Category C) | 5 edits | — |
| 7 | Update transcript intersection files (minor) | 2 edits | — |

Phases 5-7 are independent of each other and of Phases 2-4. Total: 4 creates + 18 edits = 22 file operations.

Single commit. All changes are prompt-file-only — zero script changes, zero Cypher changes, zero runtime changes.

---

## Phase 1: Create 4 New Intersection Files

These receive content relocated from type-level and asset-profile files.

### FILE 1: CREATE `types/guidance/assets/8k-primary.md`

```markdown
# Guidance × 8-K — Primary Pass

Rules for extracting guidance from 8-K earnings filings. Loaded at slot 4 by the primary agent.

## Routing — 8-K Content Fetch

Use the content fetch order in the asset profile (8k.md):
1. Query 4G (inventory) → 4C (exhibit EX-99.1)
2. Fallbacks: 4E (section text), 4F (filing text)

Apply empty-content rules from the asset profile.

## What to Extract from 8-K

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit range | "We expect Q2 revenue of $94-98 billion" | Yes: `derivation=explicit`, low=94000, high=98000 |
| Point guidance | "CapEx of approximately $2 billion" | Yes: `derivation=point`, mid=2000 |
| Table projections | Revenue guidance row: `$94B - $98B` | Yes: extract from table context |
| GAAP vs non-GAAP pair | "GAAP EPS $3.20; non-GAAP EPS $3.50" | Yes: extract BOTH with appropriate `basis_norm` |
| Growth rate guidance | "Revenue growth of 5-7% year-over-year" | Yes: `unit=percent_yoy`, low=5, high=7 |
| Margin guidance | "Gross margin between 46.5% and 47.5%" | Yes: `unit=percent`, low=46.5, high=47.5 |
| Floor/ceiling | "At least $150M in free cash flow" | Yes: `derivation=floor`, low=150 |
| Qualitative direction | "We see continued momentum" | No: lacks quantitative anchor |
| Prior quarter results | "Q1 revenue was $124 billion" | No: past period, not forward guidance |
| Safe harbor only | "Forward-looking statements involve risks..." | No: boilerplate disclaimer |

## Do NOT Extract

1. **Pure actuals** — past period results with no forward component
2. **Pure safe-harbor boilerplate** — but keep concrete guidance adjacent to disclaimers (safe-harbor proximity rule)
3. **Analyst consensus references** — "versus analyst expectations of $X" is not company guidance
4. **Historical comparisons without forward projection** — "compared to $90B last year" is context, not guidance (unless paired with a forward statement)

## Quote Prefix

All guidance extracted from 8-K exhibits/sections MUST use quote prefix: `[8-K]`

Example: `[8-K] We expect second quarter revenue to be between $94 billion and $98 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"8k"` |
| `source_key` | `"EX-99.1"`, `"EX-99.2"`, `"Item 2.02"`, `"Item 7.01"` (whichever contained the guidance) |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Exhibit or item IDs if available. Empty array `[]` when no sub-source granularity applies. |

## Dedup Rule

When the same guidance metric appears in BOTH exhibit and section text:
1. **Exhibit is primary** — use the exhibit version (more detailed, includes tables)
2. **Section may add context** — annotate in `conditions` field
3. **Never double-count** — deterministic IDs prevent duplicates; verify `source_key` differs
```

---

### FILE 2: CREATE `types/guidance/assets/news-primary.md`

```markdown
# Guidance × News — Primary Pass

Rules for extracting guidance from Benzinga news articles. Loaded at slot 4 by the primary agent.

## Routing — News Content Fetch

Use the content fetch order in the asset profile (news.md):
1. Query 6A (single item by ID)
2. For batch processing: 6B (channel-filtered)

Apply empty-content rules from the asset profile.

## Critical Rule: Company Guidance ONLY

Ignore analyst estimates ("Est $X", "consensus $Y"). Extract only company-issued guidance. This is the single most important rule for news extraction.

## What to Extract from News

| Signal | Example | Extract? |
|--------|---------|----------|
| Company guidance verb + metric + value | "Apple expects Q2 revenue of $94-98B" | Yes |
| Raised/lowered guidance | "Tesla raises full-year guidance to 2M units" | Yes: note revision in `conditions` |
| Reaffirmed guidance | "Microsoft reaffirms FY25 outlook" | Yes: `conditions = "reaffirmed"` |
| Withdrawn guidance | "Company withdraws full-year outlook" | Yes: `qualitative = "withdrawn"`, no numeric values |
| Narrowed range | "Narrows EPS guidance to $3.45-$3.55 from $3.40-$3.60" | Yes: extract NEW range only |
| Multiple metrics in body | "Revenue $94-98B, EPS $1.46-$1.50" | Yes: one GuidanceUpdate per metric |
| Floor/ceiling | "At least $150M free cash flow" | Yes: `derivation=floor` |
| Qualitative direction | "Expects double-digit services growth" | Yes: `derivation=implied`, `qualitative="double-digit"` |

## Do NOT Extract

### Analyst Estimates (CRITICAL)

Benzinga frequently mixes company guidance with analyst consensus in the same article.

| Signal | Example | Action |
|--------|---------|--------|
| "Est $X" | "Q2 EPS Est $1.43" | SKIP — analyst estimate |
| "versus consensus" | "vs consensus of $94.5B" | SKIP — analyst comparison |
| "consensus" | "Consensus expects $3.50 EPS" | SKIP — market estimate |
| "Street expects" | "The Street expects revenue of $95B" | SKIP — analyst aggregate |
| "analysts project" | "Analysts project 15% growth" | SKIP — analyst view |
| "according to estimates" | "Revenue of $95B, according to estimates" | SKIP — sourced from estimates |

### Prior Period Values

| Signal | Example | Action |
|--------|---------|--------|
| "(Prior $X)" | "Revenue guidance of $95B (Prior $93B)" | Extract $95B ONLY; $93B is historical context |
| "compared to prior guidance of" | "Raised to $3.50 from prior $3.20" | Extract $3.50 ONLY |
| "previous outlook" | "Previous outlook was $90-92B" | Do not extract as new guidance |

### Other Exclusions

- Generic positive/negative sentiment without numbers
- Pure actuals: "Q1 revenue came in at $124B"
- Analyst ratings: "Upgraded to Buy with $200 target"
- Price target changes: "Price target raised to $250"

## Reaffirmation Handling

| Verb | Treatment |
|------|-----------|
| `reaffirm` / `reaffirms` | Extract values from THIS source; `conditions = "reaffirmed"` |
| `maintain` / `maintains` | Extract values from THIS source; `conditions = "maintained"` |
| `keep` / `keeps` | Extract values from THIS source; `conditions = "maintained"` |
| `unchanged` | Extract values from THIS source; `conditions = "unchanged"` |
| `reiterate` / `reiterates` | Extract values from THIS source; `conditions = "reiterated"` |

**Rules**:
1. Extract exact values stated in THIS source — do not rewrite values to match prior guidance
2. If the news item states only "reaffirms guidance" without restating values, extract with `qualitative` only (no numeric fields)
3. Deterministic IDs + provenance preserve both history and source-level differences

## Quote Prefix

All guidance extracted from news MUST use quote prefix: `[News]`

Example: `[News] Apple Expects Q2 Revenue Between $94B-$98B`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"news"` |
| `source_key` | `"title"` (always, regardless of whether guidance was in title or body) |
| `given_date` | `n.created` (the news publication date) |
| `source_refs` | Empty array `[]` — news items have no sub-source nodes. |
```

---

### FILE 3: CREATE `types/guidance/assets/10q-primary.md`

```markdown
# Guidance × 10-Q — Primary Pass

Rules for extracting guidance from 10-Q quarterly filings. Loaded at slot 4 by the primary agent.

## Routing — 10-Q Content Fetch

Use the content fetch order in the asset profile (10q.md):
1. Query 5B (MD&A section — primary)
2. Fallbacks: 5C (financial statement footnotes), 4F (filing text)

Apply empty-content rules from the asset profile.

## What to Extract from MD&A

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit forward range | "We expect FY25 revenue between $380-390B" | Yes: `derivation=explicit` |
| CapEx/investment plans | "We plan capital expenditures of approximately $12B in fiscal 2025" | Yes: `derivation=point` |
| Growth expectations | "We expect services to grow in the low double digits" | Yes: `derivation=implied`, `qualitative="low double digits"` |
| Margin expectations | "We anticipate gross margins in the range of 44-46%" | Yes: `derivation=explicit` |
| Liquidity targets | "We target maintaining at least $20B in cash" | Yes: `derivation=floor` |
| Segment outlook | "Cloud revenue is expected to exceed $30B" | Yes: `derivation=floor`, `segment="Cloud"` |
| Past period results | "Revenue increased 8% to $95B in Q1" | No: backward-looking |
| Boilerplate risk language | "Various factors could affect our results" | No: generic disclaimer |
| Accounting policy changes | "We adopted ASC 842 effective..." | No: accounting, not guidance |
| Legal contingencies | "We may be subject to fines up to $X" | No: legal risk, not operational guidance |

## Do NOT Extract

1. **Past period results** — MD&A is primarily backward-looking; only extract statements about FUTURE periods
2. **Boilerplate / legal / risk-heavy text** — skip RiskFactors, LegalProceedings, and generic cautionary language
3. **Accounting policy descriptions** — not forward guidance
4. **Repeated guidance** — deterministic ID handles dedup automatically via MERGE. Do not manually skip.

## Forward-Looking Strictness Rule

MD&A is predominantly backward-looking. Apply the forward-looking filter strictly — target period must be after `r.created`. Zero guidance from a periodic filing is an acceptable result; do not lower thresholds to force extraction. Filter MD&A boilerplate aggressively.

## Quote Prefix

All guidance extracted from 10-Q MUST use quote prefix: `[10-Q]`

Example: `[10-Q] We expect fiscal 2025 revenue between $380 billion and $390 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"10q"` |
| `source_key` | `"MD&A"` (always, regardless of which sub-section). If from financial statement footnotes: `"footnotes"`. If from filing text fallback: `"filing_text"`. |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Empty array `[]` — 10-Q sections have no sub-source nodes. |
```

---

### FILE 4: CREATE `types/guidance/assets/10k-primary.md`

```markdown
# Guidance × 10-K — Primary Pass

Rules for extracting guidance from 10-K annual filings. Loaded at slot 4 by the primary agent.

## Routing — 10-K Content Fetch

Use the content fetch order in the asset profile (10k.md):
1. Query 5B (MD&A section — primary)
2. Fallbacks: 5C (financial statement footnotes), 4F (filing text)

Apply empty-content rules from the asset profile.

## What to Extract from MD&A

| Signal | Example | Extract? |
|--------|---------|----------|
| Explicit forward range | "We expect FY26 revenue between $400-420B" | Yes: `derivation=explicit` |
| CapEx/investment plans | "We plan capital expenditures of approximately $15B in fiscal 2026" | Yes: `derivation=point` |
| Growth expectations | "We expect services to grow in the low double digits" | Yes: `derivation=implied`, `qualitative="low double digits"` |
| Margin expectations | "We anticipate gross margins in the range of 44-46%" | Yes: `derivation=explicit` |
| Liquidity targets | "We target maintaining at least $20B in cash" | Yes: `derivation=floor` |
| Segment outlook | "Cloud revenue is expected to exceed $35B" | Yes: `derivation=floor`, `segment="Cloud"` |
| Multi-year targets | "We target 40% operating margin by fiscal 2028" | Yes: `derivation=explicit`, long_range period |
| Past period results | "Revenue increased 8% to $380B for the year" | No: backward-looking |
| Boilerplate risk language | "Various factors could affect our results" | No: generic disclaimer |
| Accounting policy changes | "We adopted ASC 842 effective..." | No: accounting, not guidance |

## Do NOT Extract

1. **Past period results** — MD&A is primarily backward-looking; only extract statements about FUTURE periods
2. **Boilerplate / legal / risk-heavy text** — skip RiskFactors, LegalProceedings, and generic cautionary language
3. **Accounting policy descriptions** — not forward guidance
4. **Repeated guidance** — deterministic ID handles dedup automatically via MERGE. Do not manually skip.

## Forward-Looking Strictness Rule

10-K MD&A is predominantly backward-looking (annual summary). Apply the forward-looking filter strictly — target period must be after `r.created`. Zero guidance from an annual filing is an acceptable result; do not lower thresholds to force extraction. Filter MD&A boilerplate aggressively.

## Quote Prefix

All guidance extracted from 10-K MUST use quote prefix: `[10-K]`

Example: `[10-K] We expect fiscal 2026 revenue between $400 billion and $420 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"10k"` |
| `source_key` | `"MD&A"` (always, regardless of which sub-section). If from financial statement footnotes: `"footnotes"`. If from filing text fallback: `"filing_text"`. |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Empty array `[]` — 10-K sections have no sub-source nodes. |
```

---

## Phase 2: Clean 4 Asset Profiles (Category E)

Remove guidance-specific content that was relocated to intersection files in Phase 1. Replace guidance-flavored wording with generic equivalents.

### FILE 5: EDIT `assets/8k.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 61 | "richest source for 8-K guidance" | "richest source for 8-K content" |
| 76 | "rarely useful for guidance" | "rarely contains extractable content" |
| 80 | "yielded zero guidance" | "yielded zero extractable content" |
| 95 | "may mix actuals and guidance" | "may mix actuals and forward-looking statements" |
| 96 | "concrete guidance" | "concrete forward-looking content" |
| 113-127 | **"What to Extract" table** (15 lines) | DELETE — moved to `8k-primary.md` |
| 128 | `---` separator after table | DELETE |
| 130-136 | **"Do NOT Extract" list** (7 lines) | DELETE — moved to `8k-primary.md` |
| 137 | `---` separator after list | DELETE |

**Lines deleted**: 27 (tables) + 2 (separators) = 29 lines removed
**Lines rewritten**: 5 word swaps

---

### FILE 6: EDIT `assets/news.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 17 | "contains complete guidance" | "contains complete forward-looking content" |
| 30 | "HIGH guidance likelihood" | "HIGH forward-looking content likelihood" |
| 37 | "MODERATE guidance likelihood" | "MODERATE forward-looking content likelihood" |
| 34 | "Company forward-looking statements" | "Company statements" |
| 41 | "may include prior guidance" | "Pre-earnings analysis" |
| 75 | "contain complete guidance" | "contain complete forward-looking content" |
| 91 | "Prior guidance values" | "Prior values for context" |
| 180 | "guidance became public" | "content became public" |
| 99-111 | **"What to Extract" table** (13 lines) | DELETE — moved to `news-primary.md` |
| 112 | `---` separator | DELETE |
| 114-143 | **"Do NOT Extract" + analyst exclusion tables** (30 lines) | DELETE — moved to `news-primary.md` |
| 144 | `---` separator | DELETE |
| 146-162 | **"Reaffirmation Handling"** (17 lines) | DELETE — moved to `news-primary.md` |
| 163 | `---` separator | DELETE |
| 208-213 | "GuidanceUpdate" references in duplicate resolution | Rewrite: "extraction item" instead of "GuidanceUpdate" (6 lines) |

**Lines deleted**: 65 (tables + sections) + 3 (separators) = 68 lines removed
**Lines rewritten**: 8 word swaps + 6 line generalizations

---

### FILE 7: EDIT `assets/10q.md`

**Note**: After the 10-K asset split, this file is already narrowed to 10-Q only. These changes remove remaining guidance-specific content.

| Line(s) | Current | New |
|---------|---------|-----|
| 16 | "designated scan scope for guidance" | "designated scan scope for extraction" |
| 62 | "Zero guidance from a 10-K" | DELETE (10-K content gone after split) |
| 85 | "10-Q/10-K guidance" | "10-Q extraction" |
| 93 | "CapEx/FCF forward guidance" | "CapEx/FCF forward expectations" |
| 97 | "zero guidance" | "zero extractable content" |
| 100-103 | "guidance keywords" reference | "extraction keywords" |
| 107 | "Zero guidance" | "Zero items" |
| 115, 119-120, 122 | "Guidance Likelihood" column header + values | "Forward-Looking Likelihood" |
| 124-138 | **"What to Extract from MD&A" table** (15 lines) | DELETE — moved to `10q-primary.md` |
| 139 | `---` separator | DELETE |
| 141-147 | **"Do NOT Extract" list** (7 lines) | DELETE — moved to `10q-primary.md` |
| 148 | `---` separator | DELETE |
| 165, 169, 171 | "guidance" in period/source sections | "content" / "extraction" |
| 183-185 | **"Forward-Looking Strictness" quality rule** (3 lines) | DELETE — moved to `10q-primary.md` |
| 236-237 | "Guidance frequency" in comparison table | "Forward-looking content frequency" |

**Lines deleted**: 27 (tables + rules) + 2 (separators) = 29 lines removed
**Lines rewritten**: 13 word swaps

---

### FILE 8: EDIT `assets/10k.md`

**Note**: This file is created by the 10-K split plan. These changes remove guidance-specific content from it.

Apply the same pattern as 10q.md above — the file is a copy of 10q.md narrowed to 10-K. Identical categories of changes:

| Category | Action |
|----------|--------|
| "guidance" word occurrences | Rewrite → "extraction" / "content" / "items" |
| "What to Extract from MD&A" table | DELETE — moved to `10k-primary.md` |
| "Do NOT Extract" list | DELETE — moved to `10k-primary.md` |
| "Forward-Looking Strictness" rule | DELETE — moved to `10k-primary.md` |

Exact line numbers depend on the 10-K split output. Apply by pattern matching rather than line numbers.

---

## Phase 3: Clean Type-Level Pass Files (Category B — pass files)

Remove asset-specific content from files loaded for ALL assets when TYPE=guidance.

### FILE 9: EDIT `types/guidance/primary-pass.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 7 | "Extract from primary section only (prepared remarks for transcripts, full content for other assets)." | "Extract from primary content section only (per intersection file for scan scope)." |
| 24-33 | **STEP 2 routing table** — 4-row table mapping each asset to queries | Replace entire table with: `Route by \`ASSET\` — see your asset profile (slot 3) for content fetch order. The intersection file (slot 4) may provide additional routing guidance.` |
| 35 | "Apply empty-content rules (core-contract.md S17)." | Keep as-is (generic reference) |
| 37 | "**For transcripts**: Extract from Prepared Remarks only. Full Q&A analysis is handled by the enrichment pass. Only use `qa_exchanges` from 3B as fallback if prepared remarks are truncated or empty. If 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing." | DELETE — already in `transcript-primary.md` lines 7-12 |
| 93 | "**News: company guidance only** — ignore analyst estimates ("Est $X", "consensus $Y"). Extract only company-issued guidance." | DELETE — moved to `news-primary.md` |
| 116-118 | "### Fiscal Context Rule\n\nIn earnings calls and SEC filings, ALL period references are fiscal unless explicitly stated as calendar. "Second half" = fiscal H2. Only use calendar interpretation when text explicitly says "calendar year/quarter" — set `calendar_override: true`." | DELETE — already in `core-contract.md` line 412-414 (identical text). Zero content loss. |
| 169-198 | JSON example payload with transcript-specific values | Replace with generic example (see below) |
| 201 | "**`source_type`**: Use `{SOURCE_TYPE}` from your input arguments (not `{ASSET}`). These differ for 10-K filings routed through the `10q` asset pipeline." | "**`source_type`**: Use `{ASSET}` — this is the source type identity written to the graph." (Note: if 10k split landed first, this line is already updated per treehouse plan) |
| 205 | "**`source_refs`**: Array of sub-source node IDs that produced the item. For transcripts, use PreparedRemark ID (`{SOURCE_ID}_pr`) or QAExchange IDs (`{SOURCE_ID}_qa__{sequence}`). For 8-K reports, use exhibit/item IDs if available. Empty array `[]` when no sub-source granularity applies." | "**`source_refs`**: Array of sub-source node IDs that produced the item. See intersection file for per-asset format. Empty array `[]` when no sub-source granularity applies." |

**Generic JSON example** (replaces lines 169-198):

```json
{
    "source_id": "{SOURCE_ID}",
    "source_type": "{ASSET}",
    "ticker": "{TICKER}",
    "fye_month": "{FYE_MONTH from Step 1}",
    "items": [
        {
            "label": "Revenue",
            "given_date": "{given_date per intersection file}",
            "fiscal_year": 2024,
            "fiscal_quarter": 1,
            "basis_norm": "unknown",
            "segment": "Total",
            "low": 89.0, "mid": null, "high": 93.0,
            "unit_raw": "billion",
            "qualitative": "similar to last year",
            "conditions": null,
            "quote": "We expect revenue...",
            "section": "{section per intersection file}",
            "source_key": "{source_key per intersection file}",
            "derivation": "explicit",
            "basis_raw": null,
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": [],
            "source_refs": []
        }
    ]
}
```

**Lines deleted**: ~18 (routing table + transcript scope + news filter + fiscal context)
**Lines rewritten**: ~35 (JSON example + scope + source_refs)

---

### FILE 10: EDIT `types/guidance/enrichment-pass.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 138 | "**Corporate announcements ARE extractable** — management decisions that allocate specific capital or change shareholder returns." | Phase 6 (Category C) — see below |

No other Category B changes needed. Enrichment-pass.md was already genericized in the previous pollution fix.

---

## Phase 4: Clean core-contract.md (Category B — reference file)

### FILE 11: EDIT `types/guidance/core-contract.md`

| Line(s) | Current | New | Category |
|---------|---------|-----|----------|
| 99 | `source_refs \| String[] \| IDs of sub-source nodes (e.g., QAExchange IDs for transcripts). Empty array if none.` | `source_refs \| String[] \| IDs of sub-source nodes (per intersection file). Empty array if none.` | B |
| 124 | `section` example: `"CFO Prepared Remarks"` | `"{section_identifier}"` | B |
| 125 | `source_key` examples: `"EX-99.1"`, `"full"`, `"title"`, `"MD&A"` | `"{per intersection file}"` | B |
| 127 | `source_type` enum: `8k, transcript, news, 10q, 10k` | `Matches \`{ASSET}\`. Extensible — add values as new source types are created.` | B |
| 507-513 | Source Types and Richness table (5 rows: Transcript/8-K/News/10-Q/XBRL) | Replace with: `Source richness varies by asset type — see asset profiles for characteristics. XBRL contains actuals only (no forward guidance).` | B |
| 517 | "Extraction MUST route by `source_type` before LLM processing. Each type has different scan scope and noise profiles. Per-source profiles in `reference/`:" | "Extraction MUST route by asset type before LLM processing. Per-source profiles loaded at slot 3 via `assets/{ASSET}.md`." | B |
| 519-524 | Routing table (4 rows mapping source_type → asset profile file) | DELETE — routing is via file path convention, documented in agent shell | B |
| 528-534 | Source Type Mapping table (source_key + given_date per asset) | Replace with: `Source field mappings (source_key, given_date, source_refs) are defined per asset in the intersection file (slot 4).` | B |
| 554 | "**Transcripts**: Two-pass extraction — prepared remarks via primary agent, Q&A enrichment via enrichment agent. MERGE+SET handles second write safely." | "**Two-pass assets**: Primary pass writes items, enrichment pass updates via MERGE+SET. The enrichment intersection file defines secondary content scope." | B |
| 556 | "**All other source types**: Read all content first, extract the richest version per metric, write once per slot." | Keep as-is (generic) | — |
| 571 | "**News: company guidance only** \| Ignore analyst estimates..." | DELETE — moved to `news-primary.md` | B |
| 573 | "**Material corporate announcements** \| Extract management decisions..." | Phase 6 (Category C) — see below | C |
| 651 | `ASSET \| Enum \| \`transcript\`, \`8k\`, \`news\`, \`10q\`` | `ASSET \| Enum \| Extensible. Current: \`transcript\`, \`8k\`, \`news\`, \`10q\`, \`10k\`` | B |
| 693-699 | Empty-Content Rules per Source Type table (4 rows) | Replace with: `Empty-content conditions are defined per asset in the asset profile (slot 3).` | B |
| 710-723 | Reference Files table (hardcoded 8 asset-specific files + 4 utility scripts) | Replace file table with path patterns: `Asset profiles: \`assets/{ASSET}.md\``, `Asset queries: \`assets/{ASSET}-queries.md\``, `Intersection files: \`types/{TYPE}/assets/{ASSET}-{pass}.md\`` Keep utility scripts table as-is. | B |

**Lines deleted**: ~30 (routing table + source mapping + empty-content table + news filter row + old reference table)
**Lines rewritten**: ~20 (generalizations + path patterns)
**Net effect**: core-contract.md shrinks by ~25 lines (toward fixing S11 #4 "too long")

---

## Phase 5: Clean Common Files + Query Descriptions (Category A)

### FILE 12: EDIT `queries-common.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 184 | `WHERE r8k.items CONTAINS 'Item 2.02'` | DELETE this WHERE clause. Rename `earnings_8k_count` → `r8k_count` in RETURN (line 196). Query 8A becomes a general inventory counting ALL 8-Ks. Type-specific item filtering belongs in type queries. |
| 196 | `count(DISTINCT r8k) AS earnings_8k_count` | `count(DISTINCT r8k) AS r8k_count` |
| 300-308 | Execution Order "Initial Build" step 4 sub-bullets: asset-specific query sequences | Replace step 4 sub-bullets with single line: `- Asset-specific source queries (see asset query files for fetch order per source type)` |
| 308 | "6B (Guidance-channel news, dates required)" | Absorbed into generic line above |

---

### FILE 13: EDIT `assets/news-queries.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 17 | "### 6B. Guidance-Channel News (Pre-Filtered)" | "### 6B. Channel-Filtered News (Pre-Filtered)" |
| 19 | "These channels most likely contain company guidance." | "These channels most likely contain forward-looking content." |
| 51 | "### 6D. News with Body Content" description "body field is often empty" | Keep as-is (already generic) |
| 55 | "### 6E. Earnings Beat/Miss News (for Context)" description "useful for cross-referencing guidance context" | "useful for cross-referencing extraction context" |

Zero Cypher changes. Description-only rewrites.

---

### FILE 14: EDIT `assets/10q-queries.md`

| Line(s) | Current | New |
|---------|---------|-----|
| 20 | "Primary for 10-Q/10-K" | "Primary for 10-Q" (if 10k split already landed, this is already done) |
| 22 | "10-Q/10-K guidance extraction" | "10-Q extraction" |
| 34 | "look for footnotes/annotations with forward guidance" | "look for footnotes/annotations with forward-looking content" |
| 51-53 | "Useful to identify so guidance scanner can skip this section" | "Useful to identify so the extraction scanner can skip this section" |

Zero Cypher changes. Description-only rewrites.

---

### FILE 15: EDIT `assets/10k-queries.md`

Apply same pattern as 10q-queries.md above. Exact lines depend on 10-K split output.

| Pattern | Current | New |
|---------|---------|-----|
| "guidance extraction" | → "extraction" |
| "guidance scanner" | → "extraction scanner" |
| "forward guidance" | → "forward-looking content" |

---

## Phase 6: Remove Corporate Announcement Rules (Category C)

Remove rules that embed `announcement` extraction logic into the `guidance` type. Replace with exclusion note.

### FILE 16: EDIT `types/guidance/primary-pass.md` (continued from Phase 3)

| Line | Current | New |
|------|---------|-----|
| 92 | "**Corporate announcements ARE extractable** — management decisions that allocate specific capital or change shareholder returns (buyback authorizations, dividend declarations, investment announcements) should be extracted." | "**Corporate announcements** — Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans). These belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable (it is guidance, not an announcement)." |

### FILE 17: EDIT `types/guidance/enrichment-pass.md`

| Line | Current | New |
|------|---------|-----|
| 138 | "**Corporate announcements ARE extractable** — management decisions that allocate specific capital or change shareholder returns." | "**Corporate announcements** — Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans). These belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable." |

### FILE 18: EDIT `types/guidance/core-contract.md` (continued from Phase 4)

| Line | Current | New |
|------|---------|-----|
| 573 | "**Material corporate announcements** \| Extract management decisions that allocate specific capital or change shareholder returns (e.g., buyback authorizations, dividend declarations, major investment programs). These are announced actions, not forecasts — use `derivation=explicit` or `derivation=point` for stated amounts, `derivation=comparative` for directional changes. Apply the same specificity rules: a quantitative anchor is required." | "**Corporate announcements** \| Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans) — these belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable." |

### FILE 19: EDIT `types/guidance/assets/transcript-primary.md`

| Line | Current | New |
|------|---------|-----|
| 42 | `\| Corporate announcement \| "Share repurchase authorization of $XX billion", "quarterly dividend of $X.XX per share" \| Yes: \`derivation=explicit\`, material capital announcement \|` | `\| Dividend guidance \| "quarterly dividend of $X.XX per share" \| Yes: `derivation=point`. Do NOT extract buyback authorizations or investment programs (separate type). \|` |

### FILE 20: EDIT `types/guidance/assets/transcript-enrichment.md`

| Line | Current | New |
|------|---------|-----|
| 51 | `\| Capital announcement or return decision \| "We authorized a new buyback program", "we increased the dividend" \| Yes: material capital/return announcement \|` | `\| Dividend guidance \| "we increased the dividend to $X.XX per share" \| Yes: `derivation=point`. Do NOT extract buyback authorizations or investment programs (separate type). \|` |

---

## Phase 7: Update Transcript Intersection Files (Minor)

Add source_refs format to transcript-primary.md for completeness (currently only in transcript-enrichment.md).

### FILE 21: EDIT `types/guidance/assets/transcript-primary.md`

Add after line 51 (after the quote prefix section):

```markdown

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"transcript"` |
| `source_key` | `"full"` |
| `given_date` | `t.conference_datetime` |
| `source_refs` | PreparedRemark ID: `{SOURCE_ID}_pr`. For Q&A fallback items: QAExchange IDs `{SOURCE_ID}_qa__{sequence}`. |
```

### FILE 22: EDIT `types/guidance/assets/transcript-enrichment.md`

No changes needed — source_refs already documented at line 85.

---

## Verification Checklist

### Contagion-Free Assertions

After all changes, these `grep` commands must return ZERO matches:

```bash
# Category A: No guidance-flavored wording in common files
grep -i "guidance" .claude/skills/extract/queries-common.md
# Expected: 0 matches (was 1 at line 308)

# Category B: No asset-specific content in type-level files
grep -i "transcript\|prepared.remarks\|Q&A\|qa_exchange\|CFO\|8-K\|8k\|EX-99\|news\|10q\|10k\|MD&A" .claude/skills/extract/types/guidance/primary-pass.md
# Expected: 0 matches (was ~15)

# Category B: No hardcoded asset examples in core-contract field definitions
grep -i "QAExchange\|CFO Prepared\|EX-99\|\"full\"\|\"title\"\|\"MD&A\"" .claude/skills/extract/types/guidance/core-contract.md
# Expected: 0 matches in S2 extraction fields table (lines 107-129). NOTE: Some may appear in
# non-field-definition contexts (e.g., S14 Chronological Ordering) — those are acceptable.

# Category C: No "ARE extractable" corporate announcement rules
grep -i "ARE extractable\|capital announcement\|buyback.*extractable" .claude/skills/extract/types/guidance/*.md .claude/skills/extract/types/guidance/assets/*.md
# Expected: 0 matches

# Category E: No "guidance" in asset profiles (except "forward-looking" which is generic)
grep -w "guidance" .claude/skills/extract/assets/8k.md .claude/skills/extract/assets/news.md .claude/skills/extract/assets/10q.md .claude/skills/extract/assets/10k.md
# Expected: 0 matches
```

### Zero-Regression Matrix

For each agent configuration, verify the prompt stream contains all necessary content:

| TYPE | ASSET | PASS | Slot 4 File | Key Content Preserved |
|------|-------|------|-------------|----------------------|
| guidance | transcript | primary | transcript-primary.md | Speaker hierarchy, PR scope, What-to-Extract, quote prefix `[PR]`, source_refs format |
| guidance | transcript | enrichment | transcript-enrichment.md | Q&A scope, What-to-Extract, quote prefix `[Q&A]`, section format, source_refs format |
| guidance | 8k | primary | **8k-primary.md** (NEW) | What-to-Extract, Do-Not-Extract, quote prefix `[8-K]`, source fields, dedup rule |
| guidance | news | primary | **news-primary.md** (NEW) | Company-only filter, What-to-Extract, analyst exclusion, reaffirmation handling, quote prefix `[News]`, source fields |
| guidance | 10q | primary | **10q-primary.md** (NEW) | What-to-Extract, Do-Not-Extract, forward-looking strictness, quote prefix `[10-Q]`, source fields |
| guidance | 10k | primary | **10k-primary.md** (NEW) | What-to-Extract, Do-Not-Extract, forward-looking strictness, quote prefix `[10-K]`, source fields |

For each row: concatenate the 8 slot files, diff against the pre-change concatenation. Every line removed from slots 1-2 or 5 must appear in slot 3 or 4.

### New-Asset Smoke Test

To verify a hypothetical new asset `foo` added to the guidance type would inherit ZERO contagion:

1. `primary-pass.md` — contains no asset-specific references → CLEAN
2. `core-contract.md` — contains no hardcoded asset examples in field definitions → CLEAN
3. `queries-common.md` — contains no asset-specific filters → CLEAN
4. Agent loads `assets/foo.md` (slot 3) and optionally `types/guidance/assets/foo-primary.md` (slot 4) — both written fresh for `foo`
5. No guidance-specific content inherited from any common or type-level file

### New-Type Smoke Test

To verify a hypothetical new type `analyst` would inherit ZERO contagion:

1. `queries-common.md` — contains no type-specific references → CLEAN
2. Asset profiles — contain no type-specific content → CLEAN (after Category E cleanup)
3. New type gets its own `types/analyst/core-contract.md`, `primary-pass.md`, etc.
4. No guidance-specific content inherited from any common or asset-level file

---

## Totals

| Metric | Count |
|--------|-------|
| New files created | 4 intersection files |
| Files edited | 18 |
| Lines relocated to intersection files | ~126 (tables, rules, field mappings) |
| Lines rewritten in-place | ~42 (word swaps: "guidance" → "content"/"extraction") |
| Lines generalized | ~50 (hardcoded tables → generic references) |
| Category C replacements | 5 (across 5 files) |
| Net lines removed from type files | ~55 (core-contract.md + primary-pass.md) |
| Net lines added to intersection files | ~320 (4 new files) |
| Cypher query changes | 1 (remove Item 2.02 filter from 8A) |
| Script changes | 0 |
| Runtime behavior changes | 0 |

---

## Commit Message

```
Eliminate all prompt-layer contagion across extraction pipeline (Categories A/B/C/E)

Create 4 intersection files (8k/news/10q/10k-primary.md) receiving guidance-specific
content from type-level and asset-profile files. Generalize primary-pass.md,
core-contract.md, queries-common.md, and 4 asset profiles. Replace corporate
announcement extraction rules with exclusion notes. Zero behavioral regression —
agents see identical content from intersection files at slot 4.
```

---

## Rollback

```bash
git revert <commit>   # single commit, single revert
```

---

## Tracker Updates (post-commit)

Update `extraction-pipeline-tracker.md`:

1. Move all Category A/B/C/E items from "STILL OPEN — CONTAGION RISKS" to "Completed — Pollution Fixes"
2. Move "Open — Remaining Pollution (8k/news/10q)" section to "Completed"
3. Move "Open — Top Note #2: Corporate Announcements" to "Completed" with note: "Replaced with exclusion. Full `announcement` type deferred to Phase 4."
4. Add this plan to "Source Files Disposition" as ARCHIVE (fully implemented)

---

*Plan created 2026-03-08. Depends on: 10-K asset split (virtual-splashing-treehouse.md). Scope: 4 creates + 18 edits = 22 file operations, single commit.*
