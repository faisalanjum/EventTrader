# -*- coding: utf-8 -*-
"""Host driver: the two boundary phases, with the script-identity check between."""
import hashlib, io, os, subprocess, sys
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = "/home/faisal/EventMarketDB-driver-recovery"
L = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/"
     "a4_final_lock_1683/launcher/boundary.py")
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
PAYLOAD = UNIT + "/ledger/prepare_1799.py"
RUN_DIR = UNIT + "/out/run_1798"
EXECUTED = R + "/a7_recovery/unit_1781/out/proposed_run/grade_batch.seg04.js"
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def boundary(mapfile, phase):
    argv = [PY, "-B", L, "--host", UNIT + "/" + mapfile, PAYLOAD, phase]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=3000)
    io.open("%s/logs/phase_%s.log" % (UNIT, phase), "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print(r.stderr[-1200:])
    return r.returncode


def main():
    if os.path.isdir(RUN_DIR) and os.listdir(RUN_DIR):
        print("REFUSED: %s is not fresh" % RUN_DIR)
        return 1
    for variant in ("candidate", "intake"):
        if subprocess.run([PY, "-B", UNIT + "/build_map_1798.py", variant],
                          capture_output=True, text=True, cwd=UNIT).returncode:
            print("REFUSED: map %s" % variant)
            return 1
    print("== phase 1: freeze the declaring root, replay 1-3, publish 4 ==")
    if boundary("a7_map_1798_candidate.tsv", "prepare"):
        return 1
    mine = os.path.join(RUN_DIR, os.path.basename(EXECUTED))
    identical, same = sha(mine) == sha(EXECUTED), os.path.samefile(mine, EXECUTED)
    print("\n== the published script vs the one that ran ==")
    print("  identical bytes: %s   the same file: %s   %s" % (identical, same, sha(mine)[:16]))
    if not identical or same:
        print("REFUSED: expected identical bytes in this unit's OWN file")
        return 1
    print("\n== phase 2: intake segment 4, then prepare the next batch, no call ==")
    return boundary("a7_map_1798_intake.tsv", "intake_next")


if __name__ == "__main__":
    sys.exit(main())
