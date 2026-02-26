"""
Pure fiscal math functions — zero external dependencies.

Extracted from get_quarterly_filings.py to allow clean imports from
guidance_ids.py, fiscal_resolve.py, and any future consumer without
triggering neo4j/dotenv top-level imports.
"""

from datetime import date
import calendar


def period_to_fiscal(period_year: int, period_month: int, period_day: int, fye_month: int, form_type: str) -> tuple:
    """
    Calculate fiscal year and quarter from 10-Q/10-K period.

    Derived from empirical analysis of actual SEC filings:
    - 10-K is ALWAYS Q4 (annual report)
    - 10-Q is ALWAYS Q1, Q2, or Q3 (quarterly reports)
    - FYE month is derived from 10-K period months (ground truth)

    Week-based fiscal calendar adjustment:
    Companies using 52/53-week calendars (e.g., Apple, retail) have quarter-end
    dates that fall in the first 1-5 days of the next calendar month. For example,
    Apple's Q2 (March quarter) might end on April 1. If we use April to calculate,
    we get Q3 (wrong). The fix: if period_day <= 5, treat it as end of previous month.

    Remaining edge cases (unfixable with formula):
    - AAP (Advance Auto Parts): Extreme 52-week calendar, quarters shift by 2-3 weeks
    - ACI (Albertsons): Extreme 52-week calendar, quarters shift by 2-3 weeks
    These companies' fiscal quarters don't align with calendar months at all.
    The dedupe logic handles these by keeping first/last occurrence per fiscal_key.

    SEC XBRL metadata anomaly (not our bug):
    - ESTC (Elastic): Filing 0001707753-24-000038 (period 2024-07-31) has
      DocumentFiscalPeriodFocus="FY" instead of "Q1". Our Q1 calculation is correct
      (July is 3 months after April FYE). The exhibit filename confirms Q1 (a25q1ex311.htm).

    Validation: 549 filings across 73 companies checked against SEC's DocumentFiscalPeriodFocus.
    Match rate: 99.1% (544/549). Only mismatches: ACI (4, known edge case), ESTC (1, SEC error).

    Args:
        period_year: Year of period end date
        period_month: Month of period end date (1-12)
        period_day: Day of period end date (1-31)
        fye_month: Fiscal year end month derived from 10-K periods
        form_type: "10-K" or "10-Q"

    Returns:
        (fiscal_year: int, fiscal_quarter: str)
    """
    # Handle week-based fiscal calendars: if period ends in first 5 days,
    # it's the END of previous month's quarter, not the start of next month
    if period_day <= 5:
        adjusted_month = period_month - 1 if period_month > 1 else 12
        adjusted_year = period_year - 1 if period_month == 1 else period_year
    else:
        adjusted_month = period_month
        adjusted_year = period_year

    # RULE 1: 10-K is always Q4
    if form_type == '10-K':
        return adjusted_year, "Q4"

    # RULE 2: For 10-Q, calculate Q1/Q2/Q3
    months_after_fye = (adjusted_month - fye_month) % 12
    if months_after_fye == 0:
        months_after_fye = 12  # Edge case: period month == fye month for 10-Q

    if months_after_fye <= 3:
        quarter = 1
    elif months_after_fye <= 6:
        quarter = 2
    else:
        quarter = 3  # 10-Q is never Q4 by definition

    # RULE 3: Fiscal year - if past FYE month, we're in next fiscal year
    if adjusted_month > fye_month:
        fiscal_year = adjusted_year + 1
    else:
        fiscal_year = adjusted_year

    return fiscal_year, f"Q{quarter}"


def _normalize_fiscal_quarter(fiscal_quarter) -> str:
    """Normalize fiscal quarter input to one of: Q1, Q2, Q3, Q4, FY."""
    fq_raw = str(fiscal_quarter).strip().upper()
    if fq_raw in {"1", "Q1"}:
        return "Q1"
    if fq_raw in {"2", "Q2"}:
        return "Q2"
    if fq_raw in {"3", "Q3"}:
        return "Q3"
    if fq_raw in {"4", "Q4"}:
        return "Q4"
    if fq_raw in {"FY", "ANNUAL", "YEAR"}:
        return "FY"
    raise ValueError(f"Unsupported fiscal_quarter: {fiscal_quarter!r}")


def _compute_fiscal_dates(fye_month: int, fiscal_year: int, fiscal_quarter: str) -> tuple:
    """
    Pure deterministic fiscal->calendar computation from FYE month.
    No database needed. Gives standard month boundaries.

    Args:
        fye_month: Fiscal year end month (1-12)
        fiscal_year: e.g. 2025
        fiscal_quarter: "Q1", "Q2", "Q3", "Q4", or "FY"

    Returns:
        (start_date: str, end_date: str) in "YYYY-MM-DD" format
    """
    fq = _normalize_fiscal_quarter(fiscal_quarter)
    fy_start_month = (fye_month % 12) + 1
    fy_start_year = fiscal_year if fye_month == 12 else fiscal_year - 1

    if fq == "FY":
        start = date(fy_start_year, fy_start_month, 1)
        _, last_day = calendar.monthrange(fiscal_year, fye_month)
        end = date(fiscal_year, fye_month, last_day)
        return start.isoformat(), end.isoformat()

    quarter_num = int(fq[1])

    q_start_month = fy_start_month + (quarter_num - 1) * 3
    q_start_year = fy_start_year
    while q_start_month > 12:
        q_start_month -= 12
        q_start_year += 1

    q_end_month = q_start_month + 2
    q_end_year = q_start_year
    while q_end_month > 12:
        q_end_month -= 12
        q_end_year += 1

    _, last_day = calendar.monthrange(q_end_year, q_end_month)
    return date(q_start_year, q_start_month, 1).isoformat(), date(q_end_year, q_end_month, last_day).isoformat()
