#!/usr/bin/env python3
"""PIT-aware external data wrapper.

Current source support:
- bz-news-api (Benzinga News REST API)
- perplexity (Perplexity AI Search/Chat APIs)
- alphavantage (Alpha Vantage Earnings/Estimates/Calendar)

Output contract:
- JSON envelope with `data[]` and `gaps[]`
- In PIT mode, each item includes `available_at` and `available_at_source`
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
try:
    from pit_time import parse_timestamp, to_new_york_iso, NY_TZ
except ModuleNotFoundError:
    # Support module-style imports (e.g., `import scripts.pit_fetch`)
    from scripts.pit_time import parse_timestamp, to_new_york_iso, NY_TZ

# --- Benzinga constants ---
API_URL = "https://api.benzinga.com/api/v2/news"
DEFAULT_LIMIT = 50
DEFAULT_MAX_PAGES = 10
DEFAULT_LOOKBACK_MINUTES = 24 * 60

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "macro": (
        "macro",
        "economy",
        "economic",
        "fed",
        "federal reserve",
        "inflation",
        "cpi",
        "rates",
        "interest rate",
        "gdp",
        "treasury",
    ),
    "oil": (
        "oil",
        "crude",
        "wti",
        "brent",
        "opec",
        "energy",
        "natural gas",
    ),
}

# --- Alpha Vantage constants ---
AV_BASE_URL = "https://www.alphavantage.co/query"

AV_OP_FUNCTION: dict[str, str] = {
    "earnings": "EARNINGS",
    "estimates": "EARNINGS_ESTIMATES",
    "calendar": "EARNINGS_CALENDAR",
}

# Horizons that represent historical (already-reported) fiscal periods in EARNINGS_ESTIMATES
AV_HISTORICAL_HORIZONS: set[str] = {"historical fiscal quarter", "historical fiscal year"}

# Coarse PIT revision buckets — ordered from most-recent to oldest.
# Each tuple: (days_before_fiscal_period_end, API_field_name)
# These are frozen snapshots anchored to the fiscal period end date.
AV_ESTIMATE_BUCKETS: list[tuple[int, str]] = [
    (7, "eps_estimate_average_7_days_ago"),
    (30, "eps_estimate_average_30_days_ago"),
    (60, "eps_estimate_average_60_days_ago"),
    (90, "eps_estimate_average_90_days_ago"),
]

# --- Perplexity constants ---
PPLX_SEARCH_URL = "https://api.perplexity.ai/search"
PPLX_CHAT_URL = "https://api.perplexity.ai/chat/completions"

PPLX_OP_MODEL: dict[str, str | None] = {
    "search": None,           # POST /search, no model
    "ask": "sonar-pro",
    "reason": "sonar-reasoning-pro",
    "research": "sonar-deep-research",
}


# ── Shared helpers ──

def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_dt(value: Any) -> datetime | None:
    return parse_timestamp(value)


def _to_new_york_iso(dt: datetime) -> str:
    return to_new_york_iso(dt)


# ── Perplexity date helpers ──

def _to_pplx_date(iso_date: str) -> str:
    """YYYY-MM-DD -> MM/DD/YYYY for Perplexity date filters."""
    parts = iso_date.split("-")
    return f"{parts[1]}/{parts[2]}/{parts[0]}"


def _pit_to_pplx_date(pit_str: str) -> str | None:
    """PIT ISO8601 -> MM/DD/YYYY (the PIT day in NY tz, for 'before' filter)."""
    dt = _parse_dt(pit_str)
    if dt is None:
        return None
    return dt.astimezone(NY_TZ).strftime("%m/%d/%Y")


# ── Benzinga helpers ──

def _as_names(value: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
            continue
        if isinstance(item, dict):
            name = item.get("name") or item.get("symbol")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def _normalize_bz_item(raw: Any) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    if not isinstance(raw, dict):
        return None, None, "raw item is not an object"

    created_raw = raw.get("created")
    created_dt = _parse_dt(created_raw)
    if created_dt is None:
        ident = raw.get("id", "unknown")
        return None, None, f"item {ident} missing/unparseable created timestamp"

    symbols = _as_names(raw.get("stocks")) or _as_names(raw.get("symbols"))
    channels = _as_names(raw.get("channels"))
    tags = _as_names(raw.get("tags"))

    body = raw.get("body")
    if not isinstance(body, str):
        body = None

    item = {
        "available_at": _to_new_york_iso(created_dt),
        "available_at_source": "provider_metadata",
        "id": str(raw.get("id", "")),
        "title": raw.get("title"),
        "teaser": raw.get("teaser"),
        "body": body,
        "url": raw.get("url"),
        "symbols": symbols,
        "channels": channels,
        "tags": tags,
        "created": created_raw,
        "updated": raw.get("updated"),
    }
    return item, created_dt, None


# ── Perplexity normalizer ──

def _normalize_pplx_result(raw: Any) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    """Normalize a Perplexity search result into envelope item.

    Works for both /search results and /chat/completions search_results.
    Uses `date` (publication date) for PIT. `last_updated` is preserved as
    metadata but never used for available_at derivation.
    """
    if not isinstance(raw, dict):
        return None, None, "raw item is not an object"

    date_raw = raw.get("date")
    if not isinstance(date_raw, str) or not date_raw.strip():
        url = raw.get("url", "unknown")
        return None, None, f"item {url} missing publication date field"

    pub_dt: datetime | None = None
    text = date_raw.strip()
    # Date-only YYYY-MM-DD -> start-of-day NY tz
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        try:
            pub_dt = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=NY_TZ)
        except ValueError:
            pass
    if pub_dt is None:
        pub_dt = _parse_dt(date_raw)
    if pub_dt is None:
        return None, None, f"unparseable date: {date_raw}"

    item = {
        "available_at": _to_new_york_iso(pub_dt),
        "available_at_source": "provider_metadata",
        "url": raw.get("url"),
        "title": raw.get("title"),
        "snippet": raw.get("snippet", ""),
        "date": date_raw,
        "last_updated": raw.get("last_updated"),
    }
    return item, pub_dt, None


# ── Alpha Vantage normalizers ──

def _normalize_av_quarterly(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, datetime | None, str | None]:
    """Normalize a quarterlyEarnings item into PIT envelope format.

    The AV EARNINGS API returns 6 fields per quarterly item:
    fiscalDateEnding, reportedDate, reportedEPS, estimatedEPS, surprise, surprisePercentage.
    No reportTime field exists — all items use date-only available_at.
    """
    reported_date = raw.get("reportedDate")
    if not isinstance(reported_date, str) or not reported_date.strip():
        fiscal = raw.get("fiscalDateEnding", "unknown")
        return None, None, f"quarterly item {fiscal} missing reportedDate"

    # Date-only available_at (AV EARNINGS has no time-of-day info)
    try:
        pub_dt = datetime.strptime(reported_date.strip(), "%Y-%m-%d").replace(tzinfo=NY_TZ)
    except ValueError:
        return None, None, f"unparseable reportedDate: {reported_date}"

    item = {
        "available_at": _to_new_york_iso(pub_dt),
        "available_at_source": "provider_metadata",
        "record_type": "quarterly_earnings",
        "fiscalDateEnding": raw.get("fiscalDateEnding"),
        "reportedDate": reported_date,
        "reportedEPS": raw.get("reportedEPS"),
        "estimatedEPS": raw.get("estimatedEPS"),
        "surprise": raw.get("surprise"),
        "surprisePercentage": raw.get("surprisePercentage"),
    }
    return item, pub_dt, None


def _normalize_av_annual(raw: dict[str, Any], available_at_iso: str | None = None) -> dict[str, Any]:
    """Normalize an annualEarnings item.

    When available_at_iso is provided (cross-referenced from Q4 quarterly reportedDate),
    the item can go into data[] with a valid available_at. Otherwise it goes to gaps[].
    """
    item: dict[str, Any] = {
        "record_type": "annual_earnings",
        "fiscalDateEnding": raw.get("fiscalDateEnding"),
        "reportedEPS": raw.get("reportedEPS"),
    }
    if available_at_iso is not None:
        item["available_at"] = available_at_iso
        item["available_at_source"] = "cross_reference"
    return item


def _normalize_av_estimate(raw: dict[str, Any], available_at_iso: str | None = None,
                           at_source: str = "provider_metadata") -> dict[str, Any]:
    """Normalize an EARNINGS_ESTIMATES item.

    The raw AV API returns flat fields: date, horizon, eps_estimate_average, etc.
    When available_at_iso is provided (cross-referenced from EARNINGS reportedDate),
    the item can be PIT-filtered. Otherwise uses current time (open mode).
    """
    if available_at_iso is None:
        available_at_iso = _to_new_york_iso(datetime.now(timezone.utc))
        at_source = "provider_metadata"
    return {
        "available_at": available_at_iso,
        "available_at_source": at_source,
        "record_type": "estimate",
        "fiscalDateEnding": raw.get("date"),
        "horizon": raw.get("horizon"),
        # Core consensus
        "eps_estimate_average": raw.get("eps_estimate_average"),
        "eps_estimate_high": raw.get("eps_estimate_high"),
        "eps_estimate_low": raw.get("eps_estimate_low"),
        "eps_estimate_analyst_count": raw.get("eps_estimate_analyst_count"),
        "revenue_estimate_average": raw.get("revenue_estimate_average"),
        "revenue_estimate_high": raw.get("revenue_estimate_high"),
        "revenue_estimate_low": raw.get("revenue_estimate_low"),
        "revenue_estimate_analyst_count": raw.get("revenue_estimate_analyst_count"),
        # Revision tracking (frozen snapshots anchored to fiscal period end date)
        "eps_estimate_average_7_days_ago": raw.get("eps_estimate_average_7_days_ago"),
        "eps_estimate_average_30_days_ago": raw.get("eps_estimate_average_30_days_ago"),
        "eps_estimate_average_60_days_ago": raw.get("eps_estimate_average_60_days_ago"),
        "eps_estimate_average_90_days_ago": raw.get("eps_estimate_average_90_days_ago"),
        "eps_estimate_revision_up_trailing_7_days": raw.get("eps_estimate_revision_up_trailing_7_days"),
        "eps_estimate_revision_down_trailing_7_days": raw.get("eps_estimate_revision_down_trailing_7_days"),
        "eps_estimate_revision_up_trailing_30_days": raw.get("eps_estimate_revision_up_trailing_30_days"),
        "eps_estimate_revision_down_trailing_30_days": raw.get("eps_estimate_revision_down_trailing_30_days"),
    }


def _normalize_av_calendar_row(row: dict[str, str]) -> dict[str, Any]:
    """Normalize a parsed CSV row from EARNINGS_CALENDAR (open mode only)."""
    return {
        "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
        "available_at_source": "provider_metadata",
        "record_type": "earnings_calendar",
        "symbol": row.get("symbol"),
        "name": row.get("name"),
        "reportDate": row.get("reportDate"),
        "fiscalDateEnding": row.get("fiscalDateEnding"),
        "estimate": row.get("estimate"),
        "currency": row.get("currency"),
        "timeOfTheDay": row.get("timeOfTheDay"),
    }


def _select_estimate_bucket(fiscal_end_date: str, pit_dt: datetime) -> tuple[str, str, str] | None:
    """Select the best EPS revision bucket for a coarse PIT query.

    The AV EARNINGS_ESTIMATES revision fields (_7_days_ago, _30_days_ago, etc.)
    are frozen snapshots anchored to the fiscal period end date.

    Selects the nearest bucket whose date does not exceed the PIT date.

    Args:
        fiscal_end_date: YYYY-MM-DD from the estimate item's 'date' field.
        pit_dt: Timezone-aware PIT datetime.

    Returns:
        (field_name, bucket_label, available_at_iso) or None if no bucket covers PIT.
    """
    fiscal_end_date = fiscal_end_date.strip()
    try:
        fiscal_end = datetime.strptime(fiscal_end_date, "%Y-%m-%d").replace(tzinfo=NY_TZ)
    except ValueError:
        return None

    pit_ny_date = pit_dt.astimezone(NY_TZ).strftime("%Y-%m-%d")

    if pit_ny_date >= fiscal_end_date:
        # PIT at or after fiscal end → use final consensus (eps_estimate_average)
        return ("eps_estimate_average", "at_period_end", _to_new_york_iso(fiscal_end))

    # PIT before fiscal end → find nearest bucket that doesn't exceed PIT
    for days, field in AV_ESTIMATE_BUCKETS:
        bucket_dt = fiscal_end - timedelta(days=days)
        bucket_date = bucket_dt.strftime("%Y-%m-%d")
        if bucket_date <= pit_ny_date:
            return (field, f"{days}d_before_period_end", _to_new_york_iso(bucket_dt))

    return None  # PIT more than 90 days before fiscal end


# ── Alpha Vantage API + processing ──

def _fetch_av(api_key: str, function: str, params: dict[str, str], timeout: int) -> str:
    """Call Alpha Vantage REST API and return raw response text."""
    query_params = {"function": function, "apikey": api_key}
    query_params.update(params)
    url = f"{AV_BASE_URL}?{urlencode(query_params)}"
    req = Request(url, headers={"User-Agent": "pit-fetch/1.0"}, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _load_av_input(path: str) -> str:
    """Load AV response from local file for offline testing."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _check_av_error(raw_text: str) -> str | None:
    """Detect AV error/rate-limit payloads. Returns error message or None."""
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError):
        return None  # Not JSON — could be CSV (calendar), let caller handle
    if isinstance(data, dict):
        # AV returns {"Note": "..."} for rate limits, {"Error Message": "..."} for bad requests
        if "Error Message" in data:
            return data["Error Message"]
        if "Note" in data and len(data) == 1:
            return data["Note"]
        if "Information" in data and len(data) == 1:
            return data["Information"]
    return None


