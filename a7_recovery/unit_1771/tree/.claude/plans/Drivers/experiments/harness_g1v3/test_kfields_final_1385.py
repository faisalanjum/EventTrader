"""Codex SEQ 1385 — the cache-scope closeout.

Build-only. Direct mutations against the ONE lawful 32-correction world the
SEQ 1384 file already builds; nothing is rebuilt per mutation and the shared
world is never damaged - every mutating control copies first, keeping the
directory basename because a receipt is bound to its own name.
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
from test_kfields_final_1384 import world                        # noqa: E402,F401

K = F.K


def _copy(src, dst_parent, name):
    dst = str(dst_parent / name)
    shutil.copytree(src, dst)
    return dst


# ------------------------------------------------- 1: the lawful warm control
def test_a_warm_cache_still_answers_the_lawful_world(world):
    """Reuse INSIDE one operation stays: the gate must still pass warm."""
    assert F.accepted_shards(world["corr"], world["b2"], "corrections")[2] == []
    assert F.signing_gate(world["events"], world["b2"])["ok"]
    assert F.corrected_shards(world["b2"])[3] == []
    assert F.accepted_shards(world["corr"], world["b2"], "corrections")[2] == []


def test_reuse_survives_inside_one_operation(world):
    """The 32 prompts must not re-prove the event run 32 times."""
    F._accepted_shards_cached.cache_clear()
    before = F._accepted_shards_cached.cache_info().misses
    F.signing_gate(world["events"], world["b2"])
    inside = F._accepted_shards_cached.cache_info()
    assert inside.hits > 0, inside
    assert inside.misses - before <= 4, inside


# ----------------------- 2: changed finalized proof is seen after a warm cache
@pytest.mark.parametrize("call", ["loader", "corrected", "gate", "signer"])
def test_a_changed_correction_finalization_refuses_even_warm(world, tmp_path,
                                                             call):
    corr = _copy(world["corr"], tmp_path, "corr")
    b = world["b2"]._replace(corrections=corr)
    assert F.accepted_shards(corr, b, "corrections")[2] == []   # warm it
    assert F.signing_gate(world["events"], b)["ok"]
    fin = os.path.join(corr, K.FINALIZATION_NAME)
    doc = K._load(fin)
    doc["phase"] = "signer"
    io.open(fin, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    if call == "loader":
        assert F.accepted_shards(corr, b, "corrections")[2] != []
    elif call == "corrected":
        assert F.corrected_shards(b)[3] != []
    elif call == "gate":
        g = F.signing_gate(world["events"], b)
        assert not g["ok"] and g["stops"]
    else:
        got = F.prepare_signer(str(tmp_path / "sig"), b)
        assert not got["ok"] and got["invocations"] == []


def test_a_changed_correction_receipt_refuses_even_warm(world, tmp_path):
    corr = _copy(world["corr"], tmp_path, "corr")
    b = world["b2"]._replace(corrections=corr)
    assert F.signing_gate(world["events"], b)["ok"]
    io.open(os.path.join(corr, K.RECEIPT_NAME), "a",
            encoding="utf-8").write(" ")
    assert not F.signing_gate(world["events"], b)["ok"]


# ------------------- 3: a changed EARLIER transcript is seen after a warm cache
def _event_transcript(events, session):
    """One official event transcript path, from the run's own receipt."""
    receipt = K._load(os.path.join(events, K.RECEIPT_NAME))
    state = receipt["states"][0]
    doc = K._load(state)
    row = [r for r in doc["workflowProgress"]
           if r.get("type") == "workflow_agent"][0]
    return os.path.join(str(session), "subagents", "workflows", doc["runId"],
                        "agent-%s.jsonl" % row["agentId"])


def test_a_lawful_fresh_identity_still_passes(world):
    """The positive beside the mutation below."""
    label = F.correction_labels(world["b1"])[0]
    receipt = K._load(os.path.join(world["corr"], K.RECEIPT_NAME))
    proved, problems = F.run_evidence(world["corr"], world["b1"], receipt)
    assert problems == []
    assert proved[label][0] == "proved"


def test_a_changed_earlier_transcript_identity_refuses_even_warm(world,
                                                                 tmp_path):
    """Codex SEQ 1385 proof 3: warm the spent identities, then make an EARLIER
    official transcript collide with a later call. The cross-phase owner must
    see the change, not answer from the warm entry."""
    events = _copy(world["events"], tmp_path, "events_v1")
    b = world["b2"]._replace(events=events)
    receipt = K._load(os.path.join(world["corr"], K.RECEIPT_NAME))
    assert F.run_evidence(world["corr"], b, receipt)[1] == []    # warm
    runs, agents, msgs, reqs = F._spent_identities(world["corr"])
    collide = sorted(msgs)[0]
    path = _event_transcript(events, world["session"])
    recs = [json.loads(l) for l in io.open(path, encoding="utf-8")
            if l.strip()]
    for r in recs:
        if r.get("type") == "assistant":
            r["message"]["id"] = collide
    with io.open(path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    _proved, problems = F.run_evidence(world["corr"], b, receipt)
    assert any("already spent" in p for p in problems), problems
