# Attribution Analysis Rules

**Goal**: Determine with 100% certainty WHY a stock moved after an 8-K filing.

**Phase**: Discovery - Learning what drivers matter for each company. Custom nodes and structures come later.

**Process**: Here is what you have to do: Read this in detail.
/home/faisal/EventMarketDB/earnings-analysis/rules.md
. Then check this file. /home/faisal/EventMarketDB/earnings-analysis/8k_fact_universe.csv Check the completed column. There should
only be one report which is completed, so true. Find a report next to that.
Based on the rules.md Do an analysis on that specific report. Then save it in /home/faisal/EventMarketDB/earnings-analysis/Companies.
 If any doubt, ask questions. You can ask questions using the Ask User
Questions tool. Have any doubts? Otherwise, go ahead and do it.
Once fully done, update the CSV to mark this report as completed
---

## Process Overview

```
Step 1: Get Report → Identify the move (direction, magnitude)
Step 2: Query News → Get beat/miss, guidance, analyst reactions
Step 3: Query Transcript → Get management commentary, analyst concerns
Step 4: Query Perplexity → Validate and fill gaps (ALWAYS do this)
Step 5: Synthesize → One clear reason why stock moved (can include multiple triggers but only when 100% certain)
```

---

## Step 1: Get Report and Returns

```cypher
MATCH (r:Report {id: $accession_no})-[pf:PRIMARY_FILER]->(c:Company)
RETURN
    c.ticker AS ticker,
    c.name AS company,
    r.created AS filed_at,
    r.items AS items,
    round((pf.hourly_stock - pf.hourly_macro) * 100) / 100 AS hourly_adj,
    round((pf.daily_stock - pf.daily_macro) * 100) / 100 AS daily_adj
```

**You now know**:
- Ticker and company name
- Filing date and time
- Items (2.02 = Earnings)
- Move magnitude (adjusted = stock - macro benchmark)

---

## Step 2: Query News (Neo4j)

```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE n.created >= $filed_at - duration('P1D')
  AND n.created <= $filed_at + duration('P1D')
RETURN n.title, n.teaser, n.channels, n.created
ORDER BY n.created
```

**Look for these channels** (in priority order):
1. `Guidance` - Forward estimates (usually the key driver)
2. `Earnings` - Beat/miss numbers
3. `Analyst Ratings` - Upgrades/downgrades
4. `why it's moving` (tag) - Direct explanation

**Extract from headlines**:
- Actual EPS vs Estimate: "$3.64 Beats $3.45" → +5.5% beat
- Guidance vs Consensus: "$12.00-$13.50 vs $13.22 Est" → midpoint miss
- Direction: Raises, Lowers, Maintains, Cuts

---

## Step 3: Query Transcript (Neo4j)

**Only for Item 2.02 (Earnings) reports.**

```cypher
// Find transcript
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE t.conference_datetime >= $filed_at - duration('P1D')
  AND t.conference_datetime <= $filed_at + duration('P1D')
RETURN t.id, t.conference_datetime

// Get Q&A exchanges
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_EXCHANGE]->(qa)
RETURN qa.questioner, qa.questioner_title, qa.exchanges
ORDER BY qa.sequence
LIMIT 10
```

**What to look for**:
- What topics do analysts ask about repeatedly?
- Where does management hedge or deflect?
- Specific numbers: orders, backlog, book-to-bill, regional performance

---

## Step 4: Query Perplexity (ALWAYS)

**Even when news exists in database, query Perplexity to validate and practice the real-time workflow.**

### 4A: Get Consensus Estimate
```
mcp__perplexity__perplexity_search:
  query: "{ticker} Q{quarter} {fiscal_year} earnings EPS estimate consensus before announcement"
```

### 4B: Get Reason for Move
```
mcp__perplexity__perplexity_search:
  query: "Why did {ticker} stock {rise/fall} on {date}? earnings reaction"
```

### 4C: Get Guidance Context (if guidance mentioned)
```
mcp__perplexity__perplexity_search:
  query: "{ticker} FY{year} guidance vs analyst expectations {date}"
```

**For SEC filing content** (use direct API, not MCP):
```python
from utils.perplexity_search import perplexity_sec_search
result = perplexity_sec_search(f"{ticker} 8-K earnings {date}")
```

---

## Step 5: Synthesize

**Answer ONE question**: Why did the stock move?

Compare what you found:
1. **Earnings beat/miss** - How much? (+5% beat, -3% miss, etc.)
2. **Guidance vs consensus** - Above, below, or in-line?
3. **Analyst concerns** - What did they probe in Q&A?
4. **Perplexity confirmation** - Does external data match?

**The driver is usually**:
- If guidance miss > earnings beat → Guidance is the driver
- If earnings miss is large → Earnings is the driver
- If both beat but stock fell → Look for hidden concern (orders, regional weakness, etc.)

---

## Output Format

**Keep it concise. One paragraph is ideal.**

```
## {TICKER} | {DATE} | {daily_adj}%

**Reason**: {One sentence explaining why the stock moved}

**Evidence**:
- {Source 1}: "{Key quote or number}"
- {Source 2}: "{Key quote or number}"

**Pattern**: {Beat-and-Lower / Miss / Beat-and-Raise / etc.}
```

