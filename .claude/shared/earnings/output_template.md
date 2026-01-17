# Output Template for Earnings Attribution

Save reports to: `earnings-analysis/Companies/{TICKER}/{accession_no}.md`

---

## Report Template

```markdown
# Attribution Analysis: {TICKER} ({Company Name})

## Report Metadata
| Field | Value |
|-------|-------|
| **Accession Number** | {accession_no} |
| **Ticker** | {TICKER} |
| **Company** | {company_name} |
| **Sector / Industry** | {sector} / {industry} |
| **Form Type** | 8-K (Item 2.02) |
| **Filed** | {filed_datetime} |
| **Analysis Date** | {current_datetime_iso} |
| **Market Cap** | {mkt_cap} |
| **Market Session** | {session} |

Note: Analysis Date must include full ISO timestamp (e.g., `2026-01-17T21:15:30Z`), not just date.

## Returns Summary
| Metric | Value |
|--------|-------|
| Daily Adj (vs SPY) | {daily_adj}% |
| Daily Adj (vs Sector) | {daily_sector_adj}% |
| Daily Adj (vs Industry) | {daily_industry_adj}% |
| Hourly Adj (vs SPY) | {hourly_adj}% |

---

## Evidence Ledger (Required)

Every numeric claim used in Surprise Analysis, Attribution, or Historical Context must appear here with source + date.
If a value is calculated, list inputs and formula in Notes.

| Metric | Value | Source | Date | Notes |
|--------|-------|--------|------|-------|
| EPS (Actual) | {value} | {source} | {date} | |
| EPS (Consensus) | {value} | {source} | {date} | |
| Revenue (Actual) | {value} | {source} | {date} | |
| Revenue (Consensus) | {value} | {source} | {date} | |
| Guidance (Actual) | {range} | {source} | {date} | |
| Guidance (Consensus) | {value} | {source} | {date} | |

Add rows for any other numeric claims used (returns, margins, cash flow, backlog, etc.).
If guidance covers a different period than the filing (e.g., FY25 guidance in a Q4 FY24 filing), label the covered period explicitly.

---

## Executive Summary

**Why did {TICKER} stock {rise/drop} {daily_adj}% (adjusted)?**

{1-2 sentence synthesis of why the market reacted this way}

---

## Surprise Analysis

| Metric | Expected | Actual | Surprise |
|--------|----------|--------|----------|
| EPS | {consensus} | {actual} | {beat/miss %} |
| Revenue | {consensus} | {actual} | {beat/miss %} |
| Guidance | {expected} | {actual} | {above/below/in-line} |

---

## Attribution

### Primary Driver
**{Driver Name}**
- Surprise: {Expected vs Actual}
- Evidence: {Source citation with quote/paraphrase}
- Why it matters: {Brief explanation}

### Contributing Factor(s)
(Include only if applicable)
**{Factor Name}**
- Evidence: {Source citation}
- Impact: {How it amplified/dampened the primary driver}

---

## Data Sources Used

| Source | Status | Key Finding |
|--------|--------|-------------|
| Report/Returns | Used | {summary} |
| News ({count} items) | Used/None found | {summary} |
| Transcript | Used/Not found | {summary} |
| XBRL History | Used/Not applicable | {summary} |
| Dividends | Checked/None | {summary} |
| Splits | Checked/None | {summary} |
| Perplexity | Used for {what} | {summary} |

---

## Confidence Assessment

**Overall Confidence**: {High/Medium/Insufficient}

**Reasoning**:
- {Why this confidence level}
- {What sources agreed/disagreed}
- {Any caveats or limitations}

---

## Historical Context (for future analyses)

{What did we learn about what moves this company's stock?}
{Any company-specific sensitivities identified?}
{Save this for building company-specific knowledge.}
```

---

## Company Learnings Template

After each analysis, update `earnings-analysis/Companies/{TICKER}/learnings.md`:

```markdown
# {TICKER} Driver Learnings

## Event: {accession_no} ({date})
- **Primary Driver**: {short name}
- **Surprise**: {+/-XX.X%} ({metric}) — or "N/A" if no consensus available
- **Move**: {daily_adj}%
- **Evidence**: {source quote or key value} (Source: {source}, {date})
- **Confidence**: {High/Medium/Insufficient} ({N} sources)

## Watch Next Time
- {metric} | Trigger: {condition} | Threshold from: {source of threshold} | Find in: {where to check next time}

## Notes
- {only if needed; evidence-backed facts only}
```
