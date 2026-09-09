# -*- coding: utf-8 -*-
"""Codex SEQ 1915 item 2: run the frozen signer packet and write the compact lock.

The packet is the candidate owner's own, unrun and frozen. This serves ONE TEST
official state for it - the frozen launcher bytes, the frozen prompt in the
transcript, a signer reply - then hands it to the canonical harvest owner and
the canonical lock owner. Neither owner is reimplemented and no signature is
copied from another packet.
"""
import collections, importlib.util, io, json, os, sys

RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
TAG = os.environ["A7_TAG"]
ATT = os.environ["A7_ATTEMPT_DIR"]; os.makedirs(ATT, exist_ok=True)
ROOT = os.environ.get("A7_LIFECYCLE_ROOT", "/tmp/a7_logs_1781/lifecycle")
OWNERS = os.environ["A7_LOCK_OWNERS"]
PATH = os.environ.get("A7_KEY_PATH", "owed")
sys.path.insert(0, RECOVERY)
sys.path.insert(0, VIEW)
import audit_worker_access as AUD                                # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import g1_fake_state as FAKE                                     # noqa: E402
import validate_benchmark_inventory as INV                       # noqa: E402

STORE = os.path.join(ROOT, "TEST_projects")
AUD.PROJECTS_ROOT = STORE
SESS = os.path.join(STORE, "TESTproj1909", K.PARENT_SESSION)
io.open(S + "/a3_serial_dir.txt", "w", encoding="utf-8").write(
    os.path.join(ROOT, "a3") + "\n")

NATIVE_INPUT = (None if os.environ.get("A7_LEGACY_NO_EXTRA_INPUT")
                else FAKE.declared_input_record())
res = collections.OrderedDict(tag=TAG, kind="COMPACT_KEY_LOCK", path=PATH,
                              runtime_input=("legacy_no_extra_input"
                                             if NATIVE_INPUT is None
                                             else "native"))
checks = collections.OrderedDict()

# the newest candidate of this path that carries an unrun frozen packet
cands = sorted(d for d in os.listdir(ROOT)
               if d.startswith("candidate_%s_" % PATH)
               and os.path.isfile(os.path.join(ROOT, d, "signer",
                                               "signer.manifest.json")))
res["candidates"] = cands
cand = os.path.join(ROOT, cands[-1]) if cands else None
res["candidate_dir"] = cand
checks["1_a_frozen_candidate_packet_exists"] = bool(cand)
if not cand:
    print("no candidate packet"); sys.exit(1)
SIG = os.path.join(cand, "signer")
man = json.load(io.open(os.path.join(SIG, "signer.manifest.json"),
                        encoding="utf-8"))
prompt = io.open(os.path.join(SIG, "signer_prompt.txt"), encoding="utf-8").read()
script = io.open(os.path.join(SIG, "final_sign.attempt1.js"),
                 encoding="utf-8").read()
res["packet"] = collections.OrderedDict([("prompt_sha256", man["prompt_sha256"]),
                                         ("script_sha256", man["script_sha256"]),
                                         ("shards", len(man["shards"]))])

sys.path.insert(0, OWNERS)
import raw_transport as RT                                       # noqa: E402
import signer_proof as SP                                        # noqa: E402

def test_reply(run_id):
    """THE SAME lawful signature for every TEST call, on purpose: two
    independent calls may return identical bytes, and a fixture that removed
    that collision would hide the very thing selection must survive
    (Codex SEQ 1924/1925)."""
    return json.dumps(collections.OrderedDict([
        ("signed", True), ("blocked", []),
        ("why", "TEST only: every scheduled row settled through its owners and "
                "the candidate re-derives; this signs the plumbing, never "
                "source truth.")]))
#: EVERY TEST call this caller makes passes through here, and nowhere else.
CALLS = []


