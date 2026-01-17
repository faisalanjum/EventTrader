# Orchestrator Queries

## Get 8-Ks for Ticker

```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE c.ticker = $ticker
  AND r.formType = '8-K'
  AND any(item IN r.items WHERE item CONTAINS 'Item 2.02')
  AND pf.daily_stock IS NOT NULL
RETURN r.accessionNo AS accession_no,
       c.ticker AS ticker,
       c.name AS company_name,
       r.created AS filing_datetime,
       pf.daily_stock AS daily_return,
       pf.daily_macro AS macro_adj_return
ORDER BY r.created ASC
```

## Count by Ticker

```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE r.formType = '8-K'
  AND any(item IN r.items WHERE item CONTAINS 'Item 2.02')
  AND pf.daily_stock IS NOT NULL
RETURN c.ticker AS ticker, count(*) AS count
ORDER BY count DESC
LIMIT 20
```
