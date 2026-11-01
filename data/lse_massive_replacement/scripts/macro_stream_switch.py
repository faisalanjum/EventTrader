#!/usr/bin/env python3
"""Isolated ON/OFF-controlled WebSocket runner for the 17-signal macro panel.

This file does not import or change EventMarketDB production code. The API key
is read only from LSE_API_KEY and is never written to disk.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence


AUDIT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = AUDIT_ROOT / "config" / "macro_stream.json"
CLIENT_ROOT = AUDIT_ROOT / "raw" / "lse-data-main"

# Fifteen macro inputs leave the free account's sixteenth live slot for the
# stock being traded. Other README indicators are calculated from these
# inputs or read from the REST economic calendar.
MACRO_SYMBOLS = (
    "ES.F",
    "VIX/USD",
    "USB10Y/USD",
    "USB02Y/USD",
    "HYG",
    "NQ.F",
    "DXY/USD",
    "US2000/USD",
    "SMH",
    "WTICO/USD",
    "USD/JPY",
    "XCU/USD",
    "GC.F",
    "CN50/USD",
    "EU50/EUR",
)

_KEY_PATTERN = re.compile(r"lse_live_[A-Za-z0-9]+")


@dataclass(frozen=True)
class StreamResult:
    reason: str
    ticks: int
    authenticated: bool
    symbols: tuple[str, ...]
    errors: tuple[str, ...] = ()


def read_switch(path: Path = DEFAULT_STATE_PATH) -> bool:
    """Return True only for a valid file containing {"enabled": true}.

    Missing, unreadable, or malformed files fail closed and return False.
    """

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("enabled") is True


def set_switch(enabled: bool, path: Path = DEFAULT_STATE_PATH) -> None:
    """Atomically set the switch without storing credentials."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    temporary.write_text(
        json.dumps({"enabled": bool(enabled)}, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_subscriptions(active_symbol: str) -> tuple[str, ...]:
    symbol = str(active_symbol).strip().upper()
    if not symbol:
        raise ValueError("active symbol is required")
    if symbol in MACRO_SYMBOLS:
        raise ValueError("active symbol must be separate from the 15 macro symbols")
    subscriptions = (*MACRO_SYMBOLS, symbol)
    if len(set(subscriptions)) != 16:
        raise ValueError("subscriptions must contain exactly 16 unique symbols")
    return subscriptions


def _redact(value: object, api_key: str) -> str:
    text = str(value)
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return _KEY_PATTERN.sub("[REDACTED]", text)


def _default_client_factory(api_key: str):
    # Load the isolated client only when the switch is ON. An OFF run does not
    # import networking code or create a connection.
    sys.path.insert(0, str(CLIENT_ROOT))
    from lse import LSE

    return LSE(api_key=api_key)


def run_stream(
    active_symbol: str,
    *,
    state_path: Path = DEFAULT_STATE_PATH,
    api_key: Optional[str] = None,
    client_factory: Optional[Callable[[str], object]] = None,
    max_seconds: float = 0,
    max_ticks: int = 0,
    poll_seconds: float = 0.5,
    emit: Callable[[str], None] = print,
) -> StreamResult:
    """Run until switched OFF, interrupted, or an optional test limit is met."""

    subscriptions = build_subscriptions(active_symbol)
    if not read_switch(state_path):
        emit("macro stream switch is OFF; no connection opened")
        return StreamResult("switch_off", 0, False, subscriptions)

    key = api_key or os.environ.get("LSE_API_KEY", "")
    if not key:
        emit("LSE_API_KEY is not set; no connection opened")
        return StreamResult("missing_api_key", 0, False, subscriptions)

    if max_seconds < 0 or max_ticks < 0 or poll_seconds <= 0:
        raise ValueError("limits must be non-negative and poll_seconds must be positive")

    factory = client_factory or _default_client_factory
    client = factory(key)
    stop_event = threading.Event()
    state_lock = threading.RLock()
    state = {
        "reason": "connection_ended",
        "ticks": 0,
        "authenticated": False,
    }
    errors: list[str] = []

    def request_stop(reason: str) -> None:
        with state_lock:
            if stop_event.is_set():
                return
            state["reason"] = reason
            stop_event.set()
        try:
            client.disconnect()
        except Exception as exc:  # pragma: no cover - defensive SDK boundary
            safe = _redact(exc, key)
            errors.append(safe)
            emit(f"disconnect error: {safe}")

    def on_authenticated() -> None:
        with state_lock:
            state["authenticated"] = True
        emit(f"authenticated; subscribed symbols={len(subscriptions)}")

    def on_tick(tick) -> None:
        with state_lock:
            state["ticks"] += 1
            tick_count = int(state["ticks"])
        timestamp = getattr(tick, "timestamp", None) or "timestamp-missing"
        replay = " replay" if getattr(tick, "replay", False) else ""
        emit(
            f"tick {tick_count}: {timestamp} "
            f"{getattr(tick, 'symbol', '')}={getattr(tick, 'price', '')}{replay}"
        )
        if max_ticks and tick_count >= max_ticks:
            request_stop("tick_limit")

    def on_error(error) -> None:
        safe = _redact(error, key)
        errors.append(safe)
        emit(f"stream error: {safe}")

    client.on("authenticated", on_authenticated)
    client.on("tick", on_tick)
    client.on("error", on_error)

    deadline = time.monotonic() + max_seconds if max_seconds else None

    def watch_switch() -> None:
        while not stop_event.wait(poll_seconds):
            if not read_switch(state_path):
                request_stop("switch_off")
                return
            if deadline is not None and time.monotonic() >= deadline:
                request_stop("time_limit")
                return

    watcher = threading.Thread(
        target=watch_switch,
        name="lse-macro-switch-watcher",
        daemon=True,
    )
    watcher.start()

    emit(f"opening WebSocket for {len(subscriptions)} symbols")
    try:
        client.connect(list(subscriptions))
    except KeyboardInterrupt:
        request_stop("keyboard_interrupt")
    except Exception as exc:
        safe = _redact(exc, key)
        errors.append(safe)
        emit(f"stream error: {safe}")
        request_stop("error")
    finally:
        if not stop_event.is_set():
            stop_event.set()
        watcher.join(timeout=max(1.0, poll_seconds * 3))

    result = StreamResult(
        reason=str(state["reason"]),
        ticks=int(state["ticks"]),
        authenticated=bool(state["authenticated"]),
        symbols=subscriptions,
        errors=tuple(errors),
    )
    emit(
        f"stream stopped: reason={result.reason}, "
        f"authenticated={result.authenticated}, ticks={result.ticks}"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safe ON/OFF switch for the isolated LSE macro WebSocket."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("on", help="allow the isolated stream to connect")
    commands.add_parser("off", help="stop and block the isolated stream")
    commands.add_parser("status", help="show the current switch state")

    run = commands.add_parser("run", help="run the stream while the switch is ON")
    run.add_argument("active_symbol", help="stock using the sixteenth live slot")
    run.add_argument(
        "--max-seconds",
        type=float,
        default=0,
        help="optional smoke-test duration; zero runs until switched OFF",
    )
    run.add_argument(
        "--max-ticks",
        type=int,
        default=0,
        help="optional smoke-test tick limit; zero is unlimited",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "on":
        set_switch(True)
        print("macro stream switch: ON")
        return 0
    if args.command == "off":
        set_switch(False)
        print("macro stream switch: OFF")
        return 0
    if args.command == "status":
        print(f"macro stream switch: {'ON' if read_switch() else 'OFF'}")
        return 0

    result = run_stream(
        args.active_symbol,
        max_seconds=args.max_seconds,
        max_ticks=args.max_ticks,
    )
    if result.reason in {"error", "missing_api_key"}:
        return 1
    if result.reason == "switch_off" and not result.authenticated:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