def _build_fiscal_date_map(quarterly_earnings: list[dict[str, Any]]) -> dict[str, str]:
    """Build fiscalDateEnding → reportedDate mapping from quarterlyEarnings.

    Used for cross-referencing: annual earnings and historical estimates
    derive their available_at from the matching quarterly reportedDate.
    """
    mapping: dict[str, str] = {}
    for q in quarterly_earnings:
        fiscal = q.get("fiscalDateEnding")
        reported = q.get("reportedDate")
        if isinstance(fiscal, str) and fiscal.strip() and isinstance(reported, str) and reported.strip():
            mapping[fiscal.strip()] = reported.strip()
    return mapping


def _process_av_response(raw_text: str, op: str, pit_dt: datetime | None,
                         envelope: dict[str, Any], args: argparse.Namespace) -> None:
    """Process Alpha Vantage response: normalize items + apply PIT filter.

    For --op earnings: quarterly items are PIT-filtered by reportedDate (date-only).
    Annual items are cross-referenced with Q4 quarterly reportedDate to derive available_at.

    For --op estimates in PIT mode: coarse PIT using revision buckets anchored to
    fiscal period end date. Selects the nearest bucket (7/30/60/90 days before period end)
    that doesn't exceed PIT. Forward-looking estimates are gapped.

    For --op calendar: always gapped in PIT mode (forward-looking snapshot).
    """
    # Check for AV error payloads (rate limit, bad API key, invalid symbol)
    av_error = _check_av_error(raw_text)
    if av_error:
        envelope["gaps"].append({"type": "upstream_error", "reason": f"Alpha Vantage: {av_error}"})
        return

    if op == "earnings":
        data = json.loads(raw_text)
        pit_date_str = pit_dt.astimezone(NY_TZ).strftime("%Y-%m-%d") if pit_dt else None
        quarterly_items = data.get("quarterlyEarnings", [])

        # Build cross-reference map for annual earnings
        fiscal_date_map = _build_fiscal_date_map(quarterly_items)

        # Quarterly earnings — PIT filterable by reportedDate (date-only)
        pit_excluded = 0
        invalid = 0
        for raw in quarterly_items:
            item, pub_dt, err = _normalize_av_quarterly(raw)
            if err:
                invalid += 1
                continue
            if pit_dt is not None and pub_dt is not None:
                # Date-only: exclude PIT day entirely (AV has no time-of-day info)
                date_str = (raw.get("reportedDate") or "").strip()
                if date_str >= pit_date_str:
                    pit_excluded += 1
                    continue
            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

        # Annual earnings — cross-reference with Q4 quarterly reportedDate
        annual_items = data.get("annualEarnings", [])
        annual_resolved = 0
        annual_unresolved = 0
        annual_pit_excluded = 0
        for raw in annual_items:
            fiscal = (raw.get("fiscalDateEnding") or "").strip()
            reported_date = fiscal_date_map.get(fiscal)
            if reported_date:
                # Derive available_at from matching Q4 quarterly reportedDate
                try:
                    ann_pub_dt = datetime.strptime(reported_date, "%Y-%m-%d").replace(tzinfo=NY_TZ)
                except ValueError:
                    annual_unresolved += 1
                    continue
                available_at_iso = _to_new_york_iso(ann_pub_dt)
                if pit_dt is not None:
                    if reported_date >= pit_date_str:
                        annual_pit_excluded += 1
                        continue
                item = _normalize_av_annual(raw, available_at_iso=available_at_iso)
                envelope["data"].append(item)
                annual_resolved += 1
            else:
                annual_unresolved += 1

        if pit_excluded > 0:
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": f"{pit_excluded} quarterly items post-PIT",
            })
        if annual_pit_excluded > 0:
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": f"{annual_pit_excluded} annual items post-PIT (cross-ref Q4 reportedDate)",
            })
        if annual_unresolved > 0:
            envelope["gaps"].append({
                "type": "unverifiable",
                "reason": f"{annual_unresolved} annual items without matching Q4 quarterly reportedDate",
            })
        if invalid > 0:
            envelope["gaps"].append({
                "type": "unverifiable",
                "reason": f"{invalid} quarterly items with unparseable/missing reportedDate",
            })

    elif op == "estimates":
        data = json.loads(raw_text)
        estimates = data.get("estimates", [])

        if pit_dt is not None:
            # Coarse PIT: use revision buckets anchored to fiscal period end date.
            # For each historical estimate, select the nearest bucket whose date
            # does not exceed PIT, then return the PIT-appropriate consensus value.
            est_resolved = 0
            est_forward_gapped = 0
            est_no_bucket = 0
            est_bucket_missing = 0

            for raw in estimates:
                horizon = (raw.get("horizon") or "").strip()
                fiscal = (raw.get("date") or "").strip()

                if horizon not in AV_HISTORICAL_HORIZONS:
                    # Forward-looking: gap (current snapshot, not PIT-safe)
                    est_forward_gapped += 1
                    continue

                if not fiscal:
                    est_no_bucket += 1
                    continue

                bucket = _select_estimate_bucket(fiscal, pit_dt)
                if bucket is None:
                    est_no_bucket += 1
                    continue

                field_name, bucket_label, available_at_iso = bucket

                # Read the PIT-appropriate consensus value
                pit_value = raw.get(field_name)
                if pit_value is None or str(pit_value).strip() in ("", "None", "-"):
                    est_bucket_missing += 1
                    continue

                # PIT-safe item: only include identifiers + the selected
                # bucket value.  All other fields (eps_estimate_average,
                # revenue_*, bucket columns closer to fiscal end) may
                # represent post-PIT information and must be excluded.
                item: dict[str, Any] = {
                    "available_at": available_at_iso,
                    "available_at_source": "coarse_pit",
                    "record_type": "estimate",
                    "fiscalDateEnding": raw.get("date"),
                    "horizon": raw.get("horizon"),
                    "pit_consensus_eps": str(pit_value).strip(),
                    "pit_bucket": bucket_label,
                }
                envelope["data"].append(item)
                est_resolved += 1

            if est_forward_gapped > 0:
                envelope["gaps"].append({
                    "type": "pit_excluded",
                    "reason": f"{est_forward_gapped} forward-looking estimates gapped "
                              "(current snapshot, not PIT-safe)",
                })
            if est_no_bucket > 0:
                envelope["gaps"].append({
                    "type": "pit_excluded",
                    "reason": f"{est_no_bucket} estimates outside coarse PIT bucket range "
                              "(>90 days before fiscal period end or missing date)",
                })
            if est_bucket_missing > 0:
                envelope["gaps"].append({
                    "type": "unverifiable",
                    "reason": f"{est_bucket_missing} estimates with missing revision "
                              "bucket value",
                })
        else:
            # Open mode: pass all estimates through
            for raw in estimates:
                item = _normalize_av_estimate(raw)
                envelope["data"].append(item)

    elif op == "calendar":
        if pit_dt is not None:
            # PIT mode: gap entirely (forward-looking snapshot)
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": "EARNINGS_CALENDAR is a forward-looking snapshot — not PIT-verifiable.",
            })
        else:
            # CSV parsing
            import csv
            import io
            reader = csv.DictReader(io.StringIO(raw_text))
            symbol_filter = (args.symbol or "").upper()
            for row in reader:
                if symbol_filter and row.get("symbol", "").upper() != symbol_filter:
                    continue
                item = _normalize_av_calendar_row(row)
                envelope["data"].append(item)


