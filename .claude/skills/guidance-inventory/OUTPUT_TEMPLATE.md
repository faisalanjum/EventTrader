# Output Template for Guidance Inventory

Save to: `earnings-analysis/Companies/{TICKER}/guidance-inventory.md`

## Table of Contents

1. [Main Template](#main-template)
   - Company Fiscal Profile
   - Fiscal Calendar Reference
   - Active Guidance (Current Outlook)
   - Guidance Timeline (Chronological)
   - Annual Guidance Revision History
   - Consensus Comparison
   - Evidence Ledger
   - Data Coverage
   - Notes & Assumptions
2. [Update Template (q>=2)](#update-template-q2)

---

## Main Template

```markdown
# {TICKER} Guidance Inventory

## Company Fiscal Profile

| Field | Value |
|-------|-------|
| Ticker | {TICKER} |
| Company Name | {full_name} |
| Fiscal Year End | {month} (e.g., September, December) |
| FY{current} Calendar Range | {start_date} - {end_date} |
| Current Fiscal Quarter | Q{N} FY{year} ({month}-{month} {year}) |
| Guidance Policy | Quarterly + Annual / Annual only / No guidance provided |
| Historical Beat Rate | {X}% ({n}/{total} quarters) |
| Last Updated | {ISO timestamp} |

---

## Fiscal Calendar Reference

| Fiscal Period | Calendar Start | Calendar End | Status |
|---------------|----------------|--------------|--------|
| Q1 FY{year} | {date} | {date} | past/current/future |
| Q2 FY{year} | {date} | {date} | past/current/future |
| Q3 FY{year} | {date} | {date} | past/current/future |
| Q4 FY{year} | {date} | {date} | past/current/future |
| FY{year} Full | {date} | {date} | current |

---

## Active Guidance (Current Outlook)

### FY{year} Full Year (Annual)

| Metric | Low | Mid | High | Unit | Basis | Given Date | Source | Action |
|--------|-----|-----|------|------|-------|------------|--------|--------|
| EPS | $X.XX | $X.XX | $X.XX | $/share | Non-GAAP | YYYY-MM-DD | 8-K:accession | RAISED |
| Revenue | $XB | $XB | $XB | USD | As reported | YYYY-MM-DD | 8-K:accession | MAINTAINED |

### Q{N} FY{year} (Current Quarter)

| Metric | Low | Mid | High | Unit | Basis | Given Date | Source | Action |
|--------|-----|-----|------|------|-------|------------|--------|--------|
| Revenue | $XB | $XB | $XB | USD | - | YYYY-MM-DD | 8-K:accession | INITIAL |
| Gross Margin | X% | X% | X% | % | - | YYYY-MM-DD | Transcript | INITIAL |

### Q{N-1} FY{year} - RESOLVED

Past quarters where guidance has been compared against actuals:

| Metric | Guidance Mid | Actual | Surprise | Given Date | Resolved Date |
|--------|--------------|--------|----------|------------|---------------|
| Revenue | $XB | $XB | +X.X% | YYYY-MM-DD | YYYY-MM-DD |
| EPS | $X.XX | $X.XX | +X.X% | YYYY-MM-DD | YYYY-MM-DD |

*Note: RESOLVED sections track how accurate prior guidance was. This informs Historical Beat Rate.*

---

## Guidance Timeline (Chronological)

### YYYY-MM-DD: Q{N} FY{year} Earnings Call

**Sources**: 8-K {accession}, Transcript

**Periods Addressed**:
- Q{N-1} FY{year}: ACTUALS REPORTED (past period)
- Q{N} FY{year}: NEW GUIDANCE (future period)
- FY{year} Full: GUIDANCE {ACTION} (in progress)

#### Financial Guidance Given:

| Period | Type | Metric | Value | Action | Quote |
|--------|------|--------|-------|--------|-------|
| FY{year} | Annual | EPS | $X.XX-$X.XX | RAISED | "We expect full-year..." |
| Q{N} FY{year} | Quarter | Revenue | $XB-$XB | INITIAL | "For Q{N}..." |

#### Operational Guidance Given:

| Period | Type | Metric | Value | Action | Quote |
|--------|------|--------|-------|--------|-------|
| FY{year} | Annual | Store Openings | XX-XX | MAINTAINED | "We plan to open..." |

#### Qualitative Signals:
- Tone: {Cautious / Confident / Neutral}
- Key phrases: "{quote1}", "{quote2}"
- Management confidence: {High / Medium / Low}

#### Conditions & Assumptions:
- {Any conditions mentioned, e.g., "Assumes stable FX rates"}

---

## Annual Guidance Revision History

### FY{year} EPS

| Date | Event | Low | Mid | High | Delta from Anchor | Cumulative |
|------|-------|-----|-----|------|-------------------|------------|
| YYYY-MM-DD | Q4 FY{year-1} call | $X.XX | $X.XX | $X.XX | — | — (anchor) |
| YYYY-MM-DD | Q1 FY{year} call | $X.XX | $X.XX | $X.XX | +$0.XX (+X.X%) | +$0.XX (+X.X%) |
| YYYY-MM-DD | Q2 FY{year} call | $X.XX | $X.XX | $X.XX | +$0.XX (+X.X%) | +$0.XX (+X.X%) |

### FY{year} Revenue

| Date | Event | Low | Mid | High | Delta from Anchor | Cumulative |
|------|-------|-----|-----|------|-------------------|------------|
| ... | ... | ... | ... | ... | ... | ... |

---

## Consensus Comparison (Reference Only)

| Metric | Period | Company Guide (Mid) | Street Consensus | Gap | Signal |
|--------|--------|---------------------|------------------|-----|--------|
| EPS | FY{year} | $X.XX | $X.XX | -X.X% | Below street |
| Revenue | FY{year} | $XB | $XB | +X.X% | Above street |

**Source**: Alpha Vantage EARNINGS_ESTIMATES, {date}

*Note: Consensus stored here for reference only — official tracking in prediction/attribution reports*

---

## Evidence Ledger

| # | Entry ID | Period | Type | Metric | Value | Source | Date | Status | Superseded By | Quote |
|---|----------|--------|------|--------|-------|--------|------|--------|---------------|-------|
| 1 | FY25-EPS-002 | FY{year} | Annual | EPS | $X.XX-$X.XX | 8-K:{accession} | YYYY-MM-DD | active | — | "Full year EPS..." |
| 2 | Q2-REV-001 | Q{N} FY{year} | Quarter | Revenue | $XB-$XB | 8-K:{accession} | YYYY-MM-DD | active | — | "For Q{N}..." |
| 3 | FY25-EPS-001 | FY{year} | Annual | EPS | $X.XX-$X.XX | 8-K:{old_accession} | YYYY-MM-DD | superseded | FY25-EPS-002 | "Initial FY..." |

**Status values**: active, superseded, withdrawn

**Entry ID format**: `{Period}-{Metric}-{sequence}` (e.g., FY25-EPS-001, Q2-REV-001)

**Supersession chain**: Entry 3 was superseded by Entry 1 (linked via Entry ID)

---

## Data Coverage

| Source Type | Date Range | Count |
|-------------|------------|-------|
| 8-K Filings | {earliest} - {latest} | {n} |
| Transcripts | {earliest} - {latest} | {n} |
| 10-K/10-Q | {earliest} - {latest} | {n} |
| Perplexity | {query date} | {n} |

---

## Notes & Assumptions

- All EPS figures are {GAAP / non-GAAP adjusted / specify}
- Revenue guidance {includes / excludes} {acquisition, FX impact, etc.}
- FX assumption: {current spot rates / specified rate}
- {Any other relevant assumptions}

---

*Last updated: {ISO timestamp}*
*Skill version: 1.0*
```

---

## Update Template (q>=2)

When updating an existing file, append a new section under "Guidance Timeline":

```markdown
### YYYY-MM-DD: Q{N} FY{year} Earnings Call

**Sources**: 8-K {accession}, Transcript

[... same format as above ...]
```

Then update:
1. "Last Updated" timestamp in header
2. "Active Guidance" section (replace superseded entries)
3. "Annual Guidance Revision History" (append new row)
4. "Evidence Ledger" (mark old entries as superseded, add new)
5. "Data Coverage" counts

---

*Version 1.2 | 2026-01-17 | Added Table of Contents*
