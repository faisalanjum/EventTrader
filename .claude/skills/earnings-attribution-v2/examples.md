# Earnings Attribution Examples

> **Note**: These examples are **illustrative only**. They demonstrate the expected output format and surprise-based reasoning. Each analysis should be driven by the actual data - derive conclusions, don't pattern match.

## Contents
- [Example 1: Guidance Miss Dominates EPS Beat](#example-1-guidance-miss-dominates-eps-beat)
- [Example 2: Double Beat with Acceleration](#example-2-double-beat-with-acceleration)
- [Example 3: Hidden Weakness in Leading Indicator](#example-3-hidden-weakness-in-leading-indicator)
- [Perplexity Query Examples](#perplexity-query-examples)

---

## Example 1: Guidance Miss Dominates EPS Beat

**Input**: Company 8-K filed after earnings

**Surprise Analysis**:
| Metric | Consensus | Actual | Surprise |
|--------|-----------|--------|----------|
| EPS | $3.52 | $3.64 | +3.41% |
| FY Guidance | $13.22 | $12.75 (midpoint) | -3.56% |

**Output**:
```
## Evidence Ledger
| Metric | Value | Source | Date | Notes |
|--------|-------|--------|------|-------|
| EPS (Actual) | $3.64 | 8-K EX-99.1 | 2024-02-01 | |
| EPS (Consensus) | $3.52 | Perplexity | 2024-01-31 | pre-filing |
| FY Guidance (Midpoint) | $12.75 | 8-K EX-99.1 | 2024-02-01 | range $12.00-$13.50 |
| FY Guidance (Consensus) | $13.22 | Perplexity | 2024-01-31 | pre-filing |
| Book-to-bill | 0.9x | Transcript Q&A | 2024-02-01 | |

## Attribution

### Primary Driver
**FY Guidance Below Expectations**
- Surprise: Consensus $13.22, Actual midpoint $12.75 (-3.56%)
- Evidence: Guidance range $12.00-$13.50 (Source: 8-K EX-99.1, 2024-02-01)
- Why it matters: Forward-looking guidance surprise (-3.56%) larger than backward-looking EPS beat (+3.41%)

### Contributing Factor
**Order Weakness Signal**
- Evidence: Book-to-bill of 0.9x indicates orders below shipments (Source: Transcript Q&A, 2024-02-01)
- Impact: Reinforced concerns about forward demand

## Confidence Assessment
**Overall Confidence**: High
- Guidance surprise magnitude clearly exceeds EPS beat
- Transcript confirms order weakness
- Price direction (down) aligns with forward-looking miss
```

**Why guidance dominates**: Absolute surprise magnitude of guidance (-3.56%) > EPS beat (+3.41%). Market prioritizes forward signals.

---

## Example 2: Double Beat with Acceleration

**Input**: Company 8-K filed after earnings

**Surprise Analysis**:
| Metric | Consensus | Actual | Surprise |
|--------|-----------|--------|----------|
| Revenue | $11.2B | $13.5B | +20.54% |
| Q3 Guidance | $12.5B | $16.0B | +28.00% |

**Output**:
```
## Evidence Ledger
| Metric | Value | Source | Date | Notes |
|--------|-------|--------|------|-------|
| Revenue (Actual) | $13.5B | 8-K EX-99.1 | 2024-05-07 | |
| Revenue (Consensus) | $11.2B | Perplexity | 2024-05-06 | pre-filing |
| Guidance (Actual) | $16.0B | 8-K EX-99.1 | 2024-05-07 | |
| Guidance (Consensus) | $12.5B | Perplexity | 2024-05-06 | pre-filing |

## Attribution

### Primary Driver
**Massive Revenue and Guidance Beats**
- Surprise: Revenue +20.54%, Guidance +28.00%
- Evidence: Revenue actual $13.5B (Source: 8-K EX-99.1, 2024-05-07)
- Evidence: Revenue consensus $11.2B (Source: Perplexity, 2024-05-06, pre-filing)
- Evidence: Guidance actual $16.0B (Source: 8-K EX-99.1, 2024-05-07)
- Evidence: Guidance consensus $12.5B (Source: Perplexity, 2024-05-06, pre-filing)
- Why it matters: Both current and forward metrics exceeded by double digits

### Contributing Factor
**Demand Narrative Confirmation**
- Evidence: CEO stated "unprecedented demand" for key products (Source: Transcript Prepared Remarks, 2024-05-07)
- Impact: Qualitative confirmation of quantitative beats

## Confidence Assessment
**Overall Confidence**: High
- Multiple metrics beat by significant margins
- Management commentary confirms demand acceleration
- Price direction (up strongly) aligns with surprise magnitude
```

**Why this moved stock**: When both backward (revenue) and forward (guidance) surprise positive by large margins, effect compounds.

---

## Example 3: Hidden Weakness in Leading Indicator

**Input**: Company 8-K filed after earnings

**Surprise Analysis**:
| Metric | Consensus | Actual | Surprise |
|--------|-----------|--------|----------|
| EPS | $2.05 | $2.12 | +3.41% |
| Guidance | Raised | Raised | In-line |
| cRPO Growth | 14% | 11% | -21.43% (relative) |

**Output**:
```
## Evidence Ledger
| Metric | Value | Source | Date | Notes |
|--------|-------|--------|------|-------|
| EPS (Actual) | $2.12 | 8-K EX-99.1 | 2024-08-01 | |
| EPS (Consensus) | $2.05 | Perplexity | 2024-07-31 | pre-filing |
| cRPO Growth (Actual) | 11% | Transcript Prepared Remarks | 2024-08-01 | |
| cRPO Growth (Consensus) | 14% | Perplexity | 2024-07-31 | pre-filing |
| Analyst Q&A focus (cRPO questions) | 5 of 10 | Transcript Q&A | 2024-08-01 | counted questions |

## Attribution

### Primary Driver
**Leading Indicator Miss (cRPO)**
- Surprise: Expected 14% growth, got 11% (-21% relative miss)
- Evidence: cRPO growth 11% vs 14% consensus (Source: Transcript Prepared Remarks, 2024-08-01; Perplexity, 2024-07-31, pre-filing)
- Why it matters: cRPO (remaining performance obligations) is forward-looking bookings metric

### Contributing Factor
**Analyst Focus on Weakness**
- Evidence: 5 of 10 analyst questions focused on cRPO slowdown (Source: Transcript Q&A, 2024-08-01)
- Impact: Analyst concern amplified market reaction to bookings miss

## Confidence Assessment
**Overall Confidence**: High
- Despite headline beat, leading indicator missed significantly
- Analyst Q&A concentration confirms this was THE concern
- Price direction (down) aligns with forward indicator miss
```

**Why this moved stock**: Headline numbers (EPS, guidance) can be positive, but market looks deeper at leading indicators. Large relative miss on bookings metric dominated.

---

## Perplexity Query Examples

**Always query Perplexity for consensus estimates** - don't rely on Neo4j News alone.

### Get Consensus Estimate
```
Query: "{Company} {TICKER} Q{N} FY{YYYY} EPS revenue estimate consensus before {date}"
Format result: Consensus EPS: $X.XX (Source: Perplexity, {YYYY-MM-DD}, pre-filing)
```

### Get Guidance Expectations
```
Query: "{Company} {TICKER} FY{YYYY} guidance analyst expectations before {date}"
Format result: Guidance consensus: $X.XX (Source: Perplexity, {YYYY-MM-DD}, pre-filing)
```

### Validate Price Reaction
```
Query: "Why did {TICKER} stock {rise/drop} on {date}"
Use to: Cross-check your surprise-based conclusion against market commentary
```

### Complex Cases (use deep_research)
```
Query: "{TICKER} earnings {date} stock reaction analysis drivers"
Use when: >10% move, conflicting sources, multiple potential drivers
```

---

*Examples loaded on-demand by earnings-attribution skill*
