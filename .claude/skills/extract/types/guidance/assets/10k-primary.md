# Guidance × 10-K — Primary Pass

Rules for extracting guidance from 10-K annual filings. Loaded at slot 4 by the primary agent.

## Routing — 10-K Content Fetch

Use the content fetch order in the asset profile (10k.md):
1. Query 5F (inventory) → 5B (MD&A section — primary)
2. Fallbacks: 5C (financial statement footnotes), 5H (exhibits), 5G (filing text)

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
| `source_key` | `"MD&A"` (always, regardless of which sub-section). If from financial statement footnotes: `"footnotes"`. If from filing text fallback (5G): `"filing_text"`. If from exhibit fallback (5H): use the exhibit number (e.g., `"EX-99.1"`). |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Empty array `[]` — 10-K sections have no sub-source nodes. |
| `section` | Sub-section name where content was found (e.g., `"MD&A"`, `"footnotes"`) |
