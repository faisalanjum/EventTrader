#!/usr/bin/env python3
"""
Shared utilities for earnings scripts.
DRY: connection, error formatting, validation.
"""
import os
from pathlib import Path
from contextlib import contextmanager
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]

def load_env():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)

def get_neo4j_config():
    return (
        os.getenv("NEO4J_URI", "bolt://localhost:30687"),
        os.getenv("NEO4J_USERNAME", "neo4j"),
        os.getenv("NEO4J_PASSWORD")
    )

@contextmanager
def neo4j_session():
    """Context manager for Neo4j session. Yields (session, error_string)."""
    uri, user, password = get_neo4j_config()
    if not password:
        yield None, error("CONFIG", "NEO4J_PASSWORD not set", "Check .env file")
        return
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            yield session, None
        driver.close()
    except Exception as e:
        yield None, parse_exception(e, uri)

def error(code: str, msg: str, hint: str = "") -> str:
    """Structured error: ERROR|CODE|MESSAGE|HINT"""
    return f"ERROR|{code}|{msg}|{hint}" if hint else f"ERROR|{code}|{msg}"

def ok(code: str, msg: str, hint: str = "") -> str:
    """Structured OK (no data but not error): OK|CODE|MESSAGE|HINT"""
    return f"OK|{code}|{msg}|{hint}" if hint else f"OK|{code}|{msg}"

def parse_exception(e: Exception, uri: str = "") -> str:
    """Convert exception to structured error."""
    err_str = str(e).lower()
    err_type = type(e).__name__
    if "parse" in err_str or "date" in err_str or "text cannot be parsed" in err_str:
        return error("INVALID_DATE", "Cannot parse date", "Use YYYY-MM-DD format")
    if "connection" in err_str or "unavailable" in err_str or "refused" in err_str:
        return error("CONNECTION", "Database unavailable", f"Check Neo4j at {uri}")
    return error(err_type, str(e))

def fmt(v, dec: int = 2) -> str:
    """Format number or return N/A."""
    return f"{v:.{dec}f}" if v is not None else "N/A"

def vol_status(days) -> str:
    """Volatility status based on day count."""
    return "OK" if days and days >= 60 else ("INSUFFICIENT" if days else "NO_DATA")

def calendar_to_fiscal(cal_year: int, cal_quarter: int, fiscal_month_end: int) -> tuple:
    """
    EXACT algorithm from EarningsCallTranscripts.py (lines 683-687).
    Converts calendar year/quarter to fiscal year/quarter.
    """
    month = [3, 6, 9, 12][cal_quarter - 1]
    fiscal_year = cal_year + 1 if month > fiscal_month_end else cal_year
    fiscal_q = ((month - fiscal_month_end - 1) % 12) // 3 + 1
    return fiscal_year, fiscal_q


def calculate_fiscal_period(period_date: str, fye_month: int, fye_day: int = 1, reported: bool = True) -> tuple:
    """
    Calculate fiscal year and quarter for a given date.

    Uses EXACT algorithm from EarningsCallTranscripts.py calendar_to_fiscal().

    Args:
        period_date: Date string (YYYY-MM-DD or ISO format)
        fye_month: Fiscal year end month (1-12)
        fye_day: Unused, kept for API compatibility
        reported: If True (default), returns the quarter being REPORTED
                  (8-K filed in Q2 reports Q1 results)

    Returns:
        (fiscal_year, fiscal_quarter) e.g., (2024, "Q1")

    Examples (AAPL, FYE September = 9, reported=True):
        8-K filed 2023-02-02 -> FY2023 Q1 (reports Oct-Dec results)
        8-K filed 2023-05-04 -> FY2023 Q2 (reports Jan-Mar results)
        8-K filed 2023-08-03 -> FY2023 Q3 (reports Apr-Jun results)
        8-K filed 2023-11-02 -> FY2023 Q4 (reports Jul-Sep results)
    """
    from datetime import date

    # Parse date
    if isinstance(period_date, str):
        period_date = period_date[:10]
        d = date.fromisoformat(period_date)
    else:
        d = period_date

    fye_month = int(fye_month)

    # Convert date to calendar year and quarter
    cal_year = d.year
    cal_quarter = (d.month - 1) // 3 + 1  # 1-4

    # Use EXACT algorithm from EarningsCallTranscripts.py
    fiscal_year, fiscal_q = calendar_to_fiscal(cal_year, cal_quarter, fye_month)

    # For 8-K earnings, return the REPORTED quarter (one quarter back)
    if reported:
        if fiscal_q == 1:
            fiscal_year -= 1
            fiscal_q = 4
        else:
            fiscal_q -= 1

    return fiscal_year, f"Q{fiscal_q}"