# ── Filters (BZ-specific) ──

def _matches_filters(
    item: dict[str, Any],
    tickers: set[str],
    channels: set[str],
    tags: set[str],
    keywords: list[str],
) -> bool:
    item_symbols = {
        s.strip().upper()
        for s in item.get("symbols", [])
        if isinstance(s, str) and s.strip()
    }
    item_channels = {
        c.strip().lower()
        for c in item.get("channels", [])
        if isinstance(c, str) and c.strip()
    }
    item_tags = {
        t.strip().lower()
        for t in item.get("tags", [])
        if isinstance(t, str) and t.strip()
    }

    if tickers and not (item_symbols & tickers):
        return False
    if channels and not (item_channels & channels):
        return False
    if tags and not (item_tags & tags):
        return False

    if keywords:
        blob_parts: list[str] = []
        for key in ("title", "teaser", "body"):
            val = item.get(key)
            if isinstance(val, str):
                blob_parts.append(val)
        blob_parts.extend(item.get("channels", []))
        blob_parts.extend(item.get("tags", []))
        blob = " ".join(str(v) for v in blob_parts).lower()
        if not any(k in blob for k in keywords):
            return False

    return True


# ── API fetchers ──

def _fetch_bz_items(api_key: str, args: argparse.Namespace) -> list[Any]:
    page = 0
    # Over-fetch raw pages so PIT/filtering can still satisfy small limits.
    page_size = max(1, min(99, max(args.limit, DEFAULT_LIMIT)))
    max_pages = max(1, args.max_pages)
    all_items: list[Any] = []

    while page < max_pages:
        params: dict[str, Any] = {
            "token": api_key,
            "page": page,
            "pageSize": page_size,
            "displayOutput": "full",
            "sort": "updated:desc",
        }
        if args.date_from:
            params["dateFrom"] = args.date_from
        if args.date_to:
            params["dateTo"] = args.date_to
        if args.updated_since is not None:
            params["updatedSince"] = args.updated_since
        if args.tickers:
            params["tickers"] = ",".join(args.tickers)

        url = f"{API_URL}?{urlencode(params)}"
        request = Request(url, headers={"accept": "application/json", "user-agent": "pit-fetch/1.0"})
        with urlopen(request, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, list):
            raise ValueError("Benzinga response is not a JSON array")
        if not payload:
            break

        all_items.extend(payload)
        if len(payload) < page_size:
            break
        page += 1

    return all_items


