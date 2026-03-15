# 8-K Filing Reference — Complete Taxonomy & Content Guide

Comprehensive reference for all 8-K report types in the EventMarketDB system. Validated against live Neo4j database (23,836 8-K filings, 796 companies) on 2026-03-14.

---

## 1. Overview

- **23,836** 8-K filings (current event reports)
- **514** 8-K/A amendments (supersede the original for the same items)
- **2** filings with null/empty items field (negligible data quality noise)
- Filed by **796 companies** tracked in the system
- Item 9.01 appears in 79% of all 8-Ks as a companion item (exhibit index)

---

## 2. The SEC Item Code Taxonomy

Every 8-K filing declares one or more "Item" codes describing the reported event. Items are stored in `Report.items` as a JSON array of strings (e.g., `["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"]`).

### Tier 1: Ubiquitous (>5,000 filings)

| Item | Name | Count | % of 8-Ks | Description |
|------|------|-------|-----------|-------------|
| **9.01** | Financial Statements and Exhibits | 18,888 | **79%** | Exhibit index — almost always a companion item, rarely standalone. Says "there are exhibits attached." |
| **2.02** | Results of Operations and Financial Condition | 8,847 | **37%** | **EARNINGS** — quarterly/annual results disclosure. The single most important 8-K type for market impact analysis. |
| **7.01** | Regulation FD Disclosure | 5,822 | **24%** | Public disclosure of material info: investor presentations, pre-announcements, guidance updates, mid-quarter revisions. |
| **5.02** | Departure/Appointment of Officers | 5,103 | **21%** | Executive/director changes — hires, departures, compensation amendments, board appointments. |

### Tier 2: Common (1,000–5,000 filings)

| Item | Name | Count | % | Description |
|------|------|-------|---|-------------|
| **8.01** | Other Events | 4,769 | 20% | Catch-all for material events not covered elsewhere: restructurings, strategic updates, share buybacks, litigation updates. |
| **1.01** | Entry into Material Definitive Agreement | 2,533 | 11% | New contracts — credit facilities, M&A agreements, leases, licensing deals, joint ventures. |
| **5.07** | Submission of Matters to a Vote of Security Holders | 2,279 | 10% | Shareholder vote results from annual/special meetings (director elections, say-on-pay, proposals). |
| **2.03** | Creation of Direct Financial Obligation | 1,494 | 6% | New debt — bond issuances, credit lines drawn, off-balance-sheet obligations. Often paired with Item 1.01. |

### Tier 3: Moderate (100–1,000 filings)

| Item | Name | Count | % | Description |
|------|------|-------|---|-------------|
| **5.03** | Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year | 836 | 3.5% | Corporate governance structural changes. |
| **3.02** | Unregistered Sales of Equity Securities | 304 | 1.3% | Stock issuances outside public offerings (private placements, employee grants). |
| **1.02** | Termination of a Material Definitive Agreement | 282 | 1.2% | Contract terminations. Often paired with Item 1.01 (old agreement terminated, new one entered). |
| **2.05** | Costs Associated with Exit or Disposal Activities | 215 | 0.9% | Restructuring charges, layoffs, facility closures, segment divestitures. |
| **2.01** | Completion of Acquisition or Disposition of Assets | 189 | 0.8% | M&A deal closings (acquisition completed, division sold). |
| **3.03** | Material Modifications to Rights of Security Holders | 127 | 0.5% | Changes to shareholder rights (charter amendments affecting stock). |

### Tier 4: Rare (<100 filings)

