import asyncio
import json
from pathlib import Path

import pytest

from scripts.orchestration.codex_liveness_guard import (
    DEFAULT_PATHS,
    REMINDER,
    GuardPaths,
    run_cycle,
)


TARGET_ID = "01a005e4-4289-7650-b77b-a1b3802aa386"
OTHER_ID = "01a02f89-371a-7541-86f4-7272168af1a4"


def test_guard_uses_the_managed_codex_binary() -> None:
    assert DEFAULT_PATHS.codex_binary == (
        Path.home() / ".codex/packages/standalone/current/codex"
    )


def make_paths(tmp_path: Path, *, armed: bool = True) -> GuardPaths:
    paths = GuardPaths(
        target_file=tmp_path / "target",
        arm_file=tmp_path / "armed",
        state_file=tmp_path / "state.json",
        lock_file=tmp_path / "guard.lock",
        socket_file=tmp_path / "app-server.sock",
    )
    paths.target_file.write_text(f"{TARGET_ID}\n", encoding="utf-8")
    if armed:
        paths.arm_file.write_text("armed\n", encoding="utf-8")
    return paths


def state(paths: GuardPaths) -> dict:
    return json.loads(paths.state_file.read_text(encoding="utf-8"))


def cycle(
    paths: GuardPaths,
    *,
    now: float,
    status="idle",
    boot_id="boot-a",
    auth=True,
    versions=True,
    queued=None,
):
    statuses = iter(status if isinstance(status, list) else [status, status])

    async def read_status(thread_id: str) -> str:
        assert thread_id == TARGET_ID
        return next(statuses)

    def queue_message(thread_id: str, message: str) -> None:
        if queued is not None:
            queued.append((thread_id, message))

    return asyncio.run(
        run_cycle(
            paths,
            now=now,
            boot_id=boot_id,
            read_status=read_status,
            auth_is_chatgpt=lambda: auth,
            versions_compatible=lambda: versions,
            queue_message=queue_message,
        )
    )


def test_reminder_text_is_exact() -> None:
    assert REMINDER == (
        "Reminder: Keep the loop on so you continue to orchestrate core/claude"
    )


