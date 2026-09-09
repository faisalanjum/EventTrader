# -*- coding: utf-8 -*-
"""Codex SEQ 1894 items 1 and 3: the REAL source lifecycle, intact.

BIR.materialize -> BIR.finalize -> BIR.lock are called for real. Only the
model's ANSWERS and the official records that carry them are TEST, and they
live in a PRIVATE TEST projects store inside the boundary, never in the live
official store. The transcript helper is the existing one; nothing here is a
second auditor and nothing re-implements a materializer.
"""
import collections, hashlib, io, json, os, shutil, sys

RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
TAG = os.environ["A7_TAG"]
ATT = os.environ["A7_ATTEMPT_DIR"]
SRC_REPLIES = os.environ["A7_TEST_REPLIES"]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RECOVERY)
sys.path.insert(0, VIEW)
import build_inventory_review as BIR                             # noqa: E402
import audit_worker_access as AUD                                # noqa: E402
import g1_fake_state as FAKE                                     # noqa: E402

res = collections.OrderedDict(tag=TAG, kind="SOURCE_LIFECYCLE_TEST")
res["label"] = ("TEST answers and TEST official records only, in a private "
                "store; no model call and no real approval")
checks = collections.OrderedDict()

STORE = os.path.join(ATT, "TEST_projects")
SESS = os.path.join(STORE, "TESTproj1894", "TESTsess1894")
AUD.PROJECTS_ROOT = STORE
os.makedirs(os.path.join(SESS, "workflows"))
PARENT = os.path.basename(SESS)
REPLIES = os.path.join(ATT, "replies"); os.makedirs(REPLIES)
PROOF = os.path.join(ATT, "subscription.json")
io.open(PROOF, "w", encoding="utf-8").write(json.dumps({
    "authMethod": BIR.REVIEW_AUTH_METHOD, "apiProvider": BIR.REVIEW_API_PROVIDER,
    "note": "TEST rehearsal proof"}, indent=1))

n = [0]


def official(task, sid, prompt, answer, raw_name, ordinal, attempt=1):
    """One TEST official record: state, child transcript and saved raw."""
    n[0] += 1
    rid = "wf_TEST1894_%s_%03d" % (task, n[0])
    agent = "TEST1894agent%03d" % n[0]
    tdir = os.path.join(SESS, "subagents", "workflows", rid)
    os.makedirs(tdir)
    FAKE._transcript(tdir, agent, PARENT, prompt, answer)
    state = {
        "runId": rid, "status": "completed", "totalToolCalls": 0,
        "script": BIR.event_script(prompt),
        "workflowProgress": [
            {"type": "workflow_phase", "index": 1, "title": "review"},
            {"type": "workflow_agent", "index": 1, "label": str(sid),
             "agentId": agent, "agentType": BIR.REVIEW_AGENT_TYPE,
             "model": BIR.REVIEW_MODEL, "state": "done", "attempt": attempt,
             "toolCalls": 0, "promptPreview": prompt[:200]}],
    }
    spath = os.path.join(SESS, "workflows", rid + ".json")
    io.open(spath, "w", encoding="utf-8").write(json.dumps(state))
    io.open(os.path.join(REPLIES, raw_name), "w", encoding="utf-8").write(answer)
    return collections.OrderedDict([
        ("task", task), ("ordinal", ordinal), ("attempt", attempt),
        ("source_id", sid), ("state_path", spath), ("agent_id", agent),
        ("raw_name", raw_name)])


shipped = BIR.review_inputs()
manifest = json.loads(BIR._read(os.path.join(BIR._package_dir(),
                                             "package.manifest.json")))
attempts = []
for i, sid in enumerate(sorted(shipped)):
    answer = io.open(os.path.join(SRC_REPLIES, "%s.TEST.attempt1.raw.json" % sid),
                     encoding="utf-8").read()
    attempts.append(official("event", sid, BIR.prompt_text(sid), answer,
                             "%s.TEST.raw.json" % sid, i))

