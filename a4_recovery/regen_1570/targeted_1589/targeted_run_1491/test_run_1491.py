# -*- coding: utf-8 -*-
"""Focused tests for the recovered targeted run 1491 (Codex SEQ 1601 item 5, 1603 item 5, 1605 item 4). Runs inside
the recovery world after the adapter has reproduced the run at its historical path with its launchers restored. The
positive control is the adapter's finalized run and binding through the EXACT owner; every mutation is one member
of a real class and must fail closed with zero accepted spend (proved_spend raises, or the owner or the placement
guard refuses). Files are restored after each case."""
import copy, hashlib, io, json, os, shutil, sys
import pytest

HOME = os.environ.get("RUN_1491_HOME", "")
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
pytestmark = pytest.mark.skipif(not (HOME and os.path.ismount("/tmp")), reason="only inside the recovery world")
GREEN = [(1, 11), (2, 1)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return io.open(p, "rb").read()


@pytest.fixture(scope="module")
def W():
    if HOME not in sys.path:
        sys.path.insert(0, HOME)
    P1 = os.path.dirname(HOME) + "/phase1_targeted_1488"
    if P1 not in sys.path:
        sys.path.insert(0, P1)
    import recover_run_1491 as A
    import recover_phase1_1488 as A1
    K, T = A1.route()
    import audit_worker_access as AUD
    items = {i["packet_id"]: i for i in T.targeted_items()}
    return {"A": A, "K": K, "T": T, "B": T, "AUD": AUD, "RUN": A.RUN, "SESS": A.SESS, "pins": A.PINS, "wfs": A.workflows(), "items": items, "LAUNCH": A.LAUNCH}


def spend(W):
    """The accepted spend, or ('REFUSED', why): zero accepted calls on any refusal."""
    try:
        rows = W["B"].proved_spend(W["RUN"]); return [(r["attempt"], r["calls"]) for r in rows]
    except Exception as e:
        return ("REFUSED", "%s: %s" % (type(e).__name__, str(e)[:160]))


def _mutate(path, fn):
    orig = read(path); io.open(path, "wb").write(fn(orig)); return orig


def _restore(path, orig):
    io.open(path, "wb").write(orig)


def _edit_json(path, fn):
    orig = read(path); doc = json.loads(orig.decode("utf-8")); fn(doc); io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1)); return orig


def test_green_control_full_spend(W):
    assert spend(W) == GREEN
    assert sha(read(W["B"].BINDING)) == W["pins"]["binding"]
    assert sha(read(W["T"].__file__)) == W["pins"]["later_owner"]


# ---- workflow class: missing / duplicate / swapped ----------------------------------------------
def _receipt(W, base):
    return W["RUN"] + ("" if base == "primary" else "/retry") + "/receipt.json"


def _with_states(W, base, fn):
    p = _receipt(W, base); orig = read(p); doc = json.loads(orig.decode("utf-8")); doc["states"] = fn(list(doc["states"]))
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    try:
        return spend(W)
    finally:
        _restore(p, orig)


def test_missing_workflow_refused(W):
    got = _with_states(W, "primary", lambda s: s[:-1]); assert got[0] == "REFUSED"; assert spend(W) == GREEN


def test_duplicate_workflow_refused(W):
    got = _with_states(W, "primary", lambda s: s + [s[0]]); assert got[0] == "REFUSED"; assert spend(W) == GREEN


def test_swapped_workflow_refused(W):
    child_state = W["SESS"] + "/workflows/" + [w for w in W["wfs"] if w["attempt"] == "2"][0]["wf"] + ".json"
    got = _with_states(W, "primary", lambda s: [child_state] + s[1:]); assert got[0] == "REFUSED"; assert spend(W) == GREEN


# ---- wrong state / journal / transcript / agent ---------------------------------------------------
# The shared proof binds the state's structure (status, label, script, result) and every record of the agent
# transcript (agentId, sessionId, effort, model, identity); it reads neither the journal nor the agent meta of a
# non-resumed row. Those two are bound by THIS unit's Core 1310 pins at placement, so their mutations are
# refused by place_states before any state reaches the store; a byte the law does not bind is not a class.
def test_wrong_state_refused(W):
    w = W["wfs"][0]; p = W["SESS"] + "/workflows/" + w["wf"] + ".json"; orig = _edit_json(p, lambda d: d.__setitem__("status", "failed"))
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def test_wrong_transcript_refused(W):
    w = W["wfs"][0]; tr = W["SESS"] + "/subagents/workflows/" + w["wf"]
    p = tr + "/" + [f for f in sorted(os.listdir(tr)) if f.startswith("agent-") and f.endswith(".jsonl")][0]
    orig = _mutate(p, lambda b: b + b'{"agentId": "foreign", "sessionId": "foreign"}\n')
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def _store_copy(W, name):
    src = W["A"].SRC_ROOT; dst = S + "/store_" + name; shutil.copytree(src, dst); return dst


