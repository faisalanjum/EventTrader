# -*- coding: utf-8 -*-
"""CALL ACCOUNTING FOR THE 22-CALL DOUBLE-BLIND HARD REVIEW (Codex SEQ 1496 item 1).

The completed ledger must include /tmp/a4_hard_review_run_1495 exactly once,
proved through the hard-review lifecycle's own context: the immutable binding
(receipt, finalization, every raw/proved byte, canonical raw tree), the
receipt, the finalization that binds it, every official state, every stored
byte, every RE-DERIVED outcome, the allowed identities, no child, and the
call count: prior 5180 + 22 = 5202. Test first.

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

import build_kfields_final as F                                  # noqa: E402
import build_kfields_hard_review_targeted as HRT                 # noqa: E402
import build_kfields_key as K                                    # noqa: E402

RUN = "/tmp/a4_hard_review_run_1495"
POINTER = os.path.join(K.EVIDENCE, "hard_review_targeted_dir.txt")
BUDGET_1493 = "/tmp/a7_budget_receipt_1493.json"
_run = pytest.mark.skipif(not os.path.isdir(RUN), reason="the hard-review run is absent")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _dump(p, doc):
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))


def _raw_names(d):
    """(raw file, proved file) of the FIRST recorded state, by the run's own names."""
    rec = _load(os.path.join(d, "receipt.json"))
    run_id = os.path.splitext(os.path.basename(rec["states"][0]))[0]
    label = K._state_label(_load(rec["states"][0]))
    return (os.path.join(d, "raw", "%s.000.raw.json" % run_id),
            os.path.join(d, "raw", "%s.attempt1.proved.json" % label.replace("/", "_")))


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
def test_the_ledger_counts_the_hard_review_run_exactly_once():
    total, rows = _clean_ledger()
    stages = [r["stage"] for r in rows]
    prim = [r for r in rows if r["stage"] == "hard_review_targeted_primary"]
    assert len(prim) == 1, stages
    assert "hard_review_targeted_retry" not in stages          # no child exists
    assert prim[0]["run_dir"] == RUN and prim[0]["calls"] == 22
    assert prim[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert prim[0]["finalization_sha256"] == _sha(RUN + "/finalization.json")
    # the CANONICAL raw-tree owner, never a shell checksum (Codex SEQ 1496)
    assert prim[0]["raw_tree"] == F.raw_tree(RUN)["sha256"]
    # the history the 1493 receipt recorded is byte-for-byte beside it
    before = _load(BUDGET_1493)
    later = ("hard_review_targeted", "final_targeted")   # stages accepted after this one
    others = [r for r in rows if not r["stage"].startswith(later)]
    assert others == before["completed_rows"]
    assert sum(r["calls"] for r in others) == before["completed_before"] == 5180
    since = sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted"))
    assert total == 5180 + 22 + since == sum(r["calls"] for r in rows)
    # asking twice is the same answer: nothing is counted on each read
    assert _clean_ledger() == [total, rows]


@_run
def test_the_pointer_binds_the_exact_run():
    assert io.open(POINTER, encoding="utf-8").read().strip() == RUN


@_run
def test_proved_spend_reports_the_primary_from_its_own_proofs():
    got = HRT.proved_spend(RUN)
    assert [(g["run_dir"], g["attempt"], g["calls"], g["raw_files"]) for g in got] == \
        [(RUN, 1, 22, 44)]
    assert got[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert got[0]["finalization_sha256"] == _sha(RUN + "/finalization.json")
    assert got[0]["raw_tree"] == F.raw_tree(RUN)["sha256"]
    assert HRT.proved_spend(RUN) == got                    # repeated reads: the same 22, once


# ------------------------------------------ the immutable evidence binding
@_run
def test_the_binding_freezes_the_accepted_identities_once():
    b = _load(HRT.BINDING)
    assert b["schema"] == HRT.BINDING_SCHEMA and b["run_dir"] == RUN
    att = {a["attempt"]: a for a in b["attempts"]}
    assert sorted(att) == [1] and att[1]["dir"] == RUN
    assert att[1]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert att[1]["finalization_sha256"] == _sha(RUN + "/finalization.json")
    raw = os.path.join(RUN, "raw")
    assert att[1]["raw_files"] == {f: _sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw))}
    assert att[1]["raw_tree"] == dict(F.raw_tree(RUN)) and att[1]["raw_tree"]["files"] == 44
    with pytest.raises((ValueError, OSError)):              # write-once
        HRT.write_binding(RUN)


