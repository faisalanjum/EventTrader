# EventMarketDB Neo4j Schema Reference v2

## 🎯 Query Pattern Guide (MOST IMPORTANT)

### Finding Financial Data: XBRL vs Non-XBRL Patterns

**XBRL Pattern** (10-K, 10-Q, 10-K/A, 10-Q/A ONLY):
```cypher
-- For specific financial metrics (revenue, EPS, assets)
MATCH (c:Company {ticker: 'AAPL'})
  <-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
  -[:HAS_XBRL]->(x:XBRLNode)
  <-[:REPORTS]-(f:Fact)
  -[:HAS_CONCEPT]->(concept:Concept)
WHERE concept.label CONTAINS 'Revenue'
  AND f.is_numeric = '1'
RETURN r.created, concept.label, f.value
```

### ⚠️ XBRL Dimensional Data Complexity

A single concept like Revenue returns MULTIPLE facts due to dimensions:

Example for AAPL Revenue:
- 1 total revenue (no dimensions)
- 5 geographic segments (Americas, Europe, China, Japan, Asia Pacific)
- 7 product categories (iPhone, Mac, iPad, Wearables, Services)
- 2 type breakdowns (Product vs Service)

**CRITICAL: Filter dimensions appropriately:**
```cypher
-- Get total only (no dimensions)
WHERE NOT EXISTS((f)-[:FACT_MEMBER]->())

-- Get specific dimension
MATCH (f)-[:FACT_MEMBER]->(m:Member)
WHERE m.label IN ['iPhone', 'Mac', 'iPad']
```

**Non-XBRL Pattern** (ALL report types including 8-K):
```cypher
-- For narrative discussions and 8-K events
MATCH (c:Company {ticker: 'AAPL'})
  <-[:PRIMARY_FILER]-(r:Report)
  -[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE r.formType = '8-K'
  AND esc.section_name = 'ResultsofOperationsandFinancialCondition'
RETURN r.created, esc.content
```

### Key Decision: When to Use Which Pattern?
- **Need specific metrics** (revenue, EPS, assets): Use XBRL (10-K/10-Q/10-K/A/10-Q/A only)
- **Need narrative/discussion**: Use ExtractedSectionContent
- **Working with 8-K**: ALWAYS use ExtractedSectionContent (8-K NEVER has XBRL)
- **Need management commentary**: Use ExtractedSectionContent
- **Need precise financial values**: Use XBRL when available

## 📈 Return Property Semantics

### Return Timeframes
- **hourly_***: 1-hour return after event
- **session_***: Market session return (pre/regular/post)
- **daily_***: Full trading day return

### Return Levels
- **\*_stock**: Individual company return
- **\*_industry**: Industry-level return  
- **\*_sector**: Sector-level return
- **\*_macro**: Market index return (SPY)

### Return Property Coverage
Return properties appear on INFLUENCES, PRIMARY_FILER, and REFERENCED_IN relationships:
- Often optional and sometimes missing
- INFLUENCES: ~22% have stock returns, ~48% have industry returns
- PRIMARY_FILER: ~98% have stock returns
- REFERENCED_IN: ~97% have stock returns

### ⚠️ Variable Data Types Warning
hourly_* properties on relationships can be:
- **FLOAT**: Single value
- **DoubleArray**: Array of values

Handle both cases:
```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
RETURN CASE 
  WHEN pf.hourly_stock IS NULL THEN NULL
  WHEN size(pf.hourly_stock) > 1 THEN pf.hourly_stock[0]  -- Array
  ELSE pf.hourly_stock  -- Single value
END as hourly_value
```

### INFLUENCES Pattern (CRITICAL)
News/Report/Transcript creates 4 separate INFLUENCES relationships:
- → Company (only daily_stock, hourly_stock, session_stock populated)
- → Industry (only daily_industry, hourly_industry, session_industry populated)  
- → Sector (only daily_sector, hourly_sector, session_sector populated)
- → MarketIndex (only daily_macro, hourly_macro, session_macro populated)

Each relationship ONLY contains returns for its target entity type!

## 🏗️ Hierarchical Market Structure

```
MarketIndex (1 instance)
    ↑ BELONGS_TO
Sector (11 instances)
    ↑ BELONGS_TO
Industry (115 instances)
    ↑ BELONGS_TO
Company (796 instances)
```

**Navigation**: Company → Industry → Sector → MarketIndex (strictly one-way)

## 📅 Date/Time Format Specifications

### Date/Time Formats
- Date.date: "YYYY-MM-DD"
- Report.created: ISO 8601 with timezone "YYYY-MM-DDTHH:MM:SS-05:00" (EST/EDT)
- Dividend dates: "YYYY-MM-DD"
- All timestamps: Eastern Time (ET)

## ⏰ Temporal Navigation

```cypher
-- Navigate trading days sequentially
MATCH (d1:Date {date: '2024-01-15'})-[:NEXT*5]->(d2:Date)
RETURN d2.date -- Returns 5 days later

-- Jump to next/previous trading day
MATCH (d:Date {date: '2024-01-15'})
RETURN d.next_trading_date, d.previous_trading_date
```

## 💡 Common Access Patterns

### Latest Report for Company
```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)
RETURN r ORDER BY r.created DESC LIMIT 1
```

### Earnings Transcripts with Q&A
```cypher
MATCH (c:Company {ticker: 'AAPL'})
  -[:HAS_TRANSCRIPT]->(t:Transcript)
  -[:HAS_QA_EXCHANGE]->(qa:QAExchange)
RETURN t.conference_datetime, qa.questioner, qa.exchanges
```

### News Impact Analysis
```cypher
MATCH (n:News)-[inf:INFLUENCES]->(c:Company {ticker: 'AAPL'})
WHERE n.created > datetime('2024-01-01')
RETURN n.title, inf.hourly_stock, inf.daily_stock
```

### ⚠️ CRITICAL: INFLUENCES Property Access Quirk
INFLUENCES relationships have a Neo4j quirk with certain alias names:

```cypher
-- ❌ WRONG (causes syntax error):
MATCH (n:News)-[inf:INFLUENCES]->(c:Company)
WHERE inf.daily_stock IS NOT NULL  -- ERROR: Type mismatch!

-- ✅ CORRECT (use 'r' or other aliases):
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL  -- Works!

-- Also handle 'NaN' string values:
WHERE r.daily_stock IS NOT NULL AND r.daily_stock <> 'NaN'
WITH toFloat(r.daily_stock) as daily_return
WHERE NOT isNaN(daily_return)
```

## 🔑 Identifier Patterns

### Key Identifier Formats
- CIK: Always 10 digits, zero-padded (e.g., "0000037785")
- ticker = symbol (always identical)
- accessionNo: SEC accession number format

## 🎯 Query Decision Trees (MOST CRITICAL)

### How to Query Financial Data

```
User asks about "revenue" →
├─ With "discuss/explain/analyze" → ExtractedSectionContent
└─ Just the number → XBRL (if 10-K/10-Q/10-K/A/10-Q/A)
    └─ Not 10-K/10-Q → ExtractedSectionContent or financial_statements JSON

User asks about 8-K event →
└─ ALWAYS ExtractedSectionContent (8-K NEVER has XBRL)

User asks about company relationships →
└─ RELATED_TO (note: bidirectional=true but single edge stored)
```

### 8-K Material Events
```cypher
MATCH (r:Report {formType: '8-K'})
  -[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name IN [
  'EntryintoaMaterialDefinitiveAgreement',
  'CompletionofAcquisitionorDispositionofAssets',
  'DepartureofDirectorsorCertainOfficers'
]
RETURN r.created, r.cik, esc.section_name, esc.content
ORDER BY r.created DESC
```

## Node Labels (Actual Counts from Database)

### Abstract
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_abstract_id_unique | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | - | |
| label | STRING | ✗ | - | abstract_ft | |
| namespace | STRING | ✗ | - | - | |
| category | STRING | ✗ | - | - | |
| type_local | STRING | ✗ | - | - | |
| balance | STRING | ✗ | - | - | |
| period_type | STRING | ✗ | - | - | |
| concept_type | STRING | ✗ | - | - | |

### AdminReport
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_adminreport_id_unique | |
| category | STRING | ✗ | - | - | |
| code | STRING | ✗ | - | - | |
| label | STRING | ✗ | - | - | |
| displayLabel | STRING | ✗ | - | - | |

### AdminSection
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_adminsection_id_unique | |

### Company
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_company_id_unique | |
| cik | STRING | ✗ | - | - | |
| ticker | STRING | ✗ | - | - | |
| symbol | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | company_ft | ⚠️ May contain apostrophes (e.g., "DICK'S SPORTING GOODS") |
| displayLabel | STRING | ✗ | - | company_ft | |
| exchange | STRING | ✗ | - | - | |
| sector | STRING | ✗ | - | - | |
| industry | STRING | ✗ | - | - | |
| industry_normalized | STRING | ✗ | - | - | |
| sector_etf | STRING | ✗ | - | - | |
| industry_etf | STRING | ✗ | - | - | |
| mkt_cap | STRING | ✗ | - | - | Comma-separated number (e.g., "4,311,821,002") |
| shares_out | STRING | ✗ | - | - | Comma-separated number (e.g., "124,840,000") |
| employees | STRING | ✓ | - | - | Comma-separated number (e.g., "6,600") |
| fiscal_year_end_month | STRING | ✗ | - | - | |
| fiscal_year_end_day | STRING | ✗ | - | - | |

