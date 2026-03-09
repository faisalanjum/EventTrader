# News Asset — Decontamination + Data Structure Completion

Fix remaining guidance contagion in `news.md` and `news-queries.md`, add missing Neo4j data structure documentation, and relocate type-specific content to the intersection file.

**Depends on**: `total-contagion-fix.md` (landed, commit `84fc97f`) — that fix replaced "guidance" with "forward-looking content" but left deeper structural contagion untouched.

**Scope**: 3 files edited (`news.md`, `news-queries.md`, `news-primary.md`). Zero script changes, zero query logic changes, zero runtime changes.

---

## Problem Statement

The contagion fix (commit `84fc97f`) removed explicit guidance vocabulary ("guidance likelihood", "forward-looking statements") from `news.md` by substituting "forward-looking content." This was a surface-level synonym swap — the deeper issues remain:

1. **Channel filter is guidance-biased**: The asset profile hardcodes 6 channels selected for "forward-looking content likelihood." An `announcement` type needs `M&A`, `Dividends`, `Contracts`. A `sentiment` type needs `Analyst Ratings`, `Upgrades`, `Downgrades`. The channel CONCEPT is asset-specific; the channel SELECTION is type-specific.

2. **Fulltext keywords are guidance-specific**: `guidance OR outlook OR expects OR forecast` — 100% guidance vocabulary baked into the asset profile.

3. **Title examples are 100% guidance**: All 4 examples show guidance headlines. No non-guidance headline shown.

4. **Body bullets contain extraction rules**: "do NOT extract as new items" and "DO NOT extract" are WHAT-to-extract instructions, not data structure descriptions.

5. **6 of 13 News node properties undocumented**: `market_session`, `authors`, `url`, `updated`, `returns_schedule`, `embedding` — all present on 100% of 341,927 nodes.

6. **Relationships entirely undocumented**: `INFLUENCES` → Company/Sector/Industry/MarketIndex with 14 return properties (daily_stock, hourly_stock, session_stock, etc.).

7. **Indexes undocumented**: 3 indexes (unique constraint, fulltext, vector) not mentioned in asset profile.

---

## Ground Truth (from Neo4j queries, 2026-03-08)

### News Node — 13 Properties (341,927 nodes)

| Property | Type | Coverage | Example |
|----------|------|----------|---------|
| `id` | String | 100% | `bzNews_42804598` |
| `title` | String | 100% | Headline text |
| `body` | String | 100% (10.2% empty) | Article body |
| `teaser` | String | 100% | Short summary |
| `created` | String (ISO+TZ) | 100% | `2025-01-05T08:02:20-05:00` |
| `updated` | String (ISO+TZ) | 100% | Usually same as created |
| `url` | String | 100% | Benzinga article URL |
| `authors` | String (JSON array) | 100% | `["Benzinga Neuro"]`, `["Kaustubh Bagalkote"]` |
| `channels` | String (JSON array) | 100% | `["News", "Tech"]` |
| `tags` | String (JSON array) | 100% | `["China", "Consumer Tech"]` |
| `market_session` | String | 100% | `in_market` (46%), `pre_market` (37%), `post_market` (14%), `market_closed` (3%) |
| `returns_schedule` | String (JSON) | 100% | `{"hourly":"...","session":"...","daily":"..."}` |
| `embedding` | Vector | 100% | 1536-dim embedding |

### Relationships (outgoing only)

| Relationship | Target | Count | Key Properties |
|-------------|--------|-------|---------------|
| `INFLUENCES` | `Company` | 341,926 | `symbol`, `daily_stock`, `hourly_stock`, `session_stock`, `daily_sector`, `hourly_sector`, `session_sector`, `daily_industry`, `hourly_industry`, `session_industry`, `daily_macro`, `hourly_macro`, `session_macro`, `created_at` |
| `INFLUENCES` | `Sector` | 341,926 | Same property set |
| `INFLUENCES` | `Industry` | 341,926 | Same property set |
| `INFLUENCES` | `MarketIndex` | 341,918 | Same property set |

No incoming relationships.

### Indexes

| Index Name | Type | Properties |
|-----------|------|-----------|
| `constraint_news_id_unique` | RANGE (unique) | `id` |
| `news_ft` | FULLTEXT | `title`, `body`, `teaser` |
| `news_vector_index` | VECTOR | `embedding` |

### All Benzinga Channels (top 20 by count)

