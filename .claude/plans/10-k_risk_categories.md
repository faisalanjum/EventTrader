# 10-K Risk Categories — Plan & Reference

## Overview

SEC 10-K filings contain Item 1A (Risk Factors) — a 20-50 page section where companies disclose every risk they face. We pulled Massive API's pre-classified version of these risks (mapped to a standardized 140-category taxonomy), stored them in Neo4j, generated vector embeddings for each, and used those embeddings to match company-specific risks against news articles to measure actual stock impact per risk driver.

## Scripts

### 1. `scripts/ingest_massive_risk_factors.py`

**Purpose:** Pull risk classifications from Massive API → store in Neo4j → generate embeddings

**Flags:**
- `--write` — required to actually write to Neo4j (default is dry-run)
- `--skip-pull` — use cached JSON from prior API pull (saves ~3 min)
- `--ticker AAPL` — process single ticker for testing
- `--pull-only` — only download from Massive, don't write

**Phases:**
1. Pull taxonomy (140 categories) + classifications (~47K) from Massive API → save to local JSON
2. Validate matches against Neo4j (match by CIK + filing date ±5 days + formType 10-K/10-K/A)
3. Write to Neo4j: RiskCategory nodes, RiskClassification nodes, relationships
4. Embed all RiskClassification nodes where `embedding IS NULL` (OpenAI text-embedding-3-large, 3072 dims)

**When to run:** After new 10-K filings are ingested. Re-runnable safely (MERGE + WHERE embedding IS NULL).

**API key:** Uses `POLYGON_API_KEY` from `.env` for Massive API. Uses `OPENAI_API_KEY` for embeddings.

**Rollback:** `MATCH (n:RiskClassification) DETACH DELETE n; MATCH (n:RiskCategory) DETACH DELETE n;`

### 2. `scripts/driver_strategy_scan.py`

**Purpose:** Scan all companies × 16 risk categories, rank trading strategies by composite score

**No OpenAI calls** — reads embeddings from Neo4j.

**Score formula:** `avg_return × sqrt(count) / (stdev + 0.5)` — rewards high avg return, many news, low volatility

**Output:** Ranked strategy tables (long, short, consistent, high-confidence) + saves to `driver_strategy_results.json`

### 3. `scripts/driver_matrix_clean.py`

**Purpose:** Visual 16×16 matrix (companies × risk categories) showing avg return, news count, and return range

**No OpenAI calls** — reads embeddings from Neo4j. Numpy-accelerated: loads all data into memory, computes cosine similarity via matmul. 17 Neo4j queries total instead of 256 vector searches. Runs in ~55 seconds.

**Configurable:** Edit `T` (ticker list) and `CATS` (category list) at top of file. Edit `NEO4J_SIM` threshold.

## Neo4j Schema (additive — nothing existing changed)

### New Nodes

**RiskCategory (140 nodes)**
```
Properties: id (unique), primary_category, secondary_category, tertiary_category, description, taxonomy_version
```

**RiskClassification (29,588 nodes)**
```
Properties: id (unique), cik, ticker, filing_date, primary_category, secondary_category, tertiary_category,
            supporting_text, span_start, span_end, source, embedding (3072 floats)
```

- `id` format: `{cik}_{filing_date}_{tertiary_category}` (deterministic, idempotent)
- `supporting_text`: verbatim quote from the company's Item 1A section
- `span_start`/`span_end`: character offsets into `ExtractedSectionContent.content` (-1 if no match)
- `source`: "massive" (provenance — vs future "self" classifications)
- `embedding`: OpenAI text-embedding-3-large output for the supporting_text

### New Relationships

- `ExtractedSectionContent -[:HAS_RISK_CLASSIFICATION]-> RiskClassification`
- `RiskClassification -[:CLASSIFIED_AS]-> RiskCategory`

### Full traversal path
```
Company ←[:PRIMARY_FILER]- Report -[:HAS_SECTION]→ ExtractedSectionContent -[:HAS_RISK_CLASSIFICATION]→ RiskClassification -[:CLASSIFIED_AS]→ RiskCategory
```

### Indexes
- `constraint_riskcategory_id` — unique on RiskCategory.id
- `constraint_riskclassification_id` — unique on RiskClassification.id
- `index_riskclassification_ticker` — range on ticker
- `index_riskclassification_filing_date` — range on filing_date
- `risk_classification_vector` — vector index (3072 dims, cosine) on embedding

