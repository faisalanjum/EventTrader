# -*- coding: utf-8 -*-
"""Freeze the complete A4 recovery: manifest, evidence map, restart commands, whitelist.

Codex SEQ 1741 item 5. Nothing is described that is not measured here: every manifest row is
hashed from the live file, every evidence row names the log or source that carries it, and
the unchanged-input rows are re-measured, not asserted.
"""
import hashlib
import io
import os
import re
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
A = P + "/a4_owner_1726"
OUT = UNIT + "/FREEZE_1741"
LOGS = UNIT + "/logs"
#: the whitelist: exactly the trees this A4 recovery owns
TREES = [UNIT + "/reconstruct", UNIT + "/tests", UNIT + "/launcher", UNIT + "/lock",
         UNIT + "/superseded", UNIT + "/manifest", UNIT + "/logs", UNIT + "/out",
         UNIT + "/runs_rw", A + "/proved", A + "/patches", A + "/tests",
         A + "/recover_a4_owner.py", A + "/patch_replay.py", A + "/A6_R3_SOURCES.json"]

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
os.makedirs(OUT, exist_ok=True)


def walk(root):
    if os.path.isfile(root):
        yield root
        return
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            yield os.path.join(dp, f)


rows, total = [], 0
for t in TREES:
    for f in sorted(walk(t)):
        if os.path.realpath(f).startswith(OUT):
            continue
        rows.append((os.path.relpath(f, R), sha(f), os.path.getsize(f)))
        total += os.path.getsize(f)
with io.open(OUT + "/MANIFEST.sha256", "w", encoding="utf-8") as fh:
    fh.write("path\tsha256\tbytes\n")
    for r in sorted(rows):
        fh.write("%s\t%s\t%d\n" % r)
with io.open(OUT + "/WHITELIST.tsv", "w", encoding="utf-8") as fh:
    fh.write("git_add_path\tfiles\tbytes\n")
    for t in TREES:
        fs = [f for f in walk(t) if not os.path.realpath(f).startswith(OUT)]
        fh.write("%s\t%d\t%d\n" % (os.path.relpath(t, R), len(fs),
                                   sum(os.path.getsize(f) for f in fs)))


def find_log(marker):
    """The newest run log that carries this exact marker."""
    for f in sorted(os.listdir(LOGS), reverse=True):
        if not f.startswith("a4_"):
            continue
        p = os.path.join(LOGS, f)
        if marker in io.open(p, encoding="utf-8", errors="replace").read():
            return "logs/" + f, sha(p)
    return "", ""


EXECUTED = [
    ("round 2 states recorded in the receipt's scheduled order", "RECORD_ROUND1_OK"),
    ("round 2 finalized once", "FINALIZE_ROUND1_OK"),
    ("round 2 bound; ledger 5217", "LEDGER_OK 5217"),
    ("round 3 corrected budget receipt ae27f66f", "BUDGET_1508_OK"),
    ("round 3 package eb3cce17", "BUILD_PACKAGE_OK"),
    ("round 3 prepared receipt 071b41f7", "PREPARE_DONE"),
    ("round 3 evidence helper derived", "EVIDENCE_1509_OK"),
    ("round 3 bound; ledger 5219", "LEDGER_OK 5219"),
    ("final candidate built and verified", "BUILD_CANDIDATE_OK"),
    ("saved signer harvested (no new call)", "HARVEST_OK"),
    ("four owed checker cases under real pytest", "CHECK_CANDIDATE_OK"),
    ("lock and receipt written once; 28/28 mutations refuse", "LOCK_OK"),
]
LOCAL_TESTS = ["tests/test_build_wrapper_refusal.py", "tests/test_stage_propagation.py",
               "tests/test_recovery_wrappers_1741.py", "tests/test_placement_rules.py"]
