# Risk-Driven Trading Signals — Methodology & Results

## What We Built (2026-04-06)

A system that links SEC 10-K risk factor disclosures to news events via vector embeddings, then measures the stock's macro-adjusted return on those news days. This reveals which disclosed risks actually move each company's stock, by how much, and in which direction.

## Pipeline (3 scripts)

### Script 1: `ingest_massive_risk_factors.py`
- Pulls risk factor classifications from Massive API (665 of 796 companies covered)
- Creates two node types in Neo4j:
  - **RiskCategory** (140 nodes) — fixed 3-tier taxonomy (7 primary → 28 secondary → 140 tertiary)
  - **RiskClassification** (29,588 nodes) — per-company per-filing risk instances with `supporting_text`
- Links: `ExtractedSectionContent -[:HAS_RISK_CLASSIFICATION]-> RiskClassification -[:CLASSIFIED_AS]-> RiskCategory`
- Generates OpenAI `text-embedding-3-large` (3072-dim) embeddings for each node's `supporting_text`
- Stores embeddings on nodes + creates `risk_classification_vector` index
- Idempotent: re-run safely — MERGE for nodes, `WHERE embedding IS NULL` for embeddings
- Flags: `--write` (required), `--skip-pull` (use cached JSON), `--ticker AAPL` (single test)

### Script 2: `driver_strategy_scan.py`
- Reads embeddings from Neo4j (zero OpenAI cost)
- Scans all 507 companies × 16 risk categories = 5,005 pairs
- For each pair: vector search against news → compute macro-adjusted returns → score
- Score formula: `avg_return × sqrt(count) / (stdev + 0.5)`
- Outputs ranked strategy tables + saves to `driver_strategy_results.json`

### Script 3: `driver_matrix_clean.py`
- Numpy-accelerated: loads embeddings + news into memory, cosine similarity via matmul
- 17 Neo4j queries total (1 for risks + 16 for news) instead of 256 vector searches
- Outputs 3 visual 16×16 matrices: avg return, news count, return range

## Key Design Decisions

