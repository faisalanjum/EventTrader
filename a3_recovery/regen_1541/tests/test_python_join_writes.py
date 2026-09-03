"""A python write through `os.path.join(NAME, "file")` names its owner.

The route finder recognised `open(NAME, "w")`, `open(NAME + "/x", "w")` and literal
paths, but not the join form the campaign used for every run directory:
`io.open(os.path.join(run, "attempts.json"), "w")` with `run = sys.argv[1]` (the run
directory passed on the command line) or `RUN = ("...")` (a literal). Neither the
file's creation nor the harvest program's rewrites of it were routes, so the ledger
replay found `invrev_run2/attempts.json` "not part of the replay world".
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import chrono_replay as CR  # noqa: E402

S = "/tmp/claude-1000/x/scratchpad"


def test_a_join_of_a_literal_directory_is_a_write_of_that_file():
    cmd = ('python3 - <<\'PY\'\nimport io, os\nRUN = ("%s"\n       "/invrev_run2")\n'
           'io.open(os.path.join(RUN, "attempts.json"), "w", encoding="utf-8").write("[]")\nPY\n' % S)
    assert CR.writes_this(cmd, S + "/invrev_run2/attempts.json", line=1, start="/home/x")
    assert not CR.writes_this(cmd, S + "/invrev_run3/attempts.json", line=1, start="/home/x")


def test_a_join_of_a_command_line_argument_is_a_write_of_that_file():
    cmd = ('S=%s\nRUN="$S/invrev_run2"\nmkdir -p "$RUN"\npython3 - "$RUN" <<\'PY\'\n'
           'import io, os, sys\nrun = sys.argv[1]\n'
           'io.open(os.path.join(run, "attempts.json"), "w", encoding="utf-8").write("[]")\nPY\n' % S)
    assert CR.writes_this(cmd, S + "/invrev_run2/attempts.json", line=1, start="/home/x")
    assert not CR.writes_this(cmd, S + "/invrev_run3/attempts.json", line=1, start="/home/x")