| Channel | Count | Relevant For |
|---------|-------|-------------|
| `News` | 255,104 | All types |
| `Analyst Ratings` | 157,216 | Sentiment |
| `Price Target` | 124,254 | Sentiment |
| `Earnings` | 50,686 | Guidance, actuals |
| `Trading Ideas` | 39,076 | Sentiment |
| `Markets` | 34,163 | Context |
| `Guidance` | 21,696 | Guidance |
| `Options` | 19,413 | — |
| `General` | 17,517 | — |
| `Movers` | 15,612 | Context |
| `Reiteration` | 13,506 | Sentiment |
| `Tech` | 11,957 | Sector |
| `Dividends` | 7,467 | Announcements |
| `Upgrades` | 7,700 | Sentiment |
| `Downgrades` | 7,761 | Sentiment |
| `Earnings Beats` | 6,168 | Guidance, actuals |
| `M&A` | 4,206 | Announcements |
| `Management` | 4,458 | Guidance, announcements |
| `Contracts` | 3,903 | Announcements |
| `Earnings Misses` | 2,854 | Guidance, actuals |

---

## Contagion Issues

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| C1 | news.md L26-66 | Channel Filter hardcodes guidance-biased channels + "forward-looking" vocabulary | HIGH |
| C2 | news.md L17,30,37,75 | "forward-looking content" is guidance synonym, not neutral language | MEDIUM |
| C3 | news.md L59-65 | Fulltext keywords (`guidance OR outlook OR expects...`) are guidance-specific | HIGH |
| C4 | news.md L82-85 | All 4 title examples show guidance headlines | MEDIUM |
| C5 | news.md L91,95 | Body bullets have "DO NOT extract" instructions (extraction rules in asset profile) | MEDIUM |
| C6 | news-queries.md L19,51 | "forward-looking content" in query descriptions | LOW |
| C7 | news.md L124 | References `core-contract.md` (guidance type file) from asset profile | LOW (accepted) |

## Data Structure Gaps

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| D1 | news.md Data Structure | Missing 6 properties: `updated`, `url`, `authors`, `market_session`, `returns_schedule`, `embedding` | HIGH |
| D2 | news.md | Relationships entirely undocumented (INFLUENCES → 4 targets + 14 return properties) | HIGH |
| D3 | news.md | Indexes not documented | MEDIUM |
| D4 | news.md L18 | Body empty says ~12%, actual is 10.2% | LOW |
| D5 | news.md L130-136 | `given_date` and `source_key` defined twice (L112-118 and L130-136) | LOW |
| D6 | news.md L162 | Version note stale — references "analyst exclusion, reaffirmation handling" which were moved to intersection file | LOW |

## Query File Issues

| # | Location | Issue | Severity |
|---|----------|-------|----------|
| Q1 | news-queries.md 6B | Hardcoded guidance channels in WHERE clause | MEDIUM |
| Q2 | news-queries.md L19,51 | "forward-looking content" vocabulary | LOW |

---

## Changes

### Change 1: `news.md` — Expand Data Structure Table

**Current** (7 fields):
```markdown
| Field | Type | Description |
| `n.id` | String | ... |
| `n.title` | String | ... |
| `n.body` | String | ... |
| `n.teaser` | String | ... |
| `n.created` | String (ISO) | ... |
| `n.channels` | String | ... |
| `n.tags` | String | ... |
```

**New** (13 fields):
```markdown
| Field | Type | Description |
|-------|------|-------------|
| `n.id` | String | Unique Benzinga news ID |
| `n.title` | String | Headline text. Always present. |
| `n.body` | String | Article body. Empty on ~10% of items. |
| `n.teaser` | String | Short summary. Often truncated version of body. |
| `n.created` | String (ISO+TZ) | Publication datetime (e.g., `2025-01-05T08:02:20-05:00`) |
| `n.updated` | String (ISO+TZ) | Last update datetime. Usually identical to `created`. |
| `n.url` | String | Benzinga source article URL |
| `n.authors` | String (JSON array) | Author names. `["Benzinga Neuro"]` = AI-generated; human names for editorial content. |
| `n.channels` | String (JSON array) | Benzinga channel tags (see Channel Reference below) |
| `n.tags` | String (JSON array) | Topic/entity tags |
| `n.market_session` | String | Market timing: `in_market` (46%), `pre_market` (37%), `post_market` (14%), `market_closed` (3%) |
| `n.returns_schedule` | String (JSON) | Return measurement windows: `{"hourly":"...","session":"...","daily":"..."}` |
| `n.embedding` | Vector | 1536-dim text embedding for semantic similarity search |
```

