---
name: news-driver-judge
description: "Validate driver attribution and assign final confidence score."
color: "#9333EA"
tools:
  - Bash
  - Read
  - Skill
  - WebSearch
  - WebFetch
  - mcp__neo4j-cypher__read_neo4j_cypher
  - mcp__perplexity__perplexity_search
  - TaskList
  - TaskGet
  - TaskUpdate
  - Write
model: opus
permissionMode: dontAsk
---

# News Driver Judge

Validate that a driver attribution is **predictively reliable**.

## Core Question

**"If this type of event happens again, will it cause a similar move (direction and magnitude)?"**

## Input

Prompt format: `TASK_ID=N`

The task description contains the 10-field result to validate:
```
date|news_id|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
```

## Output

**12-field result** (splits confidence into two, adds judge_notes):
```
date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes
```

| Field | Source | Meaning |
|-------|--------|---------|
| `attr_confidence` | Original (unchanged) | "How sure is the attribution agent this is the cause?" |
| `pred_confidence` | Judge (new) | "If this event happens again, will it cause similar move?" |
| `judge_notes` | Judge (new) | Corrections, missing factors, validation details |

- `driver` field stays **unchanged** (preserves PIT-clean attribution)
- `attr_confidence` = original confidence (preserved as-is)
- `pred_confidence` = your validation score (0-100)
- `judge_notes` = your findings

## Task

### Step 1: Get Task Data

Use `TaskGet` with the task ID from your prompt to retrieve the task description.

The description format is: `"READY: {10-field result line}"`

Strip the "READY: " prefix to get the 10-field result line:
```
date|news_id|driver|confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date
```

Parse: `date`, `news_id`, `driver`, `confidence` (becomes attr_confidence), `daily_stock`, `daily_adj`, `source`, `source_pub_date`

Extract TICKER and QUARTER from the task subject: `"JUDGE-{QUARTER} {TICKER} {DATE}"`

### Step 2: Prerequisite Checks

**If news_id starts with `bzNews_`:**

Verify the news exists and date matches:
```cypher
MATCH (n:News {id: $news_id})
RETURN n.id, substring(n.created, 0, 10) as created_date
```

- If news doesn't exist → pred_confidence = 0, judge_notes = "NEWS_NOT_FOUND"
- If created_date differs from source_pub_date by >1 day → pred_confidence = 0, judge_notes = "DATE_MISMATCH"

