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

### 5B. Canonical MD&A Section Content

Fetch the canonical management discussion section when it exists.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name STARTS WITH 'Management'
  AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'
RETURN s.id AS section_id,
       s.section_name,
       s.content AS content,
       size(s.content) AS content_length,
       r.accessionNo,
       r.formType,
       r.created AS filing_date,
       r.periodOfReport
```
**Note**: 10-K uses the curly apostrophe variant (U+2019). If this returns no rows, use 5D to discover available sections and 5I to fetch a specific section by name.

### 5C. Financial Statement Content (Supplementary)

Structured JSON statement payload.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
WHERE fs.statement_type = $source_key
RETURN fs.id AS statement_id,
       fs.statement_type,
       fs.value AS content,
       size(fs.value) AS content_length,
       r.accessionNo,
       r.formType,
       r.created AS filing_date,
       r.periodOfReport
```
**statement_type values**: `BalanceSheets`, `StatementsOfIncome`, `StatementsOfCashFlows`, `StatementsOfShareholdersEquity`.

### 5D. All Sections for Report (Discovery)

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN s.id AS section_id, s.section_name, size(s.content) AS content_length
ORDER BY s.section_name
```

### 5E. Risk Factors Section Lookup

Fetch the canonical Risk Factors section when present.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = 'RiskFactors'
RETURN s.id AS section_id, s.section_name, size(s.content) AS content_length
```

### 5F. Content Inventory for Report

Quickly check what content types exist before fetching.

```cypher
MATCH (r:Report {accessionNo: $accession})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
RETURN r.accessionNo, r.formType, r.created, r.periodOfReport,
       r.primaryDocumentUrl, r.linkToTxt, r.linkToHtml,
       r.market_session, r.returns_schedule,
       collect(DISTINCT e.exhibit_number) AS exhibits,
       collect(DISTINCT s.section_name) AS sections,
       collect(DISTINCT fs.statement_type) AS financial_stmts,
       count(DISTINCT ft) AS filing_text_count
```
**Note**: `returns_schedule` is a JSON string on the Report node.

### 5G. Filing Text Content (Fallback)

Raw full filing text. This is typically much larger than section content and should usually be bounded before model input.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.id AS filing_text_id,
       f.content AS content,
       size(f.content) AS content_length,
       r.accessionNo,
       r.formType,
       r.created AS filing_date,
       r.periodOfReport
```

### 5H. Exhibit Content (Fallback)

Fetch exhibit content by number.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = $source_key
RETURN e.id AS exhibit_id,
       e.exhibit_number,
       e.content AS content,
       size(e.content) AS content_length,
       r.accessionNo,
       r.formType,
       r.created AS filing_date,
       r.periodOfReport
```

### 5I. Section Content by Name

Fetch any specific extracted section after discovering available names with 5D.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = $section_name
RETURN s.id AS section_id,
       s.section_name,
       s.content AS content,
       size(s.content) AS content_length,
       r.accessionNo,
       r.formType,
       r.created AS filing_date,
       r.periodOfReport
```
