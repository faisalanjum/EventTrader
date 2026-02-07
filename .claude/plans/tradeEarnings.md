# tradeEarnings

## Entry Point

**earnings-orchestrator** - triggers all workflows per report

Historical report generation flow:
1. Fetches 8-K reports for a company with Item 2.02 (earnings announcements)
   <details>
   <summary><b>8-K Fetch Query ▶</b></summary>

   ```cypher
   MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company)
   WHERE c.ticker = $ticker
     AND r.formType = '8-K'
     AND r.items CONTAINS '2.02'
     AND pf.daily_stock IS NOT NULL
   RETURN r.accessionNo, c.ticker, r.created, pf.daily_stock
   ORDER BY r.created ASC
   ```
   - `Item 2.02` = "Results of Operations and Financial Condition" (earnings)
   - `pf.daily_stock IS NOT NULL` = has return data for analysis

   </details>
2. Sorts by publish date ascending (oldest first)
3. Processes reports chronologically — each report triggers workflows

## Per-Company Files

Two cumulative files per company (not per quarter):
- `{ticker}/news-impact.md` — cumulative news inventory
- `{ticker}/guidance-inventory.md` — cumulative guidance time series (financial + non-financial)

<details>
<summary><b>Trigger Chain ▶</b></summary>

```
User provides $ticker (or auto-trigger on 8-K ingestion)
         ↓
   earnings-orchestrator
         ↓
   Fetches all 8-K (Item 2.02) → sorted by r.created ASC
         ↓
   For each report:
         │
         ├── q=1:  news-impact (init) ────────┐
         │         guidance-inventory (init) ─┴──→ attribution(q1)
         │
         │
         └── q≥2:  news-impact (update) ───┐
                   guidance-inventory ─────┼──→ prediction(q) ──→ attribution(q)
                   prior attributions ─────┘                            │
                                                                        ↓
                                                             updates guidance-inventory
```

</details>

<details>
<summary><b>Workflow Diagram — per report, q ≥ 2 ▶</b></summary>

```
┌───────────┐            ┌─────────────────────┐
│ attr(q-1) │            │    news-impact      │
├───────────┤            │    (cumulative)     │
│ attr(q-2) │            ├─────────────────────┤
├───────────┤            │ guidance-inventory  │◀───────────────┐
│    ...    │            │    (cumulative)     │                │
├───────────┤            └──────────┬──────────┘                │
│ attr(1)   │                       │                           │ updates
└─────┬─────┘           ┌───────────┴───────────┐               │
      │                 │                       │               │
      ▼                 ▼                       ▼               │
┌─────────────────────────┐         ┌────────────────────┐      │
│     prediction(q)       │────────▶│   attribution(q)   │──────┘
└─────────────────────────┘         └────────────────────┘
(q = quarter)

For q=1: news-impact + guidance-inventory → attribution only (no prediction)
```

</details>

**Flow per report:**

For q=1 (first report):
1. Initial build: news-impact + guidance-inventory from all available historical data
2. Run attribution(q1) — updates guidance-inventory

For q≥2:
1. Update news-impact (add q-1→q window, using `r.created` publish dates)
2. Run prediction(q) — reads news-impact, guidance-inventory, prior attributions
3. Run attribution(q) — reads everything, updates guidance-inventory with new guidance from filings

## Five Workflows

1. **earnings-prediction** — point-in-time data only, predicts outcome *(skipped for q=1)*
   - Note: PIT filtering can be toggled off for real-time prediction

2. **earnings-attribution** — full returns data, explains why, compares to prediction

3. **news-impact** — cumulative news inventory: what moved the stock (macro + company specific)
   - Single file per company, grows over time
   - q=1: all available historical data
   - q≥2: adds q-1→q window (previous `r.created` to this `r.created`) — no overlap
   - Filter: absolute daily return >= ~2-2.5% (TBD)

   <details>
   <summary><b>Data Sources ▶</b></summary>

   **Source 1: (News)-[:INFLUENCES]->(Company)** - explains WHY stock moved
   ```
   Returns matrix: {hourly|session|daily} x {stock|sector|industry|macro} = 12 properties
   + symbol, created_at
   ```
   ```cypher
   MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $ticker})
   WHERE n.published >= $startDate AND n.published < $endDate
     AND abs(r.daily_stock) >= 2.0
   RETURN n.title, n.published, r.daily_stock, r.daily_sector, r.daily_macro
   ORDER BY n.published
   ```

   **Source 2: (Date)-[:HAS_PRICE]->(Company)** - shows WHAT happened (time series)
   ```
   Properties: open, high, low, close, volume, vwap, daily_return, transactions, timestamp
   ```
   ```cypher
   MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker: $ticker})
   WHERE d.date >= $startDate AND d.date < $endDate
   RETURN d.date, r.close, r.daily_return, r.volume
   ORDER BY d.date
   ```

   **Source 3: Perplexity/web search** - fills gaps, especially macro moves

   </details>