| Item | Name | Count | % | Description |
|------|------|-------|---|-------------|
| **3.01** | Notice of Delisting / Transfer of Listing | 55 | 0.2% | Exchange delistings or listing transfers (e.g., NYSE to Nasdaq). |
| **2.06** | Material Impairments | 54 | 0.2% | Asset write-downs, goodwill impairments, long-lived asset impairments. |
| **4.01** | Changes in Registrant's Certifying Accountant | 42 | 0.2% | Auditor switches (e.g., Deloitte to PwC). |
| **5.01** | Changes in Control of Registrant | 23 | 0.1% | Ownership control changes (mergers, buyouts, activist takeovers). |
| **2.04** | Triggering Events That Accelerate Financial Obligations | 15 | 0.06% | Debt covenant triggers, acceleration events, cross-default clauses. |
| **1.04** | Mine Safety Reporting | 15 | 0.06% | Mining company safety violations (Dodd-Frank mandate). |
| **4.02** | Non-Reliance on Previously Issued Financial Statements | 15 | 0.06% | Restatement red flags — prior financials can no longer be relied upon. |
| **1.05** | Material Cybersecurity Incidents | 12 | 0.05% | Cyber breaches (new SEC rule effective Dec 2023). |
| **5.04** | Temporary Suspension of Trading Under Employee Benefit Plans | 10 | 0.04% | 401(k)/ESOP trading blackouts. |
| **5.08** | Shareholder Nominations Pursuant to Rule 14a-11 | 10 | 0.04% | Board nomination filings under universal proxy rules. |
| **5.05** | Amendments to Code of Ethics or Waiver | 6 | 0.03% | Ethics policy changes or waivers for executives. |
| **1.03** | Bankruptcy or Receivership | 1 | 0.004% | Chapter 7/11 bankruptcy filings. |

### Zero in Database

| Item | Name | Why absent |
|------|------|------------|
| **5.06** | Change in Shell Company Status | No shell companies in universe |
| **6.01–6.05** | Asset-Backed Securities Items | No ABS issuers in universe |

---

## 3. Multi-Item Filings

Most 8-Ks contain multiple items. Only 18.6% are single-item:

| Items per filing | Filings | % |
|---|---|---|
| 1 item | 4,434 | 18.6% |
| 2 items | 12,611 | **52.9%** |
| 3 items | 5,342 | 22.4% |
| 4 items | 1,125 | 4.7% |
| 5 items | 236 | 1.0% |
| 6+ items | 86 | 0.4% |

### Most Common Combinations (Top 15)

| Combination | Count | Interpretation |
|---|---|---|
| 2.02 + 9.01 | 6,157 | **Standard earnings release** (press release as exhibit) |
| 8.01 + 9.01 | 1,996 | Other material event with attached exhibit |
| 7.01 + 9.01 | 1,587 | Reg FD with investor deck/presentation |
| 5.02 alone | 1,583 | Executive change announcement (no exhibit needed) |
| 2.02 + 7.01 + 9.01 | 1,468 | **Earnings + investor presentation** (richest earnings filing) |
| 5.02 + 9.01 | 1,350 | Executive change with employment agreement attached |
| 5.07 alone | 1,186 | Standalone voting results |
| 5.02 + 7.01 + 9.01 | 826 | Executive change with Reg FD materials |
| 8.01 alone | 712 | Other event, section text only |
| 1.01 + 2.03 + 9.01 | 705 | **New debt agreement** (contract + obligation created) |
| 7.01 alone | 519 | Reg FD disclosure, section text only |
| 2.02 + 8.01 + 9.01 | 391 | Earnings with additional other events |
| 1.01 + 9.01 | 378 | Material agreement with contract exhibit |
| 5.02 + 5.07 + 9.01 | 301 | Executive changes + voting results |
| 5.03 + 9.01 | 298 | Bylaw amendments with exhibit |

**Key insight:** Item 9.01 is almost never meaningful by itself — it's the exhibit index. The real event is always in the other items. When analyzing what an 8-K is "about," ignore 9.01 and look at the other items.

---

## 4. The Four Content Layers

Every 8-K can have up to 4 types of attached content in Neo4j:

| Layer | Node Label | Relationship | Avg Size | 8-Ks Having It | % |
|---|---|---|---|---|---|
| **Sections** | ExtractedSectionContent | `Report-[:HAS_SECTION]->` | 1.4 KB | 23,785 | 99.8% |
| **Exhibits** | ExhibitContent | `Report-[:HAS_EXHIBIT]->` | 24–205 KB | 16,000 | 67% |
| **Filing Text** | FilingTextContent | `Report-[:HAS_FILING_TEXT]->` | 690 KB | 494 | 2% |
| **Financial Statements** | FinancialStatementContent | `Report-[:HAS_FINANCIAL_STATEMENT]->` | N/A | **0** | 0% |

**Financial statements are NEVER attached to 8-K filings.** They exist only on 10-K and 10-Q filings.

### Content Layer Combinations

| Combination | Count | % |
|---|---|---|
| Exhibit + Section | 15,643 | **65.6%** |
| Section only | 7,648 | **32.1%** |
| Exhibit + Section + Filing Text | 329 | 1.4% |
| Section + Filing Text | 165 | 0.7% |
| Exhibit only (no section) | 28 | 0.1% |
| Neither | 23 | 0.1% |