## Taxonomy Structure

140 categories organized in 3 tiers:

| Primary (7) | Secondary (28) | Tertiary (140) |
|---|---|---|
| external_and_systemic | economic_and_market_conditions, geopolitical_and_trade, natural_and_catastrophic_events, social_and_demographic | 22 |
| financial_and_market | capital_structure_and_performance, credit_and_liquidity, international_and_currency, market_and_investment | 20 |
| governance_and_stakeholder | corporate_governance, organizational_and_management, reputation_and_brand, stakeholder_relations | 19 |
| operational_and_execution | core_operations, human_capital_and_workforce, project_and_contract_management, supply_chain_and_procurement | 19 |
| regulatory_and_compliance | data_and_privacy, industry_regulation, legal_and_litigation, tax_and_financial_reporting | 23 |
| strategic_and_competitive | customer_and_revenue, innovation_and_product_development, market_position_and_competition, strategic_execution | 19 |
| technology_and_information | cybersecurity_and_data_protection, digital_transformation_and_innovation, information_management, technology_infrastructure | 18 |

Taxonomy source: Massive API (`/stocks/taxonomies/vX/risk-factors`). Cached in `scripts/massive_risk_data/taxonomy.json`.

## How It Links Together

Each company's 10-K has one Item 1A section (a wall of text with ~15-30 distinct risks). Massive decomposes that text into individual risk paragraphs and classifies each into one of the 140 categories. We store each classification as a separate `RiskClassification` node hanging off the `ExtractedSectionContent` node for that section.

```
Report (AAPL 10-K 2024)
  └─[:HAS_SECTION]→ ExtractedSectionContent {section_name: "RiskFactors", content: "42K chars..."}
                       ├─[:HAS_RISK_CLASSIFICATION]→ RiskClassification {supporting_text: "foreign exchange...", embedding: [...]}
                       │                                └─[:CLASSIFIED_AS]→ RiskCategory {id: "foreign_exchange_and_currency_exposure"}
                       ├─[:HAS_RISK_CLASSIFICATION]→ RiskClassification {supporting_text: "supply chain...", embedding: [...]}
                       │                                └─[:CLASSIFIED_AS]→ RiskCategory {id: "raw_material_availability_and_cost_volatility"}
                       └─ ... ~25 more
```

The RiskCategory nodes are shared — AAPL's and TSLA's "foreign exchange" classifications both point to the same RiskCategory node. This enables cross-company queries.

## Embeddings — Why and How

Each RiskClassification node's `supporting_text` is embedded with OpenAI `text-embedding-3-large` (3072 dimensions). The embedding is stored directly on the node.

**Why company-specific text, not generic category descriptions:** We tested both. Generic category descriptions scored 0.64-0.67 cosine similarity to matching news. Company-specific supporting_text scored 0.77-0.79. The company's own words ("Fuel costs represented 17% of our operating expense") match news about them ("Delta fuel costs hurt Q4") far better than the abstract category description ("Risk from fluctuations in raw material costs").

**Why embed all 29,588 nodes (not just latest per company):** Each filing year has slightly different text (companies update risk language). Embedding all preserves temporal signal. Storage: ~355MB across 253GB cluster RAM.

**Vector index:** `risk_classification_vector` on Neo4j enables reverse lookup — given a news article, find which companies' disclosed risks it matches.

**Similarity scoring:** Neo4j vector search returns `(1 + cosine) / 2`. So Neo4j score 0.75 = raw cosine similarity 0.50. The numpy scripts convert accordingly.

## Span Matching

`span_start` and `span_end` on each RiskClassification are character offsets locating the `supporting_text` within the parent `ExtractedSectionContent.content`. This enables future LLM-free classification:

1. New 10-K arrives → extract RiskFactors section (existing pipeline)
2. Split into paragraphs
3. Fuzzy-match each paragraph against existing `supporting_text` values (full-text index)
4. Match found (~80% of risks are copy-pasted year-over-year) → use same category, compute new span
5. No match → LLM classify using taxonomy + few-shot examples from existing labeled data

Smart quote normalization (`\u2019` → `'`) achieved 89-95% span match rate. Remaining misses are from text extraction differences between Massive and our parser.

## Coverage

