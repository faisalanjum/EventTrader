# -*- coding: utf-8 -*-
"""Codex SEQ 2012: independent review of final_scope / candidate_scope and
their direct consumers, in the frozen unit_2009 composite.

NO MODEL IS CALLED and NO completed TEST reply is regenerated: the finished
artifacts are consumed as evidence. Every mutation is made on a PRIVATE clone
served by this unit's own map, and each is restored with the positive re-run.
"""
import collections, contextlib, hashlib, io, json, os, sys
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_2012_final_join_review"
sys.path.insert(0, A + "/unit_2009/owner")
import a4_review_composite as R                                   # noqa: E402
CL, SK, K, HR, F, INV = R.CL, R.SK, R.K, R.HR, R.F, R.INV

# The POSITIVE is read from the completed originals, read-only: the pinned
# stage record embeds absolute paths, so a relocated clone cannot reproduce
# the package pins. Every MUTATION below is made on the clone instead.
ORIG = A + "/unit_2009/TEST_codex_join2009_a"
T = U + "/TEST_join_clone"
REVIEW, PKG = ORIG + "/review", ORIG + "/review_package"
KEY_RUN, KEY_PKG = ORIG + "/key_run", ORIG + "/key_package"
CANDIDATE, ORDINARY = ORIG + "/candidate", ORIG + "/ordinary_bound.json"
M_REVIEW, M_PKG = T + "/review", T + "/review_package"
os.environ["A7_ORDINARY_BOUND"] = ORDINARY
cases, counts, TOUCHED = [], collections.Counter(), set()


def case(name, got, want):
    ok = got == want
    counts["total"] += 1
    counts["passed" if ok else "failed"] += 1
    cases.append(collections.OrderedDict([("case", name), ("ok", ok)]
                 + ([] if ok else [("got", got), ("want", want)])))


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def outcome(fn):
    try:
        fn()
        return "ACCEPTED"
    except Exception as exc:                          # noqa: BLE001 - measured
        return "%s: %s" % (type(exc).__name__, str(exc)[:110])


@contextlib.contextmanager
def swapped(path, new_bytes):
    TOUCHED.add(path)
    keep = io.open(path, "rb").read() if os.path.isfile(path) else None
    try:
        if new_bytes is None:
            os.remove(path)
        else:
            io.open(path, "wb").write(new_bytes)
        yield
    finally:
        if keep is None:
            os.path.isfile(path) and os.remove(path)
        else:
            io.open(path, "wb").write(keep)


ORIG_BEFORE = {os.path.join(d, n): hashlib.sha256(
    io.open(os.path.join(d, n), "rb").read()).hexdigest()
    for d, _s, fs in os.walk(ORIG) for n in sorted(fs)}

res = collections.OrderedDict()
res["composite_under_review"] = fsha(R.__file__.rstrip("c"))
res["candidate_builder"] = fsha(A + "/unit_2005/owner/a4_source_candidate.py") \
    if os.path.isfile(A + "/unit_2005/owner/a4_source_candidate.py") else None

# ======================================================================
# POSITIVE: the completed join still holds, from the finished artifacts
# ======================================================================
merged, stages = R.merged_readings(REVIEW, PKG)
case("P1 all sixty-six review obligations are valid in the merge",
     [len(merged), sorted({v[0] for v in merged.values()})], [66, ["valid"]])
with R.final_scope(REVIEW, PKG) as proof:
    doc = SK.manifest()
    res["before_final_adjudication"] = doc["budget"]["before"]
    case("P2 both review stages are bound into the real key manifest",
         [doc["hard_review"]["stages"] == stages, doc["budget"]["before"]],
         [True, 499])
    case("P3 two independent leads per source, none omitted or foreign",
         [len(proof["by_source"]),
          sorted({len(v) for v in proof["by_source"].values()})], [33, [2]])
    resumed = SK.resume_plan(KEY_RUN, package=KEY_PKG)
    shards, raws, bad = SK.accepted_shards(KEY_RUN, package=KEY_PKG)
    key, sidecar, mbad = SK.materialize(shards)
    case("P4 the real resume owes nothing and the materializer is whole",
         [resumed["owed"], resumed["problems"], bad, mbad,
          SK.counts(key, sidecar)["rows_accounted"], len(shards)],
         [[], [], [], [], 191, 33])
with R.final_scope(REVIEW, PKG, bind_role=True):
    bound = SK.bound(KEY_RUN, KEY_PKG)
    case("P5 the existing signing gate accepts the completed TEST key",
         F.signing_gate(KEY_RUN, bound)["ok"], True)

identity = json.loads(io.open(CANDIDATE + "/key_identity.json",
                              encoding="utf-8").read())
runs = identity["runs"]
case("P6 every actual stage binds exactly once, no invented history",
     [len(runs), len(set(runs))], [5, 5])
