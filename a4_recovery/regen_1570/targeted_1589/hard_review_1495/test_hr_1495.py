# -*- coding: utf-8 -*-
"""Recovery-specific controls for the hard-review run 1495 (Codex SEQ 1612 item 4). Runs inside the recovery world after
the adapter reproduced the run at its historical path. The positive control is the finalized run itself, re-proved
through the exact owners; every mutation is one member of a real class and must fail closed on a disposable copy or
on bytes restored afterwards: the receipt transform, receipt identity, binding identity, missing / duplicate /
swapped state, foreign transcript bytes, changed / extra raw bytes. The artifact tree is never written."""
import copy, hashlib, io, json, os, shutil, sys
import pytest

HOME = os.environ.get("HR_1495_HOME", "")
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
pytestmark = pytest.mark.skipif(not (HOME and os.path.ismount("/tmp")), reason="only inside the recovery world")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


def load(p):
    return json.loads(read(p).decode("utf-8"))


@pytest.fixture(scope="module")
def W():
    for d in (os.path.dirname(HOME) + "/phase1_targeted_1488", os.path.dirname(HOME) + "/targeted_run_1491", HOME):
        if d not in sys.path:
            sys.path.insert(0, d)
    import recover_hr_1495 as A
    import recover_phase1_1488 as A1
    import reconstruct_receipt_1493 as RR
    K, T = A1.route()
    import build_kfields_hard_review as HR, build_kfields_hard_review_targeted as HRT, build_kfields_final as F
    return {"A": A, "K": K, "T": T, "HR": HR, "HRT": HRT, "F": F, "RR": RR, "RUN": A.RUN, "SESS": A.SESS, "pins": A.PINS, "wfs": A.workflows(), "ctx": HRT._ctx()}


def refinalize(W, name, mutate):
    """A same-named disposable copy of the finalized run, its finalization removed (write-once), one mutation applied,
    then the exact owner's finalize over it. -> the finalization document."""
    dst = S + "/copies_" + name + "/" + os.path.basename(W["RUN"])
    if os.path.exists(dst):
        shutil.rmtree(os.path.dirname(dst))
    shutil.copytree(W["RUN"], dst); os.remove(dst + "/finalization.json")
    mutate(dst)
    return W["HRT"].finalize(dst), dst


GREEN = {"scheduled": 22, "valid": 22, "invalid_response": 0, "transport_no_answer": 0, "unproved": 0, "missing": 0}


def test_positive_control_reproves_the_run(W):
    fin = load(W["RUN"] + "/finalization.json")
    assert fin["ledger"] == GREEN and fin["problems"] == [] and fin.get("retry") == [] and fin["primary_complete"] is True
    assert sha(read(W["RUN"] + "/receipt.json")) == W["pins"]["run_receipt"] and sha(read(W["RUN"] + "/finalization.json")) == W["pins"]["run_finalization"]
    assert W["F"].raw_tree(W["RUN"])["sha256"] == W["pins"]["raw_tree_canonical"]
    doc, dst = refinalize(W, "positive", lambda d: None)
    assert doc["ledger"] == GREEN and doc["problems"] == [] and doc.get("retry") == []


# ---- the receipt transform -------------------------------------------------------------------------------
def test_transform_reproduces_the_exact_1493_receipt(W):
    b = read(HOME + "/inputs/a7_budget_receipt_1492.json")
    out = W["RR"].transform(b, sha(read(W["T"].BINDING)))
    assert sha(out) == W["pins"]["budget_receipt"] and len(out) == 6547


