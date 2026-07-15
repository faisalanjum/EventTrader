# Stock Movement Driver Analysis Framework

## Purpose
This document provides unambiguous, systematic rules for creating stock movement driver analysis documents for ANY company using the EventMarketDB database structure.

## Step-by-Step Framework for Creating Driver Documents

### STEP 1: Initial Event Query
```cypher
MATCH (c:Company {ticker: [TARGET_TICKER]})
MATCH (n)-[r:INFLUENCES|PRIMARY_FILER]->(c)
WHERE (n:News OR n:Transcript OR (n:Report AND type(r) = 'PRIMARY_FILER'))
  AND abs(r.hourly_stock - r.hourly_macro) > [THRESHOLD]
RETURN n, r, (r.hourly_stock - r.hourly_macro) as adj_return
ORDER BY abs(adj_return) DESC
```
- Set THRESHOLD = 2.0 as default
- **CRITICAL**: Order by magnitude of adjusted_return (largest moves first)
- Expect 10-30 events for major companies over 1-2 years

### STEP 2: Extract Complete Return Data
For EACH event found in Step 1, extract:
```cypher
RETURN 
  n.id as node_id,
  labels(n)[0] as node_type,
  n.created as datetime,
  n.market_session as market_session,
  r.hourly_stock, r.hourly_macro, r.hourly_sector, r.hourly_industry,
  r.session_stock, r.session_macro, r.session_sector, r.session_industry,
  r.daily_stock, r.daily_macro, r.daily_sector, r.daily_industry
```

### STEP 3: Calculate Performance Metrics
For each event, calculate:
1. **Adjusted Return** = hourly_stock - hourly_macro
2. **Sector Outperformance** = hourly_stock - hourly_sector
3. **Industry Outperformance** = hourly_stock - hourly_industry
4. **Idiosyncratic Return** = hourly_stock - max(hourly_sector, hourly_industry)

### STEP 4: Gather Historical Context
**For earnings events**, track the pattern:
```cypher
MATCH (r:Report)-[rel:PRIMARY_FILER]->(c:Company {ticker: [TARGET_TICKER]})
WHERE r.formType = '8-K' AND r.description CONTAINS 'Item 2.02'
  AND r.created < [CURRENT_EVENT_DATE]
RETURN r.created, (rel.hourly_stock - rel.hourly_macro) as historical_reaction
ORDER BY r.created DESC
LIMIT 4
```

**Look for patterns:**
- Deteriorating reactions: -0.5% → -1.2% → -2.4% → -4.8%
- Improving reactions: -3.2% → -2.1% → -0.8% → +1.2%
- Include this progression in your reasoning with arrow notation

### STEP 5: Build Company Context
**Query for basic company facts:**
```cypher
MATCH (c:Company {ticker: [TARGET_TICKER]})
RETURN c.sector, c.industry, c.mkt_cap
```

**Key context to research (via news/reports):**
- Major revenue segments and their typical %
- Historical growth rates for key products
- Seasonal patterns (e.g., iPhone launch quarters)
- Key supplier relationships
- Major geographic revenue splits

### STEP 6: Query Related Companies
Find supply chain/competitor impacts:
```cypher
MATCH (c:Company {ticker: [TARGET_TICKER]})-[:RELATED_TO]-(related:Company)
MATCH (n2)-[r2:INFLUENCES]->(related)
WHERE n2.created >= [EVENT_DATE - 2 days] AND n2.created <= [EVENT_DATE + 2 days]
  AND abs(r2.hourly_stock - r2.hourly_macro) > 1.0
RETURN related.ticker, count(*) as related_events
```

### STEP 7: Extract Event-Specific Information
Based on node_type:

**For News nodes:**
- title/headline
- body/teaser (first 200 chars)
- authors
- tags

**For Report nodes:**
- formType
- description
- items (if 8-K)
- periodOfReport

**For Transcript nodes:**
- fiscal_quarter
- conference_datetime
- company_name

### STEP 8: Determine Confidence Score
Confidence reflects how well you can EXPLAIN the movement, not just data availability.

