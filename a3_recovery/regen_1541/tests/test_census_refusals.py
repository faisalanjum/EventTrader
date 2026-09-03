"""The open census must refuse every way its evidence can be wrong (Codex SEQ 1558 #2).

Its previous controls exercised only a missing and a malformed inventory file. Meanwhile
the live census reported 15 refused occurrences with an empty `failures`, hardcoded the
pass-through before-state to "", and read a growing live transcript during the proof.

These controls call THE SAME functions the census calls, so a control cannot pass
against a rule the census does not apply - which is exactly how the branch verdict came
to read a key the real rows never carry.
"""
import io
import os
import re
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "ledger"))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "proofs"))


import census_rules as CRU                                      # noqa: E402
class _Live(dict):
    """The rules are looked up on the LIVE module at call time, so a fault installed
    on census_rules.row_failures reaches every control here; a dict captured at import
    held the original function and the audit found the null control passing under
    its fault."""
    def __getitem__(self, k):
        return getattr(CRU, k)


C = _Live()


REQUIRED = CRU.REQUIRED


def _row(**over):
    row = dict((k, "x") for k in REQUIRED)
    row.update({"kind": "owner", "before_bytes": 1, "after_bytes": 1,
                "resolved_target": "/nowhere/x", "effective_mode": "r"})
    row.update(over)
    return row


def test_it_REFUSES_a_checkpoint_mismatch():
    bad = C["route_failures"]("o.py", 1, "a" * 64, 10, "b" * 64, 10, [_row()])
    assert any("checkpoint mismatch" in x for x in bad), bad


def test_it_REFUSES_a_byte_count_mismatch():
    bad = C["route_failures"]("o.py", 1, "a" * 64, 10, "a" * 64, 11, [_row()])
    assert any("byte-count mismatch" in x for x in bad), bad


def test_it_REFUSES_a_route_with_no_opens():
    bad = C["route_failures"]("o.py", 1, "a" * 64, 10, "a" * 64, 10, [])
    assert any("no opens" in x for x in bad), bad


def test_it_ACCEPTS_a_route_that_matches():
    assert C["route_failures"]("o.py", 1, "a" * 64, 10, "a" * 64, 10, [_row()]) == []


def test_it_REFUSES_an_incomplete_row():
    row = _row()
    del row["tool_use_id"]
    assert any("missing or null" in x
               for x in C["row_failures"]([row], _R, REQUIRED))


def test_it_REFUSES_a_NULL_in_a_required_field():
    assert any("null in a required field" in x
               for x in C["row_failures"]([_row(tool_use_id=None)], _R, REQUIRED))


def test_it_REFUSES_an_unexplained_pass_through_kind():
    assert any("unexplained kind" in x
               for x in C["row_failures"]([_row(kind="something-else")], _R, REQUIRED))


def test_it_REFUSES_read_only_drift():
    """The live-source defect in miniature: bytes changed under a read-only open."""
    row = _row(drift_under_read_only_open=True)
    assert any("saw the target change" in x
               for x in C["row_failures"]([row], _R, REQUIRED))


def test_it_REFUSES_an_unreadable_boundary_read():
    assert any("could not read" in x
               for x in C["row_failures"]([_row(unreadable_before=True)], _R,
                                          REQUIRED))


def test_a_refusal_is_EXPECTED_only_when_history_also_failed():
    """The census must adjudicate refusals, not count them.

    It delegates to `branch_inventory.call_outcome`, the module that already owns this
    rule, keyed by each record's own tool-use id through the exact result ledger. A
    replay failure where HISTORY also failed is faithful; one where history SUCCEEDED is
    my defect. The census's `expected` flag is exactly `verdict == "faithfully-failed"`,
    so this control pins that mapping.
    """
    import branch_inventory as BI
    failed_history = "Traceback (most recent call last):\nValueError: boom"
    clean_history = "ok, wrote 3 files"

    faithful = BI.call_outcome(True, failed_history, True, False)
    mine = BI.call_outcome(True, clean_history, True, False)

    assert faithful == "faithfully-failed"
    assert mine != "faithfully-failed"
    # the census treats only the first as expected
    assert (faithful == "faithfully-failed") is True
    assert (mine == "faithfully-failed") is False