receipt = collections.OrderedDict([
    ("parent_session_id", PARENT),
    ("transport", BIR.REVIEW_TRANSPORT),
    ("max_output_tokens", str(manifest["reviewers"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"])),
    ("subscription_proof", PROOF),
    ("base_commit", manifest["base_commit"]),
    ("base_tree", manifest["base_tree"]),
    ("package_manifest_sha256", BIR._sha_text(BIR._read(
        os.path.join(BIR._package_dir(), "package.manifest.json")))),
    ("attempts", attempts)])
RPATH = os.path.join(ATT, "receipt.json")


def write_receipt(r, path=None):
    p = path or RPATH
    io.open(p, "w", encoding="utf-8").write(json.dumps(r, indent=1))
    return p


write_receipt(receipt)
artifacts, problems, report = BIR.materialize(REPLIES, RPATH)
res["materialize_problems"] = list(problems)[:8]
checks["1_materialize_is_intact"] = not problems
res["report"] = report if not problems else {}
if problems:
    res["checks"] = checks
    io.open(os.path.join(ATT, "LIFECYCLE_%s.json" % TAG), "w",
            encoding="utf-8").write(json.dumps(res, indent=2) + "\n")
    print("MATERIALIZE REFUSED (%d):" % len(problems))
    for p in problems[:8]:
        print("   %s" % p)
    sys.exit(1)

res["artifacts"] = {k: BIR._sha_text(v) for k, v in artifacts.items()}
res["records"] = json.loads(artifacts["final_inventory.json"])["counts"]

# the final sign, whose prompt IS the materialized sign input
sign_prompt = artifacts["final_sign_input.json"]
sign_answer = json.dumps({"signed": True, "blocked": None,
                          "why": "TEST rehearsal signature: mechanical "
                                 "handling only, never model truth"}, indent=1)
# THE SIGN TASK IS SCHEDULED WITH NO SOURCE: the receipt gate's own task list
# names ("final_sign", len(events), None), so the attempt carries source_id None.
attempts.append(official("final_sign", None, sign_prompt, sign_answer,
                         "final_sign.TEST.raw.json", len(shipped)))
write_receipt(receipt)

OUT = os.path.join(ATT, "locked")
fin = BIR.finalize(REPLIES, RPATH, OUT)
res["finalize"] = {"ok": fin["ok"], "problems": fin["problems"][:6],
                   "written": fin.get("written")}
checks["2_finalize_writes_every_artifact"] = bool(fin["ok"])
locked = BIR.lock(REPLIES, RPATH, OUT) if fin["ok"] else {"ok": False,
                                                          "problems": ["not finalized"]}
res["lock"] = {"ok": locked.get("ok"), "problems": (locked.get("problems") or [])[:6]}
checks["3_lock_accepts_the_proved_run"] = bool(locked.get("ok"))
# ---- the PUBLIC gate must refuse each concrete fault -------------------------
# Every case is a COPY of the proved run with exactly one thing wrong, so the
# refusal names that thing and nothing else.
import copy                                                      # noqa: E402
refusals = collections.OrderedDict()


def gate(name, mutate, replies=REPLIES, want=None):
    """One fault, in isolation, against a COMPLETE published output.

    The negative case is given the SAME four materialized artifacts as the
    proved positive, so a refusal can only come from the fault under test and
    never from an output that was never published (Codex SEQ 1895 item 2).
    """
    r = copy.deepcopy(receipt)
    mutate(r)
    path = os.path.join(ATT, "receipt_%s.json" % name)
    write_receipt(r, path)
    # the SAME published artifacts as the positive, and only those: the lock's
    # own output name must still be free, or a write-once refusal would stand
    # in for the fault under test.
    out = os.path.join(ATT, "locked_" + name)
    os.makedirs(out)
    for a_name in BIR.ARTIFACTS:
        shutil.copyfile(os.path.join(OUT, a_name), os.path.join(out, a_name))
    _a, probs, _rep = BIR.materialize(replies, path)
    if not probs:
        try:
            locked = BIR.lock(replies, path, out)
            probs = locked.get("problems") or []
        except Exception as exc:                      # noqa: BLE001 - by design
            probs = ["%s: %s" % (type(exc).__name__, exc)]
    refusals[name] = probs[:2]
    if want is not None:
        return bool(probs) and any(want in p for p in probs)
    return bool(probs)


victim = sorted(shipped)[0]
vi = [i for i, a in enumerate(receipt["attempts"])
      if a["source_id"] == victim][0]
si = [i for i, a in enumerate(receipt["attempts"])
      if a["task"] == "final_sign"][0]


def repeat_event(r):
    a = official("event", victim, BIR.prompt_text(victim),
                 io.open(os.path.join(REPLIES, r["attempts"][vi]["raw_name"]),
                         encoding="utf-8").read(),
                 "%s.TEST.attempt2.raw.json" % victim, vi, attempt=2)
    r["attempts"].insert(vi + 1, a)


def repeat_sign(r):
    a = official("final_sign", None, sign_prompt, sign_answer,
                 "final_sign.TEST.attempt2.raw.json", len(shipped), attempt=2)
    r["attempts"].append(a)


def wrong_prompt(r):
    other = sorted(shipped)[1]
    a = official("event", victim, BIR.prompt_text(other),
                 io.open(os.path.join(REPLIES, r["attempts"][vi]["raw_name"]),
                         encoding="utf-8").read(),
                 "%s.TEST.wrongprompt.raw.json" % victim, vi)
    r["attempts"][vi] = a


def wrong_raw(r):
    r["attempts"][vi] = dict(r["attempts"][vi],
                             raw_name=r["attempts"][vi + 1]["raw_name"])


def wrong_transcript(r):
    r["attempts"][vi] = dict(r["attempts"][vi],
                             agent_id=r["attempts"][vi + 1]["agent_id"])


def missing_result(r):
    r["attempts"].pop(vi)


checks["4_a_repeated_successful_event_is_refused"] = gate(
    "repeat_event", repeat_event,
    want="was retried although attempt 1 was not an invalid-format reply")
checks["5_a_repeated_successful_sign_is_refused"] = gate(
    "repeat_sign", repeat_sign,
    want="was retried although attempt 1 was not an invalid-format reply")
checks["6_a_wrong_prompt_is_refused"] = gate("wrong_prompt", wrong_prompt)
checks["7_a_wrong_raw_identity_is_refused"] = gate("wrong_raw", wrong_raw)
checks["8_a_wrong_transcript_identity_is_refused"] = gate("wrong_transcript", wrong_transcript)
checks["9_a_missing_required_result_is_refused"] = gate("missing_result", missing_result)

# bound-artifact drift: the lock re-derives every artifact and compares
drift_dir = os.path.join(ATT, "locked_drift")
shutil.copytree(OUT, drift_dir)
tgt = os.path.join(drift_dir, "final_inventory.json")
io.open(tgt, "a", encoding="utf-8").write("\n")
drifted = BIR.lock(REPLIES, RPATH, drift_dir)
refusals["artifact_drift"] = (drifted.get("problems") or [])[:2]
checks["10_bound_artifact_drift_is_refused"] = not drifted.get("ok")
res["refusals"] = refusals

res["checks"] = checks
ok = all(checks.values())
res["all_green"] = ok
out = os.path.join(ATT, "LIFECYCLE_%s.json" % TAG)
io.open(out, "w", encoding="utf-8").write(json.dumps(res, indent=2) + "\n")
print("owner %s" % hashlib.sha256(io.open(os.path.abspath(BIR.__file__), "rb").read()).hexdigest())
print("%d/%d -> %s" % (sum(1 for v in checks.values() if v), len(checks), ok))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
print("counts %s" % json.dumps(res.get("records", {})))
print("finalize %s  lock %s" % (res["finalize"], res["lock"]))
print("saved %s" % out)
sys.exit(0 if ok else 1)
