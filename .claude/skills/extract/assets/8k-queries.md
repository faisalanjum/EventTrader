# 8-K / Exhibit Queries (S4)

Source content queries for 8-K filings and their exhibits.

---

## 4. Source Content: 8-K / Exhibits

### 4A. 8-K Filings with Item 2.02 (Earnings)

```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.items CONTAINS 'Item 2.02'
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.created, r.items, r.market_session
ORDER BY r.created
```
**Usage**: Pass `null` for both dates to retrieve all historical 8-K earnings filings.

### 4B. Pre-Announcements (Item 7.01 / 8.01)

Mid-quarter updates, often market-moving. Check between regular earnings dates.

```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE (r.items CONTAINS '7.01' OR r.items CONTAINS '8.01')
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.created, r.items
ORDER BY r.created
```

### 4C. Exhibit Content (by Exhibit Number)

Primary content source for 8-K earnings. 94% of Item 2.02 filings have data in EX-99.1.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = $source_key
RETURN e.content AS content, r.created AS filing_date
```
**Note**: Use exact match on `exhibit_number` (e.g., `'EX-99.1'`). Common values: `EX-99.1` (press release), `EX-99.2` (presentation), `EX-10.1`/`EX-10.2` (material contracts/agreements). If exact match fails, use 4D to discover actual exhibit numbers (dirty variants like `EX-99.01` exist).

### 4D. All Exhibits for Report (Discovery)

Run when unsure which exhibit has content or when exact match fails.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
RETURN e.exhibit_number, size(e.content) AS content_length
ORDER BY e.exhibit_number
```

### 4E. Section Content (8-K Item Text)

For items where data is in the section itself (33% of 8-Ks have section-only data).

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = $source_key
RETURN s.content AS content, r.created AS filing_date
```
**section_name values**: See full 12-value table in the asset profile (`8k.md`, Step 3). Examples: `ResultsofOperationsandFinancialCondition` (Item 2.02), `EntryintoaMaterialDefinitiveAgreement` (Item 1.01).

### 4F. Filing Text Content (Fallback)

Fallback when exhibit and section parsing both fail. Average 690KB — large.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content, r.created AS filing_date
```

### 4G. Content Inventory for Report

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

### 4H. 8-K Filings by Item Code (Generic)

Parameterized version of 4A/4B for any SEC item code. Use when extraction targets items beyond 2.02/7.01/8.01.

```cypher
MATCH (r:Report {formType: '8-K'})-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.items CONTAINS $item_code
  AND ($start_date IS NULL OR r.created >= $start_date)
  AND ($end_date IS NULL OR r.created <= $end_date)
RETURN r.accessionNo, r.created, r.items, r.market_session
ORDER BY r.created
```
**Usage**: Pass item code as string, e.g., `$item_code = 'Item 1.01'`. For common items, prefer 4A (Item 2.02) or 4B (7.01/8.01) — they have tighter filters.

### 4I. Financial Statement Content

Structured JSON financial statements attached to a report. Rare for 8-K but exists. Check 4G `financial_stmts` first.

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN fs.statement_type, fs.value AS content, r.created AS filing_date
```
**statement_type values**: `BalanceSheets`, `StatementsOfIncome`, `StatementsOfCashFlows`, `StatementsOfShareholdersEquity`. Note: `fs.value` is a JSON string — needs parsing, not direct field read.
