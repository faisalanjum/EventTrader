A Guidance Inventory skill is fundamentally different from prediction/attribution - it's about building cumulative state over time rather than analyzing a single event.

  Core Concept: What IS Guidance?
  ┌──────────────────┬──────────────────────────────────────────────┬─────────────────────────┐
  │       Type       │                   Examples                   │       Where Found       │
  ├──────────────────┼──────────────────────────────────────────────┼─────────────────────────┤
  │ Financial - Hard │ EPS, Revenue, Margins, CapEx, FCF, Debt      │ 8-K EX-99.1, Transcript │
  ├──────────────────┼──────────────────────────────────────────────┼─────────────────────────┤
  │ Financial - Soft │ "Double-digit growth", "Margin expansion"    │ Transcript Q&A, News    │
  ├──────────────────┼──────────────────────────────────────────────┼─────────────────────────┤
  │ Operational      │ Units, subscribers, DAUs, stores, headcount  │ 8-K, Transcript         │
  ├──────────────────┼──────────────────────────────────────────────┼─────────────────────────┤
  │ Qualitative      │ "Cautious outlook", "Strong demand pipeline" │ Transcript (tone)       │
  └──────────────────┴──────────────────────────────────────────────┴─────────────────────────┘
  Key Design Elements

  1. Temporal Structure (Critical)

  ┌─────────────────────────────────────────────────────────────────┐
  │  GUIDANCE GIVEN DATE  vs  PERIOD COVERED                        │
  │                                                                 │
  │  2025-02-05 (Q4 FY24 call) → "FY25 EPS $12.00-$13.50"          │
  │       ↑                            ↑                            │
  │  When guidance was issued    What period it covers              │
  │  (citation date)             (target period)                    │
  └─────────────────────────────────────────────────────────────────┘

  Must track BOTH dates - this is often confused.

  2. Q1 vs Other Quarters (The Anchor Problem)
  ┌─────────┬──────────────────────────────────────────────┬──────────────────────────────────────────────┐
  │ Quarter │            What Typically Happens            │                How to Handle                 │
  ├─────────┼──────────────────────────────────────────────┼──────────────────────────────────────────────┤
  │ Q1      │ Annual guidance established ("anchor")       │ Store as anchor_guidance for FY              │
  ├─────────┼──────────────────────────────────────────────┼──────────────────────────────────────────────┤
  │ Q2      │ Update to annual + Q2 guidance               │ Compare to anchor: raised/lowered/maintained │
  ├─────────┼──────────────────────────────────────────────┼──────────────────────────────────────────────┤
  │ Q3      │ Update to annual + Q3 guidance               │ Track cumulative revision from anchor        │
  ├─────────┼──────────────────────────────────────────────┼──────────────────────────────────────────────┤
  │ Q4      │ Final annual + sometimes preliminary next FY │ Close out FY, may seed next anchor           │
  └─────────┴──────────────────────────────────────────────┴──────────────────────────────────────────────┘
  Example:
  Q1 FY25 call: "FY25 EPS $12.00-$13.50" (anchor midpoint: $12.75)
  Q2 FY25 call: "FY25 EPS $12.50-$13.50" (revision: +$0.25 midpoint, +2.0%)
  Q3 FY25 call: "FY25 EPS $13.00-$14.00" (cumulative: +$0.75 from anchor, +5.9%)

  3. Citation Requirements (Non-Negotiable)

  Every guidance entry MUST have:

  metric: "FY25 EPS"
  value: "$12.00-$13.50"
  midpoint: 12.75
  source_type: "8-K EX-99.1"  # or "Transcript Q&A #3", "News", "Perplexity"
  source_id: "0001234567-25-000001"  # accession or URL
  source_date: "2025-02-05"
  quote: "We expect full-year earnings per share of $12.00 to $13.50"
  page_or_section: "Page 2, Outlook section"

  4. Guidance Actions (State Transitions)
  ┌────────────┬─────────────────────────────────┬────────────────────────────────────────────────────┐
  │   Action   │           Definition            │                      Signals                       │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ INITIAL    │ First guidance for this period  │ Sets anchor                                        │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ RAISED     │ Midpoint increased              │ Bullish                                            │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ LOWERED    │ Midpoint decreased              │ Bearish                                            │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ NARROWED   │ Range tightened, midpoint same  │ More certainty                                     │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ WIDENED    │ Range expanded                  │ More uncertainty                                   │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ MAINTAINED │ Explicitly reiterated unchanged │ Neutral (sometimes disappointing if beat expected) │
  ├────────────┼─────────────────────────────────┼────────────────────────────────────────────────────┤
  │ WITHDRAWN  │ Guidance removed                │ Usually very bearish                               │
  └────────────┴─────────────────────────────────┴────────────────────────────────────────────────────┘
  5. Sources & Priority
  ┌───────────────┬───────────────────────────────┬─────────────┬────────────────────────────┐
  │    Source     │           Best For            │ Reliability │        How to Query        │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ 8-K EX-99.1   │ Official numbers              │ Highest     │ neo4j-report               │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ Transcript    │ Context, nuance, Q&A          │ High        │ neo4j-transcript           │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ Alpha Vantage │ Consensus estimates           │ High        │ alphavantage-earnings      │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ News          │ Reactions, analyst commentary │ Medium      │ neo4j-news                 │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ Perplexity    │ Fill gaps, historical         │ Medium      │ perplexity-search/research │
  ├───────────────┼───────────────────────────────┼─────────────┼────────────────────────────┤
  │ WebSearch     │ SEC filings, IR pages         │ Medium      │ WebSearch                  │
  └───────────────┴───────────────────────────────┴─────────────┴────────────────────────────┘
  6. What You're NOT Thinking About

  A. Guidance vs Consensus Distinction

  Company Guidance: "FY25 EPS $12.00-$13.50" (what management says)
  Street Consensus: "$13.22" (what analysts expect)
  Gap: Company guiding BELOW street → bearish signal
  Both must be tracked separately.

  B. Metric Definition Drift

  Q1: "Adjusted EPS excluding stock comp: $3.50"
  Q2: "Adjusted EPS: $3.40"  ← Did definition change?
  Need to track which definition is being used.

  C. Segment-Level Guidance

  Total Revenue: $10B
    - Cloud: $4B (guidance given)
    - Hardware: $6B (no guidance)
  Some companies guide by segment - capture both.

  D. FX / Constant Currency

  "Revenue growth 8-10% constant currency"
  "Revenue growth 5-7% as reported" (includes FX headwind)
  Must note which basis.

  E. Conditional Guidance

  "Guidance assumes no further Fed rate increases"
  "Contingent on closing the Acme acquisition in Q3"
  Track the assumptions - they can invalidate guidance.

  F. Pre-Announcements (Mid-Quarter Updates)

  8-K filed mid-quarter: "Lowering Q2 guidance due to..."
  These are often the most market-moving and must be captured.

  G. Guidance Policy

  "Company does not provide quarterly guidance" (Berkshire, Amazon historically)
  Track whether company guides at all - absence is informative.

  H. Historical Accuracy (Credibility)

  Last 8 quarters: Beat guidance 7/8 times
  Average beat: +3.2%
  Pattern: "Sandbagger" - guides low, beats high
  This is predictive signal.

  I. Comparable Periods

  FY25 Q2 guidance vs FY24 Q2 actual (YoY)
  FY25 Q2 guidance vs FY25 Q1 actual (Sequential)
  Need to link guidance to historical actuals for context.

  J. Range Asymmetry

  Range: $12.00-$14.00
  Midpoint: $13.00
  But if low end = -8% and high end = +8%, that's symmetric
  If low end = -2% and high end = +14%, that's asymmetric bullish
  Range shape matters.

  7. Output File Structure

  # Guidance Inventory: {TICKER}
  ## Period: {from_date} to {to_date}
  ## Generated: {timestamp}

  ---

  ## Company Profile
  | Field | Value |
  |-------|-------|
  | Ticker | AAPL |
  | Guidance Policy | Quarterly guidance provided |
  | Fiscal Year End | September |
  | Historical Beat Rate | 87.5% (7/8 quarters) |

  ---

  ## Active Guidance (Current Outlook)

  ### FY25 Full Year
  | Metric | Low | Mid | High | Source | Date | Action |
  |--------|-----|-----|------|--------|------|--------|
  | EPS | $12.00 | $12.75 | $13.50 | 8-K:000123... | 2025-02-05 | INITIAL |
  | Revenue | $380B | $390B | $400B | 8-K:000123... | 2025-02-05 | INITIAL |

  ### Q2 FY25
  | Metric | Low | Mid | High | Source | Date | Action |
  |--------|-----|-----|------|--------|------|--------|
  | Revenue | $92B | $95B | $98B | 8-K:000123... | 2025-02-05 | INITIAL |

  ---

  ## Guidance History (Last 3 Months)

  ### 2025-02-05: Q1 FY25 Earnings Call
  **Source**: 8-K 000123..., Transcript

  #### Financial Guidance Given:
  | Metric | Period | Value | Action | Quote |
  |--------|--------|-------|--------|-------|
  | EPS | FY25 | $12.00-$13.50 | INITIAL | "We expect..." |
  | Revenue | FY25 | $380B-$400B | INITIAL | "Full year revenue..." |
  | Revenue | Q2 FY25 | $92B-$98B | INITIAL | "For Q2..." |
  | Gross Margin | Q2 FY25 | 45%-46% | INITIAL | "Gross margin..." |

  #### Operational Guidance Given:
  | Metric | Period | Value | Action | Quote |
  |--------|--------|-------|--------|-------|
  | Store Openings | FY25 | 50-60 | INITIAL | "We plan to open..." |

  #### Qualitative Signals:
  - Tone: Cautiously optimistic
  - Key phrases: "Strong demand", "Supply chain normalized"
  - Management confidence: High

  ---

  ## Consensus Comparison

  | Metric | Period | Company Guide (Mid) | Street Consensus | Gap | Signal |
  |--------|--------|---------------------|------------------|-----|--------|
  | EPS | FY25 | $12.75 | $13.22 | -3.6% | Below street |
  | Revenue | FY25 | $390B | $395B | -1.3% | Slightly below |

  **Source**: Alpha Vantage EARNINGS_ESTIMATES, 2025-02-04

  ---

  ## Guidance Revision Timeline

  FY25 EPS Guidance:
  Q1 call (2025-02-05): $12.00-$13.50 (anchor: $12.75)
  Q2 call (2025-05-05): $12.50-$13.50 (+$0.25, +2.0% from anchor)
  Q3 call (2025-08-05): [pending]

  ---

  ## Evidence Ledger

  | # | Metric | Value | Source | Date | Quote/Reference |
  |---|--------|-------|--------|------|-----------------|
  | 1 | FY25 EPS | $12.00-$13.50 | 8-K:000123... | 2025-02-05 | "We expect full-year..." |
  | 2 | FY25 Revenue | $380B-$400B | 8-K:000123... | 2025-02-05 | "Revenue range of..." |
  | 3 | FY25 EPS Consensus | $13.22 | AlphaVantage | 2025-02-04 | EARNINGS_ESTIMATES |

  ---

  ## Notes & Assumptions
  - All EPS figures are non-GAAP adjusted
  - Revenue guidance excludes impact of pending Acme acquisition
  - FX assumption: current spot rates

  ---
  *Last updated: {timestamp}*

  8. Workflow

  Step 1: IDENTIFY SCOPE
    - Ticker, from_date, to_date
    - Determine fiscal quarters covered

  Step 2: GATHER EXISTING GUIDANCE (Neo4j)
    - Query 8-K filings with Item 2.02/7.01
    - Query transcripts in date range
    - Query news mentioning "guidance"

  Step 3: GET CONSENSUS (Alpha Vantage)
    - EARNINGS_ESTIMATES for current/next quarter
    - Historical beat/miss pattern

  Step 4: FILL GAPS (Perplexity/WebSearch)
    - Missing consensus figures
    - Historical guidance not in Neo4j

  Step 5: STRUCTURE INVENTORY
    - Identify anchor (Q1 or earliest)
    - Calculate revisions vs anchor
    - Flag actions (RAISED/LOWERED/etc)

  Step 6: VALIDATE & CITE
    - Every number has source
    - Quotes extracted for key guidance

  Step 7: OUTPUT FILE
    - Single file: Companies/{TICKER}/guidance-inventory.md
    - Or date-stamped: Companies/{TICKER}/guidance-{from}-{to}.md

  9. Integration with Prediction/Attribution
  ┌───────────────────────┬────────────────────────────────────────────────────┐
  │         Skill         │            Uses Guidance Inventory For             │
  ├───────────────────────┼────────────────────────────────────────────────────┤
  │ earnings-prediction   │ Know what guidance existed BEFORE filing (PIT)     │
  ├───────────────────────┼────────────────────────────────────────────────────┤
  │ earnings-attribution  │ Compare actual vs prior guidance for surprise calc │
  ├───────────────────────┼────────────────────────────────────────────────────┤
  │ earnings-orchestrator │ Maintain cumulative guidance state across analyses │
  └───────────────────────┴────────────────────────────────────────────────────┘
  ---
  Key Questions for You

  1. Cumulative vs Snapshot: Should this maintain a rolling cumulative file (updated after each earnings) or generate fresh snapshot each time? 
     updated after each earnings - so previous update is not overwritten

  2. PIT Mode: Does this need to support PIT filtering (for prediction use case)?
     Not neccessarily
  
  3. Granularity: Per-company file, per-quarter file, or single universe file?
    Per company file

  4. Automation Trigger: Run on-demand, or automatically after each 8-K earnings filing?
    Already explained in tradeEarnings.md

  5. Historical Depth: Just last 3 months, or maintain full history for pattern analysis?
        for q=1, all prior, but for q >= 2, last 3 months from the date earnings report released (r.created)


