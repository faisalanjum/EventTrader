# -*- coding: utf-8 -*-
"""Run the G1 compatibility suite and record the real result (SEQ 1781)."""
import io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = "/tmp/a7_logs_1781"
label = sys.argv[1]
mods = sys.argv[2:] or ["test_g1_cached_resume_1781.py"]
os.makedirs(OUT, exist_ok=True)
argv = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
        "--no-header", "-rf"] + [os.path.join(H, m) for m in mods]
r = subprocess.run(argv, capture_output=True, text=True, cwd=H,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
io.open("%s/tests_%s.log" % (OUT, label), "w", encoding="utf-8").write(
    "COMMAND: %s\nCWD: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
    % (" ".join(argv), H, r.stdout, r.stderr, r.returncode))
tail = [l for l in r.stdout.splitlines() if l.strip()]
print("label %s exit %d" % (label, r.returncode))
for l in tail[-14:]:
    print("  |", l)
sys.exit(0)
