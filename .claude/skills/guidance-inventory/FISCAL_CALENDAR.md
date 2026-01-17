# Fiscal Calendar Handling

Companies have different fiscal year ends. "Q2 FY25" maps to DIFFERENT calendar months depending on the company.

## Table of Contents

1. [Common Fiscal Year Ends](#common-fiscal-year-ends)
2. [Detecting Fiscal Year End](#detecting-fiscal-year-end)
3. [Building the Calendar](#building-the-calendar)
4. [Examples](#examples)
5. [Period Status Logic](#period-status-logic)
6. [Matching Guidance to Period](#matching-guidance-to-period)
7. [Edge Cases](#edge-cases)

---

## Common Fiscal Year Ends

| FYE Month | Example Companies | FY25 = Calendar | Q1 FY25 Calendar |
|-----------|-------------------|-----------------|------------------|
| December | Most companies | Jan-Dec 2025 | Jan-Mar 2025 |
| January | Walmart, HD | Feb 2024-Jan 2025 | Feb-Apr 2024 |
| March | Accenture | Apr 2024-Mar 2025 | Apr-Jun 2024 |
| May | Nike | Jun 2024-May 2025 | Jun-Aug 2024 |
| June | Microsoft | Jul 2024-Jun 2025 | Jul-Sep 2024 |
| August | Costco | Sep 2024-Aug 2025 | Sep-Nov 2024 |
| September | Apple | Oct 2024-Sep 2025 | Oct-Dec 2024 |
| October | Disney | Nov 2024-Oct 2025 | Nov-Jan 2025 |

---

## Detecting Fiscal Year End

### Option 1: Neo4j Company Node

```cypher
MATCH (c:Company {ticker: $ticker})
RETURN c.fiscal_year_end_month, c.fiscal_year_end_day
```

### Option 2: 10-K periodOfReport

```cypher
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report {formType: '10-K'})
RETURN r.periodOfReport
ORDER BY r.created DESC
LIMIT 1
```

The `periodOfReport` reveals FYE:
- `2024-09-30` → September FYE
- `2024-12-31` → December FYE
- `2025-01-31` → January FYE

### Option 3: Perplexity Fallback

```
"{ticker} fiscal year end month"
```

---

## Building the Calendar

Given FYE month, calculate quarter boundaries:

```python
def get_fiscal_calendar(fye_month: int, fiscal_year: int) -> dict:
    """
    fye_month: 1-12 (January=1, December=12)
    fiscal_year: e.g., 2025

    Returns quarter start/end dates for given fiscal year.
    """
    # Q1 starts in month AFTER FYE of previous calendar year
    q1_start_month = (fye_month % 12) + 1

    # Determine calendar year for Q1 start
    if fye_month >= 1 and fye_month <= 11:
        # FYE in Jan-Nov: FY25 Q1 starts in same calendar year as FY number minus 1
        q1_start_year = fiscal_year - 1
    else:  # December FYE
        # FYE in Dec: FY25 Q1 starts Jan of FY year
        q1_start_year = fiscal_year

    quarters = {}
    current_month = q1_start_month
    current_year = q1_start_year

    for q in range(1, 5):
        start_date = date(current_year, current_month, 1)

        # End is last day of 3rd month in quarter
        end_month = (current_month + 2 - 1) % 12 + 1
        end_year = current_year + ((current_month + 2 - 1) // 12)
        end_date = date(end_year, end_month, last_day_of_month(end_year, end_month))

        quarters[f"Q{q}"] = {
            "start": start_date,
            "end": end_date
        }

        # Move to next quarter
        current_month = (current_month + 3 - 1) % 12 + 1
        if current_month <= 3:
            current_year += 1

    return quarters
```

---

## Examples

### Apple (September FYE)

| Fiscal Period | Calendar Start | Calendar End |
|---------------|----------------|--------------|
| Q1 FY25 | 2024-10-01 | 2024-12-31 |
| Q2 FY25 | 2025-01-01 | 2025-03-31 |
| Q3 FY25 | 2025-04-01 | 2025-06-30 |
| Q4 FY25 | 2025-07-01 | 2025-09-30 |
| FY25 Full | 2024-10-01 | 2025-09-30 |

### Walmart (January FYE)

| Fiscal Period | Calendar Start | Calendar End |
|---------------|----------------|--------------|
| Q1 FY25 | 2024-02-01 | 2024-04-30 |
| Q2 FY25 | 2024-05-01 | 2024-07-31 |
| Q3 FY25 | 2024-08-01 | 2024-10-31 |
| Q4 FY25 | 2024-11-01 | 2025-01-31 |
| FY25 Full | 2024-02-01 | 2025-01-31 |

### Microsoft (June FYE)

| Fiscal Period | Calendar Start | Calendar End |
|---------------|----------------|--------------|
| Q1 FY25 | 2024-07-01 | 2024-09-30 |
| Q2 FY25 | 2024-10-01 | 2024-12-31 |
| Q3 FY25 | 2025-01-01 | 2025-03-31 |
| Q4 FY25 | 2025-04-01 | 2025-06-30 |
| FY25 Full | 2024-07-01 | 2025-06-30 |

---

## Period Status Logic

Given analysis date (or PIT date), determine period status:

```python
def get_period_status(period_end: date, as_of: date) -> str:
    """
    Determine if a fiscal period is past, current, or future.
    """
    # Calculate period start (assuming 3-month quarters)
    period_start = period_end - timedelta(days=90)  # Approximate

    if period_end < as_of:
        return "past"      # Period ended, actuals should exist
    elif period_start <= as_of <= period_end:
        return "current"   # Period in progress
    else:
        return "future"    # Period hasn't started
```

| Status | Meaning | Implication |
|--------|---------|-------------|
| `past` | Period has ended | Actuals should exist, can calculate surprise |
| `current` | Period in progress | Guidance is "live", no actuals yet |
| `future` | Period not started | Pure forward guidance |

---

## Matching Guidance to Period

When extracting guidance like "Q2 revenue of $95B":

1. Identify the fiscal quarter (Q2)
2. Identify the fiscal year (from context: FY25)
3. Look up company FYE
4. Calculate calendar dates for Q2 FY25
5. Store with both fiscal (Q2 FY25) and calendar (Jan-Mar 2025) info

---

## Edge Cases

### 53-Week Fiscal Years

Some retailers (Walmart, Costco) occasionally have 53-week fiscal years. The extra week falls in Q4. Note this in the inventory if detected.

### Mid-Year FYE Changes

Rare, but companies can change their FYE. Query for 10-K/T (transition report) filings which indicate FYE change.

### Stub Periods

After M&A or FYE change, companies may report stub periods (e.g., "7-month period ended..."). Track as `other` period type.

---

*Version 1.1 | 2026-01-17 | Added Table of Contents*