@pytest.mark.parametrize("what", ["state", "journal", "transcript", "agent_meta"])
def test_wrong_pinned_evidence_refused_at_placement(W, what):
    w = W["wfs"][0]; root = _store_copy(W, what); sess = [os.path.join(dp, d) for dp, dn, fn in os.walk(root) for d in dn if d == "workflows"][0].rsplit("/", 1)[0]
    tr = sess + "/subagents/workflows/" + w["wf"]
    if what == "state":
        p = sess + "/workflows/" + w["wf"] + ".json"
    elif what == "journal":
        p = tr + "/journal.jsonl"
    elif what == "transcript":
        p = tr + "/" + [f for f in sorted(os.listdir(tr)) if f.startswith("agent-") and f.endswith(".jsonl")][0]
    else:
        p = tr + "/" + [f for f in sorted(os.listdir(tr)) if f.endswith(".meta.json")][0]
    _mutate(p, lambda b: b.replace(b"a", b"b", 1))
    with pytest.raises(RuntimeError):
        W["A"].place_states(root, S + "/dest_" + what)
    assert not os.path.exists(S + "/dest_" + what + "/workflows/" + w["wf"] + ".json")
    assert spend(W) == GREEN


def test_pinned_evidence_placement_positive(W):
    root = _store_copy(W, "ok"); dest, rows = W["A"].place_states(root, S + "/dest_ok")
    assert len(rows) == 12 and all(r[5] == "pinned+projected" for r in rows)
    assert sorted(os.listdir(dest + "/workflows")) == sorted(w["wf"] + ".json" for w in W["wfs"])


# ---- launcher restoration class: the finalized run's armed launcher files ----------------------------
def _launcher(W, i):
    w = W["wfs"][i]; return json.loads(read(W["SESS"] + "/workflows/" + w["wf"] + ".json").decode("utf-8"))["scriptPath"]


def test_launcher_missing_refused(W):
    p = _launcher(W, 0); orig = read(p); os.remove(p)
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def test_launcher_swapped_refused(W):
    p, q = _launcher(W, 0), _launcher(W, 1); a, b = read(p), read(q); assert a != b
    io.open(p, "wb").write(b); io.open(q, "wb").write(a)
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, a); _restore(q, b)
    assert spend(W) == GREEN


def test_launcher_changed_path_refused(W):
    p = _launcher(W, 0); shutil.move(p, p + ".moved")
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        shutil.move(p + ".moved", p)
    assert spend(W) == GREEN


def test_launcher_changed_bytes_refused(W):
    p = _launcher(W, 0); orig = _mutate(p, lambda b: b + b"\n")
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def test_launcher_wrong_attempt_refused(W):
    i = [k for k, w in enumerate(W["wfs"]) if w["attempt"] == "2"][0]; p = _launcher(W, i); orig = read(p)
    other = W["K"].render_launcher(W["items"][W["wfs"][i]["packet_id"]], 1).encode("utf-8"); assert other != orig
    io.open(p, "wb").write(other)
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


# ---- launcher placement guard: the adapter's own restoration refuses every unlawful state --------------
def _docs(W, launch_dir):
    docs = []
    for order, attempt, pid, wf, doc in W["A"].state_docs(W["SESS"]):
        d = copy.deepcopy(doc); d["scriptPath"] = launch_dir + "/" + os.path.basename(doc["scriptPath"]); docs.append((order, attempt, pid, wf, d))
    return docs


def test_launcher_guard_positive(W):
    d = S + "/guard_ok"; rows = W["A"].place_launchers(W["K"], W["items"], _docs(W, d), d)
    assert len(rows) == 12 and sorted(r[4] for r in rows) == sorted(os.path.join(d, f) for f in os.listdir(d))
    assert [r[5] for r in rows] == [sha(read(_launcher(W, i))) for i in range(12)]


