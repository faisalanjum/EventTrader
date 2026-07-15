# Non-XBRL Query Patterns for Neo4j EventMarketDB

This comprehensive guide covers ALL non-XBRL queries including all content node types, with **FULLTEXT SEARCH** optimized for large text fields.

**Generated**: January 2025  
**Updated**: With fulltext search patterns (10-100x faster)
**Content Types Covered**: ExtractedSectionContent (54 types), FinancialStatementContent (4 types), ExhibitContent, FilingTextContent

## 🎯 Key Changes with Fulltext Indexes

1. **Speed**: 10-100x faster than CONTAINS for text search
2. **Relevance**: Automatic scoring and ranking
3. **Features**: Phrase search, fuzzy matching, boolean logic
4. **Syntax**: Lucene query syntax for advanced searches
5. **Prerequisites**: All fulltext indexes must be created (see end of document)

### When to Use Each Search Method

| Use Case | Approach | Example |
|----------|----------|----------|
| **Searching content** | Fulltext | Finding "revenue growth" in any section |
| **Known section browsing** | Direct match | Getting all Risk Factors sections |
| **Topic discovery** | Fulltext | Finding cyber discussions across all content |
| **Specific 8-K events** | Direct match | Getting all executive departure announcements |
| **Complex text patterns** | CONTAINS | Regex for dollar amounts |
| **Semantic similarity** | Vector search | Finding similar news or Q&A discussions |
| **Topic clustering** | Vector search | Grouping related analyst questions |

**Rule of thumb**: 
- Use fulltext when searching for specific terms/phrases
- Use direct match when filtering by metadata
- Use vector search when finding semantically similar content

## 🔍 Fulltext Search Strategies (10-100x Faster)

### Strategy 1: Basic Fulltext Search (Recommended - Fastest)
```cypher
// Simple fulltext search with relevance scoring
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'cybersecurity') 
YIELD node, score
WHERE node.section_name = 'RiskFactors'
RETURN node.filing_id, substring(node.content, 0, 1000) as excerpt, score
ORDER BY score DESC
LIMIT 20
```

### Strategy 2: Phrase Search with Context
```cypher
// Exact phrase search with surrounding context (without APOC)
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', '"revenue growth"') 
YIELD node, score
WITH node, score, toLower(node.content) as lower_content
WITH node, score,
     CASE 
       WHEN lower_content CONTAINS 'revenue growth' 
       THEN size(split(substring(lower_content, 0, size(lower_content)), 'revenue growth')[0])
       ELSE -1 
     END as position
WHERE position > -1
RETURN node.filing_id,
       substring(node.content, 
                 CASE WHEN position < 200 THEN 0 ELSE position - 200 END,
                 400) as context_excerpt,
       score
ORDER BY score DESC
LIMIT 20
```

### Strategy 3: Boolean Multi-Term Search
```cypher
// AND/OR/NOT boolean search
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 
    'revenue AND (growth OR increase) NOT decline') 
YIELD node, score
WHERE node.section_name = 'ManagementDiscussionandAnalysis'
RETURN node.filing_id, substring(node.content, 0, 1000) as excerpt, score
ORDER BY score DESC
LIMIT 20
```

### Strategy 4: Fuzzy Search for Variations
```cypher
// Fuzzy search handles typos and variations
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'acquisiton~') 
YIELD node, score
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, node.section_name,
       substring(node.content, 0, 500) as excerpt, score
ORDER BY score DESC
LIMIT 20
```

### Strategy 5: Fallback to CONTAINS
```cypher
// Use CONTAINS only for: regex patterns, complex wildcards, or when fulltext fails
MATCH (esc:ExtractedSectionContent)
WHERE esc.content =~ '.*\$[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})?.*'  -- Regex for dollar amounts
RETURN esc.filing_id, substring(esc.content, 0, 500)
LIMIT 10
```

---

## 📑 ExtractedSectionContent Patterns (All 54 Types)

### 1. Financial Statements & Exhibits

#### Financial Statements (10-K/10-Q)
**Natural Language**: financial statements text | balance sheet narrative | income statement discussion | cash flow text | financial tables

```cypher
-- Direct match when you know exact section name (fastest for browsing)
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name IN ['FinancialStatements', 'FinancialStatementsandSupplementaryData']
RETURN c.ticker, r.formType, 
       substring(esc.content, 0, 2000) as financial_text,
       size(esc.content) as content_size
ORDER BY r.created DESC
LIMIT 10
```

```cypher
-- Fulltext search when looking for specific content within financial statements
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'cash flow operating activities')
YIELD node, score
WHERE node.section_name IN ['FinancialStatements', 'FinancialStatementsandSupplementaryData']
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, substring(node.content, 0, 2000) as financial_text, score
ORDER BY score DESC
LIMIT 10
```

#### Financial Statements and Exhibits (8-K)
**Natural Language**: 8-K exhibits | 8-K attachments | earnings release | presentation materials

```cypher
-- Direct match for 8-K exhibits section (fastest for browsing)
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'FinancialStatementsandExhibits'
RETURN c.ticker, substring(esc.content, 0, 1000) as exhibit_info, r.created
ORDER BY r.created DESC
LIMIT 20
```

### 2. Management Discussion & Analysis

#### MD&A Section
**Natural Language**: management discussion | MD&A | performance analysis | management commentary | explain results

```cypher
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'revenue') 
YIELD node, score
WHERE node.section_name IN ['ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations',
                            'Management'sDiscussionandAnalysisofFinancialConditionandResultsofOperations']
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, substring(node.content, 0, 2000) as mda_text, score
ORDER BY score DESC
LIMIT 10
```

### 3. Risk Disclosures

#### Risk Factors
**Natural Language**: risk factors | business risks | operational risks | financial risks | risk disclosures

```cypher
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 
    'cyber OR security OR breach') 
YIELD node, score
WHERE node.section_name = 'RiskFactors'
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, 
       substring(node.content, 0, 1500) as risk_excerpt,
       score
ORDER BY score DESC
LIMIT 20
```

#### Cybersecurity Disclosures
**Natural Language**: cybersecurity risks | data breach | cyber incidents | security measures | cyber disclosure

