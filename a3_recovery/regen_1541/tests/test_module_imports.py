"""A replayed program may IMPORT a sibling, not only open it (Codex SEQ 1544 item 7).

The shim serves reads, but Python's import machinery never calls `open` on a path the
shim would recognise, so a program that did `import kf_lint` died with
ModuleNotFoundError - the last refusal where history had succeeded. The rule is the
same one the shim already applies to reads: a sibling is served as its own history
built it, from the executing process's own tree.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "ledger"))
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402

RAW = "bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py"


def test_a_replayed_program_can_IMPORT_a_sibling_it_could_open():
    """The import must yield the ACTUAL module, not merely a different exception.

    Codex SEQ 1546 caught this control passing while the record still died: asserting
    "not ModuleNotFoundError" is satisfied by any other failure. The rule is that the
    served module is the sibling the tree had, so the control demands the exact symbol
    that only the era's own `kf_lint` provides.
    """
    import contextlib
    import io as _io
    served = {}
    H = ("/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
         "experiments/harness")
    side = {H + "/kf_lint.py": "def part_lookup(source_id, inputs_dir):\n"
                               "    return {'ok': source_id}\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport kf_lint\n"
           "io.open('thing.py','w').write(kf_lint.part_lookup('SID','d')['ok'] + '\\n')\n"
           "PY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
    except ModuleNotFoundError as exc:
        out = "the import was not served: %s" % exc
    assert out == "SID\n", out
    assert served == {}


def test_the_era_kf_lint_is_served_with_its_own_symbols():
    """The real sibling, replayed: 22765's program needs `kf_lint.part_lookup`, which
    the COMMIT's copy does not have. Serving the replayed one is the whole rule."""
    import contextlib
    import io as _io
    o = CR.tree_origin("bench_1306")
    KF = "bench_1306/.claude/plans/Drivers/experiments/harness/kf_lint.py"
    with contextlib.redirect_stdout(_io.StringIO()):
        recs = CR.route_records(KF, o[0], 29152)[0]
        t = RT._committed("/x/" + KF, commit=o[1]) or ""
        for n, r in recs:
            t, _ = RT.apply_saved_edits(t, {n: r}, KF, side={})
    import hashlib
    assert hashlib.sha256(t.encode()).hexdigest().startswith("920742cf"), t[:60]
    assert "def part_lookup" in t


def test_an_UNKNOWN_module_still_refuses():
    """Serving imports must not invent modules: a name no sibling provides still
    raises, so a program cannot quietly run against something that never existed."""
    import contextlib
    import io as _io
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "import a_module_that_never_existed\n"
           "io.open('thing.py','w').write('X\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    raised = None
    with contextlib.redirect_stdout(_io.StringIO()):
        try:
            RT.apply_saved_edits("BASE\n", {1: rec}, owner, side={})
        except Exception as exc:                              # noqa: BLE001
            raised = exc
    assert isinstance(raised, ModuleNotFoundError), repr(raised)


def test_a_pre_imported_bench_module_never_answers_a_replayed_import():
    """The census imports the bench harness owners; a replayed program's `import
    kf_lint` must still be served from ITS world, not from sys.modules. Everything this
    control changes to set that up is put back exactly."""
    import contextlib
    import io as _io
    import sys as _sys
    bench_h = os.path.join(os.path.dirname(__file__), "..", "bench", ".claude", "plans", "Drivers", "experiments", "harness")
    path_before = list(_sys.path)
    env_before = os.environ.get("GUIDANCE_SCRIPTS_DIR")
    mod_before = _sys.modules.get("kf_lint")
    try:
        _sys.path.insert(0, os.path.abspath(bench_h))
        os.environ.setdefault("GUIDANCE_SCRIPTS_DIR", os.path.abspath(os.path.join(bench_h, "..", "..", "..", "..", "..", ".claude", "skills", "earnings-orchestrator", "scripts")))
        import kf_lint as real                                 # the real owner, pre-loaded
        assert "kf_lint" in _sys.modules and real.__file__.startswith(os.path.abspath(bench_h))
        H = ("/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
             "experiments/harness")
        side = {H + "/kf_lint.py": "def part_lookup(source_id, inputs_dir):\n"
                                   "    return {'ok': source_id}\n"}
        cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport kf_lint\n"
               "io.open('thing.py','w').write(kf_lint.part_lookup('SID','d')['ok'] + '\\n')\n"
               "PY\n" % H)
        rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                        "input": {"command": cmd}}]}}
        owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
        assert out == "SID\n", out
        assert _sys.modules.get("kf_lint") is real             # put back afterwards
    finally:
        _sys.path[:] = path_before
        if env_before is None:
            os.environ.pop("GUIDANCE_SCRIPTS_DIR", None)
        else:
            os.environ["GUIDANCE_SCRIPTS_DIR"] = env_before
        if mod_before is None:
            _sys.modules.pop("kf_lint", None)
        else:
            _sys.modules["kf_lint"] = mod_before


def test_the_pre_import_control_leaves_no_trace():
    """The control above inserts a sys.path entry, may set GUIDANCE_SCRIPTS_DIR and imports
    kf_lint; every one of those must be exactly as it was once it returns."""
    import sys as _sys
    path = list(_sys.path)
    env = os.environ.get("GUIDANCE_SCRIPTS_DIR")
    had = _sys.modules.get("kf_lint")
    test_a_pre_imported_bench_module_never_answers_a_replayed_import()
    assert _sys.path == path
    assert os.environ.get("GUIDANCE_SCRIPTS_DIR") == env
    assert _sys.modules.get("kf_lint") is had


def test_a_namespace_package_the_world_served_does_not_linger():
    """`driver/relocation` has no __init__.py; the finder served it as a namespace package
    with NO loader, and the cleanup after a replay - keyed on the loader class - left it
    in sys.modules. The next REAL `import driver.relocation.exact_numbers` then searched
    the world's stale path and failed: the pre-import control failed on a cold cache and
    passed on a warm one (cold-cache rerun, Codex SEQ 1562 round)."""
    import contextlib
    import io as _io
    import sys as _sys
    H = ("/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
         "experiments/harness")
    side = {H + "/nsp/leaf.py": "VALUE = 'leaf'\n"}
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\nimport nsp.leaf\n"
           "io.open('thing.py','w').write(nsp.leaf.VALUE + '\\n')\nPY\n" % H)
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    try:
        with contextlib.redirect_stdout(_io.StringIO()):
            out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
        assert out == "leaf\n", out
        assert [k for k in _sys.modules if k == "nsp" or k.startswith("nsp.")] == []
    finally:
        for k in [k for k in _sys.modules if k == "nsp" or k.startswith("nsp.")]:
            _sys.modules.pop(k)