def _build_pplx_date_filters(args: argparse.Namespace) -> dict[str, str]:
    """Build server-side date filters for Perplexity API (coarse prefilter)."""
    filters: dict[str, str] = {}
    if args.pit:
        pplx_date = _pit_to_pplx_date(args.pit)
        if pplx_date:
            filters["search_before_date_filter"] = pplx_date
    elif args.date_to:
        filters["search_before_date_filter"] = _to_pplx_date(args.date_to)
    if args.date_from:
        filters["search_after_date_filter"] = _to_pplx_date(args.date_from)
    return filters


def _fetch_pplx_search(api_key: str, args: argparse.Namespace) -> list[Any]:
    """POST /search — raw ranked results, no model."""
    all_results: list[Any] = []
    date_filters = _build_pplx_date_filters(args)
    for query in args.queries:
        body: dict[str, Any] = {
            "query": query,
            "max_results": min(20, max(1, args.max_results)),
        }
        body.update(date_filters)
        if args.search_recency:
            body["search_recency_filter"] = args.search_recency
        if args.search_domains:
            body["search_domain_filter"] = _csv(args.search_domains)
        if args.search_mode != "web":
            body["search_mode"] = args.search_mode
        if args.pplx_max_tokens is not None:
            body["max_tokens"] = args.pplx_max_tokens
        if args.pplx_max_tokens_per_page is not None:
            body["max_tokens_per_page"] = args.pplx_max_tokens_per_page

        data = json.dumps(body).encode("utf-8")
        req = Request(PPLX_SEARCH_URL, data=data, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "pit-fetch/1.0",
        }, method="POST")
        with urlopen(req, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        results = payload.get("results", [])
        if isinstance(results, list):
            all_results.extend(results)
    return all_results


def _fetch_pplx_chat(api_key: str, args: argparse.Namespace, model: str) -> tuple[list[Any], str, list[str]]:
    """POST /chat/completions — synthesized answer + search_results."""
    combined_query = "\n".join(args.queries)
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": combined_query}],
    }
    date_filters = _build_pplx_date_filters(args)
    body.update(date_filters)
    if args.search_recency:
        body["search_recency_filter"] = args.search_recency
    if args.search_domains:
        body["search_domain_filter"] = _csv(args.search_domains)
    if args.search_mode != "web":
        body["search_mode"] = args.search_mode
    if args.search_context_size != "low":
        body["web_search_options"] = {"search_context_size": args.search_context_size}

    data = json.dumps(body).encode("utf-8")
    req = Request(PPLX_CHAT_URL, data=data, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "pit-fetch/1.0",
    }, method="POST")
    with urlopen(req, timeout=max(args.timeout, 60)) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    search_results = payload.get("search_results", [])
    answer = ""
    choices = payload.get("choices", [])
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message", {})
        answer = msg.get("content", "")
    citations = payload.get("citations", [])

    return (
        search_results if isinstance(search_results, list) else [],
        answer if isinstance(answer, str) else "",
        citations if isinstance(citations, list) else [],
    )


