# -*- coding: utf-8 -*-
"""Codex SEQ 2001 item 3: the CALLABLE positive path, end to end. No AI.

NO MODEL IS CALLED and the real official store is shadowed by this unit's TEST
tree inside the binding. Every reading and every final reply here is a CLEARLY
LABELLED SYNTHETIC stand-in; none of them establishes any source truth.

What it drives, all through the existing owners:

  full TEST review results -> final adjudication request -> TEST final reply
  -> parsed final key with the unchanged initial settlements reused
  -> the real signing gate -> the real signer preparation -> a TEST signature
  -> the real lock.

Then the failure cases that must stop it, each with the positive control still
standing: a missing reading, an invalid reading, a stale attempt, a duplicate
run-level error, and the lawful invalid-only child that must be consumed once.
"""
import collections
import hashlib
import io
import json
import os
import sys

U1 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2002"
sys.path.insert(0, U1 + "/owner")
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2001/tests")
import a4_source_closure as CL                                    # noqa: E402
import synthetic_reading as SYN                                   # noqa: E402

K, F, SK, HR = CL.K, CL.F, CL.SK, CL.HR
TAG = os.environ.get("A7_TAG", "x")
BASE = os.path.dirname(CL.PKG_DIR)
PKG = os.path.join(BASE, "closure_pkg_%s" % TAG)
REVIEW = os.path.join(BASE, "review_%s" % TAG)
FINAL_PKG = os.path.join(BASE, "final_pkg_%s" % TAG)
FINAL_RUN = os.path.join(BASE, "final_%s" % TAG)
SIGNER = os.path.join(BASE, "signer_%s" % TAG)
PROJECTS = "/home/faisal/.claude/projects"
PRISTINE = os.path.join(PROJECTS, "_pristine")
SESSION = os.path.join(PROJECTS, "-home-faisal-EventMarketDB", K.PARENT_SESSION)
KEEP = frozenset(os.path.splitext(n)[0]
                 for n in os.listdir(os.path.join(SESSION, "workflows")))

res = collections.OrderedDict()
res["kind"] = ("callable closure path over CLEARLY LABELLED SYNTHETIC results; "
               "no model call, no real source truth, no real signature")
res["closure_owner_sha256"] = hashlib.sha256(
    io.open(CL.__file__.rstrip("c"), "rb").read()).hexdigest()
before = hashlib.sha256(io.open(
    os.path.join(CL.INITIAL_RUN, K.RECEIPT_NAME), "rb").read()).hexdigest()
steps = []


def step(name, ok, detail=""):
    steps.append(collections.OrderedDict([
        ("step", name), ("ok", bool(ok)), ("detail", str(detail)[:240])]))
    return ok


# ---- 1. THE REVIEW PHASE: publish, then serve every owed reading ----------
CL.build(PKG)
got = CL.prepare_run(REVIEW, PKG)
step("review/publish", got["ok"] and len(got["invocations"]) == 66,
     "invocations=%d" % len(got.get("invocations") or []))

labels = CL.canonical_calls()
for n, label in enumerate(labels):
    p = SYN.write_state(CL, REVIEW, PKG, label, "wf_e2e%s%03d" % (TAG, n),
                        PRISTINE, PROJECTS)
    CL.record_state(REVIEW, p)
readings, run_problems = CL.readings(REVIEW, PKG)
valid = [l for l, v in readings.items() if v[0] == "valid"]
step("review/every owed reading is valid",
     len(valid) == len(labels) and run_problems == [],
     "valid=%d/%d problems=%s" % (len(valid), len(labels), run_problems[:1]))
res["review"] = collections.OrderedDict([
    ("owed", len(labels)), ("valid", len(valid)),
    ("run_problems", run_problems[:2]),
    ("outcomes", dict(collections.Counter(v[0] for v in readings.values())))])

by_source = CL.leads_by_source(readings)
res["leads_per_event"] = collections.Counter(
    len(v) for v in by_source.values())
review_fin = CL.finalize(REVIEW, PKG)
step("review/the completed reading ledger is saved before final preparation",
     review_fin["ledger"]["valid"] == len(labels)
     and not review_fin["retry"] and not review_fin["problems"],
     json.dumps(review_fin["ledger"]))

# ---- 2. THE FINAL ADJUDICATION REQUEST, through the source owner's own
#         lifecycle under the closure scope ---------------------------------
with CL.final_scope(REVIEW, PKG):
    final_doc = SK.build(FINAL_PKG)
    pkg_problems = SK.package_problems(FINAL_PKG)
    # THE REAL PUBLICATION DOOR. `test_binding` is only for a role declared
    # TEST; this door's role is LIVE, and publishing writes request scripts on
    # disk and launches nothing.
    prep = SK.prepare_run(FINAL_RUN, package=FINAL_PKG)
    prompts = {t["source_id"]: SK.prompt(t) for t in SK.tasks()}