rows = identity["bindings"]
paths = [r["path"] for r in rows.values()]
case("P7 no artifact is bound twice", len(paths), len(set(paths)))
case("P8 the saved-answer consumer keeps the original source-key binding",
     rows["initial_source_package"]["path"],
     os.path.join(SK.PKG_DIR, SK.MANIFEST_NAME))
case("P9 every bound artifact still hashes to its recorded bytes",
     [p for p, r in ((r["path"], r) for r in rows.values())
      if os.path.isfile(p) and fsha(p) != r["sha256"]], [])

# ======================================================================
# NEGATIVES: the bindings this join adds must be load-bearing
# ======================================================================
neg = collections.OrderedDict()

# 1. a FOREIGN preserved review named by the final phase
def foreign_final():
    with R.final_scope(REVIEW, PKG):
        CL.readings(KEY_RUN, KEY_PKG)          # not the preserved pair
neg["foreign preserved review at the final phase"] = outcome(foreign_final)

# 2. a FOREIGN preserved review named by the candidate
def foreign_candidate():
    with R.candidate_scope(REVIEW, PKG, KEY_RUN, KEY_PKG):
        CL.final_scope(KEY_RUN, KEY_PKG)
neg["foreign preserved review at the candidate"] = outcome(foreign_candidate)

# 3. a DIFFERENT candidate owner binding
def foreign_owner():
    sys.path.insert(0, A + "/unit_2005/owner")
    import a4_source_candidate as SC
    keep = SC.__file__
    SC.__file__ = "/tmp/not-the-approved-candidate.py"
    try:
        with R.candidate_scope(REVIEW, PKG, KEY_RUN, KEY_PKG):
            pass
    finally:
        SC.__file__ = keep
neg["a different candidate owner is loaded"] = outcome(foreign_owner)

# 4. an UNFINISHED new review stage
fin_new = os.path.join(M_REVIEW, K.FINALIZATION_NAME)
with swapped(fin_new, None):
    neg["the new review stage is unfinished"] = outcome(
        lambda: R.merged_readings(M_REVIEW, M_PKG))

# 5. an INVALID new review result
raw_new = os.path.join(M_REVIEW, "raw")
first_proved = sorted(n for n in os.listdir(raw_new)
                      if n.endswith(".proved.json"))[0]
with swapped(os.path.join(raw_new, first_proved), b'{"drifted": true}'):
    neg["a new review result no longer proves"] = outcome(
        lambda: R.merged_readings(M_REVIEW, M_PKG))

# 6. the new stage's own receipt removed
with swapped(os.path.join(M_REVIEW, K.RECEIPT_NAME), None):
    neg["the new stage receipt is gone"] = outcome(
        lambda: R.merged_readings(M_REVIEW, M_PKG))

res["negatives"] = neg
case("N1 every foreign, unfinished or invalid input refuses",
     [k for k, v in neg.items() if v == "ACCEPTED"], [])

# ======================================================================
# THE ADDED LEDGER CONNECTION, AND THE ADDED STAGE RECORD
# ======================================================================
with_new = F._ledger_before(R._prior(REVIEW))
without_new = F._ledger_before(R._prior(None))
res["clone_positive_is_path_bound"] = outcome(
    lambda: R.merged_readings(M_REVIEW, M_PKG))
res["ledger_before_with_new_stage"] = with_new
res["ledger_before_without_new_stage"] = without_new
case("L1 the new stage is actually counted in the key's own ledger",
     [with_new, with_new - without_new], [499, 4])

real_manifest = SK.manifest


def stage_record_dropped():
    """final_scope without its stages injection - is the record load-bearing?"""
    with R.final_scope(REVIEW, PKG) as p:
        with R._using(SK, manifest=real_manifest):
            d = SK.manifest()
            return ("hard_review" in d and "stages" in (d.get("hard_review") or {}),
                    SK.package_problems(KEY_PKG))


present, bad_without = stage_record_dropped()
res["stage_record_without_injection"] = {
    "stages_key_present": present, "package_problems": bad_without}
case("L2 removing the stages injection makes the REAL key package refuse",
     [present, bool(bad_without)], [False, True])
res["package_problems_without_the_injection"] = bad_without

def snap(root):
    return {os.path.join(d, n): fsha(os.path.join(d, n))
            for d, _s, fs in os.walk(root) for n in sorted(fs)}


res["originals_unchanged_by_this_review"] = snap(ORIG) == ORIG_BEFORE
case("Z1 the completed originals were only read, never written",
     res["originals_unchanged_by_this_review"], True)
res["counts"] = dict(counts)
res["failed"] = [c for c in cases if not c["ok"]]
res["cases"] = [c["case"] for c in cases]
res["clone_only"] = all(p.startswith(U) for p in TOUCHED)
res["files_this_battery_rewrote"] = sorted(
    os.path.relpath(p, U) for p in TOUCHED)
res["ok"] = not res["failed"] and res["clone_only"]
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
