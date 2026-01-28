# News Impact Skill Plan

## Date: 2026-01-22

---

## Goal

Identify what drives stock price moves with maximum **accuracy**, **comprehensiveness**, and **confidence** - so downstream agents know exactly what moved prices.

---

## Architecture

```
/news-impact (TICKER, START_DATE, END_DATE, [THRESHOLD])
    │
    ├─→ /get-bz-news → News with |daily_adj| >= 1.5σ (default)
    │
    ├─→ Analyze title+body+market_session → driver + confidence
    │
    └─→ Gap days (big move, ZERO news):
            │
            ├─→ WebSearch first → find 2+ corroborating sources
            │       │
            │       ├─→ 2+ sources agree → accept (confidence based on agreement)
            │       └─→ <2 sources → escalate to Perplexity
            │
            └─→ Perplexity (fallback) → search → reason → research
```

**Threshold:** Volatility-adjusted (1.5σ of trailing adjusted returns)

**Skills:** 2 total
- `/news-impact` - orchestrator
- `/get-bz-news` - data layer (replaceable when Benzinga ends)

---

## Arguments

| # | Argument | Required | Default | Description |
|---|----------|----------|---------|-------------|
| 1 | TICKER | Yes | - | Company ticker (e.g., AAPL) |
| 2 | START_DATE | Yes | - | Window start datetime |
| 3 | END_DATE | Yes | - | Window end datetime |
| 4 | THRESHOLD | No | `1.5s` | `1.5s`, `2s` (sigma) or `3` (fixed %) |

**Note:** Fiscal quarter calculation happens in orchestrator, not here.

---

## Volatility-Based Thresholds

### Why Sigma?

A 3% move means different things for different stocks:
- AAPL (low vol ~1.5%): 3% = 2σ (unusual)
- GBX (high vol ~2.9%): 3% = 1σ (normal)

### Calculation

**Sigma of ADJUSTED returns** (stock - SPY), not raw returns:
- Calculated over **trailing 252 days** (or available, min 60 days)
- Period ends at **START_DATE** (point-in-time compliant)
- Applied to adjusted returns during analysis period

```cypher
MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= date($start) - duration('P365D') AND d.date < date($start)
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE r.daily_return IS NOT NULL AND m.daily_return IS NOT NULL
RETURN stdev(r.daily_return - m.daily_return) AS adj_vol
```

### Universe Analysis (2024, 796 companies)

| Threshold | News Captured | Per Company/Year | Per Quarter |
|-----------|---------------|------------------|-------------|
| 1.0 sigma | 38.4% | ~33 | ~8 |
| **1.5 sigma** | **26.0%** | **~22** | **~5-6** |
| 2.0 sigma | 19.4% | ~17 | ~4 |

**Recommendation:** 1.5σ balances comprehensiveness with signal quality.

### Volatility Distribution

| Percentile | Daily Vol | 1.5σ Threshold |
|------------|-----------|----------------|
| p25 (low vol) | 1.60% | 2.4% |
| Median | 2.17% | 3.3% |
| p75 (high vol) | 3.11% | 4.7% |

---

## Market Session Analysis

Use `market_session` to assess causation vs explanation:

| Session | Interpretation | Confidence Impact |
|---------|---------------|-------------------|
| `pre_market` | News likely CAUSED the day's move | HIGH |
| `in_market` | News aligns with intraday action | MEDIUM-HIGH |
| `post_market` | News EXPLAINS today's move, but **impacts NEXT trading day** | MEDIUM (reactive) |

**Post-market note:** After-hours news (earnings, guidance changes, etc.) will move the stock at next market open. When analyzing, associate post_market news with the NEXT day's return, not today's.

---

## Output Format

