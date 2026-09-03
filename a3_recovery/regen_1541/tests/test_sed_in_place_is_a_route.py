"""`sed -i` on a quoted file is a write of that file - as a route and at replay.

Record 29188 moved the harvest program from run directory 3 to 4 with
`sed -i 's#/scratchpad/invrev_run3#/scratchpad/invrev_run4#' "$S/harvest.py"`. The
route finder knew redirects, copies and scripts but not sed, so the record was not the
program's; and the replay's sed handler kept the quotes on the file token, so even a
routed edit compared `"…/harvest.py"` (quote included) against the owner and skipped
it. The program then read run 2's accumulator where history read run 4's.
"""
import contextlib
import io
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import replay_transcript as RT  # noqa: E402
import chrono_replay as CR  # noqa: E402

S = "/tmp/claude-1000/x/scratchpad"


def test_sed_in_place_on_a_quoted_file_is_a_route_of_that_file():
    cmd = 'S=%s\nsed -i \'s#/scratchpad/invrev_run3#/scratchpad/invrev_run4#\' "$S/harvest.py"\n' % S
    assert CR.writes_this(cmd, S + "/harvest.py", line=1, start="/home/x")
    assert not CR.writes_this(cmd, S + "/other.py", line=1, start="/home/x")


def test_sed_in_place_on_a_quoted_file_is_applied_at_replay():
    cmd = 'S=%s\nsed -i \'s#/scratchpad/invrev_run3#/scratchpad/invrev_run4#\' "$S/harvest.py"\n' % S
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    with contextlib.redirect_stdout(io.StringIO()):
        out, _ = RT.apply_saved_edits('RUN = "%s/invrev_run3"\n' % S, {1: rec}, "harvest.py", side={})
    assert out == 'RUN = "%s/invrev_run4"\n' % S, out


def test_sed_after_a_same_line_cd_names_its_file_relative_to_that_directory():
    E = S + "/step1_envelope/.claude/plans/Drivers/experiments"
    cmd = "cd %s && sed -i 's|old_guard|new_guard|' harness/test_harness_guards.py\n" % E
    assert CR.writes_this(cmd, E + "/harness/test_harness_guards.py", line=1, start="/home/x")
    assert not CR.writes_this(cmd, S + "/step1_ctl/.claude/plans/Drivers/experiments/harness/test_harness_guards.py",
                              line=1, start="/home/x")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}, "cwd": "/home/x"}
    with contextlib.redirect_stdout(io.StringIO()):
        out, _ = RT.apply_saved_edits("x = old_guard\n", {1: rec},
                                      "step1_envelope/.claude/plans/Drivers/experiments/harness/test_harness_guards.py", side={})
    assert out == "x = new_guard\n", out
