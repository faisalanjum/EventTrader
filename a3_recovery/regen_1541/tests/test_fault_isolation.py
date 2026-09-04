"""A recompiled fault touches ONE symbol and nothing the module body installs elsewhere.

`recompiled()` executes the module's source into a fresh namespace; chrono_replay's
body installs four hooks into replay_transcript at import (SIBLING_RESOLVER,
TREE_COMMIT, TREE_MODIFIED, SELECT_UNITS), so every recompiled chrono fault re-pointed
those hooks at the mutant namespace and the revert put back only the targeted
attribute. The append fault then left SELECT_UNITS calling a mutant `_python_writes`,
and an unrelated control failed inside the audit (row "a command starts in its record's
directory") while passing alone.
"""
import glob
import importlib
import os
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(R, "ledger"), R, os.path.join(R, "proofs")]
import chrono_replay as CR  # noqa: E402
import replay_transcript as RT  # noqa: E402
import replay_caches  # noqa: E402
import mutations as MU  # noqa: E402

HOOKS = ("SIBLING_RESOLVER", "TREE_COMMIT", "TREE_MODIFIED", "SELECT_UNITS")


def test_a_recompiled_fault_leaves_the_transcript_hooks_untouched():
    before = {h: getattr(RT, h) for h in HOOKS}
    with replay_caches.preserved(CR, RT), MU.FAULTS["an append is not a write"].applied(True):
        assert CR.DISK_CACHE_WRITES is False           # read-only while the fault is applied
    after = {h: getattr(RT, h) for h in HOOKS}
    assert all(after[h] is before[h] for h in HOOKS), [h for h in HOOKS if after[h] is not before[h]]
    assert CR.DISK_CACHE_WRITES is True                # and writable again afterwards


def test_the_record_directory_control_still_passes_after_the_append_fault():
    with replay_caches.preserved(CR, RT), MU.FAULTS["an append is not a write"].applied(True):
        pass
    mod = importlib.import_module("test_replay_world") if "test_replay_world" in sys.modules else None
    if mod is None:
        sys.path.insert(0, os.path.join(R, "tests"))
        mod = importlib.import_module("test_replay_world")
    with replay_caches.preserved(CR, RT):
        mod.test_a_command_without_cd_stood_in_the_records_working_directory()


def test_nested_applied_faults_restore_the_exact_prior_flag():
    """`applied()` once forced DISK_CACHE_WRITES=True on exit: an inner context re-enabled
    disk writes while the outer fault was still applied, and a prior False was lost."""
    f, g = MU.FAULTS["an append is not a write"], MU.FAULTS["the prefix digest is not compared"]
    prior = CR.DISK_CACHE_WRITES
    try:
        for start in (True, False):
            CR.DISK_CACHE_WRITES = start
            with replay_caches.preserved(CR, RT), f.applied(True):
                with g.applied(True):
                    assert CR.DISK_CACHE_WRITES is False
                assert CR.DISK_CACHE_WRITES is False           # still inside the outer fault
            assert CR.DISK_CACHE_WRITES is start               # the exact prior, not True
    finally:
        CR.DISK_CACHE_WRITES = prior


def test_a_fault_whose_setup_fails_leaves_the_flag_as_it_was():
    prior = CR.DISK_CACHE_WRITES
    try:
        for start in (True, False):
            CR.DISK_CACHE_WRITES = start
            bad = MU.Fault("NOPE.nothing", lambda saved: saved)
            try:
                with bad.applied(True):
                    raise AssertionError("an unregistered owner must not apply")
            except KeyError:
                pass
            assert CR.DISK_CACHE_WRITES is start
            try:
                bad.install()
                raise AssertionError("an unregistered owner must not install")
            except KeyError:
                pass
            assert CR.DISK_CACHE_WRITES is start
    finally:
        CR.DISK_CACHE_WRITES = prior


def test_restore_puts_back_the_snapshot_value_of_the_flag():
    prior = CR.DISK_CACHE_WRITES
    try:
        CR.DISK_CACHE_WRITES = False
        shot = MU._snapshot()
        CR.DISK_CACHE_WRITES = True
        MU._restore(shot)
        assert CR.DISK_CACHE_WRITES is False                   # the snapshot's value, not a forced True
    finally:
        CR.DISK_CACHE_WRITES = prior


def _host():
    import builtins
    import io as _io
    import time
    return (_io.open, builtins.open, os.path.isfile, os.path.exists, os.path.isdir, os.listdir, os.walk,
            os.getcwd, time.sleep, sys.modules.get("subprocess"), os.scandir, os.path.lexists, sys.argv, list(sys.meta_path))


def _restore_host(h):
    import builtins
    import io as _io
    import time
    _io.open, builtins.open, os.path.isfile, os.path.exists, os.path.isdir, os.listdir, os.walk, os.getcwd, time.sleep = h[:9]
    if h[9] is None:
        sys.modules.pop("subprocess", None)
    else:
        sys.modules["subprocess"] = h[9]
    os.scandir, os.path.lexists, sys.argv = h[10:13]
    sys.meta_path[:] = h[13]