| Metric | Count |
|---|---|
| Companies in our DB | 796 |
| Massive covers | 665 (83.5%) |
| Both have data (linkable) | 507 companies |
| Total RiskClassification nodes | 29,588 |
| Classifications linked to sections | 29,588 |
| Embeddings generated | 29,588 |
| Sections matched (of 46,990 from Massive) | 30,309 (64.5%) |
| Unmatched (filing before our date range or not yet ingested) | 16,681 |

**Unmatched filings** are mostly pre-2023 (our data starts 2023-01-03). Re-running the script after ingesting new 10-Ks will link them automatically.

## Methodology — News-to-Risk Matching

For each company×risk pair:
1. Read the company's `supporting_text` embedding from Neo4j
2. Compute cosine similarity against all news embeddings for that company
3. Filter by threshold (Neo4j 0.75 = cosine 0.50)
4. For each matching news article, compute macro-adjusted return: `daily_stock - daily_macro` (isolates company-specific reaction from market movement)
5. Aggregate: count, avg return, stdev, min, max, win rate

**Three return timeframes available:**
- `hourly_stock/hourly_macro` — 1 hour after news
- `session_stock/session_macro` — market session window
- `daily_stock/daily_macro` — full trading day

## Results — Tradeable Signals

### Filtering criteria for highest-confidence signals:
1. Minimum 3 news matches (statistical validity)
2. Hourly AND daily returns must agree on direction (no reversal signals)
3. Ranked by combined win rate across timeframes

### 100% win rate on BOTH hourly and daily:

| Signal | Dir | Hourly (n, avg, win%) | Daily (n, avg, win%) |
|---|---|---|---|
| ALL × Weather | LONG | 5, +1.3%, 100% | 5, +2.7%, 100% |
| BAX × M&A | SHORT | 5, -2.5%, 100% | 5, -7.5%, 100% |
| SNAP × Investor | SHORT | 6, -3.7%, 100% | 6, -27.1%, 100% |
| DIS × Strategic | LONG | 5, +0.5%, 100% | 5, +2.6%, 100% |
| VC × FX | LONG | 6, +0.8%, 100% | 6, +4.7%, 100% |
| MDT × Litigation | SHORT | 5, -0.1%, 80% | 5, -0.7%, 100% |

### High win rate with larger sample:

| Signal | Dir | Hourly Win% | Daily Win% | Daily Avg | News | Key finding |
|---|---|---|---|---|---|---|
| EXPD × Inflation | SHORT | 71% | 83% | -2.9% | 24 | Best sample with dual confirmation |
| AA × OilMtrl | SHORT | 62% | 92% | -3.3% | 13 | Alcoa hit hard by commodity news |
| SNAP × Margin | SHORT | 65% | 88% | -13.5% | 17 | Margin pressure destroys Snap |
| F × Labor | SHORT | 51% (coin flip hourly) | 89% (daily) | -2.3% | 28 | Hourly is noise, daily is real — UAW effect |
| JBLU × OilMtrl | SHORT | 51% (coin flip hourly) | 81% (daily) | -8.1% | 16 | Oil news builds through the day |

### Key insight on timing:
Most signals are coin flips at hourly but strengthen by end of day. The market doesn't react instantly — the move builds over hours. Signals like TSLA × AI even go the WRONG direction hourly (+1.8%) then reverse hard by daily (-5.9%). This means there's an entry window — news hits, hourly is flat/wrong, you enter before daily close captures the full move.

### Per-category impact (across all 507 companies):

| Category | Signals | Avg of Avgs | Direction |
|---|---|---|---|
| IntRate | 6 | -3.37% | Hardest-hitting |
| Climate | 13 | -1.86% | Consistently negative |
| Margin | 28 | -1.48% | Negative |
| Cyber | 6 | -0.97% | Negative |
| Tariff | 16 | -0.74% | Negative |
| OilMtrl | 22 | -0.58% | Mixed (positive for EVs, negative for fuel users) |
| IP | 5 | +1.48% | Positive (patent enforcement = value) |

## Cached Data Files

| File | Contents |
|---|---|
| `scripts/massive_risk_data/taxonomy.json` | 140 risk categories with descriptions |
| `scripts/massive_risk_data/classifications.json` | 46,990 classifications across 665 tickers |
| `scripts/massive_risk_data/driver_strategy_results.json` | 251 valid signals from full scan |
| `scripts/massive_risk_data/ingest_results.json` | Ingestion validation stats |
| `scripts/massive_risk_data/risk_driver_methodology.md` | Earlier methodology doc |