**What changed**: Added 6 missing properties. Removed "forward-looking content" from `n.title` description. Fixed body empty percentage to ~10%. Changed `n.created` type from `String (ISO)` to `String (ISO+TZ)` (actually includes timezone offset).

### Change 2: `news.md` — Add Relationships Section

**New section** (after Data Structure table):

```markdown
### Relationships

News nodes have outgoing `INFLUENCES` relationships to four entity types:

| Target | Count | Query Pattern |
|--------|-------|--------------|
| `Company` | 341,926 | `(n:News)-[:INFLUENCES]->(c:Company)` |
| `Sector` | 341,926 | `(n:News)-[:INFLUENCES]->(s:Sector)` |
| `Industry` | 341,926 | `(n:News)-[:INFLUENCES]->(i:Industry)` |
| `MarketIndex` | 341,918 | `(n:News)-[:INFLUENCES]->(m:MarketIndex)` |

No incoming relationships.

**INFLUENCES properties** (on relationship, not node):

| Property | Type | Description |
|----------|------|-------------|
| `symbol` | String | Ticker symbol |
| `daily_stock` | Float | Stock return from publication to market close |
| `hourly_stock` | Float | Stock return in first hour after publication |
| `session_stock` | Float | Stock return from publication to session end |
| `daily_sector` / `hourly_sector` / `session_sector` | Float | Sector-level returns at same horizons |
| `daily_industry` / `hourly_industry` / `session_industry` | Float | Industry-level returns at same horizons |
| `daily_macro` / `hourly_macro` / `session_macro` | Float | Market index returns at same horizons |
| `created_at` | String | Timestamp when returns were computed |

**Do NOT select return properties in extraction queries** — they waste context and are irrelevant to content extraction. Use them only for impact analysis.
```

### Change 3: `news.md` — Add Indexes Section

**New section** (after Relationships):

```markdown
### Indexes

| Index | Type | Properties | Usage |
|-------|------|-----------|-------|
| `constraint_news_id_unique` | RANGE (unique) | `id` | Lookup by news ID |
| `news_ft` | FULLTEXT | `title`, `body`, `teaser` | Keyword search (query 9F) |
| `news_vector_index` | VECTOR | `embedding` | Semantic similarity search |
```

### Change 4: `news.md` — Replace Channel Filter with Channel Reference

**Current** (lines 26-66): Guidance-biased channel filter with "forward-looking content likelihood" rankings, hardcoded 6-channel selection, and fulltext keywords.

**New**: Type-neutral channel reference + mechanism description. Channel SELECTION moves to intersection file.

```markdown
## Channel Reference

News items are tagged with one or more Benzinga channels. Channels indicate content type and are stored as a JSON array string in `n.channels`.

### Channel Filtering Mechanism

Use `n.channels CONTAINS $channel_name` for filtering. Note: `CONTAINS 'Earnings'` also matches `Earnings Beats` and `Earnings Misses` (substring match).

Intersection files (slot 4) specify which channels to filter for each extraction type.

### All Channels (by frequency)

| Channel | Count | Content Type |
|---------|-------|-------------|
| `News` | 255,104 | General news |
| `Analyst Ratings` | 157,216 | Rating changes (Buy/Sell/Hold) |
| `Price Target` | 124,254 | Analyst price target updates |
| `Earnings` | 50,686 | Earnings results and related coverage |
| `Trading Ideas` | 39,076 | Trade setup analysis |
| `Markets` | 34,163 | Market-wide commentary |
| `Guidance` | 21,696 | Company forward statements |
| `Options` | 19,413 | Options activity |
| `General` | 17,517 | Uncategorized |
| `Movers` | 15,612 | Significant price moves |
| `Reiteration` | 13,506 | Analyst rating reiterations |
| `Tech` | 11,957 | Technology sector |
| `Dividends` | 7,467 | Dividend actions |
| `Upgrades` | 7,700 | Analyst upgrades |
| `Downgrades` | 7,761 | Analyst downgrades |
| `Earnings Beats` | 6,168 | Beat consensus |
| `Equities` | 5,785 | Equity-specific |
| `Biotech` | 5,426 | Biotech sector |
| `Management` | 4,458 | Management commentary |
| `M&A` | 4,206 | Mergers & acquisitions |
| `Contracts` | 3,903 | Contract awards |
| `Earnings Misses` | 2,854 | Missed consensus |

### Fulltext Search

Fulltext index `news_ft` covers `title`, `body`, `teaser`. Query via `db.index.fulltext.queryNodes('news_ft', $query)` (query 9F in queries-common.md). Search terms are type-specific — see intersection file.
```

