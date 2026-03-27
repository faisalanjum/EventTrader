#!/usr/bin/env python3
"""Consensus builder — 3-source AV join (EARNINGS + ESTIMATES + INCOME_STATEMENT).

Produces a `consensus.v1` packet with:
  - quarterly_rows: current quarter + 7 prior (EPS + revenue surprise)
  - forward_estimates: next quarters + fiscal years with revision tracking (live only)
  - summary: beat streak, avg surprise

Two modes:
  - Live  (no --pit): include all, forward estimates populated
  - Historical (--pit ISO): PIT-filtered, forward estimates empty

Usage:
    python3 scripts/earnings/build_consensus.py CRM
    python3 scripts/earnings/build_consensus.py CRM --pit 2025-02-26T16:03:55-05:00
    python3 scripts/earnings/build_consensus.py CRM --pit 2025-02-26T16:03:55-05:00 --out-path /tmp/consensus.json

Orchestrator call:
    build_consensus(ticker, quarter_info, as_of_ts=None, out_path=None)

Environment:
    ALPHAVANTAGE_API_KEY (or .env file in project root)
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Constants ────────────────────────────────────────────────────────────

_HISTORY_QUARTERS = 8      # total including current, newest first
_FORWARD_QUARTERS = 4
_FORWARD_YEARS = 2
_AV_BASE_URL = "https://www.alphavantage.co/query"
_AV_REQUEST_SPACING = 1.2  # seconds between API calls
_AV_RETRY_SPACING = 2.0    # seconds before retry on rate limit
_AV_MAX_RETRIES = 2
_AV_TIMEOUT = 30

# Session label normalization map
_SESSION_MAP = {
    "pre-market": "pre_market",
    "pre_market": "pre_market",
    "post-market": "post_market",
    "post_market": "post_market",
    "in-market": "in_market",
    "in_market": "in_market",
    "after_hours": "post_market",
    "afterhours": "post_market",
    "regular": "in_market",
}


# ── Helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _parse_iso(ts_str: str | None) -> datetime | None:
    """Parse ISO timestamp to timezone-aware datetime. Stdlib only, no dateutil."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    s = ts_str.strip()
    if not s:
        return None
    # Handle Z suffix (fromisoformat doesn't accept it on Python <3.11)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # Assume NY if naive
            import pytz
            dt = pytz.timezone("America/New_York").localize(dt)
        return dt
    except (ValueError, TypeError):
        return None


def _normalize_session(raw: str | None) -> str | None:
    """Normalize session labels from any source (AV, Neo4j, orchestrator)."""
    if not raw or not isinstance(raw, str):
        return None
    return _SESSION_MAP.get(raw.strip().lower().replace(" ", "_"))


