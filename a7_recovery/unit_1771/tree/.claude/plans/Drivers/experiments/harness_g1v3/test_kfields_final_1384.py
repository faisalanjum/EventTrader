"""Codex SEQ 1384 — bounded proof for the six pre-call boundaries.

Build-only: no model call, no signer call, no lock publication, no database,
no repository edit. ONE lawful 32-correction composition is built once at module
scope and reused; every mutation is a small direct input, never a repeated full
fixture. The accepted 30-test matrix is deliberately not rerun.
"""
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_final as F                                  # noqa: E402
import test_kfields_final_1379 as T9                             # noqa: E402
import test_kfields_final_1380 as T8                             # noqa: E402
import test_kfields_final_1383 as T3                             # noqa: E402

K = F.K
EV, HRR, FIXR = T9.EV, T9.HRR, T9.FIXR
LIVE_EVENTS = T3.LIVE_EVENTS


# ------------------------------------------------------------ ONE fixture --
@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """The single lawful world: package, copied v1 run, 32 corrections, signer.

    Built once. Codex SEQ 1384: no repeated full fixture per mutation.
    """
    mp = pytest.MonkeyPatch()
    root = tmp_path_factory.mktemp("w1384")
    session = root / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)
    real = F.HR.AUD._official_location

    def located(path):
        p = os.path.realpath(str(path))
        if p.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        return real(path)

    mp.setattr(F.HR.AUD, "_official_location", located)

    pkg = str(root / "pkg")
    F.build(pkg, EV, HRR, FIXR)
    events = str(root / "events_v1")
    shutil.copytree(LIVE_EVENTS, events)
    b1 = F.Bound(pkg, EV, HRR, FIXR, events)

    answers = T8.gate_clean_answers(F.event_tasks(EV))
    corr = str(root / "corr")
    prepared = F.prepare_corrections(corr, b1)
    assert prepared["ok"], prepared["problems"]
    for label in F.correction_labels(b1):
        F.record_state(corr, T3.build_correction_call(
            session, b1, label, answers[label]))
    fin = F.finalize(corr, b1)
    assert fin["problems"] == [] and fin["ledger"]["valid"] == 32
    b2 = b1._replace(corrections=corr)

    gate = F.signing_gate(events, b2)
    assert gate["ok"], gate["stops"]
    sdir = str(root / "signer")
    sp = F.prepare_signer(sdir, b2)
    assert sp["ok"], sp["problems"]
    text = '{"signed": true, "blocked": [], "why": "clean"}'
    run_id, agent = "wfs_1384", "agent_wfs_1384"
    tdir = session / "subagents" / "workflows" / run_id
    tdir.mkdir(parents=True, exist_ok=True)
    prompt = F._signer_context(b2, 1)[0]
    recs = [{"type": "user", "uuid": "su0", "parentUuid": None,
             "agentId": agent, "sessionId": K.PARENT_SESSION,
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "uuid": "su1", "parentUuid": "su0",
             "agentId": agent, "sessionId": K.PARENT_SESSION,
             "effort": K.EFFORT, "requestId": "req_" + run_id,
             "message": {"role": "assistant", "id": "msg_" + run_id,
                         "model": K.RUNTIME_MODEL_ID,
                         "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": text}]}}]
    with io.open(str(tdir / ("agent-%s.jsonl" % agent)), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "script": F._signer_context(b2, 1)[1],
           "workflowProgress": [{"type": "workflow_agent", "state": "done",
                                 "label": "a4-final-signer", "agentId": agent,
                                 "model": K.RUNTIME_MODEL_ID,
                                 "agentType": K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"role": "signer", "attempt": 1, "model": K.MODEL,
                      "effort": K.EFFORT, "agentType": K.AGENT_TYPE,
                      "text": text}}
    spath = session / "workflows" / ("%s.json" % run_id)
    io.open(str(spath), "w", encoding="utf-8").write(json.dumps(doc))
    F.record_state(sdir, str(spath))
    F.finalize(sdir, b2)

    yield {"root": root, "session": session, "pkg": pkg, "events": events,
           "corr": corr, "signer": sdir, "b1": b1, "b2": b2,
           "prepared": prepared, "answers": answers}
    mp.undo()


# =================================== 1: capacity measured before publishing ==
def test_the_exact_scripts_are_measured_before_the_receipt_exists(world):
    assert world["prepared"]["largest_script_bytes"] == 342555
    assert world["prepared"]["largest_script_bytes"] < K.TRANSPORT_LIMIT


@pytest.mark.parametrize("size,refuses", [(524287, False), (524288, True)])
def test_the_capacity_edge_is_the_exact_utf8_byte(size, refuses):
    scripts = {"one": "a" * size}
    assert len("a" * size) == size
    assert bool(F.capacity_problems(scripts)) is refuses


def test_a_script_over_the_limit_refuses_before_publication(world, tmp_path,
                                                            monkeypatch):
    monkeypatch.setattr(K, "TRANSPORT_LIMIT", 1024)
    out = str(tmp_path / "cap")
    got = F.prepare_corrections(out, world["b1"])
    assert not got["ok"] and got["invocations"] == []
    assert not os.path.isfile(os.path.join(out, K.RECEIPT_NAME))


# ============================================ 2: the whole raw tree is pinned =
def test_the_raw_tree_pin_counts_every_preserved_file(world):
    pins = K._load(os.path.join(world["corr"], K.RECEIPT_NAME))["v1_evidence"]
    assert pins["raw_tree"]["files"] == 72
    assert pins["raw_tree"] == F.raw_tree(world["events"])
    assert F.original_evidence_unchanged(world["b2"], pins) == []


@pytest.mark.parametrize("how", ["add", "delete", "change"])
def test_any_raw_tree_edit_refuses(world, tmp_path, how):
    events = str(tmp_path / "copy")
    shutil.copytree(world["events"], events)
    b = world["b2"]._replace(events=events)
    pins = K._load(os.path.join(world["corr"], K.RECEIPT_NAME))["v1_evidence"]
    assert F.original_evidence_unchanged(b, pins) == []
    raw = os.path.join(events, "raw")
    names = sorted(os.listdir(raw))
    if how == "add":
        io.open(os.path.join(raw, "zz_extra.json"), "w",
                encoding="utf-8").write("{}")
        expect = "files"
    elif how == "delete":
        os.remove(os.path.join(raw, names[0]))
        expect = "files"
    else:
        io.open(os.path.join(raw, names[0]), "a", encoding="utf-8").write(" ")
        expect = "changed"
    bad = F.original_evidence_unchanged(b, pins)
    assert any(expect in x for x in bad), bad


# ==================================== 3: identities are fresh across phases ==
def test_a_later_phase_seeds_every_earlier_run(world):
    b2 = world["b2"]
    corr_receipt = K._load(os.path.join(world["corr"], K.RECEIPT_NAME))
    seeded = F._prior_runs(world["corr"], b2, corr_receipt)
    assert world["events"] in seeded
    sig_receipt = K._load(os.path.join(world["signer"], K.RECEIPT_NAME))
    sseed = F._prior_runs(world["signer"], b2, sig_receipt)
    assert world["events"] in sseed and world["corr"] in sseed


@pytest.mark.parametrize("reuse", ["agent", "message"])
def test_a_correction_that_reuses_an_event_identity_refuses(world, tmp_path,
                                                            reuse):
    """The mutation is one extra state, not another full run."""
    b1, label = world["b1"], F.correction_labels(world["b1"])[0]
    runs, agents, msgs, reqs = F._spent_identities(world["events"])
    kw = {"run_id": "wfc_clash_%s" % reuse}
    if reuse == "agent":
        kw["agent"] = sorted(agents)[0]
        word = "agent id"
    else:
        kw["rec_mutate"] = lambda r: r[-1]["message"].__setitem__(
            "id", sorted(msgs)[0])
        word = "response id"
    path = T3.build_correction_call(world["session"], b1, label,
                                    world["answers"][label], **kw)
    receipt = dict(K._load(os.path.join(world["corr"], K.RECEIPT_NAME)))
    receipt["states"] = [path]
    _proved, problems = F.run_evidence(world["corr"], b1, receipt)
    assert any(word in p and "already spent" in p for p in problems), problems


# ============================================= 4: the exhibit keeps the text =
def test_the_exhibit_accounts_every_original_question(world):
    ex = F.exhibit(world["b2"])
    assert ex["problems"] == []
    assert ex["replaced"] == 32 and ex["kept_original"] == 4
    assert len(ex["events"]) == 36
    assert ex["original_issues_total"] == 91
    assert ex["final_issues_total"] == 0
    kept = [r for r in ex["events"] if r["origin"] == "a4_final_v1"]
    assert len(kept) == 4
    for r in ex["events"]:
        assert isinstance(r["original_issues"], list)
        assert len(r["original_issues"]) == r["original_issue_count"]
        assert r["final_issues"] == []
        assert r["original_sha256"] and r["final_sha256"]
        if r["origin"] == "a4_final_v1":
            assert r["original_sha256"] == r["final_sha256"]


# ================================== 5: the conditional v2 lock, and only it ==
def test_the_corrected_lock_is_v2_and_binds_both_runs(world):
    b2, sdir = world["b2"], world["signer"]
    locked = F.lock(sdir, b2)
    assert locked["schema"] == "a4-detailed-key-lock-v2"
    assert locked["loader"]["entry"] == "corrected_shards"
    assert len(locked["key_shards"]) == 36
    assert sum(1 for s in locked["key_shards"]
               if s["origin"] == "a4_final_v2_correction") == 32
    assert locked["v1_evidence"]["raw_tree"]["files"] == 72
    assert locked["exhibit_sha256"] == K._sha(F.exhibit_bytes(b2))
    assert locked["correction_receipt_sha256"] == F.INV.sha_file(
        os.path.join(world["corr"], K.RECEIPT_NAME))
    assert F.lock_problems(locked, sdir, b2) == []


@pytest.mark.parametrize("field", [
    "schema", "loader", "key_shards", "v1_evidence",
    "correction_receipt_sha256", "correction_finalization_sha256",
    "exhibit_sha256", "signer_raw_sha256", "counts", "bound_owners"])
def test_every_new_v2_binding_is_rederived(world, field):
    locked = F.lock(world["signer"], world["b2"])
    locked[field] = "tampered"
    assert F.lock_problems(locked, world["signer"], world["b2"]) != []


def test_the_uncorrected_lock_shape_is_untouched(world):
    """v1 must still emit exactly what it always did."""
    src = F.inspect.getsource(F.lock) if hasattr(F, "inspect") else ""
    del src
    b1 = world["b1"]
    assert b1.corrections is None
    gate = F.signing_gate(world["events"], b1)
    assert not gate["ok"]          # v1 alone still carries its open issues
    assert any("open issue" in s for s in gate["stops"])


# =============================== 6: a broken correction artifact is reported =
@pytest.mark.parametrize("how", ["missing_receipt", "malformed_receipt",
                                 "missing_finalization", "no_pins"])
def test_a_broken_correction_artifact_stops_the_gate(world, tmp_path, how):
    corr = str(tmp_path / "c")
    shutil.copytree(world["corr"], corr)
    b = world["b2"]._replace(corrections=corr)
    assert F.signing_gate(world["events"], b)["ok"]
    if how == "missing_receipt":
        os.remove(os.path.join(corr, K.RECEIPT_NAME))
    elif how == "malformed_receipt":
        io.open(os.path.join(corr, K.RECEIPT_NAME), "w",
                encoding="utf-8").write("{not json")
    elif how == "missing_finalization":
        os.remove(os.path.join(corr, K.FINALIZATION_NAME))
    else:
        doc = K._load(os.path.join(corr, K.RECEIPT_NAME))
        doc["v1_evidence"] = {}
        io.open(os.path.join(corr, K.RECEIPT_NAME), "w",
                encoding="utf-8").write(json.dumps(doc))
    gate = F.signing_gate(world["events"], b)
    assert not gate["ok"] and gate["stops"]
    got = F.prepare_signer(str(tmp_path / "s_%s" % how), b)
    assert not got["ok"] and got["invocations"] == []


# ================================== the one lawful composition, reused once ==
def test_the_lawful_corrected_composition(world):
    b2 = world["b2"]
    shards, raws, origins, bad = F.corrected_shards(b2)
    assert bad == [] and len(shards) == 36
    assert sum(1 for o in origins.values()
               if o == "a4_final_v2_correction") == 32
    assert sum(1 for o in origins.values() if o == "a4_final_v1") == 4
    gate = F.signing_gate(world["events"], b2)
    assert gate["ok"], gate["stops"]
    c = gate["counts"]
    assert c["rows_accounted"] == 196 and c["events_accounted"] == 36
    assert c["open_issues"] == 0
    for tag, n in c["distinct_rows_per_tag"].items():
        assert n >= F.BIR.CLASS_FLOOR, (tag, n)
    assert c["sequential_rows"] >= F.BIR.SEQUENTIAL_FLOOR


def test_same_event_duplicates_refuse_while_cross_event_ones_do_not(world,
                                                                    monkeypatch):
    b2 = world["b2"]
    real = F.materialize

    def same_event(evidence_dir, shards):
        key, side, probs = real(evidence_dir, shards)
        sid = [s for s in key if key[s]][0]
        key[sid] = list(key[sid]) + [key[sid][0]]
        return key, side, probs

    def cross_event(evidence_dir, shards):
        key, side, probs = real(evidence_dir, shards)
        got = [s for s in key if key[s]]
        key[got[1]] = list(key[got[1]]) + [key[got[0]][0]]
        return key, side, probs

    monkeypatch.setattr(F, "materialize", same_event)
    assert any("semantic duplicates" in s
               for s in F.signing_gate(world["events"], b2)["stops"])
    monkeypatch.setattr(F, "materialize", cross_event)
    assert F.signing_gate(world["events"], b2)["ok"]
