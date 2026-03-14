# 10-Q Report Reference

Complete reference for 10-Q quarterly filings in the EventMarketDB Neo4j database.

---

## Mental Model

Think of a 10-Q as a **slimmer, quarterly sibling of the 10-K**.

```
┌─────────────────────────────────────────────────────────────┐
│                        10-K (Annual)                         │
│   21 sections across 4 Parts (I-IV)                          │
│   Full business narrative + financials + governance           │
│   Average ~420 KB of section content                         │
├─────────────────────────────────────────────────────────────┤
│                        10-Q (Quarterly)                      │
│   11 sections across 2 Parts (I-II)                          │
│   Financials + MD&A + risk updates only                      │
│   Average ~170 KB of section content                         │
│   No Part III (governance) — that's only in the 10-K         │
│   No Part IV (exhibits listing) — folded into Part II        │
└─────────────────────────────────────────────────────────────┘
```

**The key intuitions:**

1. **Two Parts, not four.** A 10-Q has only Part I (Financial Information) and Part II (Other Information). It drops Part III (governance/compensation — that's annual-only) and Part IV (just an exhibit listing). This is why a 10-Q has ~11 sections vs ~21 for a 10-K.

2. **Part I is the substance.** Part I contains the 4 core sections: FinancialStatements, MD&A, Quantitative Disclosures, and Controls. This is where 95%+ of the useful content lives. Part II sections are mostly stubs or "None".

3. **The content layers are identical to 10-K.** Same 4-layer architecture (sections → financial statements → exhibits → filing text) plus XBRL. Same node types, same relationships. The difference is in what the sections contain, not how they're stored.

4. **MD&A is retrospective.** Unlike 10-K MD&A which often contains forward-looking guidance, 10-Q MD&A is primarily backward-looking — reporting on the quarter that just ended. The extraction pipeline flags this: "10-Qs are mostly retrospective — zero guidance is valid."

5. **Section keys use a different format.** 10-K uses numeric items (`'1'`, `'1A'`, `'7'`). 10-Q uses `partXitemY` lowercase format (`'part1item1'`, `'part2item1a'`). But the `section_name` values stored in Neo4j are PascalCase-no-spaces, same convention as 10-K.

6. **Filing cadence: 3 per year.** Companies file Q1, Q2, Q3 as 10-Qs. Q4 results go in the 10-K annual report. So a company with a Dec 31 fiscal year files 10-Qs for Mar 31, Jun 30, Sep 30.

7. **Two structural tiers.** ~48% of 10-Qs have all 11 sections. ~29% have 9 sections (dropping MineSafetyDisclosures and DefaultsUponSeniorSecurities — items that are "None" for most companies). Together that's 77% of filings in just two patterns.

8. **Amendments are rare.** Only 30 10-Q/A amendments exist (vs 108 for 10-K/A). Most are targeted corrections with 1-2 sections.

```
                        10-Q Content Volume

  FinancialStatements  ████████████████████████████████  78 KB avg
  MD&A                 ██████████████████████████        56 KB avg
  RiskFactors          ████████████████                  32 KB avg
  Exhibits             ██                                 3 KB avg
  QuantitativeDisc     █                                  3 KB avg
  ControlsAndProc      █                                  2 KB avg
  OtherInformation     █                                  2 KB avg
  UnregisteredSales    ▏                                  1 KB avg
  LegalProceedings     ▏                                  1 KB avg
  MineSafety           ▏                                 84 B avg
  DefaultsSenior       ▏                                 57 B avg
```

The top 3 sections (FinancialStatements, MD&A, RiskFactors) hold ~97% of all 10-Q narrative content.

---

## Inventory

| Form Type | Count | Date Range | Companies |
|-----------|-------|------------|-----------|
| 10-Q | 6,033 | 2023-01-04 → 2025-08-29 | 772 |
| 10-Q/A | 30 | 2023-03-27 → 2025-07-03 | 22 |
| **Total** | **6,063** | | |

Year distribution:

| Year | 10-Q | 10-Q/A |
|------|------|--------|
| 2023 | 2,360 | ~10 |
| 2024 | 2,093 | ~12 |
| 2025 | 1,580 (through Aug) | ~8 |

Filings per company:

| Filings | Companies | Notes |
|---------|-----------|-------|
| 9 | 28 | Non-calendar fiscal years (AAPL, QCOM, etc.) |
| 8 | 452 | Full coverage for calendar-year companies |
| 7 | 254 | Partial 2025 coverage |
| 6 | 29 | |
| ≤5 | 9 | New listings or limited history |

### Filing Seasonality

10-Q filings cluster around quarterly SEC deadlines (40-45 days after quarter end):

| Month | ~Count | Driver |
|-------|--------|--------|
| **May** | 510 | Q1 results (Mar 31 quarter) |
| **Nov** | 400 | Q3 results (Sep 30 quarter) |
| **Aug** | 390 | Q2 results (Jun 30 quarter) |
| Oct | 240 | Offset fiscal Q3 |
| Jul | 210 | Offset fiscal Q2 |
| Apr | 185 | Offset fiscal Q1 |

---

## Graph Structure

### Relationship Map

```
Report ──PRIMARY_FILER─────────→ Company                (5,886 reports)
       ──REFERENCED_IN─────────→ Company                (177 REFERENCE_ONLY reports)
       ──HAS_SECTION───────────→ ExtractedSectionContent (58,799 nodes)
       ──HAS_FINANCIAL_STATEMENT→ FinancialStatementContent (22,644 nodes)
       ──HAS_EXHIBIT───────────→ ExhibitContent          (4,916 nodes)
       ──HAS_XBRL──────────────→ XBRLNode                (5,857 nodes)
       ──INFLUENCES────────────→ MarketIndex             (1 per report)
       ──INFLUENCES────────────→ Sector                  (1 per report)
       ──INFLUENCES────────────→ Industry                (1 per report)
       ──IN_CATEGORY───────────→ AdminReport             (1 per report)
       ──HAS_FILING_TEXT────────→ FilingTextContent       (176 fallback nodes)
       ──FROM_SOURCE←───────────  GuidanceUpdate          (1 — extraction pipeline output)
```

### Report Node Properties (21 fields)

| Field | Type | Description |
|-------|------|-------------|
| `accessionNo` / `id` | String | Canonical SEC filing ID |
| `formType` | String | `10-Q` or `10-Q/A` |
| `periodOfReport` | String | Quarter end date (e.g. `2024-09-30`) |
| `created` | ISO datetime | Filing timestamp (Eastern time) |
| `isAmendment` | Boolean | `false` for 10-Q, `true` for 10-Q/A |
| `cik` | String | SEC CIK number (null for REFERENCE_ONLY) |
| `market_session` | String | `post_market` / `in_market` / `pre_market` / `market_closed` |
| `xbrl_status` | String | `COMPLETED` / `PROCESSING` / `FAILED` / `REFERENCE_ONLY` |
| `is_xml` | Boolean | Whether filing is XML format |
| `description` | String | `"Form 10-Q - Quarterly report [Sections 13 or 15(d)]"` |
| `primaryDocumentUrl` | String | SEC primary document URL |
| `linkToTxt` / `linkToHtml` / `linkToFilingDetails` | String | SEC links |
| `symbols` | String | Ticker symbol(s) |
| `entities` | String | Filing entity metadata |
| `returns_schedule` | JSON string | Return-window calculation metadata |
| `extracted_sections` | JSON string | Section extraction metadata |
| `financial_statements` | JSON string | Financial statement metadata |
| `exhibits` | JSON string | Exhibit metadata |

**Note:** 10-Q nodes have 21 properties vs 22 for 10-K. The difference: 10-Q lacks the `exhibit_contents` property (exhibits metadata is in the `exhibits` field instead).

---

## Section Structure (Layer 1)

### Source Definition

From `secReports/reportSections.py`:

```python
ten_q_sections = {
    'part1item1':  'FinancialStatements',
    'part1item2':  'ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations',
    'part1item3':  'QuantitativeandQualitativeDisclosuresAboutMarketRisk',
    'part1item4':  'ControlsandProcedures',
    'part2item1':  'LegalProceedings',
    'part2item1a': 'RiskFactors',
    'part2item2':  'UnregisteredSalesofEquitySecuritiesandUseofProceeds',
    'part2item3':  'DefaultsUponSeniorSecurities',
    'part2item4':  'MineSafetyDisclosures',
    'part2item5':  'OtherInformation',
    'part2item6':  'Exhibits',
}
```

Key differences from 10-K section keys:
- **Format**: `partXitemY` (lowercase) vs 10-K's numeric (`'1'`, `'1A'`, etc.)
- **Count**: 11 sections vs 10-K's 22
- **MD&A name**: No curly apostrophe — uses `ManagementDiscussion...` (not `Management's...`)

### The Standard 10-Q Skeleton

```
PART I — Financial Information
├── Item 1    Financial Statements                        ████████████████████████ 78 KB avg
├── Item 2    MD&A                                        ██████████████████       56 KB avg
├── Item 3    Quantitative/Qualitative Disclosures        █                         3 KB avg
└── Item 4    Controls and Procedures                     █                         2 KB avg

PART II — Other Information
├── Item 1    Legal Proceedings                           ▏                         1 KB avg
├── Item 1A   Risk Factors                                ██████████               32 KB avg
├── Item 2    Unregistered Sales of Equity Securities     ▏                         1 KB avg
├── Item 3    Defaults Upon Senior Securities             ▏                        57 B avg
├── Item 4    Mine Safety Disclosures                     ▏                        84 B avg
├── Item 5    Other Information                           █                         2 KB avg
└── Item 6    Exhibits                                    ██                        3 KB avg
```

### Section Coverage Table

| SEC Item | `section_name` | Count | Coverage | Avg Size | Max Size |
|----------|---------------|-------|----------|----------|----------|
| **Part I** | | | | | |
| I-1 | `FinancialStatements` | 5,959 | 98.8% | **78 KB** | 524 KB |
| I-2 | `ManagementDiscussionandAnalysis...` | 5,968 | 98.9% | **56 KB** | 348 KB |
| I-3 | `QuantitativeandQualitativeDisclosuresAboutMarketRisk` | 5,921 | 98.1% | 3 KB | 285 KB |
| I-4 | `ControlsandProcedures` | 6,010 | 99.6% | 2 KB | 225 KB |
| **Part II** | | | | | |
| II-1 | `LegalProceedings` | 5,780 | 95.8% | 1 KB | 129 KB |
| II-1A | `RiskFactors` | 5,739 | 95.1% | **32 KB** | 316 KB |
| II-2 | `UnregisteredSalesofEquitySecuritiesandUseofProceeds` | 5,528 | 91.6% | 1 KB | 6 KB |
| II-3 | `DefaultsUponSeniorSecurities` | 3,014 | **49.9%** | 57 B | 1 KB |
| II-4 | `MineSafetyDisclosures` | 3,112 | **51.6%** | 84 B | 4 KB |
| II-5 | `OtherInformation` | 5,606 | 92.9% | 2 KB | 467 KB |
| II-6 | `Exhibits` | 6,013 | 99.7% | 3 KB | 45 KB |

### Section Count Distribution

| Sections per Report | Reports | % | What it means |
|--------------------|---------|---|---------------|
| **11** | 2,886 | 47.9% | Full set (all 11 sections including MineSafety + Defaults) |
| **9** | 1,757 | 29.1% | Standard — drops MineSafety + Defaults |
| 10 | 206 | 3.4% | Has one of MineSafety/Defaults but not both |
| 8 | 865 | 14.3% | Drops one more optional section |
| 7 | 216 | 3.6% | |
| 6 | 90 | 1.5% | |
| ≤5 | 12 | 0.2% | Edge cases |
| 0 | 1 | 0.02% | Single extraction failure |

**77% of 10-Qs have either 11 or 9 sections.** The two dominant profiles:
- **11 sections (48%)**: Full set — all items extracted
- **9 sections (29%)**: Everything except MineSafetyDisclosures + DefaultsUponSeniorSecurities (which are "None" for most companies anyway — avg 57-84 bytes)

### Why the 10-Q Has Fewer Sections Than 10-K

The 10-Q intentionally omits sections that are annual-only disclosures:

| 10-K Has, 10-Q Does NOT | Reason |
|--------------------------|--------|
| Business (Item 1) | Annual narrative — no quarterly update needed |
| Unresolved Staff Comments (Item 1B) | Annual only |
| Cybersecurity (Item 1C) | Annual only (SEC rule specifies annual disclosure) |
| Properties (Item 2) | Annual only |
| Selected Financial Data (Item 6) | Annual only (also eliminated post-2021) |
| Changes in Accountants (Item 9) | Annual only |
| Directors & Officers (Item 10) | Part III — annual/proxy only |
| Executive Compensation (Item 11) | Part III — annual/proxy only |
| Security Ownership (Item 12) | Part III — annual/proxy only |
| Related Transactions (Item 13) | Part III — annual/proxy only |
| Accountant Fees (Item 14) | Part III — annual/proxy only |
| Exhibits Schedule (Item 15) | Part IV — annual only |

The 10-Q **does** retain: FinancialStatements, MD&A, Quantitative Disclosures, Controls, LegalProceedings, RiskFactors, and several Part II items — the sections that can meaningfully change quarter-to-quarter.

### ExtractedSectionContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `section_name` | String | Canonical section key (PascalCase, no spaces) |
| `content` | String | Full text content |
| `content_length` | String | Comma-formatted length (use `size(s.content)` for integer) |
| `filing_id` | String | Accession number back-reference |
| `form_type` | String | `10-Q` |
| `filer_cik` | String | SEC CIK |
| `filed_at` | String | ISO 8601 filing datetime |

Same schema as 10-K sections. No `sequence` or `order` property.

---

## Financial Statement Content (Layer 2)

### Coverage

| `statement_type` | Count | Coverage | Avg Size | Max Size |
|-----------------|-------|----------|----------|----------|
| `BalanceSheets` | 5,842 | 96.8% | 24 KB | 529 KB |
| `StatementsOfCashFlows` | 5,827 | 96.6% | 15 KB | 188 KB |
| `StatementsOfIncome` | 5,514 | 91.4% | **34 KB** | 518 KB |
| `StatementsOfShareholdersEquity` | 5,410 | 89.7% | 27 KB | 540 KB |

- **85% of 10-Qs have all 4 financial statements** (5,128 reports)
- 188 (3.1%) have zero financial statements
- Average ~3.7 statements per report

**StatementsOfIncome is the largest** at 34 KB avg — because quarterly filings include both Q and YTD columns, plus comparison periods.

### FinancialStatementContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `statement_type` | String | One of the 4 types above |
| `value` | JSON string | Structured financial statement payload |
| `filing_id` | String | Accession number |
| `form_type` | String | `10-Q` |
| `filer_cik` | String | SEC CIK |
| `filed_at` | String | ISO 8601 filing datetime |

---

## Exhibit Content (Layer 3)

### The SEC Exhibit Numbering System

The SEC defines a **universal exhibit table** in Regulation S-K Item 601 — a master menu of ~30 attachment categories used across ALL filing types (8-K, 10-K, 10-Q, proxy statements, registration statements, everything). Think of it like a post office with numbered mailboxes:

```
Box 1:   Underwriting agreements
Box 2:   Plans of acquisition / reorganization
Box 3:   Articles of incorporation & bylaws
Box 4:   Instruments defining rights of security holders
Box 5:   Opinion on legality
Box 8:   Opinion on tax matters
Box 10:  MATERIAL CONTRACTS               ← EX-10.x comes from here
Box 11:  Computation of per-share earnings
Box 13:  Annual report to security holders
Box 14:  Code of ethics
Box 16:  Letter re: change in accountant
Box 21:  Subsidiaries of the registrant
Box 23:  Consents of experts and counsel
Box 24:  Power of attorney
Box 31:  CEO/CFO certifications (SOX §302)
Box 32:  CEO/CFO certifications (SOX §906)
Box 95:  Mine safety disclosure
Box 96:  Technical report summary (mining/oil)
Box 97:  Clawback policy
Box 99:  ADDITIONAL EXHIBITS (catch-all)   ← EX-99.x comes from here
Box 101: Interactive data (XBRL)
Box 104: Cover page interactive data
```

The same exhibit number means the same thing regardless of filing type. An `EX-10.1` on an 8-K is the same category (material contract) as an `EX-10.1` on a 10-K or 10-Q.

**Our database ingests only 2 of the ~30 categories: EX-10.x and EX-99.x.** The others (certifications, consents, charter documents, XBRL interactive data, etc.) are legal/administrative boilerplate — not analytically useful for market analysis. Across the entire database (30,812 exhibits total):

| Category | What it is | 8-K | 10-K | 10-Q | Other filings |
|----------|-----------|-----|------|------|---------------|
| **EX-10.x** | Material contracts | 3,455 (16%) | 4,080 (97%) | 4,831 (99%) | 91 |
| **EX-99.x** | Press releases / other | 17,507 (84%) | 127 (3%) | 71 (1%) | 630 |

The usage pattern flips by filing type: 8-K exhibits are ~84% press releases (EX-99.x), while 10-K/10-Q exhibits are ~97% material contracts (EX-10.x). This makes intuitive sense — 8-Ks announce events (via press releases), while annual/quarterly filings disclose agreements.

### Coverage

- **2,224 of 6,033 (36.9%) have exhibits** — significantly less than 10-K (62.6%)
- 3,809 (63.1%) have zero exhibits
- Max: 24 exhibits on a single 10-Q

| Exhibits per Report | Reports |
|--------------------|---------|
| 0 | 3,809 |
| 1 | 1,099 |
| 2 | 499 |
| 3 | 272 |
| 4 | 147 |
| 5+ | 207 |

### Exhibit Type Breakdown

| Category | Dominant Exhibits | Notes |
|----------|------------------|-------|
| **EX-10.x** | EX-10.1 (1,563), EX-10.2 (1,022), EX-10.3 (657) | Material contracts — 97%+ |
| **EX-99.x** | EX-99.1 (61) | Press releases — rare on 10-Qs |

Same pattern as 10-K: dominated by material contracts. Average exhibit size ~76 KB (larger than 10-K avg of 55 KB).

### ExhibitContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `exhibit_number` | String | e.g. `EX-10.1`, `EX-99.1` |
| `content` | String | Exhibit text (~76 KB avg, up to ~1.44 MB) |
| `filing_id` | String | Accession number |
| `form_type` | String | `10-Q` |
| `filer_cik` | String | SEC CIK |
| `filed_at` | String | ISO 8601 filing datetime |

---

## Filing Text Content (Layer 4 — Fallback)

- 176 reports (2.9%) — the REFERENCE_ONLY reports
- Average ~2.0 MB per node (smaller than 10-K's ~4.0 MB)

---

## XBRL Data (Layer 5)

- 5,857 of 6,033 (97.1%) have an `XBRLNode` link
- 95.9% COMPLETED, 1.2% PROCESSING, 2.9% REFERENCE_ONLY, 1 FAILED
- Same index-pointer architecture as 10-K

---

## 177 REFERENCE_ONLY Reports

Same pattern as 10-K. These 177 10-Q reports:
- Lack `PRIMARY_FILER` → use `REFERENCED_IN` instead
- Have `HAS_FILING_TEXT` with raw ~2 MB text
- Have `xbrl_status: REFERENCE_ONLY`
- Are subsidiary/holding-company filings (PNW, XRX, ETR, PPL, URI, EIX, ED, etc.)

---

## 10-Q/A Amendments

### How They Differ From 10-Q

| Dimension | 10-Q | 10-Q/A |
|-----------|------|--------|
| Count | 6,033 | 30 (22 companies) |
| `isAmendment` | `false` | `true` |
| Avg sections | 9.7 | variable (1-11) |
| Has exhibits | 36.9% | ~7% |
| Has financial statements | 96.9% | ~47% |
| XBRL status | 95.9% COMPLETED | 96.7% COMPLETED |

### Amendment Patterns

| Section Count | 10-Q/A Reports | Pattern |
|--------------|----------------|---------|
| 11 | 7 | Full re-filing |
| 9 | 2 | Full minus optional items |
| 5-7 | 4 | Partial |
| 1-3 | 17 | **Targeted corrections** |

Most amendments (17 of 30) have only 1-3 sections — confirming they are targeted fixes, not full re-filings.

Top amenders: HSY (3), BILL (3), RH (3), GME (2), IIPR (2).

---

## Market Returns Data

### Coverage

| Return Type | Count | Coverage |
|------------|-------|----------|
| `daily_stock` | 5,785 | 98.8% |
| `hourly_stock` | 5,785 | 98.8% |
| `session_stock` | 5,785 | 98.8% |
| `daily_macro` | 5,857 | 100% |
| `daily_industry` | 5,856 | 99.98% |
| `daily_sector` | 5,857 | 100% |

Returns live on the `PRIMARY_FILER` relationship edge.

### Return Statistics (excess = daily_stock - daily_macro)

| Metric | Value |
|--------|-------|
| Mean | -0.10% (essentially zero) |
| Std Dev | **7.59%** |
| Min | **-77.56%** |
| Max | **+49.35%** |
| n | 5,785 |

10-Q filings show higher return dispersion (std 7.59%) than 10-K filings (std 6.58%), because quarterly reports are more event-like — they reveal earnings results for the first time (when filed before or alongside the 8-K).

### Filing Session Distribution

| Session | 10-Q | 10-Q/A |
|---------|------|--------|
| `post_market` | 61.7% | majority |
| `in_market` | 22.2% | |
| `pre_market` | 14.2% | |
| `market_closed` | 1.9% | |

---

## 10-Q vs 10-K: Side-by-Side Comparison

| Dimension | 10-Q | 10-K |
|-----------|------|------|
| **Purpose** | Quarterly update | Annual comprehensive |
| **Count** | 6,033 | 2,263 |
| **Frequency** | 3 per year (Q1-Q3) | 1 per year (Q4/annual) |
| **Sections defined** | 11 | 22 |
| **Typical sections** | 9-11 | 20-21 |
| **Parts** | I + II | I + II + III + IV |
| **Section key format** | `partXitemY` lowercase | Numeric (`'1'`, `'1A'`) |
| **MD&A section name** | `ManagementDiscussion...` (no apostrophe) | `Management\u2019sDiscussion...` (curly apostrophe) |
| **MD&A avg size** | 56 KB | 72 KB |
| **Financial statements avg** | 25 KB | 29 KB |
| **Exhibit coverage** | 36.9% | 62.6% |
| **Filing text coverage** | 2.9% (176) | 3.0% (67) |
| **REFERENCE_ONLY** | 177 | 67 |
| **Amendments** | 30 (10-Q/A) | 108 (10-K/A) |
| **Return std dev** | 7.59% | 6.58% |
| **Cybersecurity section** | No | Yes (65.7%) |
| **Part III governance** | No | Yes |

---

## Extraction Pipeline

### How Sections Get Extracted

Source: `redisDB/ReportProcessor.py`

1. `_get_sections_map()` returns `ten_q_sections` dict for `formType = 10-Q`
2. `_extract_sections()` iterates all 11 items in parallel via `ThreadPoolExecutor`
3. Each item calls `sec-api.io` `ExtractorApi` with 90s timeout and retry logic
4. Content goes through HTML unescaping + NFKC Unicode normalization
5. Non-empty results become `ExtractedSectionContent` nodes with `HAS_SECTION` edges
6. Missing/empty sections are simply not created (no placeholder nodes)

Pipeline is **identical** to 10-K — only the section dictionary differs.

### Content Fetch Order (for downstream consumers)

1. **Run query 5F** (content inventory) to see which layers exist
2. **Fetch canonical MD&A** via query 5B (section name: `ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations` — no apostrophe)
3. **Discover other sections** via 5D, fetch specific ones via 5I
4. **Financial statements** via 5C (by `statement_type`)
5. **Exhibits** via 5H (by `exhibit_number`)
6. **Filing text** via 5G (last resort only — bound/slice before use)

---

## Standardization Summary

| Aspect | Standardized? | Notes |
|--------|:------------:|-------|
| Section names | **Yes** | 11 canonical strings, zero variants |
| Section presence | **Mostly** | Top 9 at ≥91.6%, bottom 2 at ~50% |
| Section ordering | **No** | No `sequence`/`order` property; name-based identification only |
| Financial statement types | **Yes** | Fixed 4-type enum, same as 10-K |
| Exhibit numbering | **Yes** | Standard SEC exhibit numbers |
| Node properties | **Yes** | Consistent field set across all content nodes |
| Return data | **Yes** | 98.8% coverage with 6 return types |
| XBRL processing | **Yes** | 95.9% completed |
| Section name format | **Yes** | PascalCase, no spaces, **no apostrophes** (unlike 10-K) |

---

## Admin Structure in Neo4j

From `neograph/Neo4jInitializer.py`:

10-Q reports are organized under an AdminReport hierarchy:
```
"10-Q Reports" (parent)
├── 10-Q_Q1
├── 10-Q_Q2
├── 10-Q_Q3
└── 10-Q_Q4
```

Each report is linked via `IN_CATEGORY → AdminReport` based on its quarter.

---

## Nuances & Gotchas

1. **No apostrophe in MD&A name.** 10-Q uses `ManagementDiscussionandAnalysis...` while 10-K uses `Management\u2019sDiscussionandAnalysis...` (curly apostrophe U+2019). Queries must match the correct variant per form type, or use `STARTS WITH 'Management'` + `CONTAINS 'DiscussionandAnalysis'` to match both.

2. **`section_name` not `sectionType`.** Same as 10-K — the property is `section_name`. No `title` field exists.

3. **`content_length` is a string.** Comma-formatted like `"3,401"`. Use `size(s.content)` in Cypher for integer comparison.

4. **MineSafety and Defaults are optional.** Only ~50% coverage. Content is almost always "None" (57-84 bytes avg). Their presence or absence is the main driver of the 11-vs-9 section split.

5. **177 REFERENCE_ONLY reports.** Same pattern as 10-K — subsidiary filings without `PRIMARY_FILER`. Use `REFERENCED_IN` relationship.

6. **No `items` field.** Like 10-K, the `items` property is 8-K-specific.

7. **`periodOfReport` varies.** Most companies use standard quarter-end dates (3/31, 6/30, 9/30) but many use 4-4-5 or 13-week fiscal quarters, resulting in non-standard dates like `2024-03-30`, `2025-06-28`, `2024-07-31`.

8. **Higher return dispersion than 10-K.** Std dev of 7.59% (vs 6.58% for 10-K) because 10-Q filings often carry earnings surprises.

9. **1 FAILED XBRL.** There is exactly 1 10-Q with `xbrl_status: FAILED` — an edge case worth noting but not actionable.

10. **Guidance extraction barely targets 10-Q.** Only 1 GuidanceUpdate node links to a 10-Q. The pipeline notes: "10-Qs are mostly retrospective — zero guidance is valid."

---

*Created 2026-03-14. Source data: 6,063 reports (6,033 10-Q + 30 10-Q/A), 772 companies, Jan 2023 – Aug 2025.*
