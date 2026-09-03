"""Product identity and call outcome are TWO facts (Codex SEQ 1550).

The report encoded them in one label, so a wrong product overwrote whatever the call
did: `producer-wrong-product-partial` says an exception happened but not whether history
faithfully failed, refused, waited, or never answered at all. Both facts must survive
independently, and only a correct product from a completed call may be finalized.

Each row below is a real positive control driven through the actual report boundary.
"""
import contextlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
import branch_inventory as BI                                 # noqa: E402
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402

AUDIT = "bench_1306/.claude/plans/Drivers/experiments/harness/audit_worker_access.py"
UPTO = 33828
LINES = (25442, 25450)


def producers_of():
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(AUDIT, CR.tree_origin("bench_1306")[0], UPTO)
    return producers


def run():
    with contextlib.redirect_stdout(io.StringIO()):
        return BI.classify(AUDIT, UPTO)


def outstanding_ledger(lines):
    """A REAL outstanding entry: the use is registered, no result ever arrives."""
    real = RT.result_ledger()
    L = RT.ResultLedger()
    L.rows = real.rows
    for line in lines:
        rec = RT.lines([line])[line]
        for b in ((rec.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
                L.uses[b["id"]] = line          # a use with no matching result
    return L


def drive(monkeypatch, *, fail=False, product=None, terminated=False,
          result="ok", present=True, outstanding=False):
    """Put both producers into one exact state and return the report rows."""
    producers = producers_of()
    real = RT.apply_saved_edits

    def act(text, records, basename, prepare=None, side=None, result_=None):
        line = list(records)[0]
        if line in producers:
            if product is not None:
                side[producers[line]] = product
            if fail:
                raise RuntimeError("after the product")
            return text, {}
        return real(text, records, basename, prepare, side, result_)

    monkeypatch.setattr(RT, "apply_saved_edits", act)
    if terminated:
        monkeypatch.setattr(RT, "shell_terminated", lambda r: True)
    monkeypatch.setattr(RT, "saved_result", lambda line, path=None: result)
    monkeypatch.setattr(RT, "result_present", lambda line, path=None: present)
    if outstanding:
        L = outstanding_ledger(LINES)
        monkeypatch.setattr(RT, "result_ledger", lambda *a, **k: L)
    return run()


def test_a_completed_call_with_the_CORRECT_product_is_finalizable():
    _rows, _detail, _text, products = run()
    for line in LINES:
        row = products[line]
        assert row["product_status"] == "correct", row
        assert row["call_outcome"] == "completed", row
        assert row["finalizable"] is True, row


def test_a_faithfully_failed_call_that_wrote_its_product_keeps_BOTH_facts(monkeypatch):
    _rows, _detail, _text, products = drive(
        monkeypatch, fail=True, product="X\n", result="Traceback (most recent call last)")
    for line in LINES:
        row = products[line]
        assert row["product_status"] == "wrong", row      # X\n is not the pinned body
        assert row["call_outcome"] == "faithfully-failed", row
        assert row["present"] is True and row["bytes"] == 2, row
        assert row["finalizable"] is False, row


def test_a_REFUSED_call_that_wrote_its_product_keeps_BOTH_facts(monkeypatch):
    _rows, _detail, _text, products = drive(
        monkeypatch, fail=True, product="X\n", result="all good, no failure text")
    for line in LINES:
        row = products[line]
        assert row["product_status"] == "wrong", row
        assert row["call_outcome"] == "refused", row
        assert row["finalizable"] is False, row


def test_a_truly_OUTSTANDING_call_is_not_credited_by_local_bytes(monkeypatch):
    """The bytes reproduce locally, but history never answered: not completed."""
    _rows, _detail, _text, products = drive(
        monkeypatch, product="X\n", result=None, present=False, outstanding=True)
    for line in LINES:
        row = products[line]
        assert row["call_outcome"] == "waiting", row
        assert row["present"] is True                     # the product exists
        assert row["finalizable"] is False, row


def test_a_MISSING_saved_result_is_not_credited_by_local_bytes(monkeypatch):
    _rows, _detail, _text, products = drive(
        monkeypatch, product="X\n", result=None, present=False)
    for line in LINES:
        row = products[line]
        assert row["call_outcome"] == "missing-result", row
        assert row["finalizable"] is False, row


def test_a_TERMINATED_call_never_executes(monkeypatch):
    _rows, _detail, _text, products = drive(monkeypatch, terminated=True)
    for line in LINES:
        row = products[line]
        assert row["call_outcome"] == "terminated", row
        assert row["product_status"] == "not-attempted", row
        assert row["finalizable"] is False, row


def test_a_WRONG_product_and_a_FAILED_call_both_survive(monkeypatch):
    """Neither fact may overwrite the other."""
    _rows, _detail, _text, products = drive(
        monkeypatch, fail=True, product="BROKEN\n",
        result="Traceback (most recent call last)")
    for line in LINES:
        row = products[line]
        assert row["product_status"] == "wrong", row
        assert row["call_outcome"] == "faithfully-failed", row
        assert row["finalizable"] is False, row


def test_the_report_lists_every_producer_call_state(monkeypatch):
    """The report boundary itself, not a filter written in the test."""
    rows, _detail, _text, _products = drive(
        monkeypatch, fail=True, product="X\n", result="all good")
    report = BI.producer_report(_products)
    # A LITERAL ORACLE. Comparing the report's keys to the production constants, and
    # then iterating those same constants, makes expected and actual omit a state
    # together - the schema must be stated independently of the code that builds it.
    want_call = ["completed", "faithfully-failed", "historically-failed",
                 "missing-result", "refused", "terminated", "waiting"]
    want_product = ["correct", "missing", "not-attempted", "unpinned", "wrong"]
    assert sorted(report["call_states"]) == want_call
    assert report["call_states"]["refused"] == list(LINES)
    for empty in want_call:
        if empty != "refused":
            assert report["call_states"][empty] == [], (empty,
                                                        report["call_states"][empty])
    assert sorted(report["product_states"]) == want_product
    assert report["product_states"]["wrong"] == list(LINES)
    assert report["finalizable"] == []
