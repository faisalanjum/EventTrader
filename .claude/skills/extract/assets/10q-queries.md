# 10-Q / 10-K Queries (S5)

Source content queries for 10-Q and 10-K filings.

---

## 5. Source Content: 10-Q / 10-K

### 5A. 10-Q/10-K Filing List

```cypher
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType IN ['10-K', '10-Q']
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.formType, r.created, r.periodOfReport
ORDER BY r.created
```

### 5B. MD&A Section Content (Primary for 10-Q/10-K)

MD&A is the primary scan scope for 10-Q/10-K guidance extraction.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name STARTS WITH 'Management'
  AND s.section_name CONTAINS 'DiscussionandAnalysisofFinancialCondition'
RETURN s.content AS content, s.section_name, r.created AS filing_date
```
**Note**: Two naming variants exist. Check both.

### 5C. Financial Statement Content (Supplementary)

Structured JSON data — look for footnotes/annotations with forward guidance.

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

### 5E. Risk Factors (Exclude from Guidance)

Useful to identify so guidance scanner can skip this section (legal/risk-heavy content).

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = 'RiskFactors'
RETURN size(s.content) AS risk_factors_length
```