### Concept
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_concept_id_unique | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | concept_ft | |
| label | STRING | ✗ | - | concept_ft | |
| namespace | STRING | ✗ | - | - | us-gaap uses yearly versions (e.g., "http://fasb.org/us-gaap/2023", "http://fasb.org/us-gaap/2024") |
| category | STRING | ✗ | - | - | |
| type_local | STRING | ✗ | - | - | |
| balance | STRING | ✗ | - | - | |
| period_type | STRING | ✗ | - | - | |
| concept_type | STRING | ✗ | - | - | |

### Context
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_context_id_unique | |
| u_id | STRING | ✗ | - | - | |
| context_id | STRING | ✗ | - | - | |
| cik | STRING | ✗ | - | - | |
| period_u_id | STRING | ✗ | - | - | |
| member_u_ids | LIST<STRING> | ✗ | STRING / 7 | - | |
| dimension_u_ids | LIST<STRING> | ✗ | STRING / 7 | - | |

### Date
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_date_id_unique | |
| date | STRING | ✗ | - | - | |
| is_trading_day | STRING | ✗ | - | - | |
| pre_market_current_day | STRING | ✓ | - | - | Present in 641/936 (68%) |
| market_open_current_day | STRING | ✓ | - | - | Present in 641/936 (68%) |
| market_close_current_day | STRING | ✓ | - | - | Present in 641/936 (68%) |
| post_market_current_day | STRING | ✓ | - | - | Present in 641/936 (68%) |
| pre_market_previous_day | STRING | ✗ | - | - | |
| market_open_previous_day | STRING | ✗ | - | - | |
| market_close_previous_day | STRING | ✗ | - | - | |
| post_market_previous_day | STRING | ✗ | - | - | |
| pre_market_next_day | STRING | ✗ | - | - | |
| market_open_next_day | STRING | ✗ | - | - | |
| market_close_next_day | STRING | ✗ | - | - | |
| post_market_next_day | STRING | ✗ | - | - | |
| previous_trading_date | STRING | ✗ | - | - | |
| next_trading_date | STRING | ✗ | - | - | |

### Dimension
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_dimension_id_unique | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | - | |
| label | STRING | ✗ | - | - | |
| is_explicit | STRING | ✗ | - | - | Values: '0' or '1' (boolean as string) |
| is_typed | STRING | ✗ | - | - | Values: '0' or '1' (boolean as string) |
| network_uri | STRING | ✗ | - | - | |

### Dividend
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_dividend_id_unique | |
| ticker | STRING | ✗ | - | - | |
| ex_dividend_date | STRING | ✗ | - | - | |
| pay_date | STRING | ✗ | - | - | |
| record_date | STRING | ✗ | - | - | |
| declaration_date | STRING | ✗ | - | - | |
| cash_amount | STRING | ✗ | - | - | |
| dividend_type | STRING | ✗ | - | - | |
| frequency | STRING | ✗ | - | - | |
| currency | STRING | ✗ | - | - | |

### Domain
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_domain_id_unique | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | - | |
| label | STRING | ✗ | - | - | |
| level | STRING | ✗ | - | - | |
| parent_qname | STRING | ✗ | - | - | |

### ExhibitContent
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_exhibitcontent_id_unique | |
| exhibit_number | STRING | ✗ | - | exhibit_content_ft | |
| content | STRING | ✗ | - | exhibit_content_ft | |
| form_type | STRING | ✗ | - | - | |
| filer_cik | STRING | ✓ | - | - | Missing in 3.29% |
| filed_at | STRING | ✗ | - | - | |
| filing_id | STRING | ✗ | - | - | |

### ExtractedSectionContent
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_extractedsectioncontent_id_unique | |
| section_name | STRING | ✗ | - | extracted_section_content_ft | See Common section_name values below |
| content | STRING | ✗ | - | extracted_section_content_ft | |
| content_length | STRING | ✗ | - | - | |
| form_type | STRING | ✗ | - | - | |
| filer_cik | STRING | ✓ | - | - | Missing in 2.52% |
| filed_at | STRING | ✗ | - | - | |
| filing_id | STRING | ✗ | - | - | |

#### Complete section_name Reference (53 verified types)

⚠️ CRITICAL: Section names have NO spaces between words

**Most Common (by count):**
1. FinancialStatementsandExhibits - 17,880 (8-K)
2. ResultsofOperationsandFinancialCondition - 8,083 (8-K)
3. ControlsandProcedures - 7,479
4. LegalProceedings - 7,260
5. RiskFactors - 7,218

**10-K/10-Q Primary Sections (21 types):**
- Business
- Properties
- LegalProceedings
- MineSafetyDisclosures
- UnresolvedStaffComments
- RiskFactors
- Cybersecurity
- MarketforRegistrant'sCommonEquity,RelatedStockholderMattersandIssuerPurchasesofEquitySecurities
- SelectedFinancialData(priortoFebruary2021)
- ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations
- Management'sDiscussionandAnalysisofFinancialConditionandResultsofOperations
- QuantitativeandQualitativeDisclosuresAboutMarketRisk
- QuantitativeandQualitativeDisclosuresaboutMarketRisk
- FinancialStatements
- FinancialStatementsandSupplementaryData
- ChangesinandDisagreementswithAccountantsonAccountingandFinancialDisclosure
- ControlsandProcedures
- OtherInformation
- Directors,ExecutiveOfficersandCorporateGovernance
- ExecutiveCompensation
- SecurityOwnershipofCertainBeneficialOwnersandManagementandRelatedStockholderMatters
- CertainRelationshipsandRelatedTransactions,andDirectorIndependence
- PrincipalAccountantFeesandServices
- ExhibitsandFinancialStatementSchedules
- Exhibits

**8-K Event Sections (27 types):**
- EntryintoaMaterialDefinitiveAgreement (Item 1.01)
- TerminationofaMaterialDefinitiveAgreement (Item 1.02)
- BankruptcyorReceivership (Item 1.03)
- MaterialCybersecurityIncidents (Item 1.05)
- CompletionofAcquisitionorDispositionofAssets (Item 2.01)
- ResultsofOperationsandFinancialCondition (Item 2.02)
- CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant (Item 2.03)
- TriggeringEventsThatAccelerateorIncreaseaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangement (Item 2.04)
- CostsAssociatedwithExitorDisposalActivities (Item 2.05)
- MaterialImpairments (Item 2.06)
- NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing (Item 3.01)
- UnregisteredSalesofEquitySecurities (Item 3.02)
- MaterialModificationstoRightsofSecurityHolders (Item 3.03)
- ChangesinRegistrantsCertifyingAccountant (Item 4.01)
- NonRelianceonPreviouslyIssuedFinancialStatementsoraRelatedAuditReportorCompletedInterimReview (Item 4.02)
- ChangesinControlofRegistrant (Item 5.01)
- DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers (Item 5.02)
- AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear (Item 5.03)
- TemporarySuspensionofTradingUnderRegistrantsEmployeeBenefitPlans (Item 5.04)
- AmendmentstotheRegistrantsCodeofEthics,orWaiverofaProvisionoftheCodeofEthics (Item 5.05)
- SubmissionofMatterstoaVoteofSecurityHolders (Item 5.07)
- ShareholderNominationsPursuanttoExchangeActRule14a-11
- RegulationFDDisclosure (Item 7.01)
- OtherEvents (Item 8.01)
- FinancialStatementsandExhibits (Item 9.01)

**Other Sections (5 types):**
- UnregisteredSalesofEquitySecuritiesandUseofProceeds
- DefaultsUponSeniorSecurities
- MineSafetyReportingofShutdownsandPatternsofViolations

### Fact
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_fact_id_unique | |
| fact_id | STRING | ✗ | - | - | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | fact_textblock_ft | |
| value | STRING | ✗ | - | fact_textblock_ft | |
| decimals | STRING | ✓ | - | - | Common: '0'-'6', '-1' to '-6', 'INF' (409k), 'null' (840k string!), extreme: 96, -12 |
| is_numeric | STRING | ✗ | - | - | Values: '1' (numeric) or '0' (text/nil) |
| is_nil | STRING | ✗ | - | - | Values: '1' (nil) or '0' (has value) |
| context_id | STRING | ✗ | - | - | |
| period_ref | STRING | ✗ | - | - | |
| concept_ref | STRING | ✗ | - | - | |
| unit_ref | STRING | ✓ | - | - | |

### FilingTextContent
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_filingtextcontent_id_unique | |
| content | STRING | ✗ | - | filing_text_content_ft | |
| form_type | STRING | ✗ | - | filing_text_content_ft | |
| filer_cik | STRING | ✓ | - | - | Missing in 53.85% |
| filed_at | STRING | ✗ | - | - | |
| filing_id | STRING | ✗ | - | - | |

### FinancialStatement (0 instances - preserved for future use)
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_financialstatement_id_unique | |

### FinancialStatement (0 instances - preserved for future use)Content
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_financialstatementcontent_id_unique | |
| statement_type | STRING | ✗ | - | financial_statement_content_ft | |
| value | STRING | ✗ | - | financial_statement_content_ft | |
| form_type | STRING | ✗ | - | - | |
| filer_cik | STRING | ✗ | - | - | |
| filed_at | STRING | ✗ | - | - | |
| filing_id | STRING | ✗ | - | - | |

### FullTranscriptText
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_fulltranscripttext_id_unique | |
| content | STRING | ✗ | - | full_transcript_ft | |

### Guidance
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_guidance_id_unique | |

### HyperCube
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_hypercube_id_unique | |

### Industry
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_industry_id_unique | |
| sector_id | STRING | ✗ | - | - | |
| etf | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | - | |

### LineItems
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_lineitems_id_unique | |

### MarketIndex
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_marketindex_id_unique | |
| ticker | STRING | ✗ | - | - | |
| etf | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | - | |

### Member
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_member_id_unique | |
| u_id | STRING | ✗ | - | - | |
| qname | STRING | ✗ | - | - | |
| label | STRING | ✗ | - | - | |
| level | STRING | ✗ | - | - | |
| parent_qname | STRING | ✓ | - | - | |

### Memory
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| name | STRING | ✓ | - | search (fulltext) | |
| type | STRING | ✓ | - | search (fulltext) | |
| observations | LIST<STRING> | ✓ | STRING | search (fulltext) | |

### News
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_news_id_unique | |
| title | STRING | ✗ | - | news_ft | |
| body | STRING | ✗ | - | news_ft | |
| teaser | STRING | ✗ | - | news_ft | |
| url | STRING | ✗ | - | - | |
| created | STRING | ✗ | - | - | |
| updated | STRING | ✗ | - | - | |
| authors | STRING | ✗ | - | - | |
| channels | STRING | ✗ | - | - | |
| tags | STRING | ✗ | - | - | |
| returns_schedule | STRING | ✗ | - | - | |
| market_session | STRING | ✗ | - | - | Values: 'post_market', 'pre_market', 'in_market', 'market_closed' |
| embedding | LIST<FLOAT> | ✓ | FLOAT / 3072 | news_vector_index | cosine similarity, HNSW |

### Other
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_other_id_unique | |

### Period
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_period_id_unique | |
| u_id | STRING | ✗ | - | - | |
| period_type | STRING | ✗ | - | - | 'instant' or 'duration' |
| start_date | STRING | ✓ | - | - | Always use this for instant periods |
| end_date | STRING | ✓ | - | - | ⚠️ For instant: always 'null' string (not NULL) |

#### Period Instant Date Quirk
- period_type='instant' has end_date property but ALWAYS contains string 'null' (2,672 instances)
- Use start_date for instant periods
- Check: `WHERE p.end_date = 'null'` not `WHERE p.end_date IS NULL`

### PreparedRemark
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_preparedremark_id_unique | |
| content | STRING | ✗ | - | prepared_remarks_ft | |

### QAExchange
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_qaexchange_id_unique | |
| transcript_id | STRING | ✗ | - | - | |
| sequence | STRING | ✗ | - | - | |
| questioner | STRING | ✗ | - | - | |
| responders | STRING | ✓ | - | - | Comma-separated names (e.g., "John Doe, Jane Smith") |
| questioner_title | STRING | ✓ | - | - | Present in ~95% |
| responder_title | STRING | ✓ | - | - | Present in ~97% |
| exchanges | STRING | ✗ | - | qa_exchange_ft | JSON array: [{"role": "question", "text": "..."}, {"role": "answer", "text": "..."}] |
| embedding | LIST<FLOAT> | ✓ | FLOAT / 3072 | qaexchange_vector_idx | cosine similarity, HNSW |

### QuestionAnswer
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_questionanswer_id_unique | |
| content | STRING | ✗ | - | question_answer_ft | |
| speaker_roles | STRING | ✓ | - | - | Present in 25/31 (81%) |

### Report
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_report_id_unique | |
| cik | STRING | ✓ | - | - | Missing in ~3% |
| accessionNo | STRING | ✗ | - | - | |
| formType | STRING | ✗ | - | - | |
| periodOfReport | STRING | ✓ | - | - | Missing in ~3% |
| created | STRING | ✗ | - | - | |
| isAmendment | BOOLEAN | ✗ | - | - | |
| xbrl_status | STRING | ✓ | - | - | Values: NULL, 'SKIPPED', 'COMPLETED', 'REFERENCE_ONLY', 'QUEUED', 'PROCESSING', 'FAILED' |
| xbrl_error | STRING | ✓ | - | - | |
| returns_schedule | STRING | ✗ | - | - | |
| market_session | STRING | ✗ | - | - | Values: 'post_market', 'pre_market', 'in_market', 'market_closed' |
| is_xml | BOOLEAN | ✗ | - | - | |
| items | STRING | ✓ | - | - | Present in ~76%, JSON array of strings |
| entities | STRING | ✗ | - | - | JSON array with single string element |
| symbols | STRING | ✗ | - | - | JSON array with single string element |
| description | STRING | ✓ | - | - | |
| linkToHtml | STRING | ✗ | - | - | |
| linkToTxt | STRING | ✗ | - | - | |
| linkToFilingDetails | STRING | ✗ | - | - | |
| primaryDocumentUrl | STRING | ✗ | - | - | |
| exhibits | STRING | ✓ | - | - | JSON object (e.g., {"EX-99.1": "url"}), not array |
| exhibit_contents | STRING | ✓ | - | - | JSON object, not array |
| extracted_sections | STRING | ✓ | - | - | |
| financial_statements | STRING | ✓ | - | - | JSON blob, 18KB-1.7MB (present in ~23%) |
| effectivenessDate | STRING | ✓ | - | - | Rare (7 instances) |

### Sector
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_sector_id_unique | |
| etf | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | - | |

### Split
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_split_id_unique | |
| ticker | STRING | ✗ | - | - | |
| execution_date | STRING | ✗ | - | - | |
| split_from | STRING | ✗ | - | - | |
| split_to | STRING | ✗ | - | - | |

### Transcript
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_transcript_id_unique | |
| symbol | STRING | ✗ | - | - | |
| formType | STRING | ✗ | - | - | |
| company_name | STRING | ✗ | - | - | |
| conference_datetime | STRING | ✗ | - | - | |
| fiscal_year | STRING | ✗ | - | - | |
| fiscal_quarter | STRING | ✗ | - | - | |
| calendar_year | STRING | ✗ | - | - | |
| calendar_quarter | STRING | ✗ | - | - | |
| speakers | STRING | ✗ | - | - | |
| created | STRING | ✗ | - | - | |
| updated | STRING | ✗ | - | - | |

### Unit
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_unit_id_unique | |
| u_id | STRING | ✗ | - | - | |
| unit_reference | STRING | ✗ | - | - | |
| name | STRING | ✗ | - | - | Common: 'iso4217:USD', 'shares', 'pure', company-specific like 'dri:segment' |
| status | STRING | ✗ | - | - | Values: 'REC', 'null' (string literal "null", not NULL!) |
| is_simple_unit | STRING | ✗ | - | - | Values: '1', '0', 'null' (string literal "null", not NULL!) |
| is_divide | STRING | ✗ | - | - | |
| item_type | STRING | ✓ | - | - | |
| namespace | STRING | ✓ | - | - | |
| registry_id | STRING | ✓ | - | - | |

### XBRLNode
| Prop | Type | Nullable | ElementType / MaxLen | Index/Constraint | Quirk / Format |
|------|------|----------|---------------------|------------------|----------------|
| id | STRING | ✗ | - | constraint_xbrlnode_id_unique | |
| cik | STRING | ✗ | - | - | |
| accessionNo | STRING | ✗ | - | - | |
| report_id | STRING | ✗ | - | - | |
| displayLabel | STRING | ✗ | - | - | |
| primaryDocumentUrl | STRING | ✗ | - | - | |

## Relationship Types

### BELONGS_TO
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Company → Industry | → | many-to-1 | 1 | No |
| Industry → Sector | → | many-to-1 | 1 | No |
| Sector → MarketIndex | → | many-to-1 | 1 | No |

### CALCULATION_EDGE
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Fact | → | many-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| cik | STRING | ✗ | - | constraint_calculation_edge_unique |
| report_id | STRING | ✗ | - | constraint_calculation_edge_unique |
| network_uri | STRING | ✗ | - | - |
| network_name | STRING | ✗ | - | - |
| parent_id | STRING | ✗ | - | constraint_calculation_edge_unique |
| child_id | STRING | ✗ | - | constraint_calculation_edge_unique |
| context_id | STRING | ✗ | - | constraint_calculation_edge_unique |
| weight | DOUBLE | ✗ | - | constraint_calculation_edge_unique |
| order | DOUBLE | ✗ | - | - |
| report_instance | STRING | ✗ | - | - |
| company_cik | STRING | ✗ | - | - |

### DECLARED_DIVIDEND
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Company → Dividend | → | one-to-many | 0 | No |

### DECLARED_SPLIT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Company → Split | → | one-to-many | 0 | No |

### FACT_DIMENSION
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Dimension | → | many-to-many | 0 | No |

### FACT_MEMBER
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Member | → | many-to-many | 0 | No |

### FOR_COMPANY
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Context → Company | → | many-to-one | 1 | No |

### HAS_CONCEPT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Concept | → | many-to-one | 1* | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| key | STRING | ✗ | - | hasConcept_key | |

### HAS_DIVIDEND
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Date → Dividend | → | one-to-many | 0 | No |

### HAS_DOMAIN
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Dimension → Domain | → | many-to-many | 0 | No |
| Dimension → Member | → | many-to-many | 0 | No |

### HAS_EXHIBIT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → ExhibitContent | → | one-to-many | 0 | No |

### HAS_FILING_TEXT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → FilingTextContent | → | one-to-many | 0 | No |

### HAS_FINANCIAL_STATEMENT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → FinancialStatementContent | → | one-to-many | 0 | No |

### HAS_FULL_TEXT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Transcript → FullTranscriptText | → | one-to-many | 0 | No |

