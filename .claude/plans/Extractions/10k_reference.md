# 10-K Report Reference

Complete reference for 10-K annual filings in the EventMarketDB Neo4j database.

---

## Mental Model

Think of a 10-K as a **layered document with a fixed skeleton**.

```
┌─────────────────────────────────────────────────────┐
│                    Report Node                       │
│  (the filing envelope — metadata, timing, returns)   │
├─────────────────────────────────────────────────────┤
│                                                      │
│   Layer 1: SECTIONS (the narrative skeleton)          │
│   ┌───────────────────────────────────────────┐      │
│   │  21 named slots, like chapters in a book  │      │
│   │  SEC mandates the chapter titles           │      │
│   │  Companies fill in their content           │      │
│   │  A few chapters are optional/era-dependent │      │
│   └───────────────────────────────────────────┘      │
│                                                      │
│   Layer 2: FINANCIAL STATEMENTS (structured data)    │
│   ┌───────────────────────────────────────────┐      │
│   │  4 statement types as JSON payloads        │      │
│   │  BalanceSheets, Income, CashFlows, Equity  │      │
│   │  Structured, not narrative                 │      │
│   └───────────────────────────────────────────┘      │
│                                                      │
│   Layer 3: EXHIBITS (attachments)                    │
│   ┌───────────────────────────────────────────┐      │
│   │  Mostly EX-10.x material contracts         │      │
│   │  Employment agreements, credit facilities   │      │
│   │  Variable count (0-23 per filing)          │      │
│   └───────────────────────────────────────────┘      │
│                                                      │
│   Layer 4: FILING TEXT (raw fallback)                │
│   ┌───────────────────────────────────────────┐      │
│   │  Only 67 reports (3%) — unparsed fallback  │      │
│   │  ~4 MB of raw HTML/text                    │      │
│   │  Use only when sections failed to extract  │      │
│   └───────────────────────────────────────────┘      │
│                                                      │
│   Layer 5: XBRL (machine-readable financials)        │
│   ┌───────────────────────────────────────────┐      │
│   │  Pointer node to structured XBRL facts     │      │
│   │  97% coverage, 94.8% fully processed       │      │
│   │  Separate fact/concept graph                │      │
│   └───────────────────────────────────────────┘      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Key intuitions:**

1. **The skeleton is fixed.** The SEC defines exactly which Items must appear. Every 10-K has the same chapter titles — `Business`, `RiskFactors`, `MD&A`, etc. The company fills in the content. This is why 94% of our 10-Ks have 20 or 21 sections.

2. **Sections are narrative, financial statements are structured.** Don't confuse Item 8 (`FinancialStatementsandSupplementaryData` — a narrative section node) with the actual `FinancialStatementContent` nodes (JSON payloads of balance sheets, income statements, etc.). They coexist but serve different purposes.

3. **Two things change the skeleton:**
   - **Cybersecurity (Item 1C)** — mandated Dec 2023. Present in 65.7% of filings. Pre-2024 filings don't have it → 20 sections. Post-2024 filings do → 21 sections.
   - **SelectedFinancialData (Item 6)** — eliminated post-Feb 2021. Still extracted from older filings (95.4% coverage) but fading out.

4. **10-K/A is a patch, not a full filing.** Amendments average only 4.3 sections (vs 20.4 for 10-K). They fix specific items — almost always Part III proxy-related sections (compensation, directors, ownership). Think of them as a targeted errata sheet.

5. **Sections vs layers are orthogonal.** Sections are the narrative chapters (21 slots). Financial statements, exhibits, and XBRL are separate content layers accessed through different relationships. A single 10-K can have content in all layers simultaneously.

6. **67 orphan reports.** These REFERENCE_ONLY reports lack `PRIMARY_FILER` and use `REFERENCED_IN` instead. They have raw filing text but no parsed sections/exhibits. They exist for cross-reference only.

---

## Inventory

| Form Type | Count | Date Range | Companies |
|-----------|-------|------------|-----------|
| 10-K | 2,263 | 2023-01-17 → 2025-08-29 | 768 |
| 10-K/A | 108 | 2023-01-24 → 2025-08-26 | 82 |
| **Total** | **2,371** | | |

Year distribution:

| Year | 10-K | 10-K/A |
|------|------|--------|
| 2023 | 785 | 36 |
| 2024 | 765 | 35 |
| 2025 | 713 (through Aug) | 37 |

Most companies have exactly 3 filings (one per fiscal year: FY2022, FY2023, FY2024).

---

## Graph Structure

### Relationship Map

```
Report ──PRIMARY_FILER─────────→ Company                (2,196 reports)
       ──REFERENCED_IN─────────→ Company                (67 REFERENCE_ONLY reports)
       ──HAS_SECTION───────────→ ExtractedSectionContent (46,744 nodes)
       ──HAS_FINANCIAL_STATEMENT→ FinancialStatementContent (8,668 nodes)
       ──HAS_EXHIBIT───────────→ ExhibitContent          (4,222 nodes)
       ──HAS_XBRL──────────────→ XBRLNode                (2,303 nodes)
       ──INFLUENCES────────────→ MarketIndex             (1 per report)
       ──INFLUENCES────────────→ Sector                  (1 per report)
       ──INFLUENCES────────────→ Industry                (1 per report)
       ──IN_CATEGORY───────────→ AdminReport             (1 per report)
       ──HAS_FILING_TEXT────────→ FilingTextContent       (67 fallback nodes)
       ──FROM_SOURCE←───────────  GuidanceUpdate          (extraction pipeline output)
