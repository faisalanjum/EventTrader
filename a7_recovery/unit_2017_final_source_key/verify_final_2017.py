# -*- coding: utf-8 -*-
"""Codex SEQ 2017: READ-ONLY proof of the frozen 33-request packet.

Writes nothing, calls nothing. Every identity is re-measured from the file it
names, the owed results are read back through the unchanged owners, and each of
the 33 launch paths is proved to be the pinned script, read-only, with the
boundary's own refusals as positive controls.
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A7 + "/unit_2017_final_source_key"
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402
sys.path.insert(0, A7 + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402

CL, HR, K, SK, INV = R.CL, R.HR, R.K, R.SK, R.INV
checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


record = json.loads(io.open(os.environ["A7_PREP_RECORD"], encoding="utf-8").read())
PKG, RUN = record["package"], record["run"]
REVIEW_RUN, REVIEW_PKG = record["review_run"], record["review_package"]
MAP = os.environ["A7_PREP_MAP"]
LAUNCH = os.environ["A7_LAUNCH_DIR"]
res = collections.OrderedDict()
res["record"] = os.environ["A7_PREP_RECORD"]
res["record_sha256"] = fsha(os.environ["A7_PREP_RECORD"])

check("1 the owners it names re-measure",
      collections.OrderedDict([
          ("review_composite", fsha(R.__file__.rstrip("c"))),
          ("source_key", fsha(SK.__file__.rstrip("c"))),
          ("key_owner_role", fsha(SK.KEY_ROLE_FILE))]),
      collections.OrderedDict(
          (k, record["owners"][k]) for k in
          ("review_composite", "source_key", "key_owner_role")))
check("2 every package file re-measures",
      collections.OrderedDict((n, INV.sha_file(os.path.join(PKG, n)))
                              for n in sorted(os.listdir(PKG))),
      collections.OrderedDict(sorted(record["package_identity"].items())))
check("3 the receipt re-measures",
      INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME)), record["receipt_sha256"])
receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
check("4 the receipt still schedules exactly the 33, unserved",
      [receipt["allowed"], receipt["attempt"], receipt["states"]],
      [record["call_order"], 1, []])
check("5 no call has been made and the run cannot close",
      [os.path.isdir(os.path.join(RUN, "raw")),
       os.path.isfile(os.path.join(RUN, K.FINALIZATION_NAME)),
       os.path.isdir(os.path.join(RUN, "retry"))], [False, False, False])

# ------------------------------ the completed review stage is untouched -----
check("6 the completed review stage re-measures",
      [INV.sha_file(os.path.join(REVIEW_RUN, K.RECEIPT_NAME)),
       INV.sha_file(os.path.join(REVIEW_RUN, K.FINALIZATION_NAME)),
       INV.sha_file(os.path.join(REVIEW_PKG, CL.MANIFEST_NAME))],
      [record["review_stage"][k] for k in
       ("receipt_sha256", "finalization_sha256", "manifest_sha256")])
merged, _stages = R.merged_readings(REVIEW_RUN, REVIEW_PKG)
res["review_outcomes"] = dict(collections.Counter(v[0] for v in merged.values()))
check("7 all 66 review slots still read valid",
      [len(merged), res["review_outcomes"]],
      [record["review_stage"]["slots"], {"valid": 66}])

# --------------------------- the owed results, read back through the owner --
with R.final_scope(REVIEW_RUN, REVIEW_PKG) as proof:
    resume = SK.resume_plan(RUN, package=PKG)
    res["resume"] = collections.OrderedDict([
        ("owed", len(resume["owed"])), ("served", len(resume["served"])),
        ("problems", resume["problems"])])
    check("8 every one of the 33 results is still owed, none served",
          [len(resume["owed"]), len(resume["served"]), resume["problems"]],
          [33, 0, []])
    check("9 the package still re-derives and preflight is still clean",
          [SK.package_problems(PKG), SK.preflight(PKG)["ok"]], [[], True])
    check("10 two independent review leads per source, still 33 sources",
          [len(proof["by_source"]),
           sorted({len(v) for v in proof["by_source"].values()})], [33, [2]])

# ------------------------------------ the 33 launch paths are callable ------
rows = {r["logical"]: r for r in boundary.read_map(MAP)}
failures = []
for inv in record["invocations"]:
    name = os.path.basename(inv["scriptPath"])
    launch = os.path.join(LAUNCH, name)
    durable = os.path.join(RUN, "scripts", name)
    if not os.path.isfile(launch):
        failures.append([inv["label"], "unreadable"])
    elif io.open(launch, "rb").read() != io.open(durable, "rb").read():
        failures.append([inv["label"], "bytes differ from the durable script"])
    elif fsha(launch) != inv["script_sha256"]:
        failures.append([inv["label"], "not the pinned script"])
    elif not (os.statvfs(launch).f_flag & os.ST_RDONLY):
        failures.append([inv["label"], "not read-only"])
res["launch_failures"] = failures
check("11 all 33 launch paths carry the pinned script, read-only",
      [len(record["invocations"]), failures], [33, []])
check("12 the launch directory holds exactly those 33 scripts",
      sorted(os.listdir(LAUNCH)),
      sorted(os.path.basename(i["scriptPath"]) for i in record["invocations"]))
row = rows[LAUNCH]
check("13 the launch binding refuses a changed or missing source",
      [boundary.validate([row]),
       any("sha mismatch" in s for s in boundary.validate([dict(row, sha="0" * 64)])),
       any("missing bind target" in s for s in
           boundary.validate([dict(row, source=os.path.join(UNIT, "no-such-dir"))]))],
      [[], True, True])

# ----------------------------------------------- the accounting and role ----
manifest = K._load(os.path.join(PKG, SK.MANIFEST_NAME))
check("14 the frozen accounting is the one that was recorded",
      [manifest["budget"][k] for k in
       ("before", "planned_key_calls", "planned_signer", "after_planned",
        "worst_case_after", "calls_made_by_this_package")],
      [record["budget"][k] for k in
       ("before", "planned_key_calls", "planned_signer", "after_planned",
        "worst_case_after", "calls_made_by_this_package")])
check("15 the isolated key role is still the frozen non-Sonnet one",
      manifest["requested_key_role"], record["role"])
import a7_prepared_run as PR                                       # noqa: E402
res["a3_answer_run"] = PR._executed(os.path.abspath(K.a3_run_dirs()[0]))
check("16 the original 382 answers are untouched",
      res["a3_answer_run"]["run_files"], record["a3_answer_run"]["files"])

res["package"] = PKG
res["run"] = RUN
res["map_sha256"] = fsha(MAP)
res["checks"] = checks
res["passed"] = len(checks)
res["model_calls"] = 0
res["launched"] = 0
print(json.dumps(res, indent=1, default=str))