❯ Lets break down the temporal precision requirements.

  The Period Problem

  Every guidance statement has THREE temporal dimensions:

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                                                                             │
  │   GUIDANCE GIVEN DATE          PERIOD TYPE          PERIOD COVERED          │
  │   (when management spoke)      (Q or FY)            (which Q/FY)            │
  │                                                                             │
  │   "2025-02-05"                 "Quarter"            "Q2 FY25"               │
  │         │                           │                    │                  │
  │         │                           │                    ├── Fiscal Year: 25│
  │         │                           │                    ├── Quarter: 2     │
  │         │                           │                    └── Calendar: Apr-Jun 2025
  │         │                           │                                       │
  │         │                           └── Annual vs Quarterly                 │
  │         │                                                                   │
  │         └── Citation timestamp                                              │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘

  Fiscal Year End (FYE) - The Hidden Complexity
  ┌────────────────┬───────────┬─────────────────────┬─────────────────────────┐
  │    Company     │ FYE Month │     FY25 Means      │ Q1 FY25 Calendar Months │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Most companies │ December  │ Jan 2025 - Dec 2025 │ Jan-Mar 2025            │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Apple          │ September │ Oct 2024 - Sep 2025 │ Oct-Dec 2024            │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Microsoft      │ June      │ Jul 2024 - Jun 2025 │ Jul-Sep 2024            │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Walmart        │ January   │ Feb 2024 - Jan 2025 │ Feb-Apr 2024            │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Nike           │ May       │ Jun 2024 - May 2025 │ Jun-Aug 2024            │
  ├────────────────┼───────────┼─────────────────────┼─────────────────────────┤
  │ Costco         │ August    │ Sep 2024 - Aug 2025 │ Sep-Nov 2024            │
  └────────────────┴───────────┴─────────────────────┴─────────────────────────┘
  This means "Q2 FY25" maps to DIFFERENT calendar months depending on the company.

  Period Schema

  Each guidance entry needs:

  # PERIOD IDENTIFICATION (Required)
  period:
    type: "quarter" | "annual" | "half" | "other"
    fiscal_year: 2025                    # The FY number
    fiscal_quarter: 2                    # 1-4 for quarters, null for annual

    # Calendar mapping (derived from company FYE)
    calendar_start: "2025-01-01"         # When this period STARTS
    calendar_end: "2025-03-31"           # When this period ENDS

    # Temporal status (relative to analysis date)
    status: "future" | "current" | "past"  # Is this period complete?

  # COMPANY FISCAL CONTEXT (Required)
  company:
    ticker: "AAPL"
    fiscal_year_end_month: 9             # September = 9
    fiscal_year_end_day: 30              # Last Saturday of September typically

  # GUIDANCE METADATA
  guidance:
    given_date: "2025-02-05"             # When this guidance was issued
    metric: "EPS"
    value_low: 1.50
    value_high: 1.70
    value_mid: 1.60
    currency: "USD"
    basis: "non-GAAP adjusted"

  Period Status Logic

  Given:
    - Today's date (or PIT date for prediction)
    - Period's calendar_end date

  Status:
    IF calendar_end > today + 30 days  → "future"   (guidance for upcoming)
    IF calendar_end > today            → "current"  (in-progress period)
    IF calendar_end <= today           → "past"     (should have actuals)

  Why This Matters:
  ┌─────────┬─────────────────────────────────────────────────────────────┐
  │ Status  │                         Implication                         │
  ├─────────┼─────────────────────────────────────────────────────────────┤
  │ future  │ Pure guidance - no actuals yet to compare                   │
  ├─────────┼─────────────────────────────────────────────────────────────┤
  │ current │ Period in progress - guidance still "live"                  │
  ├─────────┼─────────────────────────────────────────────────────────────┤
  │ past    │ Period ended - actuals should exist, can calculate surprise │
  └─────────┴─────────────────────────────────────────────────────────────┘
  Quarter vs Annual Disambiguation

  Companies often give BOTH in the same call:

  Q1 FY25 Earnings Call (Feb 2025):
  ├── Q2 FY25 Guidance (next quarter) ← QUARTERLY
  ├── FY25 Full Year Guidance         ← ANNUAL (update/maintain)
  └── Sometimes: FY26 Preliminary     ← ANNUAL (next year preview)

  Must track separately:
  ┌─────────────┬───────────────────────────┬───────────────────────────────────┐
  │ Period Type │          Covers           │          Typical Pattern          │
  ├─────────────┼───────────────────────────┼───────────────────────────────────┤
  │ Quarterly   │ Single quarter (3 months) │ Given for next quarter only       │
  ├─────────────┼───────────────────────────┼───────────────────────────────────┤
  │ Annual      │ Full fiscal year          │ Given in Q1, updated each quarter │
  ├─────────────┼───────────────────────────┼───────────────────────────────────┤
  │ Half-Year   │ H1 or H2 (6 months)       │ Some international companies      │
  ├─────────────┼───────────────────────────┼───────────────────────────────────┤
  │ Long-Range  │ Multi-year targets        │ "2027 targets", analyst days      │
  └─────────────┴───────────────────────────┴───────────────────────────────────┘
  Fiscal Year Detection

  Where to get FYE:

  1. Neo4j Company node: Check if fiscal_year_end property exists
  2. 10-K filing: Always states fiscal year end
  3. Perplexity: "{TICKER} fiscal year end month"
  4. Alpha Vantage: Company overview endpoint

  Query to check:
  MATCH (c:Company {ticker: $ticker})
  RETURN c.ticker, c.fiscal_year_end, c.fiscal_quarter_end

  If not in Neo4j, must query externally and cache in the inventory file.

  Updated Output Structure

  # Guidance Inventory: AAPL

  ## Company Fiscal Profile
  | Field | Value |
  |-------|-------|
  | Ticker | AAPL |
  | Fiscal Year End | September 30 |
  | FY25 Calendar Range | Oct 1, 2024 - Sep 30, 2025 |
  | Current Fiscal Quarter | Q2 FY25 (Jan-Mar 2025) |
  | Guidance Policy | Quarterly + Annual |

  ## Fiscal Calendar Reference
  | Fiscal Period | Calendar Start | Calendar End | Status |
  |---------------|----------------|--------------|--------|
  | Q1 FY25 | 2024-10-01 | 2024-12-31 | past |
  | Q2 FY25 | 2025-01-01 | 2025-03-31 | current |
  | Q3 FY25 | 2025-04-01 | 2025-06-30 | future |
  | Q4 FY25 | 2025-07-01 | 2025-09-30 | future |
  | FY25 Full | 2024-10-01 | 2025-09-30 | current |

  ---

  ## Active Guidance by Period

  ### FY25 Full Year (Annual)
  | Metric | Low | Mid | High | Given Date | Source | Action | Status |
  |--------|-----|-----|------|------------|--------|--------|--------|
  | EPS | $6.80 | $7.10 | $7.40 | 2025-02-05 | 8-K:000123 | RAISED | current |
  | Revenue | $380B | $390B | $400B | 2025-02-05 | 8-K:000123 | MAINTAINED | current |

  ### Q2 FY25 (Jan-Mar 2025) - CURRENT QUARTER
  | Metric | Low | Mid | High | Given Date | Source | Action | Status |
  |--------|-----|-----|------|------------|--------|--------|--------|
  | Revenue | $92B | $95B | $98B | 2025-02-05 | 8-K:000123 | INITIAL | current |
  | Gross Margin | 45.0% | 45.5% | 46.0% | 2025-02-05 | 8-K:000123 | INITIAL | current |

  ### Q1 FY25 (Oct-Dec 2024) - RESOLVED
  | Metric | Guidance Mid | Actual | Surprise | Given Date | Resolved Date |
  |--------|--------------|--------|----------|------------|---------------|
  | Revenue | $89B | $92B | +3.4% | 2024-11-01 | 2025-02-05 |
  | EPS | $1.65 | $1.72 | +4.2% | 2024-11-01 | 2025-02-05 |

  ---

  ## Guidance Timeline (Chronological)

  ### 2025-02-05: Q1 FY25 Earnings Call
  **Periods Addressed:**
  - Q1 FY25 (Oct-Dec 2024): **ACTUALS REPORTED** ← past period
  - Q2 FY25 (Jan-Mar 2025): **NEW GUIDANCE** ← future period
  - FY25 Full Year: **GUIDANCE RAISED** ← current period (in progress)

  | Period | Type | Metric | Value | Action |
  |--------|------|--------|-------|--------|
  | Q2 FY25 | Quarter | Revenue | $92B-$98B | INITIAL |
  | Q2 FY25 | Quarter | Gross Margin | 45%-46% | INITIAL |
  | FY25 | Annual | EPS | $6.80-$7.40 | RAISED (+$0.10 from prior) |
  | FY25 | Annual | Revenue | $380B-$400B | MAINTAINED |

  ### 2024-11-01: Q4 FY24 Earnings Call
  **Periods Addressed:**
  - Q4 FY24 (Jul-Sep 2024): **ACTUALS REPORTED** ← past period
  - Q1 FY25 (Oct-Dec 2024): **NEW GUIDANCE** ← future period (now past)
  - FY25 Full Year: **INITIAL ANNUAL GUIDANCE** ← anchor established

  | Period | Type | Metric | Value | Action |
  |--------|------|--------|-------|--------|
  | Q1 FY25 | Quarter | Revenue | $87B-$91B | INITIAL |
  | FY25 | Annual | EPS | $6.60-$7.30 | INITIAL (anchor) |
  | FY25 | Annual | Revenue | $380B-$400B | INITIAL (anchor) |

  ---

  ## Annual Guidance Revision History (FY25 EPS)

  | Date | Event | Low | Mid | High | Δ from Anchor | Cumulative Δ |
  |------|-------|-----|-----|------|---------------|--------------|
  | 2024-11-01 | Q4 FY24 call | $6.60 | $6.95 | $7.30 | — | — (anchor) |
  | 2025-02-05 | Q1 FY25 call | $6.80 | $7.10 | $7.40 | +$0.15 (+2.2%) | +$0.15 (+2.2%) |
  | 2025-05-05 | Q2 FY25 call | TBD | TBD | TBD | TBD | TBD |

  ---

  ## Evidence Ledger

  | # | Period | Type | Metric | Value | Source | Date | Status | Quote |
  |---|--------|------|--------|-------|--------|------|--------|-------|
  | 1 | FY25 | Annual | EPS | $6.80-$7.40 | 8-K:000123 | 2025-02-05 | current | "Full year EPS..." |
  | 2 | Q2 FY25 | Quarter | Revenue | $92B-$98B | 8-K:000123 | 2025-02-05 | current | "For Q2..." |
  | 3 | FY25 | Annual | EPS | $6.60-$7.30 | 8-K:000119 | 2024-11-01 | superseded | "Initial FY25..." |

  ---

  Key Data Model

  @dataclass
  class GuidancePeriod:
      """Represents a fiscal period that guidance covers."""
      period_type: Literal["quarter", "annual", "half", "other"]
      fiscal_year: int                    # e.g., 2025
      fiscal_quarter: Optional[int]       # 1-4 for quarters, None for annual
      calendar_start: date                # Derived from company FYE
      calendar_end: date                  # Derived from company FYE

      def status(self, as_of: date) -> Literal["future", "current", "past"]:
          if self.calendar_end < as_of:
              return "past"
          elif self.calendar_start <= as_of <= self.calendar_end:
              return "current"
          else:
              return "future"

  @dataclass
  class GuidanceEntry:
      """A single guidance data point."""
      period: GuidancePeriod
      metric: str                         # "EPS", "Revenue", etc.
      value_low: Optional[float]
      value_mid: Optional[float]
      value_high: Optional[float]
      unit: str                           # "USD", "%", "B USD"
      basis: str                          # "GAAP", "non-GAAP adjusted"

      # Citation
      source_type: str                    # "8-K", "Transcript", "News"
      source_id: str                      # accession or URL
      given_date: date                    # When guidance was issued
      quote: str                          # Exact quote

      # State
      action: Literal["INITIAL", "RAISED", "LOWERED", "MAINTAINED", "NARROWED", "WIDENED", "WITHDRAWN"]
      superseded_by: Optional[str]        # ID of newer guidance if superseded

  Fiscal Year End Detection Query

  // Check if FYE is stored on Company node
  MATCH (c:Company {ticker: $ticker})
  RETURN c.fiscal_year_end_month, c.fiscal_year_end_day

  // If not, check most recent 10-K for fiscal period
  MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
  RETURN r.periodOfReport
  ORDER BY r.created DESC
  LIMIT 1

  The periodOfReport on a 10-K tells you when the fiscal year ended - e.g., 2024-09-30 means September FYE.

  ---
  Summary: Period Requirements Checklist
  ┌──────────────────────┬───────────────────────────────────────────────────────┐
  │     Requirement      │                     How Addressed                     │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Period association   │ Every entry has GuidancePeriod object                 │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Quarter vs Annual    │ period_type field distinguishes                       │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Fiscal year tracking │ fiscal_year + company fiscal_year_end_month           │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Calendar mapping     │ calendar_start / calendar_end derived from FYE        │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Future vs Past       │ status() method computes relative to analysis date    │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Supersession         │ superseded_by links to newer guidance                 │
  ├──────────────────────┼───────────────────────────────────────────────────────┤
  │ Anchor tracking      │ Q1 annual guidance marked, revisions calc'd vs anchor │
  └──────────────────────┴───────────────────────────────────────────────────────┘