```

### Report Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `accessionNo` / `id` | String | Canonical SEC filing ID |
| `formType` | String | `10-K` or `10-K/A` |
| `periodOfReport` | String | Fiscal year end date (e.g. `2024-12-31`) |
| `created` | ISO datetime | Filing timestamp (Eastern time) |
| `isAmendment` | Boolean | `false` for 10-K, `true` for 10-K/A |
| `cik` | String | SEC CIK number (null for REFERENCE_ONLY) |
| `market_session` | String | `post_market` / `in_market` / `pre_market` / `market_closed` |
| `xbrl_status` | String | `COMPLETED` / `PROCESSING` / `QUEUED` / `REFERENCE_ONLY` |
| `is_xml` | Boolean | Whether filing is XML format |
| `description` | String | Always `"Form 10-K - Annual report [Section 13 and 15(d), not S-K Item 405]"` |
| `primaryDocumentUrl` | String | SEC primary document URL |
| `linkToTxt` / `linkToHtml` / `linkToFilingDetails` | String | SEC links |
| `symbols` | String | Ticker symbol(s) |
| `entities` | String | Filing entity metadata |
| `returns_schedule` | JSON string | Return-window calculation metadata |
| `extracted_sections` | JSON string | Section extraction metadata (up to ~690KB) |
| `exhibit_contents` | JSON string | Exhibit metadata |
| `financial_statements` | JSON string | Financial statement metadata |

---

## Section Structure (Layer 1)

### Source Definition

From `secReports/reportSections.py`:

```python
ten_k_sections = {
    '1':  'Business',
    '1A': 'RiskFactors',
    '1B': 'UnresolvedStaffComments',
    '1C': 'Cybersecurity',
    '2':  'Properties',
    '3':  'LegalProceedings',
    '4':  'MineSafetyDisclosures',
    '5':  'MarketforRegistrant\u2019sCommonEquity,...',
    '6':  'SelectedFinancialData(priortoFebruary2021)',
    '7':  'Management\u2019sDiscussionandAnalysis...',
    '7A': 'QuantitativeandQualitativeDisclosuresaboutMarketRisk',
    '8':  'FinancialStatementsandSupplementaryData',
    '9':  'ChangesinandDisagreementswithAccountants...',
    '9A': 'ControlsandProcedures',
    '9B': 'OtherInformation',
    '10': 'Directors,ExecutiveOfficersandCorporateGovernance',
    '11': 'ExecutiveCompensation',
    '12': 'SecurityOwnershipofCertainBeneficialOwners...',
    '13': 'CertainRelationshipsandRelatedTransactions,...',
    '14': 'PrincipalAccountantFeesandServices',
    '15': 'ExhibitsandFinancialStatementSchedules',
}
```

Section names use **PascalCase-no-spaces with curly apostrophes (U+2019)**. Zero spelling variants exist across the entire corpus.

### The Standard 10-K Skeleton (SEC Regulation S-K)

```
PART I
├── Item 1    Business                                          ██████████ 62 KB avg
├── Item 1A   Risk Factors                                      ████████████████ 105 KB avg
├── Item 1B   Unresolved Staff Comments                         ▏ 0.4 KB avg
├── Item 1C   Cybersecurity                          [NEW 2023] █ 7 KB avg
├── Item 2    Properties                                        █ 3.6 KB avg
├── Item 3    Legal Proceedings                                 ▏ 1.4 KB avg
└── Item 4    Mine Safety Disclosures                           ▏ 0.9 KB avg