**Confidence Guidelines:**
- **95-99%**: Perfect explanation with multiple corroborating factors
  - Historical pattern + Sector divergence + Specific catalyst + Timing alignment
  - Example: "4th consecutive earnings disappointment with sector underperformance"
- **90-94%**: Strong explanation with 2-3 solid factors
  - Clear catalyst + Historical context OR Sector divergence
  - Example: "Supply constraint admission after revenue miss"
- **85-89%**: Good explanation with primary catalyst clear
  - Obvious news driver with reasonable magnitude
  - Example: "10% product revenue decline in earnings"
- **80-84%**: Decent explanation but some uncertainty
  - Event explains direction but not magnitude
  - Example: "Analyst upgrade during oversold conditions"
- **75-79%**: Weak explanation, likely other factors
  - Event timing suspicious or magnitude seems wrong
  - Example: "Small price hike causing 3% drop"

### STEP 9: Identify Movement Drivers
Apply this decision tree:

1. **If sector_outperformance > 2%** → Company-specific factors dominate
2. **If industry_outperformance > 2%** → Company outperforming peers
3. **If adjusted_return negative AND sector positive** → Company-specific problems
4. **If historical pattern shows acceleration** → Trend confirmation
5. **If multiple product/segment details** → Segment-specific issues
6. **If supply constraints mentioned** → Operational execution
7. **If guidance/forward-looking** → Future expectations shift

### STEP 10: Construct Reason Statement
**Structure your reasoning with numbered points and specific data:**

**Opening Statement Pattern:**
"The [X.XX]% [decline/gain] [represents/reflects/triggered by] [primary insight with context]."

**Body Structure (3-7 numbered points):**
1. **Sector/Industry Comparison**: Always calculate and state the divergence
   - "Apple underperformed its sector by 3.86% (-5.07% vs -1.21%)"
2. **Historical Pattern** (if applicable): Show progression
   - "This was the 4th consecutive disappointing quarter (Q1: -0.67% → Q4: -4.60%)"
3. **Specific Metrics**: Include exact numbers from headlines/filings
   - "iPhone revenue grew only 2.8% YoY vs 15%+ typical for launch quarters"
4. **Hidden Details** (if found): Information not in headlines
   - "Americas revenue grew only 0.77% - effectively flat in core market"
5. **Market Context**: Macro factors or peer performance
   - "With CPI at 3.7%, real growth was negative"
6. **Time Dynamics**: How the move evolved
   - "The -3.66% session return despite +0.55% macro shows sustained selling"
7. **Implications**: What this means
   - "This marks Apple's transition from growth stock to value trap"

**Example from AAPL:**
"The 5.07% decline represents Apple's WORST earnings reaction in recent history, validated by database patterns showing progressively negative reactions (Q1'23: -0.67% → Q4'23: -4.60%). Deep analysis reveals: (1) Apple underperformed its sector by 3.86% (-5.07% vs -1.21%), confirming company-specific issues beyond tech weakness. (2) Historical earnings pattern shows this was the 4th consecutive disappointing quarter, establishing a clear downtrend. (3) The exhibit_contents parsing reveals revenue declined 0.7% YoY with Americas (40% of revenue) growing only 0.77% - effectively flat in Apple's core market..."

### STEP 11: Generate Driver Tags
Create 4-6 SPECIFIC drivers that capture the essence of the movement.

**Driver Construction Rules:**
1. **Be Specific**: Include numbers when impactful
   - GOOD: "Sector underperformance -3.86%"
   - BAD: "Sector underperformance"

2. **Be Memorable**: Use superlatives when accurate
   - GOOD: "Weakest iPhone launch ever"
   - BAD: "Weak iPhone sales"

3. **Show Progression**: Indicate trends
   - GOOD: "4th consecutive disappointment"
   - BAD: "Earnings miss"

4. **Highlight Transitions**: Mark inflection points
   - GOOD: "Growth→Value transition"
   - BAD: "Valuation concerns"

5. **Include Implications**: Show cascading effects
   - GOOD: "Supply chain contagion"
   - BAD: "Supply issues"