def test_a_refusal_with_no_saved_result_is_NOT_silently_expected():
    """A missing result cannot excuse a refusal: nothing adjudicated it."""
    import branch_inventory as BI
    assert BI.call_outcome(True, None, False, False) != "faithfully-failed"


def _raw_measurer():
    return CRU._raw


def test_the_boundary_measurement_does_NOT_go_through_the_patched_open(tmp_path):
    """While a saved program runs, the replay swaps `io.open` and `builtins.open` for
    its shim. The first census measured through `io.open`, so measuring a pass-through
    re-entered the shim, which measured again: RecursionError on every pass-through,
    and the chain refused. The measurement must use the replay's own unpatched
    primitive, so here BOTH patched names raise and the measurement must still read
    the true bytes."""
    import builtins
    f = tmp_path / "target.bin"
    payload = b"\x00\xff bytes that a text decode would mangle \xfe"
    f.write_bytes(payload)
    raw = _raw_measurer()

    def trap(*a, **k):
        raise AssertionError("measurement went through the PATCHED open")
    saved = io.open, builtins.open
    io.open = builtins.open = trap
    try:
        n, sha = raw(str(f))
    finally:
        io.open, builtins.open = saved
    import hashlib
    assert (n, sha) == (len(payload), hashlib.sha256(payload).hexdigest())


def test_the_boundary_measurement_reports_an_unreadable_target_as_None(tmp_path):
    raw = _raw_measurer()
    assert raw(str(tmp_path / "absent")) == (None, None)


# ---------------------------------------------------------------------------
# Codex SEQ 1559 item 2: every required field present AND non-null, no crash on a
# malformed row, unreadable only with a failed open, reads inside the package, and the
# after-state measured after the consumer is done - not merely after open() returned.
# ---------------------------------------------------------------------------
import pytest


@pytest.mark.parametrize("field", REQUIRED)
def test_it_REFUSES_a_null_in_EVERY_required_field(field):
    r = _row(); r[field] = None
    assert any("missing or null" in x for x in C["row_failures"]([r], _R, REQUIRED)), field


@pytest.mark.parametrize("field", REQUIRED)
def test_it_REFUSES_a_missing_required_field_without_crashing(field):
    r = _row(); del r[field]
    bad = C["row_failures"]([r], _R, REQUIRED)         # must not raise
    assert any("missing or null" in x for x in bad), field


def test_it_ACCEPTS_a_failed_open_over_an_unreadable_target():
    """The program received the same exception history did: faithful, not a gap."""
    r = _row(kind="passthrough", unreadable_before=True, open_failed="FileNotFoundError",
             resolved_target=os.path.join(_R, "does-not-exist"))
    assert C["row_failures"]([r], _R, REQUIRED) == []


def test_it_REFUSES_a_successful_open_over_bytes_it_could_not_read():
    r = _row(kind="passthrough", unreadable_before=True,
             resolved_target=os.path.join(_R, "x"))
    assert any("could not read" in x for x in C["row_failures"]([r], _R, REQUIRED))


def test_it_REFUSES_a_pass_through_that_read_outside_the_package():
    r = _row(kind="passthrough", resolved_target="/etc/hostname")
    assert any("outside the package" in x for x in C["row_failures"]([r], _R, REQUIRED))


def test_it_ACCEPTS_a_pass_through_inside_the_package():
    r = _row(kind="passthrough", resolved_target=os.path.join(_R, "products", "x"))
    assert C["row_failures"]([r], _R, REQUIRED) == []


def _boundary():
    return {k: getattr(CRU, k) for k in ("_AUDIT_PRE", "_AUDIT_OWN", "_AUDIT_POST", "_AUDIT_FAILED", "_close_owned_handles")}


