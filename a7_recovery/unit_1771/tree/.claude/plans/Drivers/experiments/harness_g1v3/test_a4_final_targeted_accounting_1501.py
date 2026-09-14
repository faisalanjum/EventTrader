# -*- coding: utf-8 -*-
"""CALL ACCOUNTING FOR THE SUCCESSOR PRIMARY RUN (Codex SEQ 1501 item 1).

The completed ledger must include /tmp/a4_final_targeted_run_1500 exactly
once, proved through the wrapper's own binding and the pinned package the run
ran under (closed history): receipt, finalization, every official state, every
raw/proved byte, the canonical raw tree, every RE-DERIVED outcome, the allowed
identities, no child, and the call count: 5202 + 8 = 5210. Test first.

Every refusal is proved on a same-named disposable copy; the run is never written.
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
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_key as K                                    # noqa: E402

RUN = "/tmp/a4_final_targeted_run_1500"
POINTER = os.path.join(K.EVIDENCE, "final_targeted_dir.txt")
BUDGET_1496 = "/tmp/a7_budget_receipt_1496.json"
_run = pytest.mark.skipif(not os.path.isdir(RUN), reason="the primary run is absent")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _dump(p, doc):
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))


def _raw_names(d):
    rec = _load(os.path.join(d, "receipt.json"))
    run_id = os.path.splitext(os.path.basename(rec["states"][0]))[0]
    label = K._state_label(_load(rec["states"][0]))
    return (os.path.join(d, "raw", "%s.000.raw.json" % run_id),
            os.path.join(d, "raw", "%s.attempt1.proved.json" % label))


def _clean_ledger():
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
def test_the_ledger_counts_the_primary_run_exactly_once():
    total, rows = _clean_ledger()
    stages = [r["stage"] for r in rows]
    prim = [r for r in rows if r["stage"] == "final_targeted_primary"]
    assert len(prim) == 1, stages
    assert "final_targeted_retry" not in stages
    assert prim[0]["run_dir"] == RUN and prim[0]["calls"] == 8
    assert prim[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert prim[0]["finalization_sha256"] == _sha(RUN + "/finalization.json")
    assert prim[0]["raw_tree"] == F.raw_tree(RUN)["sha256"]
    before = _load(BUDGET_1496)
    later = [r for r in rows if r not in before["completed_rows"] and r["stage"] != "final_targeted_primary"]
    assert [r for r in rows if r not in later and r not in prim] == before["completed_rows"]   # every earlier row, unchanged, in order
    at = rows.index(prim[0])
    assert rows[at + 1:at + 1 + len(later)] == later                 # every stage bound since follows this run's row
    assert sum(r["calls"] for r in before["completed_rows"]) == before["completed_before"]
    assert total == before["completed_before"] + 8 + sum(r["calls"] for r in later) == sum(r["calls"] for r in rows)
    assert _clean_ledger() == [total, rows]


@_run
def test_the_pointer_binds_the_exact_run():
    assert io.open(POINTER, encoding="utf-8").read().strip() == RUN


@_run
def test_proved_spend_reports_the_primary_from_its_own_proofs():
    got = FT.proved_spend(RUN)
    assert [(g["run_dir"], g["attempt"], g["calls"], g["raw_files"]) for g in got] == [(RUN, 1, 8, 16)]
    assert got[0]["receipt_sha256"] == _sha(RUN + "/receipt.json")
    assert got[0]["raw_tree"] == F.raw_tree(RUN)["sha256"]
    assert FT.proved_spend(RUN) == got


@_run
def test_the_binding_freezes_the_run_and_its_pinned_package_once():
    b = _load(FT.BINDING)
    assert b["schema"] == FT.BINDING_SCHEMA and b["run_dir"] == RUN
    pkg = b["package"]
    assert pkg["manifest_sha256"] == _sha(os.path.join(pkg["dir"], FT.MANIFEST_NAME)) \
        == _load(RUN + "/receipt.json")["manifest_sha256"]
    att = {a["attempt"]: a for a in b["attempts"]}
    assert sorted(att) == [1] and att[1]["dir"] == RUN
    raw = os.path.join(RUN, "raw")
    assert att[1]["raw_files"] == {f: _sha(os.path.join(raw, f)) for f in sorted(os.listdir(raw))}
    assert att[1]["raw_tree"] == dict(F.raw_tree(RUN)) and att[1]["raw_tree"]["files"] == 16
    with pytest.raises((ValueError, OSError)):
        FT.write_binding(RUN, pkg["dir"])


@_run
def test_the_closed_package_is_history_not_a_live_gate():
    """The wrapper binds its own bytes, so the package the run ran under no
    longer rebuilds live - by exactly the owner hash - yet the bound run
    still proves against those pinned bytes."""
    pkg = _load(FT.BINDING)["package"]["dir"]
    bad = FT.package_problems(pkg)
    assert bad == ["the pinned derived_from is not the live one"], bad
    pinned = _load(os.path.join(pkg, FT.MANIFEST_NAME))["derived_from"]
    live = FT._derived_from()
    assert {k for k in live if live[k] != pinned.get(k)} == {"final_targeted_owner_sha256"}
    assert FT.proved_spend(RUN)[0]["calls"] == 8


@_run
def test_a_copy_of_the_run_is_not_the_bound_run(tmp_path):
    dst = str(tmp_path / os.path.basename(RUN)); shutil.copytree(RUN, dst)
    with pytest.raises(ValueError) as exc:
        FT.proved_spend(dst)
    assert "is not the bound %s run" % FT.DOOR in str(exc.value)


# ------------------------------------------------ refusals on a same-named copy
@pytest.fixture
def copy(tmp_path, monkeypatch):
    dst = str(tmp_path / os.path.basename(RUN)); shutil.copytree(RUN, dst)
    real = _load(FT.BINDING)
    doc = {"schema": FT.BINDING_SCHEMA, "run_dir": dst, "package": real["package"],
           "attempts": [FT._measured_attempt(dst, 1)]}
    bound = str(tmp_path / "final_targeted_binding.json"); _dump(bound, doc)
    monkeypatch.setattr(FT, "BINDING", bound)
    # the correction round is chained to the primary binding through its review receipt:
    # a device that rebinds the primary rebinds EVERY owner, so the receipt follows the copy
    rev = _load(FT.REVIEW_RECEIPT)
    rev["primary_binding"] = {"binding_path": bound, "binding_sha256": _sha(bound), "run_dir": dst}
    review = str(tmp_path / "review.json"); _dump(review, rev)
    monkeypatch.setattr(FT, "REVIEW_RECEIPT", review)
    return dst


def _mutations():
    def raw_byte(d):
        io.open(_raw_names(d)[0], "a", encoding="utf-8").write(" ")

    def proved_byte(d):
        io.open(_raw_names(d)[1], "a", encoding="utf-8").write(" ")

    def raw_missing(d):
        os.remove(_raw_names(d)[0])

    def extra_file(d):
        io.open(os.path.join(d, "raw", "zz_extra.raw.json"), "w").write("{}")

    def swapped_files(d):
        raw = os.path.join(d, "raw")
        names = sorted(n for n in os.listdir(raw) if n.endswith(".raw.json"))[:2]
        a, b = (os.path.join(raw, n) for n in names)
        ta, tb = io.open(a, encoding="utf-8").read(), io.open(b, encoding="utf-8").read()
        io.open(a, "w", encoding="utf-8").write(tb); io.open(b, "w", encoding="utf-8").write(ta)

    def script_byte(d):
        p = sorted(os.listdir(os.path.join(d, "scripts")))[0]
        io.open(os.path.join(d, "scripts", p), "a").write(" ")

    def receipt_allowed_swapped(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        rec["allowed"][0], rec["allowed"][1] = rec["allowed"][1], rec["allowed"][0]; _dump(p, rec)

    def receipt_prompt_tampered(d):
        p = os.path.join(d, "receipt.json"); rec = _load(p)
        rec["prompts"][rec["allowed"][0]] = "0" * 64; _dump(p, rec)

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
        fin["ledger"]["valid"] = 7; fin["ledger"]["invalid_response"] = 1; _dump(p, fin)

    def finalization_retry_invented(d):
        p = os.path.join(d, "finalization.json"); fin = _load(p)
        fin["retry"] = [fin["outcomes"][0][0]]; _dump(p, fin)

    def finalization_missing(d):
        os.remove(os.path.join(d, "finalization.json"))

    def unexpected_child(d):
        os.makedirs(os.path.join(d, "retry")); io.open(os.path.join(d, "retry", "receipt.json"), "w").write("{}")
    return [("raw_byte", raw_byte), ("proved_byte", proved_byte), ("raw_missing", raw_missing),
            ("extra_file", extra_file), ("swapped_files", swapped_files), ("script_byte", script_byte),
            ("receipt_allowed_swapped", receipt_allowed_swapped), ("receipt_prompt_tampered", receipt_prompt_tampered),
            ("foreign_state", foreign_state), ("duplicate_state", duplicate_state), ("state_dropped", state_dropped),
            ("finalization_receipt_sha", finalization_receipt_sha),
            ("finalization_outcome_flipped", finalization_outcome_flipped),
            ("finalization_ledger_only", finalization_ledger_only),
            ("finalization_retry_invented", finalization_retry_invented),
            ("finalization_missing", finalization_missing), ("unexpected_child", unexpected_child)]


@_run
def test_the_unaltered_copy_is_the_lawful_control(copy):
    assert [(g["attempt"], g["calls"], g["raw_files"]) for g in FT.proved_spend(copy)] == [(1, 8, 16)]


@_run
@pytest.mark.parametrize("name,mutate", _mutations(), ids=[m[0] for m in _mutations()])
def test_every_mutation_refuses_the_whole_row(copy, name, mutate):
    mutate(copy)
    with pytest.raises(ValueError):
        FT.proved_spend(copy)


@_run
def test_a_moved_pinned_package_refuses(copy, tmp_path, monkeypatch):
    b = _load(FT.BINDING); b["package"] = dict(b["package"], manifest_sha256="0" * 64)
    moved = str(tmp_path / "moved.json"); _dump(moved, b)
    monkeypatch.setattr(FT, "BINDING", moved)
    with pytest.raises(ValueError) as exc:
        FT.proved_spend(copy)
    assert "pinned package" in str(exc.value)


def _ledger_over(copy, binding, review):
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB')\n"
         "import a6_launch_freeze as A6, build_kfields_final_targeted as FT\n"
         "real = A6._read_ptr\n"
         "A6._read_ptr = lambda name: %r if name == 'final_targeted_dir.txt' else real(name)\n"
         "FT.BINDING = %r\n"
         "FT.REVIEW_RECEIPT = %r\n"
         "try:\n"
         "    total, rows = A6.ledger()\n"
         "    print('ACCEPTED', total, json.dumps([(r['stage'], r['calls']) for r in rows if r['stage'].startswith('final_targeted')]))\n"
         "except ValueError as exc:\n"
         "    print('REFUSED', str(exc))"
         % (_HERE, copy, binding, review)],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-600:]
    return out.stdout.strip()


@_run
def test_the_ledger_counts_a_bound_copy_and_refuses_it_after_one_raw_byte(copy):
    binding, review = FT.BINDING, FT.REVIEW_RECEIPT
    positive = _ledger_over(copy, binding, review)
    assert positive.startswith("ACCEPTED "), positive
    total, stages = int(positive.split()[1]), json.loads(positive.split(" ", 2)[2])
    before = _load(BUDGET_1496)["completed_before"]
    assert stages[0] == ["final_targeted_primary", 8]                # this run's row, exactly once
    assert all(s[0].startswith("final_targeted_correction") for s in stages[1:])   # then the rounds bound since it
    assert total == before + sum(n for _s, n in stages)             # before + every stage bound since
    _mutations()[0][1](copy)
    negative = _ledger_over(copy, binding, review)
    assert negative.startswith("REFUSED ") and "is not the bound identity" in negative, negative
    assert "is not the bound %s run" % FT.DOOR not in negative


@_run
def test_no_rule_lives_in_a6_only_the_row():
    src = io.open(os.path.join(_HERE, "a6_launch_freeze.py"), encoding="utf-8").read()
    block = src[src.index("_FT.proved_spend"):src.index("# THE COMPLETED PRODUCER HISTORY")]
    for word in ("_run_evidence", "run_evidence", "_stored_matches", "receipt_problems", "outcomes", "scheduled"):
        assert word not in block, word
    assert src.count("final_targeted_dir.txt") == 2
