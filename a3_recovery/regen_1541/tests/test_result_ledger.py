"""ONE exact result ledger, keyed by tool-use id (Codex SEQ 1544 item 4).

Presence and text are different facts. A command that completed with no output has an
EMPTY result, which is not the same as having no result at all - reading both as
"absent" turned eight real A3 completions into unexplained silence, and would let a
genuinely outstanding call look like a success.

The population controls are measured over Codex's frozen append-only prefix, so they
do not drift as this session keeps writing to the same transcript.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "ledger"))
import replay_transcript as RT                                # noqa: E402

#: Codex's frozen prefix, verified byte-exact this round
FROZEN = 210560179
FROZEN_SHA = "d191941462674e63f16370104478a1e0774b88cbb953b8133a6face8353c1d93"
#: the eight A3-slice results that completed with empty content
EMPTY_A3 = (24632, 24723, 27102, 29525, 29584, 31870, 34343, 35219)


def led():
    return RT.result_ledger(RT.TRANSCRIPT, limit_bytes=FROZEN)


def test_the_frozen_prefix_is_the_one_that_was_measured():
    import hashlib
    import io
    data = io.open(RT.TRANSCRIPT, "rb").read(FROZEN)
    assert len(data) == FROZEN
    assert hashlib.sha256(data).hexdigest() == FROZEN_SHA
    assert data.count(b"\n") == 111621


def test_an_EMPTY_completed_result_is_PRESENT_not_missing():
    """Eight A3 results carry no text at all. They are completions, not silence."""
    L = led()
    for line in EMPTY_A3:
        assert L.present_at(line) is True, line
        assert L.text_at(line) == "", line
        assert RT.saved_result(line) == "", line


def test_a_MISSING_result_is_distinguishable_from_an_empty_one():
    """A use whose result never arrived is outstanding; it must not read as empty."""
    L = led()
    assert L.outstanding, "the frozen boundary cuts one live call"
    for tid in L.outstanding:
        assert tid not in L.text
        assert L.present(tid) is False


def test_the_ledger_accounts_for_EVERY_row_of_the_frozen_prefix():
    """Corrupt, duplicate, unmatched, outstanding and empty rows are each counted."""
    L = led()
    assert L.rows == 111621
    assert L.corrupt == [93274]
    assert len(L.uses) == 17228
    assert len(L.text) == 17227
    assert L.matched == 17227
    assert L.duplicate_uses == []
    assert L.duplicate_results == []
    assert L.unmatched == []
    assert len(L.outstanding) == 1
    assert L.empty_results == 52


def test_a_result_is_matched_by_ID_however_far_it_is_DELAYED():
    """23746's result sits six rows below it, interleaved with assistant text."""
    got = RT.saved_result(23746)
    assert got is not None and "AssertionError" in got


def test_a_WRONG_ID_never_matches():
    """The ledger is keyed by exact id: a neighbouring result is not this call's."""
    L = led()
    assert L.text.get("toolu_this_id_does_not_exist") is None
    assert L.present("toolu_this_id_does_not_exist") is False