def serve_test_call(attempt):
    """THE TEST TRANSPORT BOUNDARY. One official state, one transcript."""
    n = 0
    while os.path.isfile(os.path.join(SESS, "workflows",
                                      "wf_TESTsign_%s_%03d.json" % (PATH, n))):
        n += 1
    run_id = "wf_TESTsign_%s_%03d" % (PATH, n)
    agent = "TESTsign_%s_%03d" % (PATH, n)
    CALLS.append(run_id)
    tdir = os.path.join(SESS, "subagents", "workflows", run_id)
    os.makedirs(tdir)
    reply = test_reply(run_id)
    # WHAT THE RUNTIME SUPPLIES, fixed before this run and never asked of the
    # packet under test (Codex SEQ 1957 item 1). The observed runtime splices
    # the approved input record into a worker transcript whatever the signer
    # manifest declares; the no-added-input case is a SEPARATE fixed fixture
    # the runner chooses through A7_LEGACY_NO_EXTRA_INPUT.
    FAKE._transcript(tdir, agent, K.PARENT_SESSION, prompt, reply,
                     NATIVE_INPUT)
    state = collections.OrderedDict([
        ("runId", run_id), ("status", "completed"), ("totalToolCalls", 0),
        ("script", io.open(os.path.join(SIG, "final_sign.attempt%d.js" % attempt),
                           encoding="utf-8").read()),
        ("workflowProgress", [
            {"type": "workflow_phase", "index": 1, "title": "Sign"},
            {"type": "workflow_agent", "index": 1, "label": "a4-final-signer",
             "agentId": agent, "agentType": K.AGENT_TYPE,
             "model": K.RUNTIME_MODEL_ID, "state": "done", "attempt": attempt,
             "toolCalls": 0, "promptPreview": prompt[:200]}]),
        ("result", collections.OrderedDict([
            ("role", "signer"), ("attempt", attempt), ("model", K.MODEL),
            ("effort", K.EFFORT), ("agentType", K.AGENT_TYPE), ("text", reply)]))])
    io.open(os.path.join(SESS, "workflows", run_id + ".json"), "w",
            encoding="utf-8").write(json.dumps(state))
    return run_id


def finished_call():
    """A call this packet already paid for, RE-PROVED. -> (attempt, run) or None.

    Not "a file exists": the saved evidence is put back through signer_proof,
    its own record must agree with what that derives, and the proved outcome
    must be the clean signature. Anything less is not a finished call.
    """
    if os.environ.get("A7_NO_REUSE"):
        return None, None            # the control that must fail without this
    lawful = [s["attempt"] for s in man.get("scripts") or [{"attempt": 1}]]
    for n in lawful:
        ev = os.path.join(SIG, "final_sign.attempt%d.evidence.json" % n)
        if not os.path.isfile(ev):
            continue
        rec = json.load(io.open(ev, encoding="utf-8"))
        if rec.get("outcome") != "signed":
            continue
        proof, why = SP.prove(SIG, man, n, rec.get("run_id"), SESS, {})
        if why or SP.disagreements(rec, proof) or proof.get("outcome") != "signed":
            continue
        return n, rec["run_id"]
    return None, None


def bound_run(n):
    """What THIS packet durably records about its own attempt n, or None.

    Only the packet's own records name its call: the evidence of a completed
    one, or the invocation of one that earned no credit. Nothing is inferred
    from the session, because an answer is not an identity.
    """
    for kind in ("evidence", "invocation"):
        p = os.path.join(SIG, "final_sign.attempt%d.%s.json" % (n, kind))
        if os.path.isfile(p):
            rec = json.load(io.open(p, encoding="utf-8"))
            return kind, rec, rec.get("run_id")
    return None, None, None


def partial_call():
    """An attempt whose answer was paid for but whose evidence is unfinished.

    -> (attempt, run, None) when the packet itself names that call,
       (None, None, reason) when a call was made and cannot be identified,
       (None, None, None) when no attempt is in that state at all.
    """
    lawful = [s["attempt"] for s in man.get("scripts") or [{"attempt": 1}]]
    for n in lawful:
        raw = os.path.join(SIG, RT._raw_filename("final_sign.attempt%d" % n))
        ev = os.path.join(SIG, "final_sign.attempt%d.evidence.json" % n)
        if not os.path.isfile(raw) or os.path.isfile(ev):
            continue
        _kind, _rec, run = bound_run(n)
        if run is None:
            return None, None, ("attempt %d paid for an answer but this packet "
                                "records no call to bind it to" % n)
        proof, why = SP.prove(SIG, man, n, run, SESS, {})
        if why:
            return None, None, ("attempt %d's recorded call %s no longer "
                                "proves: %s" % (n, run, why[0]))
        paid = SP.sha(io.open(raw, encoding="utf-8").read())
        if proof.get("raw_sha256") != paid:
            return None, None, ("attempt %d's saved answer is not what its "
                                "recorded call %s returned" % (n, run))
        return n, run, None
    return None, None, None