@_run
def test_a_copy_of_the_run_is_not_the_bound_run(tmp_path):
    dst = str(tmp_path / os.path.basename(RUN)); shutil.copytree(RUN, dst)
    with pytest.raises(ValueError) as exc:                  # the REAL binding names the real directory
        HRT.proved_spend(dst)
    assert "not the bound hard-review run" in str(exc.value)


# ------------------------------------------------ refusals on a same-named copy
@pytest.fixture
def copy(tmp_path, monkeypatch):
    """A same-named disposable copy, BOUND before any test mutates it. The
    real binding stays untouched."""
    dst = str(tmp_path / os.path.basename(RUN))    # the receipt binds its run_id
    shutil.copytree(RUN, dst)
    doc = {"schema": HRT.BINDING_SCHEMA, "run_dir": dst,
           "attempts": [HRT._measured_attempt(dst, 1)]}
    bound = str(tmp_path / "hard_review_targeted_binding.json")
    _dump(bound, doc)
    monkeypatch.setattr(HRT, "BINDING", bound)
    return dst


def _mutations():
    def raw_byte(d):
        io.open(_raw_names(d)[0], "a", encoding="utf-8").write(" ")

    def proved_byte(d):
        io.open(_raw_names(d)[1], "a", encoding="utf-8").write(" ")

    def raw_missing(d):
        os.remove(_raw_names(d)[0])

    def proved_missing(d):
        os.remove(_raw_names(d)[1])

    def extra_file(d):
        io.open(os.path.join(d, "raw", "zz_extra.raw.json"), "w").write("{}")

    def swapped_files(d):
        raw = os.path.join(d, "raw")
        names = sorted(n for n in os.listdir(raw) if n.endswith(".raw.json"))[:2]
        a, b = (os.path.join(raw, n) for n in names)
        ta, tb = io.open(a, encoding="utf-8").read(), io.open(b, encoding="utf-8").read()
        io.open(a, "w", encoding="utf-8").write(tb); io.open(b, "w", encoding="utf-8").write(ta)

    def receipt_allowed_swapped(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        rec["allowed"][0], rec["allowed"][1] = rec["allowed"][1], rec["allowed"][0]; _dump(p, rec)

    def receipt_prompt_tampered(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        rec["prompts"][rec["allowed"][0]] = "0" * 64; _dump(p, rec)

    def receipt_attempt_2(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p); rec["attempt"] = 2; _dump(p, rec)

    def foreign_state(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        here = os.path.join(d, "elsewhere.json"); shutil.copy(rec["states"][0], here)
        rec["states"][0] = here; _dump(p, rec)

    def duplicate_state(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        rec["states"].append(rec["states"][0]); _dump(p, rec)

    def state_dropped(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p); rec["states"].pop(); _dump(p, rec)

    def finalization_receipt_sha(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p); fin["receipt_sha256"] = "0" * 64; _dump(p, fin)

    def finalization_outcome_flipped(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p)
        fin["outcomes"][0][1] = "invalid_response"; _dump(p, fin)

    def finalization_ledger_only(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p)
        fin["ledger"]["valid"] = 21; fin["ledger"]["invalid_response"] = 1; _dump(p, fin)

    def finalization_retry_invented(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p)
        fin["retry"] = [fin["outcomes"][0][0]]; _dump(p, fin)

    def finalization_incomplete(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p); fin["primary_complete"] = False; _dump(p, fin)

    def finalization_missing(d):
        os.remove(os.path.join(d, "finalization.json"))

    def unexpected_child(d):
        os.makedirs(os.path.join(d, "retry")); io.open(os.path.join(d, "retry", "receipt.json"), "w").write("{}")
    return [("raw_byte", raw_byte), ("proved_byte", proved_byte), ("raw_missing", raw_missing),
            ("proved_missing", proved_missing), ("extra_file", extra_file), ("swapped_files", swapped_files),
            ("receipt_allowed_swapped", receipt_allowed_swapped), ("receipt_prompt_tampered", receipt_prompt_tampered),
            ("receipt_attempt_2", receipt_attempt_2), ("foreign_state", foreign_state),
            ("duplicate_state", duplicate_state), ("state_dropped", state_dropped),
            ("finalization_receipt_sha", finalization_receipt_sha),
            ("finalization_outcome_flipped", finalization_outcome_flipped),
            ("finalization_ledger_only", finalization_ledger_only),
            ("finalization_retry_invented", finalization_retry_invented),
            ("finalization_incomplete", finalization_incomplete), ("finalization_missing", finalization_missing),
            ("unexpected_child", unexpected_child)]


@_run
def test_the_unaltered_copy_is_the_lawful_control(copy):
    got = HRT.proved_spend(copy)
    assert [(g["attempt"], g["calls"], g["raw_files"]) for g in got] == [(1, 22, 44)]


@_run
@pytest.mark.parametrize("name,mutate", _mutations(), ids=[m[0] for m in _mutations()])
def test_every_mutation_refuses_the_whole_row(copy, name, mutate):
    mutate(copy)
    with pytest.raises(ValueError):
        HRT.proved_spend(copy)


@_run
def test_a_finalization_edit_alone_cannot_pass_a_rebuilt_binding(copy, tmp_path, monkeypatch):
    """Rebinding AFTER a finalization edit still refuses: the stored outcome
    is re-derived from the official states, never read (the count is not a
    stored total)."""
    _mutations()[14][1](copy)                                # ledger numbers only
    doc = {"schema": HRT.BINDING_SCHEMA, "run_dir": copy,
           "attempts": [HRT._measured_attempt(copy, 1)]}
    rebound = str(tmp_path / "rebound.json"); _dump(rebound, doc)
    monkeypatch.setattr(HRT, "BINDING", rebound)
    with pytest.raises(ValueError) as exc:
        HRT.proved_spend(copy)
    assert "re-derived count" in str(exc.value)


def _ledger_over(copy, binding):
    """A6.ledger() in a CLEAN process with BOTH owners rebound to the same
    disposable evidence: the A6 pointer -> the copied run, and the hard-review
    owner's BINDING -> the copy's own pre-mutation binding. -> stdout"""
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB')\n"
         "import a6_launch_freeze as A6, build_kfields_hard_review_targeted as HRT\n"
         "real = A6._read_ptr\n"
         "A6._read_ptr = lambda name: %r if name == 'hard_review_targeted_dir.txt' else real(name)\n"
         "HRT.BINDING = %r\n"
         "try:\n"
         "    total, rows = A6.ledger()\n"
         "    print('ACCEPTED', total, json.dumps([(r['stage'], r['calls']) for r in rows if r['stage'].startswith('hard_review_targeted')]))\n"
         "except ValueError as exc:\n"
         "    print('REFUSED', str(exc))"
         % (_HERE, copy, binding)],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-600:]
    return out.stdout.strip()


@_run
def test_the_ledger_counts_a_bound_copy_and_refuses_it_after_one_raw_byte(copy):
    """The positive control first, then the exact refusal: the tampered byte
    must reach the bound-identity check, not a folder mismatch and not a
    generic refusal (Codex SEQ 1494)."""
    binding = HRT.BINDING                            # the copy's own binding (fixture)
    positive = _ledger_over(copy, binding)
    assert positive == "ACCEPTED %d " % _clean_ledger()[0] + json.dumps(
        [["hard_review_targeted_primary", 22]]), positive
    _mutations()[0][1](copy)                         # one raw byte
    negative = _ledger_over(copy, binding)
    assert negative.startswith("REFUSED "), negative
    assert "is not the bound identity" in negative, negative
    assert "not the bound hard-review run" not in negative, negative


@_run
def test_the_ledger_refuses_an_unexpected_child_whole(copy):
    binding = HRT.BINDING
    _mutations()[18][1](copy)                        # an unbound retry directory
    negative = _ledger_over(copy, binding)
    assert negative.startswith("REFUSED ") and "the binding owns" in negative, negative


@_run
def test_no_rule_lives_in_a6_only_the_row():
    src = io.open(os.path.join(_HERE, "a6_launch_freeze.py"), encoding="utf-8").read()
    block = src[src.index("_HRT.proved_spend"):src.index("# THE COMPLETED PRODUCER HISTORY")]
    for word in ("_run_evidence", "_stored_matches", "_receipt_problems", "outcomes", "scheduled"):
        assert word not in block, word
    assert src.count("hard_review_targeted_dir.txt") == 2      # the pointer tuple and the one read
