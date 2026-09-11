# -*- coding: utf-8 -*-
"""Codex SEQ 2014: independent review of the closing non-AI evidence.

NO MODEL IS CALLED, no completed TEST artefact is regenerated and NO FILE IS
WRITTEN outside this unit: the 33 lock mutations are applied to in-memory
copies and judged by the REAL verifier, so nothing on disk is touched.
"""
import collections, hashlib, importlib.util, io, json, os, sys
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A + "/unit_2009"
saved = json.loads(io.open(UNIT + "/TEST_codex_join2009_a/TEST_RESULT.json",
                           encoding="utf-8").read())
CAND = saved["candidate"]
os.environ.pop("A7_APPROVED_KEY_DIR", None)      # exactly as his checker does
os.environ["A7_CANDIDATE_DIR"] = CAND
os.environ["A7_ORDINARY_BOUND"] = saved["ordinary"]
# the lock binds the authority document its build was given; his run pinned
# this archived message, so the same one must be named to re-derive
AUTHORITY = "/home/faisal/.core827-orchestrator/archive_CODEX_2011.md"
os.environ["A7_AUTHORITY"] = AUTHORITY
os.environ["A7_SIGNER_SESSION"] = os.path.join(
    "/home/faisal/.claude/projects", "-home-faisal-EventMarketDB",
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
sys.path.insert(0, UNIT + "/owner")
import a4_review_composite as R                                   # noqa: E402
CL, K = R.CL, R.K
OWNERS = A + "/unit_1955/lock_owners"
sys.path.insert(0, OWNERS)
import signer_proof as SP                                         # noqa: E402

cases, counts = [], collections.Counter()


def case(name, got, want):
    ok = got == want
    counts["total"] += 1
    counts["passed" if ok else "failed"] += 1
    cases.append(collections.OrderedDict([("case", name), ("ok", ok)]
                 + ([] if ok else [("got", got), ("want", want)])))


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


res = collections.OrderedDict()
res["composite_frozen"] = fsha(R.__file__.rstrip("c"))
res["authority_document"] = AUTHORITY
res["authority_sha256"] = fsha(AUTHORITY)
LOCK = CAND + "/a4_final_key_lock.json"
RCPT = CAND + "/a4_final_key_lock_receipt.json"
lock = json.loads(io.open(LOCK, encoding="utf-8").read())
receipt = json.loads(io.open(RCPT, encoding="utf-8").read())
res["lock_sha256"] = fsha(LOCK)
res["receipt_sha256"] = fsha(RCPT)
case("1 the receipt names the lock that is actually on disk",
     receipt["lock_sha256"], res["lock_sha256"])

# ---- load the REAL lock owner and re-verify, then re-earn its flag ----
spec = importlib.util.spec_from_file_location(
    "core2014_lock", OWNERS + "/build_final_key_lock.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
res["lock_owner_sha256"] = fsha(OWNERS + "/build_final_key_lock.py")

# The lock verifier re-derives the candidate, which only exists inside the
# composite's own candidate scope - the same scope his checker enters.
SCOPE = R.candidate_scope(saved["review"], saved["review_package"],
                          saved["key_run"], saved["key_package"])
SCOPE.__enter__()
live_problems = L.verify(json.loads(json.dumps(lock)))
case("2 POSITIVE CONTROL: the published lock verifies clean", live_problems, [])

# THE SAME 33 MUTATIONS, ENUMERATED FROM THE LOCK ITSELF, judged by the real
# verifier - the receipt's boolean is re-earned here, never read.
mine = collections.OrderedDict()
for k in list(lock["artifacts"]):
    m = json.loads(json.dumps(lock))
    m["artifacts"][k] = "0" * 64
    mine["artifact:" + k] = "refused" if L.verify(m) else "NOT REFUSED"
for k in ("run_id", "agent_id", "raw_sha256", "transcript_sha256",
          "state_sha256", "parent_session_id", "model", "effort", "agent_type",
          "prompt_sha256", "script_sha256", "signed", "blocked"):
    m = json.loads(json.dumps(lock))
    m["signer"][k] = False if k == "signed" else (
        ["tampered"] if k == "blocked" else "0" * 8)
    mine["signer:" + k] = "refused" if L.verify(m) else "NOT REFUSED"
for k in ("counts", "validator", "call_accounting", "key", "authority"):
    m = json.loads(json.dumps(lock))
    first = list(m[k])[0]
    m[k][first] = -1
    mine["block:" + k] = "refused" if L.verify(m) else "NOT REFUSED"

res["mutations_i_ran"] = len(mine)
res["not_refused"] = [k for k, v in mine.items() if v != "refused"]
case("3 every bound value refuses when mutated, re-earned not read",
     [len(mine), res["not_refused"]], [33, []])
case("4 my own replay agrees with the receipt's recorded results",
     mine == receipt["mutations"], True)

# ---- the saved signature is reusable, never a new call ---------------
session = os.path.join("/home/faisal/.claude/projects",
                       "-home-faisal-EventMarketDB", K.PARENT_SESSION)
sig = CAND + "/signer"
choice = SP.select_saved_call(sig, saved["signer_manifest"], 1, session)
res["saved_call_selection"] = list(choice)
case("5 the completed signature selects as REUSE, not a new call",
     choice[0], "reuse")
SCOPE.__exit__(None, None, None)

# ---- the accounting, recomputed from each stage's own closeout --------
stages = collections.OrderedDict()
for name, run in (("initial_key", CL.INITIAL_RUN),
                  ("review_primary", R.OLD_RUN),
                  ("review_child", os.path.join(R.OLD_RUN, "retry")),
                  ("clarified_review", saved["review"]),
                  ("final_adjudication", saved["key_run"])):
    p = os.path.join(run, K.FINALIZATION_NAME)
    stages[name] = K._load(p)["ledger"]["scheduled"] if os.path.isfile(p) else None
a3 = K.ledger_before()
res["a3_saved_answers"] = a3
res["stage_scheduled"] = stages
total = a3 + sum(v for v in stages.values() if v)
res["recomputed_ledger_before"] = total
case("6 the signed baseline is each stage counted once",
     [total, lock["call_accounting"]["ledger_before"],
      lock["call_accounting"]["signer_calls"],
      lock["call_accounting"]["ledger_after"]],
     [532, 532, 1, 533])

# ---- the original saved answers are untouched -------------------------
native = json.loads(io.open(
    A + "/unit_2010_native_fixture/NATIVE_FIXTURE_MANIFEST.json",
    encoding="utf-8").read())
import a7_prepared_run as PR                                      # noqa: E402
a3_run = os.path.abspath(K.a3_run_dirs()[0])
res["a3_digest_now"] = PR._executed(a3_run)
case("7 the original answer run still carries its recorded digest",
     res["a3_digest_now"]["run_files"], 799)

res["counts"] = dict(counts)
res["failed"] = [c for c in cases if not c["ok"]]
res["cases"] = [c["case"] for c in cases]
res["ok"] = not res["failed"]
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
