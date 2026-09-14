"""Codex SEQ 1398: the V6 lock-only owner, and one mutation table.

One lawful synthetic V6 signer is built ONCE on the real accepted V6 world and
reused. No model call, no real lock published, no broadened audit.
"""
import copy
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_final as F                                  # noqa: E402
import v6_lock_1398 as L                                         # noqa: E402

K = F.K
S = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
     '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad')
rd = lambda n: io.open(S + '/' + n, encoding='utf-8').read().strip()  # noqa: E731
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """The real accepted V6 world plus ONE lawful synthetic signer."""
    pkg = S + '/bench_1306/.claude/plans/Drivers/experiments/kfields_final'
    b6 = F.Bound(pkg, rd('a4_dir.txt'), rd('hr_dir.txt'), rd('hrfix_dir.txt'),
                 rd('final_dir.txt'), rd('corr_dir.txt'),
                 rd('decision_dir.txt'), rd('v4_dir.txt'), rd('v5_dir.txt'),
                 rd('v6_dir.txt'))
    gate = F.signing_gate(b6.events, b6)
    assert gate["ok"], gate["stops"]
    sdir = str(tmp_path_factory.mktemp("v6signer") / "signer")
    sp = F.prepare_signer(sdir, b6)
    assert sp["ok"], sp["problems"]

    text = '{"signed": true, "blocked": [], "why": "clean"}'
    run_id, agent = "wfs_v6_1398", "agent_wfs_v6_1398"
    tdir = os.path.join(SESSION, "subagents", "workflows", run_id)
    os.path.isdir(tdir) or os.makedirs(tdir)
    prompt, script = F._signer_context(b6, 1)
    recs = [{"type": "user", "uuid": "su0_v6", "parentUuid": None,
             "agentId": agent, "sessionId": K.PARENT_SESSION,
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "uuid": "su1_v6", "parentUuid": "su0_v6",
             "agentId": agent, "sessionId": K.PARENT_SESSION,
             "effort": K.EFFORT, "requestId": "req_" + run_id,
             "message": {"role": "assistant", "id": "msg_" + run_id,
                         "model": K.RUNTIME_MODEL_ID, "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": text}]}}]
    with io.open(os.path.join(tdir, "agent-%s.jsonl" % agent), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "script": script,
           "workflowProgress": [{"type": "workflow_agent", "state": "done",
                                 "label": "a4-final-signer", "agentId": agent,
                                 "model": K.RUNTIME_MODEL_ID,
                                 "agentType": K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"role": "signer", "attempt": 1, "model": K.MODEL,
                      "effort": K.EFFORT, "agentType": K.AGENT_TYPE,
                      "text": text}}
    spath = os.path.join(SESSION, "workflows", "%s.json" % run_id)
    io.open(spath, "w", encoding="utf-8").write(json.dumps(doc))
    assert not F.record_state(sdir, spath)
    fin = F.finalize(sdir, b6)
    assert fin["problems"] == [], fin["problems"]
    return {"b6": b6, "signer": sdir, "gate": gate}


# ------------------------------------------------- the lawful V6 lock, once
def test_one_lawful_v6_signer_yields_exactly_one_v6_lock(world):
    lock = L.v6_lock(world["signer"], world["b6"])
    assert lock["schema"] == "a4-detailed-key-lock-v6"
    assert lock["state"] == "LOCKED"
    assert lock["signature"]["signed"] is True
    assert len(lock["key_shards"]) == 36
    assert lock["v6_events"] == F.v6_labels(world["b6"])
    assert sorted(lock["history_evidence"]) == ["v1", "v2", "v3", "v4", "v5"]
    assert lock["loader"]["entry"] == "v6_shards"
    assert lock["lock_owner"]["module"] == "v6_lock_1398"
    # deriving twice gives the same document
    assert L.v6_lock(world["signer"], world["b6"]) == lock
    assert L.v6_lock_problems(lock, world["signer"], world["b6"]) == []


def test_the_frozen_owner_still_refuses_a_v6_bound_lock(world):
    """The edge that could not be reached before a clean gate existed."""
    with pytest.raises(ValueError) as exc:
        F.lock(world["signer"], world["b6"])
    assert "no v6 lock shape is authorised" in str(exc.value)


def test_the_v6_owner_refuses_a_non_v6_bound(world):
    b5 = world["b6"]._replace(decision_correction_v6=None)
    with pytest.raises(ValueError) as exc:
        L.v6_lock(world["signer"], b5)
    assert "no v6 run is bound" in str(exc.value)


# --------------------------------------------- ONE parameterized mutation table
_FIELDS = ["schema", "state", "base_commit", "package_manifest_sha256",
           "bound_owners", "lock_owner", "loader", "key_shards", "v6_events",
           "history_evidence", "v6_receipt_sha256", "v6_finalization_sha256",
           "v6_raw_tree", "signer_raw_sha256", "signer_finalization_sha256",
           "signer_raw_tree", "counts", "signature"]


@pytest.mark.parametrize("field", _FIELDS)
def test_mutating_any_returned_lock_field_refuses(world, field):
    lock = L.v6_lock(world["signer"], world["b6"])
    bad = copy.deepcopy(lock)
    v = bad[field]
    bad[field] = ("MUTATED" if isinstance(v, str)
                  else (v + ["MUTATED"] if isinstance(v, list)
                        else dict(list(v.items()) + [("MUTATED", 1)])
                        if isinstance(v, dict) else not v))
    probs = L.v6_lock_problems(bad, world["signer"], world["b6"])
    assert probs, "mutating %s was accepted" % field
    assert any(field in p for p in probs), probs


@pytest.mark.parametrize("how", ["shard_order", "shard_origin", "shard_hash",
                                 "extra_field"])
def test_mutating_the_key_shards_refuses(world, how):
    lock = L.v6_lock(world["signer"], world["b6"])
    bad = copy.deepcopy(lock)
    if how == "shard_order":
        bad["key_shards"][0], bad["key_shards"][1] = \
            bad["key_shards"][1], bad["key_shards"][0]
    elif how == "shard_origin":
        # must be a value it is NOT: shard 0 already reads a4_final_v3_decision,
        # so the old mutation was a no-op that passed for the wrong reason.
        assert bad["key_shards"][0]["origin"] != "a4_final_v6_correction"
        bad["key_shards"][0]["origin"] = "a4_final_v6_correction"
    elif how == "shard_hash":
        bad["key_shards"][0]["sha256"] = "0" * 64
    else:
        bad["an_invented_field"] = "MUTATED"
    probs = L.v6_lock_problems(bad, world["signer"], world["b6"])
    assert probs, "%s was accepted" % how


@pytest.mark.parametrize("tag", ["v1", "v2", "v3", "v4", "v5"])
def test_mutating_a_retained_history_pin_refuses(world, tag):
    lock = L.v6_lock(world["signer"], world["b6"])
    bad = copy.deepcopy(lock)
    bad["history_evidence"][tag] = {"raw_tree": {"sha256": "0" * 64}}
    probs = L.v6_lock_problems(bad, world["signer"], world["b6"])
    assert probs, "mutating the %s pin was accepted" % tag


@pytest.mark.parametrize("what", ["v6_raw", "v6_receipt", "v6_finalization",
                                  "signer_raw", "signer_finalization"])
def test_mutating_a_live_artifact_makes_the_lock_refuse(world, what, tmp_path):
    """Not the document - the BYTES it is derived from."""
    b6, sdir = world["b6"], world["signer"]
    lock = L.v6_lock(sdir, b6)
    target = {"v6_raw": os.path.join(b6.decision_correction_v6, "raw"),
              "v6_receipt": os.path.join(b6.decision_correction_v6,
                                         K.RECEIPT_NAME),
              "v6_finalization": os.path.join(b6.decision_correction_v6,
                                              K.FINALIZATION_NAME),
              "signer_raw": os.path.join(sdir, "raw"),
              "signer_finalization": os.path.join(sdir,
                                                  K.FINALIZATION_NAME)}[what]
    if os.path.isdir(target):
        target = os.path.join(target, sorted(os.listdir(target))[0])
    original = io.open(target, "rb").read()
    try:
        io.open(target, "ab").write(b" ")
        probs = L.v6_lock_problems(lock, sdir, b6)
        assert probs, "an appended byte in %s was accepted" % what
    finally:
        io.open(target, "wb").write(original)
    # and the world is restored
    assert L.v6_lock_problems(lock, sdir, b6) == []
