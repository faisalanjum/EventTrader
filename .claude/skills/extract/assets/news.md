# News Extraction Profile

Per-source extraction rules for Benzinga news items. Loaded by the extraction agent when `ASSET = news`.

## Asset Metadata
- sections: full
- label: News
- neo4j_label: News

## Data Structure

News items are single nodes with text fields. No sub-nodes or content hierarchy.

| Field | Type | Description |
|-------|------|-------------|
| `n.id` | String | Unique Benzinga news ID |
| `n.title` | String | Headline — often contains complete forward-looking content. Always present. |
| `n.body` | String | Article body. May be empty (~12% of items lack body text). |
| `n.teaser` | String | Short summary. Often truncated version of body. |
| `n.created` | String (ISO) | Publication datetime |
| `n.channels` | String | Comma-separated Benzinga channels (JSON-like string) |
| `n.tags` | String | Topic tags |

---

## Channel Filter (Pre-LLM Gate)

Apply BEFORE sending any content to the LLM. This is a hard gate — do not process news items that fail the channel filter.

### Primary Channels (HIGH forward-looking content likelihood)

| Channel | Typical Count | Content |
|---------|--------------|---------|
| `Guidance` | ~21,000 | Company statements |
| `Earnings` | ~49,000 | Earnings results, often includes outlook |

### Secondary Channels (MODERATE forward-looking content likelihood)

| Channel | Typical Count | Content |
|---------|--------------|---------|
| `Previews` | ~587 | Pre-earnings analysis |
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

Titles frequently contain complete forward-looking content in a structured pattern:

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
- Prior values for context (do NOT extract as new items)
- GAAP vs non-GAAP clarification
- Segment-level detail
- Conditions or assumptions
- Analyst consensus comparisons (DO NOT extract)

---

## Period Identification

### Common Patterns in News

| Source Text | period_type | fiscal_year | fiscal_quarter |
|-------------|-------------|-------------|----------------|
| "Q2 revenue" | quarter | Derive from context | Q2 |
| "full-year outlook" | annual | From text or derive from date | `.` |
| "FY25 outlook" | annual | 2025 | `.` |
| "second half" | half | From text | `.` |
| "next quarter" | quarter | Derive from date + FYE | Next fiscal Q |
| "fiscal 2026" | annual | 2026 | `.` |

### given_date

Always `n.created` (the news publication date). This is the point-in-time stamp for when the content became public via news.

### source_key

Always `"title"` for news items — regardless of whether content was found in title or body. This is the canonical source_key for the news source type per spec.

---

## Basis, Segment, Quality Filters

See core-contract.md S6 (Basis Rules), S7 (Segment Rules), S13 (Quality Filters).

### News-Specific: Basis Defaults to Unknown

Most news extraction defaults to `unknown` basis. This is correct — another source type provides the authoritative basis.

### News-Specific: given_date

Always `n.created` (the news publication date).

### News-Specific: source_key

Always `"title"` for news items — regardless of whether content was found in title or body.

---

## Duplicate Resolution

News items frequently duplicate content from other sources (8-K, transcript). This is expected and handled by deterministic IDs:

1. **Same values from news + 8-K** → different `source_id` and `source_type` → different extraction item IDs → both stored (provenance preserved)
2. **News paraphrases 8-K** → values may differ slightly (rounding) → different `evhash16` → both stored
3. **Multiple news articles for same event** → if exact same values, `evhash16` matches → MERGE is idempotent. If different articles report slightly different values, each gets its own node.
4. **Cross-source dedup is NOT performed** — each source creates its own extraction node. Query-time ordering handles "latest value" resolution.

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
