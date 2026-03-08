# 10-K Queries (S5)

Source content queries for 10-K annual filings.

---

## 5. Source Content: 10-K

### 5A. 10-K Filing List

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '10-K'
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.formType, r.created, r.periodOfReport
ORDER BY r.created
```

### 5B. MD&A Section Content (Primary for 10-K)

MD&A is the primary scan scope for 10-K extraction.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name STARTS WITH 'Management'
  AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'
RETURN s.content AS content, s.section_name, r.created AS filing_date
```
**Note**: 10-K uses the curly apostrophe variant (U+2019).

### 5C. Financial Statement Content (Supplementary)

Structured JSON data — look for footnotes/annotations with forward-looking content.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type = $source_key
RETURN fs.value AS content, r.created AS filing_date
```
**statement_type values**: `BalanceSheets`, `StatementsOfIncome`, `StatementsOfCashFlows`, `StatementsOfShareholdersEquity`.

### 5D. All Sections for Report (Discovery)

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN s.section_name, size(s.content) AS content_length
ORDER BY s.section_name
```

### 5E. Risk Factors (Exclude from Extraction)

Useful to identify so the extraction scanner can skip this section (legal/risk-heavy content).

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = 'RiskFactors'
RETURN size(s.content) AS risk_factors_length
```

### 5F. Content Inventory for Report

Quickly check what content types exist before fetching.

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

### 5G. Filing Text Content (Fallback)

Fallback when MD&A and financial statement parsing both fail. Average 690KB — large.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content, r.created AS filing_date
```

### 5H. Exhibit Content (Fallback)

Fetch exhibit content by number. Use when 5F inventory shows exhibits exist and MD&A is missing. Some 10-K filings have press releases (EX-99.1) attached.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = $source_key
RETURN e.content AS content, r.created AS filing_date
```