---

## 5. Section Types (ExtractedSectionContent)

26 distinct `section_name` values observed across 8-K filings. Section names are the SEC item names with spaces removed.

| section_name | Count | Avg Size | Max Size | Item Code |
|---|---|---|---|---|
| `FinancialStatementsandExhibits` | 18,810 | 531 B | 19 KB | 9.01 |
| `ResultsofOperationsandFinancialCondition` | 8,766 | 1,049 B | 230 KB | 2.02 |
| `RegulationFDDisclosure` | 5,712 | 1,454 B | 22 KB | 7.01 |
| `DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers` | 5,068 | 2,408 B | 23 KB | 5.02 |
| `OtherEvents` | 4,737 | 2,285 B | 231 KB | 8.01 |
| `EntryintoaMaterialDefinitiveAgreement` | 2,523 | 4,433 B | 40 KB | 1.01 |
| `SubmissionofMatterstoaVoteofSecurityHolders` | 2,276 | 2,566 B | 16 KB | 5.07 |
| `CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant` | 1,488 | 784 B | 19 KB | 2.03 |
| `AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear` | 831 | 1,684 B | 10 KB | 5.03 |
| `UnregisteredSalesofEquitySecurities` | 299 | 1,227 B | 10 KB | 3.02 |
| `TerminationofaMaterialDefinitiveAgreement` | 280 | 904 B | 5 KB | 1.02 |
| `CostsAssociatedwithExitorDisposalActivities` | 214 | 2,680 B | 8 KB | 2.05 |
| `CompletionofAcquisitionorDispositionofAssets` | 176 | 2,380 B | 11 KB | 2.01 |
| `MaterialModificationstoRightsofSecurityHolders` | 127 | 1,770 B | 14 KB | 3.03 |
| `NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing` | 55 | 1,539 B | 5 KB | 3.01 |
| `MaterialImpairments` | 53 | 1,769 B | 7 KB | 2.06 |
| `ChangesinRegistrantsCertifyingAccountant` | 41 | 3,405 B | 7 KB | 4.01 |
| `ChangesinControlofRegistrant` | 20 | 517 B | 1 KB | 5.01 |
| `MineSafetyReportingofShutdownsandPatternsofViolations` | 15 | 708 B | 1 KB | 1.04 |
| `TriggeringEventsThatAccelerateorIncreaseaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangement` | 15 | 1,432 B | 6 KB | 2.04 |
| `NonRelianceonPreviouslyIssuedFinancialStatementsoraRelatedAuditReportorCompletedInterimReview` | 14 | 5,280 B | 13 KB | 4.02 |
| `MaterialCybersecurityIncidents` | 12 | 3,388 B | 5 KB | 1.05 |
| `ShareholderNominationsPursuanttoExchangeActRule14a-11` | 10 | 952 B | 5 KB | 5.08 |
| `TemporarySuspensionofTradingUnderRegistrantsEmployeeBenefitPlans` | 10 | 2,744 B | 7 KB | 5.04 |
| `AmendmentstotheRegistrantsCodeofEthics,orWaiverofaProvisionoftheCodeofEthics` | 6 | 1,091 B | 2 KB | 5.05 |
| `BankruptcyorReceivership` | 1 | 2,163 B | 2 KB | 1.03 |

### Section Content Patterns

- **Pointer sections** (avg ~0.5–1.5 KB): Items 9.01, 2.02, 7.01, 2.03 — these typically say "see Exhibit 99.1" and contain minimal text. The real data lives in exhibits.
- **Substantive sections** (avg 2–5 KB): Items 5.02, 8.01, 5.07, 1.01, 4.02 — these contain the actual event details directly in the section body.
- **Hybrid sections**: Item 5.02 sections (2.4 KB avg) are substantive AND may have an employment agreement exhibit attached.

---

## 6. Exhibit Landscape (ExhibitContent)

### Two Major Exhibit Families

| Family | Purpose | Total Count | Avg Size | Content Type |
|---|---|---|---|---|
| **EX-99.x** | Press releases, presentations, supplemental data | ~17,400 | 24–33 KB | Narrative text |
| **EX-10.x** | Material contracts, agreements, employment terms | ~3,400 | 80–205 KB | Legal documents |

### Top Exhibits by Volume

