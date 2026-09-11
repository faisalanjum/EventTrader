# -*- coding: utf-8 -*-
"""Codex SEQ 2015: READ-ONLY proof of the frozen four-request packet.

Writes nothing, calls nothing. Every identity is re-measured from the file it
names, every outcome is read back through the unchanged owners, and each of
the four launch paths is proved to be the pinned script, read-only, with the
boundary's own refusals as positive controls.
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = os.path.join(A7, "unit_2015_real_reviews")
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402
sys.path.insert(0, os.path.join(A7, "unit_2009/owner"))
import a4_review_composite as R                                    # noqa: E402

CL, HR, K, INV = R.CL, R.HR, R.K, R.INV
checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


record = json.loads(io.open(os.environ["A7_PREP_RECORD"], encoding="utf-8").read())
PKG, RUN = record["package"], record["run"]
res = collections.OrderedDict()
res["record"] = os.environ["A7_PREP_RECORD"]
res["record_sha256"] = fsha(os.environ["A7_PREP_RECORD"])

# ------------------------------------------------- 1. the owners it names ---
check("1 the composite owner re-measures", fsha(R.__file__.rstrip("c")),
      record["owners"]["review_composite"])
check("2 the clarified hard-review owner re-measures",
      fsha(HR.__file__.rstrip("c")), record["owners"]["clarified_hard_review"])
check("3 the preserved hard-review owner re-measures",
      fsha(str(R.OLD_OWNER_PATH)), record["owners"]["preserved_hard_review"])

# ------------------------------------------- 2. the package and the receipt -
check("4 every package file re-measures",
      collections.OrderedDict((n, INV.sha_file(os.path.join(PKG, n)))
                              for n in sorted(os.listdir(PKG))),
      collections.OrderedDict(sorted(record["package_identity"].items())))
check("5 the receipt re-measures",
      INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME)), record["receipt_sha256"])
receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
check("6 the receipt still schedules exactly the four, unserved",
      [receipt["allowed"], receipt["attempt"], receipt["states"]],
      [[i["label"] for i in record["invocations"]], 1, []])
check("7 no call has been made and the run cannot close",
      [os.path.isdir(os.path.join(RUN, "raw")),
       os.path.isfile(os.path.join(RUN, K.FINALIZATION_NAME)),
       os.path.isdir(os.path.join(RUN, "retry"))], [False, False, False])

# -------------------------- 3. the outcomes, read back through the owners ---
with R._current_scope():
    new_got, new_bad = CL.readings(RUN, PKG)
res["new_run_outcomes"] = dict(collections.Counter(v[0] for v in new_got.values()))
res["new_run_problems"] = new_bad
check("8 every owed reading is visibly MISSING, with no run problem",
      [res["new_run_outcomes"], new_bad, sorted(new_got)],
      [{"missing": 4}, [], sorted(i["label"] for i in record["invocations"])])

old, stage = R.old_readings()
res["preserved_outcomes"] = dict(collections.Counter(v[0] for v in old.values()))
check("9 the preserved review is untouched: 62 valid, 4 invalid",
      res["preserved_outcomes"], {"valid": 62, "invalid_response": 4})
check("10 the preserved receipts and package re-measure",
      [INV.sha_file(os.path.join(R.OLD_RUN, K.RECEIPT_NAME)),
       INV.sha_file(os.path.join(R.OLD_RUN, K.FINALIZATION_NAME)),
       INV.sha_file(os.path.join(R.OLD_RUN, "retry", K.RECEIPT_NAME)),
       INV.sha_file(os.path.join(R.OLD_PKG, CL.MANIFEST_NAME))],
      [record["preserved"][k] for k in
       ("receipt_sha256", "finalization_sha256", "retry_receipt_sha256",
        "manifest_sha256")])

# ----------------------------------- 4. the four launch paths are callable --
MAP = os.environ["A7_PREP_MAP"]
rows = {r["logical"]: r for r in boundary.read_map(MAP)}
LAUNCH = os.environ["A7_LAUNCH_DIR"]
failures = []
for inv in record["invocations"]:
    name = os.path.basename(inv["scriptPath"])
    launch, durable = os.path.join(LAUNCH, name), os.path.join(RUN, "scripts", name)
    if not os.path.isfile(launch):
        failures.append([inv["label"], "unreadable"])
    elif io.open(launch, "rb").read() != io.open(durable, "rb").read():
        failures.append([inv["label"], "bytes differ from the durable script"])
    elif fsha(launch) != inv["script_sha256"]:
        failures.append([inv["label"], "not the pinned script"])
    elif not (os.statvfs(launch).f_flag & os.ST_RDONLY):
        failures.append([inv["label"], "not read-only"])
res["launch_failures"] = failures
check("11 all four launch paths carry the pinned script, read-only",
      [len(record["invocations"]), failures], [4, []])
check("12 the launch directory holds exactly those four scripts",
      sorted(os.listdir(LAUNCH)),
      sorted(os.path.basename(i["scriptPath"]) for i in record["invocations"]))
row = rows[LAUNCH]
check("13 the launch binding refuses a changed or missing source",
      [boundary.validate([row]),
       any("sha mismatch" in s for s in boundary.validate([dict(row, sha="0" * 64)])),
       any("missing bind target" in s for s in
           boundary.validate([dict(row, source=os.path.join(UNIT, "no-such-dir"))]))],
      [[], True, True])

# ----------------------------------------------- 5. the accounting and pins -
check("14 the call accounting is the one that was frozen",
      [record["accounting"][k] for k in
       ("historical_total", "new_primaries", "after_primaries",
        "worst_case_after")], [495, 4, 499, 503])
check("15 the transport is Sonnet 5 at high effort, 128000 output tokens",
      [record["transport"]["model_alias"], record["transport"]["runtime_model_id"],
       record["transport"]["effort"], record["runtime"]["max_output_tokens"]],
      ["sonnet", "claude-sonnet-5", "high", 128000])
import a7_prepared_run as PR                                       # noqa: E402
res["a3_answer_run"] = PR._executed(os.path.abspath(K.a3_run_dirs()[0]))
check("16 the original answer run is still 799 files",
      res["a3_answer_run"]["run_files"], record["a3_answer_run"]["files"])

res["package"] = PKG
res["run"] = RUN
res["map_sha256"] = fsha(MAP)
res["checks"] = checks
res["passed"] = len(checks)
res["model_calls"] = 0
res["launched"] = 0
print(json.dumps(res, indent=1, default=str))
