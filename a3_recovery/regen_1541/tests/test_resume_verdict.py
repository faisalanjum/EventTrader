"""The resume verdict (Codex SEQ 1559 item 1): an exception is failure, never clean."""
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
import run_resume_path as RRP                                  # noqa: E402


def test_a_completed_run_inside_the_package_is_clean():
    assert RRP.verdict("completed", [], [], [], []) is True


def test_a_run_that_raised_is_NEVER_clean_whatever_it_read():
    assert RRP.verdict("FileNotFoundError: x", [], [], [], []) is False
    assert RRP.verdict("SystemExit 1", [], [], [], []) is False
    assert RRP.verdict(None, [], [], [], []) is False


def test_a_read_into_the_dirty_checkout_is_never_clean():
    assert RRP.verdict("completed", ["/home/faisal/EventMarketDB/x"], [], [], []) is False


def test_an_unmanifested_read_is_never_clean():
    assert RRP.verdict("completed", [], ["/pkg/unlisted"], [], []) is False


def test_a_temporary_tree_read_is_never_clean():
    assert RRP.verdict("completed", [], [], ["/tmp/claude-1000/x"], []) is False


def test_an_unaudited_child_is_never_clean():
    assert RRP.verdict("completed", [], [], [], [["bash", "-c", "x"]]) is False


def test_the_evidence_root_is_the_package_and_is_set_not_inherited(monkeypatch):
    monkeypatch.setenv("KFIELDS_EVIDENCE", "/somewhere/stale")
    assert RRP.EVIDENCE_ROOT.startswith(_R)
    import io
    src = io.open(os.path.join(_R, "run_resume_path.py"), encoding="utf-8").read()
    # the package root is the only default; the explicit verified pair alone may
    # replace it, never an ambient value (Codex SEQ 1561 item 1)
    assert 'os.environ["KFIELDS_EVIDENCE"] = evidence_root or EVIDENCE_ROOT' in src
    assert "setdefault(\"KFIELDS_EVIDENCE\"" not in src
    assert RRP.projection_inputs([]) == (None, None)


def test_home_is_overridden_into_the_package_not_inherited():
    import io
    src = io.open(os.path.join(_R, "run_resume_path.py"), encoding="utf-8").read()
    assert 'os.environ["HOME"] = os.path.join(R, "home")' in src
    assert "searched_reads.append" not in src          # no read is excused as a search
