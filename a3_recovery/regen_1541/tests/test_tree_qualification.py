"""Another tree's copy of the same filename is not this owner (Codex SEQ 1558).

The `wrong tree` fault was declared and killed by its case control but used by no
inventory row, and the existing named test does not detect it: that test covers an
ABSOLUTE destination accepted on its bare filename, while this rule covers a write
judged by bare filename ALONE. Two distinct ways the same rule owner can break, so the
unused fault owns a real rule and needed a named test rather than deletion.
"""
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "ledger"))
import chrono_replay as CR                                     # noqa: E402

BENCH = "bench_1306/.claude/plans/Drivers/experiments/harness"
OTHER = "/tmp/claude-1000/x/scratchpad/p1319/.claude/plans/Drivers/experiments/harness"


def test_a_write_into_ANOTHER_tree_is_not_a_write_of_this_owner():
    """The command NAMES this owner's tree, so a cheap prefilter passes and the
    decision falls to the rule that resolves the write destination."""
    cmd = ('echo "comparing against %s/raw_transport.py"\n'
           'cd "%s" && python3 - <<\'PY\'\n'
           'import io\n'
           'io.open("raw_transport.py","w",encoding="utf-8").write("other tree")\n'
           'PY\n' % (BENCH, OTHER))
    assert CR.writes_this(cmd, BENCH + "/raw_transport.py") is False


def test_a_write_into_THIS_tree_still_counts():
    """The positive half: the rule must not simply refuse everything."""
    here = "/tmp/claude-1000/x/scratchpad/" + BENCH
    cmd = ('cd "%s" && python3 - <<\'PY\'\n'
           'import io\n'
           'io.open("raw_transport.py","w",encoding="utf-8").write("this tree")\n'
           'PY\n' % here)
    assert CR.writes_this(cmd, BENCH + "/raw_transport.py") is True
