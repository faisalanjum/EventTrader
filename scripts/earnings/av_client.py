"""Standardized Alpha Vantage HTTP client with retry.

Single transport layer for all AV API calls. Handles:
- Rate limit detection and retry
- AV error response detection (Error Message / Information / Note)
- Caller-defined retry conditions (e.g., false-empty detection)
- HTTP/timeout errors with retry

Callers import fetch_av_raw() or fetch_av_json() instead of rolling their own.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

AV_BASE_URL = "https://www.alphavantage.co/query"

# ── Error detection ──────────────────────────────────────────────────────

def check_av_error(raw_text: str) -> str | None:
    """Return error message if response is an AV error payload, else None.

    AV error responses are JSON dicts with 1-2 keys, one of which is
    'Error Message', 'Information', or 'Note'.  Normal data responses
    have many keys (symbol, quarterlyEarnings, …) so len > 2.

    CSV responses (e.g., EARNINGS_CALENDAR) are not JSON and return None.
    """
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        for key in ("Error Message", "Information", "Note"):
            if key in data and len(data) <= 2:
                return str(data[key])
    return None


def is_rate_limit(error_msg: str) -> bool:
    """True if the AV error message indicates a rate limit."""
    msg = error_msg.lower()
    return "rate limit" in msg or "spreading out" in msg or "25 requests" in msg


# ── False-empty detection ────────────────────────────────────────────────

# AV silently returns valid JSON with 0 data rows under load instead of
# errors.  Empirically confirmed: 108/796 false empties at 70 req/min,
# all succeeded on retry.

_EXPECTED_LISTS: dict[str, tuple[str, ...]] = {
    "EARNINGS": ("quarterlyEarnings", "annualEarnings"),
    "EARNINGS_ESTIMATES": ("data", "estimates"),
    "INCOME_STATEMENT": ("quarterlyReports", "annualReports"),
}


def is_false_empty(data: dict, function: str, symbol: str) -> bool:
    """Detect likely transient AV false-empty responses.

    True when the response has the right symbol but all expected list
    fields are present and empty.  Only checks known endpoints.
    """
    if str(data.get("symbol", "")).upper() != symbol.upper():
        return False
    expected = _EXPECTED_LISTS.get(function)
    if not expected:
        return False
    lists = [data.get(key) for key in expected if isinstance(data.get(key), list)]
    return len(lists) > 0 and all(len(v) == 0 for v in lists)


def make_false_empty_checker(function: str, symbol: str) -> Callable[[str], bool]:
    """Create a should_retry_response callback for false-empty detection."""
    def checker(raw_text: str) -> bool:
        try:
            data = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            return False
        return is_false_empty(data, function, symbol) if isinstance(data, dict) else False
    return checker


# ── Transport ────────────────────────────────────────────────────────────

def fetch_av_raw(
    api_key: str,
    function: str,
    params: dict[str, str] | None = None,
    *,
    timeout: int = 30,
    max_retries: int = 2,
    retry_spacing: float = 2.0,
    should_retry_response: Callable[[str], bool] | None = None,
    _urlopen: Any = None,  # test injection point
) -> str | None:
    """Fetch raw response text from Alpha Vantage with retry.

    Retries on:
    - AV rate-limit error payloads
    - HTTP / URL / timeout errors
    - Caller-defined conditions (should_retry_response returns True)

    Returns raw response text on success, None after all retries exhausted
    or on non-retryable AV error.

    Args:
        should_retry_response: Optional callback called on successful (non-error)
            responses.  If it returns True and retries remain, the request is
            retried.  Use make_false_empty_checker() for false-empty detection.
        _urlopen: Test injection — replaces urllib.request.urlopen.
    """
    query_params = {"function": function, "apikey": api_key}
    if params:
        query_params.update(params)
    url = f"{AV_BASE_URL}?{urlencode(query_params)}"
    req = Request(url, headers={"User-Agent": "av-client/1.0"}, method="GET")

    opener = _urlopen or urlopen

    for attempt in range(max_retries + 1):
        # ── HTTP call ──
        try:
            with opener(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt < max_retries:
                log.warning("AV %s HTTP error (attempt %d/%d): %s — retrying in %.1fs",
                            function, attempt + 1, max_retries + 1, exc, retry_spacing)
                time.sleep(retry_spacing)
                continue
            log.error("AV %s HTTP error (final attempt %d/%d): %s",
                      function, attempt + 1, max_retries + 1, exc)
            return None

        # ── AV error detection ──
        error_msg = check_av_error(raw)
        if error_msg is not None:
            if is_rate_limit(error_msg) and attempt < max_retries:
                log.warning("AV %s rate-limited (attempt %d/%d) — retrying in %.1fs",
                            function, attempt + 1, max_retries + 1, retry_spacing)
                time.sleep(retry_spacing)
                continue
            if error_msg:
                log.error("AV %s error (attempt %d/%d): %s",
                          function, attempt + 1, max_retries + 1, error_msg[:200])
            return None

        # ── Caller-defined retry condition ──
        if should_retry_response and attempt < max_retries and should_retry_response(raw):
            log.warning("AV %s retryable response (attempt %d/%d) — retrying in %.1fs",
                        function, attempt + 1, max_retries + 1, retry_spacing)
            time.sleep(retry_spacing)
            continue

        return raw

    return None


def fetch_av_json(
    api_key: str,
    function: str,
    params: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict | None:
    """Fetch and parse AV JSON response. Convenience wrapper.

    Returns parsed dict on success, None on error or non-JSON response.
    Accepts all keyword arguments of fetch_av_raw().
    """
    raw = fetch_av_raw(api_key, function, params, **kwargs)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None
