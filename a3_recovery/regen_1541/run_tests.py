#!/usr/bin/env python3
"""Run the suite once and SAVE the result, so the send gate can read it.

A claim that re-runs the test or mutation programs is not read-only: it rewrites the
reports and can leave a manifested file changed, which is exactly how the package
stopped matching the manifest it had just been frozen against.
"""
import io
import json
import os
import re
import subprocess
import sys

R = os.path.dirname(os.path.abspath(__file__))
PY = "/home/faisal/EventMarketDB/venv/bin/python"

out = subprocess.run(
    [PY, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
     "--basetemp=" + os.path.join(R, ".pt"), "--import-mode=importlib"],
    capture_output=True, text=True, cwd=R,
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
tail = out.stdout.strip().split("\n")[-1]
passed = int(re.search(r"(\d+) passed", out.stdout).group(1))
failed = int((re.search(r"(\d+) failed", out.stdout) or [0, "0"])[1])
rep = {"passed": passed, "failed": failed, "summary": tail,
       "returncode": out.returncode}
io.open(os.path.join(R, "reports", "tests.json"), "w", encoding="utf-8").write(
    json.dumps(rep, indent=2) + "\n")
subprocess.run(["rm", "-rf", os.path.join(R, ".pt")])
print("%d passed, %d failed" % (passed, failed))
raise SystemExit(0 if failed == 0 and out.returncode == 0 else 1)
