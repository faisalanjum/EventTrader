"""
Polygon subscription-death detection.

Design:
  * Zero added API traffic on the healthy path — piggybacks on organic
    calls from eventReturns/polygonClass.py (validate_ticker, get_last_trade).
  * Only the live runner (scripts/run_event_trader.py) self-terminates on
    confirmed death; batch scripts that import Polygon are unaffected.
  * Probe hits the SAME endpoint family the production returns path uses
    (1-second aggregates via /v2/aggs/.../range/1/second/...), so plan
    downgrades that would break production are detected — a probe against
    /prev would falsely pass on tiers that exclude second aggregates.
  * Classifier is narrow: only HTTP 401/403 OR body status == "NOT_AUTHORIZED"
    counts as auth failure. Generic body status "ERROR", timeouts, 5xx, 429
    are treated as transient.
  * Single module-level state machine; no per-source flags; no state file.
"""
import logging
import os
import signal
import threading
import time
from datetime import datetime, timedelta

import pytz
import requests

from eventtrader.keys import POLYGON_API_KEY

logger = logging.getLogger(__name__)

_STATE_ALIVE, _STATE_VERIFYING, _STATE_DEAD = "ALIVE", "VERIFYING", "DEAD"
_state = _STATE_ALIVE
_lock = threading.Lock()
_is_live_runner = False  # opt-in set by run_event_trader after startup probe

# Monotonic counter — bumped at the TOP of on_auth_failure() (before the
# state check), so every caller is recorded whether or not they trigger
# verification. Callers (ReturnsProcessor._update_return) sample this at
# entry; a delta at decision time means auth was suspected during their
# call, race-free even if verification resolves back to ALIVE before the
# caller observes _state.
_auth_suspect_counter = 0

_PROBE_TIMEOUT = 8

_AUTH_ERROR_MARKERS = (
    "NOT_AUTHORIZED",      # Polygon canonical status for plan/auth failures
    "UNAUTHORIZED",        # HTTP 401 reason phrase
    "FORBIDDEN",           # HTTP 403 reason phrase
    "UNKNOWN API KEY",     # observed body on invalid/expired key
    "INVALID API KEY",     # variant
    "NOT_ENTITLED",        # variant for plan mismatches
)


def exception_looks_like_auth_failure(exc) -> bool:
    """Classify a Polygon SDK exception as auth failure. polygon-api-client's
    BadResponse wraps only the response body (HTTP status stripped at
    polygon/rest/base.py), so we parse body.status + body.error with a
    string-level fallback. Aligned with _looks_like_auth_failure which
    handles Response objects directly."""
    msg = str(exc)
    try:
        import json
        body = json.loads(msg)
    except (ValueError, TypeError):
        body = None
    if isinstance(body, dict):
        status = (body.get("status") or "").upper()
        if status == "NOT_AUTHORIZED":
            return True
        if status == "ERROR":
            err = (body.get("error") or body.get("message") or "").upper()
            if any(m in err for m in _AUTH_ERROR_MARKERS):
                return True
    upper = msg.upper()
    return any(m in upper for m in _AUTH_ERROR_MARKERS)


def get_auth_suspect_counter() -> int:
    """Monotonic counter incremented every time on_auth_failure() is entered
    (before the state check). Callers sample at entry, compare at decision
    time — any delta means an auth suspicion occurred during the call."""
    return _auth_suspect_counter


def enable_fatal_shutdown() -> None:
    """Called by run_event_trader.py after startup probe passes. Enables
    SIGTERM on confirmed auth death. Batch scripts that import Polygon
    do NOT call this; for them, DEAD state just stays latched and
    subsequent calls keep returning nan/False as today."""
    global _is_live_runner
    _is_live_runner = True


def _looks_like_auth_failure(resp) -> bool:
    """True iff HTTP 401/403 OR body.status == NOT_AUTHORIZED.
    Timeouts/5xx/429/generic body ERROR intentionally return False."""
    if resp.status_code in (401, 403):
        return True
    if resp.status_code != 200:
        return False
    try:
        body = resp.json()
    except ValueError:
        return False
    return (body.get("status") or "").upper() == "NOT_AUTHORIZED"


def _last_weekday_second_window_ms():
    """Return (from_ms, to_ms) for a 10-second window at 14:00 ET on the
    most recent weekday before today. Always a valid historical window;
    on US market holidays the probe still returns 200 OK with 0 results,
    which the classifier correctly treats as non-auth (i.e., alive)."""
    ny = pytz.timezone("America/New_York")
    d = datetime.now(ny).date() - timedelta(days=1)
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= timedelta(days=1)
    start = ny.localize(datetime.combine(
        d, datetime.strptime("14:00:00", "%H:%M:%S").time()))
    end = start + timedelta(seconds=10)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _single_probe() -> bool:
    """Return True iff probe confirms auth failure. Network errors, 5xx,
    429, or non-auth responses all return False."""
    try:
        from_ms, to_ms = _last_weekday_second_window_ms()
        url = (f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/second/"
               f"{from_ms}/{to_ms}")
        r = requests.get(url, params={
            "apiKey": POLYGON_API_KEY,
            "adjusted": "true",
            "sort": "desc",
            "limit": 50,
        }, timeout=_PROBE_TIMEOUT)
    except Exception:
        return False
    return _looks_like_auth_failure(r)


def check_at_startup() -> bool:
    """Return True iff subscription is alive. Called once by the live
    runner before starting ingestion threads. Two tries — any non-auth
    response means alive."""
    for _ in range(2):
        if not _single_probe():
            return True
        time.sleep(1)
    return False


def on_auth_failure(trigger_exc: Exception) -> None:
    """Called from polygonClass.py's NOT_AUTHORIZED exception paths.
    First caller runs 2 further probes (~4s). If 3/3 confirm, and
    this process has opted-in via enable_fatal_shutdown(), we SIGTERM
    ourselves so the existing signal handler runs manager.stop() for
    a clean drain. Later callers (other threads) return immediately."""
    global _state, _auth_suspect_counter
    with _lock:
        # Latch every caller BEFORE the state check, so callers that arrive
        # while another thread is already verifying still get counted.
        _auth_suspect_counter += 1
        if _state != _STATE_ALIVE:
            return
        _state = _STATE_VERIFYING

    logger.warning(
        "Polygon: suspected auth failure (%s); verifying…", trigger_exc)
    confirms = 1  # triggering exception counts as sample #1
    for _ in range(2):
        time.sleep(2)
        if _single_probe():
            confirms += 1

    with _lock:
        if confirms >= 3:
            _state = _STATE_DEAD
            logger.critical(
                "POLYGON SUBSCRIPTION DEAD — 3/3 auth failures confirmed.")
            if _is_live_runner:
                os.kill(os.getpid(), signal.SIGTERM)
        else:
            _state = _STATE_ALIVE
            logger.warning(
                "Polygon: transient auth event (%d/3) — resuming.", confirms)


def is_dead() -> bool:
    """Exposed for callers that want to short-circuit further calls
    once death is latched. Not currently used by the two hook points
    (they return nan/False after on_auth_failure), but kept for future
    extension."""
    return _state == _STATE_DEAD
