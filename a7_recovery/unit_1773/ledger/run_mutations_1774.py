# -*- coding: utf-8 -*-
"""Drive every mutation case at the run's OWN logical identity.

Codex SEQ 1774 item 1. For each case this makes ONE isolated private copy of
the accepted producer run, binds THAT copy at the run's logical path so it is a
lawful run rather than one refusing for its path, and runs the case through the
same published boundary. The accepted output is never mutated: it is only ever
the copy source. Full command, stdout, stderr and exit status are recorded at
execution.
"""
import io
import json
import os
import shutil
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
PY_ = "/home/faisal/EventMarketDB/venv/bin/python3"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
RUN_LOGICAL = S + "/a6_a5run_1515"
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

ACCEPTED_RUN = UNIT + "/out/producer_run"
MUT = UNIT + "/out/mutations"
CASES = ["control", "missing_receipt", "foreign_receipt", "changed_receipt",
         "changed_finalization", "changed_raw", "missing_finalization",
         "wrong_freeze", "wrong_era", "candidate_control", "changed_prompt",
         "changed_question", "short_population"]


def case_map(case, run_src, out_src):
    """The unit map with the run row repointed at THIS case's private copy."""
    rows = []
    for ln in io.open(UNIT + "/a7_map_1773.tsv", encoding="utf-8").read().splitlines():
        lg, src, sha, mode = ln.split("\t")
        if lg == RUN_LOGICAL:
            src, sha, mode = run_src, boundary.source_sha(run_src), "rw"
        rows.append("\t".join([lg, src, sha, mode]))
    rows.append("\t".join(["/tmp/a7_mut_out", out_src,
                           boundary.source_sha(out_src), "rw"]))
    p = os.path.join(os.path.dirname(run_src), "map.tsv")
    io.open(p, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    return p


def main():
    if os.path.isdir(MUT):
        shutil.rmtree(MUT)
    records, bad = [], []
    for case in CASES:
        d = os.path.join(MUT, case)
        run_src = os.path.join(d, "a6_a5run_1515")
        out_src = os.path.join(d, "cand_out")
        os.makedirs(d)
        shutil.copytree(ACCEPTED_RUN, run_src)
        os.makedirs(out_src)
        mp = case_map(case, run_src, out_src)
        argv = [PY_, "-B", L + "/launcher/boundary.py", "--host", mp,
                UNIT + "/ledger/mutation_case_1774.py", case]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=900)
        ok = r.returncode == 0 and "OK" in r.stdout
        io.open(os.path.join(d, "case.log"), "w", encoding="utf-8").write(
            "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
            % (" ".join(argv), r.stdout, r.stderr, r.returncode))
        result = ""
        for line in r.stdout.splitlines():
            if line.startswith("RESULT "):
                result = line[7:]
        records.append({"case": case, "command": argv, "exit": r.returncode,
                        "detected": ok, "result": result})
        if not ok:
            bad.append(case)
        print("  %-22s rc=%-3d %-9s %s"
              % (case, r.returncode, "DETECTED" if ok else "FAILED", result[:74]))
    io.open(UNIT + "/logs/MUTATION_RECORDS.json", "w", encoding="utf-8").write(
        json.dumps(records, indent=1) + "\n")
    print("\n%d cases, %d failed %s" % (len(CASES), len(bad), bad or ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
