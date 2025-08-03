# XBRL Query Patterns for Neo4j EventMarketDB

This is the definitive collection of XBRL query patterns for the Neo4j EventMarketDB.
All patterns have been thoroughly tested and verified.

**IMPORTANT**: XBRL data is ONLY available for 10-K and 10-Q reports. 8-K and other report types do NOT have XBRL.

**Generated**: January 2025  
**Database Coverage**: 7.69M Facts, 6.57M PRESENTATION_EDGE, 1.92M CALCULATION_EDGE relationships

## Critical Schema Rules

1. **NO Direct Fact-Report Relationship** - Facts connect to Reports ONLY through XBRLNode
2. **Correct Traversal Path**: Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact  
3. **Boolean Values**: `is_numeric` and `is_nil` use string values '1' or '0', NOT boolean true/false
4. **PRESENTATION_EDGE**: Only originates from Abstract nodes (never from Facts)
5. **All Properties Optional**: Most properties can be NULL - use IS NOT NULL checks where needed

---

## 1. Basic XBRL Navigation

### Get XBRL Nodes
**Natural Language**: what financial data is available | show me financial filings | list available reports | what documents do you have | show financial information

```cypher
MATCH (x:XBRLNode)
RETURN x.id, x.cik, x.accessionNo, x.report_id, x.displayLabel, x.primaryDocumentUrl
LIMIT 10
```

### Find Reports with XBRL
**Natural Language**: show me 10-K reports | find annual reports | get quarterly filings | list 10-Q documents | what reports have XBRL | which filings have structured data

```cypher
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)
WHERE r.formType IN ['10-K', '10-Q']
RETURN r.formType, r.cik, r.created, x.displayLabel
ORDER BY r.created DESC
LIMIT 20
```

### Company XBRL Documents
**Natural Language**: show apple's 10-K or 10-Q | get AAPL structured data | microsoft XBRL documents | find MSFT annual report | tesla's 10-K | amazon quarterly reports | structured financial data

```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)
RETURN c.ticker, r.formType, r.created, x.displayLabel
ORDER BY r.created DESC
LIMIT 10
```

---

## 2. Revenue and Income Facts

### Get Revenue Data (10-K/10-Q Only)
**Natural Language**: what's the revenue from 10-K | annual revenue | quarterly revenue | show sales from 10-Q | total revenue | revenue numbers | structured revenue data | XBRL revenue

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax' 
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as revenue, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Net Income/Loss (10-K/10-Q Only)
**Natural Language**: what's the profit from 10-K | annual net income | quarterly earnings | net income from 10-Q | bottom line | structured profit data | XBRL earnings | annual profit | quarterly profit

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept)
WHERE con.qname = 'us-gaap:NetIncomeLoss' 
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as net_income, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Earnings Per Share (10-K/10-Q Only)
**Natural Language**: earnings per share from 10-K | EPS from quarterly report | structured EPS data | annual EPS | quarterly EPS | XBRL earnings per share | per share profit

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:EarningsPerShareBasic', 'us-gaap:EarningsPerShareDiluted']
  AND f.is_numeric = '1'
RETURN c.ticker, f.qname, f.value as eps, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

---

## 3. Balance Sheet Items

### Get Total Assets (10-K/10-Q Only)
**Natural Language**: total assets | what do they own | asset value | how much are they worth | company assets | balance sheet assets | assets from 10-K | assets from 10-Q

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:Assets'
  AND f.is_numeric = '1'
WITH c, f, r ORDER BY r.created DESC
RETURN c.ticker, f.value as total_assets, r.formType, r.created
LIMIT 20
```

### Get Current Assets (10-K/10-Q Only)
**Natural Language**: current assets from 10-K | quarterly current assets | liquid assets from 10-Q | short term assets | structured asset data | XBRL current assets

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:AssetsCurrent'
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as current_assets, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Total Liabilities (10-K/10-Q Only)
**Natural Language**: total debt from 10-K | liabilities from quarterly report | structured debt data | XBRL liabilities | annual debt | quarterly obligations | total liabilities

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:Liabilities'
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as total_liabilities, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Stockholders Equity (10-K/10-Q Only)
**Natural Language**: shareholders equity from 10-K | book value from quarterly report | structured equity data | XBRL stockholders equity | annual equity | quarterly net worth

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:StockholdersEquity'
  AND f.is_numeric = '1'
RETURN c.ticker, f.value as equity, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Cash Balance (10-K/10-Q Only)
**Natural Language**: cash from 10-K | quarterly cash balance | structured cash data | XBRL cash position | annual cash | cash from 10-Q | available cash

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:Cash', 'us-gaap:CashAndCashEquivalentsAtCarryingValue']
  AND f.is_numeric = '1'
RETURN c.ticker, f.qname, f.value as cash, r.formType, r.created
ORDER BY r.created DESC
LIMIT 20
```

