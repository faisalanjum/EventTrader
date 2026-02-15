---
name: evidence-standards
description: Anti-hallucination and source traceability rules for all data sub-agents. Prompt-level guard — reduces hallucination risk, does not guarantee correctness.
user-invocable: false
---

# Evidence Standards

Universal rules for ALL data sub-agents. Apply regardless of source (Neo4j, Benzinga, Perplexity, Alpha Vantage, any future source).

## Rule 1: Source-Only Data

Return ONLY values present in your tool/query output. Never supplement with training knowledge.

- If your query returned it: include it
- If your query did not return it: report as gap
- If you "know" something but your source did not return it: do NOT include it

## Rule 2: Exact Values

Return source values exactly as received. No rounding, no paraphrasing.

- WRONG: ~$2, "about 84%", "revenue grew strongly"
- RIGHT: $2.03, 84.14%, "revenue: $345.6M"

## Rule 3: Traceability

Every `data[]` item must include at least one stable source reference so the value can be traced back to its origin. Use your source's existing identifier fields — do not create ad-hoc traceability keys. Examples:

- Neo4j: `id`, `accession_no`, or composite key already in query results
- API: record `id` or `url` from the provider response
- External: citation URL or ticker + date + endpoint

This works with pit-envelope's existing `available_at` and `available_at_source` fields. No additional date field needed.

## Rule 4: Derived Values

If you compute, transform, or normalize a value (e.g., surprise percentages, timezone conversions, aggregations), mark it as derived and cite the inputs used.

- A computed field (like `surprise_pct`) must reference the source values and their origins
- WRONG: returning a computed value with no indication it was derived
- RIGHT: indicating the value is derived, with inputs: actual from `Report:{accession}`, consensus from `perplexity search`

## Domain Boundary

Stay in your agent's designated domain. Cross-domain date-anchor joins are allowed (e.g., using a Transcript date to scope News queries). Cross-domain content extraction is not — redirect to the correct agent.