```cypher
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'cyber') 
YIELD node, score
WHERE node.section_name = 'Cybersecurity' 
   OR node.section_name = 'RiskFactors'
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, node.section_name,
       substring(node.content, 0, 1500) as cyber_disclosure,
       score
ORDER BY score DESC
LIMIT 20
```

### 4. 8-K Event Sections

**Note**: 8-K sections have specific standardized names. Direct matching is optimal when you know the exact event type. Use fulltext when searching for topics within these sections.

#### Results of Operations (8-K Item 2.02)
**Natural Language**: 8-K earnings announcement | quarterly results announcement | earnings release | financial results 8-K

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'ResultsofOperationsandFinancialCondition'
RETURN c.ticker, r.created, 
       substring(esc.content, 0, 2000) as earnings_announcement
ORDER BY r.created DESC
LIMIT 20
```

#### Executive Changes (8-K Item 5.02)
**Natural Language**: executive departure | CEO resignation | CFO appointment | management changes | officer changes | director election

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as executive_change
ORDER BY r.created DESC
LIMIT 20
```

#### Regulation FD Disclosure (8-K Item 7.01)
**Natural Language**: regulation FD | investor presentation | conference presentation | investor day | analyst meeting

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'RegulationFDDisclosure'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as fd_disclosure
ORDER BY r.created DESC
LIMIT 20
```

#### Material Agreements (8-K Item 1.01)
**Natural Language**: material agreement | new contract | business agreement | partnership agreement | definitive agreement

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'EntryintoaMaterialDefinitiveAgreement'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as agreement_details
ORDER BY r.created DESC
LIMIT 20
```

#### Other Events (8-K Item 8.01)
**Natural Language**: other events | other material events | additional disclosure | miscellaneous 8-K

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'OtherEvents'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as other_event
ORDER BY r.created DESC
LIMIT 20
```

### 5. Corporate Governance Sections

#### Executive Compensation
**Natural Language**: executive compensation | CEO pay | management compensation | officer salaries | equity awards

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'ExecutiveCompensation'
RETURN c.ticker, r.formType,
       substring(esc.content, 0, 2000) as compensation_info
ORDER BY r.created DESC
LIMIT 10
```

#### Directors and Officers
**Natural Language**: board of directors | executive officers | corporate governance | board members | management team

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'Directors,ExecutiveOfficersandCorporateGovernance'
RETURN c.ticker, r.formType,
       substring(esc.content, 0, 1500) as governance_info
ORDER BY r.created DESC
LIMIT 10
```

### 6. Business Operations Sections

#### Business Description
**Natural Language**: business overview | company description | what does company do | business model | operations overview

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'Business'
RETURN c.ticker, substring(esc.content, 0, 3000) as business_description
ORDER BY r.created DESC
LIMIT 10
```

#### Properties
**Natural Language**: company properties | facilities | real estate | locations | manufacturing plants

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'Properties'
RETURN c.ticker, r.formType,
       substring(esc.content, 0, 1500) as properties_info
ORDER BY r.created DESC
LIMIT 10
```

### 7. Additional 8-K Event Types

#### Shareholder Voting Results (8-K Item 5.07)
**Natural Language**: shareholder vote | annual meeting results | proxy voting | stockholder meeting | voting results

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'SubmissionofMatterstoaVoteofSecurityHolders'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as voting_results
ORDER BY r.created DESC
LIMIT 20
```

#### Debt/Financial Obligations (8-K Item 2.03)
**Natural Language**: new debt | loan agreement | credit facility | financial obligation | debt issuance

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as debt_details
ORDER BY r.created DESC
LIMIT 20
```

#### Bankruptcy/Receivership (8-K Item 1.03)
**Natural Language**: bankruptcy filing | chapter 11 | receivership | insolvency | bankruptcy proceedings

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'BankruptcyorReceivership'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 2000) as bankruptcy_info
ORDER BY r.created DESC
LIMIT 20
```

#### Material Impairments (8-K Item 2.06)
**Natural Language**: impairment charge | goodwill impairment | asset writedown | material impairment

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'MaterialImpairments'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as impairment_details
ORDER BY r.created DESC
LIMIT 20
```

#### Acquisitions/Dispositions (8-K Item 2.01)
**Natural Language**: acquisition completed | asset sale | business combination | divestiture | merger completion

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'CompletionofAcquisitionorDispositionofAssets'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 2000) as transaction_details
ORDER BY r.created DESC
LIMIT 20
```

#### Delisting Notices (8-K Item 3.01)
**Natural Language**: delisting | nasdaq deficiency | nyse warning | listing standards | delisting notice

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '8-K'})-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing'
RETURN c.ticker, r.created,
       substring(esc.content, 0, 1500) as delisting_notice
ORDER BY r.created DESC
LIMIT 20
```

### 8. Legal & Compliance Sections

#### Legal Proceedings
**Natural Language**: lawsuits | litigation | legal matters | court cases | legal proceedings

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'LegalProceedings'
RETURN c.ticker, r.formType,
       substring(esc.content, 0, 2000) as legal_matters
ORDER BY r.created DESC
LIMIT 20
```

#### Controls and Procedures
**Natural Language**: internal controls | sox compliance | control procedures | audit controls | financial controls

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
WHERE esc.section_name = 'ControlsandProcedures'
RETURN c.ticker, r.formType,
       substring(esc.content, 0, 1500) as controls_info
ORDER BY r.created DESC
LIMIT 10
```

---

## 💼 FinancialStatementContent Patterns (JSON Structure)

### Balance Sheets
**Natural Language**: balance sheet data | assets liabilities equity | financial position | balance sheet json

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FINANCIAL_STATEMENT]->(fsc:FinancialStatementContent)
WHERE fsc.statement_type = 'BalanceSheets'
RETURN c.ticker, r.formType, 
       substring(fsc.value, 0, 1000) as balance_sheet_json,
       size(fsc.value) as json_size
ORDER BY r.created DESC
LIMIT 10
```