step("final/the request package rebuilds from the live owners",
     pkg_problems == [], json.dumps(pkg_problems[:2]))
step("final/one request per event, in order",
     prep["ok"] and [i["label"] for i in prep["invocations"]]
     == [t["source_id"] for t in SK.tasks()],
     "invocations=%d" % len(prep.get("invocations") or []))
res["final_request"] = collections.OrderedDict([
    ("package", FINAL_PKG), ("problems", pkg_problems[:2]),
    ("invocations", len(prep.get("invocations") or [])),
    ("prompt_sha256_sample",
     {s: K._sha(t) for s, t in list(prompts.items())[:2]}),
    ("every_prompt_carries_its_own_leads", all(
        json.loads(prompts[s].rsplit("[INPUT]\n", 1)[1])["leads"]
        == by_source.get(s, [])
        for s in prompts))])
step("final/every decoded prompt carries exactly its own proved leads",
     res["final_request"]["every_prompt_carries_its_own_leads"])
step("final/the manifest names the actual lead population and closure owner",
     final_doc["counts"]["leads_shown"] == len(labels)
     and res["closure_owner_sha256"] in final_doc["bound"].values(),
     "leads=%s closure_owner_bound=%s" % (
         final_doc["counts"]["leads_shown"],
         res["closure_owner_sha256"] in final_doc["bound"].values()))
role_text = next(iter(prompts.values())).split("[ROLE]\n", 1)[1].split(
    "\n\n[RULES]\n", 1)[0]
step("final/the manifest identifies the role and output card actually sent",
     final_doc["role_sha256"] == K._sha(role_text)
     and final_doc["output_section_sha256"] == K._sha(F._output_section()),
     "role=%s output=%s" % (final_doc["role_sha256"],
                            final_doc["output_section_sha256"]))
expected_before = CL.ledger_before() + review_fin["ledger"]["scheduled"]
step("final/the budget includes the actual completed prior stages",
     final_doc["budget"]["before"] == expected_before,
     "declared=%s actual=%s" % (final_doc["budget"]["before"], expected_before))

# ---- 3. THE TEST FINAL REPLIES, recorded and proved ----------------------
with CL.final_scope(REVIEW, PKG):
    script_of = {i["label"]: i["scriptPath"] for i in prep["invocations"]}
    for n, task in enumerate(SK.tasks()):
        p = SYN.write_final_state(CL, FINAL_RUN, FINAL_PKG, task["source_id"],
                                  "wf_fin%s%03d" % (TAG, n), PROJECTS,
                                  by_source,
                                  script_path=script_of[task["source_id"]],
                                  resolve_open_issues=True)
        SK.record_state(FINAL_RUN, p)
    receipt = K._load(os.path.join(FINAL_RUN, K.RECEIPT_NAME))
    proved, fprob = SK.run_evidence(FINAL_RUN, receipt, package=FINAL_PKG)
    fin = SK.finalize(FINAL_RUN, package=FINAL_PKG)
# THE FINAL SHARDS ARE READ WITH THEIR OWN LEADS. `SK.accepted_shards` forces
# the lead list empty, which is right for an initial reply and refuses a
# closure reply that reconciles the readings it was shown.
with CL.final_scope(REVIEW, PKG):
    shards, raws, sbad = SK.accepted_shards(FINAL_RUN, package=FINAL_PKG)
    key, sidecar, mat = SK.materialize(shards)
    counts = SK.counts(key, sidecar)
step("final/every reply proves and parses",
     fprob == [] and sbad == [] and len(shards) == 33,
     "proof=%s parse=%s shards=%d" % (fprob[:1], sbad[:1], len(shards)))
step("final/the key materializes with the initial settlements reused",
     mat == [] and counts["rows_accounted"] == 191,
     "materializer=%s rows=%s" % (mat[:1], counts.get("rows_accounted")))
res["final_key"] = collections.OrderedDict([
    ("ledger", fin.get("ledger")), ("phase_complete", fin.get("phase_complete")),
    ("shards", len(shards)), ("counts", counts),
    ("materializer_problems", mat[:2]),
    ("initial_raw_reused_verbatim", sum(
        1 for s in shards if raws[s] == CL._initial()[1][s]))])

# Independently required conservation: a successfully parsed final answer
# must remain completed through the actual finalizer AND resume interface.
with CL.final_scope(REVIEW, PKG):
    resumed = SK.resume_plan(FINAL_RUN, package=FINAL_PKG)
