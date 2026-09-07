# -*- coding: utf-8 -*-
"""What caused the named producer-freeze failures? (Codex SEQ 1794 item 3.)

The pre-fix log kept only truncated tails and does not record its own command,
so the failures cannot be attributed by reading it. This asks the question the
only way that answers it: run the SAME affected modules twice - once with the
preserved PRE-FIX owners installed, once with the corrected ones - under the
same map, same bindings and durable logs, and compare.

The owners are restored from the corrected bytes in every case, including on
error, and the restored hashes are recorded.
"""
import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = UNIT + "/view/harness_g1v3"
PREFIX = UNIT + "/evidence/prefix_1792"
R = "/home/faisal/EventMarketDB-driver-recovery"
L = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/"
     "a4_final_lock_1683/launcher/boundary.py")
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
OWNERS = ("audit_worker_access.py", "a7_g1_build.py")
MODULES = ["test_a7_postrun_identity_1521_recovery_1774.py",
           "test_a7_g1_precall_freeze_1525.py",
           "test_a7_cached_rows_1413.py"]


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def suite(label):
    # THE MAP PINS THE VIEW'S DIGEST. Swapping an owner changes it, so the map
    # must be rebuilt for the swapped bytes or the boundary refuses before it
    # runs anything - which is exactly what the first attempt hit.
    subprocess.run([PY, "-B", UNIT + "/build_a7_map_1792.py"],
                   capture_output=True, text=True, cwd=UNIT)
    subprocess.run([PY, "-B", L, "--host", UNIT + "/a7_map_1792.tsv",
                    UNIT + "/ledger/run_tests_1792.py", label] + MODULES,
                   capture_output=True, text=True, timeout=1800)
    path = UNIT + "/logs/tests_%s.log" % label
    text = io.open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    summary = [l for l in text.splitlines()
               if re.search(r"\d+ (passed|failed|error)", l)]
    return collections.OrderedDict([
        ("label", label), ("log", os.path.basename(path)),
        ("summary", summary[-1].strip() if summary else None),
        ("failed", sorted({f.split("::")[-1].split("[")[0]
                           for f in re.findall(r"^FAILED (\S+)", text, re.M)})),
        ("errors", len(re.findall(r"^ERROR ", text, re.M)))])


def main():
    corrected = {n: io.open(VIEW + "/" + n, encoding="utf-8").read() for n in OWNERS}
    try:
        for n in OWNERS:
            io.open(VIEW + "/" + n, "w", encoding="utf-8").write(
                io.open("%s/%s.prefix" % (PREFIX, n), encoding="utf-8").read())
        before = suite("diagnose_with_the_prefix_owners")
    finally:
        for n, text in corrected.items():
            io.open(VIEW + "/" + n, "w", encoding="utf-8").write(text)
    restored = {n: sha(VIEW + "/" + n) for n in OWNERS}
    subprocess.run([PY, "-B", UNIT + "/build_a7_map_1792.py"],
                   capture_output=True, text=True, cwd=UNIT)
    after = suite("diagnose_with_the_corrected_owners")
    doc = collections.OrderedDict([
        ("question", "do the named producer-freeze failures come from the "
                     "interrupted pre-fix implementation, or from something else?"),
        ("modules", MODULES),
        ("with_the_prefix_owners", before),
        ("with_the_corrected_owners", after),
        ("owners_restored", restored),
        ("owners_unchanged", all(
            restored[n] == hashlib.sha256(corrected[n].encode("utf-8")).hexdigest()
            for n in OWNERS))])
    io.open(UNIT + "/logs/FREEZE_DIAGNOSIS_1794.json", "w",
            encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")
    for key in ("with_the_prefix_owners", "with_the_corrected_owners"):
        d = doc[key]
        print("  %-32s %s  failed %s  errors %d"
              % (key, d["summary"], d["failed"][:4], d["errors"]))
    print("  owners restored unchanged: %s" % doc["owners_unchanged"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
