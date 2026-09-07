# -*- coding: utf-8 -*-
"""Host driver for the two-phase candidate (Codex SEQ 1794 item 4).

Builds this unit's two maps, runs the prepare phase inside the boundary, proves
the published segment-4 script it wrote is byte-identical to - and a DIFFERENT
file from - the immutable one the native call executed, then runs the intake
phase under the map whose scoped override presents that immutable file at the
logical path. No published byte is written, moved or relinked.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = "/home/faisal/EventMarketDB-driver-recovery"
L = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/"
     "a4_final_lock_1683/launcher/boundary.py")
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
PAYLOAD = UNIT + "/ledger/candidate_1794.py"
RUN_DIR = UNIT + "/out/candidate_run_1794"
EXECUTED = R + "/a7_recovery/unit_1781/out/proposed_run/grade_batch.seg04.js"


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def boundary(mapfile, phase):
    argv = [PY, "-B", L, "--host", UNIT + "/" + mapfile, PAYLOAD, phase]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=3000)
    io.open("%s/logs/candidate_%s.log" % (UNIT, phase), "w",
            encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print(r.stderr[-1500:])
    return r.returncode


def main():
    if os.path.isdir(RUN_DIR) and os.listdir(RUN_DIR):
        print("REFUSED: %s is not fresh; preserve it and name a new run before "
              "another attempt" % RUN_DIR)
        return 1
    for variant in ("candidate", "candidate_intake"):
        r = subprocess.run([PY, "-B", UNIT + "/build_a7_map_1792.py", variant],
                           capture_output=True, text=True, cwd=UNIT)
        if r.returncode != 0:
            print("REFUSED map %s: %s" % (variant, r.stderr[-400:]))
            return 1

    print("== phase 1: freeze the declaring root, replay 1-3, publish 4 ==")
    if boundary("a7_map_1792_candidate.tsv", "prepare"):
        return 1

    mine = os.path.join(RUN_DIR, os.path.basename(EXECUTED))
    if not os.path.isfile(mine):
        print("REFUSED: the prepare phase published no segment-4 script")
        return 1
    identical, same_file = sha(mine) == sha(EXECUTED), os.path.samefile(mine, EXECUTED)
    print("\n== the published script vs the one that ran ==")
    print("  candidate : %s  %s" % (sha(mine)[:16], mine))
    print("  executed  : %s  %s" % (sha(EXECUTED)[:16], EXECUTED))
    print("  identical bytes: %s   the same file: %s" % (identical, same_file))
    if not identical or same_file:
        print("REFUSED: the candidate must publish the same BYTES in its OWN "
              "file before the intake may present the immutable original")
        return 1

    print("\n== phase 2: intake, audit and finalization, no call ==")
    rc = boundary("a7_map_1792_candidate_intake.tsv", "intake")
    io.open(UNIT + "/logs/CANDIDATE_SCRIPT_IDENTITY_1794.json", "w",
            encoding="utf-8").write(json.dumps({
                "candidate_published": {"path": mine, "sha256": sha(mine)},
                "actually_executed": {"path": EXECUTED, "sha256": sha(EXECUTED)},
                "identical_bytes": identical,
                "the_same_file_on_disk": same_file,
                "intake_presents_the_executed_file_by_a_scoped_read_only_bind":
                    True}, indent=1) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
