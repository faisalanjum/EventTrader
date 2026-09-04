"""The real owner boundaries of the signed-V6 baseline, exercised on the projected world after a
complete continuation build (run_foundation.sh run <n> --trace --tests): the built V6 lock re-derives
clean; the V6 composition accounts for every event, row and origin; then one mutation per boundary,
each restored afterwards, refused with the owner's own words: an altered historical receipt (the
finalized receipt no longer the proved one) or finalization and a missing raw reply (the next receipt's
recorded history), an altered V6 finalization
or raw reply (the lock's live re-derivation), a schema-invalid saved result (no accepted shard), an
altered launcher (the events phase), the signer reply's shape, and the administrative
receipt-epoch seam: an era receipt passes the owner's check only through the seam, and each mutated
field, byte or launcher refuses there with its reason. The owners are imported from the
projected harness; nothing here calls a model or parses a reply itself. Skipped outside the world.
"""
import collections
import copy
import io
import json
import os
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import foundation as FD  # noqa: E402
import receipt_epoch as RE  # noqa: E402

pytestmark = pytest.mark.skipif(not FD.inside_projection(), reason="the owner boundaries need the projected world: run_foundation.sh run <n> --trace --tests")


@pytest.fixture(scope="module")
def world():
    FD._owners()
    import build_kfields_final as F
    import v6_lock_1398 as L
    RE.install(F)
    b = FD.bound(F, "lock")
    sig = FD.X + "/runs/" + FD.run_root("signer")
    lock = json.loads(io.open(os.path.join(sig, FD.LOCK_NAME), "rb").read().decode("utf-8"))
    assert L.v6_lock_problems(lock, sig, b) == []
    return {"F": F, "L": L, "b": b, "signer": sig, "lock": lock}


def _problems(w):
    return w["L"].v6_lock_problems(w["lock"], w["signer"], w["b"])


def _restore(w, path, original):
    io.open(path, "wb").write(original)
    assert _problems(w) == []


def test_the_v6_composition_accounts_for_every_event_row_and_origin(world):
    F, b = world["F"], world["b"]
    shards, raws, origins, bad = F.v6_shards(b)
    assert bad == []
    gate = F.signing_gate(b.events, b)
    assert gate["ok"], gate["stops"]
    assert list(raws) == list(gate["raws"])
    order = [t["source_id"] for t in F.event_tasks(b.evidence)]
    assert FD.v6_accounting_problems(order, shards, origins, gate["counts"]) == []


@pytest.mark.parametrize("what,want", [
    ("v1 receipt", "the receipt changed after finalization"),
    ("v3 finalization", "receipt.v1_evidence is not the expected value"),
    ("v6 finalization", "the locked v6_finalization_sha256 is not the live one"),
    ("v6 raw", "the locked v6_raw_tree is not the live one"),
])
def test_an_altered_artifact_refuses_the_lock_with_the_owners_reason(world, what, want):
    K, b = world["F"].K, world["b"]
    tag, kind = what.split()
    run = {"v1": b.events, "v3": b.decision, "v6": b.decision_correction_v6}[tag]
    if kind == "raw":
        path = os.path.join(run, "raw", sorted(os.listdir(os.path.join(run, "raw")))[0])
    else:
        path = os.path.join(run, {"receipt": K.RECEIPT_NAME, "finalization": K.FINALIZATION_NAME}[kind])
    original = io.open(path, "rb").read()
    io.open(path, "ab").write(b" ")
    try:
        bad = _problems(world)
        assert bad and want in bad[0], bad
        if tag == "v6":
            assert bad == [want]
    finally:
        _restore(world, path, original)


def test_a_missing_raw_reply_refuses_at_the_next_receipts_history(world):
    b = world["b"]
    raw = os.path.join(b.corrections, "raw")
    names = sorted(os.listdir(raw))
    path = os.path.join(raw, names[0])
    original = io.open(path, "rb").read()
    os.remove(path)
    try:
        bad = _problems(world)
        assert bad and "receipt.v1_evidence is not the expected value" in bad[0], bad
    finally:
        _restore(world, path, original)


def test_a_schema_invalid_saved_result_leaves_its_event_without_an_accepted_shard(world):
    K, b = world["F"].K, world["b"]
    receipt = K._load(os.path.join(b.decision_correction_v6, K.RECEIPT_NAME))
    state_path = receipt["states"][0]
    doc = json.loads(io.open(state_path, "rb").read().decode("utf-8"))
    row = [r for r in doc["workflowProgress"] if r.get("type") == "workflow_agent"][0]
    transcript = os.path.join(FD.SESS, "subagents", "workflows", doc["runId"], "agent-%s.jsonl" % row["agentId"])
    originals = {p: io.open(p, "rb").read() for p in (state_path, transcript)}
    recs = [json.loads(l) for l in originals[transcript].decode("utf-8").split("\n") if l.strip()]
    last = [r for r in recs if r.get("type") == "assistant"][-1]
    invalid = '{"not": "a lawful shard"}'
    [c for c in last["message"]["content"] if c.get("type") == "text"][-1]["text"] = invalid
    doc["result"]["text"] = invalid
    io.open(state_path, "wb").write(json.dumps(doc).encode("utf-8"))
    io.open(transcript, "wb").write(("\n".join(json.dumps(r) for r in recs) + "\n").encode("utf-8"))
    try:
        bad = _problems(world)
        assert bad and "have no accepted shard" in bad[0], bad
    finally:
        for p, orig in originals.items():
            io.open(p, "wb").write(orig)
        assert _problems(world) == []


