
## 8-K Specialist Enhancement with LangExtract
    https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/


### Context
Analysis of 22,495 8-K reports shows 48,541 ExtractedSectionContent instances across 26 section types. Currently these are text blobs requiring regex/text search at query time.

### Extraction Opportunity
- **Extractable facts**: ~45% of 8-K text contains financial amounts, dates, entity names
- **XBRL linkage**: 81% of extracted entities can map to XBRL concepts when using company-specific taxonomies from their 10-K/10-Q filings (772 of 794 companies have these)
- **Section patterns**: Different section types (MaterialImpairments, DepartureofDirectors, etc.) follow consistent SEC-mandated structures

### Proposed Approach
1. Extract facts from 8-K sections into structured nodes (Amount, Date, Person, Company)
2. Link to company's existing XBRL taxonomy members where applicable
3. Preserve remaining context as properties on nodes
4. Mark boilerplate/references for filtering

### Cost Estimate
- One-time historical: ~$290 (Gemini 2.5 Pro for 68M tokens)
- Ongoing: ~$438/year for new filings

### What Needs Research
- **Exhibit parsing**: 97% of ResultsofOperations sections just reference EX-99.1 exhibits - should we parse exhibits (avg 23KB) or just sections (avg 1KB)?
- **Extraction schemas**: Need to define specific extraction patterns for each of 26 section types
- **Company taxonomy loading**: Efficient method to load/cache company-specific XBRL taxonomies for context
- **Incremental updates**: Strategy for processing new 8-Ks daily without reprocessing

### Expected Benefit
- Query performance: 100x faster than text search
- Enables aggregation queries impossible with text
- 90% of queries answerable from extracted nodes, 10% fallback to original text

### Span Contract
**IMPORTANT**: All text spans use 0-based, half-open intervals [start, end).
- `span_start`: Inclusive starting position (0-based)
- `span_end`: Exclusive ending position
- Example: span [10, 15) extracts characters at positions 10, 11, 12, 13, 14
- Verification: `content[span_start:span_end]` should exactly match extracted text

---

## Critical Findings from Deep Analysis

### Content Node Types in 8-Ks
1. **ExtractedSectionContent**: 48,541 instances, avg 1.4KB (parsed sections)
2. **ExhibitContent**: 19,604 instances, avg 49.7KB (attached documents, 35x larger!)
3. **FilingTextContent**: 459 instances, avg 695KB (fallback for parsing failures)

### Key Discovery: Data Location Varies by Event Type
| Event Type | Count | Have Exhibits | Primary Data Location |
|------------|-------|---------------|----------------------|
| Results of Operations | 8,027 | 93.3% | EX-99.1 press release |
| Acquisitions | 164 | 83.5% | Both section + exhibit |
| Material Agreements | 2,399 | 68.9% | Exhibit (EX-10.x) |
| Personnel Changes | 4,830 | 56.9% | Section itself |
| Material Impairments | 49 | 34.7% | Section itself |
| Voting Results | 2,254 | 20.6% | Section only |

**Critical Insight**: 33.5% of 8-Ks have NO exhibits - data only in sections!

### Optimal Strategy: Three-Bucket Approach

#### Bucket 1: Section-Primary (Extract Section Only)
- Voting Results, Material Impairments, Personnel Changes
- ~7,100 sections with data directly embedded
- Cost: $50

#### Bucket 2: Exhibit-Primary (Skip Section, Extract Exhibit)  
- Results of Operations → EX-99.1 press releases
- ~7,500 exhibits with rich financial data
- Cost: $150

#### Bucket 3: Hybrid (Extract Both & Merge)
- Acquisitions, Material Agreements
- ~2,500 events needing both sources
- Cost: $50

### Source-Linked Architecture (Key Innovation)
```cypher
// Every extracted node traces back to source
(Impairment {amount: 162500000})
    -[:EXTRACTED_FROM]->(ExtractedSectionContent {id: 'esc_123'})
    
// Enables surgical text access when needed (not broad search)
MATCH (i:Impairment)-[:EXTRACTED_FROM]->(source)
WHERE i.amount > 100000000
RETURN i.amount, source.content  // Direct traversal, no search
```

### Coverage Analysis
- **With sections only**: 45% coverage (miss earnings data)
- **With exhibits only**: 66.5% coverage (miss impairments, votes)
- **With both + smart routing**: 99.9% coverage
- **Text search elimination**: 99.9% (only 0.1% truly novel keywords)

### XBRL Linkage Enhancement via Company Context
- Load company's XBRL taxonomy from their 10-K/10-Q
- Use their specific Members (executives, segments, acquisitions)
- Result: 81% linkage (vs 45% without context)
- Example: "SolarCity" → tsla:SolarCityMember (already exists!)

### Implementation Notes
- **Single specialist** with routing logic (not multiple sub-agents)
- **Deduplication** needed when both section + exhibit extracted
- **Boilerplate filtering** critical (~60% of section text is legal disclaimers)



### Guidance

 - Maybe can link guidnace for each type of section etc. above
 - use sec-api to search for guidance from 10-K/10-Q seperately to make a comprehensive set

#### Other report types like 425, 6-k, SC TO-I, SCHEDULE 13D, SC 14D9
 - ignore or handle with simple regex


  extraction_priority = {
      "MUST EXTRACT": [
          "8-K",        # 22,495 reports - material events
      ],

      "ALREADY STRUCTURED": [
          "10-K",       # 2,091 reports - have XBRL
          "10-Q",       # 5,383 reports - have XBRL
      ],

      "SKIP (Low Value)": [
          "425",        # 711 - merger comms, mostly narrative
          "6-K",        # 26 - foreign, no standard
          "SC TO-I",    # 8 - too few
          "SC 14D9",    # 4 - too few
      ],

      "MAYBE (If Needed)": [
          "SCHEDULE 13D",  # 276 - ownership, simple facts
      ]
  }




# Cycpher Query for Analysis

### 1. Get value-counts of all reports including **8-K reports**
    MATCH (n:Report)
    WITH n.formType AS FormType, COUNT(*) AS Reports
    WITH SUM(Reports) AS total, collect({FormType: FormType, Reports: Reports}) AS data
    UNWIND data AS row
    RETURN row.FormType AS FormType,
        row.Reports AS Reports,
        ROUND(100.0 * row.Reports / total, 1) AS `%Reports`
    ORDER BY Reports DESC;


1. **8-K** – Reports: 23,097, %Reports: 70.7%  
2. **10-Q** – Reports: 5,642, %Reports: 17.3%  
3. **10-K** – Reports: 2,234, %Reports: 6.8%  
4. **425** – Reports: 746, %Reports: 2.3%  
5. **8-K/A** – Reports: 498, %Reports: 1.5%  
6. **SCHEDULE 13D/A** – Reports: 268, %Reports: 0.8%  
7. **10-K/A** – Reports: 107, %Reports: 0.3%  
8. **10-Q/A** – Reports: 30, %Reports: 0.1%  
9. **6-K** – Reports: 26, %Reports: 0.1%  
10. **SCHEDULE 13D** – Reports: 23, %Reports: 0.1%  
11. **SC TO-I** – Reports: 8, %Reports: 0.0%  
12. **SC 14D9** – Reports: 4, %Reports: 0.0%  


### 2. All node types (8-k report) links to (ex ['MarketIndex','Sector','Industry','Company', 'AdminReport'])
    // Value counts by connected node label (1-hop), with % of 8-K reports
    CALL { MATCH (r:Report {formType:'8-K'}) RETURN COUNT(r) AS total_reports }

    MATCH (r:Report {formType:'8-K'})--(n)
    WITH total_reports, r, n,
        [x IN labels(n) WHERE NOT x IN ['MarketIndex','Sector','Industry','Company','AdminReport']] AS kept
    UNWIND kept AS Label
    WITH total_reports, Label, COLLECT(DISTINCT r) AS Rs, COLLECT(DISTINCT n) AS Ns
    RETURN Label,
        SIZE(Rs) AS Reports,
        ROUND(100.0 * SIZE(Rs) / total_reports, 1) AS `%Reports`,
        SIZE(Ns) AS Occurrences
    ORDER BY Reports DESC;


1. **ExtractedSectionContent** – Reports: 23,047, %Reports: 99.8%, Occurrences: 49,889  
2. **ExhibitContent** – Reports: 15,443, %Reports: 66.9%, Occurrences: 20,248  
3. **FilingTextContent** – Reports: 474, %Reports: 2.1%, Occurrences: 474  


### 3. Value Count of section_name field in **ExtractedSectionContent** (8-K only)
    CALL { MATCH (r:Report {formType:'8-K'}) RETURN COUNT(r) AS total_reports }
    CALL { MATCH (:Report {formType:'8-K'})--(:ExtractedSectionContent) RETURN COUNT(*) AS total_occurrences }

    MATCH (r:Report {formType:'8-K'})
    OPTIONAL MATCH (r)-[:HAS_SECTION]->(e:ExtractedSectionContent)
    WITH total_reports, total_occurrences, e.section_name AS section_name, COUNT(DISTINCT r) AS reports
    WHERE section_name IS NOT NULL
    RETURN section_name AS Section,
        reports AS Reports,
        ROUND(100.0 * reports / total_reports, 1) AS `%Reports`,
        ROUND(100.0 * reports / total_occurrences, 1) AS `%AllSections`
    ORDER BY Reports DESC