### Income Statements
**Natural Language**: income statement data | profit loss statement | earnings statement | income statement json

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FINANCIAL_STATEMENT]->(fsc:FinancialStatementContent)
WHERE fsc.statement_type = 'StatementsOfIncome'
RETURN c.ticker, r.formType,
       substring(fsc.value, 0, 1000) as income_statement_json,
       size(fsc.value) as json_size
ORDER BY r.created DESC
LIMIT 10
```

### Cash Flow Statements
**Natural Language**: cash flow data | cash flow statement | operating investing financing | cash flow json

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FINANCIAL_STATEMENT]->(fsc:FinancialStatementContent)
WHERE fsc.statement_type = 'StatementsOfCashFlows'
RETURN c.ticker, r.formType,
       substring(fsc.value, 0, 1000) as cash_flow_json,
       size(fsc.value) as json_size
ORDER BY r.created DESC
LIMIT 10
```

### Shareholders Equity Statements
**Natural Language**: equity statement | shareholders equity changes | equity reconciliation | equity statement json

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FINANCIAL_STATEMENT]->(fsc:FinancialStatementContent)
WHERE fsc.statement_type = 'StatementsOfShareholdersEquity'
RETURN c.ticker, r.formType,
       substring(fsc.value, 0, 1000) as equity_statement_json,
       size(fsc.value) as json_size
ORDER BY r.created DESC
LIMIT 10
```

---

## 📎 ExhibitContent Patterns

### Press Releases (EX-99.1)
**Natural Language**: press release | earnings press release | announcement | news release | exhibit 99.1

```cypher
// For specific exhibit lookup, direct match is still fastest
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_EXHIBIT]->(ec:ExhibitContent)
WHERE ec.exhibit_number = 'EX-99.1'
RETURN c.ticker, r.formType,
       substring(ec.content, 0, 2000) as press_release,
       r.created
ORDER BY r.created DESC
LIMIT 20
```

### Material Contracts (EX-10.x)
**Natural Language**: material contract | employment agreement | loan agreement | purchase agreement | exhibit 10

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_EXHIBIT]->(ec:ExhibitContent)
WHERE ec.exhibit_number STARTS WITH 'EX-10.'
RETURN c.ticker, r.formType, ec.exhibit_number,
       substring(ec.content, 0, 1500) as contract_excerpt,
       r.created
ORDER BY r.created DESC
LIMIT 20
```

### Presentations (EX-99.2)
**Natural Language**: investor presentation | slide deck | conference presentation | exhibit 99.2

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_EXHIBIT]->(ec:ExhibitContent)
WHERE ec.exhibit_number = 'EX-99.2'
RETURN c.ticker, r.formType,
       substring(ec.content, 0, 1500) as presentation_content,
       r.created
ORDER BY r.created DESC
LIMIT 20
```

### Search Within Exhibits
**Natural Language**: search exhibits | find in attachments | exhibit search | attachment content

```cypher
CALL db.index.fulltext.queryNodes('exhibit_content_ft', 'compensation') 
YIELD node, score
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
RETURN c.ticker, r.formType, node.exhibit_number,
       substring(node.content, 0, 1000) as matching_excerpt,
       r.created, score
ORDER BY score DESC
LIMIT 20
```

---

## 📝 FilingTextContent Patterns

### Proxy Solicitations (425)
**Natural Language**: merger proxy | acquisition filing | proxy materials | deal announcement | 425 filing

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FILING_TEXT]->(ftc:FilingTextContent)
WHERE ftc.form_type = '425'
RETURN c.ticker, substring(ftc.content, 0, 2000) as proxy_text, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Schedule 13D/A (Ownership)
**Natural Language**: activist investor | 5% ownership | schedule 13D | beneficial ownership | shareholder activism

```cypher
MATCH (c:Company)<-[:REFERENCED_IN]-(r:Report)-[:HAS_FILING_TEXT]->(ftc:FilingTextContent)
WHERE ftc.form_type CONTAINS 'SCHEDULE 13D'
RETURN c.ticker, ftc.form_type,
       substring(ftc.content, 0, 1500) as ownership_disclosure,
       r.created
ORDER BY r.created DESC
LIMIT 20
```

### Foreign Private Issuer (6-K)
**Natural Language**: foreign issuer report | 6-K filing | international company report | foreign private issuer

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_FILING_TEXT]->(ftc:FilingTextContent)
WHERE ftc.form_type = '6-K'
RETURN c.ticker, substring(ftc.content, 0, 1500) as foreign_issuer_content, r.created
ORDER BY r.created DESC
LIMIT 20
```

---

## 🔄 Combined Search Patterns

### Search All Content Types for a Term
**Natural Language**: search everywhere | find anywhere | comprehensive search | search all documents

```cypher
// Unified search across all content types using UNION
WITH 'acquisition' as search_term
CALL {
    WITH search_term
    CALL db.index.fulltext.queryNodes('extracted_section_content_ft', search_term) 
    YIELD node, score
    RETURN node.filing_id as filing_id, 'Section' as type, 
           node.section_name as name, score
    UNION
    WITH search_term
    CALL db.index.fulltext.queryNodes('exhibit_content_ft', search_term) 
    YIELD node, score
    RETURN node.filing_id as filing_id, 'Exhibit' as type, 
           node.exhibit_number as name, score
    UNION
    WITH search_term
    CALL db.index.fulltext.queryNodes('filing_text_content_ft', search_term) 
    YIELD node, score
    RETURN node.filing_id as filing_id, 'Filing' as type, 
           node.form_type as name, score
}
WITH filing_id, COLLECT({type: type, name: name, score: score}) as found_in
MATCH (r:Report {id: filing_id})<-[:PRIMARY_FILER]-(c:Company)
WHERE r.created > datetime() - duration('P90D')
RETURN c.ticker, r.formType, r.created, found_in
ORDER BY r.created DESC
LIMIT 20
```

### Get All Available Content for a Report
**Natural Language**: all report content | complete filing | full document | everything in report