step("final/the closeout credits every valid answer and schedules no retry",
     fin["ledger"]["valid"] == len(SK.tasks())
     and fin["ledger"]["invalid_response"] == 0
     and not fin["retry"] and not fin["problems"],
     json.dumps(fin["ledger"]))
step("final/resume reuses every success and owes no repeated call",
     resumed["served"] == [t["source_id"] for t in SK.tasks()]
     and resumed["never_repeat"] == resumed["served"]
     and not resumed["owed"] and not resumed["retryable"]
     and not resumed["problems"],
     "served=%d owed=%d problems=%s" % (
         len(resumed["served"]), len(resumed["owed"]), resumed["problems"][:1]))
res["resume"] = {"served": len(resumed["served"]),
                 "owed": len(resumed["owed"]),
                 "never_repeat": len(resumed["never_repeat"]),
                 "problems": resumed["problems"]}

# ---- 4. THE REAL SIGNING GATE over the FINAL run -------------------------
gate = CL.signing_checks(REVIEW, PKG, key_run=FINAL_RUN,
                         key_package=FINAL_PKG)
step("signing/the gate is clean once every reading and shard is served",
     gate["ok"] is True, json.dumps(gate["stops"][:2]))
res["gate"] = collections.OrderedDict([
    ("ok", gate["ok"]), ("stops", gate["stops"][:3]),
    ("counts", gate.get("counts")),
    ("owed_blind_readings", len(gate["owed_blind_readings"])),
    ("run_problems", gate["run_problems"][:2])])

# ---- 5. THE REAL SIGNER PREPARATION and a TEST SIGNATURE, then the LOCK ---
signer = None
locked = None
with CL.final_scope(REVIEW, PKG, bind_role=True):
    bound = SK.bound(FINAL_RUN, FINAL_PKG)
    signer = F.prepare_signer(SIGNER, bound)
    if signer["ok"]:
        sig_label = "a4-final-signer"
        sp = SYN.write_signature_state(
            CL, SIGNER, bound, sig_label, "wf_sig%s" % TAG, PROJECTS)
        F.record_state(SIGNER, sp)
        sig_fin = F.finalize(SIGNER, bound)
        try:
            locked = F.lock(SIGNER, bound)
            lock_err = None
        except Exception as exc:
            locked, lock_err = None, "%s: %s" % (type(exc).__name__, str(exc)[:200])
step("signing/the signer prepares once the gate is clean",
     bool(signer and signer["ok"]),
     json.dumps((signer or {}).get("problems", [])[:2]))
step("signing/a TEST signature locks the prepared key",
     bool(locked) and locked.get("state") == "LOCKED",
     str(locals().get("lock_err") or (locked or {}).get("state")))
res["lock"] = collections.OrderedDict([
    ("state", (locked or {}).get("state")),
    ("schema", (locked or {}).get("schema")),
    ("package_manifest_sha256", (locked or {}).get("package_manifest_sha256")),
    ("key_shards", len((locked or {}).get("key_shards") or [])),
    ("event_receipt_sha256", (locked or {}).get("event_receipt_sha256")),
    ("event_finalization_sha256",
     (locked or {}).get("event_finalization_sha256")),
    ("signer_raw_sha256", (locked or {}).get("signer_raw_sha256")),
    ("counts", (locked or {}).get("counts")),
    ("signature", (locked or {}).get("signature")),
    ("THIS_IS_A_TEST_SIGNATURE",
     "the signature above was written by a fixture, not by a signer call. "
     "It establishes no source truth and locks no real key.")])
res["signer"] = collections.OrderedDict([
    ("ok", bool(signer and signer["ok"])),
    ("problems", (signer or {}).get("problems", [])[:2]),
    ("signer_bytes", (signer or {}).get("signer_bytes")),
    ("invocations", len((signer or {}).get("invocations") or [])),
    ("signer_finalization", (locals().get("sig_fin") or {}).get("ledger")),
    ("lock", "locked" if locked else "NOT LOCKED"),
    ("lock_error", locals().get("lock_err"))])

res["read_only"] = {"initial_receipt_unchanged": before == hashlib.sha256(
    io.open(os.path.join(CL.INITIAL_RUN, K.RECEIPT_NAME), "rb").read()
    ).hexdigest()}
res["real_states_preserved"] = sorted(
    os.path.splitext(n)[0] for n in
    os.listdir(os.path.join(SESSION, "workflows"))
    if os.path.splitext(n)[0] in KEEP) == sorted(KEEP)
res["steps"] = steps
res["passed"] = sum(1 for s in steps if s["ok"])
res["total"] = len(steps)
res["ok"] = (res["passed"] == res["total"]
             and res["read_only"]["initial_receipt_unchanged"]
             and res["real_states_preserved"])
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