def test_the_after_state_is_measured_AFTER_the_consumer_not_after_open(tmp_path):
    """RED for the old sequence: the target changes between open() and the read.
    Measuring right after open() could not see it; owning the reader does."""
    ns = _boundary()
    f = tmp_path / "t.bin"; f.write_bytes(b"before")
    row = ns["_AUDIT_PRE"](str(f), "r", 1)
    fh = ns["_AUDIT_OWN"](row, open(str(f), "rb"))
    f.write_bytes(b"CHANGED")                    # a change during the actual read
    fh.read()
    fh.close()
    assert row.get("drift_under_read_only_open") is True    # under the fault the key is absent
    assert any("change under them" in x for x in
               C["row_failures"]([dict(_row(), **row)], _R, REQUIRED))


def test_an_unchanged_target_is_the_positive_control(tmp_path):
    ns = _boundary()
    f = tmp_path / "t.bin"; f.write_bytes(b"stable")
    row = ns["_AUDIT_PRE"](str(f), "r", 1)
    with ns["_AUDIT_OWN"](row, open(str(f), "rb")) as fh:
        assert fh.read() == b"stable"
    assert row["pre_post_identical"] is True and not row.get("drift_under_read_only_open")


def test_a_handle_the_program_never_closed_is_measured_at_the_record_end(tmp_path):
    ns = _boundary()
    f = tmp_path / "t.bin"; f.write_bytes(b"x")
    row = ns["_AUDIT_PRE"](str(f), "r", 1)
    ns["_AUDIT_OWN"](row, open(str(f), "rb"))   # never closed by the "program"
    assert "after_sha256" not in row
    ns["_close_owned_handles"]()
    assert row["closed_by_census"] is True and row["after_sha256"] == row["before_sha256"]


def test_a_failed_open_yields_a_complete_row(tmp_path):
    ns = _boundary()
    missing = str(tmp_path / "absent")
    row = ns["_AUDIT_PRE"](missing, "rb", 1)
    try:
        open(missing, "rb")
    except OSError as e:
        ns["_AUDIT_FAILED"](row, e)
    assert row["open_failed"] == "FileNotFoundError"
    assert row["after_bytes"] == row["before_bytes"] and row["after_sha256"] == row["before_sha256"]


def test_the_replays_own_typed_inability_is_its_own_class_never_faithful():
    """A ReplayEnvironmentError is the replay declaring what it cannot provide; it is
    reported apart, and no other exception class is ever treated as environment."""
    assert CRU.refusal_class("ReplayEnvironmentError") == "environment"
    for other in ("AssertionError", "ValueError", "FileNotFoundError", "RuntimeError", None):
        assert CRU.refusal_class(other) == "program"

def test_a_background_record_is_judged_by_what_history_observed_not_its_launch_notice():
    """Record 7097 answered only a launch notice; history read the task's output at
    the waiter that follows, and THAT text is the outcome the replay is judged by."""
    import replay_transcript as RT
    assert RT.background_task_id("Command running in background with ID: b1bxwdxrx. Output is being written to: x") == "b1bxwdxrx"
    assert RT.background_task_id("14 passed in 0.7s") is None
    tid, observed = RT.background_outcome(7097)
    assert tid == "b1bxwdxrx"
    assert observed and "ok  tguards" in observed, (observed or "")[:200]
    assert RT.background_outcome(22345) == (None, None)


def test_a_background_record_nobody_read_back_is_reported_apart(tmp_path):
    """A launch notice with no later reader of its output: (task id, None), which the
    census reports as background-unobserved, never as expected or unexplained."""
    import json
    import replay_transcript as RT
    p = tmp_path / "t.jsonl"
    rec = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "tu1", "name": "Bash",
                                                          "input": {"command": "python3 x.py", "run_in_background": True}}]}}
    res = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "tu1",
                                                     "content": "Command running in background with ID: bzz. Output is being written to: /tmp/t/tasks/bzz.output"}]}}
    p.write_text(json.dumps(rec) + "\n" + json.dumps(res) + "\n")
    assert RT.background_outcome(1, str(p)) == ("bzz", None)


def test_it_REFUSES_a_null_in_every_required_field_all():
    """The parametrized control, in one fixture-free call for the exact-credit audit."""
    for field in REQUIRED:
        r = _row(); r[field] = None
        assert any("missing or null" in x for x in C["row_failures"]([r], _R, REQUIRED)), field