### HAS_MEMBER
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Domain → Member | → | one-to-many | 0 | No |
| Domain → Domain | → | one-to-many | 0 | No |
| Member → Member | → | one-to-many | 0 | No |

### HAS_PERIOD
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Period | → | many-to-one | 1* | No |
| Context → Period | → | many-to-one | 1 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| key | STRING | ✗ | - | hasPeriod_key | |

### HAS_PREPARED_REMARKS
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Transcript → PreparedRemark | → | one-to-many | 0 | No |

### HAS_PRICE
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Date → Company | → | one-to-many | 0 | No |
| Date → Industry | → | one-to-many | 0 | No |
| Date → Sector | → | one-to-many | 0 | No |
| Date → MarketIndex | → | one-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| open | DOUBLE | ✗ | - | Opening price |
| close | DOUBLE | ✗ | - | Closing price |
| high | DOUBLE | ✗ | - | High price |
| low | DOUBLE | ✗ | - | Low price |
| volume | DOUBLE | ✗ | - | Trading volume |
| vwap | DOUBLE | ✗ | - | Volume-weighted average price |
| transactions | DOUBLE | ✗ | - | Number of transactions |
| daily_return | DOUBLE | ✗ | - | Daily return percentage |
| timestamp | STRING | ✗ | - | Format: "YYYY-MM-DD HH:MM:SS-0400" (space before TZ, not 'T') |

### HAS_QA_EXCHANGE
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Transcript → QAExchange | → | one-to-many | 0 | No |

### HAS_QA_SECTION
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Transcript → QuestionAnswer | → | one-to-many | 0 | No |

### HAS_SECTION
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → ExtractedSectionContent | → | one-to-many | 0 | No |

### HAS_SPLIT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Date → Split | → | one-to-many | 0 | No |

### HAS_SUB_REPORT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| AdminReport → AdminReport | → | one-to-many | 0 | No |

### HAS_TRANSCRIPT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Company → Transcript | → | one-to-many | 0 | No |

### HAS_UNIT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Unit | → | many-to-one | 0* | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| key | STRING | ✗ | - | hasUnit_key | |

### HAS_XBRL
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → XBRLNode | → | one-to-one | 0 | No |

### IN_CATEGORY
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → AdminReport | → | many-to-one | 1 | No |

### IN_CONTEXT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → Context | → | many-to-one | 1 | No |

### INFLUENCES
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → Industry | → | many-to-many | 0 | No |
| Report → Sector | → | many-to-many | 0 | No |
| Report → MarketIndex | → | many-to-many | 0 | No |
| News → Company | → | many-to-many | 0 | No |
| News → Industry | → | many-to-many | 0 | No |
| News → Sector | → | many-to-many | 0 | No |
| News → MarketIndex | → | many-to-many | 0 | No |
| Transcript → Company | → | many-to-many | 0 | No |
| Transcript → Industry | → | many-to-many | 0 | No |
| Transcript → Sector | → | many-to-many | 0 | No |
| Transcript → MarketIndex | → | many-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| symbol | STRING | ✗ | - | - |
| created_at | STRING | ✗ | - | - |
| daily_stock | DOUBLE | ✓ | - | Missing in ~2-3% |
| hourly_stock | DOUBLE | ✓ | - | Missing in ~2-3% |
| session_stock | DOUBLE | ✓ | - | Missing in ~2-3% |
| daily_industry | DOUBLE | ✓ | - | Missing in ~1% |
| hourly_industry | DOUBLE | ✓ | - | Missing in ~2-3% |
| session_industry | DOUBLE | ✓ | - | Missing in ~3% |
| daily_sector | DOUBLE | ✗ | - | - |
| hourly_sector | DOUBLE | ✗ | - | - |
| session_sector | DOUBLE | ✗ | - | - |
| daily_macro | DOUBLE | ✗ | - | - |
| hourly_macro | DOUBLE | ✗ | - | - |
| session_macro | DOUBLE | ✗ | - | - |

### NEXT
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Date → Date | → | one-to-one | 0 | No |

### NEXT_EXCHANGE
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| QAExchange → QAExchange | → | one-to-one | 0 | No |

### PARENT_OF
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Member → Member | → | one-to-many | 0 | No |
| Domain → Member | → | one-to-many | 0 | No |

### PRESENTATION_EDGE
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Abstract → Fact | → | many-to-many | 0 | No |
| Abstract → Abstract | → | many-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| cik | STRING | ✗ | - | constraint_presentation_edge_unique |
| report_id | STRING | ✗ | - | constraint_presentation_edge_unique |
| network_uri | STRING | ✗ | - | - |
| network_name | STRING | ✗ | - | constraint_presentation_edge_unique |
| parent_id | STRING | ✗ | - | constraint_presentation_edge_unique |
| child_id | STRING | ✗ | - | constraint_presentation_edge_unique |
| parent_level | LONG | ✗ | - | constraint_presentation_edge_unique |
| child_level | LONG | ✗ | - | constraint_presentation_edge_unique |
| parent_order | INTEGER | ✗ | - | - |
| child_order | INTEGER | ✗ | - | - |
| company_cik | STRING | ✗ | - | - |

### PRIMARY_FILER
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → Company | → | many-to-one | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| symbol | STRING | ✗ | - | - |
| created_at | STRING | ✗ | - | - |
| daily_stock | DOUBLE | ✓ | - | Missing in ~2% |
| hourly_stock | DOUBLE | ✗ | - | - |
| session_stock | DOUBLE | ✓ | - | Missing in ~2% |
| daily_industry | DOUBLE | ✓ | - | Missing in ~1% |
| hourly_industry | DOUBLE | ✓ | - | Missing in ~1% |
| session_industry | DOUBLE | ✓ | - | Missing in ~2% |
| daily_sector | DOUBLE | ✗ | - | - |
| hourly_sector | DOUBLE | ✗ | - | - |
| session_sector | DOUBLE | ✗ | - | - |
| daily_macro | DOUBLE | ✗ | - | - |
| hourly_macro | DOUBLE | ✗ | - | - |
| session_macro | DOUBLE | ✗ | - | - |

### REFERENCED_IN
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Report → Company | → | many-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| symbol | STRING | ✗ | - | - |
| created_at | STRING | ✗ | - | - |
| daily_stock | DOUBLE | ✓ | - | Missing in ~3% |
| hourly_stock | DOUBLE | ✓ | - | Missing in ~3% |
| session_stock | DOUBLE | ✓ | - | Missing in ~3% |
| daily_industry | DOUBLE | ✗ | - | - |
| hourly_industry | DOUBLE | ✓ | - | Missing in ~3% |
| session_industry | DOUBLE | ✓ | - | Missing in ~3% |
| daily_sector | DOUBLE | ✗ | - | - |
| hourly_sector | DOUBLE | ✗ | - | - |
| session_sector | DOUBLE | ✗ | - | - |
| daily_macro | DOUBLE | ✗ | - | - |
| hourly_macro | DOUBLE | ✗ | - | - |
| session_macro | DOUBLE | ✗ | - | - |

### RELATED_TO
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Company → Company | → | many-to-many | 0 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| source_ticker | STRING | ✗ | - | - |
| target_ticker | STRING | ✗ | - | - |
| relationship_type | STRING | ✗ | - | - |
| bidirectional | BOOLEAN | ✗ | - | Always true, but stored as single edge (not reciprocal) |

### REPORTS
| Source → Target | Direction | Cardinality | Min-Card | Self-Rel |
|-----------------|-----------|-------------|----------|----------|
| Fact → XBRLNode | → | many-to-one | 1 | No |

| Prop | Type | Nullable | ElementType / MaxLen | Quirk / Format |
|------|------|----------|---------------------|----------------|
| report_id | STRING | ✗ | - | - |
| company_cik | STRING | ✗ | - | - |

## Indexes & Constraints

### Unique Constraints
- constraint_abstract_id_unique: Abstract(id)
- constraint_adminreport_id_unique: AdminReport(id)
- constraint_adminsection_id_unique: AdminSection(id)
- constraint_company_id_unique: Company(id)
- constraint_concept_id_unique: Concept(id)
- constraint_context_id_unique: Context(id)
- constraint_date_id_unique: Date(id)
- constraint_dimension_id_unique: Dimension(id)
- constraint_dividend_id_unique: Dividend(id)
- constraint_domain_id_unique: Domain(id)
- constraint_exhibitcontent_id_unique: ExhibitContent(id)
- constraint_extractedsectioncontent_id_unique: ExtractedSectionContent(id)
- constraint_fact_id_unique: Fact(id)
- constraint_filingtextcontent_id_unique: FilingTextContent(id)
- constraint_financialstatement_id_unique: FinancialStatement(id)
- constraint_financialstatementcontent_id_unique: FinancialStatementContent(id)
- constraint_fulltranscripttext_id_unique: FullTranscriptText(id)
- constraint_guidance_id_unique: Guidance(id)
- constraint_hypercube_id_unique: HyperCube(id)
- constraint_industry_id_unique: Industry(id)
- constraint_lineitems_id_unique: LineItems(id)
- constraint_marketindex_id_unique: MarketIndex(id)
- constraint_member_id_unique: Member(id)
- constraint_news_id_unique: News(id)
- constraint_other_id_unique: Other(id)
- constraint_period_id_unique: Period(id)
- constraint_preparedremark_id_unique: PreparedRemark(id)
- constraint_qaexchange_id_unique: QAExchange(id)
- constraint_questionanswer_id_unique: QuestionAnswer(id)
- constraint_report_id_unique: Report(id)
- constraint_sector_id_unique: Sector(id)
- constraint_split_id_unique: Split(id)
- constraint_transcript_id_unique: Transcript(id)
- constraint_unit_id_unique: Unit(id)
- constraint_xbrlnode_id_unique: XBRLNode(id)

