# -*- coding: utf-8 -*-
"""Run the focused and affected A7 no-call tests, and record the real result.

Codex SEQ 1774 items 1 and 4: the full invocation, complete stdout and stderr,
and the exit status are written at execution - not reconstructed afterwards.
Unchanged closed A3-A6 proofs are reused by identity and are NOT re-run here.
"""
import io
import json
import os
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = "/tmp/a7_logs_1773"

#: the affected suites, each named for the restored boundary it covers
SUITES = [
    ("postrun_identity",
     "PR.load/current, immutable launch bindings, executed-run budget",
     "test_a7_postrun_identity_1521_recovery_1774.py"),
    ("g1_precall_freeze",
     "G1 candidate/prompt/population identity and offline admission",
     "test_a7_g1_precall_freeze_1525.py"),
    # the controlled refusals are NOT a pytest module: each needs its own
    # private copy bound at the run's logical path, so they are driven per case
    # by ledger/run_mutations_1774.py and recorded in MUTATION_RECORDS.json
]


def main():
    os.makedirs(OUT, exist_ok=True)
    records = []
    rc_all = 0
    for name, covers, mod in SUITES:
        argv = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
                "-q", os.path.join(H, mod)]
        r = subprocess.run(argv, capture_output=True, text=True, cwd=H,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        io.open("%s/test_%s.log" % (OUT, name), "w", encoding="utf-8").write(
            "COMMAND: %s\nCWD: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n"
            "--- EXIT ---\n%d\n" % (" ".join(argv), H, r.stdout, r.stderr,
                                    r.returncode))
        tail = [l for l in r.stdout.splitlines() if l.strip()][-1:] or [""]
        records.append({"suite": name, "covers": covers, "module": mod,
                        "command": argv, "cwd": H, "exit": r.returncode,
                        "summary": tail[0].strip()})
        print("  %-20s rc=%d  %s" % (name, r.returncode, tail[0].strip()))
        rc_all = rc_all or r.returncode
    io.open(OUT + "/TEST_RECORDS.json", "w", encoding="utf-8").write(
        json.dumps(records, indent=1) + "\n")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
