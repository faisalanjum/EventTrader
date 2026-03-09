# Guidance × News — Primary Pass

Rules for extracting guidance from Benzinga news articles. Loaded at slot 4 by the primary agent.

## Routing — News Content Fetch

Use the content fetch order in the asset profile (news.md):
1. Query 6A (single item by ID)
2. For batch processing: 6C with caller-supplied channels

Recommended guidance channels for batch discovery:
- Core: `Guidance`, `Earnings`, `Previews`, `Management`
- Optional recall expansion: `Earnings Beats`, `Earnings Misses`

Channel matches are a recall aid only. They do not prove the article contains company-issued guidance.

Apply empty-content rules from the asset profile.

## Supplementary Fulltext Recall

When using common query `9F` for News fulltext recall, start with:

`guidance OR outlook OR expects OR "full year" OR "fiscal year"`

## Attribution Rule (News-Specific)

News articles mix company statements with analyst commentary, reporter narration, and third-party quotes in the same item.

Extract only statements that the article attributes to company management or the company itself. Skip values attributed to analysts, consensus, the Street, price targets, rating actions, or unnamed third parties.

When attribution is ambiguous, skip the item. Err toward precision over recall for attribution.

## Title / Body / Teaser Handling

- Always inspect the title.
- Inspect the body when present.
- Use the teaser only as supporting text or when it contains the clearest quoted guidance language.
- Do not create duplicate items from the same article just because the headline, teaser, and body restate the same guidance.

## Prior Period Values

| Signal | Example | Action |
|--------|---------|--------|
| "(Prior $X)" | "Revenue guidance of $95B (Prior $93B)" | Extract $95B ONLY; $93B is historical context |
| "compared to prior guidance of" | "Raised to $3.50 from prior $3.20" | Extract $3.50 ONLY |
| "previous outlook" | "Previous outlook was $90-92B" | Do not extract as new guidance |

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

## Withdrawn / Suspended Guidance

If the news item says the company withdrew, suspended, or pulled guidance/outlook, extract a qualitative-only item with `qualitative = "withdrawn"` and leave numeric fields null. Do not reuse prior values from earlier guidance.

## Quote Prefix

All guidance extracted from news MUST use quote prefix: `[News]`

Example: `[News] Apple Expects Q2 Revenue Between $94B-$98B`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"news"` |
| `source_key` | `"title"` (canonical news source key, even when guidance was found in body or teaser) |
| `given_date` | `n.created` (the news publication date) |
| `source_refs` | Empty array `[]` — news items have no sub-source nodes. |
| `section` | `"title"` when quote came from headline, `"body"` when from article body, `"teaser"` when quote came from teaser |
