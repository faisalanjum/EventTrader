# 10-Q Decontamination Plan

Decontaminate 10-Q asset files so they meet the same 3 requirements applied to News decontamination.

## Requirements

1. **Any new extraction type works without new queries** — the 10-Q query surface (5A-5H) is generic enough that a future type can use it without adding asset-specific queries.
2. **Zero contamination** — the generic asset profile (`10q.md`) and queries (`10q-queries.md`) contain zero guidance-specific content. Other job types read only asset-level source facts.
3. **Guidance × 10-Q immediately executable** — `10q-primary.md` contains everything the guidance agent needs beyond the shared type-level logic, reusing `primary-pass.md` and `core-contract.md` at slots 1-2.

## Ground Truth (from Neo4j, 2026-03-09)

### 10-Q Report Nodes: 6,033 total

| Property | Coverage | Notes |
|----------|----------|-------|
| `accessionNo` | 100% | Documented ✓ |
| `id` | 100% | Documented ✓ |
| `created` | 100% | Documented ✓ |
| `formType` | 100% | Documented ✓ |
| `periodOfReport` | 100% | Documented ✓ |
| `market_session` | 100% | **UNDOCUMENTED** — post_market 62%, in_market 22%, pre_market 14%, market_closed 2% |
| `isAmendment` | 100% | Not documented, but 0 amendments exist for 10-Q |
| 19 other properties | varies | Metadata/internal (cik, links, xbrl_status, etc.) — not needed for extraction |

### Content Layer Coverage

| Layer | Count | % of 6,033 |
|-------|-------|-----------|
| Sections (ExtractedSectionContent) | 6,032 | 99.98% |
| Financial Statements | 5,845 | 96.9% |
| Exhibits | 2,224 | 36.9% |
| Filing Text | 176 | 2.9% |

### MD&A Coverage

MD&A present on 5,968 of 6,033 = **98.9%**. Asset profile says "~99%" — accurate.

---

## Current State Assessment

### Queries: ONE FIX NEEDED

`10q-queries.md` queries 5A-5H are fully generic — parameterized by `$accession`, `$ticker`, `$source_key`, `$start_date`, `$end_date`. No type-specific filters, no hardcoded keywords. All query logic is type-neutral.

One description has guidance vocabulary:

- **10q-queries.md:34** — `"forward-looking content"` in 5C description

### Guidance × 10-Q intersection file: PASS — already has proper content

`10q-primary.md` has what-to-extract tables, forward-looking strictness rule, quote prefix, source fields. Shared guidance logic loads from `primary-pass.md` (slot 2) and `core-contract.md` (slot 1).

### Asset profile (10q.md): FAIL — contamination across 4 categories + data structure gaps

---

## Contamination Inventory

### Category A: Guidance-specific scan instructions in generic file

**A1. Financial Statements step (10q.md:83-88)**

Current:
```
Query 5C. Look for footnotes or annotations that mention forward expectations.
The `value` field is JSON — parse for text annotations, not just numbers.

Useful `statement_type` values:
- `StatementsOfIncome` — footnotes may reference expected trends
- `StatementsOfCashFlows` — CapEx/FCF forward expectations sometimes in footnotes
```

Problem: "forward expectations", "expected trends", "CapEx/FCF forward expectations" are guidance-specific scan instructions. The asset profile should describe what the data IS, not what to look for in it.

Fix: Strip scan instructions. Keep only structural description.
```
Query 5C. The `value` field is a JSON string — parse it to access structured data and any text annotations.

Common `statement_type` values:
- `StatementsOfIncome`
- `StatementsOfCashFlows`
- `BalanceSheets`
- `StatementsOfShareholdersEquity`
```

Move to `10q-primary.md`: Add a note that financial statement footnotes may contain forward expectations (CapEx/FCF, expected trends).

**A2. Scan Scope: MD&A Section table (10q.md:109-117)**

Current:
```
| Sub-Section | Forward-Looking Likelihood | Notes |
|-------------|-------------------|-------|
| **Overview / Executive Summary** | Medium | May contain high-level outlook statements |
| **Results of Operations** | Low | Primarily backward-looking actuals |
| **Outlook / Forward-Looking** | Highest | Dedicated forward section (when present) |
| **Liquidity and Capital Resources** | Medium | CapEx/FCF forward expectations, debt targets |
| **Segment Discussion** | Medium | Segment-level outlook statements |
| **Critical Accounting Policies** | None | Skip — no extractable content |
```

