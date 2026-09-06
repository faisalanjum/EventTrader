# -*- coding: utf-8 -*-
"""Durable projection builder (Codex SEQ 1695 item 2), stage 1.

Supplies the direct inputs the RED trace proved missing, from the already
durable verified recovery sources under regen_1570 only:

  * the A6 ledger pointer files that name the pre-targeted signed A4 history
    (the 3 correction pointers are WRITTEN by the bind owners during
    reconstruction, so they are outputs, not inputs, and are not placed here);
  * the pre-targeted run directories those pointers name, plus the signer run;
  * the `kfields_final` package `A6.bound` binds;
  * the pinned primary package `final_targeted_1499`.

Every byte is copied from a named durable source and re-hashed after the copy.
Any missing, duplicate, moved, or hash-mismatched required byte refuses.
Nothing unrelated is recreated. Re-runnable: an identical byte already in place
is left alone and counted, a differing byte refuses.
"""
import hashlib
import io
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
R70 = R + "/a4_recovery/regen_1570"
T = R70 + "/targeted_1589"
UNIT = T + "/post_1500_exact_1626/out/a4_final_lock_1683"
EV = UNIT + "/evidence"                                  # the logical S root
X = UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments"
FOUND = R70 + "/foundation/out"

problems = []
placed = []                                              # (dest_rel, sha256, source)


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src, dst, what):
    """Copy one required byte and re-hash it; refuse anything not exact."""
    if not os.path.isfile(src):
        problems.append("MISSING required source for %s: %s" % (what, src))
        return
    h = fsha(src)
    if os.path.isfile(dst):
        if fsha(dst) == h:                               # already exact
            placed.append((os.path.relpath(dst, UNIT), h, src))
            return
        problems.append("REFUSE differing byte already at %s (%s)" % (dst, what))
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != h:
        problems.append("REFUSE copy mismatch for %s: %s" % (what, dst))
        return
    placed.append((os.path.relpath(dst, UNIT), h, src))


def place_tree(src_dir, dst_dir, what):
    if not os.path.isdir(src_dir):
        problems.append("MISSING required source tree for %s: %s" % (what, src_dir))
        return
    for dp, dn, fn in os.walk(src_dir):
        dn.sort()
        for f in sorted(fn):
            s = os.path.join(dp, f)
            if os.path.islink(s) or not os.path.isfile(s):
                continue
            place(s, os.path.join(dst_dir, os.path.relpath(s, src_dir)), what)


# ---- 1. A6 ledger pointer files (inputs only) ------------------------------
PTR_SRC = T + "/post_1500_exact_1626/inputs/pointers"
POINTERS = {
    "a4_dir.txt": FOUND + "/5/a4_dir.txt",
    "hr_dir.txt": T + "/hard_review_1495/inputs/pointers/hr_dir.txt",
}
for name in ("hrfix_dir.txt", "final_dir.txt", "corr_dir.txt", "decision_dir.txt",
             "v4_dir.txt", "v5_dir.txt", "v6_dir.txt", "signer_dir.txt",
             "targeted_dir.txt", "hard_review_targeted_dir.txt",
             "final_targeted_dir.txt"):
    POINTERS[name] = os.path.join(PTR_SRC, name)
for name, src in sorted(POINTERS.items()):
    place(src, os.path.join(EV, name), "ledger pointer %s" % name)

# ---- 2. the runs those pointers name (pre-targeted history + signer) -------
# Resolve each run name from the pointer bytes themselves, then take the most
# complete durable copy under foundation/out.
RUNS_DST = X + "/runs"
run_names = []
for name in sorted(POINTERS):
    p = os.path.join(EV, name)
    if not os.path.isfile(p):
        continue
    target = io.open(p, encoding="utf-8").read().strip()
    if "/experiments/runs/" in target:                   # a bench-relative logical run
        run_names.append(os.path.basename(target))
run_names = sorted(set(run_names))

for run in run_names:
    best, bestn = None, -1
    for n in sorted(os.listdir(FOUND), key=lambda s: (len(s), s)):
        cand = os.path.join(FOUND, n,
                            "bench_1306/.claude/plans/Drivers/experiments/runs", run)
        if os.path.isdir(cand):
            c = sum(len(f) for _d, _s, f in os.walk(cand))
            if c > bestn:
                best, bestn = cand, c
    if best is None:
        problems.append("MISSING durable run directory: %s" % run)
        continue
    place_tree(best, os.path.join(RUNS_DST, run), "run %s" % run)

# ---- 3. packages ----------------------------------------------------------
kf_final = None
for n in sorted(os.listdir(FOUND), key=lambda s: (len(s), s)):
    cand = os.path.join(FOUND, n, "bench_1306/.claude/plans/Drivers/experiments/kfields_final")
    if os.path.isdir(cand):
        c = sum(len(f) for _d, _s, f in os.walk(cand))
        if kf_final is None or c > kf_final[1]:
            kf_final = (cand, c)
if kf_final is None:
    problems.append("MISSING durable kfields_final package")
else:
    place_tree(kf_final[0], X + "/kfields_final", "kfields_final package")

FA4 = T + "/final_adjudication_1500/out/attempt4/A"
PKG1499 = X + "/kfields_key_a4/final_targeted_1499"
place(FA4 + "/final_targeted.manifest.json",
      PKG1499 + "/final_targeted.manifest.json", "primary package manifest")
place(FA4 + "/prompt_prefix_final_targeted.txt",
      PKG1499 + "/prompt_prefix_final_targeted.txt", "primary package prefix")

# ---- report ---------------------------------------------------------------
man = UNIT + "/manifest/PROJECTION_STAGE1.tsv"
os.makedirs(os.path.dirname(man), exist_ok=True)
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\tdurable_source\n")
    for rel, h, src in sorted(placed):
        fh.write("%s\t%s\t%s\n" % (rel, h, src.replace(R + "/", "")))

print("pointers placed      : %d" % len(POINTERS))
print("runs projected       : %d  (%s)" % (len(run_names), ", ".join(r[:22] for r in run_names[:3]) + " ..."))
print("files placed total   : %d" % len(placed))
print("manifest             : manifest/PROJECTION_STAGE1.tsv")
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:20]:
        print("   " + p)
    sys.exit(1)
print("STAGE1 OK")