### Example Output

```
## ROK | 2023-11-02 | -5.06%

**Reason**: Stock fell despite Q4 earnings beat because FY24 guidance midpoint ($12.75) was 3.6% below consensus ($13.22), signaling growth deceleration.

**Evidence**:
- News (07:06): "FY24 EPS $12.00-$13.50 vs $13.22 Est"
- Transcript Q&A: CFO confirmed book-to-bill of 0.9x (orders below shipments)
- Perplexity: Confirmed guidance miss was primary driver

**Pattern**: Beat-and-Lower (guidance miss overshadowed earnings beat)
```

---

## Data Sources Reference

### Neo4j Nodes

| Node | Key Properties | Relationship |
|------|---------------|--------------|
| Report | `id`, `created`, `items` | `-[:PRIMARY_FILER]->Company` |
| Company | `ticker`, `name`, `mkt_cap` | |
| News | `title`, `teaser`, `channels`, `created` | `-[:INFLUENCES]->Company` |
| Transcript | `id`, `conference_datetime` | `-[:INFLUENCES]->Company` |
| QAExchange | `questioner`, `exchanges`, `sequence` | `Transcript-[:HAS_QA_EXCHANGE]->` |

### Returns (on PRIMARY_FILER relationship)

| Property | Meaning |
|----------|---------|
| `hourly_stock` | Stock return first hour after filing |
| `hourly_macro` | Market benchmark return same hour |
| `daily_stock` | Stock return full day |
| `daily_macro` | Market benchmark return full day |

**Adjusted return** = `stock - macro` (removes market noise)

### Perplexity Tools

| Tool | Use For |
|------|---------|
| `mcp__perplexity__perplexity_search` | Quick questions, consensus, reactions |
| `mcp__perplexity__perplexity_ask` | Conversational Q&A with real-time web search |
| `mcp__perplexity__perplexity_reason` | Complex multi-factor analysis |
| `mcp__perplexity__perplexity_research` | Comprehensive investigation, conflicting sources |
| `perplexity_sec_search()` | SEC filing content (10-K, 10-Q, 8-K) |

**Note**: MCP tools don't support SEC-specific search. Use `utils/perplexity_search.py` for SEC content.

---

## Common Patterns

| Pattern | What Happened | Stock Reaction |
|---------|---------------|----------------|
| **Beat-and-Raise** | EPS beat + guidance raised | Up |
| **Beat-and-Lower** | EPS beat + guidance missed | Down (guidance wins) |
| **Beat-and-Maintain** | EPS beat + guidance unchanged | Flat to slightly up |
| **Beat-with-Inflection** | EPS beat + forward indicators turning (orders, B2B) | Strong up |
| **Beat-but-Quality-Concerns** | EPS beat + guidance raised, BUT underlying demand weak | Down |
| **Miss-and-Lower** | EPS missed + guidance cut | Strong down |
| **Miss-and-Maintain** | EPS missed + guidance unchanged | Down |

**Note on Quality Patterns**: Even with Beat-and-Raise, stock can fall if:
- ARR/recurring revenue misses expectations
- Growth is from one-time factors (tariff pull-ins, channel stuffing)
- Management signals no demand inflection
- Key segment underperforms

---

## Rules

1. **Use ALL sources** - News, Transcript, AND Perplexity
2. **Perplexity is mandatory** - Always query even if news exists (practice for real-time)
3. **One reason** - Synthesize to a single primary driver
4. **Evidence required** - Every claim needs a source
5. **No XBRL for 8-K** - XBRL only exists for 10-K and 10-Q
6. **Adjusted returns** - Always use stock minus macro

---

## Perplexity Query Templates

**Consensus estimate (historical)**:
```
{ticker} Q{quarter} FY{year} EPS estimate consensus Wall Street before {date}
```

**Consensus estimate (forward-looking)**:
```
{ticker} Q{quarter} FY{year} EPS estimate consensus analyst expectations
```

**Why stock moved**:
```
Why did {ticker} stock drop on {month} {day} {year}
```

**Guidance vs expectations**:
```
{ticker} {fiscal_year} guidance analyst expectations
```

**Analyst reactions**:
```
{ticker} earnings analyst upgrade downgrade {date}
```

---

## Perplexity Capabilities

**Forward-Looking Estimates**: Perplexity CAN provide consensus estimates for UPCOMING earnings reports, not just historical. This is critical for real-time signal generation.

**Sources**: Perplexity aggregates from Nasdaq, Zacks, MarketBeat, Public.com, Financial Modeling Prep - all reliable Wall Street consensus sources.

**Example** (as of Jan 2, 2026):
```
Query: "Rockwell Automation ROK Q1 FY2026 EPS estimate consensus"
Result: Consensus EPS $2.46, expected ~Feb 9, 2026
```

**Real-Time Workflow**:
1. New 8-K arrives with Item 2.02
2. Query Perplexity for consensus estimate
3. Extract actual EPS from press release
4. Calculate beat/miss percentage
5. Query for guidance direction
6. Generate signal

---

*Version 2.1 | 2026-01-02*
