# Guidance × 10-K — Primary Pass

Rules for extracting guidance from 10-K annual filings. Loaded at slot 4 by the primary agent.

## Routing — 10-K Content Fetch

Use the content fetch order in the asset profile (10k.md):
1. Query 5F (inventory) → 5B (MD&A section — primary)
2. If 5B returns no row, use 5D → 5I to inspect and fetch another narrative section before raw filing text
3. Fallbacks: 5C (financial statement payloads), 5H (exhibits), 5G (filing text)

Apply empty-content rules from the asset profile.

## Periodic Filing Caution

10-Ks are mostly retrospective. Zero guidance from an annual filing is a valid result. Do not lower thresholds to force extraction.

## Section Preference

- Prefer canonical MD&A when it exists.
- If MD&A is missing, inspect other long narrative sections via 5D → 5I before resorting to raw filing text.
- Skip these section types as primary guidance targets: `RiskFactors`, `LegalProceedings`, `QuantitativeandQualitativeDisclosuresaboutMarketRisk`, `ControlsandProcedures`, `ExhibitsandFinancialStatementSchedules`, `Signatures`.
- Use financial statement payloads for note text or embedded narrative context, not just numeric tables.
- Use raw filing text only as bounded fallback content.

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

## Basis Context Inheritance

MD&A sometimes establishes basis context once and then reuses it across the section. Inherit basis only when the connection is explicit and unambiguous. If there is any doubt, default to `basis_norm = "unknown"`.

## Filing Text Fallback

When using 5G, do not send the full filing text to the model. Use the guidance keyword seed from `guidance-queries.md` Section 10 to carve bounded windows first.

## Cross-Asset Dedup

Never suppress a 10-K extraction because similar guidance already appeared in an 8-K or transcript. Deterministic IDs and evidence hashes handle no-op merges versus genuinely updated values.

## Quote Prefix

All guidance extracted from 10-K MUST use quote prefix: `[10-K]`

Example: `[10-K] We expect fiscal 2026 revenue between $400 billion and $420 billion`

## Source Fields

| Field | Value |
|-------|-------|
| `source_type` | `"10k"` |
| `source_key` | Canonical MD&A via 5B: `"MD&A"`. Other section text via 5I: `s.section_name`. Financial statement payloads via 5C: `fs.statement_type`. Filing text via 5G: `"filing_text"`. Exhibits via 5H: `e.exhibit_number`. |
| `given_date` | `r.created` (the filing date) |
| `source_refs` | Empty array `[]` for the current guidance write path. |
| `section` | Canonical MD&A via 5B: `"MD&A"`. Otherwise use the actual section / statement / exhibit identifier that produced the quote. |
