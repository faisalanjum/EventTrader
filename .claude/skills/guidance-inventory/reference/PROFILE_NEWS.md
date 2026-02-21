# News Extraction Profile

Per-source extraction rules for Benzinga news items. Loaded by the guidance extraction agent when `SOURCE_TYPE = news`.

## Data Structure

News items are single nodes with text fields. No sub-nodes or content hierarchy.

| Field | Type | Description |
|-------|------|-------------|
| `n.id` | String | Unique Benzinga news ID |
| `n.title` | String | Headline — often contains complete guidance. Always present. |
| `n.body` | String | Article body. May be empty (~12% of items lack body text). |
| `n.teaser` | String | Short summary. Often truncated version of body. |
| `n.created` | String (ISO) | Publication datetime |
| `n.channels` | String | Comma-separated Benzinga channels (JSON-like string) |
| `n.tags` | String | Topic tags |

---

## Channel Filter (Pre-LLM Gate)

Apply BEFORE sending any content to the LLM. This is a hard gate — do not process news items that fail the channel filter.

### Primary Channels (HIGH guidance likelihood)

| Channel | Typical Count | Content |
|---------|--------------|---------|
| `Guidance` | ~21,000 | Company forward-looking statements |
| `Earnings` | ~49,000 | Earnings results, often includes outlook |

### Secondary Channels (MODERATE guidance likelihood)

| Channel | Typical Count | Content |
|---------|--------------|---------|
| `Previews` | ~587 | Pre-earnings analysis, may include prior guidance |
| `Management` | ~4,400 | Management commentary, strategic outlook |
| `Earnings Beats` | ~5,800 | Beat/miss context, sometimes includes revised outlook |
| `Earnings Misses` | ~2,700 | Beat/miss context, sometimes includes revised outlook |

### Channel Filter Query (6B in QUERIES.md)

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $start_date AND n.created <= $end_date
  AND (n.channels CONTAINS 'Guidance'
    OR n.channels CONTAINS 'Earnings'
    OR n.channels CONTAINS 'Previews'
    OR n.channels CONTAINS 'Management')
RETURN n.id, n.title, n.created, n.channels
ORDER BY n.created
```

### Supplementary Fulltext Recall (9F in QUERIES.md)

After channel-filtered extraction, run fulltext search for items that may have been missed:
```
guidance OR outlook OR expects OR forecast OR "full year" OR "fiscal year"
```
Cross-check fulltext hits against already-processed IDs to avoid re-extraction.

---

## Scan Scope

Process BOTH title and body for every news item that passes the channel filter.

### Title (Always Process)

Titles frequently contain complete guidance in a structured pattern:

```
{Company} {Action Verb} {Metric} {Value/Range} {Period}
```

Examples:
- `Apple Expects Q2 Revenue Between $94B-$98B`
- `Tesla Raises Full-Year Delivery Guidance To 2M Units`
- `Microsoft Reaffirms FY25 Revenue Outlook At $245B`
- `Amazon Lowers Q3 Operating Income Guidance To $11.5B-$15B`

### Body (Process When Available)

Body text may contain:
- Additional metrics not in the title
- Prior guidance values for context (do NOT extract as new guidance)
- GAAP vs non-GAAP clarification
- Segment-level detail
- Conditions or assumptions
- Analyst consensus comparisons (DO NOT extract)

---

## What to Extract

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

---

## Do NOT Extract

### Analyst Estimates (CRITICAL)

The single most important rule for news extraction. Benzinga frequently mixes company guidance with analyst consensus in the same article.

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

- Generic positive/negative sentiment without numbers: "Company optimistic about growth"
- Pure actuals: "Q1 revenue came in at $124B"
- Analyst ratings: "Upgraded to Buy with $200 target"
- Price target changes: "Price target raised to $250"

---

## Reaffirmation Handling (§3 News Guardrail)

When news language contains reaffirmation verbs:

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

---

## Period Identification

### Common Patterns in News

| Source Text | period_type | fiscal_year | fiscal_quarter |
|-------------|-------------|-------------|----------------|
| "Q2 revenue" | quarter | Derive from context | Q2 |
| "full-year outlook" | annual | From text or derive from date | `.` |
| "FY25 guidance" | annual | 2025 | `.` |
| "second half" | half | From text | `.` |
| "next quarter" | quarter | Derive from date + FYE | Next fiscal Q |
| "fiscal 2026" | annual | 2026 | `.` |

### given_date

Always `n.created` (the news publication date). This is the point-in-time stamp for when the guidance became public via news.

### source_key

Always `"title"` for news items — regardless of whether guidance was found in title or body. This is the canonical source_key for the news source type per spec §3.

---

## Basis, Segment, Quality Filters

See SKILL.md [§6 Basis Rules](../SKILL.md#6-basis-rules), [§7 Segment Rules](../SKILL.md#7-segment-rules), [§13 Quality Filters](../SKILL.md#13-quality-filters).

### News-Specific: Basis Defaults to Unknown

Most news guidance defaults to `unknown` basis. This is correct — the transcript or 8-K source provides the authoritative basis.

### News-Specific: given_date

Always `n.created` (the news publication date).

### News-Specific: source_key

Always `"title"` for news items — regardless of whether guidance was found in title or body.

---

## Duplicate Resolution

News items frequently duplicate guidance from other sources (8-K, transcript). This is expected and handled by deterministic IDs:

1. **Same values from news + 8-K** → different `source_id` and `source_type` → different `GuidanceUpdate.id` → both stored (provenance preserved)
2. **News paraphrases 8-K** → values may differ slightly (rounding) → different `evhash16` → both stored
3. **Multiple news articles for same event** → if exact same values, `evhash16` matches → MERGE is idempotent. If different articles report slightly different values, each gets its own node.
4. **Cross-source dedup is NOT performed** — each source creates its own GuidanceUpdate node. Query-time ordering (§8) handles "latest value" resolution.

---

## Empty Content Handling

| Scenario | Action |
|----------|--------|
| Title present, body null/empty | Process title only — valid extraction (common case) |
| Title present, body present | Process both — standard case |
| BOTH title and body are null/empty | Return `EMPTY_CONTENT\|news\|full` |

---

---
*Version 1.1 | 2026-02-21 | Deduplicated basis/segment/quality sections → SKILL.md references. Kept news-specific: channel filter, analyst exclusion, reaffirmation handling.*
