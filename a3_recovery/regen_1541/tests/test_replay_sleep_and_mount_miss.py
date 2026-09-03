"""Two rules from the ledger's hour-long hang at record 29758.

The harvest program polled a workflow state file 360 times with `time.sleep(10)`
between tries. Under replay the world is fixed, so the wait decides nothing and a
replay that sleeps real time on it is not a computation. And the file it polled
through `os.path.isfile` was absent from its mount: the miss was never recorded,
so the recovery tool that copies missing mount files had nothing to copy.
"""
import contextlib
import io
import os
import sys
import tempfile

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import replay_transcript as RT  # noqa: E402


def test_a_replayed_program_does_not_sleep_real_time():
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io, time\nt = time.time(); time.sleep(3)\n"
           "io.open('thing.py','w').write(str(time.time() - t < 1) + '\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    with contextlib.redirect_stdout(io.StringIO()):
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side={})
    assert out == "True\n", out


def test_an_absent_mounted_file_asked_through_isfile_is_a_recorded_miss():
    d = tempfile.mkdtemp()
    io.open(os.path.join(d, "held.json"), "w").write("{}")
    root = "/hist/session/workflows"
    saved = dict(RT.MOUNTS)
    RT.MOUNTS[root] = d
    try:
        del RT.MOUNT_MISSES[:]
        assert RT._world_isfile(root + "/held.json", {}) is True
        assert RT._world_isfile(root + "/gone.json", {}) is False
        assert root + "/gone.json" in RT.MOUNT_MISSES
        assert root + "/held.json" not in RT.MOUNT_MISSES
    finally:
        RT.MOUNTS.clear()
        RT.MOUNTS.update(saved)