@pytest.mark.parametrize("case", ["script_mismatch", "duplicate_path", "wrong_attempt", "outside_launch_dir", "label_mismatch", "dir_present"])
def test_launcher_guard_refuses(W, case):
    d = S + "/guard_" + case; docs = _docs(W, d)
    if case == "script_mismatch":
        docs[0][4]["script"] += "\n"
    elif case == "duplicate_path":
        docs[1][4]["scriptPath"] = docs[0][4]["scriptPath"]
    elif case == "wrong_attempt":
        o, a, pid, wf, doc = docs[0]; docs[0] = (o, 2, pid, wf, doc)
    elif case == "outside_launch_dir":
        docs[0][4]["scriptPath"] = S + "/elsewhere/" + os.path.basename(docs[0][4]["scriptPath"])
    elif case == "label_mismatch":
        o, a, pid, wf, doc = docs[0]; docs[0] = (o, a, docs[1][2], wf, doc)
    else:
        os.makedirs(d)
    with pytest.raises(RuntimeError):
        W["A"].place_launchers(W["K"], W["items"], docs, d)
    assert spend(W) == GREEN


# ---- prompt / launcher / runtime / tool drift -------------------------------------------------------
def test_runtime_freeze_drift_refused(W):
    p = W["K"]._HERE + "/a2_runtime_freeze.json"; orig = _mutate(p, lambda b: b + b"\n")
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def test_package_prompt_drift_refused(W):
    p = W["T"].PKG_DIR + "/phase1.manifest.json"; orig = read(p); doc = json.loads(orig.decode("utf-8"))
    doc["items"][0]["prompt_sha256"] = ("0" if doc["items"][0]["prompt_sha256"][0] != "0" else "1") + doc["items"][0]["prompt_sha256"][1:]
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


# ---- raw / proved file changed, missing, extra ------------------------------------------------------
@pytest.mark.parametrize("what", ["changed", "missing", "extra"])
def test_raw_tree_change_refused(W, what):
    raw = W["RUN"] + "/raw"; files = sorted(os.listdir(raw)); p = raw + "/" + files[0]; orig = read(p)
    try:
        if what == "changed":
            io.open(p, "wb").write(orig + b" ")
        elif what == "missing":
            os.remove(p)
        else:
            io.open(raw + "/zz_extra.raw.json", "wb").write(b"{}")
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        if what == "extra":
            os.remove(raw + "/zz_extra.raw.json")
        else:
            io.open(p, "wb").write(orig)
    assert spend(W) == GREEN


# ---- meaningful receipt / finalization changes --------------------------------------------------------
def _erase_outcomes(d):
    assert isinstance(d["outcomes"], list) and d["outcomes"]; d["outcomes"] = []


@pytest.mark.parametrize("case", ["primary_retry_erased", "child_scheduled_changed", "child_outcomes_erased"])
def test_finalization_changes_refused(W, case):
    if case == "primary_retry_erased":
        p = W["RUN"] + "/finalization.json"; orig = _edit_json(p, lambda d: d.__setitem__("retry", []))
    elif case == "child_scheduled_changed":
        p = W["RUN"] + "/retry/finalization.json"; orig = _edit_json(p, lambda d: d["ledger"].__setitem__("scheduled", d["ledger"]["scheduled"] + 1))
    else:
        p = W["RUN"] + "/retry/finalization.json"; orig = _edit_json(p, _erase_outcomes)
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


# ---- missing / unexpected child ---------------------------------------------------------------------
def test_missing_child_refused(W):
    retry = W["RUN"] + "/retry"; shutil.move(retry, retry + ".aside")
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        shutil.move(retry + ".aside", retry)
    assert spend(W) == GREEN


# An UNEXPECTED child (a retry directory the primary finalization does not owe) is the primary_retry_erased case
# above: the owner is bound by the binding's attempt list and the run-root retry directory, and a nested
# directory it never names is not evidence, so a stray retry/retry is outside its law and is not a class.


# ---- binding / dependency drift ---------------------------------------------------------------------
def test_binding_drift_refused(W):
    p = W["B"].BINDING; orig = _edit_json(p, lambda d: d["attempts"][0].__setitem__("receipt_sha256", "0" * 64))
    try:
        got = spend(W); assert got[0] == "REFUSED"
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN


def test_dependency_drift_refused(W):
    base = json.loads(read(W["K"].A3_BASELINE).decode("utf-8")); rel = sorted(f for f in base["files"] if f.startswith("harness_g1v3/") and f.endswith(".py"))[0]
    p = W["K"]._X + "/" + rel; orig = _mutate(p, lambda b: b + b"\n# moved\n")
    try:
        r = W["T"].prepare_run(S + "/drift_run"); assert r["ok"] is False and r["invocations"] == []
    finally:
        _restore(p, orig)
    assert spend(W) == GREEN
