# -*- coding: utf-8 -*-
"""Is the one failing test caused by this correction, or already failing?

Runs the SAME single test twice: once with the untouched owner, once with the
corrected candidate first on the path. Only the comparison can say whether the
data addition caused it.
"""
import io, json, os, subprocess, sys, collections
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
U = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1820"
OUT = "/tmp/a7_logs_1781"
T = "test_a7_runstates_1470.py::test_a_mutation_after_identity_capture_refuses_before_any_answer"


def run(label, pypath):
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", T],
                       capture_output=True, text=True, cwd=H,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                                PYTHONPATH=pypath))
    line = [l for l in (r.stdout or "").splitlines() if "passed" in l or "failed" in l]
    print("  %-22s exit %d   %s" % (label, r.returncode, line[-1] if line else ""))
    return collections.OrderedDict([
        ("label", label), ("exit", r.returncode),
        ("summary", line[-1] if line else ""),
        ("assert_lines", [l.strip() for l in (r.stdout or "").splitlines()
                          if l.strip().startswith(("E ", "assert"))][:4])])


a = run("ORIGINAL owner", H)
b = run("corrected candidate", U + "/candidate:" + H)
same = a["exit"] == b["exit"]
print("  same outcome either way: %s  -> the correction %s cause it"
      % (same, "did NOT" if same else "DID"))
io.open(OUT + "/BASELINE_TEST_1820.json", "w", encoding="utf-8").write(
    json.dumps(collections.OrderedDict([
        ("test", T), ("original", a), ("candidate", b),
        ("identical_outcome", same),
        ("caused_by_this_correction", not same)]), indent=1) + "\n")
for l in a["assert_lines"]:
    print("    original says: %s" % l)
