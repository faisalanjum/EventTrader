# -*- coding: utf-8 -*-
"""Run the ORIGINAL coordinator inside the boundary and record the real result.

Codex SEQ 1778. This wrapper adds no logic of its own: it execs the recovered
g1_run_1525.py with the arguments given, and writes the full argv, complete
stdout and stderr, and the actual numeric exit into this unit's logs.

usage (inside the boundary): run_g1_1778.py <label> <coordinator args...>
"""
import io
import json
import os
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
COORD = S + "/g1_run_1525.py"
OUT = "/tmp/a7_logs_1778"


def main():
    label, args = sys.argv[1], sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    argv = [sys.executable, "-B", COORD] + args
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1_%s.log" % (OUT, label), "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    rec = {"label": label, "command": argv, "exit": r.returncode,
           "stdout_tail": r.stdout.strip().splitlines()[-6:],
           "stderr_tail": r.stderr.strip().splitlines()[-4:]}
    p = OUT + "/G1_RUN_RECORDS.json"
    all_recs = json.load(io.open(p)) if os.path.exists(p) else []
    all_recs.append(rec)
    io.open(p, "w", encoding="utf-8").write(json.dumps(all_recs, indent=1) + "\n")
    print("label %s exit %d" % (label, r.returncode))
    for l in (r.stdout.strip().splitlines() or [""])[-8:]:
        print("  out|", l)
    for l in (r.stderr.strip().splitlines() or [""])[-4:]:
        print("  err|", l)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