ATTEMPT, RUN = finished_call()
res["resumed"] = bool(RUN)
AMBIGUOUS = None
if RUN is None:
    ATTEMPT, RUN, AMBIGUOUS = partial_call()
    res["finished_an_interrupted_call"] = bool(RUN)
if AMBIGUOUS:
    # A CALL WAS MADE AND CANNOT BE IDENTIFIED: a named failure with no call,
    # never a fall-through to the unrun branch (Codex SEQ 1925).
    res["ambiguous"] = AMBIGUOUS
    res["test_calls_made"] = list(CALLS)
    checks["2_the_signature_is_harvested_and_proved"] = False
    res["checks"] = checks
    res["all_green"] = False
    io.open(os.path.join(ATT, "COMPACT_%s.json" % TAG), "w",
            encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
    print("AMBIGUOUS: %s" % AMBIGUOUS)
    sys.exit(1)
if RUN is None:
    ATTEMPT = 1
    RUN = serve_test_call(ATTEMPT)
res["signer_state"] = os.path.join(SESS, "workflows", RUN + ".json")
res["test_calls_made"] = list(CALLS)
run_id = RUN

os.environ["A7_CANDIDATE_DIR"] = cand
os.environ["A7_SIGNER_SESSION"] = SESS
argv = list(sys.argv)
sys.argv = [os.path.join(OWNERS, "harvest_final_sign.py"), run_id, str(ATTEMPT)]
spec = importlib.util.spec_from_file_location("harvest_final_sign", sys.argv[0])
mod = importlib.util.module_from_spec(spec)
code = 0
try:
    spec.loader.exec_module(mod)
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else 1
except BaseException as exc:                          # noqa: BLE001 - by design
    res["harvest_error"] = "%s: %s" % (type(exc).__name__, exc)
    code = 1
finally:
    sys.argv = argv
res["harvest_exit"] = code
# THE HARVEST EITHER SUCCEEDED OR IT DID NOT. A reply already on disk and a
# resumed flag excuse nothing (Codex SEQ 1924/1925).
checks["2_the_signature_is_harvested_and_proved"] = (code == 0)
res["signer_files"] = sorted(os.listdir(SIG))

# THE FINAL CHECKS ALWAYS RUN: fewer checks is never a pass.
if True:
    spec = importlib.util.spec_from_file_location(
        "build_final_key_lock", os.path.join(OWNERS, "build_final_key_lock.py"))
    lock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock)
    try:
        lock.main()
        lock_code = 0
    except SystemExit as exc:
        lock_code = exc.code if isinstance(exc.code, int) else 1
    except BaseException as exc:                      # noqa: BLE001 - by design
        res["lock_error"] = "%s: %s" % (type(exc).__name__, exc)
        lock_code = 1
    res["lock_exit"] = lock_code
    checks["3_the_compact_lock_is_written_and_every_value_refuses_mutation"] = (
        lock_code == 0)
    for name in ("a4_final_key_lock.json", "a4_final_key_lock_receipt.json"):
        p = os.path.join(cand, name)
        if os.path.isfile(p):
            res[name] = INV.sha_file(p)
    checks["4_the_lock_and_its_receipt_exist"] = all(
        os.path.isfile(os.path.join(cand, n))
        for n in ("a4_final_key_lock.json", "a4_final_key_lock_receipt.json"))

res["checks"] = checks
ok = all(checks.values())
res["all_green"] = ok
io.open(os.path.join(ATT, "COMPACT_%s.json" % TAG), "w",
        encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
print("candidate %s" % cand)
print("%d/%d -> %s" % (sum(1 for v in checks.values() if v), len(checks), ok))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
sys.exit(0 if ok else 1)
