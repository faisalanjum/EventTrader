## Cypher Query to Reproduce

```cypher
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
WHERE r.formType = '8-K' 
  AND r.items CONTAINS '2.02'
  AND pf.hourly_stock IS NOT NULL 
  AND pf.hourly_macro IS NOT NULL
  AND pf.daily_stock IS NOT NULL 
  AND pf.daily_macro IS NOT NULL
  AND ABS(pf.hourly_stock - pf.hourly_macro) > 3
  AND SIGN(pf.hourly_stock - pf.hourly_macro) = SIGN(pf.daily_stock - pf.daily_macro)
  AND ABS(pf.daily_stock - pf.daily_macro) > ABS(pf.hourly_stock - pf.hourly_macro)
RETURN r.id AS accession_no, 
       c.ticker AS ticker,
       c.name AS company_name, 
       r.description AS description,
       r.items AS items,
       r.periodOfReport AS report_date,
       r.created AS filed_at,
       c.mkt_cap AS market_cap,
       round((pf.hourly_stock - pf.hourly_macro) * 100) / 100 AS hourly_adj_return,
       round((pf.daily_stock - pf.daily_macro) * 100) / 100 AS daily_adj_return
ORDER BY daily_adj_return DESC
```



---

## Return Distribution Summary

| Metric            | Hourly Adj Return | Daily Adj Return |
|-------------------|-------------------|------------------|
| Count             |             1,298 |            1,298 |
| Positive          |         611 (47.1%) |        611 (47.1%) |
| Negative          |         687 (52.9%) |        687 (52.9%) |
| Min               |           -56.25% |          -77.56% |
| Max               |            53.27% |           84.14% |
| Mean              |            -0.73% |           -0.81% |
| Median            |            -3.19% |           -5.06% |

## Distribution by Bracket

| Bracket         | Hourly Adj |     % | Daily Adj |     % |
|-----------------|------------|-------|-----------|-------|
| < -50%          |          1 |   0.1% |         5 |   0.4% |
| -50% to -30%    |          5 |   0.4% |        48 |   3.7% |
| -30% to -20%    |         12 |   0.9% |        96 |   7.4% |
| -20% to -10%    |        108 |   8.3% |       291 |  22.4% |
| -10% to -5%     |        261 |  20.1% |       211 |  16.3% |
| -5% to 0%       |        300 |  23.1% |        36 |   2.8% |
| 0% to +5%       |        276 |  21.3% |        39 |   3.0% |
| +5% to +10%     |        250 |  19.3% |       165 |  12.7% |
| +10% to +20%    |         79 |   6.1% |       272 |  21.0% |
| +20% to +30%    |          5 |   0.4% |        85 |   6.5% |
| +30% to +50%    |          0 |   0.0% |        45 |   3.5% |
| > +50%          |          1 |   0.1% |         5 |   0.4% |

**Selection Criteria:** 8-K Item 2.02 (Earnings) | Hourly adj return > ±3% | Daily continues same direction with larger magnitude

**Data:** `8k_fact_universe.csv` — 1,298 reports across 499 companies