**(%AllSections, %Reports, #Reports) SectionName**
1. (36%, 79%, #18175) FinancialStatementsandExhibits
2. (17%, 36%, #8399) ResultsofOperationsandFinancialCondition
3. (11%, 24%, #5547) RegulationFDDisclosure
4. (10%, 21%, #4916) DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers
5. (9%, 20%, #4592) OtherEvents
6. (5%, 10.6%, #2445) EntryintoaMaterialDefinitiveAgreement
7. (4.5%, 9.8%, #2266) SubmissionofMatterstoaVoteofSecurityHolders
8. (2.9%, 6.2%, #1440) CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant
9. (1.6%, 3.5%, #815) AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear
10. (0.6%, 1.3%, #291) UnregisteredSalesofEquitySecurities
11. (0.5%, 1.2%, #270) TerminationofaMaterialDefinitiveAgreement
12. (0.4%, 0.9%, #209) CostsAssociatedwithExitorDisposalActivities
13. (0.3%, 0.7%, #165) CompletionofAcquisitionorDispositionofAssets
14. (0.2%, 0.5%, #122) MaterialModificationstoRightsofSecurityHolders
15. (0.1%, 0.2%, #49) NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing
16. (0.1%, 0.2%, #49) MaterialImpairments
17. (0.1%, 0.2%, #41) ChangesinRegistrantsCertifyingAccountant
18. (0.0%, 0.1%, #17) ChangesinControlofRegistrant
19. (0.0%, 0.1%, #15) MineSafetyReportingofShutdownsandPatternsofViolations
20. (0.0%, 0.1%, #14) NonRelianceonPreviouslyIssuedFinancialStatementsoraRelatedAuditReportorCompletedInterimReview
21. (0.0%, 0.1%, #14) TriggeringEventsThatAccelerateorIncreaseaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangement
22. (0.0%, 0.1%, #12) MaterialCybersecurityIncidents
23. (0.0%, 0.0%, #10) ShareholderNominationsPursuanttoExchangeActRule14a-11
24. (0.0%, 0.0%, #9) TemporarySuspensionofTradingUnderRegistrantsEmployeeBenefitPlans
25. (0.0%, 0.0%, #6) AmendmentstotheRegistrantsCodeofEthics,orWaiverofaProvisionoftheCodeofEthics
26. (0.0%, 0.0%, #1) BankruptcyorReceivership


### 4. Value Count of exhibit_number field in **ExhibitContent**

**note: primarily only 2 types of exhibits - EX-10 and EX-99**
    // Value counts by EX base (e.g., EX-10, EX-99), with %s
    CALL { MATCH (r:Report {formType:'8-K'}) RETURN COUNT(r) AS total_reports }
    CALL { MATCH (:Report {formType:'8-K'})--(:ExhibitContent) RETURN COUNT(*) AS total_exhibits }

    MATCH (r:Report {formType:'8-K'})--(x:ExhibitContent)
    WITH total_reports, total_exhibits, r, toUpper(replace(x.exhibit_number,' ','')) AS ex
    WITH total_reports, total_exhibits, r, head(split(replace(ex,'EX-',''),'.')) AS base
    WITH total_reports, total_exhibits, r, 'EX-' + base AS ex_base
    WITH total_reports, total_exhibits, ex_base,
        COUNT(*) AS exhibits, COUNT(DISTINCT r) AS reports
    RETURN ex_base        AS ExhibitBase,
        exhibits       AS Exhibits,
        ROUND(100.0*exhibits/total_exhibits,1) AS `%AllExhibits`,
        reports        AS Reports,
        ROUND(100.0*reports/total_reports,1)   AS `%Reports`
    ORDER BY Exhibits DESC;

**(%AllExhibits, %Reports, #Reports) ExhibitBase**
1. (83%, 60%, #13830) EX-99
2. (17%, 10%, #2326) EX-10


    // Per-exhibit: counts + % of all exhibits + % of reports containing it
    CALL { MATCH (r:Report {formType:'8-K'}) RETURN COUNT(r) AS total_reports }
    CALL { MATCH (:Report {formType:'8-K'})--(:ExhibitContent) RETURN COUNT(*) AS total_exhibits }

    MATCH (r:Report {formType:'8-K'})
    OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(x:ExhibitContent)
    WITH total_reports, total_exhibits, r, x, x.exhibit_number AS ex
    WHERE ex IS NOT NULL
    WITH total_reports, total_exhibits, ex,
        COUNT(x) AS exhibits,            // total ExhibitContent nodes with this number
        COUNT(DISTINCT r) AS reports     // reports that include at least one
    RETURN ex AS exhibit_number,
        exhibits AS Exhibits,
        ROUND(100.0 * exhibits / total_exhibits, 1) AS `%AllExhibits`,
        reports AS Reports,
        ROUND(100.0 * reports / total_reports, 1) AS `%Reports`
    ORDER BY Exhibits DESC, exhibit_number


**(%AllExhibits, %Reports, #Reports) ExhibitNumber – Meaning**
1.  (68%, 59%, #13687) EX-99.1 – Additional exhibits (commonly earnings press release)
2.  (13%, 11%, #2579) EX-99.2 – Additional exhibits (commonly investor presentation/supplemental info)
3.  (11%, 10%, #2274) EX-10.1 – Material contract or agreement
4.  (2.9%, 2.5%, #579) EX-10.2 – Material contract or agreement
5.  (1.7%, 1.5%, #351) EX-99.3 – Additional exhibits (miscellaneous supplemental)
6.  (1.1%, 1.0%, #225) EX-10.3 – Material contract or agreement
7.  (0.5%, 0.5%, #111) EX-10.4 – Material contract or agreement
8.  (0.5%, 0.4%, #93) EX-99.01 – Additional exhibits (press release variant)
9.  (0.3%, 0.3%, #60) EX-99.4 – Additional exhibits (supplemental info)
10. (0.2%, 0.2%, #47) EX-10.5 – Material contract or agreement
11. (0.1%, 0.1%, #25) EX-10.6 – Material contract or agreement
12. (0.1%, 0.1%, #25) EX-99.1 CHARTER – Additional exhibits (corporate charter/bylaws excerpt)
13. (0.1%, 0.1%, #16) EX-99.5 – Additional exhibits (miscellaneous)
14. (0.1%, 0.1%, #13) EX-10.7 – Material contract or agreement
15. (0.0%, 0.0%, #8)  EX-99.1(A) – Additional exhibits (appendix to press release)
16. (0.0%, 0.0%, #7)  EX-10.8 – Material contract or agreement
17. (0.0%, 0.0%, #7)  EX-10.9 – Material contract or agreement
18. (0.0%, 0.0%, #7)  EX-99.6 – Additional exhibits (miscellaneous)
19. (0.0%, 0.0%, #6)  EX-10.01 – Material contract or agreement
20. (0.0%, 0.0%, #6)  EX-99.02 – Additional exhibits (variant)
21. (0.0%, 0.0%, #5)  EX-99.7 – Additional exhibits (miscellaneous)
22. (0.0%, 0.0%, #3)  EX-10.12 – Material contract or agreement
23. (0.0%, 0.0%, #3)  EX-10.1A – Material contract or agreement (amendment/attachment)
24. (0.0%, 0.0%, #3)  EX-10.1B – Material contract or agreement (amendment/attachment)
25. (0.0%, 0.0%, #3)  EX-10.1C – Material contract or agreement (amendment/attachment)
26. (0.0%, 0.0%, #3)  EX-10.1D – Material contract or agreement (amendment/attachment)
27. (0.0%, 0.0%, #3)  EX-99.1A – Additional exhibits (variant)
28. (0.0%, 0.0%, #3)  EX-99.1PRE – Additional exhibits (pre-release)
29. (0.0%, 0.0%, #3)  EX-99.8 – Additional exhibits (miscellaneous)
30. (0.0%, 0.0%, #3)  EX-99.9 – Additional exhibits (miscellaneous)
31. (0.0%, 0.0%, #2)  EX-10.10 – Material contract or agreement
32. (0.0%, 0.0%, #2)  EX-10.11 – Material contract or agreement
33. (0.0%, 0.0%, #2)  EX-10.13 – Material contract or agreement
34. (0.0%, 0.0%, #2)  EX-10.1E – Material contract or agreement (amendment/attachment)
35. (0.0%, 0.0%, #2)  EX-10.1F – Material contract or agreement (amendment/attachment)
36. (0.0%, 0.0%, #2)  EX-10.1G – Material contract or agreement (amendment/attachment)
37. (0.0%, 0.0%, #2)  EX-10.1H – Material contract or agreement (amendment/attachment)
38. (0.0%, 0.0%, #2)  EX-10.1I – Material contract or agreement (amendment/attachment)
39. (0.0%, 0.0%, #2)  EX-10.1J – Material contract or agreement (amendment/attachment)
40. (0.0%, 0.0%, #2)  EX-10.1K – Material contract or agreement (amendment/attachment)
41. (0.0%, 0.0%, #2)  EX-10.1L – Material contract or agreement (amendment/attachment)
42. (0.0%, 0.0%, #2)  EX-10.A – Material contract or agreement (alternate format)
43. (0.0%, 0.0%, #2)  EX-99.10 – Additional exhibits (miscellaneous)
44. (0.0%, 0.0%, #2)  EX-99.11 – Additional exhibits (miscellaneous)
45. (0.0%, 0.0%, #2)  EX-99.12 – Additional exhibits (miscellaneous)
46. (0.0%, 0.0%, #2)  EX-99.1B – Additional exhibits (variant)
47. (0.0%, 0.0%, #1)  EX-10.1 2 – Material contract or agreement
48. (0.0%, 0.0%, #1)  EX-10.10(M) – Material contract (specific amendment)
49. (0.0%, 0.0%, #1)  EX-10.10(N) – Material contract (specific amendment)
50. (0.0%, 0.0%, #1)  EX-10.10(O) – Material contract (specific amendment)
51. (0.0%, 0.0%, #1)  EX-10.10(P) – Material contract (specific amendment)
52. (0.0%, 0.0%, #1)  EX-10.12K – Material contract or agreement
53. (0.0%, 0.0%, #1)  EX-10.15 – Material contract or agreement
54. (0.0%, 0.0%, #1)  EX-10.16 – Material contract or agreement
55. (0.0%, 0.0%, #1)  EX-10.18 – Material contract or agreement
56. (0.0%, 0.0%, #1)  EX-10.1M – Material contract (amendment/attachment)
57. (0.0%, 0.0%, #1)  EX-10.1N – Material contract (amendment/attachment)
58. (0.0%, 0.0%, #1)  EX-10.1O – Material contract (amendment/attachment)
59. (0.0%, 0.0%, #1)  EX-10.1P – Material contract (amendment/attachment)
60. (0.0%, 0.0%, #1)  EX-10.1Q – Material contract (amendment/attachment)
61. (0.0%, 0.0%, #1)  EX-10.1R – Material contract (amendment/attachment)
62. (0.0%, 0.0%, #1)  EX-10.25 – Material contract or agreement
63. (0.0%, 0.0%, #1)  EX-10.26 – Material contract or agreement
64. (0.0%, 0.0%, #1)  EX-10.27 – Material contract or agreement
65. (0.0%, 0.0%, #1)  EX-10.32 – Material contract or agreement
66. (0.0%, 0.0%, #1)  EX-10.36 – Material contract or agreement
67. (0.0%, 0.0%, #1)  EX-10.37 – Material contract or agreement
68. (0.0%, 0.0%, #1)  EX-10.40 – Material contract or agreement
69. (0.0%, 0.0%, #1)  EX-10.5 10 – Material contract (specific numbered addendum)
70. (0.0%, 0.0%, #1)  EX-10.5 11 – Material contract (specific numbered addendum)
71. (0.0%, 0.0%, #1)  EX-10.5 8 – Material contract (specific numbered addendum)
72. (0.0%, 0.0%, #1)  EX-10.5 9 – Material contract (specific numbered addendum)
73. (0.0%, 0.0%, #1)  EX-10.62 – Material contract or agreement
74. (0.0%, 0.0%, #1)  EX-10.6A – Material contract (appendix/attachment)
75. (0.0%, 0.0%, #1)  EX-10.6B – Material contract (appendix/attachment)
76. (0.0%, 0.0%, #1)  EX-10.74 – Material contract or agreement
77. (0.0%, 0.0%, #1)  EX-10.75 – Material contract or agreement
78. (0.0%, 0.0%, #1)  EX-10.7D – Material contract (amendment/attachment)
79. (0.0%, 0.0%, #1)  EX-10.7E – Material contract (amendment/attachment)
80. (0.0%, 0.0%, #1)  EX-10.8A – Material contract (appendix/attachment)
81. (0.0%, 0.0%, #1)  EX-10.EXECSEVPLAN – Executive severance plan agreement
82. (0.0%, 0.0%, #1)  EX-10.III – Material contract or agreement
83. (0.0%, 0.0%, #1)  EX-99.(10)(1) – Additional exhibits (miscellaneous)
84. (0.0%, 0.0%, #1)  EX-99.-1 – Additional exhibits (miscellaneous)
85. (0.0%, 0.0%, #1)  EX-99.03 – Additional exhibits (miscellaneous)
86. (0.0%, 0.0%, #1)  EX-99.04 – Additional exhibits (miscellaneous)
87. (0.0%, 0.0%, #1)  EX-99.05 – Additional exhibits (miscellaneous)
88. (0.0%, 0.0%, #1)  EX-99.1 PR Q3 F23 EA – Additional exhibits (press release for earnings announcement)
89. (0.0%, 0.0%, #1)  EX-99.13 – Additional exhibits (miscellaneous)
90. (0.0%, 0.0%, #1)  EX-99.14 – Additional exhibits (miscellaneous)
91. (0.0%, 0.0%, #1)  EX-99.15 – Additional exhibits (miscellaneous)
92. (0.0%, 0.0%, #1)  EX-99.16 – Additional exhibits (miscellaneous)
93. (0.0%, 0.0%, #1)  EX-99.17 – Additional exhibits (miscellaneous)
94. (0.0%, 0.0%, #1)  EX-99.18 – Additional exhibits (miscellaneous)
95. (0.0%, 0.0%, #1)  EX-99.19 – Additional exhibits (miscellaneous)
96. (0.0%, 0.0%, #1)  EX-99.2 Q3 F23 SUPPL – Additional exhibits (supplemental earnings materials)
97. (0.0%, 0.0%, #1)  EX-99.20 – Additional exhibits (miscellaneous)
98. (0.0%, 0.0%, #1)  EX-99.21 – Additional exhibits (miscellaneous)
99. (0.0%, 0.0%, #1)  EX-99.22 – Additional exhibits (miscellaneous)
100. (0.0%, 0.0%, #1) EX-99.3 PR APPOINTME – Additional exhibits (press release for appointment)
101. (0.0%, 0.0%, #1) EX-99.A – Additional exhibits (miscellaneous)
102. (0.0%, 0.0%, #1) EX-99.EX-99 – Additional exhibits (miscellaneous)
103. (0.0%, 0.0%, #1) EX-99.EX-99_1 – Additional exhibits (miscellaneous)
104. (0.0%, 0.0%, #1) EX-99.EX-99_2 – Additional exhibits (miscellaneous)


### Get All XBRL nodes linked to Fact
    MATCH (:Fact)-[]-(n)
    RETURN labels(n) AS node_labels, COUNT(DISTINCT n) AS nodes
    ORDER BY nodes DESC, node_labels;

["Context"]
["Fact"]
["Member"]
["Concept"]
["Abstract"]
["Period"]
["XBRLNode"]
["Unit"]
["Dimension"]


### SEC Item codes

---

## Plan (To be Reviewed)

**Primary Purpose**
First of all since this was written by an AI, I need to be able to understand each compoent in great detail but in simplest language possible. Let me tell you what i Have in mind and then you can tell me how its set up exactly in step by step manner in a way thats super easy to understand and remember. Look the idea is first for each company separately, we get all its Dimension & Member and Context linked to facts for all reports for a particular company - these are company specific anyway. Then we start with company-specific fact-linked XBRL concepts as well as Unit and Period which are typically generic but constraining it to company will likely result in more accurate xbrl-linking. Next step is using LangExtract we go report (8-K) by report or 8-k report section by section and link these all if possible. For the ones which are not linked to any (Concept, Unit, Period) we can look for any other database-wide concepts, Unit & Period. while concept have to be 100% from the database, for period (& maybe Unit)If those are also not appropriate we have few options - Create 8-k specific period (also can be used with context since its simply period + company) and use those. company-specific Dimension and or member (more appropriately) should be linked to extracted 8k-facts whenever applicable and possible to make better sense of data.  Other minor details are each 8k-fact is linked to its respective section or report as case maybe. For each specific section type, we ned to provide a different extraction schema to LangExtract so it can do the job well. Ideally, all facts mentioned in the 8-k sections/reports are 100% properly extracted and linked to xbrl concepts, unit, period, context. Any related textual data or value will be a property of that 8k-fact node. Overall this is the primary requirement so first how well is our plan implementing this. second is there anything in the plan which is unnecessary to this primary purpose since ideally we would like most minimalistic yet 100% reliable implementation. 


**Why we’re doing this (context)**
We want a deterministic, production-safe way to extract facts from 8-K filings (sections + exhibits), route them by SEC Item code, and link as many as possible to existing XBRL concepts/contexts—so downstream teams can query 8-K facts just like 10-K/10-Q XBRL facts. Reliability (traceable spans, idempotent writes, clean rollback) beats heuristics. Minimalism matters: only create links we can prove (concept/unit/period), and keep everything auditable.

### Phase 1: Content Classification & Routing

#### 1.1 Deterministic Content Routing

**Step 1: Create Canonical Section to Item Mapping**
```python
def canon_key(s: str) -> str:
    """Strip all non-alphanumeric chars and uppercase for deterministic matching"""
    return re.sub(r'[^A-Z0-9]', '', s.upper())

# Complete mapping from database section_name values to SEC Item codes
SECTION_TO_ITEM = {
    'ENTRYINTOAMATERIALDEFINITIVEAGREEMENT': '1.01',
    'TERMINATIONOFAMATERIALDEFINITIVEAGREEMENT': '1.02',
    'BANKRUPTCYORRECEIVERSHIP': '1.03',
    'MINESAFETYREPORTINGOFSHUTDOWNSANDPATTERNSOFVIOLATIONS': '1.04',
    'MATERIALCYBERSECURITYINCIDENTS': '1.05',
    'COMPLETIONOFACQUISITIONORDISPOSITIONOFASSETS': '2.01',
    'RESULTSOFOPERATIONSANDFINANCIALCONDITION': '2.02',
    'CREATIONOFADIRECTFINANCIALOBLIGATIONORANOBLIGATIONUNDERANOFFBALANCESHEETARRANGEMENTOFAREGISTRANT': '2.03',
    'TRIGGERINGEVENTSTHATACCELERATEORINCREASEADIRECTFINANCIALOBLIGATIONORANOBLIGATIONUNDERANOFFBALANCESHEETARRANGEMENT': '2.04',
    'COSTSASSOCIATEDWITHEXITORDISPOSALACTIVITIES': '2.05',
    'MATERIALIMPAIRMENTS': '2.06',
    'NOTICEOFDELISTINGORFAILURETOSATISFYACONTINUEDLISTINGRULEORSTANDARDTRANSFEROFLISTING': '3.01',
    'UNREGISTEREDSALESOFEQUITYSECURITIES': '3.02',
    'MATERIALMODIFICATIONSTORIGHTSOFSECURITYHOLDERS': '3.03',
    'CHANGESINREGISTRANTSCERTIFYINGACCOUNTANT': '4.01',
    'NONRELIANCEONPREVIOUSLYISSUEDFINANCIALSTATEMENTSORARELATEDAUDITREPORTORCOMPLETEDINTERIMREVIEW': '4.02',
    'CHANGESINCONTROLOFREGISTRANT': '5.01',
    'DEPARTUREOFDIRECTORSORCERTAINOFFICERSELECTIONOFDIRECTORSAPPOINTMENTOFCERTAINOFFICERSCOMPENSATORYARRANGEMENTSOFCERTAINOFFICERS': '5.02',
    'AMENDMENTSTOARTICLESOFINCORPORATIONORBYLAWSCHANGEINFISCALYEAR': '5.03',
    'TEMPORARYSUSPENSIONOFTRADINGUNDERREGISTRANTSEMPLOYEEBENEFITPLANS': '5.04',
    'AMENDMENTSTOTHEREGISTRANTSCODEOFETHICSORWAIVEROFAPROVISIONOFTHECODEOFETHICS': '5.05',
    'CHANGEINSHELLCOMPANYSTATUS': '5.06',
    'SUBMISSIONOFMATTERSTOAVOTEOFSECURITYHOLDERS': '5.07',
    'SHAREHOLDERNOMINATIONSPURSUANTTOEXCHANGEACTRULE14A11': '5.08',
    'REGULATIONFDDISCLOSURE': '7.01',
    'OTHEREVENTS': '8.01',
    'FINANCIALSTATEMENTSANDEXHIBITS': '9.01'
}
```

**Step 2: Generate and Persist Routing Keys (Pre-compute in Python)**
```python
import hashlib

def generate_routing_key(node):
    """Generate deterministic routing key for any content node"""
    if isinstance(node, ExtractedSectionContent):
        canon = canon_key(node.section_name)
        item = SECTION_TO_ITEM.get(canon, 'UNKNOWN')
        return f"ESC:{item}"
    elif isinstance(node, ExhibitContent):
        # Will be determined after explicit reference parsing
        return f"EXH:{canon_exhibit(node.exhibit_number)}:PENDING"
    elif isinstance(node, FilingTextContent):
        return "FTC:UNKNOWN"

def compute_source_hash(content: str) -> str:
    """Compute SHA256 hash of RAW content for span verification
    CRITICAL: Do NOT normalize content before hashing!
    Hash must match the exact stored content so spans remain valid forever.
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Pre-compute in Python, then persist
for section in sections:
    routing_key = generate_routing_key(section)
    source_hash = compute_source_hash(section.content)
    
    # Update via Cypher with pre-computed values
    query = """
    MATCH (n:ExtractedSectionContent {id: $id})
    SET n.routing_key = $routing_key,
        n.source_sha256 = $source_hash
    """
    run_query(query, {'id': section.id, 'routing_key': routing_key, 'source_hash': source_hash})

# Similarly for exhibits
for exhibit in exhibits:
    exhibit_canon = canon_exhibit(exhibit.exhibit_number)
    source_hash = compute_source_hash(exhibit.content)
    
    query = """
    MATCH (x:ExhibitContent {id: $id})
    SET x.exhibit_canon = $exhibit_canon,
        x.source_sha256 = $source_hash,
        x.routing_key = 'EXH:' + $exhibit_canon + ':PENDING'
    """
    run_query(query, {'id': exhibit.id, 'exhibit_canon': exhibit_canon, 'source_hash': source_hash})

# And for FilingTextContent (fallback nodes)
for filing_text in filing_texts:
    source_hash = compute_source_hash(filing_text.content)
    
    query = """
    MATCH (f:FilingTextContent {id: $id})
    SET f.source_sha256 = $source_hash,
        f.routing_key = 'FTC:UNKNOWN'
    """
    run_query(query, {'id': filing_text.id, 'source_hash': source_hash})
```

#### 1.2 Special Case: Item 7.01 Routing Logic

**Step 1: Implement 7.01 Gating**
```python
def route_item_to_schema(item: str, content: str = None, normalized_header: str = None) -> str:
    """Route Item to extraction schema with special 7.01 handling"""
    
    # Special case: Item 7.01 defaults to FD
    if item == '7.01':
        if content and has_earnings_exhibit_ref(content, normalized_header):
            return 'EARNINGS'  # Only if explicit EX-99.1/99.2 reference
        return 'FD'  # Default for Regulation FD
    
    # Standard mapping for all other items
    return ITEM_TO_SCHEMA.get(item, 'OTHER')

def has_earnings_exhibit_ref(content: str, normalized_header: str = None) -> bool:
    """Check if content explicitly references earnings exhibits"""
    # Use pre-normalized header if provided, else normalize here
    header = normalized_header or normalize_for_matching(content[:2000])
    patterns = ['EX-99.1', 'EXHIBIT 99.1', 'EX 99.1', 'EX-99.2', 'EXHIBIT 99.2']
    return any(p in header for p in patterns)
```

**Step 2: Unit Test for 7.01 Logic**
```python
def test_item_701_routing():
    """Critical test for 7.01 routing logic"""
    
    # Test 1: Plain 7.01 → FD
    content_no_exhibit = "Item 7.01 Regulation FD Disclosure. Company announces partnership."
    assert route_item_to_schema('7.01', content_no_exhibit) == 'FD'
    
    # Test 2: 7.01 with EX-99.1 → EARNINGS
    content_with_exhibit = "Item 7.01 Regulation FD. See Exhibit 99.1 for Q4 earnings."
    assert route_item_to_schema('7.01', content_with_exhibit) == 'EARNINGS'
    
    # Test 3: 7.01 with EX-99.2 → EARNINGS
    content_with_99_2 = "Item 7.01. Presentation attached as Exhibit 99.2"
    assert route_item_to_schema('7.01', content_with_99_2) == 'EARNINGS'
```

#### 1.3 Exhibit Processing

**Step 1: Deterministic Multi-Item Exhibit Routing**
```python
def route_exhibit_to_items(exhibit_canon: str, section_items: List[str]) -> List[str]:
    """Deterministically route exhibits that reference multiple Items"""
    # Map exhibit SERIES to their Item codes (not specific exhibit numbers)
    EXHIBIT_ITEM_MAP = {
        'EX-99': ['2.02', '7.01'],  # EX-99.1, EX-99.2 etc. -> Earnings or FD
        'EX-10': ['1.01', '5.02'],   # EX-10.1, EX-10.2 etc. -> Agreements or compensation
    }
    
    # Get base exhibit type (EX-99, EX-10)
    base = exhibit_canon.split('.')[0] if '.' in exhibit_canon else exhibit_canon
    
    # If sections explicitly reference this exhibit, use those Items
    if section_items:
        return section_items
    
    # Otherwise use deterministic default mapping
    return EXHIBIT_ITEM_MAP.get(base, ['9.01'])  # Default to 9.01
```

**Step 2: Canonicalize Exhibit Numbers**
```python
def canon_exhibit(s: str) -> str:
    """Canonicalize exhibit numbers to standard format"""
    t = re.sub(r'\s+', '', s.upper())  # Remove all spaces
    
    # Normalize EXHIBIT variations to EX-
    t = t.replace('EXHIBIT', 'EX').replace('EX-', 'EX').replace('EX', 'EX-')
    
    # Collapse leading zeros: EX-99.01 → EX-99.1
    t = re.sub(r'\.0+(\d)', r'.\1', t)
    
    # Strip trailing descriptive words but keep valid suffixes
    # Keep: A, B, (M), .III etc.  Strip: CHARTER, PR Q3, etc.
    t = re.sub(r'(EX-\d{2}\.\d+[A-Z]?(?:\([A-Z]\))?)[A-Z ]+.*', r'\1', t)
    
    return t

# Unit test for exhibit canonicalization
test_cases = [
    ("EX-99.01", "EX-99.1"),
    ("Exhibit 99.1", "EX-99.1"),
    ("EX-99.1 CHARTER", "EX-99.1"),
    ("EX-10.10(M)", "EX-10.10(M)"),
    ("EX-99.1A", "EX-99.1A"),
    ("EX 99.01", "EX-99.1"),
    ("EX-99.1 PR Q3 F23 EA", "EX-99.1")
]
```

**Step 3: Parse Explicit References Only**
```python
def find_explicit_references(section_content: str, exhibits_in_report: List[str], normalized_header: str = None) -> List[str]:
    """Find only explicit exhibit references in section header"""
    # Use pre-normalized header if provided, else normalize here
    header = normalized_header or normalize_for_matching(section_content[:2000])
    referenced = []
    
    for exhibit in exhibits_in_report:
        canon = canon_exhibit(exhibit)
        patterns = [
            canon,
            canon.replace('EX-', 'EXHIBIT '),
            canon.replace('EX-', 'EX '),
            f"({canon.replace('EX-', '')})"  # (99.1) format
        ]
        if any(p in header for p in patterns):
            referenced.append(canon)
    
    return referenced
```

**Step 4: Create REFERENCES Edges (with normalization)**
```python
def normalize_for_matching(text: str) -> str:
    """Normalize unicode, whitespace, and special chars for reliable matching
    IMPORTANT: This is ONLY for matching/searching! 
    Never normalize content before computing source_sha256 or storing.
    """
    import re
    # Replace various unicode spaces and special chars
    text = text.replace('\u00A0', ' ')  # NBSP
    text = text.replace('\t', ' ')      # Tab
    text = text.replace('\r', ' ')      # CR
    text = text.replace('\n', ' ')      # LF
    text = text.replace('—', '-')       # Em dash
    text = text.replace('–', '-')       # En dash  
    text = text.replace('\u2011', '-')  # Non-breaking hyphen
    text = text.replace('\u2212', '-')  # Unicode minus
    text = text.replace('\u200B', '')   # Zero-width space (drop)
    # Collapse multiple spaces into single space
    text = re.sub(r'\s+', ' ', text)
    return text.upper()

# Create explicit references - SCOPED to current filing only
# Run once for entire report (set-based, safe)
query = """
WITH $batch_id AS batch_id, $pipeline_id AS pipeline_id, $filing_id AS filing_id
MATCH (r:Report {filing_id: filing_id})  // SCOPE to specific filing (8-K or 8-K/A)
MATCH (r)-[:HAS_EXHIBIT]->(x:ExhibitContent)  // Use specific relationship
WHERE x.exhibit_canon IS NOT NULL
MATCH (r)-[:HAS_SECTION]->(e:ExtractedSectionContent)
WITH e, x, batch_id, pipeline_id,
     toUpper(replace(replace(replace(replace(replace(replace(replace(replace(replace(substring(e.content,0,2000),
       '\u00A0',' '),'\t',' '),'\r',' '),'\n',' '),'—','-'),'–','-'),'\u2011','-'),'\u2212','-'),'\u200B','')) AS header
WHERE header CONTAINS x.exhibit_canon
   OR header CONTAINS replace(x.exhibit_canon,'EX-','EXHIBIT ')
   OR header CONTAINS replace(x.exhibit_canon,'EX-','EX ')
   OR header CONTAINS '(' + replace(x.exhibit_canon,'EX-','') + ')'
MERGE (e)-[ref:REFERENCES]->(x)
SET ref.kind='explicit', 
    ref.batch_id=batch_id, 
    ref.pipeline_id=pipeline_id, 
    ref.created_at=datetime()
"""

# Run once for the entire report, not per-section
run_query(query, {
    'filing_id': report.filing_id,  # SCOPE to current filing
    'batch_id': batch_id,
    'pipeline_id': pipeline_id
})

# After creating REFERENCES, persist exhibit routing keys
query = """
MATCH (x:ExhibitContent)<-[:REFERENCES]-(e:ExtractedSectionContent)
WITH x, collect(DISTINCT e.routing_key) AS keys
WHERE size(keys) > 0
SET x.routing_keys = [k IN keys WHERE NOT k CONTAINS 'UNKNOWN']
"""
run_query(query)

# Fallback routing for exhibits with no section references
query = """
MATCH (x:ExhibitContent)
WHERE coalesce(x.routing_keys, []) = []
WITH x,
     CASE WHEN x.exhibit_canon STARTS WITH 'EX-99' THEN ['ESC:2.02','ESC:7.01']
          WHEN x.exhibit_canon STARTS WITH 'EX-10' THEN ['ESC:1.01','ESC:5.02']
          ELSE ['ESC:9.01'] END AS keys
SET x.routing_keys = keys
"""
run_query(query)

# Clear the PENDING routing_key on exhibits (rely only on routing_keys array)
query = """
MATCH (x:ExhibitContent)
SET x.routing_key = NULL
"""
run_query(query)
```

#### 1.4 Amendment Handling

**Step 1: Track 8-K/A Amendments**
```python
def handle_amendment(report):
    """Track 8-K/A amendments with metadata"""
    if report.formType == '8-K/A':
        # Find the original 8-K being amended (same CIK, earlier date)
        query = """
        MATCH (r:Report {formType: '8-K', cik: $cik})
        WHERE r.filingDate < $amendment_date
        RETURN r.filing_id AS original_filing
        ORDER BY r.filingDate DESC
        LIMIT 1
        """
        original = run_query(query, {'cik': report.cik, 'amendment_date': report.filingDate})
        
        return {
            'is_amendment': True,
            'amends_filing': original['original_filing'] if original else None,
            'routing': 'SAME_AS_ORIGINAL'  # Route same as base 8-K
        }
    return {'is_amendment': False}

def apply_amendment_supersedence(batch_id):
    """Mark facts from original 8-K as superseded by 8-K/A facts"""
    query = """
    // Find amendment facts
    MATCH (amended:EightKFact {batch_id: $batch_id, is_amendment: true})
    WHERE amended.amends_filing IS NOT NULL
    
    // Find corresponding facts from original filing
    MATCH (original:EightKFact {filing_id: amended.amends_filing})
    WHERE original.dedupe_key = amended.dedupe_key
      AND NOT original.superseded
    
    // Mark original as superseded
    SET original.superseded = true,
        original.superseded_by = amended.fact_id
    
    RETURN count(original) AS superseded_count
    """
    return run_query(query, {'batch_id': batch_id})
```

### Phase 2: Text Extraction with LangExtract

#### 2.1 Schema Configuration

**Step 1: Define Extraction Schemas**
```python
# Map Items to extraction schemas
ITEM_TO_SCHEMA = {
    '1.01': 'AGREEMENTS', '1.02': 'AGREEMENTS', '1.03': 'COMPLIANCE',
    '1.04': 'COMPLIANCE', '1.05': 'COMPLIANCE',
    '2.01': 'M&A', '2.02': 'EARNINGS', '2.03': 'DEBT',
    '2.04': 'DEBT', '2.05': 'RESTRUCTURING', '2.06': 'IMPAIRMENT',
    '3.01': 'LISTING', '3.02': 'EQUITY', '3.03': 'EQUITY',
    '4.01': 'AUDIT', '4.02': 'AUDIT',
    '5.01': 'CONTROL', '5.02': 'PERSONNEL', '5.03': 'GOVERNANCE',
    '5.04': 'GOVERNANCE', '5.05': 'GOVERNANCE', '5.06': 'GOVERNANCE',
    '5.07': 'VOTING', '5.08': 'VOTING',
    '7.01': 'FD',  # Default, upgraded to EARNINGS conditionally
    '8.01': 'OTHER', '9.01': 'OTHER'
}

# Define extraction patterns per schema
EXTRACTION_SCHEMAS = {
    'EARNINGS': {
        'facts': ['revenue', 'eps', 'margin', 'guidance'],
        'examples': [...],  # LangExtract examples
        'confidence_threshold': 0.85
    },
    'PERSONNEL': {
        'facts': ['name', 'title', 'effective_date', 'reason'],
        'examples': [...],
        'confidence_threshold': 0.90
    },
    # ... other schemas
}
```

**Step 2: Configure LangExtract**
```python
def configure_langextract(schema_type: str):
    """Configure LangExtract for specific schema"""
    config = EXTRACTION_SCHEMAS[schema_type]
    
    return {
        'model': 'gemini-2.5-flash',
        'examples': config['examples'],
        'track_spans': True,  # Always track character positions
        'confidence_threshold': config['confidence_threshold'],
        'schema_version': '1.0.0',  # Version tracking
        'prompt_version': '1.0.0'
    }
```

#### 2.2 Extraction Process

**Step 1: Extract with Span Tracking**
```python
from decimal import Decimal, ROUND_HALF_UP

def normalize_value_to_abs(value_raw: str, unit: str|None) -> tuple[int|None, str|None]:
    """Convert extracted value to canonical absolute representation
    Returns (value_abs, display_scale)
    """
    import re
    
    if not value_raw:
        return (None, None)
    
    s = value_raw.strip()
    
    # Detect negative values (parentheses, minus, or keywords)
    sign = -1 if re.search(r'^\(|^-\s*|decrease|decline|loss', s.lower()) else 1
    
    # Extract numeric value (handle commas)
    num_match = re.search(r'([\d.,]+)', s.replace(',', ''))
    if not num_match:
        return (None, None)
    
    try:
        q = Decimal(num_match.group(1))
    except:
        return (None, None)
    
    # Detect scale
    scale = Decimal(1)
    display_scale = None
    if re.search(r'\bbillion\b', s, re.I):
        scale = Decimal('1000000000')
        display_scale = 'billion'
    elif re.search(r'\bmillion\b', s, re.I):
        scale = Decimal('1000000')
        display_scale = 'million'
    elif re.search(r'\bthousand\b', s, re.I):
        scale = Decimal('1000')
        display_scale = 'thousand'
    
    # Convert based on unit type
    if unit and re.search(r'\b(usd|dollar|\$)\b', str(unit), re.I):
        # Convert to cents for currency
        q = (q * scale * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return (int(sign * q), display_scale)  # No 'dollars' - that's currency not scale
    
    if unit and re.search(r'%|percent', str(unit), re.I):
        # Convert to basis points for percentages
        q = (q * 10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return (int(sign * q), None)  # No 'percent' display_scale - unit already implies it
    
    # Default: integer representation
    q = (q * scale).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return (int(sign * q), display_scale)

def extract_facts(content: str, schema_type: str, source_hash: str, source_key: str):
    """Extract facts with full span tracking and proper field setup"""
    import re
    config = configure_langextract(schema_type)
    
    # Run extraction
    result = langextract.extract(
        text=content,
        config=config
    )
    
    # Validate spans and set proper fields
    for fact in result.facts:
        assert content[fact.span.start:fact.span.end] == fact.text
        fact.source_hash = source_hash  # Link to immutable source
        # Set span fields directly (not nested)
        fact.span_start = fact.span.start
        fact.span_end = fact.span.end
        fact.source_key = source_key  # section_name or exhibit_canon
        # Cache snippet for debugging
        fact.source_text = content[fact.span_start:min(fact.span_end, fact.span_start + 200)]
        
        # Normalize value to absolute representation
        if hasattr(fact, 'value_raw') and hasattr(fact, 'unit'):
            fact.value_abs, fact.value_display_scale = normalize_value_to_abs(fact.value_raw, fact.unit)
            # Track currency separately
            if fact.unit and re.search(r'\b(usd|dollar|\$)\b', str(fact.unit), re.I):
                fact.currency = 'USD'
    
    return result
```

### Phase 3: EightKFact Node Creation

#### 3.1 Node Schema Definition

**Step 1: Define EightKFact Properties**
```python
class EightKFact:
    # Identification
    fact_id: str           # MD5 hash, deterministic
    filing_id: str         # Use existing property name (not accessionNumber)
    cik: str               # Company CIK for fast filtering
    
    # Values (canonical representation)
    value_raw: str         # "$162.5 million" as extracted
    value_abs: int         # 162500000 absolute value in base units (cents for USD, basis points for %)
    value_display_scale: str  # "million", "billion" for UX (optional)
    currency: str          # "USD" if detected
    
    # Source tracking
    span_start: int
    span_end: int
    source_text: str       # Extracted text snippet (optional cache)
    source_type: str       # 'Section' | 'Exhibit' | 'FilingText'
    
    # Routing & extraction
    routing_key: str       # "ESC:2.06"
    extraction_schema: str # "IMPAIRMENT"
    
    # XBRL mapping
    concept_ref: str       # "us-gaap:GoodwillImpairmentLoss" or None
    mapped: bool           # true if linked to XBRL
    candidate_concepts: List[str]  # Suggestions if unmapped
    mapping_confidence: float
    mapping_method: str    # "direct" | "fuzzy" | "ml"
    completeness: str      # "unmapped" | "concept_only" | "concept_unit" | "concept_unit_period" | "full"
    
    # Deduplication & Amendments
    dedupe_key: str
    superseded: bool       # true if duplicate or amended
    superseded_by: str     # fact_id of preferred version
    is_amendment: bool     # true for 8-K/A facts
    amends_filing: str     # filing_id of original 8-K (if amendment)
    
    # Tracking
    batch_id: str
    pipeline_id: str       # "8K_EXTRACTION_V1"
    extraction_date: str   # ISO date (not created_at for consistency)
    
    # Version tracking (simplified)
    schema_version: str    # "1.0.0"
    prompt_version: str    # "1.0.0"
```

**Step 2: Generate Deterministic Fact ID**
```python
def generate_fact_id(filing_id, source_key, span_start, span_end, value_abs, unit_u_id, period_u_id, member_uids, concept_ref=None):
    """Generate deterministic, portable fact ID using canonical value and span"""
    # Canonicalize concept QName
    concept_canon = canonicalize_qname(concept_ref) if concept_ref else 'UNMAPPED'
    
    components = [
        filing_id,  # Use filing_id not accessionNumber
        source_key,  # section_name or exhibit_canon
        str(span_start),  # Include span for uniqueness
        str(span_end),
        str(value_abs) if value_abs is not None else 'NULL',  # Handle None values
        concept_canon,
        unit_u_id or 'NONE',
        period_u_id or 'NONE',
        '|'.join(sorted(member_uids)) if member_uids else 'NONE'
    ]
    
    fact_string = '|'.join(components)
    return f"8KF_{hashlib.md5(fact_string.encode()).hexdigest()}"

def canonicalize_qname(qname: str) -> str:
    """Canonicalize concept/member/dimension QNames"""
    if ':' in qname:
        prefix, local = qname.split(':', 1)
        return f"{prefix.lower()}:{local}"
    return qname.lower()
```

#### 3.2 Deduplication Strategy

**Step 1: Generate Dedupe Key**
```python
def generate_dedupe_key(fact):
    """Generate key for deduplication
    CRITICAL: Only call AFTER finalize_fact() sets UIDs!
    """
    concept_canon = canonicalize_qname(fact.concept_ref) if fact.concept_ref else 'UNMAPPED'
    components = [
        fact.filing_id,  # Use filing_id not accessionNumber
        concept_canon,
        ((fact.metric or 'UNKNOWN_METRIC') if concept_canon == 'UNMAPPED' else ''),  # Add metric for unmapped facts with proper precedence
        fact.unit_u_id or 'NONE',
        fact.period_u_id or 'NONE',  # Consistent naming
        str(fact.value_abs) if fact.value_abs is not None else 'NULL',  # Handle None properly
        '|'.join(sorted(getattr(fact, 'member_uids', []) or [])) or 'NONE'
    ]
    return hashlib.md5('|'.join(components).encode()).hexdigest()
```

**Step 2: Apply Deduplication Rules**
```python
def deduplicate_facts(facts):
    """Apply deduplication with deterministic precedence
    CRITICAL: Call AFTER finalize_fact() has set UIDs!
    """
    def rank(f):
        """Deterministic ranking to avoid flapping"""
        type_rank = {'Exhibit': 3, 'Section': 2, 'FilingText': 1}.get(f.source_type, 0)
        completeness_rank = {'full': 4, 'concept_unit_period': 3, 'concept_unit': 2, 'concept_only': 1, 'unmapped': 0}[f.completeness]
        # Prefer smaller span (tighter match); break ties by source_key+span_start
        span_size = -(f.span_end - f.span_start)
        return (type_rank, completeness_rank, span_size, f.source_key, f.span_start)
    
    dedupe_map = {}
    
    for fact in facts:
        # Generate dedupe_key here (after finalize_fact has set UIDs)
        if not hasattr(fact, 'dedupe_key'):
            fact.dedupe_key = generate_dedupe_key(fact)
        key = fact.dedupe_key
        
        if key in dedupe_map:
            existing = dedupe_map[key]
            # Replace if new fact ranks higher
            if rank(fact) > rank(existing):
                existing.superseded = True
                existing.superseded_by = fact.fact_id
                dedupe_map[key] = fact
            else:
                fact.superseded = True
                fact.superseded_by = existing.fact_id
        else:
            dedupe_map[key] = fact
    
    return facts  # All facts kept, duplicates marked
```

### Phase 4: XBRL Taxonomy Linking

#### 4.1 Progressive Relationship Creation

**Step 1: Load Company Taxonomy**
```python
def load_company_taxonomy(cik: str):
    """Load company-specific XBRL taxonomy from latest 10-K/10-Q"""
    query = """
    MATCH (c:Company {cik: $cik})-[:FILED]->(r:Report)
    WHERE r.formType IN ['10-K', '10-Q']
    WITH r ORDER BY r.filingDate DESC LIMIT 1
    MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)-[:HAS_CONCEPT]->(concept:Concept)
    RETURN collect(DISTINCT concept.qname) AS concepts
    """
    return run_query(query, {'cik': cik})
```

**Step 2: Progressive XBRL Linking**
```python
def link_to_xbrl(fact, company_taxonomy):
    """Progressively link fact to XBRL components"""
    completeness_level = None
    
    # Level 1: Concept only
    if concept := match_concept(fact.metric, company_taxonomy):
        fact.concept_ref = concept
        fact.mapped = True
        completeness_level = 'concept_only'
        
        # Level 2: Concept + Unit
        if unit := extract_unit(fact.value_raw):
            fact.unit_ref = unit
            completeness_level = 'concept_unit'
            
            # Level 3: Concept + Unit + Period
            if period := extract_period(fact.source_text):
                fact.period_start = period['start']
                fact.period_end = period['end']
                fact.period_type = period.get('type', 'instant')  # Ensure period_type is set
                completeness_level = 'concept_unit_period'
                
                # Level 4: Full (with context/members)
                if members := extract_members(fact.source_text, company_taxonomy):
                    fact.members = members
                    completeness_level = 'full'
    else:
        # Unmapped - store candidates
        fact.mapped = False
        fact.candidate_concepts = suggest_concepts(fact.metric, company_taxonomy)[:3]
        fact.mapping_confidence = 0.0
    
    fact.completeness = completeness_level or 'unmapped'
    return fact

def finalize_fact(fact):
    """Normalize fact fields to UIDs before ID generation and storage"""
    # Map model outputs to graph UIDs
    fact.unit_u_id = unit_ref_to_uid(fact.unit_ref) if hasattr(fact, 'unit_ref') else None
    
    # Convert period dates to u_id format using helper
    if hasattr(fact, 'period_start') and hasattr(fact, 'period_end'):
        fact.period_u_id = period_to_uid(fact.period_start, fact.period_end, 
                                          getattr(fact, 'period_type', 'instant'))
    else:
        fact.period_u_id = None
    
    # Convert member references to UIDs
    fact.member_uids = [member_to_uid(m) for m in getattr(fact, 'members', [])]
    
    # Now safe to compute fact_id (but NOT dedupe_key yet - dedup happens after)
    fact.fact_id = generate_fact_id(
        fact.filing_id, fact.source_key,
        fact.span_start, fact.span_end,
        fact.value_abs, fact.unit_u_id, fact.period_u_id, fact.member_uids,
        concept_ref=getattr(fact, 'concept_ref', None)
    )
    # NOTE: dedupe_key generated in deduplicate_facts() AFTER all facts finalized
    
    return fact

def unit_ref_to_uid(unit_ref: str) -> str:
    """Convert unit reference to UID format"""
    # Map common unit refs to UIDs (e.g., 'USD' -> 'iso4217:USD')
    if not unit_ref:
        return None
    if unit_ref.upper() == 'USD':
        return 'iso4217:USD'
    if unit_ref.lower() in ['percent', '%']:
        return 'pure'
    if unit_ref.lower() == 'shares':
        return 'shares'
    return unit_ref

def extract_period(text: str) -> dict|None:
    """Extract period information from text
    Returns dict with 'start', 'end', and 'type' (instant or duration)
    
    TODO [CRITICAL - NOT ACCEPTABLE FOR PRODUCTION]:
    This is a stub that returns None, causing 0% temporal mapping.
    Must implement before production to achieve 80% mapping target.
    Needs regex/NLP to extract dates like "Q4 2023", "December 31, 2023", "three months ended"
    """
    # STUB - MUST IMPLEMENT
    return None

def extract_unit(value_raw: str) -> str|None:
    """Extract unit from value text"""
    if '$' in value_raw or 'dollar' in value_raw.lower():
        return 'USD'
    if '%' in value_raw or 'percent' in value_raw.lower():
        return 'percent'
    if 'share' in value_raw.lower():
        return 'shares'
    return None

def extract_members(text: str, taxonomy: list) -> list:
    """Extract member references from text using company taxonomy
    
    TODO [CRITICAL - NOT ACCEPTABLE FOR PRODUCTION]:
    This is a stub that returns empty list, causing 0% dimensional mapping.
    Must implement before production to achieve 80% mapping target.
    Needs to match text against known members in taxonomy.
    """
    # STUB - MUST IMPLEMENT
    return []

def match_concept(metric: str, taxonomy: list) -> str|None:
    """Match metric to XBRL concept from taxonomy
    
    TODO [CRITICAL - NOT ACCEPTABLE FOR PRODUCTION]:
    This is a stub that returns None, causing 0% concept mapping.
    Must implement before production to achieve 80% mapping target.
    Needs fuzzy matching against taxonomy concepts.
    """
    # STUB - MUST IMPLEMENT
    return None

def suggest_concepts(metric: str, taxonomy: list) -> list:
    """Suggest possible XBRL concepts for unmapped metric
    
    TODO [CRITICAL - NOT ACCEPTABLE FOR PRODUCTION]:
    This is a stub that returns empty list, preventing fallback suggestions.
    Must implement before production to help with manual mapping.
    Needs to return top N fuzzy matches.
    """
    # STUB - MUST IMPLEMENT
    return []

def member_to_uid(member: str) -> str:
    """Convert member reference to UID format"""
    # Ensure member has proper namespace prefix
    if ':' not in member:
        return f"us-gaap:{member}"
    return member

def period_to_uid(start_date: str, end_date: str, period_type: str = 'instant') -> str:
    """Convert period dates to standard u_id format"""
    # Normalize dates and create consistent UID
    if start_date == end_date:
        return f"instant_{start_date}"
    return f"{period_type}_{start_date}_{end_date}"

def is_standard_quarter(start_date: str, end_date: str) -> bool:
    """Check if dates represent a standard fiscal quarter"""
    # Placeholder - would check if dates match Q1/Q2/Q3/Q4 patterns
    return False

def is_specific_date(start_date: str, end_date: str) -> bool:
    """Check if dates are specific enough to create a Context"""
    # Placeholder - would validate date specificity
    return start_date and end_date

def find_context(cik: str, start_date: str, end_date: str) -> dict|None:
    """Find existing context matching the period"""
    # Placeholder - would query Neo4j for existing Context
    return None
```

#### 4.2 Context Handling

**Step 1: Smart Context Creation**
```python
def create_context(ctx: dict) -> str:
    """We MERGE the Context in Cypher; here we just return the id"""
    return ctx['context_id']

def handle_context(fact):
    """Create or reuse Context based on period specificity"""
    
    if not fact.period_start:
        # No period - don't create Context
        return None
    
    # Check if exact quarterly match
    if is_standard_quarter(fact.period_start, fact.period_end):
        # Try to reuse existing quarterly Context
        existing = find_context(fact.cik, fact.period_start, fact.period_end)
        if existing:
            return existing.context_id
    
    # Create new Context for specific dates
    if is_specific_date(fact.period_start, fact.period_end):
        context = {
            'context_id': f"8K_{fact.cik}_{fact.period_start}_{fact.period_end}",
            'source': '8-K',  # Marker for 8-K contexts
            'cik': fact.cik,
            'period_u_id': f"{fact.period_type}_{fact.period_start}_{fact.period_end}",
            'member_u_ids': fact.members or [],
            'dimension_u_ids': []
        }
        return create_context(context)
    
    # Vague period - store as property only
    fact.period_text = fact.source_text  # Store original text
    return None
```

### Phase 5: Relationship Creation

**Step 1: Create Core Relationships (Idempotent with MERGE)**
```cypher
// MERGE EightKFact for idempotence (prevents duplicates on re-run)
MERGE (f:EightKFact {fact_id: $fact_id})
ON CREATE SET
    f.filing_id = $filing_id,  // Use filing_id not accessionNumber
    f.cik = $cik,  // Include for faster queries
    f.value_raw = $value_raw,
    f.value_abs = $value_abs,  // Canonical absolute value
    f.value_display_scale = $value_display_scale,  // Optional for UX
    f.currency = $currency,  // Optional currency code
    f.routing_key = $routing_key,
    f.source_type = $source_type,  // 'Section'|'Exhibit'|'FilingText' for clean dedupe
    f.extraction_schema = $schema,
    f.metric = $metric,  // CRITICAL: For XBRL mapping
    f.completeness = $completeness,
    f.mapped = $mapped,
    f.concept_ref = $concept_ref,  // XBRL concept or 'UNMAPPED'
    f.unit_u_id = $unit_u_id,  // Unit ID if available
    f.period_u_id = $period_u_id,  // Period ID if available (consistent naming)
    f.member_uids = $member_uids,  // Array of member IDs for audit
    f.dedupe_key = $dedupe_key,  // For deduplication
    f.superseded = $superseded,  // Boolean
    f.superseded_by = $superseded_by,  // Optional fact_id
    f.is_amendment = $is_amendment,  // For 8-K/A tracking
    f.amends_filing = $amends_filing,  // Original filing_id if amendment
    f.batch_id = $batch_id,
    f.pipeline_id = $pipeline_id,
    f.extraction_date = $extraction_date,  // String ISO date
    f.created_at = datetime(),  // UTC datetime for date operations
    f.source_text = $source_text  // Optional snippet for debugging
ON MATCH SET
    f.last_seen = datetime()  // Track re-processing

// MERGE EXTRACTED_FROM for idempotence (prevents duplicate edges)
WITH f
MATCH (source {id: $source_id})  // Property match, uses index
MERGE (f)-[r:EXTRACTED_FROM {
    span: [$span_start, $span_end],
    source_sha256: $source_hash
}]->(source)
ON CREATE SET 
    r.batch_id = $batch_id,
    r.pipeline_id = $pipeline_id

// Progressive XBRL relationships (Neo4j FOREACH cannot contain MATCH)
// HAS_CONCEPT - OPTIONAL MATCH then conditional MERGE
WITH f, $completeness AS comp, $concept_ref AS cref, $batch_id AS bid, $pipeline_id AS pid
OPTIONAL MATCH (c:Concept {qname: cref})
FOREACH (_ IN CASE WHEN comp IN ['concept_only','concept_unit','concept_unit_period','full'] AND c IS NOT NULL THEN [1] ELSE [] END |
    MERGE (f)-[:HAS_CONCEPT {batch_id: bid, pipeline_id: pid}]->(c)
)

// HAS_UNIT - OPTIONAL MATCH then conditional MERGE
WITH f, $completeness AS comp, $unit_u_id AS uid, $batch_id AS bid, $pipeline_id AS pid
OPTIONAL MATCH (u:Unit {u_id: uid})
FOREACH (_ IN CASE WHEN comp IN ['concept_unit','concept_unit_period','full'] AND u IS NOT NULL THEN [1] ELSE [] END |
    MERGE (f)-[:HAS_UNIT {batch_id: bid, pipeline_id: pid}]->(u)
)

// HAS_PERIOD - OPTIONAL MATCH then conditional MERGE
WITH f, $completeness AS comp, $period_u_id AS puid, $batch_id AS bid, $pipeline_id AS pid
OPTIONAL MATCH (p:Period {u_id: puid})  // Period nodes use u_id property in database
FOREACH (_ IN CASE WHEN comp IN ['concept_unit_period','full'] AND p IS NOT NULL THEN [1] ELSE [] END |
    MERGE (f)-[:HAS_PERIOD {batch_id: bid, pipeline_id: pid}]->(p)
)

// IN_CONTEXT (only when full completeness and context exists)
WITH f, $completeness AS comp, $context_id AS ctxid, $batch_id AS bid, $pipeline_id AS pid
FOREACH (_ IN CASE WHEN comp = 'full' AND ctxid IS NOT NULL THEN [1] ELSE [] END |
    MERGE (ctx:Context {context_id: ctxid})  // OK to MERGE Context if explicitly decided
    MERGE (f)-[:IN_CONTEXT {batch_id: bid, pipeline_id: pid}]->(ctx)
)

// Optional: FACT_MEMBER relationships (Neo4j FOREACH cannot contain MATCH)
WITH f, $completeness AS comp, $member_uids AS muids, $batch_id AS bid, $pipeline_id AS pid
UNWIND CASE WHEN comp = 'full' AND size(muids) > 0 THEN muids ELSE [] END AS member_uid
OPTIONAL MATCH (m:Member {u_id: member_uid})
FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
    MERGE (f)-[:FACT_MEMBER {batch_id: bid, pipeline_id: pid}]->(m)
)

// Optional: FACT_DIMENSION relationships (Neo4j FOREACH cannot contain MATCH)
WITH f, $completeness AS comp, $dimension_uids AS duids, $batch_id AS bid, $pipeline_id AS pid
UNWIND CASE WHEN comp = 'full' AND size(duids) > 0 THEN duids ELSE [] END AS dim_uid
OPTIONAL MATCH (d:Dimension {u_id: dim_uid})
FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
    MERGE (f)-[:FACT_DIMENSION {batch_id: bid, pipeline_id: pid}]->(d)
)

RETURN f.fact_id AS created_fact_id
```

### Phase 6: Production Requirements

#### 6.1 Database Constraints & Indexes

```cypher
// Neo4j 5 syntax for constraints and indexes
CREATE CONSTRAINT eightkfact_id IF NOT EXISTS 
FOR (f:EightKFact) REQUIRE f.fact_id IS UNIQUE;

CREATE INDEX eightkfact_batch IF NOT EXISTS 
FOR (f:EightKFact) ON (f.batch_id);

CREATE INDEX eightkfact_pipeline IF NOT EXISTS 
FOR (f:EightKFact) ON (f.pipeline_id);

CREATE INDEX eightkfact_filing IF NOT EXISTS 
FOR (f:EightKFact) ON (f.filing_id);  // Use filing_id not accessionNumber

CREATE INDEX eightkfact_dedupe IF NOT EXISTS 
FOR (f:EightKFact) ON (f.dedupe_key);

CREATE INDEX eightkfact_completeness IF NOT EXISTS 
FOR (f:EightKFact) ON (f.completeness);

CREATE INDEX eightkfact_mapped IF NOT EXISTS 
FOR (f:EightKFact) ON (f.mapped);

CREATE INDEX eightkfact_cik IF NOT EXISTS
FOR (f:EightKFact) ON (f.cik);  // Added for faster company filtering

// Ensure all source nodes have hashes and routing keys
CREATE INDEX esc_source_hash IF NOT EXISTS
FOR (n:ExtractedSectionContent) ON (n.source_sha256);

CREATE INDEX esc_routing_key IF NOT EXISTS
FOR (n:ExtractedSectionContent) ON (n.routing_key);

CREATE INDEX exh_source_hash IF NOT EXISTS
FOR (n:ExhibitContent) ON (n.source_sha256);

CREATE INDEX exh_exhibit_canon IF NOT EXISTS
FOR (n:ExhibitContent) ON (n.exhibit_canon);

CREATE INDEX ftc_source_hash IF NOT EXISTS
FOR (n:FilingTextContent) ON (n.source_sha256);

// Add indexes on source node IDs for fast lookups
CREATE INDEX esc_id IF NOT EXISTS 
FOR (n:ExtractedSectionContent) ON (n.id);

CREATE INDEX exh_id IF NOT EXISTS 
FOR (n:ExhibitContent) ON (n.id);

CREATE INDEX ftc_id IF NOT EXISTS 
FOR (n:FilingTextContent) ON (n.id);

// Note: Indexes on concept.qname, unit.u_id, context.context_id NOT needed
// as UNIQUE constraints below already create indexes

// Add unique constraints on taxonomy nodes
CREATE CONSTRAINT context_id_unique IF NOT EXISTS
FOR (ctx:Context) REQUIRE ctx.context_id IS UNIQUE;

CREATE CONSTRAINT concept_qname_unique IF NOT EXISTS
FOR (c:Concept) REQUIRE c.qname IS UNIQUE;

CREATE CONSTRAINT unit_uid_unique IF NOT EXISTS
FOR (u:Unit) REQUIRE u.u_id IS UNIQUE;

CREATE CONSTRAINT period_uid_unique IF NOT EXISTS
FOR (p:Period) REQUIRE p.u_id IS UNIQUE;

CREATE CONSTRAINT member_uid IF NOT EXISTS 
FOR (m:Member) REQUIRE m.u_id IS UNIQUE;

CREATE CONSTRAINT dimension_uid IF NOT EXISTS 
FOR (d:Dimension) REQUIRE d.u_id IS UNIQUE;
```

#### 6.2 Rollback Capability

```python
def rollback_batch(batch_id: str):
    """Rollback specific batch including all nodes and edges"""
    # Delete facts
    query1 = """
    MATCH (f:EightKFact {batch_id: $batch_id})
    DETACH DELETE f
    RETURN count(f) AS facts_deleted
    """
    
    # Delete REFERENCES edges
    query2 = """
    MATCH ()-[r:REFERENCES {batch_id: $batch_id}]-()
    DELETE r
    RETURN count(r) AS references_deleted
    """
    
    result1 = run_query(query1, {'batch_id': batch_id})
    result2 = run_query(query2, {'batch_id': batch_id})
    
    return {
        'facts_deleted': result1['facts_deleted'],
        'references_deleted': result2['references_deleted']
    }

def rollback_pipeline(pipeline_id: str):
    """Rollback entire pipeline including all nodes and edges"""
    # Delete facts
    query1 = """
    MATCH (f:EightKFact {pipeline_id: $pipeline_id})
    DETACH DELETE f
    RETURN count(f) AS facts_deleted
    """
    
    # Delete REFERENCES edges
    query2 = """
    MATCH ()-[r:REFERENCES {pipeline_id: $pipeline_id}]-()
    DELETE r
    RETURN count(r) AS references_deleted
    """
    
    result1 = run_query(query1, {'pipeline_id': pipeline_id})
    result2 = run_query(query2, {'pipeline_id': pipeline_id})
    
    return {
        'facts_deleted': result1['facts_deleted'],
        'references_deleted': result2['references_deleted']
    }
```

### Phase 7: Quality Assurance & Validation

#### 7.1 Success Metrics

```cypher
// Comprehensive validation query
WITH datetime() AS check_time, 
     '8K_EXTRACTION_V1' AS pipeline
MATCH (f:EightKFact {pipeline_id: pipeline})
WITH check_time, pipeline,
     COUNT(f) AS total_facts,
     SUM(CASE WHEN f.mapped THEN 1 ELSE 0 END) AS mapped_facts,
     SUM(CASE WHEN f.routing_key CONTAINS 'UNKNOWN' THEN 1 ELSE 0 END) AS unknown_routed,
     SUM(CASE WHEN f.superseded THEN 1 ELSE 0 END) AS superseded_facts,
     COUNT(DISTINCT f.dedupe_key) AS unique_facts,
     SUM(CASE WHEN f.completeness = 'full' THEN 1 ELSE 0 END) AS full_facts

WITH check_time, total_facts, mapped_facts, unknown_routed, superseded_facts, unique_facts, full_facts,
     round(100.0 * mapped_facts / total_facts, 2) AS mapping_rate,
     round(100.0 * unknown_routed / total_facts, 2) AS unknown_rate,
     round(100.0 * full_facts / total_facts, 2) AS full_completeness_rate

RETURN 
    check_time,
    total_facts,
    mapping_rate,
    unknown_rate,
    full_completeness_rate,
    total_facts - superseded_facts AS active_facts,
    unique_facts = (total_facts - superseded_facts) AS dedup_pass,
    mapping_rate >= 80.0 AS mapping_target_met,
    unknown_rate <= 1.0 AS routing_target_met
```

#### 7.2 QA Guardrails

```cypher
// Every EXTRACTED_FROM has span and source hash
MATCH ()-[r:EXTRACTED_FROM]->(t) 
WHERE r.span IS NULL OR t.source_sha256 IS NULL 
RETURN count(r) AS missing_span_or_hash;
// Expected: 0

// Check span fidelity for sample (fixed to handle truncated source_text)
MATCH (f:EightKFact)-[r:EXTRACTED_FROM]->(s)
WITH f, r.span AS span, s.content AS content LIMIT 100
WITH f, substring(content, span[0], span[1] - span[0]) AS actual_text,
     substring(f.source_text, 0, 200) AS cached_snippet
// Only compare if source_text is the full span (not truncated)
WHERE size(actual_text) <= 200 AND actual_text <> cached_snippet
   OR size(actual_text) > 200 AND substring(actual_text, 0, 200) <> cached_snippet
RETURN count(f) AS span_mismatches;
// Expected: 0

// No accidental REPORTS edges from EightKFacts
MATCH (:EightKFact)-[r:REPORTS]->()
RETURN count(r) AS bad_reports_edges;
// Expected: 0

// Unknown routing rate check on SOURCE NODES (handles both routing_key and routing_keys)
MATCH (n)
WHERE n:ExtractedSectionContent OR n:ExhibitContent OR n:FilingTextContent
WITH labels(n)[0] AS node_type, n,
     CASE 
       WHEN n:ExhibitContent THEN 
         CASE WHEN size(coalesce(n.routing_keys, [])) = 0 THEN true
              WHEN any(k IN n.routing_keys WHERE k CONTAINS 'UNKNOWN') THEN true
              ELSE false END
       ELSE coalesce(n.routing_key, '') CONTAINS 'UNKNOWN'
     END AS is_unknown
RETURN node_type,
       sum(CASE WHEN is_unknown THEN 1 ELSE 0 END) AS unknown_count,
       count(*) AS total_count,
       round(100.0 * sum(CASE WHEN is_unknown THEN 1 ELSE 0 END) / count(*), 2) AS unknown_rate
ORDER BY unknown_rate DESC;
// Expected: <1% for sections, may be higher for exhibits until REFERENCES are created

// Unknown routing rate check on facts
MATCH (f:EightKFact)
WHERE f.routing_key CONTAINS 'UNKNOWN'
WITH date(f.created_at) AS day, count(f) AS unknown_count
MATCH (f2:EightKFact)
WHERE date(f2.created_at) = day
WITH day, unknown_count, count(f2) AS total_count
RETURN day, round(100.0 * unknown_count / total_count, 2) AS unknown_rate
ORDER BY day DESC;
// Expected: <1% per day

// Verify exhibit routing keys are arrays
MATCH (x:ExhibitContent)
WHERE x.routing_keys IS NOT NULL AND size(x.routing_keys) > 0
RETURN count(x) AS exhibits_with_routing,
       avg(size(x.routing_keys)) AS avg_routes_per_exhibit;

// Check 7.01 gating correctness (Neo4j 5 syntax)
MATCH (f:EightKFact {extraction_schema:'EARNINGS'})-[:EXTRACTED_FROM]->(s:ExtractedSectionContent)
WHERE s.routing_key = 'ESC:7.01'
  AND NOT EXISTS((s)-[:REFERENCES]->(:ExhibitContent))
RETURN count(f) AS bad_701_earnings;
// Expected: 0

// Validate only explicit REFERENCES
MATCH ()-[r:REFERENCES]->()
WHERE r.kind <> 'explicit'
RETURN count(r) AS non_explicit_refs;
// Expected: 0

// Fact→XBRL completeness coherence check (Neo4j 5 syntax)
MATCH (f:EightKFact)
WITH f,
     EXISTS((f)-[:HAS_CONCEPT]->()) AS hc,
     EXISTS((f)-[:HAS_UNIT]->()) AS hu,
     EXISTS((f)-[:HAS_PERIOD]->()) AS hp,
     EXISTS((f)-[:IN_CONTEXT]->()) AS ic
RETURN 
    count(CASE WHEN f.completeness='unmapped' AND NOT hc THEN 1 END) AS unmapped_ok,
    count(CASE WHEN f.completeness='concept_only' AND hc AND NOT hu THEN 1 END) AS concept_only_ok,
    count(CASE WHEN f.completeness='concept_unit' AND hc AND hu AND NOT hp THEN 1 END) AS concept_unit_ok,
    count(CASE WHEN f.completeness='concept_unit_period' AND hc AND hu AND hp AND NOT ic THEN 1 END) AS concept_unit_period_ok,
    count(CASE WHEN f.completeness='full' AND hc AND hu AND hp AND ic THEN 1 END) AS full_ok,
    count(CASE WHEN NOT (
        (f.completeness='unmapped' AND NOT hc) OR
        (f.completeness='concept_only' AND hc AND NOT hu) OR
        (f.completeness='concept_unit' AND hc AND hu AND NOT hp) OR
        (f.completeness='concept_unit_period' AND hc AND hu AND hp AND NOT ic) OR
        (f.completeness='full' AND hc AND hu AND hp AND ic)
    ) THEN 1 END) AS mismatches;
// Expected: mismatches = 0

// Duplicate detection audit
MATCH (f:EightKFact)
WITH f.dedupe_key AS key, collect(f) AS facts
WHERE size(facts) > 1
WITH key, facts, 
     [f IN facts WHERE f.superseded = true] AS superseded_facts,
     [f IN facts WHERE f.superseded = false OR f.superseded IS NULL] AS active_facts
WHERE size(active_facts) <> 1
RETURN key, size(facts) AS total, size(superseded_facts) AS superseded, size(active_facts) AS active;
// Expected: 0 rows (all duplicates should have exactly 1 active)

// Single-source invariant - each EightKFact has exactly one source
MATCH (f:EightKFact)
WITH f, size([(f)-[:EXTRACTED_FROM]->() | 1]) AS srcs
WHERE srcs <> 1
RETURN count(f) AS bad_source_cardinality;
// Expected: 0

// No lingering PENDING exhibit routing
MATCH (x:ExhibitContent)
WHERE x.routing_key CONTAINS 'PENDING' 
   OR any(k IN coalesce(x.routing_keys, []) WHERE k CONTAINS 'PENDING')
RETURN count(x) AS exhibits_with_pending_routing;
// Expected: 0 after REFERENCES creation
```

#### 7.3 Unit Tests

```python
# Test suite for critical components
def run_unit_tests():
    test_item_701_routing()        # 7.01 logic
    test_exhibit_canonicalization() # Exhibit normalization
    test_span_verification()        # Span fidelity
    test_deduplication()           # Exhibit precedence
    test_qname_canonicalization()  # Concept normalization
    test_completeness_levels()     # Progressive linking
    test_context_strategy()        # Context creation logic
```

### Phase 8: Integration & Monitoring

#### 8.1 Query Compatibility

```cypher
// Combined queries work with both Facts and EightKFacts
MATCH (f)-[:HAS_CONCEPT]->(c:Concept {qname: 'us-gaap:Revenue'})
WHERE (f:Fact) OR (f:EightKFact AND f.completeness IN ['full', 'concept_unit_period'])
// Fact uses 'value', EightKFact uses 'value_abs'
RETURN coalesce(f.value, f.value_abs) AS value,
       f.value_raw, labels(f) AS type

// Find unmapped 8-K facts for review
MATCH (f:EightKFact {mapped: false})
RETURN f.value_raw, f.candidate_concepts, f.routing_key,
       COUNT(*) AS occurrences
ORDER BY occurrences DESC

// Compare 8-K extractions with 10-K XBRL (handling unit scale differences)
MATCH (f8:EightKFact)-[:HAS_CONCEPT]->(c:Concept)<-[:HAS_CONCEPT]-(f10:Fact)
WHERE f8.cik = f10.cik  // Same company
WITH f8, f10, c
MATCH (f8)-[:HAS_PERIOD]->(p8:Period),
      (f10)-[:HAS_PERIOD]->(p10:Period)
WHERE p8.u_id = p10.u_id  // Period nodes use u_id property
MATCH (f8)-[:HAS_UNIT]->(u8:Unit),
      (f10)-[:HAS_UNIT]->(u10:Unit)
WHERE u8.u_id = u10.u_id  // Only compare when units match
// Note: 8-K value_abs is in cents for USD, basis points for percentages
// 10-K value is typically in dollars for USD, percent for percentages
RETURN c.qname, 
       f8.value_abs AS from_8k_cents_or_bps,
       f10.value AS from_10k_dollars_or_pct,
       CASE 
         WHEN u8.u_id = 'iso4217:USD' THEN f8.value_abs / 100.0  // Convert cents to dollars
         WHEN u8.u_id = 'pure' THEN f8.value_abs / 10000.0       // Convert bps to percent
         ELSE f8.value_abs 
       END AS from_8k_normalized,
       u8.u_id AS unit,
       f8.completeness
```

#### 8.2 Daily Processing Pipeline

```python
def create_eightkfacts(facts, batch_id, pipeline_id):
    """Create multiple EightKFacts by calling create_eightkfact for each"""
    for fact in facts:
        create_eightkfact(fact, batch_id, pipeline_id)

def process_daily_8ks():
    """Daily pipeline for new 8-K processing"""
    
    # Initialize pipeline
    pipeline_id = "8K_EXTRACTION_V1"
    batch_id = datetime.now().isoformat()
    run_date = datetime.now().date().isoformat()
    
    # Get unprocessed 8-Ks
    new_8ks = get_unprocessed_8ks()
    
    for report in new_8ks:
        try:
            # Handle amendments FIRST (before creating facts)
            meta = handle_amendment(report)
            
            # Phase 1: Route content
            sections = route_sections(report)
            exhibits = route_exhibits(report, sections)
            
            # Phase 2: Extract facts
            facts = []
            for content_node in sections + exhibits:
                # Determine schema type and routing key
                if isinstance(content_node, ExtractedSectionContent):
                    schema_type = determine_schema_from_routing(content_node.routing_key)
                    source_key = content_node.section_name
                    chosen_routing = content_node.routing_key
                else:  # ExhibitContent
                    # Resolve exhibit schema from routing_keys
                    if hasattr(content_node, 'routing_keys') and content_node.routing_keys:
                        # Prefer 2.02 (EARNINGS) over 7.01 (FD)
                        if 'ESC:2.02' in content_node.routing_keys:
                            schema_type = 'EARNINGS'
                            chosen_routing = 'ESC:2.02'
                        elif 'ESC:7.01' in content_node.routing_keys:
                            schema_type = 'FD'
                            chosen_routing = 'ESC:7.01'
                        else:
                            # Use first non-UNKNOWN routing key
                            chosen_routing = next((k for k in content_node.routing_keys if 'UNKNOWN' not in k), 'ESC:9.01')
                            schema_type = determine_schema_from_routing(chosen_routing)
                    else:
                        schema_type = 'OTHER'
                        chosen_routing = 'ESC:9.01'
                    source_key = content_node.exhibit_canon
                
                source_hash = content_node.source_sha256
                
                # Extract with correct signature
                extracted = extract_facts(content_node.content, schema_type, source_hash, source_key)
                
                # Add source type, schema, routing, amendment flags, and source ID
                for fact in extracted:
                    fact.extraction_schema = schema_type
                    fact.routing_key = chosen_routing
                    fact.source_type = 'Section' if isinstance(content_node, ExtractedSectionContent) else 'Exhibit'
                    fact.source_id = content_node.id  # For EXTRACTED_FROM relationship
                    fact.is_amendment = meta['is_amendment']
                    fact.amends_filing = meta.get('amends_filing')
                
                facts.extend(extracted)
            
            # Phase 3: Link to XBRL and finalize (BEFORE deduplication)
            company_taxonomy = load_company_taxonomy(report.cik)
            for fact in facts:
                fact.extraction_date = run_date  # Set extraction date
                link_to_xbrl(fact, company_taxonomy)
                fact.context_id = handle_context(fact)  # Set context before finalize
                finalize_fact(fact)  # CRITICAL: Sets UIDs needed for dedupe_key
            
            # Phase 4: Deduplicate (AFTER finalization sets UIDs)
            facts = deduplicate_facts(facts)
            
            # Phase 5: Create nodes and relationships
            # Pass context_ids along with facts
            create_eightkfacts(facts, batch_id, pipeline_id)
            
            # Phase 6: Apply amendment supersedence
            if report.formType == '8-K/A':
                apply_amendment_supersedence(batch_id)
            
        except Exception as e:
            log_error(f"Failed processing {report.filing_id}: {e}")
            continue
    
    # Run validation
    validate_batch(batch_id)
```

### Summary of Key Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Routing** | Deterministic Item codes only | 100% predictable |
| **7.01 Logic** | FD default, EARNINGS with EX-99.x | Prevents misclassification |
| **Source Hash** | SHA-256 of RAW content (no normalization) | Permanent span verification |
| **IDs** | filing_id (not accessionNumber) + cik | Match existing schema |
| **Tracking** | pipeline_id + batch_id on all nodes/edges | Two-level rollback |
| **XBRL Linking** | MATCH not MERGE, progressive completeness | Avoid orphan nodes |
| **Values** | Scaled integers, no floats | Precision preservation |
| **REPORTS Edge** | No - traverse via EXTRACTED_FROM | Avoids redundancy |
| **Context** | MERGE only for new specific dates | Reuse quarterly contexts |

### ⚠️ CRITICAL TODO - NOT PRODUCTION READY

**The following stub functions MUST be implemented before production deployment:**

1. **`extract_period()`** - Currently returns None → 0% temporal mapping
2. **`match_concept()`** - Currently returns None → 0% concept mapping  
3. **`suggest_concepts()`** - Currently returns [] → No fallback suggestions
4. **`extract_members()`** - Currently returns [] → 0% dimensional mapping

**Impact**: Current stubs will result in ~5-10% mapping rate instead of 80% target.
**Resolution Required**: Tomorrow's priority to implement these functions.
| **Unmapped** | completeness='unmapped' | Valid domain value |
| **Deduplication** | Use source_type: Exhibit > Section | Cleaner than parsing keys |
| **Amendments** | Apply supersedence after creation | Handle 8-K/A properly |
| **Normalization** | Only for matching, never for storage | Preserve exact content |

---



Here’s the 8-K Extraction **Bot Brief** you can drop in front of a cold bot. It’s the minimum it needs to do the job exactly as intended.

Purpose
Deterministically extract facts from 8-K sections & exhibits, route by SEC Item, and link to company XBRL so downstream can query 8-K facts like 10-K/10-Q. Reliability > recall.

Hard invariants (never break)
No heuristic guesses. Only create links you can prove.

Hash raw text only. source_sha256 = sha256(raw_content). Do not normalize before hashing.

Track spans. Every fact must have span_start, span_end, EXTRACTED_FROM(span, source_sha256).

Spans are 0-based, half-open [start, end). So content[start:end] equals the captured text.

Exactly one source. Each EightKFact has one EXTRACTED_FROM edge.

Idempotent writes. Use MERGE for facts/edges; writes must be re-runnable.

No REPORTS edges from EightKFact. Traverse via EXTRACTED_FROM.

UIDs before IDs. Convert to unit_u_id, period_u_id, member_uids before generating fact_id/dedupe_key.

Use filing_id (not accessionNumber) and include cik on facts.

Period nodes use u_id. EightKFact.period_u_id → (:Period {u_id}).

Values are integers. Currency in cents; percents in basis points. No floats on facts.

Routing & exhibits
Section → Item: Build canon_key(section_name) → SECTION_TO_ITEM. Persist n.routing_key = "ESC:<item>".

7.01 gating: Default schema = FD. Upgrade to EARNINGS only if section header (first 2k chars) explicitly references EX-99.1 or EX-99.2.

Explicit refs only: Create (:ExtractedSectionContent)-[:REFERENCES {kind:'explicit'}]->(:ExhibitContent) by scanning normalized header.

Exhibit canonicalization: canon_exhibit("Exhibit 99.01 PR Q3") -> "EX-99.1". Persist x.exhibit_canon.

Exhibit routing: If any referencing section gives Items, use those. Else map by series: EX-99 → [2.02, 7.01], EX-10 → [1.01, 5.02], else default 9.01.

Exhibit schema selection: If routing_keys contain both 2.02 and 7.01, prefer 2.02→EARNINGS over 7.01→FD; otherwise map via ITEM_TO_SCHEMA, else OTHER.

No lingering PENDING. After references are built, exhibits must not remain :PENDING.

Normalization (for matching/search only)
Use a single helper everywhere (REFERENCES, 7.01 gating, Python helpers):

Replace \u00A0(NBSP)→space, tabs/CR/LF→space, —/–/\u2011→-, \u2212→-, strip \u200B, uppercase, collapse spaces.

Do not use this output for hashing or storage.

Extraction configuration
configure_langextract(schema) uses examples, confidence_threshold, track_spans=True, schema_version, prompt_version.

Model output must include: metric, value_raw, unit (if any), span, and enough context text for period/members.

Value normalization
Convert value_raw → (value_abs, value_display_scale) using Decimal with ROUND_HALF_UP.

Detect negatives via (, -, and cues like “decrease/decline/loss”.

Units:

USD → cents (×100; apply million/billion/thousand scales first).

Percent → basis points (×10,000).

Other counts → integer base units with the same scaling rules.

XBRL linking & completeness
Load company taxonomy (latest 10-K/10-Q).

Progression per fact:

concept_only

concept_unit

concept_unit_period

full (+ members/context)

If no concept match: mapped=false, store candidate_concepts[:3], completeness='unmapped'.

Periods & context
Build period_u_id via period_to_uid(start,end,type); instant_YYYY-MM-DD or duration_YYYY-MM-DD_YYYY-MM-DD.

Reuse existing quarterly contexts when exact match; only MERGE a new Context for specific dates; otherwise keep period text on the fact and skip context.

If completeness='full' and context_id present, create IN_CONTEXT.

IDs & dedupe
fact_id must include the span for uniqueness across occurrences:
Hash of [filing_id, source_key, span_start, span_end, value_abs/NULL, concept_canon/UNMAPPED, unit_u_id/NONE, period_u_id/NONE, sorted(member_uids)/NONE].

dedupe_key (no span) = md5 of [filing_id, concept_canon/UNMAPPED, ((metric or 'UNKNOWN_METRIC') if UNMAPPED else ''), unit_u_id/NONE, period_u_id/NONE, value_abs, sorted(member_uids)/NONE].
(Note the parentheses on that ternary!)

Dedup precedence: Exhibit > Section > FilingText, then higher completeness, then smaller span, then source_key, then span_start. Mark non-winners superseded=true.

Graph writes (required params per fact write)
Params:
fact_id, filing_id, cik, value_raw, value_abs, value_display_scale, currency, routing_key, source_type, schema, metric, completeness, mapped, concept_ref, unit_u_id, period_u_id, member_uids, dedupe_key, superseded, superseded_by, is_amendment, amends_filing, batch_id, pipeline_id, extraction_date, source_text, source_id, span_start, span_end, source_hash, context_id(optional), dimension_uids(optional)

Cypher:

MERGE (f:EightKFact {fact_id}) ...

MATCH (source {id:$source_id}) MERGE (f)-[:EXTRACTED_FROM {span:[...], source_sha256:$source_hash, batch_id, pipeline_id}]->(source)

Conditional HAS_CONCEPT, HAS_UNIT, HAS_PERIOD, IN_CONTEXT, FACT_MEMBER, FACT_DIMENSION using OPTIONAL MATCH + FOREACH pattern.

Amendments
If 8-K/A, find original 8-K by same CIK, latest earlier date; mark new facts is_amendment=true and amends_filing.

After creation, apply_amendment_supersedence(batch_id) marks originals with identical dedupe_key as superseded.

Indexes & constraints (Neo4j 5)
Uniques: EightKFact.fact_id, Context.context_id, Concept.qname, Unit.u_id, Period.u_id, Member.u_id, Dimension.u_id.

Indexes: EightKFact on batch_id, pipeline_id, filing_id, dedupe_key, completeness, mapped, cik; sources on source_sha256, routing_key/exhibit_canon; taxonomy on qname/u_id.

Rollback
By batch_id or pipeline_id: delete :EightKFact nodes and :REFERENCES edges with that tag. Facts/edges must carry both IDs.

QA checks (run every batch)
Missing span/hash: count of EXTRACTED_FROM with null span or missing source_sha256 == 0.

Single source per fact: count facts with EXTRACTED_FROM cardinality ≠ 1 == 0.

7.01 gating: no EARNINGS facts from sections with ESC:7.01 lacking explicit REFERENCES to EX-99.x.

REFERENCES kind: only 'explicit'.

Completeness coherence: relationships match declared completeness (concept/unit/period/context).

Duplicates: each dedupe_key has exactly 1 active fact.

Unknown routing rate:

Sections: <1% where routing_key CONTAINS 'UNKNOWN'.

Exhibits: treat separately via routing_keys (array must not be empty/unknown-only).

No EXH:*:PENDING remaining.

Optional: mapping rate ≥ 80%, unknown routing ≤ 1%.

Pipeline order (per report)
Compute & persist routing_key / exhibit_canon / source_sha256.

Build explicit REFERENCES (scoped to filing); set ExhibitContent.routing_keys.

Route each content node → schema (exhibits via priority 2.02>7.01).

Extract with spans.

Link to XBRL (progression); parse unit/period/members.

Finalize → convert to UIDs (unit_u_id, period_u_id, member_uids), compute context_id, then compute fact_id & dedupe_key.

Create fact + relationships.

If amendment, run supersedence.

Run QA.

Helpers (must exist & be used)
canon_key(s), canon_exhibit(s), normalize_for_matching(text)

period_to_uid(start, end, type), unit_ref_to_uid(unit_ref), member_to_uid(member)

normalize_value_to_abs(value_raw, unit) (Decimal, negatives)

generate_fact_id(...) (includes span), generate_dedupe_key(fact)

determine_schema_from_routing(routing_key); exhibit schema resolver (2.02>7.01>first known>OTHER)

Mixed queries (Fact vs EightKFact)
Use parentheses for precedence and coalesce for values:

MATCH (f)-[:HAS_CONCEPT]->(c:Concept {qname:'us-gaap:Revenue'})
WHERE (f:Fact) OR (f:EightKFact AND f.completeness IN ['full','concept_unit_period'])
RETURN coalesce(f.value, f.value_abs) AS value, f.value_raw, labels(f) AS type
When comparing 8-K to 10-K, ensure units match and present normalized columns (e.g., 8-K cents → dollars).

Final drop-ins
1) Complete mappings (copy/paste)
python
Copy
Edit
def canon_key(s: str) -> str:
    import re
    return re.sub(r'[^A-Z0-9]', '', s.upper())

SECTION_TO_ITEM = {
    'ENTRYINTOAMATERIALDEFINITIVEAGREEMENT': '1.01',
    'TERMINATIONOFAMATERIALDEFINITIVEAGREEMENT': '1.02',
    'BANKRUPTCYORRECEIVERSHIP': '1.03',
    'MINESAFETYREPORTINGOFSHUTDOWNSANDPATTERNSOFVIOLATIONS': '1.04',
    'MATERIALCYBERSECURITYINCIDENTS': '1.05',
    'COMPLETIONOFACQUISITIONORDISPOSITIONOFASSETS': '2.01',
    'RESULTSOFOPERATIONSANDFINANCIALCONDITION': '2.02',
    'CREATIONOFADIRECTFINANCIALOBLIGATIONORANOBLIGATIONUNDERANOFFBALANCESHEETARRANGEMENTOFAREGISTRANT': '2.03',
    'TRIGGERINGEVENTSTHATACCELERATEORINCREASEADIRECTFINANCIALOBLIGATIONORANOBLIGATIONUNDERANOFFBALANCESHEETARRANGEMENT': '2.04',
    'COSTSASSOCIATEDWITHEXITORDISPOSALACTIVITIES': '2.05',
    'MATERIALIMPAIRMENTS': '2.06',
    'NOTICEOFDELISTINGORFAILURETOSATISFYACONTINUEDLISTINGRULEORSTANDARDTRANSFEROFLISTING': '3.01',
    'UNREGISTEREDSALESOFEQUITYSECURITIES': '3.02',
    'MATERIALMODIFICATIONSTORIGHTSOFSECURITYHOLDERS': '3.03',
    'CHANGESINREGISTRANTSCERTIFYINGACCOUNTANT': '4.01',
    'NONRELIANCEONPREVIOUSLYISSUEDFINANCIALSTATEMENTSORARELATEDAUDITREPORTORCOMPLETEDINTERIMREVIEW': '4.02',
    'CHANGESINCONTROLOFREGISTRANT': '5.01',
    'DEPARTUREOFDIRECTORSORCERTAINOFFICERSELECTIONOFDIRECTORSAPPOINTMENTOFCERTAINOFFICERSCOMPENSATORYARRANGEMENTSOFCERTAINOFFICERS': '5.02',
    'AMENDMENTSTOARTICLESOFINCORPORATIONORBYLAWSCHANGEINFISCALYEAR': '5.03',
    'TEMPORARYSUSPENSIONOFTRADINGUNDERREGISTRANTSEMPLOYEEBENEFITPLANS': '5.04',
    'AMENDMENTSTOTHEREGISTRANTSCODEOFETHICSORWAIVEROFAPROVISIONOFTHECODEOFETHICS': '5.05',
    'CHANGEINSHELLCOMPANYSTATUS': '5.06',
    'SUBMISSIONOFMATTERSTOAVOTEOFSECURITYHOLDERS': '5.07',
    'SHAREHOLDERNOMINATIONSPURSUANTTOEXCHANGEACTRULE14A11': '5.08',
    'REGULATIONFDDISCLOSURE': '7.01',
    'OTHEREVENTS': '8.01',
    'FINANCIALSTATEMENTSANDEXHIBITS': '9.01'
}

ITEM_TO_SCHEMA = {
    '1.01': 'AGREEMENTS', '1.02': 'AGREEMENTS',
    '1.03': 'COMPLIANCE', '1.04': 'COMPLIANCE', '1.05': 'COMPLIANCE',
    '2.01': 'M&A', '2.02': 'EARNINGS',
    '2.03': 'DEBT', '2.04': 'DEBT',
    '2.05': 'RESTRUCTURING', '2.06': 'IMPAIRMENT',
    '3.01': 'LISTING',
    '3.02': 'EQUITY', '3.03': 'EQUITY',
    '4.01': 'AUDIT', '4.02': 'AUDIT',
    '5.01': 'CONTROL',
    '5.02': 'PERSONNEL',
    '5.03': 'GOVERNANCE', '5.04': 'GOVERNANCE', '5.05': 'GOVERNANCE', '5.06': 'GOVERNANCE',
    '5.07': 'VOTING', '5.08': 'VOTING',
    '7.01': 'FD',   # upgraded to EARNINGS only with explicit EX-99.1/99.2 ref
    '8.01': 'OTHER', '9.01': 'OTHER'
}
2) Clarifications (lock these in)
source_id in write params = the id property on ExtractedSectionContent or ExhibitContent (not Neo4j’s internal id).

Helper status:

extract_period() → TODO (regex/NLP).

match_concept() / suggest_concepts() → TODO (fuzzy match vs company taxonomy).

extract_members() → TODO (taxonomy member matching).

load_company_taxonomy() → implemented via Neo4j query (already spec’d).

REFERENCES timing: run once per report after all sections/exhibits are loaded, not per section.

Exhibit multi-item: If an exhibit maps to multiple Items (e.g., EX-99 → [2.02, 7.01]), choose one schema by priority 2.02 > 7.01, else first known, else OTHER.

3) Minor but important
batch_id = datetime.now().isoformat()

pipeline_id = "8K_EXTRACTION_V1"

Compute source_sha256 before any normalization and store on the source node.

4) Single-fact writer (ready to call)
python
Copy
Edit
def create_eightkfact(fact, batch_id: str, pipeline_id: str):
    """
    Writes one EightKFact and its relationships.
    Requires fact to be finalized (unit_u_id/period_u_id/member_uids set,
    fact_id & dedupe_key computed, source_id present).
    """
    params = {
        "fact_id": fact.fact_id,
        "filing_id": fact.filing_id,
        "cik": fact.cik,
        "value_raw": getattr(fact, "value_raw", None),
        "value_abs": fact.value_abs,
        "value_display_scale": getattr(fact, "value_display_scale", None),
        "currency": getattr(fact, "currency", None),
        "routing_key": fact.routing_key,
        "source_type": fact.source_type,
        "schema": fact.extraction_schema,
        "metric": getattr(fact, "metric", None),
        "completeness": fact.completeness,
        "mapped": getattr(fact, "mapped", False),
        "concept_ref": getattr(fact, "concept_ref", None),
        "unit_u_id": getattr(fact, "unit_u_id", None),
        "period_u_id": getattr(fact, "period_u_id", None),
        "member_uids": getattr(fact, "member_uids", []),
        "dedupe_key": fact.dedupe_key,
        "superseded": getattr(fact, "superseded", False),
        "superseded_by": getattr(fact, "superseded_by", None),
        "is_amendment": getattr(fact, "is_amendment", False),
        "amends_filing": getattr(fact, "amends_filing", None),
        "batch_id": batch_id,
        "pipeline_id": pipeline_id,
        "extraction_date": getattr(fact, "extraction_date", None),
        "source_text": getattr(fact, "source_text", None),
        "source_id": fact.source_id,              # <- property id on source node
        "span_start": fact.span_start,
        "span_end": fact.span_end,
        "source_hash": fact.source_hash,
        "context_id": getattr(fact, "context_id", None),
        "dimension_uids": getattr(fact, "dimension_uids", []),
    }

    cypher = """
    MERGE (f:EightKFact {fact_id: $fact_id})
    ON CREATE SET
      f.filing_id=$filing_id, f.cik=$cik,
      f.value_raw=$value_raw, f.value_abs=$value_abs, f.value_display_scale=$value_display_scale, f.currency=$currency,
      f.routing_key=$routing_key, f.source_type=$source_type, f.extraction_schema=$schema, f.metric=$metric,
      f.completeness=$completeness, f.mapped=$mapped, f.concept_ref=$concept_ref,
      f.unit_u_id=$unit_u_id, f.period_u_id=$period_u_id, f.member_uids=$member_uids,
      f.dedupe_key=$dedupe_key, f.superseded=$superseded, f.superseded_by=$superseded_by,
      f.is_amendment=$is_amendment, f.amends_filing=$amends_filing,
      f.batch_id=$batch_id, f.pipeline_id=$pipeline_id, f.extraction_date=$extraction_date,
      f.created_at=datetime(), f.source_text=$source_text
    ON MATCH SET f.last_seen=datetime()
    WITH f
    MATCH (source {id: $source_id})
    MERGE (f)-[r:EXTRACTED_FROM {span: [$span_start, $span_end], source_sha256: $source_hash}]->(source)
    ON CREATE SET r.batch_id=$batch_id, r.pipeline_id=$pipeline_id
    WITH f
    OPTIONAL MATCH (c:Concept {qname: $concept_ref})
    FOREACH (_ IN CASE WHEN c IS NULL OR NOT $completeness IN ['concept_only','concept_unit','concept_unit_period','full'] THEN [] ELSE [1] END |
      MERGE (f)-[:HAS_CONCEPT {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(c)
    )
    WITH f
    OPTIONAL MATCH (u:Unit {u_id: $unit_u_id})
    FOREACH (_ IN CASE WHEN u IS NULL OR NOT $completeness IN ['concept_unit','concept_unit_period','full'] THEN [] ELSE [1] END |
      MERGE (f)-[:HAS_UNIT {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(u)
    )
    WITH f
    OPTIONAL MATCH (p:Period {u_id: $period_u_id})
    FOREACH (_ IN CASE WHEN p IS NULL OR NOT $completeness IN ['concept_unit_period','full'] THEN [] ELSE [1] END |
      MERGE (f)-[:HAS_PERIOD {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(p)
    )
    WITH f
    FOREACH (_ IN CASE WHEN $completeness <> 'full' OR $context_id IS NULL THEN [] ELSE [1] END |
      MERGE (ctx:Context {context_id: $context_id})
      MERGE (f)-[:IN_CONTEXT {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(ctx)
    )
    WITH f
    UNWIND CASE WHEN $completeness='full' AND size($member_uids)>0 THEN $member_uids ELSE [] END AS mu
    OPTIONAL MATCH (m:Member {u_id: mu})
    FOREACH (_ IN CASE WHEN m IS NULL THEN [] ELSE [1] END |
      MERGE (f)-[:FACT_MEMBER {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(m)
    )
    WITH f
    UNWIND CASE WHEN $completeness='full' AND size($dimension_uids)>0 THEN $dimension_uids ELSE [] END AS du
    OPTIONAL MATCH (d:Dimension {u_id: du})
    FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END |
      MERGE (f)-[:FACT_DIMENSION {batch_id:$batch_id, pipeline_id:$pipeline_id}]->(d)
    )
    RETURN f.fact_id AS id
    """
    return run_query(cypher, params)
5) Final pipeline order (lock this)
Build & persist routing_key/exhibit_canon/source_sha256 (hash raw text).

Run REFERENCES (once per report); set ExhibitContent.routing_keys.

Resolve schema for each node (exhibit priority 2.02 > 7.01).

Extract with spans.

Link to XBRL → set period/unit/members (best-effort).

Finalize (convert to UIDs, compute context_id if any, then compute fact_id & dedupe_key).

Deduplicate (now that keys are correct) → mark superseded flags.

Write each fact via create_eightkfact(...).

If 8-K/A, run supersedence.

QA checks.

