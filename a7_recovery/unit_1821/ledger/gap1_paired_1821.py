# -*- coding: utf-8 -*-
"""Gap 1, completed: the affected test with each owner served ITS OWN document."""
import collections, hashlib, io, json, os, re, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U, OUT = A + "/unit_1821", "/tmp/a7_logs_1781"
FROZEN = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
          "targeted_1589/post_1500_exact_1626/budget_inputs_1720/out_g23/"
          "tmp__a7_reference_inventory.json")
TEST = H + "/test_a7_runstates_1470.py"
SIDES = [("original_paired", H + "/a7_reference_inventory.py", FROZEN),
         ("candidate_paired", A + "/unit_1820/candidate/a7_reference_inventory.py",
          OUT + "/candidate_reference_inventory.json")]
runs = []
for label, owner, inv in SIDES:
    rpt = "%s/PRELOAD_%s.json" % (OUT, label)
    r = subprocess.run([sys.executable, "-B", U + "/ledger/preload_pytest_1821.py",
                        owner, TEST, label, inv],
                       capture_output=True, text=True, cwd=H,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                PYTHONPATH=H, REPORT=rpt))
    doc = json.load(io.open(rpt, encoding="utf-8"))
    out = r.stdout or ""
    summ = [l for l in out.splitlines() if " passed" in l or " failed" in l]
    doc.update(collections.OrderedDict([
        ("inventory_served", inv),
        ("pytest_summary", summ[-1] if summ else ""),
        ("failed_tests", sorted(set(re.findall(r"FAILED (\S+)", out)))),
        ("first_failure_cause",
         next((l.strip()[:200] for l in out.splitlines()
               if l.strip().startswith("E ")), None)),
        ("stdout_sha256", hashlib.sha256(out.encode("utf-8")).hexdigest())]))
    io.open("%s/GAP1P_%s.json" % (OUT, label), "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    io.open("%s/GAP1P_%s.stdout.txt" % (OUT, label), "w", encoding="utf-8").write(out)
    runs.append(doc)
    print("  %-17s owner %s  inv %s" % (label, doc["loaded_before"]["module_sha256"][:16],
                                        hashlib.sha256(io.open(inv, "rb").read())
                                        .hexdigest()[:16]))
    print("      held %s   exit %s   %s" % (doc["owner_held_through_the_test"],
                                            doc["exit"], doc["pytest_summary"]))
    print("      failed: %s" % [f.split("::")[-1] for f in doc["failed_tests"]] or "none")
a, b = runs
same = (a["failed_tests"] == b["failed_tests"]
        and a["first_failure_cause"] == b["first_failure_cause"])
io.open(OUT + "/GAP1_PAIRED_COMPARISON.json", "w", encoding="utf-8").write(json.dumps(
    collections.OrderedDict([
        ("distinct_owners_loaded",
         a["loaded_before"]["module_sha256"] != b["loaded_before"]["module_sha256"]),
        ("distinct_documents_served",
         a["inventory_served"] != b["inventory_served"]),
        ("same_failed_test_set", a["failed_tests"] == b["failed_tests"]),
        ("same_first_failure_cause",
         a["first_failure_cause"] == b["first_failure_cause"]),
        ("failure_is_pre_existing", same),
        ("caused_by_the_correction", not same)]), indent=1) + "\n")
print()
print("  same failed set: %s   same cause: %s   -> the correction %s cause it"
      % (a["failed_tests"] == b["failed_tests"],
         a["first_failure_cause"] == b["first_failure_cause"],
         "did NOT" if same else "DID"))
