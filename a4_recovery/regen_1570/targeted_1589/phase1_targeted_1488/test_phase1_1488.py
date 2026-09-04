# -*- coding: utf-8 -*-
"""In-world focused tests for the phase1_targeted_1488 package (Codex SEQ 1598): the green control
reproduces both pinned files; one positive-control mutation per owner boundary actually used refuses
for its intended reason. The owner comes through the adapter's single historical import route."""
import hashlib, io, json, os, shutil, sys
import pytest

HOME = os.environ.get("PHASE1_1488_HOME", "")
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
pytestmark = pytest.mark.skipif(not (HOME and os.path.ismount("/tmp")), reason="only inside the recovery world")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


@pytest.fixture(scope="module")
def W():
    if HOME not in sys.path:
        sys.path.insert(0, HOME)
    import recover_phase1_1488 as A
    K, T = A.route()
    return {"A": A, "K": K, "T": T, "pins": A.PINS}


def build(W, out_dir):
    try:
        W["T"].build_targeted(str(out_dir))
        return (sha(read(str(out_dir) + "/phase1.manifest.json")), sha(read(str(out_dir) + "/rules.txt")))
    except Exception as e:
        return ("REFUSED", "%s: %s" % (type(e).__name__, str(e)[:160]))


def _targets(W):
    return (W["pins"]["manifest_sha256"], W["pins"]["rules_sha256"])


def test_green_control(W, tmp_path):
    assert build(W, tmp_path / "g") == _targets(W)


def _mutate(path, fn):
    orig = read(path); io.open(path, "wb").write(fn(orig)); return orig


def _restore(path, orig):
    io.open(path, "wb").write(orig)


def test_correction_output_changed_refused(W, tmp_path):
    p = os.path.dirname(W["T"].CORRECTION_RECEIPT) + "/final_inventory.json"; orig = _mutate(p, lambda b: b + b"\n")
    try:
        got = build(W, tmp_path / "o"); assert got[0] == "REFUSED" and "actual outputs" in got[1]
    finally:
        _restore(p, orig)
    assert build(W, tmp_path / "g") == _targets(W)


def test_correction_output_missing_refused(W, tmp_path):
    p = os.path.dirname(W["T"].CORRECTION_RECEIPT) + "/validator_receipt.json"; orig = read(p); os.remove(p)
    try:
        got = build(W, tmp_path / "o"); assert got[0] == "REFUSED" and "actual outputs" in got[1]
    finally:
        io.open(p, "wb").write(orig)
    assert build(W, tmp_path / "g") == _targets(W)


def test_correction_output_extra_refused(W, tmp_path):
    p = os.path.dirname(W["T"].CORRECTION_RECEIPT) + "/extra.json"; io.open(p, "w").write("{}")
    try:
        got = build(W, tmp_path / "o"); assert got[0] == "REFUSED" and "actual outputs" in got[1]
    finally:
        os.remove(p)
    assert build(W, tmp_path / "g") == _targets(W)


def test_budget_receipt_changed_misses_and_package_rebuild_names_budget(W, tmp_path):
    p = W["T"].BUDGET_RECEIPT; orig = _mutate(p, lambda b: b + b"\n")
    try:
        got = build(W, tmp_path / "o"); assert got != _targets(W) and got[0] != "REFUSED"
        assert any("manifest.budget" in x for x in W["T"].package_problems(W["T"].PKG_DIR))
    finally:
        _restore(p, orig)
    assert W["T"].package_problems(W["T"].PKG_DIR) == [] and build(W, tmp_path / "g") == _targets(W)


def test_real_door_refuses_a_moved_a3_byte_and_recovers(W, tmp_path):
    """The real targeted door: green control, one byte moved in a file the exact baseline lists ->
    ok false, the exact refusal reason, zero invocations, no receipt; restored -> green again."""
    K, T = W["K"], W["T"]; p99 = json.load(io.open(HOME + "/pins_1599.json", encoding="utf-8"))
    base_doc = json.loads(read(K.A3_BASELINE).decode("utf-8")); assert base_doc["digest"] == p99["baseline_digest"]
    target = sorted(f for f in base_doc["files"] if f.startswith("harness_g1v3/") and f.endswith(".py"))[0]
    g1 = T.prepare_run(str(tmp_path / "g1")); assert (g1["ok"], g1["problems"], len(g1["invocations"])) == (True, [], 11)
    assert [i["packet_id"] for i in g1["invocations"]] == W["pins"]["targets"] and os.path.isfile(str(tmp_path / "g1" / "receipt.json"))
    p = K._X + "/" + target; orig = _mutate(p, lambda b: b + b"\n# moved\n")
    try:
        red = T.prepare_run(str(tmp_path / "red"))
        assert red["ok"] is False and red["problems"] == [p99["refusal_reason"]] and red["invocations"] == [] and not os.path.exists(str(tmp_path / "red" / "receipt.json"))
    finally:
        _restore(p, orig)
    g2 = T.prepare_run(str(tmp_path / "g2")); assert (g2["ok"], g2["problems"], len(g2["invocations"])) == (True, [], 11)
    assert K._receipt_problems(str(tmp_path / "g2"), json.loads(read(str(tmp_path / "g2" / "receipt.json")).decode("utf-8")), T._ctx()) == []


def test_corrected_inventory_changed_refused(W, tmp_path):
    """A corrected record differing in a field the correction may not touch refuses in diff()."""
    p = W["T"].CORRECTED_INVENTORY; orig = read(p); doc = json.loads(orig.decode("utf-8"))
    doc["records"][0]["proposed_record_kind"] += "x"
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1, sort_keys=True))
    try:
        got = build(W, tmp_path / "o"); assert got[0] == "REFUSED" and "may differ" in got[1]
    finally:
        _restore(p, orig)
    assert build(W, tmp_path / "g") == _targets(W)