### Relationship Unique Constraints
- constraint_calculation_edge_unique: CALCULATION_EDGE(cik, report_id, network_uri, parent_id, child_id, context_id, weight)
- constraint_presentation_edge_unique: PRESENTATION_EDGE(cik, report_id, network_name, parent_id, child_id, parent_level, child_level)
- hasConcept_key: HAS_CONCEPT(key)
- hasPeriod_key: HAS_PERIOD(key)
- hasUnit_key: HAS_UNIT(key)

### Full-text Indexes
| Index Name | Target | Fields | Analyzer | Case-Sensitive |
|------------|--------|--------|----------|----------------|
| abstract_ft | Abstract | label | standard | No |
| company_ft | Company | name, displayLabel | standard | No |
| concept_ft | Concept | label, qname | standard | No |
| exhibit_content_ft | ExhibitContent | content, exhibit_number | standard | No |
| extracted_section_content_ft | ExtractedSectionContent | content, section_name | standard | No |
| fact_textblock_ft | Fact | value, qname | standard | No |
| filing_text_content_ft | FilingTextContent | content, form_type | standard | No |
| financial_statement_content_ft | FinancialStatementContent | value, statement_type | standard | No |
| full_transcript_ft | FullTranscriptText | content | standard | No |
| news_ft | News | title, body, teaser | standard | No |
| prepared_remarks_ft | PreparedRemark | content | standard | No |
| qa_exchange_ft | QAExchange | exchanges | standard | No |
| question_answer_ft | QuestionAnswer | content | standard | No |
| search | Memory | name, type, observations | standard | No |

### Vector Indexes
| Index Name | Label.Property | Dimension | Similarity | Algorithm |
|------------|----------------|-----------|------------|-----------|
| news_vector_index | News.embedding | 3072 | cosine | HNSW |
| qaexchange_vector_idx | QAExchange.embedding | 3072 | cosine | HNSW |

## Schema Quirks & Pitfalls

1. **String Booleans**: Fact.is_numeric uses '1'/'0' not true/false
2. **Comma-separated Strings**: 
   - Company.employees (e.g., "6,600")
   - QAExchange.responders (names as CSV)
3. **JSON Blobs**: Report.financial_statements (18KB-1.7MB strings)
4. **Missing CIKs**: ~3% of Reports lack cik property
5. **Optional Properties**: Report.items (present ~76%), periodOfReport (present ~97%)
6. **Non-reciprocal "bidirectional"**: RELATED_TO has bidirectional='true' but stored as single edge
7. **Date gaps**: Only 68% of Date nodes have current day trading properties
8. **Numeric Values as Strings**: Some return properties may contain 'NaN' string requiring conversion:
   ```cypher
   -- Pattern for handling string numeric values
   MATCH (n:News)-[r:INFLUENCES]->(c:Company)
   WHERE r.daily_stock IS NOT NULL 
     AND r.daily_stock <> 'NaN'  -- Check for 'NaN' string
   WITH toFloat(r.daily_stock) as daily_return
   WHERE NOT isNaN(daily_return)  -- Check for actual NaN after conversion
   RETURN daily_return
   ```
8. **Empty labels preserved**: AdminSection, FinancialStatement, Guidance, HyperCube, LineItems, Other, Memory (0 instances)

## Architectural Invariants

1. **Report NEVER influences Company** (0 instances)
2. **HAS_PRICE relationships ONLY originate from Date nodes**
3. **BELONGS_TO is strictly hierarchical**: Company→Industry→Sector→MarketIndex (no reverse)
4. **Most Facts have HAS_CONCEPT and HAS_PERIOD** (but 1698-1699 violations exist)
5. **XBRL nodes (XBRLNode) exist ONLY for Report.formType IN ['10-K', '10-Q', '10-K/A', '10-Q/A']**
6. **PRESENTATION_EDGE only originates from Abstract nodes**
7. **CALCULATION_EDGE only connects Fact→Fact**
9. **Every Company has exactly one BELONGS_TO→Industry relationship**
10. **No multi-label nodes exist** (all nodes have exactly one label)
11. **No self-relationships in RELATED_TO**

## Comprehensive XBRL Data Model

### Alternative XBRL Navigation Paths

**Path 1 - Via Report (COMPLETE - gets ALL facts):**
```
Company ← PRIMARY_FILER ← Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact
```

**Path 2 - Direct via Context (FASTER but misses 0.13% of facts):**
```
Company ← FOR_COMPANY ← Context ← IN_CONTEXT ← Fact
```

**⚠️ CRITICAL WARNING: Facts Without Context**
- 10,745 Facts (0.13%) do NOT have IN_CONTEXT relationships
- These Facts have context_id property but no Context node connection
- Path 2 will miss these Facts entirely
- For complete coverage, use Path 1 or handle missing Context:

```cypher
-- Complete pattern handling Facts without Context
MATCH (comp:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.is_numeric = '1'
OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context)
RETURN f.value, f.qname, ctx.context_id
```

### XBRL Coverage & Processing

**Coverage by Form Type:**
- **10-K**: 5,981 reports with XBRL (annual reports)
- **10-Q**: 126 reports with XBRL (quarterly reports)  
- **10-K/A**: 107 reports with XBRL (amended annual)
- **10-Q/A**: 26 reports with XBRL (amended quarterly)
- **8-K**: 0 reports with XBRL (NEVER has XBRL - use ExtractedSectionContent instead)
- **Other types**: 0 reports with XBRL

**Processing Status Values (Report.xbrl_status):**
- **SKIPPED** (23,300): Reports that cannot have XBRL (8-K, 425, etc.)
- **COMPLETED** (6,560): Successfully processed XBRL data
- **REFERENCE_ONLY** (913): Referenced but not processed
- **QUEUED** (738): Awaiting processing
- **PROCESSING** (98): Currently being processed
- **FAILED** (1): Processing failed
- **NULL** (8): Not yet categorized

### XBRL Node Properties (All Verified)

**XBRLNode:** id, displayLabel, cik, report_id, accessionNo, primaryDocumentUrl
**Fact:** id, context_id, u_id, qname, is_nil, fact_id, decimals, period_ref, is_numeric, unit_ref, value, concept_ref
**Concept:** id, u_id, qname, label, namespace, category, type_local, balance, period_type, concept_type
**Abstract:** id, u_id, qname, label, namespace, category, type_local, balance, period_type, concept_type
**Period:** id, u_id, period_type, start_date, end_date (both present even for 'instant')
**Unit:** id, u_id, unit_reference, name, status ('REC' or 'null' string), is_simple_unit ('0'/'1'/'null' strings), is_divide, item_type, namespace, registry_id
**Context:** id, u_id, context_id, cik, period_u_id, member_u_ids, dimension_u_ids
**Dimension:** id, u_id, qname, name, label, is_explicit ('0'/'1'), is_typed ('0'/'1'), network_uri
**Domain:** id, u_id, qname, label, level, parent_qname
**Member:** id, u_id, qname, label, level, parent_qname

### XBRL Relationship Properties

**REPORTS:** report_id, company_cik
**HAS_CONCEPT:** key
**HAS_PERIOD:** key
**HAS_UNIT:** key
**CALCULATION_EDGE:** cik, report_id, network_name, parent_id, child_id, network_uri, context_id, weight, company_cik, report_instance, order (ALL mandatory)
**PRESENTATION_EDGE:** cik, report_id, network_name, parent_id, child_id, parent_level, child_level, network_uri, company_cik, parent_order, child_order (ALL mandatory)
**IN_CONTEXT:** (no properties)
**FACT_DIMENSION:** (no properties)
**FACT_MEMBER:** (no properties)
**HAS_DOMAIN:** (no properties)
**HAS_MEMBER:** (no properties)
**PARENT_OF:** (no properties)

### Most Common XBRL Concepts

**Revenue Concepts:**
- us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax (234,675 facts)
- us-gaap:Revenues (92,745 facts)
- us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax (28,677 facts)
- us-gaap:CostOfRevenue (10,273 facts)

**Income/Earnings Concepts:**
- us-gaap:OperatingIncomeLoss (48,342 facts)
- us-gaap:NetIncomeLoss (47,728 facts)
- us-gaap:EarningsPerShareDiluted (23,840 facts)
- us-gaap:EarningsPerShareBasic (23,721 facts)
- us-gaap:IncomeTaxExpenseBenefit (30,246 facts)

**Balance Sheet Concepts:**
- us-gaap:StockholdersEquity (95,162 facts)
- us-gaap:Assets (35,899 facts)
- us-gaap:Liabilities (14,660 facts)
- us-gaap:CashAndCashEquivalentsAtCarryingValue (20,698 facts)

**Cash Flow Concepts:**
- us-gaap:NetCashProvidedByUsedInOperatingActivities (16,360 facts)
- us-gaap:NetCashProvidedByUsedInFinancingActivities (16,337 facts)
- us-gaap:NetCashProvidedByUsedInInvestingActivities (16,062 facts)

### Critical XBRL Schema Rules (MUST FOLLOW)

1. **NO Direct Fact-Report Relationship** - Facts connect to Reports ONLY through XBRLNode
2. **Correct Traversal Path**: Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact  
3. **Boolean Values**: `is_numeric` and `is_nil` use string values '1' or '0', NOT boolean true/false
4. **PRESENTATION_EDGE**: Only originates from Abstract nodes (never from Facts)
5. **All Properties Optional**: Most properties can be NULL - use IS NOT NULL checks where needed