4. **guidance-inventory** — cumulative time series of company guidance
   - Single file per company, grows over time
   - q=1: all available historical guidance
   - q≥2: updated by attribution(q-1) — no separate update step needed
   - Financial guidance (EPS, revenue, cash flow estimates)
   - Non-financial guidance (from presentation slides etc*) *TODO: not in DB yet
   - Pure data — no met/missed analysis (that's attribution's job)
   - Note: consensus estimates (analyst expectations) live in prediction/attribution reports, not here
   - **Details**: See [guidanceInventory.md](guidanceInventory.md) for types, temporal structure, FYE handling, actions, and edge cases

5. **financial-modeler** (business fundamentals) - how does the company make money, detailed financial modelling using XBRL & statements & presentations etc? *(postponed)*

## Trading Strategy (Data-Validated)

Backtested against 8,601 Item 2.02 8-K filings with hourly/session/daily returns.

### Return Calculation Methodology (Verified Feb 2026)

<details>
<summary><b>How Returns Are Calculated ▶</b></summary>

**Core formula** (`polygonClass.py:437`):
```
return = (end_price - start_price) / start_price × 100
```

Prices fetched via Polygon API using **second-level trade data** (`get_aggs(timespan="second")`).
`get_last_trade()` finds the closest trade at or before the target timestamp, expanding search window progressively (300s → 600s → ... up to max_days_back).

**Time windows by return type:**

| Return | Start Price | End Price | What It Measures |
|--------|------------|-----------|------------------|
| **Hourly** | Actual filing time | Filing time + 60 min | First hour reaction (extended hours) |
| **Session** | Actual filing time | Next market open + 5 min | Overnight reaction through opening |
| **Daily** | Previous close (4 PM) | Next close (4 PM) | Close-to-close |

**Post-market example (filing at 4:15 PM ET):**
- Hourly: 4:15 PM → 5:15 PM (both after-hours — `respect_session_boundary=False`)
- Session: 4:15 PM → 9:35 AM next day
- Daily: 4:00 PM same day → 4:00 PM next day

**Pre-market example (filing at 7:30 AM ET):**
- Hourly: 7:30 AM → 8:30 AM (both pre-market)
- Session: 7:30 AM → 9:35 AM same day
- Daily: 4:00 PM previous day → 4:00 PM same day

**Extended hours data confirmed:**
- Polygon API returns real second-level trade data for after-hours/pre-market timestamps
- Neo4j data validates: 73.5% of 8,601 filings have hourly returns ≥ 0.1%
- Post-market filings show large hourly moves (e.g., MGNX at 16:06 → hourly -56.23%, CDLX at 16:06 → hourly +28.85%)
- Hourly captures meaningful fraction of daily: 52.3% of filings with |daily| > 1% show hourly at 20%+ of daily

**Code chain:** `ReturnsProcessor._calculate_available_returns` → `Polygon.get_event_returns` → `MarketSessionClassifier.get_interval_start/end_time` → `Polygon.get_returns_indexed` → `Polygon.get_last_trade` → `Polygon.get_aggs(timespan="second")`

</details>

### Entry Rules

