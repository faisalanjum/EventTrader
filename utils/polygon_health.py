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

_PROBE_TIMEOUT = 8


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
    global _state
    with _lock:
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
