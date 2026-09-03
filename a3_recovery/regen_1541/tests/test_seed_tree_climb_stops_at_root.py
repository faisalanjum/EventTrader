"""A copy source outside every seeded tree has no seed tree - and says so promptly.

`_dir_files` climbed from the source directory to the seeded tree it lies under; for
a source outside every such tree the climb reached "/" whose parent is "/" again and
never ended. Ledger recovery 11 and 14 spent hours there (record-level harvest copies
from the repository checkout).
"""
import os
import signal
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import replay_transcript as RT  # noqa: E402


def _bounded(fn, seconds=5):
    def _alarm(_sig, _frm):
        raise TimeoutError("the climb did not end")
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(seconds)
    try:
        return fn()
    except TimeoutError:
        return "THE CLIMB DID NOT END"                 # asserted against, never raised
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def test_a_source_outside_every_seeded_tree_has_no_seed_tree():
    assert _bounded(lambda: RT._seed_tree("/home/faisal/EventMarketDB/driver/core")) is None
    assert _bounded(lambda: RT._seed_tree("/")) is None


def test_a_source_inside_a_seeded_tree_names_that_tree():
    assert RT._seed_tree("/x/step1_iso/a/b") == "/x/step1_iso"
    assert RT._seed_tree("/x/bench_1306/.claude/plans") == "/x/bench_1306"