**Example Driver Sets from AAPL:**
- Event 1: ["Historical worst reaction", "Sector underperformance -3.86%", "Americas growth stall", "4th consecutive disappointment", "Supply chain cascade", "Growth→Value transition"]
- Event 2: ["Weakest launch ever", "Negative real growth", "Supply chain contagion", "China luxury collapse", "Algo revaluation", "Unit decline confirmation"]
- Event 3: ["TSMC execution failure", "45% margin mix disaster", "China luxury freeze", "9-year streak broken", "Management credibility loss", "Human-driven selling"]

## XBRL Data Integration (Optional Enhancement)

**Reality Check**: XBRL data arrives 1.5-2 hours AFTER the market has already reacted. It cannot explain real-time movements but can validate your analysis.

### When to Use XBRL
1. **Large reactions (>4%) to earnings** - Worth checking if fundamentals justify the move
2. **"Beat and drop" scenarios** - XBRL often reveals the hidden problems
3. **When confidence is <85%** - XBRL might provide missing pieces

### Practical XBRL Usage
```cypher
# Check if 10-K/10-Q filed after the event
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: [TARGET_TICKER]})
WHERE r.formType IN ['10-K', '10-Q']
  AND r.created >= [EVENT_TIME] 
  AND r.created <= [EVENT_TIME + 3 hours]
  AND r.xbrl_status = 'COMPLETED'
RETURN r.accessionNo, r.created
```

**What XBRL Can Reveal (Examples from AAPL):**
- Geographic revenue breakdown (Americas grew only 0.77%)
- Cash flow vs earnings divergence (-9.5% operating cash flow)
- Segment performance not in press release
- Deferred revenue changes indicating future headwinds

**Do NOT:**
- Wait for XBRL before analyzing an event
- Assume XBRL will always be available or useful
- Use XBRL for predictive purposes
- Overcomplicate analysis with too many XBRL facts

**Integration Rule**: If XBRL reveals something that changes your understanding of the movement, update your reasoning and confidence. Otherwise, proceed without it.

## Output JSON Structure

```json
{
  "stock_ticker": "[TICKER]",
  "analysis_date": "[YYYY-MM-DD]",
  "threshold": [THRESHOLD_VALUE],
  "events": [
    {
      "node_id": "[DATABASE_NODE_ID]",
      "node_type": "[News|Report|Transcript]",
      "datetime": "[ISO_DATETIME]",
      "market_session": "[pre_market|in_market|post_market]",
      "adjusted_return": [DECIMAL],
      "confidence": [INTEGER 0-100],
      "returns": {
        "stock": {
          "hourly": [DECIMAL],
          "session": [DECIMAL],
          "daily": [DECIMAL]
        },
        "macro": {
          "hourly": [DECIMAL],
          "session": [DECIMAL],
          "daily": [DECIMAL]
        },
        "sector": {
          "hourly": [DECIMAL],
          "session": [DECIMAL],
          "daily": [DECIMAL]
        },
        "industry": {
          "hourly": [DECIMAL],
          "session": [DECIMAL],
          "daily": [DECIMAL]
        }
      },
      "headline": "[EVENT_TITLE]",
      "reason_for_movement": "[CONSTRUCTED_REASON]",
      "drivers": ["[DRIVER1]", "[DRIVER2]", "[DRIVER3]", ...]
    }
  ],
  "summary": {
    "total_events": [COUNT],
    "news_events": [COUNT],
    "report_events": [COUNT],
    "transcript_events": [COUNT],
    "positive_events": [COUNT],
    "negative_events": [COUNT],
    "largest_positive_move": [DECIMAL],
    "largest_negative_move": [DECIMAL],
    "average_confidence": [DECIMAL]
  }
}
```

## Quality Checks

Before finalizing the document, verify:

1. **Data Completeness**
   - All events have complete return data
   - No null values in required fields
   - Datetime formats are consistent

2. **Logic Consistency**
   - Adjusted returns match stock - macro calculation
   - Confidence scores are justified by data
   - Driver tags match the reason statement

3. **Statistical Validity**
   - Sample size sufficient (minimum 5 events recommended)
   - Time period reasonable (avoid cherry-picking)
   - Threshold appropriate for company volatility