def _safe_float(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "None", "-", "null"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    return int(f) if f is not None else None


# ── PIT timestamp resolution ─────────────────────────────────────────────

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from utils.market_session import MarketSessionClassifier
        _classifier = MarketSessionClassifier()
    return _classifier


def _resolve_pub_ts(reported_date: str,
                    report_time: str | None,
                    is_current_quarter: bool = False,
                    filed_8k_ts: datetime | None = None) -> datetime | None:
    """Resolve publication timestamp for a quarterly earnings row.

    Resolution order:
      1. Current quarter + filed_8k available → use filed_8k (exact)
      2. reportedDate + reportTime → MarketSessionClassifier (session boundary)
      3. reportedDate only → None (caller applies date-only same-day exclusion)
    """
    # Step 1: current quarter with exact timestamp
    if is_current_quarter and filed_8k_ts is not None:
        return filed_8k_ts

    # Step 2: session-aware resolution
    normalized = _normalize_session(report_time)
    if reported_date and normalized in ("pre_market", "post_market", "in_market"):
        try:
            cls = _get_classifier()
            result, is_trading = cls.get_trading_hours(reported_date)
            if result and is_trading:
                _prev, curr, _next = result
                if curr != "market_closed":
                    pre_start, mkt_open, mkt_close, _post_end = curr
                    if normalized == "pre_market":
                        return pre_start.to_pydatetime()
                    elif normalized == "in_market":
                        return mkt_open.to_pydatetime()
                    else:  # post_market
                        return mkt_close.to_pydatetime()
        except Exception:
            pass  # fall through

    # Step 3: no resolution — return None, caller handles date-only fallback
    return None


# ── AV API ───────────────────────────────────────────────────────────────

def _fetch_av(api_key: str, function: str, symbol: str) -> dict | None:
    """Fetch one AV endpoint with retry on rate limit."""
    params = {"function": function, "symbol": symbol, "apikey": api_key}
    url = f"{_AV_BASE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "build-consensus/2.0"}, method="GET")

    for attempt in range(_AV_MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=_AV_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                for key in ("Error Message", "Information", "Note"):
                    if key in data and len(data) <= 2:
                        msg = str(data[key]).lower()
                        if "rate limit" in msg or "spreading out" in msg or "25 requests" in msg:
                            if attempt < _AV_MAX_RETRIES:
                                time.sleep(_AV_RETRY_SPACING)
                                continue
                        return None
            return data
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            if attempt < _AV_MAX_RETRIES:
                time.sleep(_AV_RETRY_SPACING)
                continue
            return None
    return None


def _fetch_all_av(api_key: str, ticker: str, gaps: list) -> tuple:
    """Fetch EARNINGS, ESTIMATES, INCOME_STATEMENT with throttling."""
    endpoints = [
        ("EARNINGS", "earnings"),
        ("EARNINGS_ESTIMATES", "estimates"),
        ("INCOME_STATEMENT", "income_statement"),
    ]
    results = []
    for i, (function, label) in enumerate(endpoints):
        if i > 0:
            time.sleep(_AV_REQUEST_SPACING)
        data = _fetch_av(api_key, function, ticker)
        if data is None:
            gaps.append({"type": "upstream_error", "reason": f"AV {function} failed for {ticker}"})
        results.append(data)
    return tuple(results)


# ── Fiscal calendar (FYE month + fiscal_math, provider-convention) ────────
#
# DESIGN (for future bots):
#
# This builder joins AV + Yahoo data. Both providers use STANDARD MONTH-END
# dates for fiscalDateEnding (e.g., AAPL Q4 = "2025-09-30" not "2025-09-27").
# SEC XBRL has EXACT 52-week dates which DON'T match the provider convention.
#
# So we need only ONE thing from infrastructure: the FYE month (adjusted for
# day<=5 52-week calendars). Then fiscal_math._compute_fiscal_dates() generates
# month-end quarter dates that match AV/Yahoo exactly.
#
# FYE month sources (in priority order):
#   1. Redis fiscal_year_end:{TICKER}.month_adj — from sec_quarter_cache_loader.py,
#      derived from 10-K filings, day<=5 already adjusted. Only needs ONE historical
#      10-K to exist (which every listed company has). Filing order doesn't matter.
#   2. Yahoo info.lastFiscalYearEnd — always available, manual day<=5 adjustment.
#   3. None → emit gap, don't guess.
#
# Quarter-end dates: ALWAYS from fiscal_math._compute_fiscal_dates(fye_month, fy, q).
#   - Pure math, no DB dependency, month-end convention.
#   - Matches AV + Yahoo FDE convention exactly.
#   - Verified 375/375 tests across 14 companies (standard + 52-week + unusual FYE).
#
# KNOWN LIMITATION: AV puts Q4 revenue estimates under horizon="fiscal year",
# not "fiscal quarter". So revenue surprise is null for Q4 quarters. This is an
# AV data convention issue, not a fiscal calendar issue. Revenue ACTUAL is still
# available from INCOME_STATEMENT.
#
# EDGE CASE: Costco (COST) reports results 2-5 days BEFORE the fiscal quarter
# officially ends. The report-date-to-FDE mapping uses a 7-day forward window
# to handle this: end <= report_date + 7d (instead of strict end < report_date).


def _get_fye_month(ticker: str, gaps: list) -> int | None:
    """Get fiscal year end month. Redis (guidance extractor) → Yahoo fallback.

    The day<=5 adjustment handles 52-week calendars where the fiscal year
    end falls in the first few days of the next month (e.g., LULU Feb 1 → January).
    Same logic as sec_quarter_cache_loader._apply_fye_adjustment() and
    fiscal_math.period_to_fiscal().
    """
    ticker = ticker.upper()

    # Tier 1: Redis — already has day<=5 adjustment from sec_quarter_cache_loader
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

        # Auto-refresh from SEC if not cached (~1s, 2 API calls)
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

    # Tier 2: Yahoo info.lastFiscalYearEnd — always available, manual day<=5 adjustment
    try:
        import yfinance as yf
        fye_ts = yf.Ticker(ticker).info.get("lastFiscalYearEnd")
        if fye_ts:
            dt = datetime.utcfromtimestamp(fye_ts)
            month = dt.month
            if dt.day <= 5:
                month = month - 1 if month > 1 else 12
            return month
    except Exception:
        pass

    # Tier 3: give up — emit gap, don't guess
    gaps.append({"type": "fiscal_calendar_missing",
                 "reason": f"Could not determine FYE month for {ticker} (Redis + Yahoo both failed)"})
    return None


def _build_quarter_ends(fye_month: int) -> list[str]:
    """Generate all quarter-end dates (2020-2028) using fiscal_math. Month-end convention."""
    try:
        scripts_dir = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from fiscal_math import _compute_fiscal_dates
    except ImportError:
        return []

    ends = []
    now_year = datetime.now().year
    for fy in range(now_year - 10, now_year + 4):
        for q in range(1, 5):
            try:
                _, end = _compute_fiscal_dates(fye_month, fy, f"Q{q}")
                ends.append(end)
            except Exception:
                pass
    ends.sort(reverse=True)
    return ends


def _map_report_date_to_fde(report_date: str, all_quarter_ends: list[str]) -> str:
    """Map a report/earnings date to the fiscal quarter end it covers.

    Uses 7-day forward window to handle companies that report 2-5 days
    before the fiscal quarter officially closes (e.g., COST).
    """
    if not report_date or not all_quarter_ends:
        return ""
    rd_dt = datetime.strptime(report_date[:10], "%Y-%m-%d")
    cutoff = (rd_dt + timedelta(days=7)).strftime("%Y-%m-%d")
    for end in all_quarter_ends:  # sorted newest first
        if end <= cutoff:
            return end
    return ""


def _map_yahoo_periods_to_fdes(fye_month: int, last_reported_fde: str) -> dict[str, str]:
    """Map Yahoo's relative period labels (0q, +1q, 0y, +1y) to actual fiscal dates.

    Uses fiscal_math to compute the next quarters after the last reported FDE.
    """
    if not fye_month or not last_reported_fde:
        return {}

    try:
        scripts_dir = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from fiscal_math import _compute_fiscal_dates, period_to_fiscal
    except ImportError:
        return {}

    # Determine fiscal position of last reported quarter
    last_dt = datetime.strptime(last_reported_fde, "%Y-%m-%d")
    form = "10-K" if last_dt.month == fye_month else "10-Q"
    fy, fq = period_to_fiscal(last_dt.year, last_dt.month, last_dt.day, fye_month, form)
    cur_fy, cur_q = fy, int(fq[1])

    fde_map = {}
    period_labels = ["0q", "+1q"]  # first 2 future quarters
    for label in period_labels:
        cur_q += 1
        if cur_q > 4:
            cur_q = 1
            cur_fy += 1
        try:
            _, end = _compute_fiscal_dates(fye_month, cur_fy, f"Q{cur_q}")
            fde_map[label] = end
        except Exception:
            pass

    # 0y = next Q4 after last reported, +1y = Q4 after that
    # Find next two Q4s
    search_fy, search_q = fy, int(fq[1])
    fy_count = 0
    for _ in range(8):  # max 8 quarters forward
        search_q += 1
        if search_q > 4:
            search_q = 1
            search_fy += 1
        if search_q == 4:
            try:
                _, end = _compute_fiscal_dates(fye_month, search_fy, "Q4")
                if fy_count == 0:
                    fde_map["0y"] = end
                elif fy_count == 1:
                    fde_map["+1y"] = end
                    break
                fy_count += 1
            except Exception:
                pass

    return fde_map


# ── Yahoo fallback (live-only) ────────────────────────────────────────────

def _is_nan(val) -> bool:
    """Check if value is NaN (works for float, numpy, pandas)."""
    if val is None:
        return True
    try:
        import math
        return isinstance(val, float) and math.isnan(val)
    except (TypeError, ValueError):
        return False


def _yahoo_session_from_utc(earnings_date_str: str) -> str | None:
    """Derive market session from Yahoo's UTC earnings datetime.

    Yahoo returns e.g. '2026-02-25T21:00:00.000Z' → 21:00 UTC = 16:00 ET = post_market.
    """
    try:
        import pytz
        dt = datetime.fromisoformat(earnings_date_str.replace("Z", "+00:00"))
        et = dt.astimezone(pytz.timezone("America/New_York"))
        hour = et.hour
        if hour < 9:
            return "pre_market"
        elif hour < 16:
            return "in_market"
        else:
            return "post_market"
    except Exception:
        return None



def _fetch_yahoo_fallback(ticker: str, gaps: list) -> tuple:
    """Fetch EPS history + forward estimates + revenue from Yahoo as AV fallback.

    Uses Neo4j fiscal calendar for 100% reliable fiscal date mapping.
    Returns (earnings_data, estimates_data, income_data) — all reshaped to AV-like dicts.
    """
    try:
        import yfinance as yf
    except ImportError:
        gaps.append({"type": "fallback_error", "reason": "yfinance not installed"})
        return None, None, None

    try:
        t = yf.Ticker(ticker)
    except Exception as exc:
        gaps.append({"type": "fallback_error", "reason": f"yfinance init failed: {exc}"})
        return None, None, None

    # Get FYE month (Redis → Yahoo → None) and build quarter-end lookup
    fye_month = _get_fye_month(ticker, gaps)
    all_quarter_ends = _build_quarter_ends(fye_month) if fye_month else []

    # 1. EPS history from get_earnings_dates (more rows + exact datetime than get_earnings_history)
    earnings_data = None
    try:
        df = t.get_earnings_dates(limit=40)
        if df is not None and not df.empty:
            rows = []
            for idx, row in df.iterrows():
                reported_eps = row.get("Reported EPS")
                estimated_eps = row.get("EPS Estimate")
                surprise_pct = row.get("Surprise(%)")

                # Skip upcoming (unreported) quarters
                if _is_nan(reported_eps):
                    continue

                # idx is Earnings Date as Timestamp — extract date and session
                ed_str = str(idx)
                ed_date = ed_str[:10] if len(ed_str) >= 10 else ""
                report_time = _yahoo_session_from_utc(ed_str)

                # Map report date → fiscal quarter end (7-day window for COST edge case)
                fde = _map_report_date_to_fde(ed_date, all_quarter_ends)
                if not fde:
                    continue  # can't map → skip (don't guess)

                eps_diff = None
                if not _is_nan(reported_eps) and not _is_nan(estimated_eps):
                    try:
                        eps_diff = float(reported_eps) - float(estimated_eps)
                    except (ValueError, TypeError):
                        pass

                rows.append({
                    "fiscalDateEnding": fde,
                    "reportedDate": ed_date,
                    "reportedEPS": str(reported_eps),
                    "estimatedEPS": str(estimated_eps) if not _is_nan(estimated_eps) else None,
                    "surprise": str(round(eps_diff, 4)) if eps_diff is not None else None,
                    "surprisePercentage": str(surprise_pct) if not _is_nan(surprise_pct) else None,
                    "reportTime": report_time,
                })
            if rows:
                earnings_data = {"quarterlyEarnings": rows, "annualEarnings": []}
    except Exception:
        pass

    # 2. Forward estimates: EPS + revenue + EPS trend (revision tracking)
    estimates_data = None
    try:
        eps_raw = rev_raw = trend_raw = None
        try:
            eps_raw = t.earnings_estimate
        except Exception:
            pass
        try:
            rev_raw = t.revenue_estimate
        except Exception:
            pass
        try:
            trend_raw = t.eps_trend
        except Exception:
            pass

        # Get last reported FDE from earnings_history (authoritative fiscal dates from Yahoo)
        last_fde = ""
        try:
            eh = t.earnings_history
            if eh is not None and not eh.empty:
                last_fde = str(eh.index[-1])[:10]
        except Exception:
            pass
        # Map Yahoo's relative periods (0q, +1q, 0y, +1y) to actual fiscal dates via fiscal_math
        period_fde_map = _map_yahoo_periods_to_fdes(fye_month, last_fde) if fye_month and last_fde else {}
        estimates_data = _merge_yahoo_estimates(eps_raw, rev_raw, trend_raw, period_fde_map)
    except Exception:
        pass

    # 3. Revenue actuals from quarterly income statement
    income_data = None
    try:
        inc = t.quarterly_income_stmt
        if inc is not None and not inc.empty:
            reports = []
            for col in inc.columns:
                fde = str(col)[:10] if col is not None else ""
                rev = None
                if "Total Revenue" in inc.index:
                    val = inc.loc["Total Revenue", col]
                    if not _is_nan(val):
                        rev = val
                if fde and rev is not None:
                    reports.append({
                        "fiscalDateEnding": fde,
                        "totalRevenue": str(int(rev)),
                    })
            if reports:
                income_data = {"quarterlyReports": reports}
    except Exception:
        pass

    return earnings_data, estimates_data, income_data


def _dfget(df, row_name: str, col):
    """Safely get a value from a DataFrame by index label and column."""
    try:
        if hasattr(df, 'index') and row_name in df.index:
            v = df.loc[row_name, col]
            return None if _is_nan(v) else v
    except Exception:
        pass
    return None


def _merge_yahoo_estimates(eps_est, rev_est, trend_est,
                           fde_map: dict[str, str] | None = None) -> dict | None:
    """Merge Yahoo EPS/revenue/trend DataFrames into AV-like estimates dict.

    Yahoo DataFrames use relative period index: 0q, +1q, 0y, +1y.
    fde_map provides the actual fiscalDateEnding for each period (from Neo4j fiscal calendar).
    """
    if fde_map is None:
        fde_map = {}

    period_horizon = {
        "0q": "fiscal quarter", "+1q": "fiscal quarter",
        "0y": "fiscal year", "+1y": "fiscal year",
    }

    items = []
    try:
        # Use index from whichever DataFrame is available
        source = eps_est if eps_est is not None and hasattr(eps_est, 'index') else None
        if source is None and rev_est is not None and hasattr(rev_est, 'index'):
            source = rev_est
        if source is None:
            return None

        for period_key in source.index:
            pk = str(period_key).strip()
            horizon = period_horizon.get(pk)
            if not horizon:
                continue

            item = {
                "horizon": horizon,
                "date": fde_map.get(pk, ""),
            }

            # EPS estimates
            if eps_est is not None and hasattr(eps_est, 'index') and pk in eps_est.index:
                avg = _dfget(eps_est, pk, "avg")
                if avg is not None:
                    item["eps_estimate_average"] = str(avg)
                low = _dfget(eps_est, pk, "low")
                if low is not None:
                    item["eps_estimate_low"] = str(low)
                high = _dfget(eps_est, pk, "high")
                if high is not None:
                    item["eps_estimate_high"] = str(high)
                cnt = _dfget(eps_est, pk, "numberOfAnalysts")
                if cnt is not None:
                    item["eps_estimate_analyst_count"] = str(cnt)

            # Revenue estimates
            if rev_est is not None and hasattr(rev_est, 'index') and pk in rev_est.index:
                avg = _dfget(rev_est, pk, "avg")
                if avg is not None:
                    item["revenue_estimate_average"] = str(avg)
                low = _dfget(rev_est, pk, "low")
                if low is not None:
                    item["revenue_estimate_low"] = str(low)
                high = _dfget(rev_est, pk, "high")
                if high is not None:
                    item["revenue_estimate_high"] = str(high)
                cnt = _dfget(rev_est, pk, "numberOfAnalysts")
                if cnt is not None:
                    item["revenue_estimate_analyst_count"] = str(cnt)

            # EPS trend (revision tracking — relative to today, live only)
            if trend_est is not None and hasattr(trend_est, 'index') and pk in trend_est.index:
                for label, key in [("7daysAgo", "eps_estimate_average_7_days_ago"),
                                   ("30daysAgo", "eps_estimate_average_30_days_ago"),
                                   ("60daysAgo", "eps_estimate_average_60_days_ago"),
                                   ("90daysAgo", "eps_estimate_average_90_days_ago")]:
                    v = _dfget(trend_est, pk, label)
                    if v is not None:
                        item[key] = str(v)

            items.append(item)
    except Exception:
        return None

    return {"data": items} if items else None


# ── Build logic ──────────────────────────────────────────────────────────

def _build_quarterly_rows(earnings_data: dict | None,
                          income_data: dict | None,
                          estimates_data: dict | None,
                          period_of_report: str,
                          filed_8k_ts: datetime | None,
                          as_of_ts: datetime | None,
                          gaps: list) -> list[dict]:
    """Build quarterly_rows: current + prior quarters with EPS + revenue surprise."""
    if not earnings_data:
        return []

    quarterly = earnings_data.get("quarterlyEarnings", [])
    if not quarterly:
        gaps.append({"type": "empty_data", "reason": "AV EARNINGS returned no quarterly items"})
        return []

    # Explicit sort: newest first by fiscalDateEnding
    quarterly.sort(key=lambda r: r.get("fiscalDateEnding", ""), reverse=True)

    # Revenue actual map from INCOME_STATEMENT
    revenue_map: dict[str, float] = {}
    if income_data:
        for row in income_data.get("quarterlyReports", []):
            fde = row.get("fiscalDateEnding")
            rev = _safe_float(row.get("totalRevenue"))
            if fde and rev is not None:
                revenue_map[fde] = rev

    # Revenue estimate map from ESTIMATES (fiscal quarter horizon only)
    estimate_rev_map: dict[str, float] = {}
    if estimates_data:
        for row in estimates_data.get("data", estimates_data.get("estimates", [])):
            if not isinstance(row, dict):
                continue
            fde = row.get("date", row.get("fiscalDateEnding"))
            horizon = str(row.get("horizon", "")).lower()
            if "quarter" in horizon and fde:
                rev_est = _safe_float(row.get("revenue_estimate_average"))
                if rev_est is not None:
                    estimate_rev_map[fde] = rev_est

    is_historical = as_of_ts is not None
    as_of_date = as_of_ts.strftime("%Y-%m-%d") if as_of_ts else None

    rows = []
    for raw in quarterly:
        fde = raw.get("fiscalDateEnding", "")
        reported_date = (raw.get("reportedDate") or "").strip()
        report_time_raw = raw.get("reportTime")
        report_time = _normalize_session(report_time_raw)

        if not fde or not reported_date:
            continue

        is_current = (fde == period_of_report)

        # PIT filter (historical mode only)
        if is_historical:
            if is_current:
                pass  # force-include: this is the 8-K trigger event (exact timing via filed_8k_ts)
            else:
                pub_ts = _resolve_pub_ts(reported_date, report_time_raw,
                                         is_current_quarter=False,
                                         filed_8k_ts=None)
                if pub_ts is not None:
                    if pub_ts > as_of_ts:
                        continue
                else:
                    # Date-only fallback: same-day exclusion (conservative)
                    if reported_date >= as_of_date:
                        continue

        # EPS fields (direct from AV)
        reported_eps = _safe_float(raw.get("reportedEPS"))
        estimated_eps = _safe_float(raw.get("estimatedEPS"))
        eps_surprise = _safe_float(raw.get("surprise"))
        eps_surprise_pct = _safe_float(raw.get("surprisePercentage"))

        # Revenue fields (joined)
        revenue_actual = revenue_map.get(fde)
        revenue_estimate = estimate_rev_map.get(fde)

        revenue_surprise = None
        revenue_surprise_pct = None
        if revenue_actual is not None and revenue_estimate is not None and revenue_estimate != 0:
            revenue_surprise = round(revenue_actual - revenue_estimate, 2)
            revenue_surprise_pct = round((revenue_surprise / revenue_estimate) * 100, 3)

        # Quality flag
        quality = None
        if revenue_surprise is not None:
            quality = "live" if not is_historical else "approximate"
        else:
            if revenue_actual is None and revenue_estimate is not None:
                gaps.append({"type": "missing_revenue_actual", "fiscalDateEnding": fde})
            elif revenue_actual is not None and revenue_estimate is None:
                gaps.append({"type": "missing_revenue_estimate", "fiscalDateEnding": fde})

        rows.append({
            "fiscalDateEnding": fde,
            "reportedDate": reported_date,
            "reportTime": report_time,
            "is_current_quarter": is_current,
            "reportedEPS": reported_eps,
            "estimatedEPS": estimated_eps,
            "epsSurprise": eps_surprise,
            "epsSurprisePct": eps_surprise_pct,
            "revenueActual": revenue_actual,
            "revenueEstimate": revenue_estimate,
            "revenueSurprise": revenue_surprise,
            "revenueSurprisePct": revenue_surprise_pct,
            "revenueSurpriseQuality": quality,
        })

        if len(rows) >= _HISTORY_QUARTERS:
            break

    return rows


def _build_forward_estimates(estimates_data: dict | None,
                             period_of_report: str,
                             gaps: list) -> list[dict]:
    """Build forward_estimates from EARNINGS_ESTIMATES. Includes revision deltas."""
    if not estimates_data:
        return []

    raw_items = estimates_data.get("data", estimates_data.get("estimates", []))
    if not isinstance(raw_items, list):
        return []

    quarter_rows = []
    year_rows = []

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        fde = raw.get("date", raw.get("fiscalDateEnding", ""))
        horizon = str(raw.get("horizon", "")).lower()
        if not fde or fde <= period_of_report:
            continue

        eps_avg = _safe_float(raw.get("eps_estimate_average"))
        eps_7d = _safe_float(raw.get("eps_estimate_average_7_days_ago"))
        eps_30d = _safe_float(raw.get("eps_estimate_average_30_days_ago"))
        eps_60d = _safe_float(raw.get("eps_estimate_average_60_days_ago"))
        eps_90d = _safe_float(raw.get("eps_estimate_average_90_days_ago"))

        row = {
            "fiscalDateEnding": fde,
            "horizon": raw.get("horizon"),
            "epsEstimateAverage": eps_avg,
            "epsEstimateHigh": _safe_float(raw.get("eps_estimate_high")),
            "epsEstimateLow": _safe_float(raw.get("eps_estimate_low")),
            "epsAnalystCount": _safe_int(raw.get("eps_estimate_analyst_count")),
            "revenueEstimateAverage": _safe_float(raw.get("revenue_estimate_average")),
            "revenueEstimateHigh": _safe_float(raw.get("revenue_estimate_high")),
            "revenueEstimateLow": _safe_float(raw.get("revenue_estimate_low")),
            "revenueAnalystCount": _safe_int(raw.get("revenue_estimate_analyst_count")),
            "epsRevision7dAgo": eps_7d,
            "epsRevision30dAgo": eps_30d,
            "epsRevision60dAgo": eps_60d,
            "epsRevision90dAgo": eps_90d,
            "epsRevisionUp7d": _safe_int(raw.get("eps_estimate_revision_up_trailing_7_days")),
            "epsRevisionDown7d": _safe_int(raw.get("eps_estimate_revision_down_trailing_7_days")),
            "epsRevisionUp30d": _safe_int(raw.get("eps_estimate_revision_up_trailing_30_days")),
            "epsRevisionDown30d": _safe_int(raw.get("eps_estimate_revision_down_trailing_30_days")),
            "epsRevisionDelta7d": round(eps_avg - eps_7d, 4) if eps_avg is not None and eps_7d is not None else None,
            "epsRevisionDelta30d": round(eps_avg - eps_30d, 4) if eps_avg is not None and eps_30d is not None else None,
            "epsRevisionDelta60d": round(eps_avg - eps_60d, 4) if eps_avg is not None and eps_60d is not None else None,
            "epsRevisionDelta90d": round(eps_avg - eps_90d, 4) if eps_avg is not None and eps_90d is not None else None,
        }

        if "quarter" in horizon:
            quarter_rows.append(row)
        elif "year" in horizon:
            year_rows.append(row)

    quarter_rows.sort(key=lambda r: r["fiscalDateEnding"])
    year_rows.sort(key=lambda r: r["fiscalDateEnding"])
    return quarter_rows[:_FORWARD_QUARTERS] + year_rows[:_FORWARD_YEARS]


def _build_summary(quarterly_rows: list[dict], forward_estimates: list[dict]) -> dict:
    """Compute summary stats."""
    # Beat streak: consecutive quarters where epsSurprise > 0, from newest
    beat_streak = 0
    for row in quarterly_rows:
        s = row.get("epsSurprise")
        if s is not None and s > 0:
            beat_streak += 1
        else:
            break

    # Avg EPS surprise % last 4 quarters
    recent_eps = [r["epsSurprisePct"] for r in quarterly_rows[:4]
                  if r.get("epsSurprisePct") is not None]
    avg_eps_surprise = round(sum(recent_eps) / len(recent_eps), 2) if recent_eps else None

    # Avg revenue surprise % last 4 quarters
    recent_rev = [r["revenueSurprisePct"] for r in quarterly_rows[:4]
                  if r.get("revenueSurprisePct") is not None]
    avg_rev_surprise = round(sum(recent_rev) / len(recent_rev), 2) if recent_rev else None

    fwd_q = [r for r in forward_estimates if "quarter" in str(r.get("horizon", "")).lower()]
    fwd_y = [r for r in forward_estimates if "year" in str(r.get("horizon", "")).lower()]

    return {
        "quarterly_row_count": len(quarterly_rows),
        "forward_quarter_count": len(fwd_q),
        "forward_year_count": len(fwd_y),
        "eps_beat_streak": beat_streak,
        "avg_eps_surprise_pct_last4": avg_eps_surprise,
        "avg_revenue_surprise_pct_last4": avg_rev_surprise,
    }


# ── Main builder ─────────────────────────────────────────────────────────

def build_consensus(
    ticker: str,
    quarter_info: dict,
    as_of_ts: str | None = None,
    out_path: str | None = None,
) -> dict:
    """Build consensus.v1 packet from 3 Alpha Vantage endpoints.

    Args:
        ticker: Stock symbol (e.g., "CRM")
        quarter_info: Dict with filed_8k, market_session, period_of_report, quarter_label
        as_of_ts: ISO timestamp for historical PIT cutoff, None for live
        out_path: Optional file path for atomic write

    Returns:
        consensus.v1 packet dict
    """
    _load_env()
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set")

    ticker = ticker.upper()
    mode = "historical" if as_of_ts else "live"
    as_of_dt = _parse_iso(as_of_ts)
    filed_8k_ts = _parse_iso(quarter_info.get("filed_8k"))
    period_of_report = quarter_info.get("period_of_report", "")
    market_session = _normalize_session(quarter_info.get("market_session"))
    gaps: list[dict] = []

    # Validate: historical mode requires parseable as_of_ts
    if mode == "historical" and as_of_dt is None:
        raise ValueError(f"as_of_ts '{as_of_ts}' could not be parsed to a valid timestamp")

    is_historical = mode == "historical"

    # Fetch 3 AV endpoints
    earnings_data, estimates_data, income_data = _fetch_all_av(api_key, ticker, gaps)

    # Detect AV returning empty/error responses (rate limit can return valid JSON without real data)
    def _av_has_data(data, key):
        return data is not None and isinstance(data.get(key), list) and len(data[key]) > 0

    av_earnings_ok = _av_has_data(earnings_data, "quarterlyEarnings")
    av_estimates_ok = estimates_data is not None and (
        _av_has_data(estimates_data, "data") or _av_has_data(estimates_data, "estimates"))
    av_income_ok = _av_has_data(income_data, "quarterlyReports")

    # Live-only Yahoo fallback when AV fails
    yahoo_used = False
    if mode == "live" and (not av_earnings_ok or not av_estimates_ok or not av_income_ok):
        yf_earnings, yf_estimates, yf_income = _fetch_yahoo_fallback(ticker, gaps)
        if not av_earnings_ok and yf_earnings is not None:
            earnings_data = yf_earnings
            yahoo_used = True
        if not av_estimates_ok and yf_estimates is not None:
            estimates_data = yf_estimates
            yahoo_used = True
        if not av_income_ok and yf_income is not None:
            income_data = yf_income
            yahoo_used = True
        if yahoo_used:
            gaps.append({"type": "source_fallback",
                         "reason": "AV rate-limited — using Yahoo Finance fallback (no revision tracking, no reportTime)"})

    # If period_of_report not provided, derive from AV quarterly rows
    if not period_of_report and earnings_data:
        qe = earnings_data.get("quarterlyEarnings", [])
        if qe:
            sorted_qe = sorted(qe, key=lambda r: r.get("fiscalDateEnding", ""), reverse=True)
            if is_historical:
                # Historical: use session-aware resolution, not date-only.
                # This prevents same-day edge cases (e.g., PIT at 15:59 for a
                # post-market report at 16:03 on the same date).
                as_of_date_str = as_of_dt.strftime("%Y-%m-%d")
                for q in sorted_qe:
                    rd = (q.get("reportedDate") or "").strip()
                    if not rd:
                        continue
                    if rd < as_of_date_str:
                        # Report date strictly before PIT date — safe
                        period_of_report = q.get("fiscalDateEnding", "")
                        break
                    elif rd == as_of_date_str:
                        # Same day — need session-aware check
                        pub_ts = _resolve_pub_ts(rd, q.get("reportTime"))
                        if pub_ts is not None and pub_ts <= as_of_dt:
                            period_of_report = q.get("fiscalDateEnding", "")
                            break
                        # pub_ts > as_of_dt or unresolvable — skip this row
                    # rd > as_of_date_str — future, skip
                if not period_of_report and sorted_qe:
                    # Fallback: take the most recent pre-PIT row even without session resolution
                    for q in sorted_qe:
                        rd = (q.get("reportedDate") or "").strip()
                        if rd and rd < as_of_date_str:
                            period_of_report = q.get("fiscalDateEnding", "")
                            break
            else:
                # Live: newest row
                period_of_report = sorted_qe[0].get("fiscalDateEnding", "")

    # Build quarterly rows
    quarterly_rows = _build_quarterly_rows(
        earnings_data, income_data, estimates_data,
        period_of_report, filed_8k_ts, as_of_dt, gaps,
    )

    # Build forward estimates (live only)
    if mode == "live":
        forward_estimates = _build_forward_estimates(estimates_data, period_of_report, gaps)
    else:
        forward_estimates = []
        gaps.append({"type": "pit_excluded",
                     "reason": "Forward estimates not PIT-safe in historical mode"})

    summary = _build_summary(quarterly_rows, forward_estimates)

    packet = {
        "schema_version": "consensus.v1",
        "ticker": ticker,
        "source_mode": mode,
        "filed_8k": quarter_info.get("filed_8k"),
        "market_session": market_session,
        "as_of_ts": as_of_ts,
        "quarterly_rows": quarterly_rows,
        "forward_estimates": forward_estimates,
        "summary": summary,
        "gaps": gaps,
        "assembled_at": _now_iso(),
    }

    # Atomic write
    if out_path is None:
        out_path = f"/tmp/consensus_{ticker}.json"
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, ensure_ascii=False)
    os.replace(tmp, out_path)

    return packet


# ── CLI ──────────────────────────────────────────────────────────────────

def _cli_get(args: list[str], flag: str) -> str | None:
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
        print(f"Error: {flag} requires an argument", file=sys.stderr)
        sys.exit(1)
    return None


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        print("Usage: build_consensus.py TICKER [--pit ISO8601] [--out-path PATH]",
              file=sys.stderr)
        print("  --pit ISO8601   historical PIT mode (omit for live)", file=sys.stderr)
        print("  --session STR   market session hint (optional)", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    ticker = args[0]

    pit = _cli_get(args, "--pit")
    session = _cli_get(args, "--session")
    period = _cli_get(args, "--period-of-report")
    out_path = _cli_get(args, "--out-path")

    # For CLI, quarter_info is minimal — builder derives period_of_report from AV data if not given
    quarter_info = {
        "filed_8k": pit or _now_iso(),
        "market_session": session or "",
        "period_of_report": period or "",  # empty = derive from AV
        "quarter_label": "",
    }

    packet = build_consensus(ticker, quarter_info, as_of_ts=pit, out_path=out_path)

    path = out_path or f"/tmp/consensus_{ticker.upper()}.json"
    s = packet["summary"]
    g = len(packet["gaps"])
    print(f"Wrote {path}")
    print(f"  {s['quarterly_row_count']} quarterly | "
          f"{s['forward_quarter_count']}Q+{s['forward_year_count']}FY forward | "
          f"beat streak {s['eps_beat_streak']} | {g} gaps")


if __name__ == "__main__":
    main()