def test_active_target_resets_an_old_idle_episode(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.state_file.write_text(
        json.dumps(
            {
                "target_thread_id": TARGET_ID,
                "boot_id": "boot-a",
                "idle_since_monotonic": 10.0,
                "reminder_attempted": True,
                "reminder_result": "queued",
            }
        ),
        encoding="utf-8",
    )

    result = cycle(paths, now=1_000.0, status="active")

    assert result.outcome == "active"
    assert state(paths)["idle_since_monotonic"] is None
    assert state(paths)["reminder_attempted"] is False


def test_idle_target_is_reminded_once_after_full_fifteen_minutes(
    tmp_path: Path,
) -> None:
    paths = make_paths(tmp_path)
    queued = []

    assert cycle(paths, now=100.0, queued=queued).outcome == "idle_waiting"
    assert cycle(paths, now=999.0, queued=queued).outcome == "idle_waiting"
    assert queued == []

    assert cycle(paths, now=1_000.0, queued=queued).outcome == "reminder_queued"
    assert queued == [(TARGET_ID, REMINDER)]
    assert state(paths)["reminder_attempted"] is True
    assert state(paths)["reminder_result"] == "queued"

    assert cycle(paths, now=2_000.0, queued=queued).outcome == "already_attempted"
    assert queued == [(TARGET_ID, REMINDER)]


def test_a_new_idle_episode_can_send_one_new_reminder(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    queued = []

    cycle(paths, now=100.0, queued=queued)
    cycle(paths, now=1_000.0, queued=queued)
    cycle(paths, now=1_010.0, status="active", queued=queued)
    cycle(paths, now=1_020.0, queued=queued)
    cycle(paths, now=1_920.0, queued=queued)

    assert queued == [(TARGET_ID, REMINDER), (TARGET_ID, REMINDER)]


@pytest.mark.parametrize("status", ["notLoaded", "systemError", "unexpected"])
def test_unsafe_target_status_never_sends(tmp_path: Path, status: str) -> None:
    paths = make_paths(tmp_path)
    queued = []

    cycle(paths, now=100.0, queued=queued)
    result = cycle(paths, now=1_000.0, status=status, queued=queued)

    assert result.outcome == "unsafe_status"
    assert queued == []
    assert state(paths)["idle_since_monotonic"] is None


def test_disarmed_guard_does_not_read_or_send(tmp_path: Path) -> None:
    paths = make_paths(tmp_path, armed=False)
    called = False

    async def read_status(_thread_id: str) -> str:
        nonlocal called
        called = True
        return "idle"

    queued = []
    result = asyncio.run(
        run_cycle(
            paths,
            now=1_000.0,
            boot_id="boot-a",
            read_status=read_status,
            auth_is_chatgpt=lambda: True,
            versions_compatible=lambda: True,
            queue_message=lambda thread_id, message: queued.append(
                (thread_id, message)
            ),
        )
    )

    assert result.outcome == "disarmed"
    assert called is False
    assert queued == []


@pytest.mark.parametrize(
    ("auth", "versions", "outcome"),
    [
        (False, True, "wrong_auth"),
        (True, False, "version_mismatch"),
    ],
)
def test_auth_and_version_checks_fail_closed(
    tmp_path: Path,
    auth: bool,
    versions: bool,
    outcome: str,
) -> None:
    paths = make_paths(tmp_path)
    queued = []
    cycle(paths, now=100.0, queued=queued)

    result = cycle(
        paths,
        now=1_000.0,
        auth=auth,
        versions=versions,
        queued=queued,
    )

    assert result.outcome == outcome
    assert queued == []
    assert state(paths)["reminder_attempted"] is False


def test_target_is_checked_again_immediately_before_queueing(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    queued = []
    cycle(paths, now=100.0, queued=queued)

    result = cycle(
        paths,
        now=1_000.0,
        status=["idle", "active"],
        queued=queued,
    )

    assert result.outcome == "became_active"
    assert queued == []
    assert state(paths)["idle_since_monotonic"] is None


def test_invalid_target_file_fails_before_reading_status(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.target_file.write_text(f"{TARGET_ID}\n{OTHER_ID}\n", encoding="utf-8")
    called = False

    async def read_status(_thread_id: str) -> str:
        nonlocal called
        called = True
        return "idle"

    result = asyncio.run(
        run_cycle(
            paths,
            now=1_000.0,
            boot_id="boot-a",
            read_status=read_status,
            auth_is_chatgpt=lambda: True,
            versions_compatible=lambda: True,
            queue_message=lambda _thread_id, _message: pytest.fail(
                "must not queue"
            ),
        )
    )

    assert result.outcome == "invalid_target"
    assert called is False


def test_corrupt_existing_state_fails_closed(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.state_file.write_text("not json", encoding="utf-8")
    called = False

    async def read_status(_thread_id: str) -> str:
        nonlocal called
        called = True
        return "idle"

    result = asyncio.run(
        run_cycle(
            paths,
            now=1_000.0,
            boot_id="boot-a",
            read_status=read_status,
            auth_is_chatgpt=lambda: True,
            versions_compatible=lambda: True,
            queue_message=lambda _thread_id, _message: pytest.fail(
                "must not queue"
            ),
        )
    )

    assert result.outcome == "invalid_state"
    assert called is False


def test_boot_or_target_change_starts_a_fresh_idle_clock(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    queued = []
    cycle(paths, now=100.0, queued=queued)

    assert (
        cycle(paths, now=1_000.0, boot_id="boot-b", queued=queued).outcome
        == "idle_waiting"
    )
    assert queued == []
    assert state(paths)["idle_since_monotonic"] == 1_000.0

    paths.target_file.write_text(f"{OTHER_ID}\n", encoding="utf-8")

    async def other_status(thread_id: str) -> str:
        assert thread_id == OTHER_ID
        return "idle"

    result = asyncio.run(
        run_cycle(
            paths,
            now=2_000.0,
            boot_id="boot-b",
            read_status=other_status,
            auth_is_chatgpt=lambda: True,
            versions_compatible=lambda: True,
            queue_message=lambda _thread_id, _message: pytest.fail(
                "must not queue"
            ),
        )
    )

    assert result.outcome == "idle_waiting"
    assert state(paths)["target_thread_id"] == OTHER_ID
    assert state(paths)["idle_since_monotonic"] == 2_000.0


def test_queue_failure_is_recorded_before_call_and_never_retried(
    tmp_path: Path,
) -> None:
    paths = make_paths(tmp_path)
    cycle(paths, now=100.0)
    attempts = []

    def failing_queue(thread_id: str, message: str) -> None:
        attempts.append((thread_id, message))
        saved = state(paths)
        assert saved["reminder_attempted"] is True
        assert saved["reminder_result"] == "pending"
        raise RuntimeError("simulated failure")

    async def idle(_thread_id: str) -> str:
        return "idle"

    result = asyncio.run(
        run_cycle(
            paths,
            now=1_000.0,
            boot_id="boot-a",
            read_status=idle,
            auth_is_chatgpt=lambda: True,
            versions_compatible=lambda: True,
            queue_message=failing_queue,
        )
    )

    assert result.outcome == "queue_failed"
    assert state(paths)["reminder_result"] == "failed"

    queued_after_restart = []
    result = cycle(paths, now=2_000.0, queued=queued_after_restart)
    assert result.outcome == "already_attempted"
    assert attempts == [(TARGET_ID, REMINDER)]
    assert queued_after_restart == []