```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)
WHERE r.created > datetime() - duration('P30D')
OPTIONAL MATCH (r)-[:HAS_SECTION]->(esc:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(ec:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fsc:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ftc:FilingTextContent)
RETURN c.ticker, r.formType, r.created,
       COUNT(DISTINCT esc) as section_count,
       COUNT(DISTINCT ec) as exhibit_count,
       COUNT(DISTINCT fsc) as financial_statement_count,
       COUNT(DISTINCT ftc) as filing_text_count,
       COLLECT(DISTINCT esc.section_name)[0..5] as sample_sections,
       COLLECT(DISTINCT ec.exhibit_number)[0..5] as sample_exhibits
ORDER BY r.created DESC
LIMIT 10
```

---

## 📊 Special Query Patterns

### Ranked Search Results by Relevance
**Natural Language**: best matches | most relevant | ranked results | relevance search

```cypher
// Fulltext provides automatic relevance scoring
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', '"revenue growth"') 
YIELD node, score
MATCH (r:Report {id: node.filing_id})<-[:PRIMARY_FILER]-(c:Company)
WHERE r.formType IN ['10-K', '10-Q']
RETURN c.ticker, r.formType, node.section_name,
       score as relevance_score,
       substring(node.content, 0, 1000) as excerpt
ORDER BY score DESC
LIMIT 20
```

### Time-Bounded Searches
**Natural Language**: recent filings | last quarter | past month | latest reports | current year

```cypher
// Combine fulltext with time filters
WITH datetime() - duration('P90D') as start_date
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'guidance') 
YIELD node, score
MATCH (r:Report {id: node.filing_id})<-[:PRIMARY_FILER]-(c:Company)
WHERE r.created > start_date
RETURN c.ticker, r.formType, r.created,
       substring(node.content, 0, 1000) as guidance_excerpt,
       score
ORDER BY score DESC
LIMIT 20
```

### Industry-Specific Searches
**Natural Language**: technology companies | healthcare sector | financial services | industry comparison

```cypher
// Fulltext search filtered by industry
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'artificial intelligence') 
YIELD node, score
MATCH (r:Report {id: node.filing_id})<-[:PRIMARY_FILER]-(c:Company)
WHERE c.sector = 'Technology'
RETURN c.ticker, c.industry, r.formType,
       substring(node.content, 0, 1000) as ai_discussion,
       score
ORDER BY score DESC
LIMIT 20
```

---

## 📋 Complete Section Name Reference (54 Total Types)

### 10-K/10-Q Primary Sections
1. **FinancialStatements** - Financial statements and notes (5,327 instances)
2. **FinancialStatementsandSupplementaryData** - Comprehensive financials (2,106 instances)
3. **ManagementDiscussionandAnalysisofFinancialConditionandResultsofOperations** - MD&A (5,339 instances)
4. **Management'sDiscussionandAnalysisofFinancialConditionandResultsofOperations** - MD&A variant (2,089 instances)
5. **RiskFactors** - Risk disclosures (7,218 instances)
6. **Business** - Business overview (2,098 instances)
7. **Properties** - Property descriptions (2,046 instances)
8. **LegalProceedings** - Legal matters (7,260 instances)
9. **ExecutiveCompensation** - Executive pay (2,109 instances)
10. **Directors,ExecutiveOfficersandCorporateGovernance** - Governance (2,116 instances)
11. **ControlsandProcedures** - Internal controls (7,479 instances)
12. **Cybersecurity** - Cyber risk disclosures (1,318 instances)
13. **QuantitativeandQualitativeDisclosuresAboutMarketRisk** - Market risk (5,295 instances)
14. **QuantitativeandQualitativeDisclosuresaboutMarketRisk** - Market risk variant (2,080 instances)
15. **UnresolvedStaffComments** - SEC comments (2,075 instances)
16. **SelectedFinancialData(priortoFebruary2021)** - Historical data (1,999 instances)
17. **MarketforRegistrant'sCommonEquity,RelatedStockholderMattersandIssuerPurchasesofEquitySecurities** - Equity market (2,095 instances)
18. **ChangesinandDisagreementswithAccountantsonAccountingandFinancialDisclosure** - Accountant changes (2,078 instances)
19. **SecurityOwnershipofCertainBeneficialOwnersandManagementandRelatedStockholderMatters** - Ownership (2,110 instances)
20. **CertainRelationshipsandRelatedTransactions,andDirectorIndependence** - Related parties (2,108 instances)
21. **PrincipalAccountantFeesandServices** - Audit fees (2,111 instances)
22. **ExhibitsandFinancialStatementSchedules** - Combined exhibits section (2,192 instances)

### 8-K Event Sections
1. **FinancialStatementsandExhibits** - Item 9.01 (17,880 instances)
2. **ResultsofOperationsandFinancialCondition** - Item 2.02 (8,083 instances)
3. **RegulationFDDisclosure** - Item 7.01 (5,419 instances)
4. **DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers** - Item 5.02 (5,046 instances)
5. **OtherEvents** - Item 8.01 (4,502 instances)
6. **EntryintoaMaterialDefinitiveAgreement** - Item 1.01 (2,415 instances)
7. **SubmissionofMatterstoaVoteofSecurityHolders** - Item 5.07 (2,339 instances)
8. **CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant** - Item 2.03 (1,418 instances)
9. **AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear** - Item 5.03 (815 instances)
10. **UnregisteredSalesofEquitySecurities** - Item 3.02 (294 instances)
11. **TerminationofaMaterialDefinitiveAgreement** - Item 1.02 (267 instances)
12. **CostsAssociatedwithExitorDisposalActivities** - Item 2.05 (225 instances)
13. **CompletionofAcquisitionorDispositionofAssets** - Item 2.01 (171 instances)
14. **MaterialModificationstoRightsofSecurityHolders** - Item 3.03 (120 instances)
15. **MaterialImpairments** - Item 2.06 (51 instances)
16. **NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing** - Item 3.01 (48 instances)
17. **ChangesinRegistrantsCertifyingAccountant** - Item 4.01 (43 instances)
18. **MaterialCybersecurityIncidents** - Item 1.05 (18 instances)
19. **ChangesinControlofRegistrant** - Item 5.01 (17 instances)
20. **NonRelianceonPreviouslyIssuedFinancialStatementsoraRelatedAuditReportorCompletedInterimReview** - Item 4.02 (14 instances)
21. **TriggeringEventsThatAccelerateorIncreaseaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangement** - Item 2.04 (14 instances)
22. **ShareholderNominationsPursuanttoExchangeActRule14a-11** - (10 instances)
23. **TemporarySuspensionofTradingUnderRegistrantsEmployeeBenefitPlans** - Item 5.04 (9 instances)
24. **AmendmentstotheRegistrantsCodeofEthics,orWaiverofaProvisionoftheCodeofEthics** - Item 5.05 (7 instances)
25. **BankruptcyorReceivership** - Item 1.03 (1 instance)

