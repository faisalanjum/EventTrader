"""A saved traceback ending in a bare exception class is the same failure.

History's `assert x in s` printed `AssertionError` with no message, then the shell
trailer. The replay raised the same bare AssertionError, and the adjudicator asked
for `AssertionError: ` (with a colon) and ruled the identical failure `refused`.
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), ".."),
                os.path.join(os.path.dirname(__file__), "..", "proofs")]
import branch_inventory as BI  # noqa: E402

SAVED = ("Traceback (most recent call last):\n  File \"<stdin>\", line 6, in <module>\n"
         "AssertionError\nShell cwd was reset to /home/faisal/EventMarketDB")


def test_a_bare_exception_class_in_history_matches_a_replay_error_with_no_message():
    assert BI.call_outcome(True, SAVED, True, False,
                           replay_error=("AssertionError", "")) == "faithfully-failed"


def test_a_message_still_has_to_match_exactly():
    assert BI.call_outcome(True, SAVED, True, False,
                           replay_error=("AssertionError", "x")) == "refused"
    assert BI.call_outcome(True, SAVED, True, False,
                           replay_error=("ValueError", "")) == "refused"