| Exhibit # | Count | Avg Size | Typical Content |
|---|---|---|---|
| EX-99.1 | 14,199 | 24 KB | Press release (earnings, Reg FD announcements) |
| EX-99.2 | 2,676 | 33 KB | Supplemental data, investor presentations |
| EX-10.1 | 2,341 | 205 KB | Primary contract/agreement |
| EX-10.2 | 591 | 114 KB | Secondary contract |
| EX-99.3 | 361 | 29 KB | Additional press release or data tables |
| EX-10.3 | 231 | 87 KB | Third contract/amendment |
| EX-10.4 | 112 | 79 KB | Fourth contract |
| EX-99.01 | 96 | 28 KB | Dirty variant of EX-99.1 |
| EX-99.4 | 64 | 29 KB | Additional supplemental |
| EX-10.5 | 47 | 73 KB | Fifth contract |

### Dirty Exhibit Numbers

101 distinct exhibit numbers exist in the database. Many are non-standard variants:

| Dirty Variant | Standard | Count |
|---|---|---|
| `EX-99.01` | EX-99.1 | 96 |
| `EX-99.-1` | EX-99.1 | 1 |
| `EX-99.1 PR Q3 F23 EA` | EX-99.1 | 1 |
| `EX-99.1 CHARTER` | EX-99.1 | 25 |
| `EX-99.EX-99` | EX-99.1 | 1 |
| `EX-99.EX-99_1` | EX-99.1 | 1 |
| `EX-10.01` | EX-10.1 | 6 |
| `EX-10.1 2` | EX-10.1 | 1 |
| `EX-10.EXECSEVPLAN` | EX-10.x | 1 |
| `EX-10.III` | EX-10.3 | 1 |
| `EX-10.10(M)` | EX-10.10 | 1 (855 KB) |

**Mitigation:** When fetching exhibits, always use query 4D (discovery) first if exact match fails. Match the closest standard number.

---

## 7. Per-Item Content Profiles

For each major item type, where does the real data live?

### Item 2.02 — Earnings (8,847 filings)

| Content combination | Count | % |
|---|---|---|
| Both exhibit + section | 8,262 | 93.4% |
| Section only | 564 | 6.4% |
| Exhibit only | 17 | 0.2% |
| Neither | 4 | 0.05% |

**Strategy: EXHIBIT-FIRST.** Read EX-99.1 (8,200 of 8,279 exhibits = 99%). Section is almost always a pointer ("see Exhibit 99.1"). EX-99.2 appears in 2,034 filings (supplemental data tables, investor presentations).

### Item 7.01 — Regulation FD (5,822 filings)

| Content combination | Count | % |
|---|---|---|
| Both | 4,936 | 84.8% |
| Section only | 864 | 14.8% |
| Exhibit only | 19 | 0.3% |
| Neither | 3 | 0.05% |

**Strategy: EXHIBIT-FIRST.** Read EX-99.1 (investor presentations, pre-announcements). 15% are section-only (usually shorter disclosures).

### Item 1.01 — Material Agreement (2,533 filings)

| Content combination | Count | % |
|---|---|---|
| Both | 1,746 | 68.9% |
| Section only | 785 | 31.0% |
| Exhibit only | 1 | 0.04% |
| Neither | 1 | 0.04% |

**Strategy: CHECK BOTH. Different exhibit profile from earnings:**
- EX-10.1: 1,266 (actual contract, 205 KB avg)
- EX-99.1: 843 (announcement press release, 24 KB avg)
- EX-10.2: 308, EX-99.2: 212, EX-10.3: 110

Section text (4.4 KB avg) often summarizes key deal terms.

### Item 5.02 — Personnel Changes (5,103 filings)

| Content combination | Count | % |
|---|---|---|
| Both | 2,912 | 57.1% |
| Section only | 2,179 | 42.7% |
| Neither | 7 | 0.1% |
| Exhibit only | 5 | 0.1% |

**Strategy: CHECK BOTH.** Section text (2.4 KB avg) contains appointment/departure details. Exhibits (when present) are employment agreements (EX-10.x) or press releases (EX-99.1).

### Item 8.01 — Other Events (4,769 filings)

| Content combination | Count | % |
|---|---|---|
| Both | 3,036 | 63.7% |
| Section only | 1,727 | 36.2% |
| Exhibit only | 4 | 0.1% |
| Neither | 2 | 0.04% |