**What is removed**: "Pre-LLM Gate" language, "forward-looking content likelihood" rankings, hardcoded 6-channel filter, fulltext keyword string. ALL moved to intersection file (Change 7).

### Change 5: `news.md` — Neutralize Scan Scope

**Current title section** (lines 73-85):
```markdown
Titles frequently contain complete forward-looking content in a structured pattern:
{Company} {Action Verb} {Metric} {Value/Range} {Period}
Examples:
- Apple Expects Q2 Revenue Between $94B-$98B
- Tesla Raises Full-Year Delivery Guidance To 2M Units
- Microsoft Reaffirms FY25 Revenue Outlook At $245B
- Amazon Lowers Q3 Operating Income Guidance To $11.5B-$15B
```

**New**:
```markdown
Titles frequently contain structured, extractable content. Common pattern:

{Company} {Action Verb} {Subject} {Value/Detail}

Title-only extraction is valid — ~10% of items have no body text.
```

**What changed**: Removed guidance-specific examples and "forward-looking content" language. Removed `{Period}` from pattern (not all types care about periods). Kept the structural insight (titles are structured and extractable).

**Current body section** (lines 88-95):
```markdown
Body text may contain:
- Additional metrics not in the title
- Prior values for context (do NOT extract as new items)
- GAAP vs non-GAAP clarification
- Segment-level detail
- Conditions or assumptions
- Analyst consensus comparisons (DO NOT extract)
```

**New**:
```markdown
Body text may contain:
- Additional detail not in the title
- GAAP vs non-GAAP clarification
- Segment-level breakdowns
- Conditions, assumptions, or caveats
- Prior/historical values for context
- Analyst commentary and consensus data
```

**What changed**: Removed "do NOT extract" / "DO NOT extract" instructions (extraction rules belong in intersection file). Reframed bullets as neutral data structure descriptions.

### Change 6: `news.md` — Deduplicate + Clean Up

1. **Remove duplicate `given_date`** (lines 130-132) — already defined at lines 112-114.
2. **Remove duplicate `source_key`** (lines 134-136) — already defined at lines 116-118.
3. **Remove "Basis, Segment, Quality Filters" section header** (lines 122-128) — the `core-contract.md` reference is type-coupled. Keep the "News-Specific: Basis Defaults to Unknown" note but move it under the existing source_key section.
4. **Update version note** — bump to v2.0, remove stale "analyst exclusion, reaffirmation handling" references.

### Change 7: `news-primary.md` — Add Channel Filter + Fulltext Keywords

**Add new section** after Routing (relocated from news.md):

```markdown
## Channel Filter (Guidance)

Filter news items by channel BEFORE LLM processing. These channels have the highest likelihood of containing company guidance.

**Primary** (filter via query 6B):
- `Guidance` (~21,700) — company forward statements
- `Earnings` (~50,700) — earnings results, often includes outlook

**Secondary** (also included in 6B via substring match on 'Earnings'):
- `Earnings Beats` (~6,200) — beat context, sometimes revised outlook
- `Earnings Misses` (~2,900) — miss context, sometimes revised outlook

**Additional** (included in 6B):
- `Previews` (~600) — pre-earnings analysis
- `Management` (~4,500) — management commentary

### Supplementary Fulltext Recall

After channel-filtered extraction, run fulltext search (query 9F) for items missed by channel filter:

```
guidance OR outlook OR expects OR forecast OR "full year" OR "fiscal year"
```

Cross-check hits against already-processed IDs to avoid re-extraction.
```

### Change 8: `news-queries.md` — Neutralize Descriptions + Add Generic Query

**6B description** (line 19):
- Current: "These channels most likely contain forward-looking content."
- New: "Channels are type-specific — see intersection file for which channels to use. Default set shown below covers guidance extraction."

**6D note** (line 51):
- Current: "title may contain complete forward-looking content"
- New: "title may contain complete extractable content"

**Add 6F** — Generic channel-filtered query with parameterized note:

```markdown
### 6F. News by Channel (Generic)

Channel-filtered query. Intersection file specifies which channels to use per extraction type. Adjust the CONTAINS clauses to match the type's channel list.

\```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date
  AND n.created <= $end_date
  AND (n.channels CONTAINS $channel_1
    OR n.channels CONTAINS $channel_2)
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
\```
**Note**: Cypher does not support parameterized lists in CONTAINS. Copy this template and replace `$channel_N` with literal channel names from the intersection file.
```

---

## Content Relocation Guarantee

For every piece of content removed from `news.md`, equivalent or stronger content exists in the intersection file:

| Removed from news.md | Now in news-primary.md |
|----------------------|----------------------|
| Channel filter (6 channels + ranking) | Change 7: Channel Filter section with same channels + counts |
| Fulltext keywords (`guidance OR outlook...`) | Change 7: Supplementary Fulltext Recall |
| Title examples (4 guidance headlines) | Already in news-primary.md: "What to Extract from News" table has equivalent examples |
| "do NOT extract" body bullets | Already in news-primary.md: "Do NOT Extract" section covers analyst estimates + prior period values |

---

## Verification

After all changes:

```bash
# No "forward-looking" in asset profile
grep -ci "forward-looking" .claude/skills/extract/assets/news.md
# Expected: 0

# No extraction instructions in asset profile
grep -ci "DO NOT extract\|do NOT extract" .claude/skills/extract/assets/news.md
# Expected: 0

# No hardcoded channel filter in asset profile (channel reference is OK)
grep -c "Pre-LLM Gate\|HIGH.*likelihood\|MODERATE.*likelihood" .claude/skills/extract/assets/news.md
# Expected: 0

# Channel filter exists in intersection file
grep -c "Channel Filter" .claude/skills/extract/types/guidance/assets/news-primary.md
# Expected: >= 1

# Fulltext keywords exist in intersection file
grep -c "guidance OR outlook" .claude/skills/extract/types/guidance/assets/news-primary.md
# Expected: >= 1

# All 13 properties documented
grep -c "n\.\(id\|title\|body\|teaser\|created\|updated\|url\|authors\|channels\|tags\|market_session\|returns_schedule\|embedding\)" .claude/skills/extract/assets/news.md
# Expected: 13

# Relationships documented
grep -c "INFLUENCES" .claude/skills/extract/assets/news.md
# Expected: >= 4

# No internal duplicates
grep -c "given_date" .claude/skills/extract/assets/news.md
# Expected: 1 (was 2)

# 6F generic query exists
grep -c "6F" .claude/skills/extract/assets/news-queries.md
# Expected: >= 1
```

---

## Risk Analysis

### Risk 1: Channel filter removal from asset profile breaks existing guidance extraction
**Severity**: None. The guidance agent loads news-primary.md (slot 4) which will contain the channel filter after Change 7. The agent sees the same channels — just from a different file in its context.

### Risk 2: Future types miss channel documentation
**Severity**: None (improved). Current state: only 6 channels documented. After change: ALL 22 channels documented with counts and content types. A new type can immediately identify relevant channels.

### Risk 3: Neutral title pattern is less helpful
**Severity**: Low. The guidance-specific examples still exist in news-primary.md's "What to Extract from News" table. The asset profile's role is to describe data structure, not provide extraction examples.

### Risk 4: `core-contract.md` cross-reference (C7)
**Severity**: Low (accepted, not fixed in this plan). All 5 asset profiles reference guidance's core-contract.md for basis/segment rules. This is a known coupling accepted during v1.1 dedup. Fix deferred to when a second extraction type is implemented (reveals whether rules are truly shared or type-specific).

---

## Implementation Order

| Phase | Files | Changes |
|-------|-------|---------|
| 1 | `news.md` | Expand Data Structure (13 fields), add Relationships, add Indexes |
| 2 | `news.md` | Replace Channel Filter with Channel Reference |
| 3 | `news.md` | Neutralize Scan Scope (title + body) |
| 4 | `news.md` | Deduplicate, remove stale sections, update version |
| 5 | `news-primary.md` | Add Channel Filter + Fulltext Keywords sections |
| 6 | `news-queries.md` | Neutralize descriptions, add 6F generic query |
| 7 | Verify | Run verification grep commands |

Single commit. All changes are prompt-file-only.

---

*Plan created 2026-03-08. Depends on: `total-contagion-fix.md` (landed `84fc97f`). Ground truth from Neo4j queries same day. Scope: 3 files, ~8 edits.*