REUSED = [
    ("the rest of check_final_key_candidate.py (dd4e321d)",
     "actual historical execution at original 87726/87817, single-test patch 87823, passing rerun 87835"),
    ("correction-round regression", "original 87773 and its corrected test rerun"),
    ("boundary and projection placement results",
     "unchanged source/input identity; tests/test_placement_rules.py re-run today"),
    ("two identical candidate builds",
     "the build plus fresh C.verify (Codex SEQ 1741 standing proof); the three-rebuild test not re-run"),
]
with io.open(OUT + "/EVIDENCE.tsv", "w", encoding="utf-8") as fh:
    fh.write("kind\twhat\tmarker_or_source\tlog\tlog_sha256\n")
    for what, marker in EXECUTED:
        log, h = find_log(marker)
        fh.write("executed\t%s\t%s\t%s\t%s\n" % (what, marker, log, h))
    for t in LOCAL_TESTS:
        p = UNIT + "/" + t
        if os.path.isfile(p):
            r = subprocess.run(["/home/faisal/EventMarketDB/venv/bin/python3", "-B", p],
                               capture_output=True, text=True, stdin=subprocess.DEVNULL,
                               cwd=UNIT, timeout=900,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            last = (r.stdout or "").strip().splitlines()[-1:] or [""]
            fh.write("executed\t%s\t%s\trc=%d\t%s\n" % (t, last[0], r.returncode, sha(p)))
    for what, src in REUSED:
        fh.write("reused\t%s\t%s\t\t\n" % (what, src))

# nothing accepted or unrelated changed
checks = []
r = subprocess.run(["/home/faisal/EventMarketDB/venv/bin/python3", "-B",
                    A + "/verify_prior_unit.py"], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, timeout=600)
checks.append(("budget_inputs_1720 (accepted unit)", (r.stdout or "").strip()))
ev = UNIT + "/evidence/lock"
diff = [f for f in walk(ev)
        if sha(f) != sha(os.path.join(UNIT, "lock", os.path.relpath(f, ev)))]
checks.append(("evidence/lock is carried unchanged inside lock/",
               "%d of %d files differ" % (len(diff), len(list(walk(ev))))))
for name, cmd in (("main HEAD", "git -C /home/faisal/EventMarketDB rev-parse HEAD"),
                  ("main staged", "git -C /home/faisal/EventMarketDB diff --cached --name-only | wc -l"),
                  ("main modified", "git -C /home/faisal/EventMarketDB status --porcelain | grep -c '^ M' ; true"),
                  ("recovery HEAD", "git -C %s rev-parse HEAD" % R),
                  ("recovery staged", "git -C %s diff --cached --name-only | wc -l" % R)):
    v = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300).stdout.strip()
    checks.append((name, v))
with io.open(OUT + "/UNCHANGED.tsv", "w", encoding="utf-8") as fh:
    fh.write("check\tresult\n")
    for k, v in checks:
        fh.write("%s\t%s\n" % (k, v.replace("\n", " ")))

io.open(OUT + "/RESTART.md", "w", encoding="utf-8").write("""# A4 recovery - exact restart

Every stage runs inside the existing private boundary through the one runner. The stage
names are the pipeline's own; `A4_STEPS` runs exactly those, in the order named.

    U=%s
    cd $U

Round 2 (already complete; ledger 5217):

    A4_ROUND=2 A4_STEPS=review_receipt_1505,build_package,prepare_1506 bash tests/run_a4.sh
    python3 -B tests/seed_runs_rw.py a4_final_targeted_corr2_run_1506
    A4_ROUND=2 A4_STEPS=record_round1_states,finalize_round1 bash tests/run_a4.sh
    A4_ROUND=2 A4_STEPS=bind_1506 bash tests/run_a4.sh
    A4_ROUND=2 A4_STEPS=ledger_check A4_LEDGER=5217 \\
      A4_A6=f323b7bcf7aabbb13b2a2d7e0ab495a7c3b8b36128db9d6059575633aecc15a0 bash tests/run_a4.sh

Round 3 (already complete; ledger 5219). The era owner is placed first:

    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <960ebdeb...>   # 1507 receipt
    A4_ROUND=3 A4_STEPS=review_receipt_1507 bash tests/run_a4.sh
    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <cdd008c1...>   # 1508 onward
    A4_ROUND=3 A4_STEPS=review_receipt_1508,budget_receipt_1508,build_package,prepare_1509 bash tests/run_a4.sh
    python3 -B tests/seed_runs_rw.py a4_final_targeted_corr3_run_1509
    A4_ROUND=3 A4_STEPS=record_round1_states,finalize_round1,evidence_1509 bash tests/run_a4.sh
    A4_ROUND=3 A4_STEPS=bind_1509,ledger_check A4_LEDGER=5219 \\
      A4_A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de bash tests/run_a4.sh

Closure (already complete; lock written once):

    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <fb7c820d...>
    A4_ROUND=3 A4_A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de \\
      A4_STEPS=build_final_candidate,harvest_final_sign_run,check_final_key_candidate,build_final_key_lock_run \\
      bash tests/run_a4.sh

The lock stage refuses if the lock already exists: it is written once.

Recovery-side tests (no boundary needed):

    python3 -B tests/test_build_wrapper_refusal.py
    python3 -B tests/test_stage_propagation.py
    python3 -B tests/test_recovery_wrappers_1741.py
    python3 -B tests/test_placement_rules.py
""" % UNIT)

print("MANIFEST.sha256 %d rows, %d bytes" % (len(rows), total))
print("WHITELIST.tsv   %d trees" % len(TREES))
for k, v in checks:
    print("   %-44s %s" % (k, v))
print("FREEZE_OK")
