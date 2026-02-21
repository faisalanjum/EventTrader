# 10-Q / 10-K Extraction Profile

Per-source extraction rules for 10-Q and 10-K periodic filings. Loaded by the guidance extraction agent when `SOURCE_TYPE = 10q` or `SOURCE_TYPE = 10k`.

## Data Structure

10-Q/10-K content comes from multiple layers. Use the content inventory query (4G) first to determine what exists.

| Layer | Node Label | Relationship | Priority |
|-------|-----------|--------------|----------|
| **MD&A Section** | ExtractedSectionContent | `Report-[:HAS_SECTION]->` | Primary — the designated scan scope for guidance |
| **Financial Statements** | FinancialStatementContent | `Report-[:HAS_FINANCIAL_STATEMENT]->` | Supplementary — structured JSON, check footnotes |
| **Filing Text** | FilingTextContent | `Report-[:HAS_FILING_TEXT]->` | Bounded fallback — full filing text |

### Report Metadata (from Report node)

| Field | Type | Example |
|-------|------|---------|
| `r.accessionNo` | String | `0000320193-25-000012` |
| `r.id` | String | Same as accessionNo |
| `r.created` | String (ISO) | `2025-02-28T16:00:00Z` |
| `r.formType` | String | `10-Q` or `10-K` |
| `r.periodOfReport` | String | `2024-12-28` |

### ExtractedSectionContent Fields

| Field | Type | Description |
|-------|------|-------------|
| `s.section_name` | String | Canonical section key (see table below) |
| `s.content` | String | Section text content |

### FinancialStatementContent Fields

| Field | Type | Description |
|-------|------|-------------|
| `fs.statement_type` | String | `BalanceSheets`, `StatementsOfIncome`, `StatementsOfCashFlows`, `StatementsOfShareholdersEquity` |
| `fs.value` | String | JSON structured financial data |

---

## Critical Database Reality

### 10-Q MD&A Coverage: ~99%

10-Q filings have excellent MD&A extraction. The primary scan path works reliably.

### 10-K MD&A Coverage: ~98%

10-K filings have high MD&A extraction (~98%). The same primary scan path (query 5B) works for both 10-Q and 10-K.

**Note**: 10-K MD&A uses a different `section_name` variant with a Unicode curly apostrophe (U+2019). Query 5B handles both variants automatically via `STARTS WITH` + `CONTAINS` matching.

**Fallback for rare missing MD&A** (~2% of 10-K):
1. Check for exhibits (some 10-K filings have press releases attached)
2. If no exhibits, use financial statement footnotes (query 5C) as supplementary source
3. As last resort, use filing text (query 4F) with keyword-window scanning
4. Zero guidance from a 10-K is an acceptable result — do not force extraction

### MD&A Section Name Variants

Two naming variants exist for the same section. Query 5B checks both:

| Variant | Form Type | Count |
|---------|-----------|-------|
| `ManagementDiscussionandAnalysis...` (no apostrophe) | 10-Q | ~5,980 |
| `Management\u2019sDiscussionandAnalysis...` (curly apostrophe U+2019) | 10-K | ~2,260 |

Use query 5D (all sections for report) if neither variant matches — the section may use a company-specific naming convention.

---

## Content Fetch Order

### Step 1: Check Content Inventory

Run query 4G to see what content types exist for the filing.

### Step 2: Fetch MD&A (Primary)

Query 5B. This is the designated primary scan scope for 10-Q/10-K guidance.

### Step 3: Financial Statements (Supplementary)

Query 5C. Look for footnotes or annotations that mention forward expectations. The `value` field is JSON — parse for text annotations, not just numbers.

Useful `statement_type` values:
- `StatementsOfIncome` — footnotes may reference expected trends
- `StatementsOfCashFlows` — CapEx/FCF forward guidance sometimes in footnotes

### Step 4: Filing Text (Bounded Fallback)

Query 4F. Only if MD&A returned zero guidance. Scan with keyword windows — do NOT process the entire filing text through LLM.

**Keyword-window rules for fallback**:
1. Search for guidance keywords (see §10 in QUERIES.md) in the filing text
2. Extract 500-char windows around each keyword hit
3. Exclude windows from these sections: `RiskFactors`, `LegalProceedings`, `QuantitativeandQualitativeDisclosuresAboutMarketRisk`
4. Send only the remaining candidate windows to LLM

### Step 5: Zero-Guidance Result

Zero guidance from a 10-Q/10-K is an **acceptable result** — not an error. Many periodic filings contain no forward guidance beyond what was already stated in the 8-K/transcript. Return normally with empty extraction set.

---

## Scan Scope: MD&A Section

MD&A is structured but varies by company. Common sub-sections to scan:

| Sub-Section | Guidance Likelihood | Notes |
|-------------|-------------------|-------|
| **Overview / Executive Summary** | Medium | May contain high-level outlook statements |
| **Results of Operations** | Low | Primarily backward-looking actuals |
| **Outlook / Forward-Looking** | Highest | Dedicated forward section (when present) |
| **Liquidity and Capital Resources** | Medium | CapEx/FCF guidance, debt targets |
| **Segment Discussion** | Medium | Segment-level outlook statements |
| **Critical Accounting Policies** | None | Skip — no guidance content |