### Additional Common Sections
1. **OtherInformation** - Miscellaneous information (7,072 instances)
2. **Exhibits** - Exhibit listings (5,397 instances)
3. **UnregisteredSalesofEquitySecuritiesandUseofProceeds** - (4,943 instances)
4. **MineSafetyDisclosures** - Mining company disclosures (4,829 instances)
5. **DefaultsUponSeniorSecurities** - Default notices (2,683 instances)
6. **MineSafetyReportingofShutdownsandPatternsofViolations** - (15 instances)

---

## 📊 ETF Ticker References

For market analysis queries, these ETF fields are available:
- **Company.sector_etf** → Sector SPDR ETF (e.g., 'XLK' for Technology)
- **Company.industry_etf** → Industry-specific ETF (e.g., 'IYW' for Tech-Software)
- **Industry.etf** → Industry ETF ticker
- **Sector.etf** → Sector ETF ticker  
- **MarketIndex.etf** → 'SPY' for S&P 500

```cypher
-- Get company with its sector/industry ETFs for market comparison
MATCH (c:Company {ticker: 'AAPL'})
RETURN c.ticker, c.sector, c.sector_etf, c.industry, c.industry_etf
-- Returns: AAPL, Technology, XLK, Computers, IYW

-- Compare company performance to sector ETF
MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: 'AAPL'})
WHERE n.created > datetime() - duration('P30D')
RETURN n.title, r.daily_stock as stock_return, r.daily_sector as sector_return,
       c.sector_etf as sector_etf,
       r.daily_stock - r.daily_sector as excess_return
ORDER BY ABS(r.daily_stock - r.daily_sector) DESC
LIMIT 20
```

## 🚀 Performance Best Practices

### With Fulltext Indexes
1. **Fulltext search first** - 10-100x faster than CONTAINS
2. **Filter after scoring** - Let fulltext rank results first
3. **Use boolean queries** - `revenue AND growth` more efficient than multiple searches
4. **Leverage fuzzy search** - `acquisiton~` handles typos automatically
5. **Cache by score threshold** - Cache results with score > 2.0
6. **Use exact phrases** - `"revenue growth"` for precise matches
7. **Index warmup** - First query after restart may be slower

### General Query Optimization
1. **Use section_name filter** when you know the specific section
2. **Add date filters** to limit scope: `WHERE r.created > datetime() - duration('P90D')`
3. **Use LIMIT early** in query chains to prevent memory issues
4. **Direct match for metadata** - Don't use fulltext for exact matches like formType
5. **Batch similar searches** - Run multiple fulltext queries in parallel when possible

## 🔍 Search Strategy Decision Tree

```
User Query Analysis:
├─ Contains "8-K" → Use 8-K specific patterns
│   ├─ "earnings" → ResultsofOperationsandFinancialCondition
│   ├─ "CEO/executive" → DepartureofDirectorsorCertainOfficers
│   ├─ "agreement/contract" → EntryintoaMaterialDefinitiveAgreement
│   ├─ "vote/meeting" → SubmissionofMatterstoaVoteofSecurityHolders
│   └─ "debt/loan" → CreationofaDirectFinancialObligation
├─ Contains "discuss/explain/analysis" → Use MD&A patterns
├─ Contains "risk" → Use RiskFactors or Cybersecurity patterns
├─ Contains "exhibit/attachment" → Use ExhibitContent patterns
├─ Contains "json/structured" → Use FinancialStatementContent
├─ Contains specific company → Add company filter first
├─ Contains date references → Add time filters
└─ General search → Use combined search pattern
```

## 🎯 Natural Language to Section Mapping

| User Says | Maps To Section |
|-----------|----------------|
| "earnings announcement" | ResultsofOperationsandFinancialCondition |
| "CEO departure", "new CFO" | DepartureofDirectorsorCertainOfficers |
| "merger agreement" | EntryintoaMaterialDefinitiveAgreement |
| "shareholder vote" | SubmissionofMatterstoaVoteofSecurityHolders |
| "new debt", "credit facility" | CreationofaDirectFinancialObligation |
| "investor presentation" | RegulationFDDisclosure + ExhibitContent |
| "bankruptcy" | BankruptcyorReceivership |
| "acquisition completed" | CompletionofAcquisitionorDispositionofAssets |
| "impairment charge" | MaterialImpairments |
| "delisting warning" | NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard |
| "business description" | Business (10-K only) |
| "risk factors" | RiskFactors |
| "legal proceedings" | LegalProceedings |
| "executive compensation" | ExecutiveCompensation |
| "cyber incident" | MaterialCybersecurityIncidents or Cybersecurity |

## 📊 Content Size Guidelines

| Content Type | Typical Size | Recommended Substring |
|--------------|--------------|----------------------|
| ExtractedSectionContent | 100-960KB | 1000-3000 chars |
| ExhibitContent | 10-500KB | 1000-2000 chars |
| FinancialStatementContent | 50KB-1.5MB | 500-1000 chars (JSON) |
| FilingTextContent | 5-200KB | 1000-2000 chars |

## 🎟️ Optimized Search Examples

### Smart Context Window Search
**Natural Language**: find discussion around specific term | context search | search with context

```cypher
// Fulltext with proximity search for better context
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', '"revenue guidance"~10') 
YIELD node, score
MATCH (r:Report {id: node.filing_id})<-[:PRIMARY_FILER]-(c:Company)
WHERE r.formType IN ['10-K', '10-Q']
// Extract context around the match (without APOC)
WITH c, r, node, score, toLower(node.content) as lower_content
WITH c, r, node, score,
     CASE 
       WHEN lower_content CONTAINS 'revenue guidance'
       THEN size(split(substring(lower_content, 0, size(lower_content)), 'revenue guidance')[0])
       ELSE 0
     END as position
RETURN c.ticker, r.formType, node.section_name,
       substring(node.content, 
                 CASE WHEN position < 500 THEN 0 ELSE position - 500 END,
                 1000) as context_excerpt,
       score
ORDER BY score DESC
LIMIT 20
```