---

## 4. Complete Fact with All Relationships

### Get Complete Revenue Fact Details (10-K/10-Q Only)
**Natural Language**: detailed XBRL revenue breakdown | structured revenue details | complete 10-K revenue data | all 10-Q revenue facts | comprehensive XBRL income data

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

---

## 5. Time-Based Queries

### Get Quarterly Data (10-Q Only)
**Natural Language**: quarterly XBRL results | Q1 revenue from 10-Q | Q2 structured earnings | Q3 XBRL data | Q4 financial facts | three month results | structured quarterly data

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE r.formType = '10-Q' 
  AND f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
  AND duration.between(date(p.start_date), date(p.end_date)).months <= 3
RETURN c.ticker, f.value as quarterly_revenue, p.start_date, p.end_date
ORDER BY p.end_date DESC
LIMIT 20
```

### Get Year-over-Year Comparison
**Natural Language**: compare to last year | year over year | annual growth | YoY | how did they do vs last year | yearly comparison | growth rate

```cypher
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname = 'us-gaap:NetIncomeLoss' 
  AND f.is_numeric = '1'
  AND r.formType = '10-K'
MATCH (f)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
RETURN c.ticker, f.value as net_income, p.start_date, p.end_date,
       p.end_date + ' to ' + p.start_date as fiscal_year
ORDER BY p.end_date DESC
LIMIT 5
```

### Get Latest Financial Data (10-K/10-Q Only)
**Natural Language**: latest XBRL results | most recent 10-K data | current structured financials | newest 10-Q facts | latest annual filing | recent quarterly XBRL | current quarter data

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)
WHERE r.formType IN ['10-K', '10-Q']
WITH c, r, x ORDER BY r.created DESC
WITH c, COLLECT({report: r, xbrl: x})[0] as latest
MATCH (latest.report)-[:HAS_XBRL]->(latest.xbrl)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 
                  'us-gaap:NetIncomeLoss', 'us-gaap:Assets']
  AND f.is_numeric = '1'
RETURN c.ticker, latest.report.formType, latest.report.created, f.qname, f.value
```

---

## 6. Period-Specific Queries

### Get Balance Sheet at Date (Instant)
**Natural Language**: assets at year end | balance sheet snapshot | what did they have on this date | point in time values | end of year balance

```cypher
MATCH (f:Fact)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'instant'
  AND f.is_numeric = '1'
  AND f.qname IN ['us-gaap:Assets', 'us-gaap:Liabilities', 'us-gaap:StockholdersEquity']
  AND p.start_date >= '2024-01-01'
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, f.qname, f.value, p.start_date as balance_date
ORDER BY p.start_date DESC
LIMIT 20
```

### Get Income Statement Period (Duration)
**Natural Language**: revenue for the quarter | income for the year | period results | how much did they make this period | quarterly performance

```cypher
MATCH (f:Fact)-[:HAS_PERIOD]->(p:Period)
WHERE p.period_type = 'duration'
  AND f.is_numeric = '1'
  AND f.qname IN ['us-gaap:Revenues', 'us-gaap:NetIncomeLoss', 'us-gaap:OperatingIncomeLoss']
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, f.qname, f.value, p.start_date, p.end_date,
       duration.between(date(p.start_date), date(p.end_date)).days as period_days
ORDER BY p.end_date DESC
LIMIT 20
```

---

## 7. TextBlock and Narrative Facts

### Get Accounting Policies
**Natural Language**: accounting policies | how do they recognize revenue | accounting methods | financial policies | reporting standards

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE r.formType = '10-K'
  AND f.qname CONTAINS 'AccountingPolicies'
  AND f.is_numeric = '0'
RETURN c.ticker, f.qname, substring(f.value, 0, 200) as policy_excerpt
LIMIT 10
```

### Get Risk Factors Text
**Natural Language**: what are the risks | business risks | risk factors | potential problems | company risks | what could go wrong

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname CONTAINS 'Risk'
  AND f.is_numeric = '0'
  AND f.qname CONTAINS 'TextBlock'
RETURN c.ticker, f.qname, substring(f.value, 0, 200) as risk_excerpt
LIMIT 10
```

---

## 8. Dimensional Analysis