### XBRL Data Type Quirks

1. **String Booleans**: is_numeric='1'/'0', is_nil='1'/'0', is_explicit='0'/'1', is_typed='0'/'1'
2. **Unit.status**: Uses literal string 'null' (not NULL)
3. **Unit.is_simple_unit**: Values are '0', '1', or literal string 'null'
4. **Period.period_type='instant'**: Still has BOTH start_date and end_date
5. **Fact traversal path**: Report→HAS_XBRL→XBRLNode←REPORTS←Fact (no direct Report-Fact link)
6. **Decimals values**: Can be numeric strings ('2', '4') or 'INF' for infinite precision
7. **Namespace patterns**: us-gaap uses yearly versions (e.g., "http://fasb.org/us-gaap/2023")
8. **Custom metrics**: Company-specific concepts have namespace like "http://www.companyname.com/20231231"

## Comprehensive XBRL Query Patterns

### 1. Basic XBRL Navigation

**Get XBRL Nodes**
Natural Language: "what financial data is available", "show me financial filings", "list available reports"
```cypher
MATCH (x:XBRLNode)
RETURN x.id, x.cik, x.accessionNo, x.report_id, x.displayLabel, x.primaryDocumentUrl
LIMIT 10
```

**Find Reports with XBRL**
Natural Language: "show me 10-K reports", "find annual reports", "get quarterly filings"
```cypher
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)
WHERE r.formType IN ['10-K', '10-Q', '10-K/A', '10-Q/A']
RETURN r.formType, r.cik, r.created, x.displayLabel
ORDER BY r.created DESC
```

**Company XBRL Documents**
Natural Language: "show apple's 10-K", "get AAPL structured data", "microsoft XBRL documents"
```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)
RETURN c.ticker, r.formType, r.created, x.displayLabel
ORDER BY r.created DESC
```

### 2. Revenue and Financial Metrics

**Get Revenue Data**
Natural Language: "what's the revenue", "annual revenue", "quarterly revenue", "total sales"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax' 
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as revenue, r.formType, r.created
ORDER BY r.created DESC
```

**Get Net Income**
Natural Language: "profit", "net income", "earnings", "bottom line"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname = 'us-gaap:NetIncomeLoss' 
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as net_income, r.formType, r.created
```

**Get EPS**
Natural Language: "earnings per share", "EPS", "per share profit"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:EarningsPerShareBasic', 'us-gaap:EarningsPerShareDiluted']
  AND f.is_numeric = '1'
RETURN c.ticker, f.qname, f.value as eps, r.formType, r.created
```

### 3. Balance Sheet Items

**Get Assets**
Natural Language: "total assets", "what do they own", "asset value", "company assets"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:Assets'
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as total_assets, r.formType, r.created
```

**Get Liabilities**
Natural Language: "total debt", "liabilities", "obligations", "what they owe"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:Liabilities'
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as total_liabilities, r.formType, r.created
```

### 4. Complete Fact with All Relationships

**Get Complete Revenue Fact Details**
Natural Language: "detailed revenue breakdown", "complete revenue data"
```cypher
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(c:Concept)
WHERE c.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax' 
  AND f.is_numeric = '1'
WITH r, x, f, c LIMIT 5
MATCH (f)-[:HAS_PERIOD]->(p:Period)
MATCH (f)-[:HAS_UNIT]->(u:Unit)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(comp:Company)
OPTIONAL MATCH (f)-[:FACT_MEMBER]->(m:Member)
RETURN comp.ticker, r.formType, f.value as revenue, c.label,
       p.period_type, p.start_date, p.end_date, u.name as unit,
       COLLECT(m.label) as dimensions
```

### 5. Time-Based Queries

**Get Quarterly Data**
Natural Language: "quarterly results", "Q1 revenue", "three month data"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE r.formType = '10-Q' 
  AND f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
  AND duration.between(date(p.start_date), date(p.end_date)).months <= 3
RETURN c.ticker, f.value as quarterly_revenue, p.start_date, p.end_date
```

**Year-over-Year Comparison**
Natural Language: "compare to last year", "YoY", "annual growth"
```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:NetIncomeLoss' 
  AND f.is_numeric = '1'
  AND r.formType = '10-K'
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
RETURN c.ticker, f.value as net_income, p.start_date, p.end_date
ORDER BY p.end_date DESC
LIMIT 5
```

### 6. Period-Specific Queries

**Balance Sheet at Date (Instant)**
Natural Language: "assets at year end", "balance sheet snapshot", "point in time values"
```cypher
MATCH (f:Fact)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'instant'
  AND f.is_numeric = '1'
  AND f.qname IN ['us-gaap:Assets', 'us-gaap:Liabilities', 'us-gaap:StockholdersEquity']
  AND p.start_date >= '2024-01-01'
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, f.qname, f.value, p.start_date as balance_date
```

**Income Statement Period (Duration)**
Natural Language: "revenue for the quarter", "period results", "quarterly performance"
```cypher
MATCH (f:Fact)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
  AND f.is_numeric = '1'
  AND f.qname IN ['us-gaap:Revenues', 'us-gaap:NetIncomeLoss', 'us-gaap:OperatingIncomeLoss']
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, f.qname, f.value, p.start_date, p.end_date,
       duration.between(date(p.start_date), date(p.end_date)).days as period_days
```

### 7. TextBlock and Narrative Facts

**Get Accounting Policies**
Natural Language: "accounting policies", "revenue recognition", "accounting methods"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE r.formType = '10-K'
  AND f.qname CONTAINS 'AccountingPolicies'
  AND f.is_numeric = '0'
RETURN c.ticker, f.qname, substring(f.value, 0, 200) as policy_excerpt
```

### 8. Dimensional Analysis

**Revenue by Segment**
Natural Language: "revenue by segment", "segment performance", "business unit revenue"
```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE f.qname CONTAINS 'Revenue'
  AND f.is_numeric = '1'
  AND m.qname CONTAINS 'Segment'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, f.value as revenue, m.label as segment
```

**Geographic Breakdown**
Natural Language: "revenue by country", "geographic breakdown", "international sales"
```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE (m.qname CONTAINS 'Geographic' OR m.qname CONTAINS 'Country')
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, c.qname, f.value, m.label as geography
```

### 9. Calculation Trees

**Net Income Calculation**
Natural Language: "how is profit calculated", "what makes up net income"
```cypher
MATCH (parent:Fact)-[calc:CALCULATION_EDGE]->(child:Fact)
WHERE parent.qname = 'us-gaap:NetIncomeLoss'
MATCH (parent)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, parent.qname as parent_concept, calc.weight as weight, 
       child.qname as child_concept, calc.order
ORDER BY calc.order
```

### 10. Presentation Structure

**Financial Statement Structure**
Natural Language: "income statement structure", "balance sheet layout"
```cypher
MATCH (a:Abstract)-[p:PRESENTATION_EDGE]->(child)
WHERE a.qname CONTAINS 'IncomeStatement' OR a.qname CONTAINS 'BalanceSheet'
RETURN a.label as section, labels(child)[0] as child_type,
       CASE WHEN 'Fact' IN labels(child) THEN child.qname 
            ELSE child.label END as child_item,
       p.child_order
ORDER BY p.parent_order, p.child_order
```

### 11. Fulltext Search Patterns

**Search Concepts**
```cypher
CALL db.index.fulltext.queryNodes('concept_ft', 'revenue') 
YIELD node, score
WHERE node.namespace CONTAINS 'us-gaap'
RETURN node.qname, node.label, node.period_type, score
ORDER BY score DESC
```

**Search Abstract Sections**
```cypher
CALL db.index.fulltext.queryNodes('abstract_ft', 'balance sheet') 
YIELD node, score
RETURN node.qname, node.label, score
ORDER BY score DESC
```

### 12. Context and Company

**Company-Specific Facts**
Natural Language: "apple financial data", "all data for AAPL"
```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(comp:Company {ticker: 'AAPL'})
WITH ctx, comp LIMIT 100
MATCH (f:Fact)-[:IN_CONTEXT]->(ctx)
WHERE f.is_numeric = '1'
WITH f, comp
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
RETURN comp.ticker, c.qname, f.value, c.label
```

**Multi-Company Comparison**
Natural Language: "compare apple and microsoft", "peer comparison"
```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE c.ticker IN ['AAPL', 'MSFT', 'GOOGL']
  AND f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
  AND r.formType = '10-K'
WITH c, f, r ORDER BY r.created DESC
WITH c, COLLECT({value: f.value, date: r.created})[0] as latest
RETURN c.ticker, latest.value as revenue, latest.date as report_date
```

### 13. Special Fact Patterns

**Nil/Null Facts**
Natural Language: "missing values", "what's not reported"
```cypher
MATCH (f:Fact)
WHERE f.is_nil = '1'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
WITH c.qname as concept, COUNT(f) as nil_count
ORDER BY nil_count DESC
RETURN concept, nil_count
```

**High Precision Facts**
Natural Language: "precise numbers", "exact values"
```cypher
MATCH (f:Fact)
WHERE f.is_numeric = '1' 
  AND f.decimals IN ['4', '5', '6', 'INF']
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, c.qname, f.value, f.decimals
```

**Custom Company Metrics**
Natural Language: "custom metrics", "non-GAAP", "adjusted earnings"
```cypher
MATCH (f:Fact)-[:HAS_CONCEPT]->(c:Concept)
WHERE NOT c.namespace CONTAINS 'fasb.org'
  AND c.namespace CONTAINS 'www.'
  AND f.is_numeric = '1'