1. 8-K earnings filing drops (post-market or pre-market)
2. LLM reads filing in 5-10 min → confirms genuine surprise (beat/miss + guidance direction)
3. Check price: has it moved in the predicted direction?
4. **Only enter if both LLM prediction AND price action agree**
5. **Note:** The >3% hourly magnitude filter from the backtest CANNOT be applied at 5-min entry (the hourly move hasn't completed yet). The LLM replaces this filter — it predicts direction and surprise magnitude from the filing itself. Price action confirmation at entry serves as the remaining gate.

### Exit Rules

- **Hold 24 hours** — exit at next day's close
- **Stop-loss: 10%** — triggers on ~5% of trades; avg loss is -5.1% (well inside the stop)
- **No profit cap** — let winners run. Avg winner is +12.1% (post-market)

### Position Sizing

- 33-50% of portfolio per trade
- Maximum 1-2 trades per day (earnings overlap during peak season)

### Key Data Findings (from Neo4j, n=8,601)

**Filing session distribution:**
- 53% post-market (after 4 PM ET)
- 45% pre-market (before 9:30 AM ET)
- 2% during market hours

**Price move timing:**
- 49% of the total daily move happens in the first hour (after-hours)
- 88% of the move is done by market open

**Win rate by hourly move magnitude (5-min entry model):**

| Hourly move | Win rate | Avg PnL | n |
|---|---|---|---|
| 1-2% | 58% | +1.58% | 639 |
| 3-5% | 68% | +4.10% | 615 |
| 5-7% | 76% | +6.77% | 324 |
| 7-10% | 84% | +9.72% | 234 |
| >10% | 90% | +15.60% | 259 |

**Bigger initial moves are more reliable. The loss on losers stays constant (~6.5%) regardless of bucket.**

**Win rate by entry timing:**

| Entry delay | Win rate | Avg PnL |
|---|---|---|
| 5 min | 72% | +6.33% |
| 15 min | 69% | +5.45% |
| 60 min | 54% | +1.09% |

**Earlier entry = higher win rate.** 5% take-profit cap destroys 80% of returns (avg winner is +11-12%).

**Direction asymmetry (>3% hourly):**
- Shorts (miss → sell): 81% win rate, +8.41% avg PnL
- Longs (beat → buy): 72% win rate, +6.93% avg PnL

**Session momentum (check at next morning's open):**
- Momentum building (move extended overnight, 56% of trades): 90-94% win rate
- Pullback (same direction, smaller, 32%): 70-74% win rate
- Full reversal (direction flipped, 13%): 34-38% win rate → EXIT immediately

**Monthly consistency:** Every month in the dataset was profitable. Worst month averaged +4.50% per trade.

### Honest Assessment: Per-Trade Win Rate = 63%

**Why 63%, not the backtested 72%:**
- Backtest shows 72% at 5-min entry with >3% hourly filter
- But the >3% hourly filter **cannot be applied at entry** — the move hasn't completed yet
- LLM replaces magnitude filter (~85-90% accurate on clear beats/misses, lower on ambiguous)
- Trading the full distribution (not just fat moves) pulls win rate down
- Selectivity (high confidence only, 800 companies) pulls back up somewhat
- Net realistic per-trade win rate: **63%**
- System-level profitability: **positive expected value confirmed**

### Realistic Expected Returns (after execution haircuts)

Haircuts: after-hours spread/slippage (~0.5-1%), entry timing (LLM replaces magnitude filter), backtest-to-live discount (20-30%).

**Per-trade:**
- Expected return on portfolio: ~1.2% per trade (at 50% position)
- Avg winner: ~+6% on position, avg loser: ~-5% (with stop-loss)

**Monthly (seasonal):**
- Peak earnings (Jan-Feb, Apr-May, Jul-Aug, Oct-Nov): 12-15 trades → ~15-20%/month
- Off-peak months: 3-5 trades → ~3-5%/month
- **Averaged across the year: ~10-12%/month**

**Annual (on $1,000, no compounding):**
- Backtest-implied: ~$2,800-3,200 year-end
- After live-trading discount (20-30%): ~$2,200-2,700 year-end
- Monthly average: ~$100-170

**Backtest-to-live discount note:** Every backtested strategy outperforms its live execution. Slippage is worse than modeled, execution is slower than assumed, not every filing is caught in time. Budget 20-30% below backtested figures.

### LLM Prediction Framework (Structured Reasoning)

The LLM replaces the hourly magnitude filter — it's the only thing that can tell you at the 5-minute mark whether this is a big move or a small one. Force systematic reasoning, not open-ended "predict the direction":

```
1. Quantitative surprise
   - EPS actual vs consensus → beat/miss by how much?
   - Revenue actual vs consensus → beat/miss by how much?
   - Magnitude relative to historical surprise range for this company

2. Guidance change
   - Raised, maintained, or lowered?
   - By how much vs prior guidance?
   - Forward guidance dominates backward results ~60-70% of the time

3. Quality of beat
   - Organic growth or one-time items?
   - Margin expansion or cost cuts?
   - Sustainable or non-recurring?

4. Management tone
   - Confident or hedging?
   - Specific or vague on forward outlook?
   - (Transcript analysis when available)

5. Sector context
   - Are peers reporting similar trends?
   - Sector headwinds or tailwinds?
   - Macro environment alignment

6. Historical pattern
   - How has this stock reacted to similar setups before?
   - Attribution feedback: what drove the move last quarter?

7. Prediction + Confidence
   - Direction: long or short
   - Confidence: high / extreme (only trade these)
   - Expected magnitude: small (<3%), medium (3-7%), large (>7%)
```

**Key insight:** The LLM's real job isn't confirming direction — it's **predicting magnitude**. "Can this filing move the stock 5%+?" is the question that matters. For extreme cases (massive beat/miss, clear guidance) the LLM is ~85%+ accurate because it's reading actual numbers vs consensus. For moderate cases (5% beat, ambiguous guidance) — skip the trade.

### What Moves the Needle (in priority order)

Focus on data quality and reasoning quality, not infrastructure. Better water, not better plumbing.

1. **Consensus estimates** — the biggest lever. Surprise = actual vs expected. You have AlphaVantage. Make sure every prediction has EPS + revenue estimate vs actual + magnitude of surprise relative to historical range.
2. **Guidance weighting** — forward guidance dominates ~60-70% of the time. A company can beat every metric and tank because they guided lower. Weight it explicitly and heavily.
3. **Attribution feedback loop** — your strongest advantage. Most systems are static. Yours learns: Q1 attribution ("guidance cut dominated revenue beat") feeds Q2 prediction. This is where accuracy compounds.
4. **Calibration tracking** — measure accuracy over time. Identify systematic biases (e.g., "always too bullish on tech"). Requires 100+ scored trades.
5. **Options-implied move** — the market prices in an expected move before earnings. If the stock moves 3% but the market expected 5%, that's actually a disappointment. Highest-value missing data point (deferred — requires additional data source).

### Strategy Summary (Simple Version)

```
1. Earnings drop → LLM reads filing → runs 7-step framework → confirms big surprise
2. Price already moving in expected direction? → Enter
3. Next morning: move kept going overnight? → Hold to close (90%+ win rate)
4. Next morning: move reversed overnight? → Exit immediately
5. Never cap winners. Stop-loss at 10% (rarely hit).
```

## Deferred: Real-time Mode

Current design uses **slow mode** (sequential updates before prediction).

For real-time trading signals, news-impact and guidance-inventory would need continuous background updates. **Deferred** — no structural changes needed, only timing changes.

**Note for later:** Rare edge case — company may update guidance AFTER the 8-K filing (e.g., special announcements between quarters). Current design only updates guidance-inventory via attribution. For real-time mode, may need a mechanism to capture mid-quarter guidance updates to avoid stale data in prediction.

## Completion Tracking (New Approach)

**Output files = source of truth** — no separate tracking CSV needed.

```
For each accession:
    ├── prediction:  does {TICKER}/{accession}_prediction.md exist?
    ├── attribution: does {TICKER}/{accession}.md exist?
    │   ├── Yes → skip (already processed)
    │   └── No  → process
```

**Why this works:**
- Idempotent — can re-run safely
- No tracking file to maintain
- Output file IS the completion marker
- Works for both historical and real-time

**Batch mode:** Orchestrator queries all 8-K (Item 2.02) for a ticker, checks file existence, processes missing ones chronologically.

**Live mode:** New 8-K ingested → triggers workflow → creates output file → done.

## Old Flow: File Outputs (will change)

Current prediction/attribution skills update these files:

<details>
<summary><b>File Output Diagram ▶</b></summary>

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   earnings-prediction   │         │   earnings-attribution  │
└───────────┬─────────────┘         └───────────┬─────────────┘
            │                                   │
            │ writes                            │ writes
            ▼                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     SHARED FILES                            │
├─────────────────────────────────────────────────────────────┤
│ predictions.csv         ← prediction appends row            │
│                         ← attribution fills actual_* cols   │
├─────────────────────────────────────────────────────────────┤
│ subagent-history.csv    ← both append session tracking      │
└─────────────────────────────────────────────────────────────┘
            │                                   │
            ▼                                   ▼
┌───────────────────────┐       ┌─────────────────────────────┐
│ Obsidian thinking     │       │ {TICKER}/{accession}.md     │
│ (build-thinking-index)│       │ {TICKER}/learnings.md       │
└───────────────────────┘       │ 8k_fact_universe.csv        │
                                │ skill files (self-update)   │
                                └─────────────────────────────┘
```

</details>

**earnings-prediction writes:**
- `predictions.csv` — appends row (actual_* columns left empty)
- `subagent-history.csv` — session tracking
- Obsidian — thinking extraction
- *Note: currently no separate prediction report file — TBD if needed*

**earnings-attribution writes:**
- `{TICKER}/{accession}.md` — attribution report
- `{TICKER}/learnings.md` — company-specific learnings
- `predictions.csv` — fills actual_direction, actual_magnitude, actual_return, correct
- `8k_fact_universe.csv` — sets completed=TRUE
- `subagent-history.csv` — session tracking
- Obsidian — thinking extraction
- Skill files — self-improvement (if SKILL_UPDATE_NEEDED)