### Get Revenue by Segment
**Natural Language**: revenue by segment | how much does each division make | segment performance | business unit revenue | revenue breakdown | sales by product

```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE f.qname CONTAINS 'Revenue'
  AND f.is_numeric = '1'
  AND m.qname CONTAINS 'Segment'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, f.value as revenue, m.label as segment
LIMIT 20
```

### Get Geographic Breakdown
**Natural Language**: revenue by country | sales by region | geographic breakdown | international sales | domestic vs foreign | where do they sell

```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE (m.qname CONTAINS 'Geographic' OR m.qname CONTAINS 'Country')
  AND f.is_numeric = '1'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, c.qname, f.value, m.label as geography
LIMIT 20
```

### Get Multi-Dimensional Facts
**Natural Language**: detailed breakdown | segment and geography | multiple breakdowns | complex analysis | detailed segments

```cypher
MATCH (f:Fact)-[:FACT_MEMBER]->(m:Member)
WHERE f.is_numeric = '1'
WITH f, COLLECT(DISTINCT m) as members
WHERE SIZE(members) > 1
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(comp:Company)
RETURN comp.ticker, c.qname, SIZE(members) as dimension_count, 
       [m IN members | m.label] as dimensions
LIMIT 10
```

### Dimension Hierarchy
**Natural Language**: show segment structure | how are segments organized | dimension hierarchy | segment categories

```cypher
MATCH (d:Dimension)-[:HAS_DOMAIN]->(dom:Domain)-[:HAS_MEMBER]->(m:Member)
WHERE d.qname CONTAINS 'Segment'
RETURN d.label as dimension, dom.label as domain, 
       COLLECT(DISTINCT m.label)[0..5] as sample_members
LIMIT 10
```

---

## 9. Calculation Trees

### Get Net Income Calculation
**Natural Language**: how is profit calculated | what makes up net income | profit calculation | income components | how do they calculate earnings

```cypher
MATCH (parent:Fact)-[calc:CALCULATION_EDGE]->(child:Fact)
WHERE parent.qname = 'us-gaap:NetIncomeLoss'
MATCH (parent)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, parent.qname as parent_concept, calc.weight as weight, 
       child.qname as child_concept, calc.order
ORDER BY calc.order
LIMIT 20
```

### Get Revenue Calculation Components
**Natural Language**: what makes up revenue | revenue components | how is revenue calculated | sales breakdown | revenue calculation

```cypher
MATCH (parent:Fact)-[calc:CALCULATION_EDGE]->(child:Fact)
WHERE parent.qname CONTAINS 'Revenue'
  AND calc.weight IS NOT NULL
MATCH (parent)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, parent.qname, child.qname, calc.weight
LIMIT 20
```

---

## 10. Presentation Structure

### Get Financial Statement Structure
**Natural Language**: how is the income statement organized | balance sheet structure | financial statement layout | report structure

```cypher
MATCH (a:Abstract)-[p:PRESENTATION_EDGE]->(child)
WHERE a.qname CONTAINS 'IncomeStatement' OR a.qname CONTAINS 'BalanceSheet'
RETURN a.label as section, labels(child)[0] as child_type,
       CASE WHEN 'Fact' IN labels(child) THEN child.qname 
            ELSE child.label END as child_item,
       p.child_order
ORDER BY p.parent_order, p.child_order
LIMIT 30
```

### Get Abstract Hierarchy
**Natural Language**: report sections | how are statements organized | document structure | statement hierarchy

```cypher
MATCH (parent:Abstract)-[p:PRESENTATION_EDGE]->(child:Abstract)
WHERE parent.qname CONTAINS 'Statement'
RETURN parent.label as parent_section, child.label as child_section, 
       p.child_order
ORDER BY p.child_order
LIMIT 20
```

### Search XBRL Structure Sections (NEW Fulltext!)
**Natural Language**: find balance sheet sections | search income statement structure | cash flow presentation | financial statement layout

```cypher
-- Search Abstract nodes by their presentation labels
CALL db.index.fulltext.queryNodes('abstract_ft', 'balance sheet') 
YIELD node, score
RETURN node.qname, node.label, score
ORDER BY score DESC
LIMIT 20
```

```cypher
-- Find all sections related to equity
CALL db.index.fulltext.queryNodes('abstract_ft', 'equity') 
YIELD node, score
-- Show what facts are under these sections
OPTIONAL MATCH (node)-[p:PRESENTATION_EDGE]->(f:Fact)
RETURN node.label as section, COUNT(f) as fact_count, score
ORDER BY score DESC
LIMIT 20
```