## Common Pitfalls to Avoid

1. **Generic Drivers**: "Revenue miss" vs "iPhone revenue grew only 2.8% in launch quarter"
2. **Missing Sector Context**: Always calculate sector/industry divergence
3. **Ignoring Historical Patterns**: Track quarter-by-quarter progression for earnings
4. **Weak Reasoning**: Single sentence vs numbered multi-point analysis
5. **Wrong Confidence**: 85% for minor news vs 95%+ for clear multi-factor explanations
6. **No Specific Numbers**: "Revenue declined" vs "Revenue declined 0.7% YoY"
7. **Missing Time Dynamics**: How did the move evolve during the session?

## Example: Good vs Bad Analysis

### BAD Example:
```json
{
  "headline": "Apple Reports Q4 Earnings",
  "adjusted_return": -5.07,
  "confidence": 85,
  "reason_for_movement": "Apple missed expectations despite beating earnings. The market was disappointed.",
  "drivers": ["Earnings disappointment", "Market reaction", "Expectations miss"]
}
```

### GOOD Example (from actual AAPL analysis):
```json
{
  "headline": "Apple Q4 EPS $1.46 vs $1.39 Est., Sales $89.5B vs $89.284B Est.",
  "adjusted_return": -5.07,
  "confidence": 98,
  "reason_for_movement": "The 5.07% decline represents Apple's WORST earnings reaction in recent history, validated by database patterns showing progressively negative reactions (Q1'23: -0.67% → Q4'23: -4.60%). Deep analysis reveals: (1) Apple underperformed its sector by 3.86% (-5.07% vs -1.21%), confirming company-specific issues beyond tech weakness. (2) Historical earnings pattern shows this was the 4th consecutive disappointing quarter, establishing a clear downtrend. (3) The exhibit_contents parsing reveals revenue declined 0.7% YoY with Americas (40% of revenue) growing only 0.77% - effectively flat in Apple's core market. (4) Industry outperformance (-0.71% vs -5.07%) shows Apple losing competitive position within Consumer Electronics. (5) Supply chain partners (QCOM, AVGO) likely saw order cuts, creating negative feedback loops. (6) The -3.66% session return despite +0.55% macro shows sustained selling pressure, not just knee-jerk reaction. This marks the inflection point where Apple transitioned from growth stock to value trap in investor perception.",
  "drivers": ["Historical worst reaction", "Sector underperformance -3.86%", "Americas growth stall", "4th consecutive disappointment", "Supply chain cascade", "Growth→Value transition"]
}
```

**What makes the GOOD example better:**
- Specific percentages and calculations
- Historical context with progression
- Multiple numbered evidence points
- Sector/industry comparisons
- Time dynamics (session vs hourly)
- Memorable, specific drivers
- Confidence reflects deep understanding

## Quick Reference Checklist

Before submitting your analysis, verify:
- [ ] Events ordered by magnitude of adjusted_return (largest first)
- [ ] All return data complete (hourly, session, daily for stock/macro/sector/industry)
- [ ] Confidence scores reflect explanation quality (not just data availability)
- [ ] Reasoning includes numbered points with specific data
- [ ] Historical pattern included for earnings events
- [ ] Sector/industry divergence calculated and stated
- [ ] Drivers are specific and memorable (not generic)
- [ ] 4-6 drivers per event capturing different aspects
- [ ] Summary statistics accurate (counts, averages)
- [ ] JSON structure matches the template exactly

## Implementation Notes

- This framework is database-schema dependent but company-agnostic
- All queries should be parameterized for any ticker
- Confidence scoring is objective and data-driven
- XBRL integration is for validation, not prediction
- Output format is consistent for ML/analysis pipelines

## Version
Framework Version: 2.0
Last Updated: 2025-07-16
Compatible with: EventMarketDB schema as of 2025-07-16

### Major Changes in v2.0:
- Added Step 5: Build Company Context
- Revised confidence scoring to reflect explanation quality
- Enhanced reasoning structure with numbered points
- Improved driver specificity with examples
- Added good vs bad example comparison
- Clarified XBRL as validation tool, not prediction
- Added quick reference checklist