### Sentiment-Aware Search
**Natural Language**: positive revenue discussion | negative outlook | optimistic guidance

```cypher
// Fulltext boolean query for sentiment analysis
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 
    '(revenue OR sales) AND (increase OR growth OR improve OR strong OR record OR exceed)') 
YIELD node, score
WHERE node.section_name CONTAINS 'Management'
MATCH (r:Report {id: node.filing_id})<-[:PRIMARY_FILER]-(c:Company)
// Boost results with more positive terms
WITH c, r, node, score,
     ['increase', 'growth', 'improve', 'strong', 'record', 'exceed'] as positive_terms,
     toLower(node.content) as lower_content
WITH c, r, node, score,
     [term IN positive_terms WHERE lower_content CONTAINS term] as found_positives
RETURN c.ticker, r.formType,
       found_positives as positive_indicators,
       substring(node.content, 0, 2000) as excerpt,
       score * SIZE(found_positives) as weighted_score
ORDER BY weighted_score DESC
LIMIT 20
```

### Cross-Reference Pattern
**Natural Language**: compare current and previous filing | year over year discussion | compare to last quarter

```cypher
// Find current and previous period discussions of same topic using fulltext
WITH 'AAPL' as ticker
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'revenue') 
YIELD node, score
WHERE node.section_name CONTAINS 'Management'
MATCH (c:Company {ticker: ticker})<-[:PRIMARY_FILER]-(r:Report {id: node.filing_id})
WHERE r.formType = '10-K'
WITH c, r, node, score
ORDER BY r.created DESC
LIMIT 2
RETURN c.ticker, r.created as filing_date,
       substring(node.content, 0, 1500) as discussion,
       score
ORDER BY r.created DESC
```

---

## 🎤 Earnings Call Transcript Patterns

### 1. Basic Transcript Access

#### Find Company Transcripts
**Natural Language**: earnings calls | conference calls | quarterly calls | investor calls | management calls

```cypher
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t:Transcript)
WHERE c.ticker = 'AAPL'
RETURN t.conference_datetime, t.fiscal_quarter, t.fiscal_year, 
       t.formType, t.speakers
ORDER BY t.conference_datetime DESC
LIMIT 10
```

#### Recent Earnings Calls Across Market
**Natural Language**: recent earnings calls | latest conference calls | newest transcripts

```cypher
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t:Transcript)
WHERE t.conference_datetime > datetime() - duration('P30D')
RETURN c.ticker, c.name, t.conference_datetime, 
       t.fiscal_quarter, t.fiscal_year
ORDER BY t.conference_datetime DESC
LIMIT 20
```

### 2. Transcript Content Access

#### Get Prepared Remarks (Management Statements)
**Natural Language**: CEO remarks | management prepared statements | opening remarks | prepared comments

```cypher
MATCH (c:Company {ticker: 'AAPL'})-[:HAS_TRANSCRIPT]->(t:Transcript)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
RETURN t.conference_datetime, substring(pr.content, 0, 3000) as remarks
ORDER BY t.conference_datetime DESC
LIMIT 5
```

#### Search Within Prepared Remarks
**Natural Language**: search earnings call remarks | find in management comments | prepared remarks about revenue

```cypher
CALL db.index.fulltext.queryNodes('prepared_remarks_ft', 'artificial intelligence')
YIELD node, score
MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(node)
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
RETURN c.ticker, t.conference_datetime, 
       substring(node.content, 0, 2000) as ai_discussion, score
ORDER BY score DESC
LIMIT 10
```

### 3. Q&A Exchange Patterns

#### Get Q&A Exchanges
**Natural Language**: analyst questions | Q&A section | earnings call questions | analyst Q&A

```cypher
MATCH (c:Company {ticker: 'MSFT'})-[:HAS_TRANSCRIPT]->(t:Transcript)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WHERE qa.questioner_title CONTAINS 'Analyst'
RETURN qa.questioner, qa.questioner_title, qa.responders, 
       qa.exchanges, qa.sequence
ORDER BY t.conference_datetime DESC, qa.sequence
LIMIT 10
```

#### Follow Q&A Thread
**Natural Language**: follow up questions | Q&A sequence | conversation thread | analyst follow ups

```cypher
MATCH (qa1:QAExchange)-[:NEXT_EXCHANGE]->(qa2:QAExchange)
WHERE qa1.questioner CONTAINS 'Goldman'
RETURN qa1.questioner, qa1.exchanges as question1,
       qa2.questioner, qa2.exchanges as followup
LIMIT 5
```

### 4. Vector Similarity Search on Q&A

#### Find Similar Questions Using Embeddings
**Natural Language**: similar analyst questions | questions like this | related Q&A | comparable discussions

```cypher
// First, get embedding for a known Q&A
MATCH (qa:QAExchange {id: 'example_qa_id'})
WITH qa.embedding as queryEmbedding
// Find similar Q&As using vector similarity
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 10, queryEmbedding)
YIELD node, score
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
RETURN c.ticker, t.conference_datetime, node.questioner,
       substring(node.exchanges, 0, 500) as question, score
ORDER BY score DESC
```

#### Semantic Search Across All Q&As
**Natural Language**: find discussions about AI | search Q&A semantically | similar topics in calls

```cypher
// Note: This requires encoding the search query to an embedding first
// Example assumes you have the embedding for "artificial intelligence strategy"
WITH [0.123, -0.456, ...] as searchEmbedding  // 3072-dimensional vector
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 20, searchEmbedding)
YIELD node, score
WHERE score > 0.8  // Similarity threshold
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(node)
MATCH (c:Company)-[:HAS_TRANSCRIPT]->(t)
RETURN c.ticker, t.conference_datetime, 
       node.questioner, node.questioner_title,
       substring(node.exchanges, 0, 1000) as discussion, score
ORDER BY score DESC
LIMIT 20
```