Problem: The "Forward-Looking Likelihood" column is guidance framing. A "historical actuals" type would rate "Results of Operations" as HIGH, not Low. A "risk analysis" type would want "Critical Accounting Policies" (marked "None"). The notes use guidance vocabulary ("outlook statements", "forward expectations").

Fix: Replace with a structural sub-section inventory describing what each sub-section contains.
```
| Sub-Section | Typical Content |
|-------------|----------------|
| **Overview / Executive Summary** | High-level business summary and strategic context |
| **Results of Operations** | Period-over-period financial comparisons |
| **Outlook / Forward-Looking** | Management expectations for future periods (when present) |
| **Liquidity and Capital Resources** | Cash position, debt, CapEx, capital allocation |
| **Segment Discussion** | Segment-level operating results and commentary |
| **Critical Accounting Policies** | Accounting methodology descriptions |
```

**A3. Keyword-window rules (10q.md:93-97)**

Current:
```
**Keyword-window rules for fallback**:
1. Search for extraction keywords (see S10 in QUERIES.md) in the filing text
2. Extract 500-char windows around each keyword hit
3. Exclude windows from these sections: RiskFactors, LegalProceedings, QuantitativeandQualitativeDisclosuresAboutMarketRisk
4. Send only the remaining candidate windows to LLM
```

Problem: "see S10 in QUERIES.md" is a **stale reference** — verified that queries-common.md has no section 10 (stops at section 9: Fulltext / Keyword Recall). Additionally, the section exclusion list assumes guidance extraction priorities (a risk analysis type would NOT exclude RiskFactors).

Fix: Make the technique generic; the type provides its own keywords and exclusions via its intersection file.
```
**Keyword-window rules for fallback**:
1. Search for type-specific keywords (see intersection file) in the filing text
2. Extract 500-char windows around each keyword hit
3. Exclude windows from sections specified by the extraction type
4. Send only the remaining candidate windows to LLM
```

Move to `10q-primary.md`: Add the specific keyword reference and the guidance-specific section exclusion list (RiskFactors, LegalProceedings, QuantitativeandQualitativeDisclosuresAboutMarketRisk).

**A4. Zero-item result language (10q.md:101)**

Current:
```
Zero items from a 10-Q is an **acceptable result** — not an error. Many periodic
filings contain no forward-looking content beyond what was already stated in the
8-K/transcript. Return normally with empty extraction set.
```

Problem: "forward-looking content" and "8-K/transcript" are guidance-specific framing.

Fix: Make type-neutral.
```
Zero items from a 10-Q is an **acceptable result** — not an error. Not every
periodic filing contains extractable content for every extraction type. Return
normally with empty extraction set.
```

### Category B: Type-specific contract references

**B1. Basis, Segment, Quality Filters reference (10q.md:146)**

Current:
```
See core-contract.md S6 (Basis Rules), S7 (Segment Rules), S13 (Quality Filters).
```

Status: **Accepted — LOW severity.** All 5 asset profiles have this same reference. This is a known coupling accepted during the News decontamination (C7). Fix deferred to when a second extraction type is implemented, which would reveal whether these rules are truly shared or type-specific.

**B2. MD&A Context Inheritance trap (10q.md:148-151)**

Current:
```
### 10-Q Trap: MD&A Context Inheritance

MD&A sections often establish a basis context ("The following discussion is on a GAAP
basis") early, then don't restate it. When this pattern is clear and unambiguous, it's
acceptable to inherit the basis. If there's any doubt, default to `unknown`.
```

Problem: "basis context", "GAAP basis", and "default to unknown" are guidance schema concepts (basis_norm field). The behavioral fact (MD&A establishes accounting framework early) is asset-level, but the interpretation ("inherit the basis", "default to unknown") is guidance-specific.

Fix: Move entirely to `10q-primary.md`. The guidance intersection file is where basis_norm interpretation rules belong.

### Category C: Guidance-specific cross-asset assumptions

**C1. Duplicate Resolution (10q.md:154-161)**

Current:
```
10-Q filings arrive 25-40 days after the quarter end. By then, 8-K and transcript
content have already been extracted.

1. Same values already exist → deterministic ID match → MERGE is a no-op (idempotent)
2. Updated/narrowed values → different evhash16 → extraction node created
3. Never suppress extraction because 8-K/transcript "already covered it"
4. Query-time ordering handles "latest value" resolution automatically
```

Problem: "8-K and transcript content have already been extracted" and "8-K/transcript 'already covered it'" assume guidance extraction's cross-asset timeline. "evhash16" is a guidance-specific schema field.