PART II
├── Item 5    Market for Common Equity                          █ 3.7 KB avg
├── Item 6    Selected Financial Data              [LEGACY]     ▏ 0.7 KB avg
├── Item 7    MD&A                                              ██████████ 72 KB avg
├── Item 7A   Quantitative/Qualitative Disclosures              █ 4.6 KB avg
├── Item 8    Financial Statements                              ██████████████████ 119 KB avg
├── Item 9    Changes in Accountants                            ▏ 0.1 KB avg
├── Item 9A   Controls and Procedures                           █ 5.1 KB avg
└── Item 9B   Other Information                                 ▏ 0.8 KB avg

PART III
├── Item 10   Directors & Officers                              ▏ 2.0 KB avg
├── Item 11   Executive Compensation                            ▏ 1.5 KB avg
├── Item 12   Security Ownership                                ▏ 1.2 KB avg
├── Item 13   Related Transactions                              ▏ 0.6 KB avg
└── Item 14   Accountant Fees                                   ▏ 0.5 KB avg

PART IV
└── Item 15   Exhibits & Financial Statement Schedules          ██████████ 62 KB avg
```

### Section Coverage Table

| SEC Item | `section_name` | Count | Coverage | Avg Size | Max Size |
|----------|---------------|-------|----------|----------|----------|
| 1 | `Business` | 2,263 | **100.0%** | 62 KB | 353 KB |
| 1A | `RiskFactors` | 2,257 | 99.7% | 105 KB | 544 KB |
| 1B | `UnresolvedStaffComments` | 2,241 | 99.0% | 0.4 KB | 534 KB |
| 1C | `Cybersecurity` | 1,486 | **65.7%** | 7 KB | 550 KB |
| 2 | `Properties` | 2,209 | 97.6% | 3.6 KB | 159 KB |
| 3 | `LegalProceedings` | 2,263 | **100.0%** | 1.4 KB | 112 KB |
| 4 | `MineSafetyDisclosures` | 2,225 | 98.3% | 0.9 KB | 17 KB |
| 5 | `MarketforRegistrant's...` | 2,262 | 100.0% | 3.7 KB | 35 KB |
| 6 | `SelectedFinancialData(...)` | 2,158 | 95.4% | 0.7 KB | 337 KB |
| 7 | `Management'sDiscussion...` | 2,253 | 99.6% | 72 KB | 372 KB |
| 7A | `QuantitativeandQualitative...` | 2,248 | 99.3% | 4.6 KB | 40 KB |
| 8 | `FinancialStatementsand...` | 2,259 | 99.8% | 119 KB | 960 KB |
| 9 | `ChangesinandDisagreements...` | 2,245 | 99.2% | 0.1 KB | 6 KB |
| 9A | `ControlsandProcedures` | 2,257 | 99.7% | 5.1 KB | 21 KB |
| 9B | `OtherInformation` | 2,248 | 99.3% | 0.8 KB | 51 KB |
| 10 | `Directors,ExecutiveOfficers...` | 2,234 | 98.7% | 2.0 KB | 47 KB |
| 11 | `ExecutiveCompensation` | 2,224 | 98.3% | 1.5 KB | 161 KB |
| 12 | `SecurityOwnershipofCertain...` | 2,226 | 98.4% | 1.2 KB | 209 KB |
| 13 | `CertainRelationshipsand...` | 2,224 | 98.3% | 0.6 KB | 34 KB |
| 14 | `PrincipalAccountantFees...` | 2,231 | 98.6% | 0.5 KB | 185 KB |
| 15 | `ExhibitsandFinancialStatement...` | 2,263 | **100.0%** | 62 KB | 611 KB |

Three sections appear in **every** 10-K: Business (Item 1), LegalProceedings (Item 3), Exhibits (Item 15).

### Section Count Distribution

| Sections per Report | Reports | % | What it means |
|--------------------|---------|---|---------------|
| **21** | 1,351 | 59.7% | Full modern filing (all items including Cybersecurity) |
| **20** | 776 | 34.3% | Pre-Cybersecurity or dropped SelectedFinancialData |
| 16-19 | 119 | 5.3% | Some Part III items incorporated by reference to proxy |
| 7-15 | 17 | 0.8% | Heavy incorporation by reference (MCD, CAH, HIG) |

**94% of 10-Ks have 20 or 21 sections.** The extraction is highly consistent.

### Why Some 10-Ks Have Fewer Sections

Two legitimate SEC mechanisms:

1. **Cybersecurity rule timing** — Item 1C mandatory only for fiscal years ending ≥ Dec 15, 2023. Pre-rule filings have 20 sections instead of 21.

2. **Incorporation by reference** — Large companies (MCD, CAH, HIG, HAL) defer Part III items (10-14) to their proxy statement (DEF 14A). The 10-K says "see proxy statement" instead of including the content. The parser correctly extracts nothing for those items, resulting in fewer section nodes.