### 5. Transcript Impact Analysis

#### Transcripts Affecting Stock Price
**Natural Language**: earnings call impact | transcript market reaction | call drove stock down | conference call returns

```cypher
MATCH (t:Transcript)-[rel:INFLUENCES]->(c:Company)
WHERE rel.daily_stock < -3.0  // Stock fell more than 3%
RETURN c.ticker, t.conference_datetime, 
       rel.daily_stock as stock_return,
       rel.daily_macro as market_return,
       rel.daily_stock - rel.daily_macro as excess_return
ORDER BY rel.daily_stock
LIMIT 20
```

#### Positive Earnings Call Reactions
**Natural Language**: positive earnings reaction | good earnings call | stock up after call

```cypher
MATCH (t:Transcript)-[rel:INFLUENCES]->(c:Company)
WHERE rel.session_stock > 5.0  // Session return > 5%
  AND t.formType = 'earnings'
RETURN c.ticker, t.conference_datetime,
       rel.session_stock as session_return,
       rel.hourly_stock as immediate_return
ORDER BY rel.session_stock DESC
LIMIT 20
```

---

## 📰 News Patterns

### 1. Basic News Queries

#### Recent Company News
**Natural Language**: latest news | recent news | company news | news articles | press coverage

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: 'AAPL'})
WHERE n.created > datetime() - duration('P7D')
RETURN n.title, n.teaser, n.created, n.url
ORDER BY n.created DESC
LIMIT 20
```

#### Search News by Content
**Natural Language**: news about merger | acquisition news | earnings news | product launch news

```cypher
CALL db.index.fulltext.queryNodes('news_ft', 'merger acquisition')
YIELD node, score
MATCH (node)-[:INFLUENCES]->(c:Company)
RETURN DISTINCT c.ticker, node.title, node.teaser, 
       node.created, score
ORDER BY score DESC
LIMIT 20
```

### 2. News Impact Analysis

#### ⚠️ CRITICAL: INFLUENCES Anomaly (DATA QUALITY ISSUE)

**Issue**: 1,730 News→Company relationships have industry returns instead of stock returns

```cypher
-- Find anomalous relationships
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_industry IS NOT NULL AND r.daily_stock IS NULL
RETURN count(*) as anomaly_count  -- Returns: 1,730

-- When querying News impact on companies, handle this edge case:
MATCH (n:News)-[r:INFLUENCES]->(c:Company)
WHERE r.daily_stock IS NOT NULL  -- Explicitly check for stock returns
   OR r.daily_industry IS NOT NULL  -- Some have industry by mistake
RETURN n.title, c.ticker,
       COALESCE(r.daily_stock, r.daily_industry) as return_value,
       CASE WHEN r.daily_stock IS NULL THEN 'ANOMALY' ELSE 'NORMAL' END as data_quality
ORDER BY ABS(COALESCE(r.daily_stock, r.daily_industry)) DESC
LIMIT 20
```

#### News Driving Significant Moves (CORRECTED)
**Natural Language**: market moving news | high impact news | news that moved stocks | significant news events

```cypher
-- CORRECTED: Handles the anomaly where some have industry returns instead
MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
WHERE ABS(COALESCE(rel.daily_stock, rel.daily_industry)) > 5.0  // More than 5% move
RETURN n.title, c.ticker, 
       COALESCE(rel.daily_stock, rel.daily_industry) as actual_return,
       rel.daily_macro, n.created,
       CASE WHEN rel.daily_stock IS NULL THEN 'ANOMALY' ELSE 'NORMAL' END as data_quality
ORDER BY ABS(COALESCE(rel.daily_stock, rel.daily_industry)) DESC
LIMIT 20
```

#### Pre-Market News Impact
**Natural Language**: pre-market news | overnight news | before open news | early morning news

```cypher
MATCH (n:News)-[rel:INFLUENCES]->(c:Company)
WHERE n.market_session = 'pre_market'
  AND ABS(rel.session_stock) > 2.0
RETURN n.title, c.ticker, n.created,
       rel.session_stock as pre_market_impact,
       rel.daily_stock as full_day_impact
ORDER BY ABS(rel.session_stock) DESC
LIMIT 20
```

### 3. Vector Similarity Search on News

#### Find Similar News Articles
**Natural Language**: similar news | related articles | news like this | comparable news stories

```cypher
// Find news similar to a known article
MATCH (n:News {id: 'example_news_id'})
WITH n.embedding as queryEmbedding
CALL db.index.vector.queryNodes('news_vector_index', 10, queryEmbedding)
YIELD node, score
WHERE score > 0.85  // High similarity threshold
RETURN node.title, node.teaser, node.created, score
ORDER BY score DESC
```

#### Semantic News Search
**Natural Language**: find news about similar topics | semantic news search | AI-powered news search

```cypher
// Requires embedding of search query first
WITH [0.234, -0.567, ...] as searchEmbedding  // "renewable energy investments"
CALL db.index.vector.queryNodes('news_vector_index', 30, searchEmbedding)
YIELD node, score
WHERE score > 0.75
MATCH (node)-[:INFLUENCES]->(c:Company)
RETURN DISTINCT c.ticker, c.sector, node.title, 
       node.teaser, node.created, score
ORDER BY score DESC
LIMIT 20
```

### 4. Cross-Entity News Impact

#### News Affecting Multiple Companies
**Natural Language**: sector-wide news | industry news impact | news affecting multiple stocks

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company)
WITH n, COUNT(DISTINCT c) as companies_affected
WHERE companies_affected > 5
MATCH (n)-[rel:INFLUENCES]->(c:Company)
RETURN n.title, companies_affected,
       COLLECT(DISTINCT {ticker: c.ticker, impact: rel.daily_stock})[0..10] as impacts
ORDER BY companies_affected DESC
LIMIT 10
```

#### Industry-Wide News Events
**Natural Language**: industry news | sector news | market-wide news | broad impact news

```cypher
MATCH (n:News)-[rel:INFLUENCES]->(i:Industry)
WHERE ABS(rel.daily_industry) > 2.0
RETURN n.title, i.name as industry, 
       rel.daily_industry as industry_impact,
       n.created
ORDER BY ABS(rel.daily_industry) DESC
LIMIT 20
```

