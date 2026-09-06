# -*- coding: utf-8 -*-
"""Prove each recovered fixture change is caught when reversed (Codex 1762 item 4).

For each fix: put the pre-fix text back, run only the tests that fix serves, require
them RED, then restore the corrected bytes and verify the file hash returns exactly.
The restore runs even if the check raises, so a failure here cannot leave the unit
holding reverted bytes.
"""
import hashlib
import io
import os
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
UNIT = R + "/a5_recovery/unit_1758"
U = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
V = UNIT + "/view/experiments/harness_g1v3"
PY = "/home/faisal/EventMarketDB/venv/bin/python3"

#: (file, the corrected text, the reverted text, log name, tests the fix serves)
CASES = [
    ("test_harness_guards.py",
     "    prompts = _mirror_prompts(work, tmp_path, plan)\n"
     "    runtime = \"claude-sonnet-5\"\n",
     "    prompts = _mirror_prompts(work, tmp_path)\n"
     "    runtime = \"claude-sonnet-5\"\n",
     "reversal_mirror_plan_1762",
     ["test_a5_route_1406.py::test_a5_public_route_runs_end_to_end_on_all_lawful_reply_shapes"]),
    ("test_a1_no_tools.py",
     "    blm.build()\n",
     "",
     "reversal_notools_build_1762",
     ["test_a1_no_tools.py::test_removing_the_deny_from_one_launcher_makes_the_derived_check_refuse"]),
]


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def remap():
    """The map pins the view's digest, so a reverted file makes the boundary refuse
    until the map is rebuilt for that exact state. Rebuilding is part of the control,
    not a way around the check."""
    subprocess.run([PY, "-B", UNIT + "/build_a5_map_1758.py"],
                   capture_output=True, text=True, cwd=UNIT, check=True)


def run(name, tests):
    remap()
    cmd = [PY, "-B", U + "/launcher/boundary.py", "--host", UNIT + "/a5_map_1758.tsv",
           UNIT + "/a5_tests_1758.py", name] + tests
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=UNIT)
    log = os.path.join(UNIT, "logs", name + ".log")
    if not os.path.isfile(log):
        raise SystemExit("REFUSED: %s produced no log; rc=%d stderr=%s"
                         % (name, p.returncode, (p.stderr or p.stdout)[-400:]))
    body = io.open(log, encoding="utf-8").read()
    return p.returncode, body


bad = []
for fname, fixed, reverted, log, tests in CASES:
    path = os.path.join(V, fname)
    good = io.open(path, encoding="utf-8").read()
    good_sha = fsha(path)
    if good.count(fixed) != 1:
        raise SystemExit("REFUSED: the corrected text is not unique in %s" % fname)
    try:
        io.open(path, "w", encoding="utf-8").write(good.replace(fixed, reverted, 1))
        rc, body = run(log, tests)
        red = "failed" in body.splitlines()[-3] if len(body.splitlines()) > 3 else False
        ok = rc != 0 and red
        print("%s %-34s reverted -> rc=%d | %s"
              % ("ok  " if ok else "BAD ", fname, rc,
                 [l for l in body.splitlines() if "passed" in l or "failed" in l][-1:]))
        if not ok:
            bad.append(fname)
    finally:
        io.open(path, "w", encoding="utf-8").write(good)
        remap()
        back = fsha(path)
        print("     restored %s == %s : %s" % (back[:16], good_sha[:16], back == good_sha))
        if back != good_sha:
            bad.append(fname + " (restore)")

print("reversal controls failed: %d %s" % (len(bad), bad))
sys.exit(1 if bad else 0)
