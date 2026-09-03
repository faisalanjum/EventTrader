"""The call gate, proved with a CORRECT product (Codex SEQ 1551).

Every earlier non-completed control wrote its own wrong bytes, so `finalizable=False`
only proved the PRODUCT gate. Here the real replay produces the exact pinned product and
ONLY the saved call evidence (or a post-write exception) varies, so each row proves the
CALL gate on its own.

The combination that was fail-open: local replay succeeds, the saved result says history
failed, the product is correct - and the report called it `completed` and finalizable.
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
FAILURE = "Traceback (most recent call last)\nAssertionError: x"


def producers_of():
    with contextlib.redirect_stdout(io.StringIO()):
        _recs, producers = CR.route_records(AUDIT, CR.tree_origin("bench_1306")[0], UPTO)
    return producers


def outstanding_ledger():
    L = RT.ResultLedger()
    L.rows = RT.result_ledger().rows
    for line in LINES:
        rec = RT.lines([line])[line]
        for b in ((rec.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
                L.uses[b["id"]] = line          # registered use, no result ever
    return L


def drive(monkeypatch, *, result="ok", present=True, raise_after=False,
          outstanding=False, unpin=False):
    """Real replay writes the REAL product; only the call evidence varies."""
    producers = producers_of()
    real = RT.apply_saved_edits

    def act(text, records, basename, prepare=None, side=None, result_=None):
        out = real(text, records, basename, prepare, side, result_)
        if raise_after and list(records)[0] in producers:
            raise RuntimeError("after the real product was written")
        return out

    monkeypatch.setattr(RT, "apply_saved_edits", act)
    monkeypatch.setattr(RT, "saved_result", lambda line, path=None: result)
    monkeypatch.setattr(RT, "result_present", lambda line, path=None: present)
    if outstanding:
        L = outstanding_ledger()
        monkeypatch.setattr(RT, "result_ledger", lambda *a, **k: L)
    if unpin:
        monkeypatch.setattr(BI, "expected_products", dict)
    with contextlib.redirect_stdout(io.StringIO()):
        return BI.classify(AUDIT, UPTO)


def only(products, key):
    return sorted({row[key] for row in products.values()})


def test_correct_product_and_a_completed_call_finalizes(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["completed"]
    assert only(products, "finalizable") == [True]


def test_correct_product_but_HISTORY_FAILED_never_finalizes(monkeypatch):
    """The fail-open combination: my replay went through, history's call did not."""
    _r, _d, _t, products = drive(monkeypatch, result=FAILURE)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["historically-failed"]
    assert only(products, "finalizable") == [False]


def test_correct_product_with_a_FAITHFUL_failure_never_finalizes(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch, result=FAILURE, raise_after=True)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["faithfully-failed"]
    assert only(products, "finalizable") == [False]


def test_correct_product_with_a_REFUSAL_never_finalizes(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch, result="all fine", raise_after=True)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["refused"]
    assert only(products, "finalizable") == [False]


def test_correct_product_that_is_still_OUTSTANDING_never_finalizes(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch, result=None, present=False,
                                 outstanding=True)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["waiting"]
    assert only(products, "finalizable") == [False]


def test_correct_product_with_no_saved_result_never_finalizes(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch, result=None, present=False)
    assert only(products, "product_status") == ["correct"]
    assert only(products, "call_outcome") == ["missing-result"]
    assert only(products, "finalizable") == [False]


def test_a_present_product_with_NO_PIN_reports_unpinned_and_fails_closed(monkeypatch):
    _r, _d, _t, products = drive(monkeypatch, unpin=True)
    assert only(products, "product_status") == ["unpinned"]
    assert only(products, "finalizable") == [False]


def test_each_non_completed_call_state_is_listed_exactly(monkeypatch):
    """Through the real report boundary, one populated state at a time."""
    for kwargs, state in (
            ({"result": FAILURE}, "historically-failed"),
            ({"result": FAILURE, "raise_after": True}, "faithfully-failed"),
            ({"result": "all fine", "raise_after": True}, "refused"),
            ({"result": None, "present": False, "outstanding": True}, "waiting"),
            ({"result": None, "present": False}, "missing-result")):
        mp = monkeypatch
        with mp.context() as m:
            _r, _d, _t, products = drive(m, **kwargs)
        report = BI.producer_report(products)
        assert report["call_states"][state] == list(LINES), (state, report)
        for other in BI.CALL_STATES:
            if other != state:
                assert report["call_states"][other] == [], (state, other, report)
        assert report["finalizable"] == [], state


def test_the_owner_lists_never_include_producer_rows(monkeypatch):
    """Owner accounting stays exact and separate; producers have their own report."""
    _r, detail, _t, products = drive(monkeypatch, result=None, present=False)
    owner_missing = [n for n, k in detail if k == "missing-result"]
    assert not set(owner_missing) & set(products), owner_missing


# ---------------------------------------------------------------------------
# Codex SEQ 1559 item 2: a replay failure is faithful only when it is THE SAME
# exception history saved - class and full message - never a generic failure keyword.
# Added at the one existing owner of the call rule.
# ---------------------------------------------------------------------------
_SAVED = ("Exit code 1\nTraceback (most recent call last):\n"
          "  File \"<stdin>\", line 11, in <module>\n"
          "TypeError: rep() missing 1 required positional argument: 'why'\n"
          "Shell cwd was reset to /home/faisal/EventMarketDB")


def test_the_EXACT_historical_exception_is_faithfully_failed():
    import branch_inventory as BI
    assert BI.call_outcome(True, _SAVED, True, False,
                           replay_error=("TypeError", "rep() missing 1 required "
                                         "positional argument: 'why'")) == "faithfully-failed"


def test_a_WRONG_exception_over_a_saved_failure_is_refused():
    import branch_inventory as BI
    assert BI.call_outcome(True, _SAVED, True, False,
                           replay_error=("ValueError", "unrelated failure")) == "refused"
    assert BI.call_outcome(True, _SAVED, True, False,
                           replay_error=("TypeError", "a different message")) == "refused"


def test_codex_generic_keyword_falsifier_is_refused():
    import branch_inventory as BI
    assert BI.call_outcome(True, "Traceback: ValueError: unrelated failure", True, False,
                           replay_error=("AssertionError", "x")) == "refused"


def test_a_message_with_a_blank_line_inside_it_is_bound_whole():
    """Live case (record 26146): the assertion message spans a blank line. A block cut
    at the first blank line made the exact replay look unexplained."""
    import branch_inventory as BI
    saved = ("Traceback (most recent call last):\n  File \"x\", line 1, in <module>\n"
             "AssertionError: first line\n\nthird line\n1 failed in 0.1s\nShell cwd was reset")
    assert BI.call_outcome(True, saved, True, False,
                           replay_error=("AssertionError", "first line\n\nthird line\n\n")) == "faithfully-failed"
    assert BI.call_outcome(True, saved, True, False,
                           replay_error=("AssertionError", "first line")) == "faithfully-failed"
    assert BI.call_outcome(True, saved, True, False,
                           replay_error=("AssertionError", "first line\n\nthird lines")) == "refused"
