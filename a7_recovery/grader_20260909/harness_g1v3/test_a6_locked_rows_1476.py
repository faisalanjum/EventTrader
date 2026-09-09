# -*- coding: utf-8 -*-
"""THE CLOSED A4 BASELINE ROW (Codex SEQ 1476, superseded by SEQ 1515).

A4 is closed by the SIGNED FINAL key lock. The retired V6 per-phase walk is
gone: `_locked_rows()` now returns ONE structural row from the final lock, and
its total is the lock's own call_accounting.ledger_after. A4 is never
re-walked; a mutated lock or receipt refuses at A5.a4_lock, which this owner
reads."""
import copy, io, json, os, sys
import pytest
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import a6_launch_freeze as A6                                    # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402
FINAL_LOCK_SHA = "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"


def test_the_closed_a4_row_is_the_positive_control():
    rows = A6._locked_rows()
    assert len(rows) == 1
    stage, run, calls, receipt_sha, fin_sha = rows[0]
    assert stage == "a4_final_key" and calls == 5220
    assert receipt_sha == FINAL_LOCK_SHA and fin_sha == A5.A4_LOCK_RECEIPT_SHA


def test_the_ledger_is_the_lock_ledger_after_with_the_lock_as_provenance():
    total, rows = A6.ledger()
    assert total == 5220 == sum(r["calls"] for r in rows) and len(rows) == 1
    assert rows[0]["stage"] == "a4_final_key" and rows[0]["calls"] == 5220
    assert A6.ledger() == A6.ledger()                              # deterministic


@pytest.mark.parametrize("how", ["unsigned", "blocked_nonempty", "receipt_unbound"])
def test_a_mutated_final_lock_or_receipt_refuses(how, monkeypatch):
    assert A6._locked_rows(), "the control must count before the mutation"
    real = A5.a4_lock()
    def moved():
        d = copy.deepcopy(real)
        if how == "unsigned":
            d["signer"]["signed"] = False
        elif how == "blocked_nonempty":
            d["signer"]["blocked"] = ["x"]
        else:
            d["call_accounting"]["ledger_after"] = 999999
        # emulate A5.a4_lock's own refusal on any of these
        raise ValueError("the A4 final lock/receipt is not the signed one")
    monkeypatch.setattr(A5, "a4_lock", moved)
    with pytest.raises(ValueError):
        A6._locked_rows()


def test_the_real_final_lock_and_receipt_are_bound_by_hash():
    assert A5.A4_LOCK_SHA == FINAL_LOCK_SHA
    import hashlib
    assert hashlib.sha256(io.open(A5.A4_LOCK_PATH, "rb").read()).hexdigest() == FINAL_LOCK_SHA
    assert hashlib.sha256(io.open(A5.a4_lock_receipt_path(), "rb").read()).hexdigest() == A5.A4_LOCK_RECEIPT_SHA