This is not a data quality issue — it accurately reflects what the SEC filing contains.

### ExtractedSectionContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `section_name` | String | Canonical section key (PascalCase, no spaces) |
| `content` | String | Full text content |
| `content_length` | String | Comma-formatted length (use `size(s.content)` for integer) |
| `filing_id` | String | Accession number back-reference |
| `form_type` | String | `10-K` |
| `filer_cik` | String | SEC CIK |
| `filed_at` | String | ISO 8601 filing datetime |

**Important:** There is no `sectionType` or `title` property. The field is `section_name`. There is no `sequence` or `order` property — sections are identified by name only.

---

## Financial Statement Content (Layer 2)

### Coverage

| `statement_type` | Count | Coverage |
|-----------------|-------|----------|
| `BalanceSheets` | 2,185 | 96.6% |
| `StatementsOfCashFlows` | 2,179 | 96.3% |
| `StatementsOfShareholdersEquity` | 2,144 | 94.7% |
| `StatementsOfIncome` | 2,079 | 91.9% |

Average ~3.8 statements per report. Average payload ~29 KB (JSON).

### FinancialStatementContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `statement_type` | String | One of the 4 types above |
| `value` | JSON string | Structured financial statement payload |
| `filing_id` | String | Accession number |
| `form_type` | String | `10-K` |
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

- 1,416 of 2,263 (62.6%) have exhibits
- 847 (37.4%) have zero exhibits ingested
- Average 1.86 exhibits per report; max 23

### Exhibit Type Breakdown

| Category | % of Exhibits | Description |
|----------|--------------|-------------|
| **EX-10.x** | 97% | Material contracts (employment, credit, lease agreements) |
| **EX-99.x** | 3% | Press releases / other (only 83 10-Ks have EX-99.1) |

This is the **inverse** of 8-K filings where EX-99.1 (press releases) dominates at 84%.

### ExhibitContent Node Properties

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `exhibit_number` | String | e.g. `EX-10.1`, `EX-99.1` |
| `content` | String | Exhibit text (~55 KB avg, up to ~947 KB) |
| `filing_id` | String | Accession number |
| `form_type` | String | `10-K` |
| `filer_cik` | String | SEC CIK |
| `filed_at` | String | ISO 8601 filing datetime |

---

## Filing Text Content (Layer 4 — Fallback)

Only 67 reports (3%) — these are REFERENCE_ONLY reports where section-level extraction was not performed.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique node ID |
| `content` | String | Raw full filing text (~4.0 MB avg) |
| `form_type` | String | `10-K` |

---

## XBRL Data (Layer 5)

- 2,303 of 2,371 (97%) have an `XBRLNode` link
- 94.8% are `COMPLETED`, 2.2% `PROCESSING`, 0.04% `QUEUED`
- XBRLNode is an **index pointer** — actual facts are accessed via separate Fact/Concept graph (see `neo4j-xbrl` agent)

---

## 10-K/A Amendments

### How They Differ From 10-K

| Dimension | 10-K | 10-K/A |
|-----------|------|--------|
| Count | 2,263 | 108 (82 companies) |
| `isAmendment` | `false` | `true` |
| Avg sections | 20.4 | **4.3** |
| Has exhibits | 62.6% | 12% |
| Has financial statements | 96.6% | 19.4% |
| Has filing text | 3.0% | 0% |

### What Gets Amended

10-K/A amendments are **targeted patches**, overwhelmingly fixing Part III proxy-related items:

| Section | % of 10-K/A reports |
|---------|-------------------|
| ExhibitsandFinancialStatementSchedules | 94% |
| ExecutiveCompensation (Item 11) | 50% |
| Directors,ExecutiveOfficers (Item 10) | 49% |
| SecurityOwnership (Item 12) | 49% |
| CertainRelationships (Item 13) | 49% |
| PrincipalAccountantFees (Item 14) | 45% |
| FinancialStatements (Item 8) | 18% |
| ControlsandProcedures (Item 9A) | 15% |
| RiskFactors (Item 1A) | 8% |
| Business (Item 1) | 6% |

**Why?** Companies commonly incorporate Part III items by reference from their proxy statement. When the proxy is filed late, contains errors, or the company decides to include the content directly, a 10-K/A is filed to amend those specific items.

---

## Market Returns Data

### Coverage

| Return Type | Coverage |
|------------|----------|
| `daily_stock` | 98.8% (2,170) |
| `hourly_stock` | 98.8% |
| `session_stock` | 98.8% |
| `daily_macro` | 100% |
| `daily_industry` | 99.8% |
| `daily_sector` | 100% |

