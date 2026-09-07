# -*- coding: utf-8 -*-
"""Run the G1 compatibility suite and record the real result (SEQ 1781)."""
import io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
#: the logical log directory the bind map carries to THIS unit's durable
#: logs/ (a7_map_1792.tsv row "/tmp/a7_logs_1781" -> unit_1792/logs, rw).
#: Writing anywhere else leaves the evidence in the namespace's tmpfs and
#: it dies with the run - which is why only truncated tails survived.
OUT = "/tmp/a7_logs_1781"
label = sys.argv[1]
mods = sys.argv[2:] or ["test_g1_cached_resume_1781.py"]
os.makedirs(OUT, exist_ok=True)
argv = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
        "--no-header", "-rf"] + [os.path.join(H, m) for m in mods]
r = subprocess.run(argv, capture_output=True, text=True, cwd=H,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
path = "%s/tests_%s.log" % (OUT, label)
n = 1
while os.path.exists(path):          # keep every earlier run's evidence
    n += 1
    path = "%s/tests_%s.%d.log" % (OUT, label, n)
io.open(path, "w", encoding="utf-8").write(
    "COMMAND: %s\nCWD: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
    % (" ".join(argv), H, r.stdout, r.stderr, r.returncode))
tail = [l for l in r.stdout.splitlines() if l.strip()]
print("label %s exit %d -> %s" % (label, r.returncode, path))
for l in tail[-14:]:
    print("  |", l)
sys.exit(0)