# ── Input file loaders ──

def _load_input_items(path: str) -> list[Any]:
    """Load BZ input file (JSON array or {items: []})."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("items"), list):
        return raw["items"]
    raise ValueError("input file must contain a JSON array or {'items': [...]}")


def _load_pplx_input(path: str, is_chat: bool) -> tuple[list[Any], str, list[str]]:
    """Load Perplexity input file. For chat ops, also extracts answer + citations."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items: list[Any] = []
    answer = ""
    citations: list[str] = []

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if is_chat:
            items = raw.get("search_results", raw.get("results", raw.get("items", [])))
            answer = raw.get("answer", "")
            citations = raw.get("citations", [])
        else:
            items = raw.get("results", raw.get("items", []))

    if not isinstance(items, list):
        items = []
    if not isinstance(answer, str):
        answer = ""
    if not isinstance(citations, list):
        citations = []

    return items, answer, citations


# ── Parser ──

def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PIT-aware external data fetch wrapper")
    p.add_argument("--source", required=True,
                   choices=["bz-news-api", "benzinga", "benzinga-news", "perplexity", "alphavantage"])
    p.add_argument("--pit", help="ISO8601 PIT timestamp (optional)")
    p.add_argument("--date-from", dest="date_from", help="YYYY-MM-DD")
    p.add_argument("--date-to", dest="date_to", help="YYYY-MM-DD")
    p.add_argument("--updated-since", dest="updated_since", type=int, help="Unix timestamp")
    p.add_argument(
        "--lookback-minutes",
        type=int,
        default=DEFAULT_LOOKBACK_MINUTES,
        help=f"Default updated-since lookback when no date range provided (default: {DEFAULT_LOOKBACK_MINUTES})",
    )
    p.add_argument("--tickers", help="Comma-separated symbols")
    p.add_argument("--channels", help="Comma-separated channel filters")
    p.add_argument("--tags", help="Comma-separated tag filters")
    p.add_argument("--keywords", help="Comma-separated keyword contains filters")
    p.add_argument("--themes", help="Comma-separated theme aliases (macro,oil)")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Max search results returned (default: {DEFAULT_LIMIT}). Chat ops append synthesis separately.")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help=f"Max pages fetched (default: {DEFAULT_MAX_PAGES})")
    p.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    p.add_argument("--input-file", help="Optional local JSON file for offline testing")
    # Perplexity / Alpha Vantage operation mode
    p.add_argument("--op", choices=["search", "ask", "reason", "research",
                                     "earnings", "estimates", "calendar"],
                   help="Operation mode (perplexity: search/ask/reason/research; alphavantage: earnings/estimates/calendar)")
    # Alpha Vantage-specific
    p.add_argument("--symbol", help="Single ticker symbol (alphavantage)")
    p.add_argument("--horizon", choices=["3month", "6month", "12month"],
                   default="3month", help="Calendar horizon (alphavantage --op calendar)")
    p.add_argument("--query", action="append", dest="queries",
                   help="Search query (repeatable for multi-pass)")
    p.add_argument("--max-results", type=int, default=10, dest="max_results",
                   help="Results per query (1-20, /search only)")
    p.add_argument("--search-recency", dest="search_recency",
                   choices=["hour", "day", "week", "month", "year"])
    p.add_argument("--search-domains", dest="search_domains",
                   help="Comma-separated domain allowlist or -prefixed denylist")
    p.add_argument("--search-mode", dest="search_mode",
                   choices=["web", "academic", "sec"], default="web")
    p.add_argument("--search-context-size", dest="search_context_size",
                   choices=["low", "medium", "high"], default="low")
    # Content extraction budget (Perplexity /search only — controls snippet depth)
    p.add_argument("--max-tokens", type=int, default=None, dest="pplx_max_tokens",
                   help="Total content extraction budget across all results (Perplexity /search). API default ~10000.")
    p.add_argument("--max-tokens-per-page", type=int, default=None, dest="pplx_max_tokens_per_page",
                   help="Content extraction per result (Perplexity /search). API default ~4096.")
    return p


