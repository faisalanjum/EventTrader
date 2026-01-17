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