**Strategy: CHECK BOTH.** This is the most heterogeneous item. Content can be anything: restructuring plans, strategic updates, litigation, share buybacks. Section text (2.3 KB avg) is often substantive.

### Item 5.07 — Shareholder Voting (2,279 filings)

| Content combination | Count | % |
|---|---|---|
| Section only | 1,808 | **79.3%** |
| Both | 470 | 20.6% |
| Neither | 1 | 0.04% |

**Strategy: SECTION-FIRST.** Inverted pattern — data lives in the section itself (2.6 KB avg). Vote tallies, director election results, say-on-pay outcomes are directly embedded. Exhibits rarely add value.

### Item 2.03 — Financial Obligations (1,494 filings)

| Content combination | Count | % |
|---|---|---|
| Both | 987 | 66.1% |
| Section only | 507 | 33.9% |

**Strategy: CHECK BOTH.** Section (784 B avg) is often a pointer to the credit agreement exhibit (EX-10.x). Frequently paired with Item 1.01 (the agreement itself).

### Extraction Strategy Summary

```
EXHIBIT-FIRST (read EX-99.1/EX-10.x before section):
  Item 2.02 Earnings     — 93% have exhibits, 99% are EX-99.1
  Item 7.01 Reg FD        — 85% have exhibits

CHECK BOTH (data may be in either layer):
  Item 1.01 Agreement     — 69% have exhibits (EX-10.1 dominant)
  Item 8.01 Other Events  — 64% have exhibits
  Item 5.02 Personnel     — 57% have exhibits
  Item 2.03 Obligations   — 66% have exhibits

SECTION-FIRST (data usually in section text):
  Item 5.07 Voting         — 79% section only
```

---

## 8. Stock Market Impact by Item Type

### Earnings vs Everything Else

| Category | Filings with Returns | Avg |Adjusted Return| | Avg Adjusted Return | Min | Max |
|---|---|---|---|---|---|
| **Item 2.02 (Earnings)** | 8,601 | **6.78%** | -0.20% | -77.56% | +84.14% |
| **Non-Earnings 8-Ks** | 14,373 | **2.37%** | -0.07% | -77.56% | +277.42% |

Earnings filings produce **2.9x** the average absolute adjusted return of non-earnings filings.

### Non-Earnings Items Ranked by Market Impact

| Item | Name | Filings | Avg |Adj Return| | Direction Bias | Notes |
|---|---|---|---|---|---|
| **7.01** | Reg FD | 3,367 | **3.05%** | Neutral (-0.06%) | Highest-impact non-earnings item |
| **2.01** | Acquisitions | 29 | **2.75%** | Negative (-0.54%) | Acquirer discount (small sample) |
| **2.06** | Impairments | 19 | **2.64%** | Slightly positive (+0.23%) | Small sample |
| **1.05** | Cybersecurity | 10 | **2.60%** | **Strongly negative (-2.46%)** | Breach = bad (tiny sample) |
| **8.01** | Other Events | 3,050 | **2.57%** | Neutral (+0.02%) | Catch-all, large sample |
| **1.01** | Material Agreement | 2,299 | **2.49%** | Neutral (0.00%) | Deals are directionally ambiguous |
| **3.01** | Delisting | 11 | **1.97%** | Positive (+0.63%) | Often planned transfers, not distress |
| **5.02** | Personnel | 3,391 | **1.83%** | Negative (-0.21%) | Departures tend to hurt |
| **2.03** | Financial Obligations | 44 | **1.66%** | Neutral (+0.03%) | Debt issuance is routine |
| **5.07** | Voting | 1,557 | **1.63%** | Neutral (-0.12%) | Routine governance |
| **5.03** | Bylaws | 339 | **1.59%** | Neutral (+0.18%) | Lowest impact |

### Return Data Coverage

| Item | Total Filings | With Daily Return | Coverage |
|---|---|---|---|
| 2.02 | 8,705 | 8,601 | 99% |
| 7.01 | 3,859 | 3,782 | 98% |
| 5.02 | 3,440 | 3,391 | 99% |
| 8.01 | 3,099 | 3,050 | 98% |
| 1.01 | 1,942 | 1,884 | 97% |
| 5.07 | 1,580 | 1,557 | 99% |

Coverage is uniformly excellent (97–99%) across all item types. Returns (daily_stock, daily_macro, hourly_stock, session_stock) live on the `PRIMARY_FILER` relationship, not the Report node.

---