WITH c.namespace as company_namespace, COUNT(DISTINCT c.qname) as custom_concepts
ORDER BY custom_concepts DESC
RETURN company_namespace, custom_concepts
```

### 14. Unit Information

**Facts by Unit Type**
Natural Language: "values in dollars", "data in shares", "per share data"
```cypher
MATCH (u:Unit)<-[:HAS_UNIT]-(f:Fact)
WHERE f.is_numeric = '1'
WITH u.name as unit_type, COUNT(f) as fact_count
ORDER BY fact_count DESC
RETURN unit_type, fact_count
```

Common unit types:
- 'iso4217:USD' - US Dollars
- 'shares' - Number of shares
- 'pure' - Ratios and percentages
- 'iso4217:USD/shares' - Per share amounts

### XBRL Query Decision Tree

```
User Query Analysis:
├─ Contains "discuss/explain/analyze"? → Use ExtractedSectionContent
├─ Report type is 8-K? → Use ExtractedSectionContent (8-K NEVER has XBRL)
├─ Needs specific metric (revenue, EPS, assets)?
│  ├─ Report is 10-K/10-Q/10-K/A/10-Q/A? → Use XBRL patterns
│  └─ Other report type? → Use ExtractedSectionContent or financial_statements JSON
├─ Needs dimensional data (by segment/geography)?
│  └─ Use FACT_MEMBER patterns
├─ Needs calculation relationships?
│  └─ Use CALCULATION_EDGE patterns
└─ Needs presentation hierarchy?
   └─ Use PRESENTATION_EDGE patterns
```

## 📊 Enumerations and Common Values

### Report.formType Enumeration
```
8-K: 22,495 instances
10-Q: 5,383 instances  
10-K: 2,091 instances
425: 711 instances
8-K/A: 487 instances
SCHEDULE 13D/A: 253 instances
10-K/A: 107 instances (HAS XBRL)
10-Q/A: 30 instances (HAS XBRL)
6-K: 26 instances
SCHEDULE 13D: 23 instances
SC TO-I: 8 instances
SC 14D9: 4 instances
```

### Company.exchange Enumeration
```
NYS: 457 companies (New York Stock Exchange)
NAS: 335 companies (NASDAQ)
TSE: 3 companies (Toronto Stock Exchange)
BATS: 1 company (BATS Exchange)
```

### Dividend Properties
```
dividend_type:
- Regular: 4,247 instances
- Special: 24 instances

currency:
- USD: 4,267 instances
- CAD: 4 instances
```

### RELATED_TO.relationship_type
```
news_co_occurrence: 2,109 instances (only value)
```

## 📗 Natural Language to XBRL Concept Mapping

### Revenue Variations
- "revenue", "sales", "total revenue" → `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` (235,030 facts)
- "revenues", "net revenue" → `us-gaap:Revenues` (93,023 facts)
- "gross revenue" → `us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax` (28,677 facts)
- "cost of goods sold", "COGS", "cost of revenue" → `us-gaap:CostOfRevenue` (10,300 facts)

### Profitability
- "net income", "profit", "earnings", "bottom line" → `us-gaap:NetIncomeLoss` (47,777 facts)
- "operating income", "EBIT", "operating profit" → `us-gaap:OperatingIncomeLoss` (48,397 facts)
- "gross profit", "gross margin" → `us-gaap:GrossProfit` (18,647 facts)
- "income tax", "tax expense" → `us-gaap:IncomeTaxExpenseBenefit` (30,275 facts)

### Per Share
- "EPS", "earnings per share", "basic EPS" → `us-gaap:EarningsPerShareBasic` (23,742 facts)
- "diluted EPS", "diluted earnings" → `us-gaap:EarningsPerShareDiluted` (23,865 facts)

### Balance Sheet
- "total assets", "assets" → `us-gaap:Assets` (35,942 facts)
- "current assets" → `us-gaap:AssetsCurrent` (13,202 facts)
- "cash", "cash and equivalents" → `us-gaap:CashAndCashEquivalentsAtCarryingValue` (20,753 facts)
- "debt", "liabilities", "total liabilities" → `us-gaap:Liabilities` (14,678 facts)
- "equity", "shareholders equity", "book value" → `us-gaap:StockholdersEquity` (119,576 facts)

### Cash Flow
- "operating cash flow", "cash from operations" → `us-gaap:NetCashProvidedByUsedInOperatingActivities` (16,404 facts)
- "investing cash flow" → `us-gaap:NetCashProvidedByUsedInInvestingActivities` (16,099 facts)
- "financing cash flow" → `us-gaap:NetCashProvidedByUsedInFinancingActivities` (16,374 facts)

## 📈 Most Common XBRL Concepts

Top 25 most used us-gaap concepts in the database:

1. **RevenueFromContractWithCustomerExcludingAssessedTax**: 234,691 facts
2. **StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest**: 119,948 facts
3. **StockholdersEquity**: 119,520 facts
4. **Revenues**: 92,867 facts
5. **AllocatedShareBasedCompensationExpense**: 54,906 facts
6. **DefinedBenefitPlanFairValueOfPlanAssets**: 54,309 facts
7. **AvailableForSaleSecuritiesDebtSecurities**: 50,205 facts
8. **OperatingIncomeLoss**: 48,356 facts
9. **NetIncomeLoss**: 47,740 facts
10. **DebtInstrumentInterestRateStatedPercentage**: 43,114 facts
11. **DebtInstrumentCarryingAmount**: 42,305 facts
12. **AdjustmentsToAdditionalPaidInCapitalSharebasedCompensationRequisiteServicePeriodRecognitionValue**: 38,077 facts
13. **OtherComprehensiveIncomeLossNetOfTax**: 36,559 facts
14. **Assets**: 35,921 facts
15. **AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShareAmount**: 34,857 facts
16. **Goodwill**: 34,742 facts
17. **ProfitLoss**: 34,231 facts
18. **AssetsFairValueDisclosure**: 32,935 facts
19. **FiniteLivedIntangibleAssetsAccumulatedAmortization**: 30,717 facts
20. **IncomeTaxExpenseBenefit**: 30,258 facts
21. **LongTermDebt**: 29,957 facts
22. **ConcentrationRiskPercentage1**: 29,772 facts
23. **FiniteLivedIntangibleAssetsGross**: 29,423 facts
24. **CashAndCashEquivalentsFairValueDisclosure**: 29,388 facts
25. **PropertyPlantAndEquipmentGross**: 29,154 facts

## 🔍 Fulltext Search Examples

### Search with Typo Handling
```cypher
-- Fuzzy search handles typos (append ~ for fuzzy matching)
CALL db.index.fulltext.queryNodes('company_ft', 'microsft~') 
YIELD node, score
RETURN node.ticker, node.name, score
-- Returns: MSFT Microsoft Corporation

-- Search concepts with variations
CALL db.index.fulltext.queryNodes('concept_ft', 'depreciation~') 
YIELD node, score
WHERE node.namespace CONTAINS 'us-gaap'
RETURN node.qname, node.label, score
```

### Multi-word Search
```cypher
-- Search for phrases
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', '"risk factors"')
YIELD node, score
RETURN node.section_name, substring(node.content, 0, 200), score
LIMIT 10

-- Boolean search
CALL db.index.fulltext.queryNodes('news_ft', 'apple AND revenue')
YIELD node, score
RETURN node.title, node.created, score
```

## ⏰ Time-Based Query Patterns

### Market Session Queries
```cypher
-- Get pre-market events
MATCH (r:Report)
WHERE r.market_session = 'pre_market'
  AND r.created >= datetime() - duration('P30D')
RETURN r.formType, r.created, r.market_session
ORDER BY r.created DESC

-- Get events by session and calculate session returns
MATCH (c:Company {ticker: 'AAPL'})<-[pf:PRIMARY_FILER]-(r:Report)
WHERE r.market_session IS NOT NULL
RETURN r.market_session, AVG(pf.session_stock) as avg_session_return,
       COUNT(*) as event_count
```

### Trading Day Navigation
```cypher
-- Find next trading day after weekend/holiday
MATCH (d:Date {date: '2024-07-04'})  -- July 4th holiday
RETURN d.next_trading_date  -- Returns next trading day

-- Get all events in a trading window
MATCH (d:Date)-[:HAS_PRICE]->(c:Company {ticker: 'AAPL'})
WHERE d.date >= '2024-01-01' AND d.date <= '2024-01-31'
  AND d.is_trading_day = '1'  -- STRING comparison, not boolean!
RETURN d.date, d.market_open_current_day as open, 
       d.market_close_current_day as close
```

## 📅 Query Patterns for Latest Data

### Getting Most Recent Data
Natural language: "latest revenue", "current quarter", "most recent results"

**Method 1: By Report Date**
```cypher
-- Get latest by Report date
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->()
WHERE r.formType = '10-Q'
WITH r ORDER BY r.created DESC LIMIT 1
MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax' 
  AND f.is_numeric = '1'