def test_a_replay_whose_arming_fails_leaves_the_host_unpatched():
    """Harness case 94's mutant raised while the sandbox was half armed - between the
    first patch of io.open and the try that restores it stood a hundred lines of setup -
    so io.open, builtins.open, the os questions, time.sleep and sys.modules['subprocess']
    stayed patched for every later case: 13 harness errors, none of them the cases' own."""
    import contextlib
    import io as _io
    before = _host()
    H = "/tmp/claude-1000/x/scratchpad/" + MU.BENCH
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport a_module_that_never_existed\n"
           "io.open('thing.py','w').write('X\\n')\nPY\n" % H)
    try:
        with replay_caches.preserved(CR, RT), MU.FAULTS["an unknown module is not invented"].applied(True):
            try:
                with contextlib.redirect_stdout(_io.StringIO()):
                    RT.apply_saved_edits("BASE\n", {1: MU._rec(cmd)}, MU.BENCH + "/thing.py", side={})
            except Exception:                                  # noqa: BLE001 - the mutant's own failure
                pass
        after = _host()
        names = ("io.open", "builtins.open", "os.path.isfile", "os.path.exists", "os.path.isdir", "os.listdir", "os.walk",
                 "os.getcwd", "time.sleep", "sys.modules[subprocess]", "os.scandir", "os.path.lexists", "sys.argv", "sys.meta_path")
        leaked = [n for n, a, b in zip(names, before, after) if (a != b if n == "sys.meta_path" else a is not b)]
        assert leaked == [], leaked
    finally:
        _restore_host(before)                                  # this control never poisons the next one


def test_a_host_leak_is_charged_to_its_case():
    """The harness fence: a binding a case leaves changed on a host module is reported
    by name, never repaired in silence, and the restore puts it back."""
    import io as _io
    shot = MU._snapshot()
    real = _io.open
    try:
        _io.open = lambda *a, **k: real(*a, **k)
        assert MU._leaked(shot) == ["io.open"]
    finally:
        _io.open = real
    assert MU._leaked(shot) == []
    MU._restore(shot)
    assert _io.open is real


def test_repeated_snapshot_and_restore_does_not_grow_the_host():
    """Codex SEQ 1563 item 1: each _snapshot inserted R into sys.path and no restore removed
    it, so every snapshot grew host state (R_counts 0 1 1 in the reviewer's own proof)."""
    before = list(sys.path)
    for _ in range(3):
        MU._restore(MU._snapshot())
    assert sys.path == before, [p for p in sys.path if p not in before]


def test_in_place_host_mutations_are_charged_and_restored():
    """A shallow snapshot of module bindings sees the same list object after an in-place
    change: sys.path, sys.meta_path and sys.argv were neither charged nor restored."""
    shot = MU._snapshot()
    p, m, a = sys.path, sys.meta_path, sys.argv
    p0, m0, a0 = list(p), list(m), list(a)
    marker = object()
    try:
        sys.path.append("/nowhere/x")
        sys.meta_path.append(marker)
        sys.argv.append("--injected")
        leaked = MU._leaked(shot)
        assert {"sys.path", "sys.meta_path", "sys.argv"} <= {l.split(" ")[0].split("[")[0] for l in leaked}, leaked
        MU._restore(shot)
        assert sys.path is p and sys.path == p0
        assert sys.meta_path is m and sys.meta_path == m0
        assert sys.argv is a and sys.argv == a0
        assert MU._leaked(shot) == []
    finally:
        p[:] = p0
        m[:] = m0
        a[:] = a0


def test_a_replaced_registry_entry_is_charged_and_restored():
    """A registry such as sys.modules grows by import - an added key is not a mutation of
    the world - but a changed or removed existing key is, and is put back exactly."""
    shot = MU._snapshot()
    real = sys.modules["subprocess"]
    try:
        sys.modules["subprocess"] = object()
        leaked = MU._leaked(shot)
        assert any(l.startswith("sys.modules[") and "subprocess" in l for l in leaked), leaked
        MU._restore(shot)
        assert sys.modules["subprocess"] is real
    finally:
        sys.modules["subprocess"] = real


def test_added_host_state_is_charged_and_removed():
    """Codex SEQ 1564 item 1: the fence compared only what the snapshot held, so a NEW
    environment key, a NEW module-registry entry and a NEW host-module attribute were
    neither charged nor removed (reported [], survives True True False in the reviewer's
    own proof). Growth is hidden state when later cases share the process."""
    import os as _os
    import types
    shot = MU._snapshot()
    _os.environ["X_NEW_1564"] = "1"
    sys.modules["x_new_1564"] = types.ModuleType("x_new_1564")
    sys.x_new_1564 = 1
    try:
        leaked = MU._leaked(shot)
        assert any("os.environ" in l and "X_NEW_1564" in l for l in leaked), leaked
        assert any("sys.modules" in l and "x_new_1564" in l for l in leaked), leaked
        assert any(l == "sys.x_new_1564" for l in leaked), leaked
        MU._restore(shot)
        assert "X_NEW_1564" not in _os.environ
        assert "x_new_1564" not in sys.modules
        assert not hasattr(sys, "x_new_1564")
        assert MU._leaked(shot) == []
    finally:
        _os.environ.pop("X_NEW_1564", None)
        sys.modules.pop("x_new_1564", None)
        if hasattr(sys, "x_new_1564"):
            del sys.x_new_1564


def test_the_fenced_runner_charges_a_leaky_base_run_and_restores():
    """The audit fenced only its mutant run; a base run went through the cache fence alone
    and could contaminate its mutant and later rows without becoming ERROR. ONE fenced
    runner serves the harness and both audit runs: it returns what the run left changed
    and puts the host back exactly."""
    import os as _os
    def leaky():
        _os.environ["X_BASE_1564"] = "1"
        sys.x_base_1564 = 1
        return "ran"
    try:
        result, leak = MU.fenced(leaky)
        assert result == "ran"
        assert any("X_BASE_1564" in l for l in leak) and any(l == "sys.x_base_1564" for l in leak), leak
        assert "X_BASE_1564" not in _os.environ and not hasattr(sys, "x_base_1564")
        result, leak = MU.fenced(lambda: 42)
        assert (result, leak) == (42, [])
    finally:
        _os.environ.pop("X_BASE_1564", None)
        if hasattr(sys, "x_base_1564"):
            del sys.x_base_1564