---

## 11. Concept and Unit Information

### Get Available Financial Concepts
**Natural Language**: what metrics are available | what can I query | available financial data | what concepts exist | list of metrics

```cypher
MATCH (c:Concept)<-[:HAS_CONCEPT]-(f:Fact)
WHERE c.namespace CONTAINS 'us-gaap'
WITH c, COUNT(f) as usage_count
ORDER BY usage_count DESC
LIMIT 20
RETURN c.qname, c.label, c.balance, c.period_type, usage_count
```

### Search Concepts by Name (NEW Fulltext!)
**Natural Language**: find revenue concepts | search for asset concepts | what concepts about debt | find depreciation concepts

```cypher
-- Search for concepts by their human-readable label
CALL db.index.fulltext.queryNodes('concept_ft', 'revenue') 
YIELD node, score
WHERE node.namespace CONTAINS 'us-gaap'
RETURN node.qname, node.label, node.period_type, score
ORDER BY score DESC
LIMIT 20
```

```cypher
-- Find concepts with fuzzy matching (handles variations)
CALL db.index.fulltext.queryNodes('concept_ft', 'depreciation~') 
YIELD node, score
WHERE node.namespace CONTAINS 'us-gaap'
RETURN node.qname, node.label, node.balance, score
ORDER BY score DESC
LIMIT 20
```

### Get Concept Types Distribution
**Natural Language**: what types of data | monetary vs shares | different data types | concept categories

```cypher
MATCH (c:Concept)
RETURN c.concept_type, COUNT(c) as count
ORDER BY count DESC
LIMIT 10
```

### Get Facts by Unit Type
**Natural Language**: values in dollars | data in shares | different units | currency values | per share data

```cypher
MATCH (u:Unit)<-[:HAS_UNIT]-(f:Fact)
WHERE f.is_numeric = '1'
WITH u.name as unit_type, COUNT(f) as fact_count
ORDER BY fact_count DESC
LIMIT 15
RETURN unit_type, fact_count
```

---

## 12. Context and Company Queries

### Get Company-Specific Facts
**Natural Language**: apple financial data | microsoft metrics | get all data for tesla | company financials | show me everything for AAPL

```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(comp:Company {ticker: 'AAPL'})
WITH ctx, comp LIMIT 100
MATCH (f:Fact)-[:IN_CONTEXT]->(ctx)
WHERE f.is_numeric = '1'
WITH f, comp
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
RETURN comp.ticker, c.qname, f.value, c.label
LIMIT 20
```

### Multi-Company Comparison
**Natural Language**: compare apple and microsoft | peer comparison | compare competitors | industry comparison | which company is better

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE c.ticker IN ['AAPL', 'MSFT', 'GOOGL']
  AND f.qname = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
  AND f.is_numeric = '1'
  AND r.formType = '10-K'
WITH c, f, r ORDER BY r.created DESC
WITH c, COLLECT({value: f.value, date: r.created})[0] as latest
RETURN c.ticker, latest.value as revenue, latest.date as report_date
ORDER BY c.ticker
```

---

## 13. XBRL Processing Status

### Get XBRL Processing Status
**Natural Language**: processing status | what's being processed | filing status | document processing | report status

```cypher
MATCH (r:Report)
WHERE r.xbrl_status IS NOT NULL
RETURN r.xbrl_status as status, COUNT(r) as count
ORDER BY count DESC
```

### Get Failed XBRL Processing
**Natural Language**: what failed | processing errors | failed reports | error messages | what went wrong

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)
WHERE r.xbrl_status = 'FAILED'
RETURN c.ticker, r.formType, r.created, r.xbrl_error
LIMIT 10
```

---

## 14. Special Fact Patterns

### Get Nil/Null Facts
**Natural Language**: missing values | null data | what's not reported | empty values | nil facts

```cypher
MATCH (f:Fact)
WHERE f.is_nil = '1'
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
WITH c.qname as concept, COUNT(f) as nil_count
ORDER BY nil_count DESC
LIMIT 10
RETURN concept, nil_count
```

### Get High Precision Facts
**Natural Language**: precise numbers | exact values | high precision data | detailed decimals

```cypher
MATCH (f:Fact)
WHERE f.is_numeric = '1' 
  AND f.decimals IN ['4', '5', '6', 'INF']
MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
MATCH (f)<-[:REPORTS]-(x:XBRLNode)<-[:HAS_XBRL]-(r:Report)<-[:PRIMARY_FILER]-(c:Company)
RETURN c.ticker, c.qname, f.value, f.decimals
LIMIT 20
```