@pytest.mark.parametrize("case", ["row_changed", "hash_changed", "wrong_schema", "shape_changed"])
def test_transform_refuses_a_changed_predecessor(W, case):
    d = load(HOME + "/inputs/a7_budget_receipt_1492.json")
    if case == "row_changed":
        d["completed_rows"][0]["calls"] += 1
    elif case == "hash_changed":
        d["receipt_sha256"] = "0" * 64
    elif case == "wrong_schema":
        d["schema"] = "a7_call_budget_receipt/1488"
    else:
        [s for s in d["stages"] if s["stage"] == "g1"][0]["shape_artifact_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        W["RR"].transform(json.dumps(d, indent=1).encode("utf-8"), sha(read(W["T"].BINDING)))


def test_transform_with_another_binding_is_another_receipt(W):
    b = read(HOME + "/inputs/a7_budget_receipt_1492.json")
    other = W["RR"].transform(b, "1" * 64)
    assert sha(other) != W["pins"]["budget_receipt"]


# ---- package identity: binding and receipt ----------------------------------------------------------------
def test_binding_identity_drift_refuses_the_package(W):
    p = W["T"].BINDING; orig = read(p)
    d = json.loads(orig.decode("utf-8")); d["attempts"][0]["receipt_sha256"] = "0" * 64
    io.open(p, "w", encoding="utf-8").write(json.dumps(d, indent=1))
    try:
        assert W["HRT"].package_problems(W["HRT"].PKG_DIR) != []
        r = W["HRT"].prepare_run(S + "/drift_binding_run"); assert r["ok"] is False and r["invocations"] == []
    finally:
        io.open(p, "wb").write(orig)
    assert W["HRT"].package_problems(W["HRT"].PKG_DIR) == []


def test_budget_receipt_drift_refuses_the_package(W):
    p = W["HRT"].BUDGET_RECEIPT; orig = read(p)
    io.open(p, "wb").write(orig + b" ")
    try:
        assert W["HRT"].package_problems(W["HRT"].PKG_DIR) != []
    finally:
        io.open(p, "wb").write(orig)
    assert W["HRT"].package_problems(W["HRT"].PKG_DIR) == []


def test_wrong_receipt_identity_leaves_every_call_unproved(W):
    def mutate(d):
        r = load(d + "/receipt.json"); r["manifest_sha256"] = "0" * 64; io.open(d + "/receipt.json", "w").write(json.dumps(r, indent=1))
    doc, dst = refinalize(W, "receipt", mutate)
    assert doc["ledger"]["valid"] == 0 and doc["ledger"]["unproved"] == 22 and doc["primary_complete"] is False


# ---- states: missing / duplicate / swapped -----------------------------------------------------------------
def _with_states(d, fn):
    r = load(d + "/receipt.json"); r["states"] = fn(list(r["states"])); io.open(d + "/receipt.json", "w").write(json.dumps(r, indent=1))


def test_missing_state_is_missing_not_valid(W):
    doc, dst = refinalize(W, "missing", lambda d: _with_states(d, lambda s: s[:-1]))
    assert doc["ledger"]["valid"] == 21 and doc["ledger"]["missing"] == 1 and doc["primary_complete"] is False and doc.get("retry") == []


def test_duplicate_state_is_refused(W):
    doc, dst = refinalize(W, "duplicate", lambda d: _with_states(d, lambda s: s + [s[0]]))
    assert doc["ledger"]["valid"] < 22 or doc["problems"] != []
    assert doc["primary_complete"] is False or doc["problems"] != []


def test_swapped_state_from_another_door_is_refused(W):
    other = W["SESS"] + "/workflows/" + [l.split("\t")[3] for l in io.open(os.path.dirname(HOME) + "/targeted_run_1491/inputs/WORKFLOWS.tsv").read().splitlines()[1:]][0] + ".json"
    doc, dst = refinalize(W, "swapped", lambda d: _with_states(d, lambda s: [other] + s[1:]))
    assert doc["ledger"]["valid"] < 22 and doc["primary_complete"] is False


# ---- transcript and raw bytes ------------------------------------------------------------------------------
def test_foreign_transcript_record_is_unproved(W):
    w = W["wfs"][0]; tr = W["SESS"] + "/subagents/workflows/" + w["wf"]
    p = tr + "/" + [f for f in sorted(os.listdir(tr)) if f.startswith("agent-") and f.endswith(".jsonl")][0]; orig = read(p)
    io.open(p, "wb").write(orig + b'{"agentId": "foreign", "sessionId": "foreign"}\n')
    try:
        doc, dst = refinalize(W, "transcript", lambda d: None)
        assert doc["ledger"]["unproved"] >= 1 and doc["ledger"]["valid"] == 21 and doc["primary_complete"] is False
    finally:
        io.open(p, "wb").write(orig)
    doc, dst = refinalize(W, "transcript_restored", lambda d: None); assert doc["ledger"] == GREEN


def test_changed_raw_bytes_are_unproved(W):
    def mutate(d):
        f = sorted(x for x in os.listdir(d + "/raw") if x.endswith(".raw.json"))[0]; io.open(d + "/raw/" + f, "ab").write(b" ")
    doc, dst = refinalize(W, "raw_changed", mutate)
    assert doc["ledger"]["unproved"] == 1 and doc["ledger"]["valid"] == 21 and doc["primary_complete"] is False


def test_extra_raw_file_moves_the_canonical_tree(W):
    def mutate(d):
        io.open(d + "/raw/zz_extra.raw.json", "wb").write(b"{}")
    doc, dst = refinalize(W, "raw_extra", mutate)
    tree = W["F"].raw_tree(dst)
    assert tree["sha256"] != W["pins"]["raw_tree_canonical"] and tree.get("files", len(os.listdir(dst + "/raw"))) != 44