RETURN f.value, r.created, r.periodOfReport
```

**Method 2: By Period End Date**
```cypher
-- Get latest by Period end date (via Context)
MATCH (c:Company {ticker: 'AAPL'})<-[:FOR_COMPANY]-(ctx:Context)<-[:IN_CONTEXT]-(f:Fact)
WHERE f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax' 
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
RETURN f.value, p.end_date
ORDER BY p.end_date DESC
LIMIT 1
```

## 📆 Time Period Natural Language Mapping

### Annual/Yearly
- "annual", "yearly", "full year", "FY" → formType = '10-K'
- Period duration ~365 days

### Quarterly
- "quarterly", "Q1", "Q2", "Q3", "Q4", "quarter" → formType = '10-Q'
- Period duration ~90 days

### Year-to-Date
- "YTD", "year to date", "cumulative" → Check period start = fiscal year start

### Trailing Twelve Months
- "TTM", "LTM", "trailing twelve months" → Sum of last 4 quarters (see aggregation pattern)

## 🎯 Dimensional Data Query Patterns

### ⚠️ CRITICAL: Understanding Revenue Dimensions
Each quarter has multiple revenue facts representing different dimensions:
- **Total Revenue**: No dimension members
- **Product Categories**: iPhone, Mac, iPad, WearablesHomeandAccessories
- **Geographic Segments**: AmericasSegment, EuropeSegment, GreaterChinaSegment, JapanSegment, RestOfAsiaPacificSegment
- **Type**: Product vs Service

### Revenue by Segment (CORRECTED)
```cypher
-- Note: Segments are company-specific, not us-gaap
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
  AND (m.label ENDS WITH 'Segment' OR m.label ENDS WITH 'SegmentMember')
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, f.value as revenue, m.label as segment, r.periodOfReport
ORDER BY r.created DESC
```

### Geographic Breakdown
```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE (m.qname CONTAINS 'Geographic' OR m.qname CONTAINS 'Country')
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, con.label, f.value, m.label as geography
```

### Multi-Dimensional Analysis
```cypher
-- Facts with multiple dimensions
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE f.is_numeric = '1'
WITH f, COLLECT(DISTINCT m) as members
WHERE SIZE(members) > 1
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
RETURN c.label, SIZE(members) as dimensions, 
       [m IN members | m.label] as dimension_labels
LIMIT 20
```

## 📐 Handling Amended Reports

Natural language: "restated", "amended", "corrected"

```cypher
-- Get amended reports
MATCH (r:Report)
WHERE r.formType ENDS WITH '/A'  -- 10-K/A, 10-Q/A, 8-K/A
  AND r.isAmendment = true
RETURN r.formType, r.created, r.periodOfReport
```

**Amended Report Counts:**
- 8-K/A: 487 instances
- SCHEDULE 13D/A: 253 instances
- 10-K/A: 107 instances (HAS XBRL)
- 10-Q/A: 30 instances (HAS XBRL)

## 🔢 Multi-Period Aggregation

### ⚠️ WARNING: Dimensional Complexity
Aggregating periods is complex due to dimensional data. Each period has:
- 1 total revenue fact
- Multiple segment facts (geographic, product, type)

**INCORRECT Pattern (sums all dimensions):**
```cypher
-- WRONG: This would sum all dimensional variants
MATCH (f:Fact)
WHERE f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
RETURN SUM(toFloat(replace(f.value, ',', '')))
```

**CORRECT Pattern (aggregates only totals):**
```cypher
-- Sum quarterly revenue to get annual (only non-dimensional facts)
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE r.formType = '10-Q' 
  AND f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
  AND NOT EXISTS((f)-[:FACT_MEMBER]->())  -- Only facts without dimensions
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.end_date >= '2024-01-01' AND p.end_date <= '2024-12-31'
  AND p.period_type = 'duration'
WITH f.value as revenue_str, p.end_date
RETURN SUM(toFloat(replace(revenue_str, ',', ''))) as annual_revenue,
       COUNT(DISTINCT p.end_date) as quarters_counted
```

## 🚨 Error Handling Guidance

### Common Query Errors and Solutions

1. **Boolean Type Mismatch**
```cypher
-- WRONG: Will cause type error
WHERE f.is_numeric = true

-- CORRECT: Use string values
WHERE f.is_numeric = '1'
```

2. **Missing XBRL Data**
```cypher
-- Always check if XBRL exists first
MATCH (r:Report {formType: '8-K'})
OPTIONAL MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)
WITH r, x
WHERE x IS NULL
-- Handle non-XBRL case
MATCH (r)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
RETURN esc.content
```

3. **Null Property Access**
```cypher
-- SAFE: Check for null before accessing
MATCH (r:Report)
WHERE r.xbrl_status IS NOT NULL 
  AND r.xbrl_status = 'COMPLETED'
RETURN r.id
```

4. **Missing Relationships**
```cypher
-- Use OPTIONAL MATCH for potentially missing relationships
MATCH (c:Company)
OPTIONAL MATCH (c)-[:RELATED_TO]->(other:Company)
RETURN c.ticker, COLLECT(other.ticker) as related
```

5. **Fact-Report Connection Error**
```cypher
-- WRONG: Direct Fact-Report relationship doesn't exist
MATCH (r:Report)-[:HAS_FACT]->(f:Fact)  -- ERROR!

-- CORRECT: Must go through XBRLNode
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
```

6. **Context Missing Error**
```cypher
-- WRONG: Assumes all Facts have Context
MATCH (f:Fact)-[:IN_CONTEXT]->(ctx:Context)  -- Misses 10,745 facts!

-- CORRECT: Use OPTIONAL for Context
MATCH (f:Fact)
OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context)
```

## 📊 Report XBRL Coverage (CRITICAL)

### Reports WITH XBRL (can use Fact patterns):
- **10-K**: 2,028 out of 2,091 have XBRL (97%)
- **10-Q**: 4,506 out of 5,383 have XBRL (84%)
- **10-K/A**: 107 out of 107 have XBRL (100%)
- **10-Q/A**: 26 out of 30 have XBRL (87%)

### Reports WITHOUT XBRL (must use ExtractedSectionContent):
- **8-K**: 0 out of 22,495 have XBRL (0% - NEVER has XBRL!)
- **425**: 0 out of 711 have XBRL
- **8-K/A**: 0 out of 487 have XBRL
- **6-K**: 0 out of 26 have XBRL
- **SCHEDULE 13D**: 0 out of 23 have XBRL

**⚠️ KEY POINT**: If user asks about "merger", "acquisition", "CEO departure" → likely 8-K → NO XBRL!

## ⚡ Query Performance Tips

### 1. Use Indexes First
```cypher
-- FAST: Start with indexed lookup
MATCH (c:Company {ticker: 'AAPL'})
MATCH (c)<-[:PRIMARY_FILER]-(r:Report)

-- SLOW: Filter after traversal
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
WHERE c.ticker = 'AAPL'
```

### 2. Limit Early in Chains
```cypher
-- EFFICIENT: Limit before expensive traversals
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)
WITH r, x LIMIT 100
MATCH (x)<-[:REPORTS]-(f:Fact)
RETURN COUNT(f)

-- INEFFICIENT: Limit after traversal
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
RETURN COUNT(f)
LIMIT 100
```

### 3. Use Date Filters
```cypher
-- Add date constraints to reduce scope
MATCH (r:Report)
WHERE r.created >= datetime() - duration('P90D')  -- Last 90 days
  AND r.formType = '10-K'
RETURN r.id
```

### 4. Profile Queries
```cypher
-- Use PROFILE to analyze performance
PROFILE
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)
RETURN COUNT(r)
```

## 🔮 Vector Similarity Search

### Finding Similar News
```cypher
-- Find news similar to a specific article
MATCH (n:News {id: 'news_123'})
CALL db.index.vector.queryNodes('news_vector_index', 10, n.embedding)
YIELD node, score
WHERE node.id <> n.id  -- Exclude the source article
RETURN node.title, node.created, score
ORDER BY score DESC
```

### Finding Similar Q&A Exchanges
```cypher
-- Find similar questions across earnings calls
MATCH (qa:QAExchange)
WHERE qa.questioner CONTAINS 'analyst'
  AND qa.embedding IS NOT NULL
WITH qa.embedding[0..10] as sample_embedding  -- Use first 10 dims as example
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, qa.embedding)
YIELD node, score
RETURN node.questioner, node.exchanges, score
```

### Cross-Entity Similarity
```cypher
-- Find news related to specific Q&A topics
MATCH (qa:QAExchange {id: 'qa_456'})
WHERE qa.embedding IS NOT NULL
WITH qa.embedding as qa_vector
MATCH (n:News)
WHERE n.embedding IS NOT NULL
WITH n, gds.similarity.cosine(qa_vector, n.embedding) as similarity
WHERE similarity > 0.8
RETURN n.title, n.created, similarity
ORDER BY similarity DESC
LIMIT 10
```

## ⚠️ Known Anomalies

### INFLUENCES Anomaly
**Issue**: 1,730 News→Company INFLUENCES relationships incorrectly have industry return properties.
```cypher
-- These should not exist but do in the current data
-- News→Company should only have stock returns
-- Industry returns should only be on News→Industry relationships
```

### RELATED_TO Single Direction
**Issue**: Despite bidirectional=true, relationships exist in only one direction.
```cypher
-- Current state (single edge)
(:Company {ticker: 'AAPL'})-[:RELATED_TO]->(:Company {ticker: 'MSFT'})

-- Not stored as reciprocal pair
-- No automatic reverse edge from MSFT to AAPL
```

## Schema Evolution Notes

- **Empty labels preserved**: 6 node types with 0 instances (likely for future use)
- **Memory node**: Has fulltext index but no data (MCP integration placeholder)
- **Date coverage**: 2023-01-01 to 2025-07-24 (936 dates)
- **Vector indexes**: Added for News and QAExchange embeddings (3072 dimensions)
- **XBRL Evolution**: 8.23M facts (up from 7.69M documented), supports 10-K/A and 10-Q/A