```
date|news_id|driver|confidence|daily_stock|daily_adj|sector_adj|industry_adj|z_score|volatility|market_session|source
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | datetime | Yes | Event timestamp |
| news_id | string | Yes | Neo4j ID or URL(s) for external research |
| driver | string | Yes | Short phrase (5-15 words) explaining move |
| confidence | int | Yes | 0-100% certainty |
| daily_stock | float | Yes | Raw daily return |
| daily_adj | float | Yes | daily_stock - daily_macro (vs SPY) |
| sector_adj | float | No | daily_stock - daily_sector (idiosyncratic vs sector) |
| industry_adj | float | No | daily_stock - daily_industry (idiosyncratic vs industry) |
| z_score | float | Yes | How many sigmas (e.g., 2.1) |
| volatility | float | Yes | Trailing adjusted vol used |
| market_session | string | No | pre_market / in_market / post_market |
| source | string | Yes | neo4j, websearch, or perplexity |

**Move Type Interpretation:**
- If |daily_adj| >> |sector_adj| → Sector-driven (not company-specific)
- If |sector_adj| ≈ |industry_adj| ≈ |daily_adj| → Idiosyncratic (company-specific)
- If all small but daily_stock large → Market beta

**All returns, volatility, and z-scores calculated in Cypher, NOT by LLM.**

---

## Skills

### /get-bz-news (context: fork)

**Purpose:** Fetch Benzinga news with significant returns

**Tools:** `mcp__neo4j-cypher__read_neo4j_cypher`

**Filter:** |daily_adj| >= 1.5σ (default) of trailing adjusted returns
**Output:** daily returns with z_score and volatility

**Fallback:** If < 60 days history, use fixed 3% threshold

---

### /news-impact (context: fork)

**Purpose:** Orchestrate news analysis + gap research

**Tools:** `Skill`, `mcp__neo4j-cypher__read_neo4j_cypher`, `WebSearch`, Perplexity MCP (fallback)

**Flow:**
1. `/get-bz-news` → news with |daily_adj| >= 1.5σ
2. Analyze title+body+session → driver + confidence
3. Direct Cypher → daily returns for gap detection (same σ threshold)
4. For gap days (big move, no news):
   - **WebSearch first** → search "{TICKER} stock {DATE} news"
   - Validate across **2+ independent sources** before accepting
   - If 2+ sources corroborate → accept with confidence based on source agreement
   - If <2 sources → escalate to Perplexity (search → reason → research)
5. Merge and return

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Threshold type | **Volatility-adjusted (σ)** | 3% means different things for different stocks |
| Sigma base | Adjusted returns (stock - SPY) | We filter on adjusted, sigma should match |
| Trailing period | 252 days before START_DATE | PIT-compliant, stable estimate |
| Minimum history | 60 days | Fall back to 3% if insufficient |
| Default sigma | 1.5σ | ~26% of moves, ~5-6 per quarter |
| Market session | Inform confidence | pre_market = causal, post_market = next day impact |
| Skill layers | /get-bz-news separate | Replaceable when Benzinga ends |
| Returns | Calculated in Cypher | Accuracy, not LLM math |
| Driver extraction | Title + BODY + session | Context matters |
| Gap research | WebSearch first | Multi-source validation before accepting |
| Source validation | 2+ sources required | Higher confidence with corroboration |
| Perplexity | Fallback only | If WebSearch finds <2 sources |

---

## NULL Handling

- If < 60 days trailing history → fall back to fixed 3% threshold
- If `daily_stock` or `daily_macro` NULL → skip (rare)
- If `sector/industry` NULL → leave empty (rare)

---

## Gap Detection

```cypher
// Calculate trailing adjusted volatility
MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= date($start) - duration('P365D') AND d.date < date($start)
MATCH (d)-[m:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WHERE r.daily_return IS NOT NULL AND m.daily_return IS NOT NULL
WITH c, stdev(r.daily_return - m.daily_return) AS adj_vol

// Find significant move days
MATCH (d2:Date)-[r2:HAS_PRICE]->(c)
WHERE d2.date >= $start AND d2.date < $end
MATCH (d2)-[m2:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
WITH d2.date AS date,
     r2.daily_return AS stock,
     m2.daily_return AS macro,
     (r2.daily_return - m2.daily_return) AS daily_adj,
     adj_vol
WHERE abs(daily_adj) >= 1.5 * adj_vol
RETURN date, stock, macro, daily_adj, adj_vol,
       abs(daily_adj) / adj_vol AS z_score
ORDER BY date
```

Compare with news-explained dates. Gap = big move with no news.

---

## Post-Implementation

- [x] Review against `.claude/plans/Infrastructure.md` best practices
- [ ] Test with multiple tickers (sigma-based)
- [ ] Verify WebSearch → Perplexity escalation works correctly
- [ ] Verify 2+ source validation logic

---

## Example Output

### CDLX (4σ threshold, --no-perplexity)

> **Note:** Output not exactly as expected - format and structure need refinement. Only ran for Q1 and Q2 (first two earnings) before being stopped.

```
/earnings-orchestrator CDLX 4s --no-perplexity
```

**Ticker:** CDLX
**Sigma Threshold:** 4s (fell back to 3% fixed due to insufficient trailing history)
**Perplexity:** Disabled (--no-perplexity)

#### Earnings Parsed

| Earnings | Accession | Date | Session | Daily Return |
|----------|-----------|------|---------|--------------|
| E1 | 0001666071-23-000026 | 2023-03-01 | post_market | -8.49% |
| E2 | 0001666071-23-000045 | 2023-04-04 | pre_market | +79.48% |

#### Q1 Period (2022-12-01 to 2023-03-01)

- **Effective data range:** 2023-01-03 to 2023-03-01
- **Significant move days:** 28
- **News coverage:** 2 days (7%)
- **Gap days:** 26 (93%)
- **Notable gaps:** +14.90% (Jan 26), +12.21% (Feb 2), +11.84% (Jan 27)

#### Q2 Period (2023-03-01 to 2023-04-04)

- **Significant move days:** 16
- **News coverage:** 4 events on 4 days (25%)
- **Gap days:** 12 (75%)
- **High-confidence events:**
  - 2023-03-02: Q4 earnings miss + weak guidance (-9.43%, 85% confidence)
  - 2023-03-14: $30M credit draw from Pacific Western (-4.59%, 70% confidence)
  - 2023-03-22: CFO resignation (-13.49%, 80% confidence)
  - 2023-04-04: Q1 guidance raise (+81.42%, 95% confidence, 13.44 sigma)
- **Notable gaps:** +15.80% (Mar 21), +12.90% (Mar 31), +8.17% (Mar 29)

#### Observations

1. CDLX had extremely volatile Q1-Q2 2023 period with 80%+ single-day move on guidance raise
2. March 2023 banking crisis (SVB) impacted stock but news attribution unclear for gap days
3. Benzinga coverage sparse in Q1 period (only 2 articles)
4. Re-run without `--no-perplexity` to research the 38 total gap days

---

*Last updated: 2026-01-23 (added WebSearch-first, post_market next-day note)*