## Cypher Query Examples

```cypher
-- All risks for a company
MATCH (s:ExtractedSectionContent)-[:HAS_RISK_CLASSIFICATION]->(rc:RiskClassification {ticker: 'AAPL'})
RETURN rc.filing_date, rc.primary_category, rc.tertiary_category, left(rc.supporting_text, 100)
ORDER BY rc.filing_date DESC, rc.primary_category

-- Which companies share a risk?
MATCH (rc:RiskClassification)-[:CLASSIFIED_AS]->(cat:RiskCategory {id: 'artificial_intelligence_and_automation'})
RETURN DISTINCT rc.ticker ORDER BY rc.ticker

-- Companies with oil exposure (via supporting_text keywords)
MATCH (rc:RiskClassification)-[:CLASSIFIED_AS]->(cat:RiskCategory {id: 'raw_material_availability_and_cost_volatility'})
WHERE rc.supporting_text CONTAINS 'oil' OR rc.supporting_text CONTAINS 'fuel'
RETURN DISTINCT rc.ticker

-- Year-over-year risk diff
MATCH (c:Company {ticker: 'AAPL'})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
MATCH (r)-[:HAS_SECTION]->()-[:HAS_RISK_CLASSIFICATION]->(rc)
WITH r.created AS filed, collect(rc.tertiary_category) AS risks ORDER BY filed
WITH collect({filed: filed, risks: risks}) AS filings
WITH filings[-2] AS prev, filings[-1] AS curr
RETURN [x IN curr.risks WHERE NOT x IN prev.risks] AS added,
       [x IN prev.risks WHERE NOT x IN curr.risks] AS dropped

-- Visual graph in Neo4j Browser
MATCH (s:ExtractedSectionContent)-[:HAS_RISK_CLASSIFICATION]->(rc:RiskClassification {ticker: 'AAPL'})-[:CLASSIFIED_AS]->(cat:RiskCategory)
WHERE rc.filing_date = '2024-11-01'
RETURN s, rc, cat
```

## Future Work

1. **Automatic driver detection:** News arrives → search `risk_classification_vector` → find which companies' disclosed risks it matches → alert
2. **10-Q risk deltas:** Classify 10-Q risk factors using Massive's labeled data as few-shot (text matching on existing supporting_text corpus, ~80% match rate without LLM)
3. **News→Risk relationships in Neo4j:** Create `News -[:TRIGGERS_RISK]-> RiskClassification` for validated signals
4. **Dynamic thresholds:** Per-company optimal similarity threshold (volatile stocks need higher)
5. **Prediction model features:** Add "has_active_driver_news" as input feature to earnings prediction pipeline
6. **Auto-trading integration:** For signals with 80%+ win rate on both hourly and daily, wire into trade daemon with session-level entry timing

## Questions & Answers from Design Session

**Q: Can we use Massive's taxonomy directly?**
A: Yes. We pulled all 140 categories via their API. Free beta access for any account type ("may change in the future").

**Q: What if Massive stops their service?**
A: We already have 29,588 labeled examples (supporting_text → category). These serve as a few-shot training set for self-classification. Companies reuse ~80% of risk factor language year-over-year, so simple text matching handles most cases. Only genuinely new risks need LLM classification.

**Q: Does this work for 10-Q?**
A: Same taxonomy applies. 10-Q Part 2, Item 1A uses identical risk categories. Massive only covers 10-K; we'd self-classify 10-Q using existing labeled data. Zero extra effort on taxonomy — just run classification on 10-Q sections.

**Q: How do we link to specific sections?**
A: `RiskClassification` hangs off `ExtractedSectionContent` (the RiskFactors section), not the Report. This is semantically correct — the classifications are decompositions of that specific section's text. The `span_start`/`span_end` properties pin each quote to its exact character offset in the section content.

**Q: Is this useful for the prediction pipeline?**
A: Not directly for earnings prediction (which uses 8-K data). But it enables driver identification — "which macro factors should we weight for this company based on their disclosed risks?" This is a feature engineering input, not a direct predictor.

**Q: Should we auto-trade these signals?**
A: Not yet. Win rates are promising (up to 100%) but sample sizes are small (3-28 news). Need more data, proper backtesting with entry/exit timing, and paper trading before live. The hourly vs daily analysis shows most signals build over the day (not instant), meaning there's an entry window but also execution risk.