Returns live on the `PRIMARY_FILER` relationship edge, not on the Report node itself.

### Return Statistics (excess = daily_stock - daily_macro)

| Metric | Value |
|--------|-------|
| Mean | -0.04% (essentially zero) |
| Std Dev | 6.58% |
| Min | -41.32% |
| Max | +78.17% |

10-K filings are annual reports, not event-driven — the mean return is near zero. But outliers show that some annual filings do move stocks significantly.

### Filing Session Distribution

| Session | 10-K | 10-K/A |
|---------|------|--------|
| `post_market` | 62% | 81% |
| `in_market` | 21% | 4% |
| `pre_market` | 13% | 6% |
| `market_closed` | 4% | 9% |

---

## Extraction Pipeline

### How Sections Get Extracted

Source: `redisDB/ReportProcessor.py`

1. `_get_sections_map()` returns `ten_k_sections` dict for `formType = 10-K`
2. `_extract_sections()` iterates all 22 items in parallel via `ThreadPoolExecutor`
3. Each item calls `sec-api.io` `ExtractorApi` with 90s timeout and retry logic
4. Content goes through HTML unescaping + NFKC Unicode normalization
5. Non-empty results become `ExtractedSectionContent` nodes with `HAS_SECTION` edges
6. Missing/empty sections are simply not created (no placeholder nodes)

### Content Fetch Order (for downstream consumers)

1. **Run query 5F** (content inventory) to see which layers exist
2. **Fetch canonical MD&A** via query 5B when needed (section name: `Management\u2019sDiscussionandAnalysisofFinancialConditionandResultsofOperations`)
3. **Discover other sections** via 5D, fetch specific ones via 5I
4. **Financial statements** via 5C (by `statement_type`)
5. **Exhibits** via 5H (by `exhibit_number`)
6. **Filing text** via 5G (last resort only — bound/slice before use)

---

## Standardization Summary

| Aspect | Standardized? | Notes |
|--------|:------------:|-------|
| Section names | **Yes** | 21 canonical strings, zero variants, defined in `reportSections.py` |
| Section presence | **Yes** | 18/21 sections at ≥95% coverage |
| Section ordering | **No** | No `sequence`/`order` property; name-based identification only |
| Financial statement types | **Yes** | Fixed 4-type enum |
| Exhibit numbering | **Yes** | Standard SEC exhibit numbers |
| Node properties | **Yes** | Consistent field set across all content nodes |
| Return data | **Yes** | 98.8% coverage with 6 return types |
| XBRL processing | **Yes** | 94.8% completed |
| Section name format | **Yes** | PascalCase, no spaces, curly apostrophes (U+2019) |

---

## Nuances & Gotchas

1. **`section_name` not `sectionType`** — The property is `section_name`. There is no `sectionType` or `title` field.

2. **Curly apostrophes** — MD&A and Market sections use U+2019 (`'`) not ASCII (`'`). Queries must match exactly: `Management\u2019sDiscussion...`

3. **`content_length` is a string** — Comma-formatted like `"73,713"`. Use `size(s.content)` in Cypher for integer comparison.

4. **Item 8 vs FinancialStatementContent** — The section node for Item 8 contains the *narrative* around financial statements. The `FinancialStatementContent` nodes (via `HAS_FINANCIAL_STATEMENT`) contain the *structured JSON* of actual balance sheets, income statements, etc. They are different things.

5. **67 REFERENCE_ONLY reports** — No `PRIMARY_FILER`, no parsed sections, no XBRL. Use `REFERENCED_IN` relationship. Have `HAS_FILING_TEXT` with raw ~4MB text.

6. **No `items` field** — Unlike 8-K reports, 10-K Report nodes do not populate the `items` field.

7. **`periodOfReport` vs `created`** — `periodOfReport` is the fiscal year end date. `created` is the filing timestamp. For point-in-time analysis, use `created`.

8. **10-K/A shares the same graph structure** — Same node types and relationships, just sparser content. Filter on `r.isAmendment = true` or `r.formType = '10-K/A'`.

9. **Exhibit composition differs from 8-K** — 10-K exhibits are 97% material contracts (EX-10.x). 8-K exhibits are 84% press releases (EX-99.x).

10. **XBRLNode is an index pointer** — It does not have child relationships to Fact nodes directly accessible from the Report. Use the `neo4j-xbrl` agent patterns instead.

---

*Created 2026-03-14. Source data: 2,371 reports (2,263 10-K + 108 10-K/A), 768 companies, Jan 2023 – Aug 2025.*
