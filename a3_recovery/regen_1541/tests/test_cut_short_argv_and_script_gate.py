"""Three rules from the ledger's accumulator rebuilding EMPTY.

1. A program the replay cut short (its `subprocess` call) had already written the
   owner; the "no half-edit" restore undid that write although the unexecuted rest
   of the program never names the owner. The restore is for programs whose remainder
   could still touch the file - it is decided by history's own text.
2. A stdin program invoked with arguments (`python - "$RUN" <<'PY'`) read `sys.argv[1]`
   as the synthetic owner path, so every sibling it wrote under that directory landed
   nowhere a later record could read it. It now gets the arguments the shell passed.
3. The route pre-filter looked for the owner's bare name in the command text; a script
   the command runs (`python "$S/harvest.py" ...`) names the owner only in its own text.
"""
import contextlib
import io
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import replay_transcript as RT  # noqa: E402
import chrono_replay as CR  # noqa: E402

S = "/tmp/claude-1000/x/scratchpad"
OWNER = "run4/attempts.json"


def _rec(cmd, cwd="/home/x"):
    return {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": cmd}}]}, "cwd": cwd}


def test_a_write_survives_a_later_environment_failure_when_the_rest_never_names_the_file():
    cmd = ("python3 - <<'PY'\nimport io, subprocess\n"
           "io.open('%s/run4/attempts.json', 'w').write('[]')\n"
           "subprocess.run(['claude', 'auth', 'status'])\nprint('done')\nPY\n" % S)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            out, _ = RT.apply_saved_edits("", {1: _rec(cmd)}, OWNER, side={})
    except RT.ReplayEnvironmentError as exc:          # the restore emptied the write and the record refused
        out = "refused: %s" % exc
    assert out == "[]", repr(out)


def test_the_restore_still_holds_when_the_rest_of_the_program_names_the_file():
    cmd = ("python3 - <<'PY'\nimport io, subprocess\np = '%s/run4/attempts.json'\n"
           "orig = io.open(p).read()\nio.open(p, 'w').write('EDIT')\n"
           "subprocess.run(['x'])\nio.open(p, 'w').write(orig)\nPY\n" % S)
    # the write is undone and, nothing of history's being known, the record refuses
    import pytest
    with contextlib.redirect_stdout(io.StringIO()), pytest.raises(RT.ReplayEnvironmentError):
        RT.apply_saved_edits("ORIG", {1: _rec(cmd)}, OWNER, side={})


def test_a_stdin_program_with_arguments_gets_them():
    cmd = ("S=%s\nRUN=\"$S/run4\"\npython3 - \"$RUN\" <<'PY'\nimport io, os, sys\n"
           "io.open(os.path.join(sys.argv[1], 'other.json'), 'w').write('SIB')\n"
           "io.open('%s/run4/attempts.json', 'w').write(io.open('%s/run4/other.json').read())\nPY\n"
           % (S, S, S))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            out, _ = RT.apply_saved_edits("", {1: _rec(cmd)}, OWNER, side={})
    except Exception as exc:                          # noqa: BLE001 - the sibling was written elsewhere
        out = "%s: %s" % (type(exc).__name__, exc)
    assert out == "SIB", repr(out)


def test_the_pre_filter_admits_a_command_whose_executed_script_names_the_file(monkeypatch):
    script = ("import io, os\nRUN = ('%s' '/run4')\n"
              "io.open(os.path.join(RUN, 'attempts.json'), 'w').write('[]')\n" % S)
    monkeypatch.setattr(CR, "_executed_script_texts",
                        lambda cmd, before_line=None: [script] if "harvest.py" in cmd else [])
    cmd = 'S=%s\npython -B "$S/harvest.py" 11 sid wf_1 1 | tail -8\n' % S
    assert CR.writes_this(cmd, S + "/run4/attempts.json", line=5, start="/home/x")
    assert not CR.writes_this(cmd, S + "/run3/attempts.json", line=5, start="/home/x")
