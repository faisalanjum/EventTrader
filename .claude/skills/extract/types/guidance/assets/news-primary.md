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
| `section` | `"title"` when quote came from headline, `"body"` when from article body |