## 9. Market Session Distribution

| Timing | Count | % |
|---|---|---|
| After hours (post_market) | 14,383 | **60.4%** |
| Before open (pre_market) | 8,142 | **34.2%** |
| During trading (in_market) | 972 | 4.1% |
| Market closed (weekends/holidays) | 339 | 1.4% |

94.5% of 8-Ks are filed outside regular trading hours. The `market_session` field lives on the `Report` node.

---

## 10. 8-K/A Amendments

- **514** 8-K/A filings in the database (2.1% of all 8-K + 8-K/A)
- `Report.formType = '8-K/A'` with `Report.isAmendment = true`
- An amendment **supersedes** the original filing for the same items
- Standard queries (4A, 4B, 4H) filter on `formType: '8-K'` and will **not** match amendments
- To include amendments, use query 4H with `formType IN ['8-K', '8-K/A']` or add a separate query

---

## 11. Mental Model — The 3-Level Hierarchy

```
Level 1: FILING TYPE
  └─ 8-K (current event) vs 10-K (annual) vs 10-Q (quarterly)

Level 2: ITEM CODES (what happened — can have multiple per filing)
  ├─ Section 1: Registrant's Business
  │   ├─ 1.01  Material Agreement           (2,533 filings)
  │   ├─ 1.02  Termination of Agreement     (282)
  │   ├─ 1.03  Bankruptcy                   (1)
  │   ├─ 1.04  Mine Safety                  (15)
  │   └─ 1.05  Cybersecurity Incident       (12)
  ├─ Section 2: Financial Information
  │   ├─ 2.01  Acquisition/Disposition      (189)
  │   ├─ 2.02  EARNINGS                     (8,847)  ← Primary use case
  │   ├─ 2.03  Financial Obligation         (1,494)
  │   ├─ 2.04  Triggering Events            (15)
  │   ├─ 2.05  Exit/Disposal Costs          (215)
  │   └─ 2.06  Material Impairments         (54)
  ├─ Section 3: Securities and Trading
  │   ├─ 3.01  Delisting/Transfer           (55)
  │   ├─ 3.02  Unregistered Sales           (304)
  │   └─ 3.03  Rights Modifications         (127)
  ├─ Section 4: Accounting Matters
  │   ├─ 4.01  Accountant Change            (42)
  │   └─ 4.02  Non-Reliance on Financials   (15)
  ├─ Section 5: Corporate Governance
  │   ├─ 5.01  Control Change               (23)
  │   ├─ 5.02  Officer Departure/Appointment (5,103)
  │   ├─ 5.03  Bylaws/Fiscal Year Change    (836)
  │   ├─ 5.04  Benefit Plan Suspension      (10)
  │   ├─ 5.05  Code of Ethics Amendment     (6)
  │   ├─ 5.07  Voting Results               (2,279)
  │   └─ 5.08  Shareholder Nominations      (10)
  ├─ Section 6: ABS Items (6.01–6.05)       — Not in universe
  ├─ Section 7: Regulation FD
  │   └─ 7.01  Reg FD Disclosure            (5,822)
  ├─ Section 8: Other
  │   └─ 8.01  Other Events                 (4,769)
  └─ Section 9: Exhibits
      └─ 9.01  Financial Statements/Exhibits (18,888) ← Companion item

Level 3: CONTENT LAYERS (where to read the actual data)
  ├─ Sections (ExtractedSectionContent)
  │   └─ 26 distinct types, 99.8% of filings, often pointers (avg 1.4 KB)
  ├─ Exhibits (ExhibitContent)
  │   ├─ EX-99.x → Narrative: press releases, presentations (avg 24–33 KB)
  │   └─ EX-10.x → Legal: contracts, agreements (avg 80–205 KB)
  ├─ Filing Text (FilingTextContent)
  │   └─ Raw HTML fallback, 2% of filings, avg 690 KB
  └─ Financial Statements (FinancialStatementContent)
      └─ NEVER on 8-Ks (only 10-K/10-Q)
```

---

## 12. Four Functional Categories

For practical analysis, 8-K filings cluster into four categories:

### A. Earnings (Item 2.02) — 37% of all 8-Ks
- **Market impact:** 6.78% avg absolute adjusted return (highest)
- **Content:** EX-99.1 press release (93.4% have exhibits)
- **Key combos:** 2.02+9.01 (standard), 2.02+7.01+9.01 (with investor deck)
- **Extraction pipeline:** Guidance extraction targets these

