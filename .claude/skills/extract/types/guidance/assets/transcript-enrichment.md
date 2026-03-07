# Guidance x Transcript — Enrichment Pass

Rules for enriching/discovering guidance from transcript Q&A exchanges.
Loaded at slot 4 by the enrichment agent.

## Scan Scope — Transcript

Process all Q&A content from the transcript. Do not skip any exchange.
Q&A often reveals guidance not present in prepared remarks.

## Speaker Hierarchy (Guidance Priority)

| Priority | Speaker | What to Look For |
|----------|---------|-----------------|
| 1 (Highest) | **CFO** (prepared remarks) | FORMAL GUIDANCE — revenue/margin/EPS guidance with specific numbers, ranges, or YoY comparisons. This is where official guidance statements live. |
| 2 | **CFO** (Q&A responses) | Clarifications, additional detail, segment-level breakdowns, GAAP vs non-GAAP distinctions, "comfortable with consensus" signals |
| 3 | **CEO** (prepared remarks) | Strategic outlook, market positioning, product momentum, qualitative direction |
| 4 | **CEO** (Q&A responses) | Strategic context, long-range targets, acquisition/product guidance |
| 5 | **Other executives** (Q&A) | Segment-specific guidance (e.g., VP of Cloud, Head of Devices) |
| Skip | **Operator** | Procedural remarks only (introductions, instructions). No guidance content. |

↳ Priority sets precedence for conflicts, not scope. Extract guidance from all speakers.

## Why Q&A Matters

Q&A is often MORE valuable for guidance than prepared remarks because:
1. Analysts probe for specifics not in prepared remarks
2. Management reveals segment-level detail under questioning
3. Geographic/product breakdowns emerge
4. GAAP vs non-GAAP clarifications are made
5. "Comfortable with consensus" signals (implied guidance)
6. Conditional guidance appears ("if X, then we'd expect Y")
7. Sensitivity bounds are revealed ("plus or minus 100 bps")

## Q&A Extraction Steps

1. **Process every exchange** — do not skip any Q&A
2. **Focus on management responses** — analyst questions provide context, but guidance comes from management answers
3. **Look for CFO responses** — these carry highest guidance authority in Q&A
4. **Capture analyst name** — use in `section` field for citation (e.g., `Q&A #3 (analyst name)`)

## What to Extract from Q&A

| Signal | Example | Extract? |
|--------|---------|----------|
| Specific numbers in response | "For the June quarter, we're looking at OpEx of $14.5-14.7 billion" | Yes |
| Consensus comfort | "We're comfortable with where the Street is" | Yes: `derivation=implied`, note in qualitative field |
| Segment detail | "Services growth will be in the mid-to-high teens" | Yes: segment="Services", qualitative |
| Conditional guidance | "Assuming no FX headwinds, we'd see 2% higher growth" | Yes: note condition in `conditions` field |
| Clarification of PR guidance | "To be more specific, that's on a non-GAAP basis" | Yes: updates basis for the PR guidance item |
| Capital announcement or return decision | "We authorized a new buyback program", "we increased the dividend" | Yes: material capital/return announcement |
| Analyst estimate repetition | "Your consensus shows $3.50" | No: analyst estimate, not company guidance |
| Generic positive sentiment | "We feel good about the business" | No: no quantitative anchor |

## Q&A Quote Prefix

All guidance extracted from Q&A MUST use quote prefix: `[Q&A]`

Example: `[Q&A] We are targeting services growth in the mid-to-high teens year over year`

## Section Field Format

For Q&A guidance, the `section` field should identify where in the Q&A:
- `Q&A #1` (by sequence number)
- `Q&A (Shannon Cross)` (by analyst name, when available)
- `Q&A #3 (Ben Reitzes)` (both, preferred)

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
