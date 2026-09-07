# -*- coding: utf-8 -*-
"""Gap 1: run the affected test against each EXPLICITLY selected owner.

Equal exit codes are not equal causes, so this also captures each run's own
failure line and compares those.
"""
import collections, hashlib, io, json, os, re, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_1821"
OUT = "/tmp/a7_logs_1781"
TEST = "test_a7_runstates_1470.py"
OWNERS = collections.OrderedDict([
    ("original", H + "/a7_reference_inventory.py"),
    ("candidate", A + "/unit_1820/candidate/a7_reference_inventory.py")])
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

runs = []
for label, owner in OWNERS.items():
    rpt = "%s/PRELOAD_%s.json" % (OUT, label)
    r = subprocess.run(
        [sys.executable, "-B", U + "/ledger/preload_pytest_1821.py",
         owner, H + "/" + TEST, label],
        capture_output=True, text=True, cwd=H,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=H,
                 REPORT=rpt))
    doc = json.load(io.open(rpt, encoding="utf-8")) if os.path.isfile(rpt) else {}
    out = r.stdout or ""
    summary = [l for l in out.splitlines() if " passed" in l or " failed" in l]
    failed = sorted(set(re.findall(r"FAILED (\S+)", out)))
    cause = [l.strip() for l in out.splitlines() if l.strip().startswith("E ")]
    doc.update(collections.OrderedDict([
        ("wrapper_exit", r.returncode),
        ("pytest_summary", summary[-1] if summary else ""),
        ("failed_tests", failed),
        ("first_failure_cause", cause[0][:220] if cause else None),
        ("stdout_sha256", hashlib.sha256(out.encode("utf-8")).hexdigest()),
        ("stdout_bytes", len(out.encode("utf-8"))),
        ("stderr_bytes", len((r.stderr or "").encode("utf-8")))]))
    io.open("%s/GAP1_%s.json" % (OUT, label), "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    io.open("%s/GAP1_%s.stdout.txt" % (OUT, label), "w",
            encoding="utf-8").write(out)
    io.open("%s/GAP1_%s.stderr.txt" % (OUT, label), "w",
            encoding="utf-8").write(r.stderr or "")
    runs.append(doc)
    print("  %-10s owner %s  overrides %s -> held %s"
          % (label, doc["loaded_before"]["module_sha256"][:16],
             doc["loaded_before"]["overrides"],
             doc["owner_held_through_the_test"]))
    print("             build code file: %s"
          % doc["loaded_before"]["build_code_filename"])
    print("             pytest exit %s  %s" % (doc["exit"], doc["pytest_summary"]))
    print("             failed: %s" % (doc["failed_tests"] or "none"))

a, b = runs
same_cause = (a["failed_tests"] == b["failed_tests"]
              and a["first_failure_cause"] == b["first_failure_cause"])
different_owners = (a["loaded_before"]["module_sha256"]
                    != b["loaded_before"]["module_sha256"])
io.open(OUT + "/GAP1_COMPARISON.json", "w", encoding="utf-8").write(json.dumps(
    collections.OrderedDict([
        ("two_distinct_owners_were_actually_loaded", different_owners),
        ("original_sha256", a["loaded_before"]["module_sha256"]),
        ("candidate_sha256", b["loaded_before"]["module_sha256"]),
        ("same_exit", a["exit"] == b["exit"]),
        ("same_failed_test_set", a["failed_tests"] == b["failed_tests"]),
        ("same_first_failure_cause", same_cause),
        ("failure_is_pre_existing", same_cause),
        ("failure_caused_by_the_correction", not same_cause and different_owners)]),
    indent=1) + "\n")
print()
print("  two DIFFERENT owners actually loaded : %s" % different_owners)
print("  same failed test set                 : %s"
      % (a["failed_tests"] == b["failed_tests"]))
print("  same first failure CAUSE             : %s" % same_cause)
print("  -> the correction %s cause it" % ("did NOT" if same_cause else "DID"))
