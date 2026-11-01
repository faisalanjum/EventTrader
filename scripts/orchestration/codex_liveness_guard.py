#!/usr/bin/env python3
"""Remind one Codex session after it has been continuously idle for 15 minutes.

The status checks use the local Codex app-server and never call a model.  The
only message is sent through ``codex queue`` after ChatGPT subscription login
and compatible local versions have both been verified.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
import fcntl
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Awaitable, Callable
import uuid


REMINDER = "Reminder: Keep the loop on so you continue to orchestrate core/claude"
IDLE_SECONDS = 15 * 60
CHECK_SECONDS = 60
MIN_QUEUE_VERSION = (0, 149, 0)
COMMAND_TIMEOUT_SECONDS = 30

_USER_HOME = Path.home()


@dataclass(frozen=True)
class GuardPaths:
    target_file: Path
    arm_file: Path
    state_file: Path
    lock_file: Path
    socket_file: Path
    codex_binary: Path = _USER_HOME / ".codex/packages/standalone/current/codex"


DEFAULT_PATHS = GuardPaths(
    target_file=_USER_HOME / ".core827-orchestrator/CODEX_LIVENESS_TARGET",
    arm_file=_USER_HOME / ".core827-orchestrator/CODEX_LIVENESS_ARMED",
    state_file=_USER_HOME / ".core827-orchestrator/codex_liveness_state.json",
    lock_file=_USER_HOME / ".core827-orchestrator/codex_liveness_guard.lock",
    socket_file=(
        _USER_HOME / ".codex/app-server-control/app-server-control.sock"
    ),
)


@dataclass
class GuardState:
    target_thread_id: str
    boot_id: str
    idle_since_monotonic: float | None = None
    reminder_attempted: bool = False
    reminder_result: str | None = None


@dataclass(frozen=True)
class CycleResult:
    outcome: str
    detail: str = ""


StatusReader = Callable[[str], Awaitable[str]]
BooleanCheck = Callable[[], bool]
MessageQueue = Callable[[str, str], None]


class InvalidTarget(ValueError):
    pass


class InvalidState(ValueError):
    pass


def _valid_thread_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def read_target(path: Path) -> str:
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        raise InvalidTarget(str(exc)) from exc
    nonempty = [line for line in lines if line]
    if len(nonempty) != 1 or not _valid_thread_id(nonempty[0]):
        raise InvalidTarget("target file must contain exactly one canonical UUID")
    return nonempty[0]


def _validate_state(raw: object) -> GuardState:
    if not isinstance(raw, dict):
        raise InvalidState("state must be a JSON object")

    expected = {
        "target_thread_id",
        "boot_id",
        "idle_since_monotonic",
        "reminder_attempted",
        "reminder_result",
    }
    if set(raw) != expected:
        raise InvalidState("state fields are incomplete or unexpected")
    if not _valid_thread_id(raw["target_thread_id"]):
        raise InvalidState("state target is not a canonical UUID")
    if not isinstance(raw["boot_id"], str) or not raw["boot_id"]:
        raise InvalidState("state boot ID is invalid")

    idle_since = raw["idle_since_monotonic"]
    if idle_since is not None:
        if isinstance(idle_since, bool) or not isinstance(idle_since, (int, float)):
            raise InvalidState("idle time is invalid")
        if idle_since < 0 or not math.isfinite(float(idle_since)):
            raise InvalidState("idle time is invalid")
        idle_since = float(idle_since)

    attempted = raw["reminder_attempted"]
    if not isinstance(attempted, bool):
        raise InvalidState("attempt marker is invalid")
    result = raw["reminder_result"]
    if result not in {None, "pending", "queued", "failed"}:
        raise InvalidState("reminder result is invalid")
    if not attempted and result is not None:
        raise InvalidState("a result requires an attempt marker")

    return GuardState(
        target_thread_id=raw["target_thread_id"],
        boot_id=raw["boot_id"],
        idle_since_monotonic=idle_since,
        reminder_attempted=attempted,
        reminder_result=result,
    )


def load_state(path: Path) -> GuardState | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidState(str(exc)) from exc
    return _validate_state(raw)


def save_state(path: Path, guard_state: GuardState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(guard_state), handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _reset_after_active(guard_state: GuardState) -> None:
    guard_state.idle_since_monotonic = None
    guard_state.reminder_attempted = False
    guard_state.reminder_result = None


def _clear_unconfirmed_idle(guard_state: GuardState) -> None:
    if not guard_state.reminder_attempted:
        guard_state.idle_since_monotonic = None
        guard_state.reminder_result = None


async def run_cycle(
    paths: GuardPaths,
    *,
    now: float,
    boot_id: str,
    read_status: StatusReader,
    auth_is_chatgpt: BooleanCheck,
    versions_compatible: BooleanCheck,
    queue_message: MessageQueue,
    idle_seconds: float = IDLE_SECONDS,
) -> CycleResult:
    """Run one fail-closed status check without reading conversation turns."""

    if not paths.arm_file.is_file():
        return CycleResult("disarmed")

    try:
        target = read_target(paths.target_file)
    except InvalidTarget as exc:
        return CycleResult("invalid_target", str(exc))

    try:
        guard_state = load_state(paths.state_file)
    except InvalidState as exc:
        return CycleResult("invalid_state", str(exc))

    if (
        guard_state is None
        or guard_state.target_thread_id != target
        or guard_state.boot_id != boot_id
    ):
        guard_state = GuardState(target_thread_id=target, boot_id=boot_id)

    try:
        status = await read_status(target)
    except Exception as exc:
        _clear_unconfirmed_idle(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("status_error", str(exc))

    if status == "active":
        _reset_after_active(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("active")
    if status != "idle":
        _clear_unconfirmed_idle(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("unsafe_status", status)

    if guard_state.reminder_attempted:
        save_state(paths.state_file, guard_state)
        return CycleResult("already_attempted", guard_state.reminder_result or "")

    if (
        guard_state.idle_since_monotonic is None
        or now < guard_state.idle_since_monotonic
    ):
        guard_state.idle_since_monotonic = now
        save_state(paths.state_file, guard_state)
        return CycleResult("idle_waiting")

    if now - guard_state.idle_since_monotonic < idle_seconds:
        save_state(paths.state_file, guard_state)
        return CycleResult("idle_waiting")

    try:
        if not auth_is_chatgpt():
            return CycleResult("wrong_auth")
    except Exception as exc:
        return CycleResult("auth_error", str(exc))

    try:
        if not versions_compatible():
            return CycleResult("version_mismatch")
    except Exception as exc:
        return CycleResult("version_error", str(exc))

    try:
        fresh_status = await read_status(target)
    except Exception as exc:
        _clear_unconfirmed_idle(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("status_error", str(exc))

    if fresh_status == "active":
        _reset_after_active(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("became_active")
    if fresh_status != "idle":
        _clear_unconfirmed_idle(guard_state)
        save_state(paths.state_file, guard_state)
        return CycleResult("unsafe_status", fresh_status)

    if not paths.arm_file.is_file():
        return CycleResult("disarmed_before_queue")
    try:
        if read_target(paths.target_file) != target:
            return CycleResult("target_changed")
    except InvalidTarget as exc:
        return CycleResult("invalid_target", str(exc))

    # This write is deliberately before the queue call.  A crash can therefore
    # miss one reminder, but it cannot send a duplicate reminder after restart.
    guard_state.reminder_attempted = True
    guard_state.reminder_result = "pending"
    save_state(paths.state_file, guard_state)

    try:
        queue_message(target, REMINDER)
    except Exception as exc:
        guard_state.reminder_result = "failed"
        save_state(paths.state_file, guard_state)
        return CycleResult("queue_failed", str(exc))

    guard_state.reminder_result = "queued"
    save_state(paths.state_file, guard_state)
    return CycleResult("reminder_queued")


def clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    return environment


async def read_app_server_status(paths: GuardPaths, target: str) -> str:
    import websockets

    async with websockets.unix_connect(
        path=str(paths.socket_file),
        uri="ws://localhost",
        compression=None,
        user_agent_header=None,
        open_timeout=10,
        close_timeout=5,
    ) as socket:
        await socket.send(
            json.dumps(
                {
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "clientInfo": {
                            "name": "eventmarketdb_codex_liveness",
                            "title": "EventMarketDB Codex Liveness",
                            "version": "1.0.0",
                        }
                    },
                }
            )
        )
        await _read_rpc_result(socket, 1)
        await socket.send(json.dumps({"method": "initialized", "params": {}}))
        await socket.send(
            json.dumps(
                {
                    "method": "thread/read",
                    "id": 2,
                    "params": {"threadId": target, "includeTurns": False},
                }
            )
        )
        result = await _read_rpc_result(socket, 2)

    try:
        status = result["thread"]["status"]["type"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("app-server returned no thread status") from exc
    if not isinstance(status, str):
        raise RuntimeError("app-server returned an invalid thread status")
    return status


async def _read_rpc_result(socket: object, request_id: int) -> dict:
    for _ in range(50):
        raw_message = await asyncio.wait_for(socket.recv(), timeout=10)
        message = json.loads(raw_message)
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise RuntimeError(f"app-server request failed: {message['error']}")
        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("app-server returned an invalid result")
        return result
    raise RuntimeError("app-server did not answer the request")


def _run_codex(paths: GuardPaths, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(paths.codex_binary), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=clean_environment(),
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


def auth_is_chatgpt(paths: GuardPaths) -> bool:
    result = _run_codex(paths, ["login", "status"])
    return result.returncode == 0 and result.stdout.strip() == "Logged in using ChatGPT"


_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _version_tuple(version: object) -> tuple[int, int, int] | None:
    if not isinstance(version, str):
        return None
    match = _VERSION_PATTERN.fullmatch(version)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def versions_compatible(paths: GuardPaths) -> bool:
    result = _run_codex(paths, ["app-server", "daemon", "version"])
    if result.returncode != 0:
        return False
    try:
        details = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    cli_version = _version_tuple(details.get("cliVersion"))
    server_version = _version_tuple(details.get("appServerVersion"))
    return (
        details.get("status") == "running"
        and cli_version is not None
        and server_version is not None
        and cli_version == server_version
        and cli_version >= MIN_QUEUE_VERSION
    )


def queue_message(paths: GuardPaths, target: str, message: str) -> None:
    remote = f"unix://{paths.socket_file}"
    result = _run_codex(
        paths,
        [
            "queue",
            "--thread",
            target,
            "--message",
            message,
            "--remote",
            remote,
        ],
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"codex queue failed: {detail}")


def read_boot_id() -> str:
    value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    if not _valid_thread_id(value):
        raise RuntimeError("Linux boot ID is invalid")
    return value


async def live_cycle(paths: GuardPaths) -> CycleResult:
    return await run_cycle(
        paths,
        now=time.monotonic(),
        boot_id=read_boot_id(),
        read_status=lambda target: read_app_server_status(paths, target),
        auth_is_chatgpt=lambda: auth_is_chatgpt(paths),
        versions_compatible=lambda: versions_compatible(paths),
        queue_message=lambda target, message: queue_message(paths, target, message),
    )


def _log_result(result: CycleResult) -> None:
    if result.outcome in {
        "invalid_target",
        "invalid_state",
        "status_error",
        "auth_error",
        "version_error",
        "wrong_auth",
        "version_mismatch",
        "queue_failed",
    }:
        logging.warning("guard outcome=%s detail=%s", result.outcome, result.detail)
    else:
        logging.info("guard outcome=%s", result.outcome)


async def run_service(paths: GuardPaths) -> None:
    while True:
        try:
            _log_result(await live_cycle(paths))
        except Exception:
            logging.exception("guard cycle failed closed")
        await asyncio.sleep(CHECK_SECONDS)


async def read_only(paths: GuardPaths) -> int:
    try:
        target = read_target(paths.target_file)
        status = await read_app_server_status(paths, target)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "targetThreadId": target,
                "status": status,
                "turnsRead": False,
            },
            sort_keys=True,
        )
    )
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="run one armed cycle")
    mode.add_argument(
        "--read-only",
        action="store_true",
        help="read only the target runtime status; do not change state",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if arguments.read_only:
        return asyncio.run(read_only(DEFAULT_PATHS))

    DEFAULT_PATHS.lock_file.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_PATHS.lock_file.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        if arguments.once:
            _log_result(asyncio.run(live_cycle(DEFAULT_PATHS)))
            return 0
        asyncio.run(run_service(DEFAULT_PATHS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