def test_an_altered_launcher_refuses_the_event_phase_at_the_owner(world):
    F, b = world["F"], world["b"]
    shards, _raws, bad = F.accepted_shards(b.events, b)
    assert bad == [] and len(shards) == len(F.event_tasks(b.evidence))
    receipt = F.K._load(os.path.join(b.events, F.K.RECEIPT_NAME))
    launcher = F.K._load(receipt["states"][0])["scriptPath"]
    original = io.open(launcher, "rb").read()
    io.open(launcher, "ab").write(b" ")
    try:
        _shards, _raws, bad = F.accepted_shards(b.events, b)
        assert bad and any("the scriptPath bytes are not the pinned script" in p for p in bad), bad
    finally:
        io.open(launcher, "wb").write(original)
        assert F.accepted_shards(b.events, b)[2] == []


# ---- the administrative receipt-epoch seam at the owner boundary ----
def _era_world(world):
    F, b = world["F"], world["b"]
    run = b.corrections                                   # an era run with a retry child
    return F, b, run, F.K._load(os.path.join(run, F.K.RECEIPT_NAME))


def test_the_era_receipt_passes_the_owners_check_only_through_the_seam(world):
    F, b, run, receipt = _era_world(world)
    assert F.receipt_problems(run, b, receipt) == []                       # the installed seam
    assert RE.ORIGINAL(run, b, receipt), "the un-seamed owner must not accept an era receipt"
    child = os.path.join(run, "retry")
    assert F.receipt_problems(child, b, F.K._load(os.path.join(child, F.K.RECEIPT_NAME))) == []
    assert F.receipt_problems(b.decision_correction_v6, b, F.K._load(os.path.join(b.decision_correction_v6, F.K.RECEIPT_NAME))) == []


@pytest.mark.parametrize("what,want", [
    ("manifest", "receipt.manifest_sha256 is not the"),
    ("bound", "receipt.bound is not the era-bound expected value"),
    ("history", "receipt.v1_evidence is not the era-bound expected value"),
    ("allowed order", "receipt.allowed is not the era-bound expected value"),
    ("prompt", "receipt.prompts is not the era-bound expected value"),
    ("state order", "is not the saved state of"),
    ("extra field", "unexpected fields"),
])
def test_a_mutated_era_receipt_refuses_at_the_seam_with_its_reason(world, what, want):
    F, b, run, receipt = _era_world(world)
    bad = copy.deepcopy(receipt)
    if what == "manifest":
        bad["manifest_sha256"] = "0" * 64
    elif what == "bound":
        bad["bound"]["final_owner_loader"] = "0" * 64
    elif what == "history":
        bad["v1_evidence"]["raw_tree"]["files"] += 1
    elif what == "allowed order":
        bad["allowed"][0], bad["allowed"][1] = bad["allowed"][1], bad["allowed"][0]
    elif what == "prompt":
        k = next(iter(bad["prompts"])); bad["prompts"][k] = "0" * 64
    elif what == "state order":
        bad["states"][0], bad["states"][1] = bad["states"][1], bad["states"][0]
    else:
        bad["later_field"] = 1
    probs = F.receipt_problems(run, b, bad)
    assert probs and any(want in p for p in probs), (what, probs)


def test_altered_era_receipt_bytes_or_launcher_refuse_at_the_seam(world):
    F, b, run, receipt = _era_world(world)
    path = os.path.join(run, F.K.RECEIPT_NAME)
    original = io.open(path, "rb").read()
    io.open(path, "ab").write(b" ")
    try:
        probs = F.receipt_problems(run, b, F.K._load(path))
        assert probs and any("not the pinned" in p for p in probs), probs
    finally:
        io.open(path, "wb").write(original)
    launcher = F.K._load(receipt["states"][0])["scriptPath"]
    original = io.open(launcher, "rb").read()
    io.open(launcher, "ab").write(b" ")
    try:
        probs = F.receipt_problems(run, b, receipt)
        assert probs and any("launcher" in p for p in probs), probs
    finally:
        io.open(launcher, "wb").write(original)
    assert F.receipt_problems(run, b, receipt) == []


def test_the_signer_reply_shape_is_the_owners(world):
    F = world["F"]
    obj, bad = F.read_signature('{"signed": true, "blocked": [], "why": "clean"}')
    assert bad == [] and obj["signed"] is True
    for text, why in (("not json", "not one lawful JSON object"), ('{"signed": true}', "keys are"),
                      ('{"signed": true, "blocked": ["x"], "why": "w"}', "a signature cannot be given with blocking reasons"),
                      ('{"signed": false, "blocked": [], "why": "w"}', "a refusal must say what blocks it")):
        obj, bad = F.read_signature(text)
        assert obj is None and any(why in b for b in bad), (text, bad)