### What to Extract from MD&A

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

---

## Do NOT Extract

1. **Past period results** — MD&A is primarily backward-looking; only extract statements about FUTURE periods
2. **Boilerplate / legal / risk-heavy text** — skip RiskFactors, LegalProceedings, and generic cautionary language
3. **Accounting policy descriptions** — not forward guidance
4. **Repeated guidance** — if the same guidance was already extracted from 8-K or transcript for this period, the deterministic ID (§2A) handles dedup automatically via MERGE. Do not manually skip.

---

## Period Identification

### Common Patterns in 10-Q/10-K

| Source Text | period_type | Derivation |
|-------------|-------------|------------|
| "For fiscal year 2025" | annual | From source |
| "For the remainder of fiscal 2025" | annual | fiscal_year from text |
| "In the second half of fiscal 2025" | half | fiscal_year from text |
| "For the next twelve months" | annual | From filing date |
| "Over the next several years" | long-range | Best-effort |
| "In Q3 2025" | quarter | Direct |

### given_date

Always `r.created` (the filing date). This is when the guidance became public in the periodic filing.

### source_key

Always `"MD&A"` for 10-Q/10-K extractions — regardless of which sub-section within MD&A the guidance was found.

If guidance was found in financial statement footnotes (fallback), use `"footnotes"` as source_key. If from filing text fallback, use `"filing_text"`.

---

## Basis, Segment, Quality Filters

See SKILL.md [§6 Basis Rules](../SKILL.md#6-basis-rules), [§7 Segment Rules](../SKILL.md#7-segment-rules), [§13 Quality Filters](../SKILL.md#13-quality-filters).

### 10-Q/10-K Trap: MD&A Context Inheritance

MD&A sections often establish a basis context ("The following discussion is on a GAAP basis") early, then don't restate it. When this pattern is clear and unambiguous, it's acceptable to inherit the basis. If there's any doubt, default to `unknown`.

### 10-Q/10-K Quality Addition: Forward-Looking Strictness

MD&A is predominantly backward-looking. Apply forward-looking filter strictly — target period must be after `r.created`. Zero guidance from a periodic filing is an acceptable result; do not lower thresholds to force extraction. Filter MD&A boilerplate aggressively.

---

## Duplicate Resolution

10-Q/10-K filings arrive 25-45 days after the earnings event. By then, 8-K and transcript guidance have already been extracted.

1. **Same values already exist** → deterministic ID match → MERGE is a no-op (idempotent)
2. **Updated/narrowed values** → different `evhash16` → new GuidanceUpdate node created (this IS new guidance)
3. **Never suppress extraction** because 8-K/transcript "already covered it" — the 10-Q/10-K may contain updated or more precise values
4. Query-time ordering (§8 `ORDER BY given_date, id`) handles "latest value" resolution automatically

---

## Empty Content Handling

| Scenario | Action |
|----------|--------|
| MD&A section exists, has content | Process normally — standard case |
| MD&A section missing (especially 10-K) | Try financial statement footnotes, then bounded filing text fallback |
| MD&A exists but zero guidance found | Acceptable result — return empty extraction set |
| No content at all (all layers empty) | Return `EMPTY_CONTENT\|10q\|MD&A` or `EMPTY_CONTENT\|10k\|MD&A` |

---

## Sections to Exclude

When scanning filing text (fallback), explicitly exclude these sections:

| section_name | Reason |
|-------------|--------|
| `RiskFactors` | Legal/risk language, not operational guidance |
| `LegalProceedings` | Litigation, not forward guidance |
| `QuantitativeandQualitativeDisclosuresAboutMarketRisk` | Market risk analysis |
| `Controls` / `ControlsandProcedures` | Internal controls discussion |
| `Signatures` | Legal signatures |
| `ExhibitIndex` | Filing metadata |

Use query 5E to check if RiskFactors exists and its size, to inform the exclusion.

---

---

## 10-K vs 10-Q Differences

| Aspect | 10-Q | 10-K |
|--------|------|------|
| Filing frequency | Quarterly (Q1-Q3) | Annual (FY end) |
| MD&A availability | ~99% have extracted MD&A | ~98% (curly apostrophe variant in section_name) |
| Guidance frequency | Moderate | Low (annual outlook, if any) |
| Typical guidance | Next-quarter or remainder-of-year outlook | Full-year or multi-year targets |
| Arrival timing | t+25 to t+40 days after quarter end | t+45 to t+60 days after FY end |
| `source_type` value | `10q` | `10k` |

---
*Version 1.2 | 2026-02-21 | Fixed 10-K MD&A coverage: ~98% (was incorrectly documented as ~0%). Fixed section_name apostrophe variant (curly U+2019, not straight). Query 5B now uses STARTS WITH + CONTAINS for robust matching.*