---

## 🤖 Advanced Pattern: Combining News and Transcripts

### News Around Earnings Calls
**Natural Language**: news before earnings | news after earnings call | earnings coverage

```cypher
MATCH (c:Company {ticker: 'AAPL'})-[:HAS_TRANSCRIPT]->(t:Transcript)
WITH c, t, t.conference_datetime as call_date
MATCH (n:News)-[:INFLUENCES]->(c)
WHERE n.created > call_date - duration('P2D')
  AND n.created < call_date + duration('P2D')
RETURN n.title, n.created, 
       CASE 
         WHEN n.created < call_date THEN 'Before Call'
         ELSE 'After Call'
       END as timing,
       duration.between(n.created, call_date) as time_diff
ORDER BY ABS(duration.inSeconds(duration.between(n.created, call_date)).seconds)
LIMIT 20
```

### Semantic Similarity Between News and Q&A
**Natural Language**: news matching earnings discussions | related news and Q&A | cross-reference news and calls

```cypher
// Find Q&As discussing topics similar to recent news
// This is a conceptual example - requires embedding comparison
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: 'TSLA'})
WHERE n.created > datetime() - duration('P7D')
  AND n.embedding IS NOT NULL
WITH n, c
LIMIT 5
UNWIND n AS news
CALL db.index.vector.queryNodes('qaexchange_vector_idx', 5, news.embedding)
YIELD node as qa, score
WHERE score > 0.8
MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(qa)
WHERE (c)-[:HAS_TRANSCRIPT]->(t)
RETURN news.title, news.created as news_date,
       t.conference_datetime as call_date,
       substring(qa.exchanges, 0, 500) as related_discussion,
       score
ORDER BY score DESC
```

For XBRL queries (structured numeric data for 10-K/10-Q only), see XBRL_PATTERNS.md

---

## 🚀 Fulltext Index Setup

### Create All Required Indexes
```cypher
// Core filing content indexes
CREATE FULLTEXT INDEX extracted_section_content_ft IF NOT EXISTS
FOR (n:ExtractedSectionContent) ON EACH [n.content, n.section_name];

CREATE FULLTEXT INDEX exhibit_content_ft IF NOT EXISTS
FOR (n:ExhibitContent) ON EACH [n.content, n.exhibit_number];

CREATE FULLTEXT INDEX filing_text_content_ft IF NOT EXISTS
FOR (n:FilingTextContent) ON EACH [n.content, n.form_type];

CREATE FULLTEXT INDEX financial_statement_content_ft IF NOT EXISTS
FOR (n:FinancialStatementContent) ON EACH [n.value, n.statement_type];

// Transcript content indexes
CREATE FULLTEXT INDEX full_transcript_ft IF NOT EXISTS
FOR (n:FullTranscriptText) ON EACH [n.content];

CREATE FULLTEXT INDEX prepared_remarks_ft IF NOT EXISTS
FOR (n:PreparedRemark) ON EACH [n.content];

CREATE FULLTEXT INDEX qa_exchange_ft IF NOT EXISTS
FOR (n:QAExchange) ON EACH [n.exchanges];

CREATE FULLTEXT INDEX question_answer_ft IF NOT EXISTS
FOR (n:QuestionAnswer) ON EACH [n.content];

// News content index
CREATE FULLTEXT INDEX news_ft IF NOT EXISTS
FOR (n:News) ON EACH [n.title, n.body, n.teaser];

// XBRL text facts index
CREATE FULLTEXT INDEX fact_textblock_ft IF NOT EXISTS
FOR (n:Fact) ON EACH [n.value, n.qname];
```

### Verify Indexes
```cypher
SHOW FULLTEXT INDEXES;
```

### Vector Indexes (Already Created)
```cypher
-- Existing vector indexes for similarity search:
-- news_vector_index: News.embedding (3072 dimensions)
-- qaexchange_vector_idx: QAExchange.embedding (3072 dimensions)

-- Verify vector indexes
SHOW VECTOR INDEXES;
```

## 📊 Performance Comparison

| Operation | CONTAINS | Fulltext | Improvement |
|-----------|----------|----------|--------------|
| Search 1M docs | 2-5 sec | 20-50ms | 100x faster |
| Phrase search | Complex | Native | Built-in |
| Relevance ranking | Manual | Automatic | Native scoring |
| Fuzzy matching | Not possible | Built-in | Handles typos |
| Boolean logic | Complex | Native | AND/OR/NOT |
| Memory usage | High | Low | Indexed |

## 🔧 Fulltext Query Syntax

- **Exact phrase**: `"revenue growth"`
- **Boolean**: `revenue AND (growth OR increase)`
- **Fuzzy**: `acquisiton~` (handles typos)
- **Wildcard**: `rev*` (prefix search)
- **Proximity**: `"revenue growth"~10` (within 10 words)
- **Boost**: `revenue^2 growth` (boost revenue term)

## ⚠️ When to Use CONTAINS Instead

1. **Complex regex patterns**: Financial amounts, dates, specific formats
2. **Case-sensitive search**: When exact case matters
3. **Character-level operations**: Finding specific punctuation
4. **When fulltext indexes are unavailable**: Fallback option

## 🤖 Note on Vector Embeddings

### Available Embeddings
- **News.embedding**: 99.27% of news articles have embeddings (176,059 of 177,349)
- **QAExchange.embedding**: 99.94% coverage (68,113 of 68,152 have embeddings)

### Using Vector Similarity
1. **Direct similarity**: Compare two known nodes using their embeddings
2. **Semantic search**: Requires encoding your search query to embedding first
3. **Similarity threshold**: Typically use score > 0.75 for relevant results
4. **Performance**: Vector searches are very fast but require pre-computed embeddings

### Example: Getting Embeddings for Semantic Search
```cypher
// Check if embeddings exist before using
MATCH (n:News)
WHERE n.embedding IS NOT NULL
RETURN COUNT(n) as news_with_embeddings

MATCH (qa:QAExchange)
WHERE qa.embedding IS NOT NULL
RETURN COUNT(qa) as qa_with_embeddings
```