Fix: Keep temporal facts (asset-level), neutralize dedup semantics.
```
## Temporal Context

10-Q filings arrive 25-40 days after the quarter end. Earlier sources (8-K,
transcript) for the same period may have already been processed.

If the extraction type uses deterministic IDs with MERGE-based writes, identical
content from multiple sources deduplicates automatically. Updated or refined
content produces new extraction nodes. Never suppress extraction because an
earlier source "already covered it" — the 10-Q may contain updated or more
precise content.
```

### Category D: Guidance-framed section exclusions

**D1. Sections to Exclude table (10q.md:182-183)**

Current:
```
| `RiskFactors` | Legal/risk language, not operational forward-looking content |
| `LegalProceedings` | Litigation, not forward-looking content |
```

Problem: "not operational forward-looking content" / "not forward-looking content" are guidance-specific reasons. A risk analysis type would want RiskFactors content.

Fix: Reword to neutral descriptions of what the sections contain. Add override note.
```
| `RiskFactors` | Legal and risk disclosures |
| `LegalProceedings` | Litigation and regulatory matters |
```

Add note: "These are default exclusions for the filing text fallback. Extraction types may override based on their scope."

### Category E: Query description

**E1. 5C description (10q-queries.md:34)**

Current:
```
Structured JSON data — look for footnotes/annotations with forward-looking content.
```

Fix:
```
Structured JSON data — contains financial statements and text annotations.
```

---

## Data Structure Gaps

| # | Issue | Impact |
|---|-------|--------|
| **D1** | `r.market_session` undocumented in Report Metadata table | 100% populated. 8k.md documents this field. A "market timing" type would need it. Add to Report Metadata table. |
| **D2** | FilingTextContent fields undocumented | 176 of 6,033 10-Qs (2.9%) have filing text. 8k.md documents `f.content`, `f.form_type`. Add field table for completeness. |
| **D3** | ExhibitContent fields undocumented | 2,224 of 6,033 (36.9%) have exhibits — described as "rare" but actually present on over a third. 8k.md documents `e.exhibit_number`, `e.content`. Add field table. |

---

## Changes to 10q-primary.md (absorb moved content)

Add the following sections to `10q-primary.md`:

1. **Financial Statement Scan Instructions** — note that footnotes in StatementsOfIncome and StatementsOfCashFlows may contain forward expectations (CapEx/FCF, expected trends).

2. **Filing Text Fallback: Keywords and Exclusions** — the guidance-specific keyword set for filing text window scanning, plus the section exclusion list (RiskFactors, LegalProceedings, QuantitativeandQualitativeDisclosuresAboutMarketRisk).

3. **MD&A Context Inheritance Trap** — the basis context inheritance note moved from the asset profile ("inherit basis when unambiguous, default to unknown").

---

## Scope

- **Files changed**: 3 (`10q.md`, `10q-primary.md`, `10q-queries.md`)
- **No Python/runtime changes**: trigger-extract.py, extraction_worker.py unchanged
- **No schema/Neo4j changes**
- **No other asset files touched**: 10-K gets its own independent pass

---

## Severity Comparison to News

10-Q contamination is **lower severity** than News was. News had active filtering mechanisms (hardcoded channels, fulltext keywords) that would EXCLUDE content for non-guidance types. 10-Q has vocabulary bias that GUIDES attention toward guidance-like content but doesn't hard-filter. The two HIGH items are:

- **Scan Scope "Forward-Looking Likelihood" column** — biases scan prioritization for all types
- **Stale S10 reference** — sends the agent to a non-existent query section in a fallback path

---

## Verification

After applying:

```bash
# No guidance vocabulary in asset profile (excluding version footer)
rg -i "forward-looking|forward expectations|outlook statement|expected trends" .claude/skills/extract/assets/10q.md
# Expected: 0

# No stale references
rg "S10|S13|S6|S7" .claude/skills/extract/assets/10q.md
# Expected: 0 (except accepted core-contract.md line)

# No guidance vocabulary in queries
rg -i "forward-looking" .claude/skills/extract/assets/10q-queries.md
# Expected: 0

# Moved content present in intersection file
rg "Context Inheritance|RiskFactors|forward expectations" .claude/skills/extract/types/guidance/assets/10q-primary.md
# Expected: >= 2

# market_session documented
rg "market_session" .claude/skills/extract/assets/10q.md
# Expected: >= 1
```

---

*Plan created 2026-03-09. Ground truth from Neo4j queries same day. Scope: 3 files.*
