from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from macro_stream_switch import (  # noqa: E402
    MACRO_SYMBOLS,
    read_switch,
    run_stream,
    set_switch,
)


class ImmediateTickClient:
    def __init__(self) -> None:
        self.callbacks: dict[str, object] = {}
        self.connected_symbols: list[str] = []
        self.disconnect_calls = 0

    def on(self, event: str, callback):
        self.callbacks[event] = callback
        return self

    def connect(self, symbols: list[str]) -> None:
        self.connected_symbols = list(symbols)
        self.callbacks["authenticated"]()
        self.callbacks["tick"](
            SimpleNamespace(
                symbol="ES.F",
                price=6500.25,
                timestamp="2026-07-19T22:00:01Z",
                replay=False,
            )
        )

    def disconnect(self) -> None:
        self.disconnect_calls += 1


class BlockingClient:
    def __init__(self) -> None:
        self.callbacks: dict[str, object] = {}
        self.connected = threading.Event()
        self.disconnected = threading.Event()

    def on(self, event: str, callback):
        self.callbacks[event] = callback
        return self

    def connect(self, symbols: list[str]) -> None:
        self.connected.set()
        self.callbacks["authenticated"]()
        self.disconnected.wait(timeout=2)

    def disconnect(self) -> None:
        self.disconnected.set()


def test_missing_switch_fails_closed_without_creating_client(tmp_path):
    created = False

    def factory(_key: str):
        nonlocal created
        created = True
        return ImmediateTickClient()

    result = run_stream(
        "AAPL",
        state_path=tmp_path / "missing.json",
        api_key="not-real",
        client_factory=factory,
        emit=lambda _message: None,
    )

    assert read_switch(tmp_path / "missing.json") is False
    assert created is False
    assert result.reason == "switch_off"
    assert result.ticks == 0


def test_enabled_run_uses_fifteen_macro_symbols_plus_active_stock(tmp_path):
    state_path = tmp_path / "switch.json"
    set_switch(True, state_path)
    client = ImmediateTickClient()
    messages: list[str] = []

    result = run_stream(
        "aapl",
        state_path=state_path,
        api_key="not-real",
        client_factory=lambda _key: client,
        max_ticks=1,
        poll_seconds=0.01,
        emit=messages.append,
    )

    assert client.connected_symbols == [*MACRO_SYMBOLS, "AAPL"]
    assert len(client.connected_symbols) == 16
    assert result.authenticated is True
    assert result.ticks == 1
    assert result.reason == "tick_limit"
    assert client.disconnect_calls >= 1
    assert all("not-real" not in message for message in messages)


def test_turning_switch_off_stops_an_active_connection(tmp_path):
    state_path = tmp_path / "switch.json"
    set_switch(True, state_path)
    client = BlockingClient()
    holder = {}

    thread = threading.Thread(
        target=lambda: holder.setdefault(
            "result",
            run_stream(
                "AAPL",
                state_path=state_path,
                api_key="not-real",
                client_factory=lambda _key: client,
                poll_seconds=0.01,
                emit=lambda _message: None,
            ),
        )
    )
    thread.start()
    assert client.connected.wait(timeout=1)

    set_switch(False, state_path)
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert client.disconnected.is_set()
    assert holder["result"].reason == "switch_off"


def test_switch_file_contains_only_the_boolean_state(tmp_path):
    state_path = tmp_path / "switch.json"

    set_switch(True, state_path)
    assert json.loads(state_path.read_text()) == {"enabled": True}

    set_switch(False, state_path)
    assert json.loads(state_path.read_text()) == {"enabled": False}