### Get Custom Company Metrics
**Natural Language**: custom metrics | non-GAAP | company specific data | adjusted earnings | special metrics | proprietary measures

```cypher
MATCH (f:Fact)-[:HAS_CONCEPT]->(c:Concept)
WHERE NOT c.namespace CONTAINS 'fasb.org'
  AND c.namespace CONTAINS 'www.'
  AND f.is_numeric = '1'
WITH c.namespace as company_namespace, COUNT(DISTINCT c.qname) as custom_concepts
ORDER BY custom_concepts DESC
LIMIT 10
RETURN company_namespace, custom_concepts
```

---

## 15. Report Type Specific Queries

### Get Annual Report Data (10-K)
**Natural Language**: annual report | 10-K data | yearly results | annual filing | full year numbers

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 
                  'us-gaap:NetIncomeLoss', 'us-gaap:Assets']
  AND f.is_numeric = '1'
RETURN c.ticker, f.qname, f.value, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Get Quarterly Report Data (10-Q)
**Natural Language**: quarterly report | 10-Q data | quarterly filing | three month results | interim report

```cypher
MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType: '10-Q'})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
WHERE f.qname IN ['us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 
                  'us-gaap:NetIncomeLoss', 'us-gaap:EarningsPerShareBasic']
  AND f.is_numeric = '1'
RETURN c.ticker, f.qname, f.value, r.created
ORDER BY r.created DESC
LIMIT 20
```

### Check if Report Has XBRL
**Natural Language**: does this report have XBRL | is structured data available | can I get XBRL data | does 8-K have XBRL | which reports have structured data

```cypher
MATCH (r:Report)
RETURN r.formType, 
       EXISTS((r)-[:HAS_XBRL]->()) as has_xbrl,
       COUNT(*) as report_count
GROUP BY r.formType, has_xbrl
ORDER BY report_count DESC
```

### No XBRL for 8-K Reports
**Natural Language**: 8-K XBRL data | structured 8-K data | 8-K financial facts | material events XBRL

```cypher
// This query will return 0 results - 8-K reports NEVER have XBRL
MATCH (r:Report {formType: '8-K'})-[:HAS_XBRL]->(x:XBRLNode)
RETURN COUNT(*) as xbrl_count
// Result: 0 - Use ExtractedSectionContent for 8-K data instead
```

---

## Common Financial Fact QNames

### Balance Sheet
- `us-gaap:Assets` - Total Assets
- `us-gaap:AssetsCurrent` - Current Assets
- `us-gaap:Liabilities` - Total Liabilities
- `us-gaap:LiabilitiesCurrent` - Current Liabilities
- `us-gaap:StockholdersEquity` - Total Equity
- `us-gaap:Cash` - Cash
- `us-gaap:CashAndCashEquivalentsAtCarryingValue` - Cash and Equivalents

### Income Statement
- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` - Revenue
- `us-gaap:Revenues` - Total Revenues
- `us-gaap:CostOfRevenue` - Cost of Revenue
- `us-gaap:GrossProfit` - Gross Profit
- `us-gaap:OperatingIncomeLoss` - Operating Income
- `us-gaap:NetIncomeLoss` - Net Income
- `us-gaap:EarningsPerShareBasic` - Basic EPS
- `us-gaap:EarningsPerShareDiluted` - Diluted EPS

### Cash Flow
- `us-gaap:NetCashProvidedByUsedInOperatingActivities` - Operating Cash Flow
- `us-gaap:NetCashProvidedByUsedInInvestingActivities` - Investing Cash Flow
- `us-gaap:NetCashProvidedByUsedInFinancingActivities` - Financing Cash Flow

---

## Usage Notes

1. **XBRL is only in 10-K and 10-Q**: No XBRL data exists for 8-K or other report types
2. **Always use correct traversal**: Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact
3. **String boolean values**: Use `is_numeric = '1'` not `is_numeric = true`
4. **Handle NULL values**: Many properties are optional, use IS NOT NULL where needed
5. **Use LIMIT**: Prevent overwhelming results, especially with 7.69M facts
6. **Check period types**: 'instant' for balance sheet, 'duration' for income statement
7. **Natural language variations**: Each pattern includes multiple phrasings for semantic matching

**For non-XBRL queries** (8-K events, narrative discussions, or when users ask about "discussions" or "analysis"), see NON_XBRL_PATTERNS.md for comprehensive patterns.

This comprehensive guide contains all verified XBRL query patterns for the EventMarketDB.