### Why company-specific embeddings, not generic category descriptions
Generic category descriptions (e.g., "Risk from currency fluctuations...") scored 0.64-0.67 similarity to news. Company-specific `supporting_text` (e.g., DAL's "Fuel costs represented 17% of our operating expense") scored 0.77-0.79. The company's own words match news about them far better.

### Similarity threshold
- Neo4j vector search returns `(1 + cosine) / 2` — so Neo4j 0.75 = cosine 0.50
- Neo4j 0.75-0.77 is the sweet spot: enough matches for statistical validity, not so loose that noise dominates
- At 0.85+, almost no matches (cosine 0.70+ is extremely strict for cross-domain text)

### Returns are macro-adjusted
Every return = `daily_stock - daily_macro` (stock return minus S&P 500 return). This isolates company-specific reaction from market-wide movement.

### Span matching for future LLM-free classification
`span_start`/`span_end` on RiskClassification nodes locate the supporting_text within the ExtractedSectionContent. Smart quote normalization (Unicode → ASCII) achieved 89-95% span match rate.

## Results: Tradeable Signals (2026-04-06)

### 100% Win Rate (every matching news day moved in expected direction)

| Signal | Direction | News Count | Avg Return | Range | Win Rate | Optimal Neo4j Threshold |
|--------|-----------|------------|------------|-------|----------|------------------------|
| TSLA × AI | SHORT | 4 | -9.17% | [-12.4%, -1.8%] | 100% | 0.76 |
| AMZN × Regulat | SHORT | 8 | -1.59% | [-2.5%, -0.2%] | 100% | 0.76 |
| BAX × M&A | SHORT | 3 | -9.39% | [-10.0%, -8.2%] | 100% | 0.75 |
| CROX × M&A | SHORT | 4 | -10.96% | [-12.2%, -7.2%] | 100% | 0.75 |

### 80-89% Win Rate (strong edge, larger sample)

| Signal | Direction | News Count | Avg Return | Range | Win Rate | Optimal Neo4j Threshold |
|--------|-----------|------------|------------|-------|----------|------------------------|
| F × Labor | SHORT | 28 | -2.30% | [-11.2%, +1.1%] | 89% | 0.78 |
| JBLU × OilMtrl | SHORT | 16 | -8.06% | [-20.0%, +1.5%] | 81% | 0.78 |
| TSLA × OilMtrl | LONG | 5 | +3.33% | [-0.1%, +7.3%] | 80% | 0.77 |
| DAL × OilMtrl | SHORT | 5 | -2.18% | [-6.1%, +2.0%] | 80% | 0.77 |

### 67-75% Win Rate (moderate edge)

| Signal | Direction | News Count | Avg Return | Range | Win Rate | Optimal Neo4j Threshold |
|--------|-----------|------------|------------|-------|----------|------------------------|
| AAL × Labor | SHORT | 4 | -2.18% | [-5.6%, +0.1%] | 75% | 0.79 |
| OXY × Climate | SHORT | 4 | -1.01% | [-3.4%, +1.6%] | 75% | 0.75 |
| TSLA × Tariff | SHORT | 15 | -2.09% | [-8.2%, +4.8%] | 67% | 0.76 |
| UPS × Labor | SHORT | 12 | -0.70% | [-2.2%, +1.2%] | 67% | 0.77 |

### Per-Category Insights (across all 507 companies)

| Category | Signals | Avg of Avgs | Interpretation |
|----------|---------|-------------|----------------|
| IntRate | 6 | -3.37% | Hardest-hitting driver |
| Climate | 13 | -1.86% | ESG news consistently negative |
| Margin | 28 | -1.48% | Margin pressure = negative |
| Cyber | 6 | -0.97% | Breach news = ~1% hit |
| Tariff | 16 | -0.74% | Trade war = drag |
| OilMtrl | 22 | -0.58% | Mixed — positive for EVs, negative for users |
| IP | 5 | +1.48% | Patent enforcement = positive (unexpected) |

## Schema Summary

```
Company ←[:PRIMARY_FILER]- Report -[:HAS_SECTION]→ ExtractedSectionContent -[:HAS_RISK_CLASSIFICATION]→ RiskClassification -[:CLASSIFIED_AS]→ RiskCategory
                                                    {section_name: "RiskFactors"}                        {embedding: [3072 dims]}                  {140 nodes}
                                                                                                          {supporting_text, span_start, span_end}
```

**Indexes:**
- `constraint_riskcategory_id` — unique on RiskCategory.id
- `constraint_riskclassification_id` — unique on RiskClassification.id
- `index_riskclassification_ticker` — range on ticker
- `index_riskclassification_filing_date` — range on filing_date
- `risk_classification_vector` — vector index (3072 dims, cosine) on embedding

**Node counts:** 140 RiskCategory + 29,588 RiskClassification + 29,588 embeddings

## Data Sources

- **Massive API** (`/stocks/filings/vX/risk-factors` + `/stocks/taxonomies/vX/risk-factors`) — risk classifications
- **Neo4j News nodes** (344,532 with embeddings) — news articles with `INFLUENCES` relationship to Company
- **OpenAI text-embedding-3-large** — 3072-dim embeddings for both risk text and news

## Cached Data Files

- `taxonomy.json` — 140 risk categories with descriptions
- `classifications.json` — 46,990 classifications across 665 tickers
- `driver_strategy_results.json` — 251 valid signals from full scan
- `ingest_results.json` — ingestion validation stats

## Future Work

1. **Automatic driver detection**: Given a new news article, search `risk_classification_vector` index to find which companies' disclosed risks it matches → automatic alert
2. **10-Q risk deltas**: Classify 10-Q risk factors using Massive's labeled data as few-shot training (text matching on existing supporting_text corpus)
3. **News → Risk linking in Neo4j**: Create `News -[:TRIGGERS_RISK]-> RiskClassification` relationships for top signals
4. **Dynamic thresholds**: Per-company optimal threshold (volatile stocks need higher thresholds)
5. **Integration with earnings prediction**: Use risk classifications as features in the prediction model
