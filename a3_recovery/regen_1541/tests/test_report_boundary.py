"""The REAL report builder, and a schema oracle that is independent of it (SEQ 1552).

Two faults this file exists to prevent:

* my previous owner-list control rebuilt the selector itself and never called `main()`,
  so a regression from exact equality back to `endswith` in the real report was
  invisible - Codex proved it by replacing `main` with a fatal function while the test
  still passed;
* my schema assertions compared the report's keys to the production constants and then
  iterated those same constants, so if production dropped a required state the expected
  answer dropped with it.

The states below are therefore written out literally. Staleness here is the point: a new
state must be added deliberately, in this file, by someone who has thought about it.
"""
import io
import json
import os
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
import branch_inventory as BI                                 # noqa: E402

#: the independent oracle - spelled out, never derived from the code under test
REQUIRED_PRODUCT_STATES = ["correct", "missing", "not-attempted", "unpinned", "wrong"]
REQUIRED_CALL_STATES = ["completed", "faithfully-failed", "historically-failed",
                        "missing-result", "refused", "terminated", "waiting"]

#: one owner row and one producer row for each suffix that could collide
DETAIL = [(10, "waiting"), (11, "producer-correct/waiting"),
          (20, "missing-result"), (21, "producer-correct/missing-result"),
          (30, "refused"), (31, "producer-wrong/refused"),
          (40, "faithfully-failed"), (41, "producer-wrong/faithfully-failed"),
          (50, "terminated"), (51, "producer-not-attempted/terminated")]
PRODUCTS = {
    11: {"product_status": "correct", "call_outcome": "waiting", "finalizable": False},
    21: {"product_status": "correct", "call_outcome": "missing-result",
         "finalizable": False},
    31: {"product_status": "wrong", "call_outcome": "refused", "finalizable": False},
    41: {"product_status": "wrong", "call_outcome": "faithfully-failed",
         "finalizable": False},
    51: {"product_status": "not-attempted", "call_outcome": "terminated",
         "finalizable": False},
}


@pytest.fixture
def emitted(tmp_path, monkeypatch):
    """Run the REAL `main()` into a temporary root and return what it wrote."""
    os.makedirs(str(tmp_path / "reports"))
    monkeypatch.setattr(BI, "R", str(tmp_path))
    monkeypatch.setattr(BI, "OWNERS", {"only": ("some/owner.py", 1)})
    monkeypatch.setattr(BI, "branches", lambda: [])
    monkeypatch.setattr(BI, "classify",
                        lambda owner, upto: ({}, DETAIL, "", PRODUCTS))
    BI.main()
    return json.loads(io.open(str(tmp_path / "reports" / "branch_inventory.json"),
                              encoding="utf-8").read())["only"]


def test_the_owner_lists_hold_only_owner_rows(emitted):
    """Exact equality, proved through the emitted report rather than restated here."""
    assert emitted["waiting_lines"] == [10], emitted["waiting_lines"]
    assert emitted["missing_result_lines"] == [20], emitted["missing_result_lines"]
    assert emitted["refused_lines"] == [30], emitted["refused_lines"]
    assert emitted["faithfully_failed_lines"] == [40], emitted["faithfully_failed_lines"]
    assert emitted["terminated_lines"] == [50], emitted["terminated_lines"]


def test_the_producer_rows_appear_in_the_producer_report(emitted):
    """The same rows the owner lists must exclude are accounted for on their own axis."""
    states = emitted["producer_report"]["call_states"]
    assert states["waiting"] == [11], states
    assert states["missing-result"] == [21], states
    assert states["refused"] == [31], states
    assert states["faithfully-failed"] == [41], states
    assert states["terminated"] == [51], states
    assert emitted["producer_lines"] == [11, 21, 31, 41, 51]


def test_the_report_carries_every_required_state(emitted):
    """Schema, from the literal oracle above - not from the code that built the report."""
    report = emitted["producer_report"]
    assert sorted(report["product_states"]) == REQUIRED_PRODUCT_STATES
    assert sorted(report["call_states"]) == REQUIRED_CALL_STATES
    assert report["product_states"]["missing"] == []
    assert report["call_states"]["completed"] == []
    assert report["finalizable"] == []