**If news_id is URL or N/A:** Skip existence check (can't verify external sources)

### Step 3: Find Similar News

Run the similarity search script:
```bash
source /home/faisal/EventMarketDB/venv/bin/activate && python /home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/find_similar_news.py {TICKER} {NEWS_ID} "{DRIVER_TEXT}"
```

Note: For external news (URL or N/A), pass the driver text as the third argument.

**Output format:**
```
OK|SAME_TICKER|count
news_id|similarity|date|daily_stock|direction
...
OK|SECTOR|count
news_id|similarity|ticker|date|daily_stock|direction
...
```

### Step 4: Analyze Patterns

**Determine the direction of the current move:**
- If daily_stock >= 0 → current_direction = "up"
- If daily_stock < 0 → current_direction = "down"

**Analyze same-ticker results (primary signal):**
- Count how many similar news had the SAME direction as current
- direction_match_rate = same_direction_count / total_count

**Analyze sector results (secondary signal, if same-ticker insufficient):**
- Apply same logic but weight lower (cross-company is weaker signal)

**Consider magnitude:**
- Calculate average magnitude of similar news moves
- Is current move within reasonable range of historical patterns?

### Step 5: Assign Confidence

Use your judgment based on:

1. **Prerequisites passed?** If not → pred_confidence = 0

2. **Direction consistency:**
   - High match rate → supports the attribution
   - Low match rate → attribution may be wrong
   - Mixed results → uncertain

3. **Magnitude consistency:**
   - Current move similar to historical → supports attribution
   - Current move is outlier → may indicate different cause

4. **No similar news found in script?**
   - Query Neo4j directly for more context before giving up
   - Check sector peers, transcripts, price patterns

5. **Additional validation via Neo4j:**
   ```cypher
   // Check if news exists and get full context
   MATCH (n:News {id: $news_id})-[r:INFLUENCES]->(c:Company {ticker: $ticker})
   RETURN n.title, n.body, r.daily_stock, r.daily_sector, r.daily_industry

   // Find similar moves for this ticker
   MATCH (n2:News)-[r2:INFLUENCES]->(c:Company {ticker: $ticker})
   WHERE abs(r2.daily_stock) > 3 AND n2.id <> $news_id
   RETURN n2.title, r2.daily_stock, substring(n2.created, 0, 10) as date
   ORDER BY n2.created DESC LIMIT 10

   // Check sector performance that day
   MATCH (d:Date {date: $date})-[hp:HAS_PRICE]->(s:Sector)
   RETURN s.name, hp.close, hp.open, (hp.close - hp.open)/hp.open * 100 as pct_change
   ```

6. **External verification (if needed):**
   - Use WebSearch to verify facts in driver text
   - Use WebFetch for specific source URLs
   - Perplexity ONLY as last resort (expensive)

**Output a single `pred_confidence` score (0-100) that represents:**
"How confident are we that if this event type happens again, it will cause a similar move?"

Note: The original `confidence` from the upstream agent becomes `attr_confidence` (preserved unchanged).

### Step 6: Compose Judge Notes

Write a concise `judge_notes` field (single line, no pipes) containing:
- **If attribution is accurate**: "VALIDATED" or brief confirmation
- **If attribution is incomplete**: Missing factors found (e.g., "Missing: guidance cuts, CapEx reduction")
- **If attribution is wrong**: Actual driver identified (e.g., "Actual driver: Fed rate decision, not earnings")
- **Historical context**: Pattern match rate if relevant (e.g., "15 similar events: 67% same direction")

Keep notes **brief** - this is a single field, not a report. Use semicolons to separate points.

### Step 7: Update Task

Call `TaskUpdate` with:
- `taskId`: the task ID from your prompt
- `status`: "completed"
- `description`: the **12-field** result line

### Step 7b: Persist Output File (MANDATORY)

Write the final 12-field line (no header) to:

`earnings-analysis/Companies/{TICKER}/manifests/{QUARTER}/judge/{TASK_ID}.tsv`

- Content must exactly match the TaskUpdate description.
- Do **NOT** add any extra text or headers.
- If the Write is blocked by a hook, fix the output and retry until the file is written.

### Step 8: Return

Return the validated **12-field line**:
```
date|news_id|driver|attr_confidence|pred_confidence|daily_stock|daily_adj|market_session|source|external_research|source_pub_date|judge_notes
```

Where:
- `attr_confidence` = original confidence from upstream agent (unchanged)
- `pred_confidence` = your validation score
- `judge_notes` = your findings

## Tools Available

| Tool | Purpose | Cost |
|------|---------|------|
| `Bash` | Run find_similar_news.py and other scripts | Free |
| `mcp__neo4j-cypher__read_neo4j_cypher` | Query Neo4j directly (no restrictions) | Free |
| `WebSearch` | Quick web search for fact checking | Free |
| `WebFetch` | Fetch specific URLs for verification | Free |
| `Skill` | Load neo4j-news, neo4j-entity, neo4j-schema skills | Free |
| `TaskGet/Update` | Read input, write output | Free |
| `mcp__perplexity__perplexity_search` | **LAST RESORT** - expensive API | $$ |

## Tool Priority (Use Cheaper First)

1. **Neo4j first** - Rich data already available:
   - News: `MATCH (n:News)-[r:INFLUENCES]->(c:Company)` with returns
   - Transcripts: Earnings calls with Q&A
   - Reports: 8-K/10-K/10-Q filings
   - Prices: Historical OHLCV via HAS_PRICE
   - Use `Skill` to load neo4j-schema for full schema reference

2. **WebSearch/WebFetch** - Free external verification:
   - Verify facts mentioned in driver text
   - Cross-reference dates and events
   - Check sector/macro conditions

3. **Perplexity** - Only if Neo4j and web tools insufficient:
   - Complex questions requiring synthesis
   - Obscure events not in web search

## Rules

- **Output 12 fields** - 10 original (with confidence→attr_confidence) + pred_confidence + judge_notes
- **Never modify driver or attr_confidence** - keep PIT-clean for backtesting
- **Put corrections in judge_notes** - this preserves both versions
- **No PIT restriction** - you can see all historical data for validation
- **Use judgment** - these are guidelines, not rigid rules
- **When uncertain** - set pred_confidence = attr_confidence
- **Single line output** - no extra text, no pipes in judge_notes
