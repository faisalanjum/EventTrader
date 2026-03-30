#!/usr/bin/env python3
"""Shared FYE month resolver — Redis → SEC refresh → Yahoo fallback.

Extracted from build_consensus.py / build_prior_financials.py to avoid
three copies of the same logic. Returns the day<=5-adjusted FYE month
suitable for _compute_fiscal_dates() and period_to_fiscal().

Usage:
    from fye_month import get_fye_month
    fye = get_fye_month("CRM", gaps=[])
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_fye_month(ticker: str, gaps: list | None = None) -> int | None:
    """Get fiscal year end month (day<=5 adjusted for 52-week calendars).

    Resolution order:
      1. Redis fiscal_year_end:{TICKER}.month_adj — pre-adjusted, from sec_quarter_cache_loader
      2. SEC auto-refresh if not cached (~1s, 2 API calls)
      3. Yahoo info.lastFiscalYearEnd — manual day<=5 adjustment
      4. None + gap

    Returns adjusted month (1-12) or None.
    """
    if gaps is None:
        gaps = []
    ticker = ticker.upper()

    # Tier 1: Redis
    try:
        import redis as redis_mod
        r = redis_mod.Redis(
            host=os.environ.get("REDIS_HOST", "192.168.40.72"),
            port=int(os.environ.get("REDIS_PORT", "31379")),
            decode_responses=True,
        )
        raw = r.get(f"fiscal_year_end:{ticker}")
        if raw:
            return json.loads(raw).get("month_adj")

        # Auto-refresh from SEC if not cached
        try:
            scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from sec_quarter_cache_loader import refresh_ticker
            refresh_ticker(r, ticker)
            raw = r.get(f"fiscal_year_end:{ticker}")
            if raw:
                return json.loads(raw).get("month_adj")
        except Exception:
            pass
    except Exception:
        pass

    # Tier 2: Yahoo
    try:
        import yfinance as yf
        fye_ts = yf.Ticker(ticker).info.get("lastFiscalYearEnd")
        if fye_ts:
            dt = datetime.fromtimestamp(fye_ts, tz=timezone.utc)
            month = dt.month
            if dt.day <= 5:
                month = month - 1 if month > 1 else 12
            return month
    except Exception:
        pass

    # Tier 3: give up
    if gaps is not None:
        gaps.append({"type": "fiscal_calendar_missing",
                     "reason": f"Could not determine FYE month for {ticker} (Redis + Yahoo both failed)"})
    return None
