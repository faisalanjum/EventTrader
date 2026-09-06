# -*- coding: utf-8 -*-
"""Rebuild the three targeted-phase LOGICAL run directories (Codex SEQ 1695
item 2, defect 2).

The durable sources for targeted-1491, hard-review-1495 and primary-1500 are
SUMMARY EXPORTS: they carry the same bytes under renamed names
(`primary.receipt.json`, `primary_raw/`, `child.*`) instead of the executable
logical run directory the owners open. This restores the logical shape:

    <run>/receipt.json        <- primary.receipt.json
    <run>/finalization.json   <- primary.finalization.json
    <run>/raw/*               <- primary_raw/*
    <run>/retry/receipt.json  <- child.receipt.json          (the binding's
    <run>/retry/finalization.json <- child.finalization.json  attempts[1].dir)
    <run>/retry/raw/*         <- child_raw/*

Every renamed artifact keeps its exact source hash - only the NAME and LOCATION
change - and each copy is re-hashed. `scripts/` is deliberately NOT invented
here: those launchers are owner-rendered and verified against LAUNCHERS.tsv.
"""
import hashlib
import io
import json
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a4_recovery/regen_1570/targeted_1589"
UNIT = T + "/post_1500_exact_1626/out/a4_final_lock_1683"
RUNS = UNIT + "/runs"

# logical run name -> its durable summary export
EXPORTS = {
    "a4_targeted_run_1491":       T + "/targeted_run_1491/out/attempt6/A",
    "a4_hard_review_run_1495":    T + "/hard_review_1495/out/attempt10/A",
    "a4_final_targeted_run_1500": T + "/final_adjudication_1500/out/attempt5/A",
}
# The exports use one of two naming conventions. Detect it from what the export
# actually carries; never assume, and never silently place nothing.
#   A (a primary + its retry child): primary.receipt.json / primary_raw / child.*
#   B (a single attempt):            run.receipt.json     / raw
CONVENTIONS = [
    {"name": "primary+child",
     "receipt": "primary.receipt.json", "finalization": "primary.finalization.json",
     "raw": "primary_raw",
     "extra": [("child.receipt.json", "retry/receipt.json"),
               ("child.finalization.json", "retry/finalization.json")],
     "extra_trees": [("child_raw", "retry/raw")]},
    {"name": "single-run",
     "receipt": "run.receipt.json", "finalization": "run.finalization.json",
     "raw": "raw", "extra": [], "extra_trees": []},
]

problems, placed = [], []


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src, dst):
    h = fsha(src)
    if os.path.isfile(dst):
        if fsha(dst) == h:
            return
        problems.append("REFUSE differing byte at %s" % dst)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != h:
        problems.append("REFUSE copy mismatch %s" % dst)
        return
    placed.append((os.path.relpath(dst, UNIT), h, src))


for run, exp in sorted(EXPORTS.items()):
    if not os.path.isdir(exp):
        problems.append("MISSING summary export for %s: %s" % (run, exp))
        continue
    dst_run = os.path.join(RUNS, run)
    conv = next((c for c in CONVENTIONS
                 if os.path.isfile(os.path.join(exp, c["receipt"]))), None)
    if conv is None:
        problems.append("REFUSE %s: export %s matches no known naming convention "
                        "(no %s)" % (run, exp,
                                     " or ".join(c["receipt"] for c in CONVENTIONS)))
        continue
    place(os.path.join(exp, conv["receipt"]), os.path.join(dst_run, "receipt.json"))
    fin = os.path.join(exp, conv["finalization"])
    if os.path.isfile(fin):
        place(fin, os.path.join(dst_run, "finalization.json"))
    else:
        problems.append("REFUSE %s: export carries no %s" % (run, conv["finalization"]))
    for src_name, dst_rel in conv["extra"]:
        s = os.path.join(exp, src_name)
        if os.path.isfile(s):
            place(s, os.path.join(dst_run, dst_rel))
    for src_dir, dst_dir in [(conv["raw"], "raw")] + conv["extra_trees"]:
        sd = os.path.join(exp, src_dir)
        if not os.path.isdir(sd):
            if src_dir == conv["raw"]:
                problems.append("REFUSE %s: export carries no %s tree" % (run, src_dir))
            continue
        for f in sorted(os.listdir(sd)):
            s = os.path.join(sd, f)
            if os.path.isfile(s):
                place(s, os.path.join(dst_run, dst_dir, f))
    print("  %-28s convention=%s" % (run, conv["name"]))

man = UNIT + "/manifest/RUN_DIRS.tsv"
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\tdurable_source\n")
    for rel, h, src in sorted(placed):
        fh.write("%s\t%s\t%s\n" % (rel, h, src.replace(R + "/", "")))

for run in sorted(EXPORTS):
    d = os.path.join(RUNS, run)
    if os.path.isdir(d):
        print("  %-28s files=%-4d receipt=%s finalization=%s raw=%-3d retry=%s"
              % (run, sum(len(f) for _a, _b, f in os.walk(d)),
                 os.path.isfile(d + "/receipt.json"),
                 os.path.isfile(d + "/finalization.json"),
                 len(os.listdir(d + "/raw")) if os.path.isdir(d + "/raw") else 0,
                 os.path.isdir(d + "/retry")))
print("files placed: %d" % len(placed))
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:15]:
        print("   " + p)
    sys.exit(1)
print("RUN DIRS OK (scripts/ intentionally absent - owner-rendered)")
