# Plan: Earnings Orchestrator News Save/Tracking

## Summary

| Decision | Choice |
|----------|--------|
| Target | `earnings-orchestrator` (uses bz-news-driver + external-news-driver) |
| Validation | Soft enforcement (schema docs existing format) |
| Storage | Orchestrator saves after collecting results |
| Tracking | Central matrix: `news_processed.csv` |

---

## Current Flow (No Changes)

```
earnings-orchestrator
    │
    ├─ get_earnings.py → E1, E2 dates
    │
    ├─ get_significant_moves.py → list of dates
    │
    ├─ bz-news-driver (per date) → explained or needs_research
    │
    └─ external-news-driver (per gap) → researched
```

**Agent output format (10 fields):**
```
date|news_id|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
```

---

## New Flow (Add Save/Track)

```
earnings-orchestrator
    │
    ├─ NEW: Check news_processed.csv → Is {TICKER} Q1 done?
    │       │
    │       ├─ YES → Skip Q1 news gathering, read from CSV
    │       └─ NO  → Continue...
    │
    ├─ get_significant_moves.py → dates
    ├─ bz-news-driver + external-news-driver → results
    │
    ├─ NEW: Save to Companies/{TICKER}/news.csv
    │
    └─ NEW: Mark Q1 done in news_processed.csv
```

---

## File Structure

```
earnings-analysis/
├── news_processed.csv              # Central tracking (matrix)
└── Companies/
    └── {TICKER}/
        └── news.csv                # All news for ticker

.claude/shared/schemas/
├── README.md
└── news-driver/                    # Documents agent output format
    ├── output_template.md
    ├── value_constraints.md
    └── evidence_audit.md
```

---

## news_processed.csv (matrix)

```csv
ticker,Q1_FY2024,Q2_FY2024,Q3_FY2024,Q4_FY2024
AAPL,2026-01-15,2026-01-20,,
MSFT,2026-01-16,,,
```

---

## news.csv (per ticker)

```csv
quarter,date,news_id,driver,confidence,daily_stock,daily_adj,market_session,source,external_research,source_pub_date
Q1_FY2024,2024-01-18,bz-123,Q1 beat with iPhone strength,85,4.23,3.15,pre_market,benzinga,false,2024-01-18
Q1_FY2024,2024-02-10,https://reuters.com/...,Supply chain concerns,62,-3.12,-2.78,,websearch,false,2024-02-09
```

Note: Added `quarter` column for filtering.

---

## Schema Files (Minimal - Document Existing)

### output_template.md

```markdown
# News Driver Output

## Format (10 fields + quarter)

```
quarter|date|news_id|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
```

## Fields

| Field | Type | Source |
|-------|------|--------|
| quarter | string | Added by orchestrator (Q1_FY2024) |
| date | date | Analysis date |
| news_id | string | Benzinga ID or URL(s) |
| driver | string | 5-15 words |
| confidence | int | 0-100 |
| daily_stock | float | Raw return |
| daily_adj | float | vs SPY |
| market_session | enum | pre_market/in_market/post_market/empty |
| source | enum | benzinga/websearch/perplexity/none |
| external_research | bool | true if gap needed research |
| source_pub_date | date | Article publication date |

## Storage

- Tracking: `earnings-analysis/news_processed.csv`
- Data: `earnings-analysis/Companies/{TICKER}/news.csv`
```

### value_constraints.md

```markdown
# Constraints

## source
| Value | Agent |
|-------|-------|
| benzinga | bz-news-driver |
| websearch | external-news-driver |
| perplexity | external-news-driver |
| none | No news found |

## confidence
| Range | When |
|-------|------|
| 70-100 | Pre-market + clear match |
| 50-69 | 2+ sources agree |
| 1-49 | Single source |
| 0 | UNKNOWN |

## driver
- 5-15 words
- UNKNOWN if no explanation
```

### evidence_audit.md

```markdown
# Checklist

- [ ] source_pub_date <= date (PIT rule)
- [ ] confidence=0 when driver=UNKNOWN
- [ ] external_research=true when uncertain
- [ ] No duplicate dates per quarter
```

---

## Implementation Order

1. Create `earnings-analysis/news_processed.csv` (header only)
2. Create `.claude/shared/schemas/news-driver/` files
3. Update `earnings-orchestrator/SKILL.md`:
   - Add check step before Q1
   - Add save step after Q1 complete
   - Add save step after Q2 complete
   - Add mark-done step for each quarter

---

## Orchestrator SKILL.md Changes

Add before Step 2:
```markdown
### Step 1b: Check News Cache

Check `earnings-analysis/news_processed.csv` for {TICKER} row.

- If Q1 column has date → Read Q1 from `Companies/{TICKER}/news.csv`, skip Step 2-3b
- If Q2 column has date → Read Q2 from `Companies/{TICKER}/news.csv`, skip Step 4a-4b
```

Add after Step 3b:
```markdown
### Step 3c: Save Q1 Results

1. Append Q1 results to `earnings-analysis/Companies/{TICKER}/news.csv` (add quarter=Q1_FY{year})
2. Update `news_processed.csv`: Set {TICKER},Q1_FY{year} = today's date
```

Add after Step 4b:
```markdown
### Step 4c: Save Q2 Results

1. Append Q2 results to `earnings-analysis/Companies/{TICKER}/news.csv` (add quarter=Q2_FY{year})
2. Update `news_processed.csv`: Set {TICKER},Q2_FY{year} = today's date
```