def main() -> None:
    parser = _make_parser()
    args = parser.parse_args()
    args.limit = max(1, args.limit)

    is_pplx = args.source == "perplexity"
    is_av = args.source == "alphavantage"

    # BZ-specific filter setup (only when not perplexity or alphavantage)
    if not is_pplx and not is_av:
        args.tickers = [t.upper() for t in _csv(args.tickers)]
        requested_tickers = set(args.tickers)
        requested_channels = {c.lower() for c in _csv(args.channels)}
        requested_tags = {t.lower() for t in _csv(args.tags)}
        requested_keywords = [k.lower() for k in _csv(args.keywords)]
        requested_themes = [t.lower() for t in _csv(args.themes)]

        for theme in requested_themes:
            requested_keywords.extend(THEME_KEYWORDS.get(theme, (theme,)))

        if (
            args.updated_since is None
            and not args.date_from
            and not args.date_to
            and not args.input_file
        ):
            args.updated_since = int(
                (datetime.now(timezone.utc) - timedelta(minutes=args.lookback_minutes)).timestamp()
            )

    envelope: dict[str, Any] = {
        "data": [],
        "gaps": [],
    }

    pit_dt = _parse_dt(args.pit) if args.pit else None
    if args.pit and pit_dt is None:
        envelope["gaps"].append({
            "type": "invalid_pit",
            "reason": f"Unparseable --pit timestamp: {args.pit}",
        })

    raw_items: list[Any] = []
    answer_text = ""
    citations_list: list[str] = []

    # ── Fetch raw data ──
    if is_pplx:
        if not args.op:
            envelope["gaps"].append({"type": "config", "reason": "--op required for perplexity"})
        elif not args.queries:
            envelope["gaps"].append({"type": "config", "reason": "--query required"})
        elif args.input_file:
            try:
                is_chat = PPLX_OP_MODEL.get(args.op) is not None
                raw_items, answer_text, citations_list = _load_pplx_input(
                    args.input_file, is_chat
                )
            except Exception as exc:
                envelope["gaps"].append({
                    "type": "input_error",
                    "reason": f"Failed to load input file: {exc}",
                })
        else:
            _load_env()
            api_key = os.getenv("PERPLEXITY_API_KEY")
            if not api_key:
                envelope["gaps"].append({
                    "type": "config", "reason": "PERPLEXITY_API_KEY not set",
                })
            else:
                model = PPLX_OP_MODEL[args.op]
                try:
                    if model is None:
                        raw_items = _fetch_pplx_search(api_key, args)
                    else:
                        raw_items, answer_text, citations_list = _fetch_pplx_chat(
                            api_key, args, model
                        )
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    envelope["gaps"].append({
                        "type": "upstream_error",
                        "reason": f"Perplexity API failed: {exc}",
                    })
                except Exception as exc:
                    envelope["gaps"].append({
                        "type": "internal_error",
                        "reason": f"Unexpected: {exc}",
                    })
    elif is_av:
        # Alpha Vantage path — fetch + normalize + PIT filter in one pass
        av_ops = {"earnings", "estimates", "calendar"}
        if not args.op or args.op not in av_ops:
            envelope["gaps"].append({"type": "config", "reason": f"--op required, one of: {sorted(av_ops)}"})
        else:
            symbol = args.symbol or (args.tickers.split(",")[0].strip().upper() if getattr(args, 'tickers', None) and args.tickers else None)
            if not symbol:
                envelope["gaps"].append({"type": "config", "reason": "--symbol required for alphavantage"})
            else:
                function = AV_OP_FUNCTION[args.op]
                av_params: dict[str, str] = {"symbol": symbol}
                if args.op == "calendar" and args.horizon:
                    av_params["horizon"] = args.horizon

                raw_text: str | None = None
                api_key: str | None = None
                try:
                    if args.input_file:
                        raw_text = _load_av_input(args.input_file)
                    else:
                        _load_env()
                        api_key = os.getenv("ALPHAVANTAGE_API_KEY")
                        if not api_key:
                            envelope["gaps"].append({"type": "config", "reason": "ALPHAVANTAGE_API_KEY not set"})
                        else:
                            raw_text = _fetch_av(api_key, function, av_params, args.timeout)
                except (HTTPError, URLError, TimeoutError) as exc:
                    envelope["gaps"].append({"type": "upstream_error", "reason": f"AV API failed: {exc}"})

                if raw_text is not None:
                    _process_av_response(raw_text, args.op, pit_dt, envelope, args)
    else:
        # Existing BZ path
        if args.input_file:
            try:
                raw_items = _load_input_items(args.input_file)
            except Exception as exc:
                envelope["gaps"].append({
                    "type": "input_error",
                    "reason": f"Failed to load input file: {exc}",
                })
        else:
            _load_env()
            api_key = os.getenv("BENZINGANEWS_API_KEY") or os.getenv("BENZINGA_API_KEY")
            if not api_key:
                envelope["gaps"].append({
                    "type": "config",
                    "reason": "BENZINGANEWS_API_KEY is not set",
                })
            else:
                try:
                    raw_items = _fetch_bz_items(api_key, args)
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    envelope["gaps"].append({
                        "type": "upstream_error",
                        "reason": f"Benzinga API request failed: {exc}",
                    })
                except Exception as exc:
                    envelope["gaps"].append({
                        "type": "internal_error",
                        "reason": f"Unexpected wrapper error: {exc}",
                    })

    # ── Normalize + filter (BZ + Perplexity only; AV handles this in _process_av_response) ──
    invalid_created = 0
    pit_excluded = 0

    if is_av:
        pass  # AV normalization + PIT filtering already done in _process_av_response
    elif is_pplx:
        seen_urls: set[str] = set()
        pit_date_str = pit_dt.astimezone(NY_TZ).strftime("%Y-%m-%d") if pit_dt else None

        for raw in raw_items:
            item, pub_dt, err = _normalize_pplx_result(raw)
            if err:
                invalid_created += 1
                continue
            if item is None or pub_dt is None:
                invalid_created += 1
                continue

            # Two-tier PIT filtering:
            #   Full timestamp (ISO8601 with time+tz): exact comparison
            #   Date-only (YYYY-MM-DD): exclude PIT day entirely
            if pit_dt is not None:
                date_raw_str = (item.get("date") or "").strip()
                if len(date_raw_str) == 10:  # date-only YYYY-MM-DD
                    if date_raw_str >= pit_date_str:
                        pit_excluded += 1
                        continue
                else:  # full timestamp
                    if pub_dt > pit_dt:
                        pit_excluded += 1
                        continue

            # Dedup by URL
            url = item.get("url") or ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

        # Synthesis item for chat ops (open mode only, appended separately from --limit)
        if args.op and args.op != "search" and answer_text:
            if pit_dt is None:
                synthesis_item = {
                    "record_type": "synthesis",
                    "answer": answer_text,
                    "citations": citations_list,
                    "available_at": _to_new_york_iso(datetime.now(timezone.utc)),
                    "available_at_source": "provider_metadata",
                }
                envelope["data"].append(synthesis_item)
            # PIT mode: synthesis excluded (available_at = now > PIT)
    else:
        seen_ids: set[str] = set()

        for raw in raw_items:
            item, created_dt, err = _normalize_bz_item(raw)
            if err:
                invalid_created += 1
                continue
            if item is None or created_dt is None:
                invalid_created += 1
                continue

            if pit_dt is not None and created_dt > pit_dt:
                pit_excluded += 1
                continue

            if not _matches_filters(
                item, requested_tickers, requested_channels, requested_tags, requested_keywords
            ):
                continue

            key = f"{item.get('id')}::{item.get('available_at')}"
            if key in seen_ids:
                continue
            seen_ids.add(key)
            envelope["data"].append(item)
            if len(envelope["data"]) >= args.limit:
                break

    # BZ/Perplexity gap summaries (AV handles its own gaps in _process_av_response)
    if not is_av:
        if invalid_created:
            envelope["gaps"].append({
                "type": "unverifiable",
                "reason": (
                    f"Dropped {invalid_created} item(s) with missing/unparseable "
                    f"{'date' if is_pplx else 'created'} timestamp"
                ),
            })
        if pit_excluded:
            envelope["gaps"].append({
                "type": "pit_excluded",
                "reason": f"Dropped {pit_excluded} item(s) published after PIT cutoff",
            })
    if not envelope["data"] and not any(g["type"] == "no_data" for g in envelope["gaps"]):
        envelope["gaps"].append({
            "type": "no_data",
            "reason": "No items matched the query and PIT constraints",
        })

    # Debug metadata -> stderr (not consumed by agents or pit_gate.py)
    if is_av:
        meta: dict[str, Any] = {
            "source": "alphavantage",
            "op": args.op,
            "mode": "pit" if args.pit else "open",
            "pit": args.pit,
            "symbol": args.symbol,
        }
    elif is_pplx:
        meta = {
            "source": "perplexity",
            "op": args.op,
            "mode": "pit" if args.pit else "open",
            "pit": args.pit,
            "model": PPLX_OP_MODEL.get(args.op) if args.op else None,
            "queries": args.queries,
            "search_mode": args.search_mode,
        }
    else:
        meta = {
            "source": "bz-news-api",
            "mode": "pit" if args.pit else "open",
            "pit": args.pit,
            "coverage": {
                "date_from": args.date_from,
                "date_to": args.date_to,
                "updated_since": args.updated_since,
            },
            "query": {
                "tickers": args.tickers,
                "channels": sorted(requested_channels),
                "tags": sorted(requested_tags),
                "keywords": requested_keywords,
                "themes": requested_themes,
                "limit": args.limit,
            },
        }
    print(json.dumps(meta), file=sys.stderr)

    # Contract output -> stdout (data + gaps only, per DataSubAgents section 4.7)
    print(json.dumps(envelope))


if __name__ == "__main__":
    main()