### B. Disclosure & Updates (Item 7.01, 8.01) — ~44% combined
- **Market impact:** 2.57–3.05% avg absolute adjusted return
- **Content:** Mixed — 7.01 is exhibit-first, 8.01 is check-both
- **Use cases:** Pre-announcements, guidance revisions, restructurings, buybacks

### C. Deals & Debt (Items 1.01, 2.03, 2.01, 1.02) — ~20% combined
- **Market impact:** 2.49% avg (neutral direction)
- **Content:** EX-10.x contracts (large docs, 80–205 KB avg)
- **Use cases:** M&A, credit facilities, bond issuances

### D. Governance (Items 5.02, 5.07, 5.03, 3.02) — ~34% combined
- **Market impact:** 1.59–1.83% avg (lowest)
- **Content:** Mostly section-only (especially 5.07 at 79%)
- **Use cases:** Executive changes, voting results, bylaw amendments

---

## 13. Key Queries Reference

### Find 8-Ks by Item Code
```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.items CONTAINS $item_code  // e.g., 'Item 2.02'
RETURN r.accessionNo, r.created, r.items, r.market_session
ORDER BY r.created DESC
```

### Content Inventory for a Filing
```cypher
MATCH (r:Report {accessionNo: $accession})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.accessionNo, r.formType, r.created,
       collect(DISTINCT e.exhibit_number) AS exhibits,
       collect(DISTINCT s.section_name) AS sections,
       collect(DISTINCT fs.statement_type) AS financial_stmts,
       count(DISTINCT ft) AS filing_text_count
```

### Read Press Release (EX-99.1)
```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = 'EX-99.1'
RETURN e.content
```

### Read Section Text
```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = $section_name
RETURN s.content
```

### Discover All Exhibits for a Filing
```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
RETURN e.exhibit_number, size(e.content) AS content_length
ORDER BY e.exhibit_number
```

---

*Version 1.0 | 2026-03-14 | Generated from live Neo4j database analysis (23,836 8-K filings)*

---

**Companion file:** `8k_strategy.md` — intuitive walkthrough (Layers 1-8), extraction routing pipeline, stock impact analysis, tier assignments, and actionable architecture decisions.

---

## Appendix: SEC Item Code Quick Reference

Source: Extracted directly from EDGAR filing data in Neo4j (23,836 8-K filings).
These are the exact strings the SEC uses. Verified 2026-03-14.

### 1_materialAgreements
#### 1.01_materialAgreementEntry
#### 1.02_materialAgreementTermination
#### 1.03_bankruptcy
#### 1.04_mineSafety
#### 1.05_cyberIncident

### 2_financialResults
#### 2.01_acquisitionOrDisposition
#### 2.02_resultsOfOperations
#### 2.03_directFinancialObligation
#### 2.04_obligationTriggerEvent
#### 2.05_exitOrDisposalCosts
#### 2.06_materialImpairment

### 3_securitiesAndTrading
#### 3.01_delistingNotice
#### 3.02_unregisteredEquitySales
#### 3.03_securityHolderRightsChange

### 4_accountantChanges
#### 4.01_certifyingAccountantChange
#### 4.02_priorStatementNonReliance

### 5_corporateGovernance
#### 5.01_controlChange
#### 5.02_officerDirectorChange
#### 5.03_bylawAmendment
#### 5.04_benefitPlanSuspension
#### 5.05_ethicsCodeChange
#### 5.06_shellStatusChange
#### 5.07_shareholderVote
#### 5.08_shareholderNomination

### 6_assetBackedSecurities
#### 6.01_absInfoMaterial
#### 6.02_servicerTrusteeChange
#### 6.03_creditEnhancementChange
#### 6.04_missedDistribution
#### 6.05_securitiesActUpdate

### 7_regFD
#### 7.01_regFDDisclosure

### 8_otherEvents
#### 8.01_otherEvents

### 9_financialStatements
#### 9.01_financialStatementsAndExhibits

**Total: 31 item codes defined by the SEC.**
- 26 appear in our database (with at least 1 filing each)
- 6 have zero filings: 5.06, 6.01, 6.02, 6.03, 6.04, 6.05

*Note: Section 6 names (6.01–6.05) are from the SEC Form 8-K instructions, not from our database (no ABS issuers tracked). All other names pulled verbatim from EDGAR filing data.*
