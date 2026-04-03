#!/usr/bin/env python3
"""Empirical test: prove the `continue` scoping bug in _fetch_av retry logic.

Replaces urlopen with a mock that returns rate-limit responses N times,
then a success. Counts how many HTTP requests actually fire for each version.
"""
import json
import time
from unittest.mock import patch, MagicMock
from io import BytesIO

# ── Simulated AV responses ──────────────────────────────────────────────

RATE_LIMIT_RESPONSE = json.dumps({
    "Information": "Thank you for using Alpha Vantage! Please consider spreading out your free API requests more sparingly (1 request per second). You may subscribe to any of the premium plans at https://www.alphavantage.co/premium/ to lift the free key rate limit (25 requests per day)."
}).encode()

SUCCESS_RESPONSE = json.dumps({
    "symbol": "CCL",
    "quarterlyEarnings": [
        {"fiscalDateEnding": "2026-02-28", "reportedDate": "2026-03-27",
         "reportedEPS": "0.2", "estimatedEPS": "0.18",
         "surprise": "0.02", "surprisePercentage": "11.1111"}
    ],
    "annualEarnings": [
        {"fiscalDateEnding": "2026-02-28", "reportedEPS": "0.2"}
    ]
}).encode()

NON_RATE_LIMIT_ERROR = json.dumps({
    "Error Message": "Invalid API call. Please retry or check your API parameters."
}).encode()


def make_mock_urlopen(responses: list[bytes]):
    """Return a urlopen mock that yields responses in order."""
    call_count = [0]
    def mock_urlopen(req, timeout=None):
        idx = call_count[0]
        call_count[0] += 1
        resp_bytes = responses[idx] if idx < len(responses) else responses[-1]
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_bytes
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp
    return mock_urlopen, call_count


# ── OLD (buggy) _fetch_av ────────────────────────────────────────────────

_AV_MAX_RETRIES = 2
_AV_RETRY_SPACING = 0.01  # fast for testing

def _fetch_av_OLD(urlopen_fn, function: str, symbol: str):
    """Exact copy of the old code with urlopen replaced."""
    for attempt in range(_AV_MAX_RETRIES + 1):
        try:
            resp = urlopen_fn(None, timeout=30)
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
                # (false-empty check omitted for clarity — not relevant to this bug)
            return data
        except Exception:
            if attempt < _AV_MAX_RETRIES:
                time.sleep(_AV_RETRY_SPACING)
                continue
            return None
    return None


# ── NEW (fixed) _fetch_av ────────────────────────────────────────────────

def _fetch_av_NEW(urlopen_fn, function: str, symbol: str):
    """Fixed version — error detection extracted from inner loop."""
    for attempt in range(_AV_MAX_RETRIES + 1):
        try:
            resp = urlopen_fn(None, timeout=30)
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                error_msg = None
                for key in ("Error Message", "Information", "Note"):
                    if key in data and len(data) <= 2:
                        error_msg = str(data[key]).lower()
                        break
                if error_msg is not None:
                    is_rate_limit = "rate limit" in error_msg or "spreading out" in error_msg or "25 requests" in error_msg
                    if is_rate_limit and attempt < _AV_MAX_RETRIES:
                        time.sleep(_AV_RETRY_SPACING)
                        continue  # retries outer attempt loop
                    return None
            return data
        except Exception:
            if attempt < _AV_MAX_RETRIES:
                time.sleep(_AV_RETRY_SPACING)
                continue
            return None
    return None


# ── Test cases ───────────────────────────────────────────────────────────

