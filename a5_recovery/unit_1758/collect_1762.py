# -*- coding: utf-8 -*-
"""Collect the affected suite inventory without executing it (Codex 1762 item 4)."""
import os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
suites = sys.argv[1:]
cmd = [sys.executable, "-B", "-m", "pytest"] + suites + [
    "--collect-only", "-q", "--import-mode=importlib", "-p", "no:cacheprovider", "--no-header"]
p = subprocess.run(cmd, cwd=H, capture_output=True, text=True,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
open("/tmp/a5_logs_1758/collect_1762.log", "w").write(
    "$ %s\n%s%s\n[rc=%d]\n" % (" ".join(cmd), p.stdout or "", p.stderr or "", p.returncode))
print((p.stdout or "").splitlines()[-1] if p.stdout else "", "rc=%d" % p.returncode)
