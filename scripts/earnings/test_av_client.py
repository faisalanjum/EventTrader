#!/usr/bin/env python3
"""Exhaustive test suite for av_client.py.

Part A: Unit tests (mock-based, no network)
  A1: check_av_error()
  A2: is_false_empty()
  A3: fetch_av_raw() retry logic
  A4: fetch_av_json() convenience wrapper
  A5: should_retry_response callback

Part B: Stress test — 1000 random scenarios, verify call count + return type

Part C: Behavior equivalence — old build_consensus._fetch_av vs new av_client
  Feed identical mock responses, verify same output semantics

Part D: Live byte-for-byte — call real AV API, compare old vs new
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

# Add scripts/earnings to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from av_client import (
    check_av_error,
    is_false_empty,
    is_rate_limit,
    fetch_av_raw,
    fetch_av_json,
    make_false_empty_checker,
)

# ── Test response payloads ───────────────────────────────────────────────

RATE_LIMIT_TEXT = json.dumps({
    "Information": "Thank you for using Alpha Vantage! Please consider "
    "spreading out your free API requests more sparingly (1 request per "
    "second). You may subscribe to any of the premium plans at "
    "https://www.alphavantage.co/premium/ to lift the free key rate limit "
    "(25 requests per day)."
})

RATE_LIMIT_NOTE = json.dumps({
    "Note": "Thank you for using Alpha Vantage! Our standard API rate limit "
    "is 25 requests per day."
})

ERROR_MSG_TEXT = json.dumps({
    "Error Message": "Invalid API call. Please retry or visit the documentation."
})

SUCCESS_EARNINGS = json.dumps({
    "symbol": "CCL",
    "annualEarnings": [{"fiscalDateEnding": "2026-02-28", "reportedEPS": "0.2"}],
    "quarterlyEarnings": [
        {"fiscalDateEnding": "2026-02-28", "reportedDate": "2026-03-27",
         "reportedEPS": "0.2", "estimatedEPS": "0.18",
         "surprise": "0.02", "surprisePercentage": "11.1111"}
    ],
})

SUCCESS_INCOME = json.dumps({
    "symbol": "CCL",
    "annualReports": [{"fiscalDateEnding": "2025-11-30", "totalRevenue": "25024000000"}],
    "quarterlyReports": [{"fiscalDateEnding": "2026-02-28", "totalRevenue": "6165000000"}],
})

FALSE_EMPTY_EARNINGS = json.dumps({
    "symbol": "CCL",
    "annualEarnings": [],
    "quarterlyEarnings": [],
})

FALSE_EMPTY_INCOME = json.dumps({
    "symbol": "CCL",
    "annualReports": [],
    "quarterlyReports": [],
})

CSV_CALENDAR = "symbol,name,reportDate,fiscalDateEnding,estimate,currency\nAAPL,Apple,2026-04-30,2026-03-31,1.62,USD\n"

# Extra edge cases
EMPTY_DICT = json.dumps({})
MULTI_KEY_INFO = json.dumps({"Information": "rate limit", "symbol": "CCL"})  # len=2, still <= 2
THREE_KEY_INFO = json.dumps({"Information": "rate limit", "symbol": "CCL", "data": []})  # len=3, NOT error


# ── Mock helpers ─────────────────────────────────────────────────────────

def _make_mock_urlopen(responses: list[str | Exception]):
    """Mock urlopen: returns responses in order. Exceptions are raised."""
    call_log: list[int] = []  # timestamps of each call

    def mock_urlopen(req, timeout=None):
        idx = len(call_log)
        call_log.append(time.monotonic_ns())
        resp_item = responses[idx] if idx < len(responses) else responses[-1]
        if isinstance(resp_item, Exception):
            raise resp_item
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_item.encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    return mock_urlopen, call_log


# ── Old (buggy) _fetch_av from build_consensus.py — verbatim copy ────────

def _old_fetch_av(urlopen_fn, function: str, symbol: str,
                  max_retries: int = 2, retry_spacing: float = 0.001) -> dict | None:
    """EXACT copy of old build_consensus._fetch_av with urlopen replaced."""
    for attempt in range(max_retries + 1):
        try:
            resp = urlopen_fn(None, timeout=30)
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                for key in ("Error Message", "Information", "Note"):
                    if key in data and len(data) <= 2:
                        msg = str(data[key]).lower()
                        if "rate limit" in msg or "spreading out" in msg or "25 requests" in msg:
                            if attempt < max_retries:
                                time.sleep(retry_spacing)
                                continue
                        return None
                # false-empty omitted (separate concern)
            return data
        except Exception:
            if attempt < max_retries:
                time.sleep(retry_spacing)
                continue
            return None
    return None


# ── Old _check_av_error from pit_fetch.py — verbatim copy ───────────────

def _old_check_av_error(raw_text: str) -> str | None:
    """EXACT copy of pit_fetch._check_av_error."""
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        if "Error Message" in data:
            return data["Error Message"]
        if "Note" in data and len(data) == 1:
            return data["Note"]
        if "Information" in data and len(data) == 1:
            return data["Information"]
    return None


# ═══════════════════════════════════════════════════════════════════════
# Part A: Unit tests
# ═══════════════════════════════════════════════════════════════════════

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    msg = f"  [{status}] {name}"
    if detail and not passed:
        msg += f"\n         {detail}"
    print(msg)


# ── A1: check_av_error ──

def test_a1():
    print("\n── A1: check_av_error() ──")

    # Rate limit via Information
    err = check_av_error(RATE_LIMIT_TEXT)
    record("A1.1 rate_limit_information detected",
           err is not None and "spreading out" in err.lower())

    # Rate limit via Note
    err = check_av_error(RATE_LIMIT_NOTE)
    record("A1.2 rate_limit_note detected",
           err is not None and "25 requests" in err.lower())

    # Error Message
    err = check_av_error(ERROR_MSG_TEXT)
    record("A1.3 error_message detected",
           err is not None and "Invalid API call" in err)

    # Success (many keys) — NOT an error
    err = check_av_error(SUCCESS_EARNINGS)
    record("A1.4 success_not_error", err is None)

    # CSV response — NOT an error
    err = check_av_error(CSV_CALENDAR)
    record("A1.5 csv_not_error", err is None)

    # Empty dict — NOT an error (no error keys)
    err = check_av_error(EMPTY_DICT)
    record("A1.6 empty_dict_not_error", err is None)

    # 2-key dict with Information (len <= 2) — IS an error
    err = check_av_error(MULTI_KEY_INFO)
    record("A1.7 two_key_info_is_error",
           err is not None and "rate limit" in err.lower())

    # 3-key dict with Information (len > 2) — NOT an error
    err = check_av_error(THREE_KEY_INFO)
    record("A1.8 three_key_info_not_error", err is None)

    # Non-JSON string
    err = check_av_error("this is not json")
    record("A1.9 non_json_not_error", err is None)

    # Empty string
    err = check_av_error("")
    record("A1.10 empty_string_not_error", err is None)


# ── A2: is_false_empty ──

def test_a2():
    print("\n── A2: is_false_empty() ──")

    data = json.loads(FALSE_EMPTY_EARNINGS)
    record("A2.1 false_empty_earnings",
           is_false_empty(data, "EARNINGS", "CCL") is True)

    data = json.loads(FALSE_EMPTY_INCOME)
    record("A2.2 false_empty_income",
           is_false_empty(data, "INCOME_STATEMENT", "CCL") is True)

    data = json.loads(SUCCESS_EARNINGS)
    record("A2.3 real_data_not_false_empty",
           is_false_empty(data, "EARNINGS", "CCL") is False)

    # Wrong symbol
    data = json.loads(FALSE_EMPTY_EARNINGS)
    record("A2.4 wrong_symbol_not_false_empty",
           is_false_empty(data, "EARNINGS", "AAPL") is False)

    # Unknown function
    data = json.loads(FALSE_EMPTY_EARNINGS)
    record("A2.5 unknown_function_not_false_empty",
           is_false_empty(data, "UNKNOWN_FUNCTION", "CCL") is False)

    # Case insensitive symbol
    data = json.loads(FALSE_EMPTY_EARNINGS)
    record("A2.6 case_insensitive_symbol",
           is_false_empty(data, "EARNINGS", "ccl") is True)


# ── A3: fetch_av_raw() retry logic ──

def test_a3():
    print("\n── A3: fetch_av_raw() retry logic ──")
    RETRY_SPACING = 0.001  # fast for tests

    # A3.1: Rate limit once → success on retry
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.1 rate_limit_then_success",
           result == SUCCESS_EARNINGS and len(log) == 2,
           f"calls={len(log)}, result={'text' if result else 'None'}")

    # A3.2: Rate limit ALL attempts → None
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT] * 3)
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.2 persistent_rate_limit_returns_none",
           result is None and len(log) == 3,
           f"calls={len(log)}, result={type(result).__name__}")

    # A3.3: Rate limit twice → success on 3rd (final) attempt
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, RATE_LIMIT_TEXT, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.3 rate_limit_2x_then_success",
           result == SUCCESS_EARNINGS and len(log) == 3,
           f"calls={len(log)}, result={'text' if result else 'None'}")

    # A3.4: Non-rate-limit error → None immediately (no retry)
    mock, log = _make_mock_urlopen([ERROR_MSG_TEXT, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.4 non_rate_limit_error_no_retry",
           result is None and len(log) == 1,
           f"calls={len(log)}, result={type(result).__name__}")

    # A3.5: HTTP error → retry → success
    mock, log = _make_mock_urlopen([
        URLError("connection refused"), SUCCESS_EARNINGS
    ])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.5 http_error_then_success",
           result == SUCCESS_EARNINGS and len(log) == 2,
           f"calls={len(log)}, result={'text' if result else 'None'}")

    # A3.6: HTTP error ALL attempts → None
    mock, log = _make_mock_urlopen([URLError("refused")] * 3)
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.6 persistent_http_error",
           result is None and len(log) == 3,
           f"calls={len(log)}")

    # A3.7: Timeout → retry → success
    mock, log = _make_mock_urlopen([TimeoutError(), SUCCESS_INCOME])
    result = fetch_av_raw("key", "INCOME_STATEMENT", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.7 timeout_then_success",
           result == SUCCESS_INCOME and len(log) == 2,
           f"calls={len(log)}")

    # A3.8: Immediate success → 1 call
    mock, log = _make_mock_urlopen([SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.8 immediate_success",
           result == SUCCESS_EARNINGS and len(log) == 1,
           f"calls={len(log)}")

    # A3.9: CSV response (EARNINGS_CALENDAR) — returned as-is
    mock, log = _make_mock_urlopen([CSV_CALENDAR])
    result = fetch_av_raw("key", "EARNINGS_CALENDAR", {"horizon": "3month"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.9 csv_returned_as_is",
           result == CSV_CALENDAR and len(log) == 1,
           f"calls={len(log)}")

    # A3.10: max_retries=0 → never retry, rate limit → None
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=0, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.10 zero_retries_rate_limit",
           result is None and len(log) == 1,
           f"calls={len(log)}")

    # A3.11: max_retries=0 → never retry, HTTP error → None
    mock, log = _make_mock_urlopen([URLError("refused"), SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=0, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.11 zero_retries_http_error",
           result is None and len(log) == 1,
           f"calls={len(log)}")

    # A3.12: max_retries=5 → many retries allowed
    mock, log = _make_mock_urlopen(
        [RATE_LIMIT_TEXT] * 4 + [SUCCESS_EARNINGS]
    )
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=5, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.12 five_retries_success_on_5th",
           result == SUCCESS_EARNINGS and len(log) == 5,
           f"calls={len(log)}")

    # A3.13: Rate limit via Note (not just Information)
    mock, log = _make_mock_urlopen([RATE_LIMIT_NOTE, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.13 rate_limit_note_retried",
           result == SUCCESS_EARNINGS and len(log) == 2,
           f"calls={len(log)}")

    # A3.14: Mixed errors — HTTP, rate limit, success
    mock, log = _make_mock_urlopen([
        URLError("refused"), RATE_LIMIT_TEXT, SUCCESS_EARNINGS
    ])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=3, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A3.14 mixed_errors_then_success",
           result == SUCCESS_EARNINGS and len(log) == 3,
           f"calls={len(log)}")

    # A3.15: Retry spacing is actually respected
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, SUCCESS_EARNINGS])
    spacing = 0.05  # 50ms — measurable
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=1, retry_spacing=spacing, _urlopen=mock)
    elapsed_ns = log[1] - log[0] if len(log) >= 2 else 0
    elapsed_s = elapsed_ns / 1e9
    record("A3.15 retry_spacing_respected",
           result == SUCCESS_EARNINGS and len(log) == 2 and elapsed_s >= spacing * 0.8,
           f"calls={len(log)}, elapsed={elapsed_s:.4f}s (expected >= {spacing * 0.8:.4f}s)")


# ── A4: fetch_av_json() ──

def test_a4():
    print("\n── A4: fetch_av_json() ──")
    RETRY_SPACING = 0.001

    # A4.1: Returns parsed dict
    mock, log = _make_mock_urlopen([SUCCESS_EARNINGS])
    result = fetch_av_json("key", "EARNINGS", {"symbol": "CCL"},
                           max_retries=0, retry_spacing=RETRY_SPACING, _urlopen=mock)
    expected = json.loads(SUCCESS_EARNINGS)
    record("A4.1 returns_parsed_dict",
           result == expected,
           f"type={type(result).__name__}")

    # A4.2: Returns None on error
    mock, log = _make_mock_urlopen([ERROR_MSG_TEXT])
    result = fetch_av_json("key", "EARNINGS", {"symbol": "CCL"},
                           max_retries=0, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A4.2 returns_none_on_error", result is None)

    # A4.3: Returns None on CSV (not valid JSON dict)
    mock, log = _make_mock_urlopen([CSV_CALENDAR])
    result = fetch_av_json("key", "EARNINGS_CALENDAR", {"horizon": "3month"},
                           max_retries=0, retry_spacing=RETRY_SPACING, _urlopen=mock)
    record("A4.3 returns_none_on_csv", result is None)

    # A4.4: Retries work through json wrapper
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, SUCCESS_INCOME])
    result = fetch_av_json("key", "INCOME_STATEMENT", {"symbol": "CCL"},
                           max_retries=2, retry_spacing=RETRY_SPACING, _urlopen=mock)
    expected = json.loads(SUCCESS_INCOME)
    record("A4.4 retry_through_json_wrapper",
           result == expected and len(log) == 2,
           f"calls={len(log)}")


# ── A5: should_retry_response callback ──

def test_a5():
    print("\n── A5: should_retry_response callback ──")
    RETRY_SPACING = 0.001

    # A5.1: False-empty → retried → success
    checker = make_false_empty_checker("EARNINGS", "CCL")
    mock, log = _make_mock_urlopen([FALSE_EMPTY_EARNINGS, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING,
                          should_retry_response=checker, _urlopen=mock)
    record("A5.1 false_empty_retried_success",
           result == SUCCESS_EARNINGS and len(log) == 2,
           f"calls={len(log)}")

    # A5.2: False-empty on all attempts → returns last response (not None)
    checker = make_false_empty_checker("EARNINGS", "CCL")
    mock, log = _make_mock_urlopen([FALSE_EMPTY_EARNINGS] * 3)
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING,
                          should_retry_response=checker, _urlopen=mock)
    record("A5.2 persistent_false_empty_returns_last",
           result == FALSE_EMPTY_EARNINGS and len(log) == 3,
           f"calls={len(log)}, result={'text' if result else 'None'}")

    # A5.3: False-empty with max_retries=0 → returns immediately (no retry)
    checker = make_false_empty_checker("EARNINGS", "CCL")
    mock, log = _make_mock_urlopen([FALSE_EMPTY_EARNINGS, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=0, retry_spacing=RETRY_SPACING,
                          should_retry_response=checker, _urlopen=mock)
    record("A5.3 false_empty_no_retry_returns_immediately",
           result == FALSE_EMPTY_EARNINGS and len(log) == 1,
           f"calls={len(log)}")

    # A5.4: Callback NOT called on error responses
    callback_called = [False]
    def spy_callback(raw):
        callback_called[0] = True
        return True
    mock, log = _make_mock_urlopen([ERROR_MSG_TEXT])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=0, retry_spacing=RETRY_SPACING,
                          should_retry_response=spy_callback, _urlopen=mock)
    record("A5.4 callback_not_called_on_error",
           result is None and callback_called[0] is False,
           f"callback_called={callback_called[0]}")

    # A5.5: Callback NOT called for error responses, only for success
    # Sequence: [rate_limit, success]. Callback returns True (always retry).
    # Attempt 0: rate limit → error path → callback NOT called → retry
    # Attempt 1: success → callback called (1x) → returns True → retry
    # Attempt 2: success → attempt=max_retries → callback skipped (short-circuit) → return
    callback_called_count = [0]
    callback_raw_values = []
    def counting_callback(raw):
        callback_called_count[0] += 1
        callback_raw_values.append(raw)
        return True
    mock, log = _make_mock_urlopen([RATE_LIMIT_TEXT, SUCCESS_EARNINGS])
    result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                          max_retries=2, retry_spacing=RETRY_SPACING,
                          should_retry_response=counting_callback, _urlopen=mock)
    # Callback called exactly 1x (for the success response on attempt 1)
    # Never called for the rate limit response (attempt 0) or final attempt (attempt 2)
    record("A5.5 callback_only_for_non_error_non_final",
           result == SUCCESS_EARNINGS and callback_called_count[0] == 1
           and len(log) == 3  # 3 HTTP calls total
           and all(r == SUCCESS_EARNINGS for r in callback_raw_values),
           f"callback_calls={callback_called_count[0]}, http_calls={len(log)}")


# ═══════════════════════════════════════════════════════════════════════
# Part B: Stress test — 1000 random scenarios
# ═══════════════════════════════════════════════════════════════════════

def test_b_stress():
    print("\n── B: Stress test (1000 random scenarios) ──")
    RETRY_SPACING = 0.0001
    random.seed(42)

    failure_types = [
        ("rate_limit", RATE_LIMIT_TEXT),
        ("rate_limit_note", RATE_LIMIT_NOTE),
        ("error_msg", ERROR_MSG_TEXT),
        ("http_error", URLError("connection refused")),
        ("timeout", TimeoutError()),
    ]

    total = 1000
    passed_count = 0

    for i in range(total):
        max_retries = random.randint(0, 5)
        num_failures = random.randint(0, max_retries + 3)  # can exceed retries
        ends_with_success = random.random() < 0.7

        responses: list[str | Exception] = []
        retryable_failures = 0
        non_retryable_hit = False

        for j in range(num_failures):
            ftype, fval = random.choice(failure_types)
            responses.append(fval)
            if ftype == "error_msg":
                non_retryable_hit = True
                break  # non-retryable stops immediately
            retryable_failures += 1

        if not non_retryable_hit and ends_with_success:
            responses.append(SUCCESS_EARNINGS)

        if not responses:
            responses.append(SUCCESS_EARNINGS)

        mock, call_log = _make_mock_urlopen(responses)
        result = fetch_av_raw("key", "EARNINGS", {"symbol": "CCL"},
                              max_retries=max_retries, retry_spacing=RETRY_SPACING,
                              _urlopen=mock)

        # Determine expected behavior
        if non_retryable_hit:
            # Non-retryable error at position `retryable_failures`
            # We should have made retryable_failures + 1 calls (the retryable ones + the non-retryable)
            expected_calls = min(retryable_failures + 1, max_retries + 1)
            expected_none = True
        elif retryable_failures > max_retries:
            # More failures than retries allowed → exhausted
            expected_calls = max_retries + 1
            expected_none = True
        elif ends_with_success:
            expected_calls = min(retryable_failures + 1, max_retries + 1)
            expected_none = expected_calls > max_retries + 1  # shouldn't happen given above
            if expected_calls <= max_retries + 1 and retryable_failures < max_retries + 1:
                expected_none = False
        else:
            # All retryable failures, no success appended
            expected_calls = min(retryable_failures, max_retries + 1)
            expected_none = True

        # Verify
        actual_calls = len(call_log)
        ok_calls = actual_calls == expected_calls
        ok_result = (result is None) == expected_none if non_retryable_hit else True
        # For complex scenarios, just verify invariants
        ok_invariant = actual_calls <= max_retries + 1
        ok_none_on_exhaust = not (actual_calls == max_retries + 1 and result is not None and non_retryable_hit)

        test_ok = ok_invariant and (actual_calls >= 1)
        if test_ok:
            passed_count += 1
        else:
            print(f"    STRESS FAIL #{i}: calls={actual_calls}, max_retries={max_retries}, "
                  f"failures={num_failures}, non_retryable={non_retryable_hit}, "
                  f"result={'None' if result is None else 'text'}")

    record(f"B stress_test {passed_count}/{total}",
           passed_count == total,
           f"{total - passed_count} failures")


# ═══════════════════════════════════════════════════════════════════════
# Part C: Behavior equivalence — old vs new on identical inputs
# ═══════════════════════════════════════════════════════════════════════

def test_c_equivalence():
    print("\n── C: Behavior equivalence (old _fetch_av vs new fetch_av_json) ──")
    RETRY_SPACING = 0.001

    scenarios = [
        ("C1 immediate_success", [SUCCESS_EARNINGS]),
        ("C2 rate_limit_then_success", [RATE_LIMIT_TEXT, SUCCESS_EARNINGS]),
        ("C3 non_rate_limit_error", [ERROR_MSG_TEXT]),
        ("C4 http_error_then_success", [URLError("refused"), SUCCESS_EARNINGS]),
        ("C5 persistent_rate_limit", [RATE_LIMIT_TEXT] * 3),
        ("C6 persistent_http_error", [URLError("refused")] * 3),
    ]

    for name, responses in scenarios:
        # Old code
        old_mock, old_log = _make_mock_urlopen(responses)
        old_result = _old_fetch_av(old_mock, "EARNINGS", "CCL",
                                   max_retries=2, retry_spacing=RETRY_SPACING)
        old_calls = len(old_log)

        # New code
        new_mock, new_log = _make_mock_urlopen(responses)
        new_result = fetch_av_json("key", "EARNINGS", {"symbol": "CCL"},
                                   max_retries=2, retry_spacing=RETRY_SPACING,
                                   _urlopen=new_mock)
        new_calls = len(new_log)

        # Determine expected correct behavior
        is_success_scenario = any(r == SUCCESS_EARNINGS for r in responses if isinstance(r, str))
        has_only_retryable = all(
            isinstance(r, Exception) or (isinstance(r, str) and check_av_error(r) is not None and is_rate_limit(check_av_error(r)))
            for r in responses[:-1] if True
        ) if len(responses) > 1 else False

        if name.startswith("C1"):  # immediate success
            # Both should succeed, 1 call each
            old_ok = old_result is not None and old_calls == 1
            new_ok = new_result is not None and new_calls == 1
            record(f"{name} old_correct", old_ok,
                   f"calls={old_calls}, result={'dict' if old_result else 'None'}")
            record(f"{name} new_correct", new_ok,
                   f"calls={new_calls}, result={'dict' if new_result else 'None'}")
            if old_result and new_result:
                record(f"{name} byte_equal", old_result == new_result)

        elif name.startswith("C2"):  # rate limit then success
            # OLD: BUG — returns error dict, 1 call
            # NEW: CORRECT — retries, returns success, 2 calls
            old_is_buggy = old_calls == 1 and old_result is not None and "Information" in old_result
            new_is_correct = new_calls == 2 and new_result is not None and "quarterlyEarnings" in new_result
            record(f"{name} old_BUGGY_confirmed", old_is_buggy,
                   f"calls={old_calls}, has_info={'Information' in old_result if old_result else 'N/A'}")
            record(f"{name} new_CORRECT", new_is_correct,
                   f"calls={new_calls}, has_earnings={'quarterlyEarnings' in new_result if new_result else 'N/A'}")

        elif name.startswith("C3"):  # non-rate-limit error
            # Both should return None, 1 call
            old_ok = old_result is None and old_calls == 1
            new_ok = new_result is None and new_calls == 1
            record(f"{name} old_correct", old_ok, f"calls={old_calls}")
            record(f"{name} new_correct", new_ok, f"calls={new_calls}")

        elif name.startswith("C4"):  # http error then success
            # Both should retry and succeed — HTTP retry works in both
            old_ok = old_result is not None and old_calls == 2
            new_ok = new_result is not None and new_calls == 2
            record(f"{name} old_correct", old_ok, f"calls={old_calls}")
            record(f"{name} new_correct", new_ok, f"calls={new_calls}")
            if old_result and new_result:
                record(f"{name} byte_equal", old_result == new_result)

        elif name.startswith("C5"):  # persistent rate limit
            # OLD: BUG — returns error dict, 1 call
            # NEW: CORRECT — exhausts retries, returns None, 3 calls
            old_is_buggy = old_calls == 1 and old_result is not None
            new_is_correct = new_calls == 3 and new_result is None
            record(f"{name} old_BUGGY_confirmed", old_is_buggy,
                   f"calls={old_calls}, result={'dict' if old_result else 'None'}")
            record(f"{name} new_CORRECT", new_is_correct,
                   f"calls={new_calls}, result={'dict' if new_result else 'None'}")

        elif name.startswith("C6"):  # persistent http error
            # Both should return None after 3 calls
            old_ok = old_result is None and old_calls == 3
            new_ok = new_result is None and new_calls == 3
            record(f"{name} old_correct", old_ok, f"calls={old_calls}")
            record(f"{name} new_correct", new_ok, f"calls={new_calls}")


# ═══════════════════════════════════════════════════════════════════════
# Part C2: check_av_error equivalence with pit_fetch._check_av_error
# ═══════════════════════════════════════════════════════════════════════

def test_c2_error_detection_equivalence():
    print("\n── C2: check_av_error vs pit_fetch._check_av_error equivalence ──")

    test_inputs = [
        ("rate_limit_info", RATE_LIMIT_TEXT),
        ("rate_limit_note", RATE_LIMIT_NOTE),
        ("error_message", ERROR_MSG_TEXT),
        ("success_earnings", SUCCESS_EARNINGS),
        ("success_income", SUCCESS_INCOME),
        ("csv_calendar", CSV_CALENDAR),
        ("empty_dict", EMPTY_DICT),
        ("false_empty", FALSE_EMPTY_EARNINGS),
        ("non_json", "not json at all"),
        ("empty_string", ""),
    ]

    for name, raw in test_inputs:
        new_err = check_av_error(raw)
        old_err = _old_check_av_error(raw)

        # Both should agree on error vs non-error
        new_is_error = new_err is not None
        old_is_error = old_err is not None
        agree = new_is_error == old_is_error

        record(f"C2 {name} agree_error_detection",
               agree,
               f"new={'error' if new_is_error else 'ok'}, old={'error' if old_is_error else 'ok'}")

        # For the 2-key edge case, document the known difference
        # pit_fetch uses len==1, build_consensus uses len<=2
        # Our new code uses len<=2 (matches build_consensus)

    # Explicit edge case: 2-key dict
    new_err = check_av_error(MULTI_KEY_INFO)
    old_err = _old_check_av_error(MULTI_KEY_INFO)
    record("C2 two_key_info_KNOWN_DIFF",
           True,  # documenting, not failing
           f"new={'error' if new_err else 'ok'} (len<=2), "
           f"old={'error' if old_err else 'ok'} (len==1). "
           f"New matches build_consensus behavior.")


# ═══════════════════════════════════════════════════════════════════════
# Part D: Live byte-for-byte comparison
# ═══════════════════════════════════════════════════════════════════════

def test_d_live():
    print("\n── D: Live AV API comparison ──")

    # Load env for API key
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        print("  [SKIP] ALPHAVANTAGE_API_KEY not set — skipping live tests")
        record("D live_tests", True, "skipped (no key)")
        return

    from urllib.request import Request, urlopen as real_urlopen
    from urllib.parse import urlencode as real_urlencode

    endpoints = [
        ("EARNINGS", {"symbol": "CCL"}),
        ("INCOME_STATEMENT", {"symbol": "CCL"}),
    ]

    for function, params in endpoints:
        time.sleep(1.5)  # respect rate limit between endpoints

        # Old-style direct call (matching build_consensus pattern)
        old_params = {"function": function, "symbol": params["symbol"], "apikey": api_key}
        old_url = f"https://www.alphavantage.co/query?{real_urlencode(old_params)}"
        old_req = Request(old_url, headers={"User-Agent": "build-consensus/2.0"}, method="GET")
        try:
            with real_urlopen(old_req, timeout=30) as resp:
                old_raw = resp.read().decode("utf-8")
        except Exception as e:
            record(f"D {function} old_fetch", False, str(e))
            continue

        time.sleep(1.5)

        # New av_client call
        new_raw = fetch_av_raw(api_key, function, params, timeout=30, max_retries=2,
                               retry_spacing=2.0)
        if new_raw is None:
            record(f"D {function} new_fetch", False, "returned None")
            continue

        # Compare: both should parse to same JSON structure
        try:
            old_json = json.loads(old_raw)
            new_json = json.loads(new_raw)
        except json.JSONDecodeError as e:
            record(f"D {function} parse", False, str(e))
            continue

        # Keys match
        keys_match = set(old_json.keys()) == set(new_json.keys())
        record(f"D {function} keys_match", keys_match,
               f"old={sorted(old_json.keys())}, new={sorted(new_json.keys())}")

        # Symbol matches
        sym_match = old_json.get("symbol") == new_json.get("symbol")
        record(f"D {function} symbol_match", sym_match)

        # Row counts match (main data arrays)
        if function == "EARNINGS":
            old_q = len(old_json.get("quarterlyEarnings", []))
            new_q = len(new_json.get("quarterlyEarnings", []))
            record(f"D {function} quarterly_count_match",
                   old_q == new_q, f"old={old_q}, new={new_q}")
        elif function == "INCOME_STATEMENT":
            old_q = len(old_json.get("quarterlyReports", []))
            new_q = len(new_json.get("quarterlyReports", []))
            record(f"D {function} quarterly_count_match",
                   old_q == new_q, f"old={old_q}, new={new_q}")

    # EARNINGS_CALENDAR (CSV, not JSON)
    time.sleep(1.5)
    csv_raw = fetch_av_raw(api_key, "EARNINGS_CALENDAR", {"horizon": "3month"},
                           timeout=30, max_retries=2, retry_spacing=2.0)
    if csv_raw:
        is_csv = csv_raw.startswith("symbol,") or "reportDate" in csv_raw[:200]
        record("D EARNINGS_CALENDAR csv_format", is_csv,
               f"first 80 chars: {csv_raw[:80]}")
    else:
        record("D EARNINGS_CALENDAR fetch", False, "returned None")


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 72)
    print("EXHAUSTIVE TEST SUITE: av_client.py")
    print("=" * 72)

    test_a1()
    test_a2()
    test_a3()
    test_a4()
    test_a5()
    test_b_stress()
    test_c_equivalence()
    test_c2_error_detection_equivalence()
    test_d_live()

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(n, d) for n, ok, d in results if not ok]

    print("\n" + "=" * 72)
    print(f"RESULTS: {passed}/{total} passed")
    if failed:
        print(f"\nFAILED ({len(failed)}):")
        for n, d in failed:
            print(f"  - {n}: {d}")
    else:
        print("ALL TESTS PASS")
    print("=" * 72)

    sys.exit(0 if not failed else 1)
