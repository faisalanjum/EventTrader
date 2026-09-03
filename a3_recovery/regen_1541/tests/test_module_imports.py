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
    kf_lint` must still be served from ITS world, not from sys.modules."""
    import contextlib
    import io as _io
    import sys as _sys
    bench_h = os.path.join(os.path.dirname(__file__), "..", "bench", ".claude", "plans", "Drivers", "experiments", "harness")
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
