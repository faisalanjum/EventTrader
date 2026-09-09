# -*- coding: utf-8 -*-
"""The SIGNER carrier: the real manifest builder, then signer_proof.prove
EXECUTED against an isolated TEST signer call.

Named for what each row executes. Nothing is hand-written into the generated
signer manifest; the TEST state and transcript are authored here and are
clearly TEST, in this attempt's own store - never the official one.
"""
import collections
import hashlib
import io
import json
import os
import sys
import traceback

H = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/"
     "plans/Drivers/experiments/harness_g1v3")
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery")
ATT = os.environ["A7_ATTEMPT_DIR"]
OWN = os.environ.get("A7_LOCK_OWNERS")
if OWN:
    sys.path.insert(0, OWN)
PHASE = os.environ.get("A7_PHASE", "after")

import audit_worker_access as AUD                                  # noqa: E402
import build_inventory_review as BIR                               # noqa: E402
import build_kfields_key as K                                      # noqa: E402
import signer_proof as SP                                          # noqa: E402

ROWS = []
APPROVED, APPROVED_SHA = BIR.declared_lane_input()


def row(name, want, fn):
    try:
        got = fn()
        kind = ("empty" if got == [] or got == {} or got is None
                else "true" if got is True else "false" if got is False
                else "refuses")
        shown = json.dumps(got, default=str)[:500]
    except Exception as exc:                          # noqa: BLE001 - by design
        kind, shown = "raises", "%s: %s" % (type(exc).__name__, exc)
        io.open(os.path.join(ATT, "trace_%s.txt" % name), "w",
                encoding="utf-8").write(traceback.format_exc())
    ok = kind == want[0] and (len(want) < 2 or want[1] in shown)
    ROWS.append(collections.OrderedDict([("row", name), ("want", want[0]),
                                         ("got", kind), ("ok", ok),
                                         ("detail", shown)]))
    print("[%s] %-56s want=%-8s got=%-8s %s"
          % ("PASS" if ok else "FAIL", name, want[0], kind, shown[:140]))
    return ok


# ---------------------------------------------- the generated signer packet
# WHERE THE TEST LIFECYCLE'S OWN STATES LIVE, named by the run binding. The
# signer builder proves the A3 evidence of THAT fixture before it writes.
LIFE = os.environ.get("A7_LIFECYCLE_ROOT", "/tmp/a7_logs_1781/lifecycle")
AUD.PROJECTS_ROOT = os.path.join(LIFE, "TEST_projects")
SIGN_OUT = os.path.join(ATT, "sign_pkg")


def _build_signer():
    import build_final_key_candidate as C
    C.build(SIGN_OUT)
    man = json.load(io.open(os.path.join(SIGN_OUT, "signer",
                                         "signer.manifest.json"),
                            encoding="utf-8"))
    return {"expected_input": man.get("expected_input"),
            "expected_input_source": man.get("expected_input_source")}


row("build_final_key_candidate_build__signer_manifest_carries_declaration",
    ("refuses", APPROVED["payload_sha256"]) if PHASE == "after"
    else ("refuses", '"expected_input": null'), _build_signer)

# ---------------------------------------------- an isolated TEST signer call
STORE = os.path.join(ATT, "TEST_projects")
SESS = os.path.join(STORE, "TESTproj1955", K.PARENT_SESSION)
RUN_ID = "wf_TEST1955signer"
AGENT = "TEST1955signeragent"
os.makedirs(os.path.join(SESS, "workflows"), exist_ok=True)
TDIR = os.path.join(SESS, "subagents", "workflows", RUN_ID)
os.makedirs(TDIR, exist_ok=True)
# AND NOW THIS ATTEMPT'S OWN TEST SIGNER STORE, for the proof rows below.
AUD.PROJECTS_ROOT = STORE


def _sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _write_call(with_declared=True):
    """The TEST signer call: one state and one child transcript, in the exact
    shape signer_proof.prove reads. Every constant comes from the owners
    (SP.LABEL, F.SIGNER_RESULT_FIELDS, K.MODEL/EFFORT/AGENT_TYPE) and the ONE
    input record comes from the approved declaration, never authored here."""
    import build_kfields_final as F
    import g1_fake_state as FAKE
    man = json.load(io.open(os.path.join(SIGN_OUT, "signer",
                                         "signer.manifest.json"),
                            encoding="utf-8"))
    prompt, script, bad = SP.packet(os.path.join(SIGN_OUT, "signer"), man, 1)
    assert not bad, bad
    answer = io.open(ANSWER_PATH, encoding="utf-8").read()
    tdir = os.path.join(SESS, "subagents", "workflows", RUN_ID)
    os.path.isdir(tdir) or os.makedirs(tdir)
    FAKE._transcript(tdir, AGENT, os.path.basename(SESS), prompt, answer,
                     FAKE.declared_input_record() if with_declared else None)
    result = collections.OrderedDict(
        [(f, {"role": "signer", "attempt": 1, "model": K.MODEL,
              "effort": K.EFFORT, "agentType": K.AGENT_TYPE,
              "text": answer}.get(f)) for f in F.SIGNER_RESULT_FIELDS])
    body = {"runId": RUN_ID, "status": "completed", "script": script,
            "totalToolCalls": 0,
            "workflowProgress": [
                {"type": "workflow_phase", "index": 1, "title": "SIGN"},
                {"type": "workflow_agent", "index": 1, "label": SP.LABEL,
                 "phaseIndex": 1, "phaseTitle": "SIGN", "agentId": AGENT,
                 "agentType": K.AGENT_TYPE, "model": K.RUNTIME_MODEL_ID,
                 "effort": K.EFFORT, "state": "done", "attempt": 1,
                 "toolCalls": 0, "promptPreview": prompt[:200],
                 "startedAt": 1, "lastProgressAt": 2, "tokens": 1}],
            "result": result}
    path = os.path.join(SESS, "workflows", RUN_ID + ".json")
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    return man, path


ANSWER_PATH = os.path.join(ATT, "TEST_signer_answer.json")
io.open(ANSWER_PATH, "w", encoding="utf-8").write("{}")


def _prove(man_override=None, with_declared=True):
    man, _state = _write_call(with_declared)
    if man_override is not None:
        man = dict(man)
        man.update(man_override)
    proof, why = SP.prove(os.path.join(SIGN_OUT, "signer"), man, 1, RUN_ID,
                          SESS, {})
    return [str(w)[:200] for w in (why or [])][:4]


row("SP_prove__positive_with_the_generated_manifest",
    ("empty",), lambda: _prove())
row("SP_prove__refuses_an_unapproved_declaration_in_the_manifest",
    ("refuses", "served approved"),
    lambda: _prove({"expected_input_source": {"path": "/tmp/not_served",
                                              "sha256": "0" * 64}}))
row("SP_prove__refuses_when_the_declared_input_is_omitted",
    ("refuses", "not at record"), lambda: _prove(with_declared=False))
row("SP_prove__restored_positive_after_those_mutations",
    ("empty",), lambda: _prove())

text = json.dumps(ROWS, indent=2)
io.open(os.path.join(ATT, "SIGNER_%s.json" % PHASE), "w",
        encoding="utf-8").write(text + "\n")
n_ok = sum(1 for r in ROWS if r["ok"])
print("%d/%d signer rows as expected (phase %s)" % (n_ok, len(ROWS), PHASE))
raise SystemExit(0 if n_ok == len(ROWS) else 1)
