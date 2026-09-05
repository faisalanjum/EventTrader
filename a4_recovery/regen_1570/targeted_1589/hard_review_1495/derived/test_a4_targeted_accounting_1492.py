# -*- coding: utf-8 -*-
"""CALL ACCOUNTING FOR THE TARGETED A4 RUN, AT ITS ONE OWNER (Codex SEQ 1492 A).

The completed ledger must include /tmp/a4_targeted_run_1491 and its child
exactly once, proved through the targeted lifecycle's own context and exact
receipt / finalization / official-state / raw / proved-byte checks:
primary 11 + child 1 = 12, prior 5168 + 12 = 5180. Test first.

Every refusal is proved on a same-named disposable copy of the run; the run
itself is never written.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402

RUN = "/tmp/a4_targeted_run_1491"
POINTER = os.path.join(K.EVIDENCE, "targeted_dir.txt")
BUDGET_1488 = "/tmp/a7_budget_receipt_1488.json"
_run = pytest.mark.skipif(not os.path.isdir(RUN), reason="the targeted run is absent")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _clean_ledger():
    """The ledger from a CLEAN interpreter (the one owner, no test imports)."""
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB'); import a6_launch_freeze as A6; "
         "t, rows = A6.ledger(); print(json.dumps([t, rows]))" % _HERE],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-600:]
    return json.loads(out.stdout)


# ------------------------------------------------ the row at the one owner
@_run
def test_the_ledger_counts_the_targeted_run_and_its_child_exactly_once():
    total, rows = _clean_ledger()
    stages = [r["stage"] for r in rows]
    prim = [r for r in rows if r["stage"] == "targeted_key_review_primary"]
    child = [r for r in rows if r["stage"] == "targeted_key_review_retry"]
    assert len(prim) == 1 and len(child) == 1, stages
    assert prim[0]["run_dir"] == RUN and child[0]["run_dir"] == RUN + "/retry"
    assert prim[0]["calls"] == 11 and child[0]["calls"] == 1
    assert prim[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert prim[0]["finalization_sha256"] == _sha(RUN + "/finalization.json")
    assert child[0]["receipt_sha256"] == _sha(RUN + "/retry/receipt.json")
    assert child[0]["finalization_sha256"] == _sha(RUN + "/retry/finalization.json")
    # the historical provenance is byte-for-byte what the 1488 receipt recorded
    before = _load(BUDGET_1488)
    others = [r for r in rows if not r["stage"].startswith("targeted_key_review")]
    assert others == before["completed_rows"]
    assert sum(r["calls"] for r in others) == before["completed_before"] == 5168
    assert total == before["completed_before"] + 12 == 5180
    # asking twice is the same answer: nothing is counted on each read
    assert _clean_ledger() == [total, rows]


@_run
def test_the_pointer_binds_the_exact_run():
    assert io.open(POINTER, encoding="utf-8").read().strip() == RUN


@_run
def test_proved_spend_reports_primary_and_child_from_their_own_proofs():
    got = T.proved_spend(RUN)
    assert [(g["run_dir"], g["attempt"], g["calls"]) for g in got] == \
        [(RUN, 1, 11), (RUN + "/retry", 2, 1)]
    assert got[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert got[1]["finalization_sha256"] == _sha(RUN + "/retry/finalization.json")


# ------------------------------------------------ refusals on a same-named copy
@pytest.fixture
def copy(tmp_path, monkeypatch):
    """A same-named disposable copy, BOUND before any test mutates it - the
    order reality has: the binding freezes the accepted run, tampering comes
    later. The real binding stays untouched."""
    dst = str(tmp_path / os.path.basename(RUN))    # the receipt binds its run_id
    shutil.copytree(RUN, dst)
    doc = {"schema": T.BINDING_SCHEMA, "run_dir": dst,
           "attempts": [T._measured_attempt(dst, 1), T._measured_attempt(dst + "/retry", 2)]}
    bound = str(tmp_path / "targeted_binding.json")
    io.open(bound, "w").write(json.dumps(doc, indent=1))
    monkeypatch.setattr(T, "BINDING", bound)
    return dst


def _mutations():
    def raw_byte(d):
        p = os.path.join(d, "raw", "wf_1b219d0e-f6f.000.raw.json")
        io.open(p, "a", encoding="utf-8").write(" ")

    def proved_missing(d):
        os.remove(os.path.join(d, "raw", "0000006201-26-000031_001.attempt1.proved.json"))

    def raw_missing(d):
        os.remove(os.path.join(d, "raw", "wf_4d457126-2c2.000.raw.json"))

    def foreign_state(d):
        rec = _load(os.path.join(d, "receipt.json"))
        p = os.path.join(d, "elsewhere.json"); shutil.copy(rec["states"][0], p)
        rec["states"][0] = p
        io.open(os.path.join(d, "receipt.json"), "w").write(json.dumps(rec, indent=1))

    def tampered_receipt(d):
        rec = _load(os.path.join(d, "receipt.json"))
        rec["rules_sha256"] = "0" * 64
        io.open(os.path.join(d, "receipt.json"), "w").write(json.dumps(rec, indent=1))

    def tampered_finalization(d):
        fin = _load(os.path.join(d, "finalization.json"))
        fin["receipt_sha256"] = "0" * 64
        io.open(os.path.join(d, "finalization.json"), "w").write(json.dumps(fin, indent=1))

    def finalization_missing(d):
        os.remove(os.path.join(d, "finalization.json"))

    def duplicate_state(d):
        rec = _load(os.path.join(d, "receipt.json"))
        rec["states"].append(rec["states"][0])
        io.open(os.path.join(d, "receipt.json"), "w").write(json.dumps(rec, indent=1))

    def child_raw_byte(d):
        p = os.path.join(d, "retry", "raw", "wf_cbc7405a-c2d.000.raw.json")
        io.open(p, "a", encoding="utf-8").write(" ")

    def child_proved_byte(d):
        p = os.path.join(d, "retry", "raw", "0000940944-26-000009_072.attempt2.proved.json")
        io.open(p, "a", encoding="utf-8").write(" ")
    return [("raw_byte", raw_byte), ("proved_missing", proved_missing), ("raw_missing", raw_missing),
            ("foreign_state", foreign_state), ("tampered_receipt", tampered_receipt),
            ("tampered_finalization", tampered_finalization), ("finalization_missing", finalization_missing),
            ("duplicate_state", duplicate_state), ("child_raw_byte", child_raw_byte),
            ("child_proved_byte", child_proved_byte)]


@_run
def test_the_unaltered_copy_is_the_lawful_control(copy):
    got = T.proved_spend(copy)
    assert [(g["attempt"], g["calls"]) for g in got] == [(1, 11), (2, 1)]


@_run
@pytest.mark.parametrize("name,mutate", _mutations(), ids=[m[0] for m in _mutations()])
def test_every_missing_foreign_or_tampered_byte_refuses_the_whole_spend(copy, name, mutate):
    mutate(copy)
    with pytest.raises(ValueError):
        T.proved_spend(copy)


@_run
def test_the_child_directory_alone_is_not_a_countable_run():
    with pytest.raises(ValueError):
        T.proved_spend(RUN + "/retry")


def _ledger_over(copy, binding):
    """A6.ledger() in a CLEAN process with BOTH owners rebound to the same
    disposable evidence: the A6 pointer -> the copied run, and the targeted
    owner's BINDING -> the copy's own pre-mutation binding. -> stdout"""
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB')\n"
         "import a6_launch_freeze as A6, build_kfields_key_targeted as T\n"
         "real = A6._read_ptr\n"
         "A6._read_ptr = lambda name: %r if name == 'targeted_dir.txt' else real(name)\n"
         "T.BINDING = %r\n"
         "try:\n"
         "    total, rows = A6.ledger()\n"
         "    print('ACCEPTED', total, json.dumps([(r['stage'], r['calls']) for r in rows if r['stage'].startswith('targeted_key_review')]))\n"
         "except ValueError as exc:\n"
         "    print('REFUSED', str(exc))"
         % (_HERE, copy, binding)],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-600:]
    return out.stdout.strip()


@_run
def test_the_ledger_counts_a_bound_copy_and_refuses_it_after_one_raw_byte(copy):
    """Codex SEQ 1494: the positive control first, then the exact refusal -
    the tampered byte must reach the bound-identity check, not a folder
    mismatch and not a generic refusal."""
    binding = T.BINDING                              # the copy's own binding (fixture)
    positive = _ledger_over(copy, binding)
    assert positive == "ACCEPTED 5180 " + json.dumps(
        [["targeted_key_review_primary", 11], ["targeted_key_review_retry", 1]]), positive
    _mutations()[0][1](copy)                         # one raw byte
    negative = _ledger_over(copy, binding)
    assert negative.startswith("REFUSED "), negative
    assert "is not the bound identity" in negative, negative
    assert "not the bound targeted run" not in negative, negative


# ------------------------------------------ the immutable evidence binding (1493)
BINDING = os.path.join(K.EVIDENCE, "targeted_binding.json")


def _finalization_mutations():
    def primary_retry_dropped(d):
        fin = _load(os.path.join(d, "finalization.json")); fin["retry"] = []
        io.open(os.path.join(d, "finalization.json"), "w").write(json.dumps(fin, indent=1))

    def child_scheduled_99(d):
        p = os.path.join(d, "retry", "finalization.json"); fin = _load(p); fin["ledger"]["scheduled"] = 99
        io.open(p, "w").write(json.dumps(fin, indent=1))

    def child_outcomes_empty(d):
        p = os.path.join(d, "retry", "finalization.json"); fin = _load(p); fin["outcomes"] = []
        io.open(p, "w").write(json.dumps(fin, indent=1))

    def primary_outcome_flipped(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p)
        fin["outcomes"] = [[k, "valid", ""] if o == "invalid_response" else [k, o, w] for k, o, w in fin["outcomes"]]
        io.open(p, "w").write(json.dumps(fin, indent=1))

    def primary_ledger_valid_11(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p); fin["ledger"]["valid"] = 11; fin["ledger"]["invalid_response"] = 0
        io.open(p, "w").write(json.dumps(fin, indent=1))

    def child_finalization_missing(d):
        os.remove(os.path.join(d, "retry", "finalization.json"))

    def bound_child_missing(d):
        shutil.rmtree(os.path.join(d, "retry"))

    def extra_raw_file(d):
        io.open(os.path.join(d, "raw", "zz_extra.raw.json"), "w").write("{}")
    return [("primary_retry_dropped", primary_retry_dropped), ("child_scheduled_99", child_scheduled_99),
            ("child_outcomes_empty", child_outcomes_empty), ("primary_outcome_flipped", primary_outcome_flipped),
            ("primary_ledger_valid_11", primary_ledger_valid_11), ("child_finalization_missing", child_finalization_missing),
            ("bound_child_missing", bound_child_missing), ("extra_raw_file", extra_raw_file)]


@_run
def test_a_copy_of_the_run_is_not_the_bound_run(tmp_path):
    dst = str(tmp_path / os.path.basename(RUN)); shutil.copytree(RUN, dst)
    with pytest.raises(ValueError) as exc:               # the REAL binding names the real directory
        T.proved_spend(dst)
    assert "not the bound targeted run" in str(exc.value)


@_run
def test_the_binding_freezes_the_accepted_identities_once():
    b = _load(BINDING)
    assert b["run_dir"] == RUN
    att = {a["attempt"]: a for a in b["attempts"]}
    assert sorted(att) == [1, 2]
    assert att[1]["dir"] == RUN and att[2]["dir"] == RUN + "/retry"
    for a in att.values():
        assert a["receipt_sha256"] == _sha(os.path.join(a["dir"], "receipt.json"))
        assert a["finalization_sha256"] == _sha(os.path.join(a["dir"], "finalization.json"))
        raw = os.path.join(a["dir"], "raw")
        assert a["raw_files"] == {f: _sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw))}
    assert T.BINDING == BINDING
    with pytest.raises((ValueError, OSError)):        # write-once
        T.write_binding(RUN)


@_run
@pytest.mark.parametrize("name,mutate", _finalization_mutations(), ids=[m[0] for m in _finalization_mutations()])
def test_every_meaningful_finalization_change_refuses_the_whole_spend(copy, name, mutate):
    mutate(copy)
    with pytest.raises(ValueError):
        T.proved_spend(copy)


@_run
def test_an_unexpected_child_that_the_binding_does_not_own_refuses(copy, tmp_path, monkeypatch):
    b = _load(T.BINDING)                                # the copy's own binding
    b["attempts"] = [a for a in b["attempts"] if a["attempt"] == 1]     # a binding with no child
    unbound = str(tmp_path / "binding_no_child.json")
    io.open(unbound, "w").write(json.dumps(b, indent=1))
    monkeypatch.setattr(T, "BINDING", unbound)
    with pytest.raises(ValueError):
        T.proved_spend(copy)                            # the copy still carries retry/


@_run
def test_the_child_is_owed_by_the_binding_not_by_stored_bytes(copy):
    _finalization_mutations()[0][1](copy)               # retry dropped from the primary finalization
    with pytest.raises(ValueError):
        T.proved_spend(copy)                            # the bound child is still owed


@_run
def test_duplicate_reads_count_the_exact_twelve_once():
    a = T.proved_spend(RUN); b = T.proved_spend(RUN)
    assert a == b and [r["calls"] for r in a] == [11, 1]
    assert _clean_ledger()[0] == 5180
