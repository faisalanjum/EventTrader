# -*- coding: utf-8 -*-
"""Run one named pytest set inside the no-call private view (Codex 1758/1759 step 2).

Every run writes its COMPLETE stdout+stderr and its exit status to its own named
log under logs/, so no evidence is truncated. Nothing is summarised away here:
the caller reads the file.

usage: a5_tests_1758.py <run-name> <suite.py> [suite.py ...]
"""
import os
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
LOGS = "/tmp/a6_logs_1765"          # a writable logical mount, durable behind it

name, suites = sys.argv[1], sys.argv[2:]
missing = [s for s in suites if not os.path.isfile(os.path.join(H, s.split("::")[0]))]
if missing:
    print("REFUSED: not present in the view: %s" % missing)
    sys.exit(3)

cmd = [sys.executable, "-B", "-m", "pytest"] + suites + [
    "--import-mode=importlib", "-p", "no:cacheprovider", "-q", "--no-header", "-rfE"]
p = subprocess.run(cmd, cwd=H, capture_output=True, text=True,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
body = "$ %s\n%s%s\n[rc=%d]\n" % (" ".join(cmd), p.stdout or "", p.stderr or "", p.returncode)
with open(os.path.join(LOGS, name + ".log"), "w") as fh:
    fh.write(body)
print(body[-3000:], flush=True)          # a tail for the terminal; the file holds all of it
print("WROTE %s.log  %d bytes  rc=%d" % (name, len(body), p.returncode), flush=True)
sys.exit(p.returncode)