def test(name, fetch_fn, responses, expect_result_type, expect_calls):
    """Run one test and report pass/fail."""
    mock_fn, call_count = make_mock_urlopen(responses)
    result = fetch_fn(mock_fn, "EARNINGS", "CCL")
    actual_calls = call_count[0]

    result_type = "None" if result is None else ("success" if "quarterlyEarnings" in result else "error_dict")

    ok_result = result_type == expect_result_type
    ok_calls = actual_calls == expect_calls

    status = "PASS" if (ok_result and ok_calls) else "FAIL"
    print(f"  [{status}] {name}")
    print(f"         HTTP calls: {actual_calls} (expected {expect_calls})")
    print(f"         Result:     {result_type} (expected {expect_result_type})")
    if not ok_result:
        print(f"         ** WRONG RESULT: got {result_type}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    if not ok_calls:
        print(f"         ** WRONG CALL COUNT: {actual_calls} != {expect_calls}")
    return ok_result and ok_calls


if __name__ == "__main__":
    print("=" * 72)
    print("TEST: _fetch_av retry logic — continue scoping bug")
    print("=" * 72)
    total = 0
    passed = 0

    # ── Scenario 1: Rate limit on first call, then success ──
    # With MAX_RETRIES=2, we expect 2 calls: fail, succeed
    responses_1 = [RATE_LIMIT_RESPONSE, SUCCESS_RESPONSE]

    print("\nScenario 1: Rate limit once, then success")
    print("-" * 50)

    total += 1
    if test("OLD code — rate limit then success",
            _fetch_av_OLD, responses_1,
            expect_result_type="error_dict",  # BUG: returns the rate limit dict
            expect_calls=1):                   # BUG: only 1 call (no retry)
        passed += 1

    total += 1
    if test("NEW code — rate limit then success",
            _fetch_av_NEW, responses_1,
            expect_result_type="success",  # FIXED: retries and gets success
            expect_calls=2):               # FIXED: 2 calls (retry fires)
        passed += 1

    # ── Scenario 2: Rate limit on ALL attempts ──
    # With MAX_RETRIES=2, we expect 3 calls, then None
    responses_2 = [RATE_LIMIT_RESPONSE, RATE_LIMIT_RESPONSE, RATE_LIMIT_RESPONSE]

    print("\nScenario 2: Rate limit on ALL 3 attempts")
    print("-" * 50)

    total += 1
    if test("OLD code — persistent rate limit",
            _fetch_av_OLD, responses_2,
            expect_result_type="error_dict",  # BUG: returns error dict on 1st call
            expect_calls=1):                   # BUG: only 1 call
        passed += 1

    total += 1
    if test("NEW code — persistent rate limit",
            _fetch_av_NEW, responses_2,
            expect_result_type="None",    # FIXED: exhausts retries, returns None
            expect_calls=3):              # FIXED: all 3 attempts fire
        passed += 1

    # ── Scenario 3: Non-rate-limit error (both should return None immediately) ──
    responses_3 = [NON_RATE_LIMIT_ERROR, SUCCESS_RESPONSE]

    print("\nScenario 3: Non-rate-limit error (no retry expected)")
    print("-" * 50)

    total += 1
    if test("OLD code — non-rate-limit error",
            _fetch_av_OLD, responses_3,
            expect_result_type="None",  # Correct: returns None
            expect_calls=1):            # Correct: no retry for non-rate-limit
        passed += 1

    total += 1
    if test("NEW code — non-rate-limit error",
            _fetch_av_NEW, responses_3,
            expect_result_type="None",  # Correct: returns None
            expect_calls=1):            # Correct: no retry for non-rate-limit
        passed += 1

    # ── Scenario 4: Immediate success (baseline) ──
    responses_4 = [SUCCESS_RESPONSE]

    print("\nScenario 4: Immediate success (baseline)")
    print("-" * 50)

    total += 1
    if test("OLD code — immediate success",
            _fetch_av_OLD, responses_4,
            expect_result_type="success",
            expect_calls=1):
        passed += 1

    total += 1
    if test("NEW code — immediate success",
            _fetch_av_NEW, responses_4,
            expect_result_type="success",
            expect_calls=1):
        passed += 1

    # ── Scenario 5: Rate limit twice, then success on 3rd (final) attempt ──
    responses_5 = [RATE_LIMIT_RESPONSE, RATE_LIMIT_RESPONSE, SUCCESS_RESPONSE]

    print("\nScenario 5: Rate limit twice, success on 3rd (final) attempt")
    print("-" * 50)

    total += 1
    if test("OLD code — 2x rate limit then success",
            _fetch_av_OLD, responses_5,
            expect_result_type="error_dict",  # BUG: returns error dict on 1st call
            expect_calls=1):                   # BUG: only 1 call
        passed += 1

    total += 1
    if test("NEW code — 2x rate limit then success",
            _fetch_av_NEW, responses_5,
            expect_result_type="success",  # FIXED: retries and gets success on 3rd
            expect_calls=3):               # FIXED: all 3 attempts fire
        passed += 1

    # ── Summary ──
    print("\n" + "=" * 72)
    print(f"RESULTS: {passed}/{total} passed")
    if passed == total:
        print("ALL TESTS PASS — bug confirmed in OLD, fix verified in NEW")
    else:
        print("SOME TESTS FAILED — review output above")
    print("=" * 72)
