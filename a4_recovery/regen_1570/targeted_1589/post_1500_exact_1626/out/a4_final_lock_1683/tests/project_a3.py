# -*- coding: utf-8 -*-
"""Durable projection, stage 3 (Codex SEQ 1695 item 2): the A3 serial run at its
EXACT historical logical name, plus the plain corrected inventory.

Why this stage exists. The durable A3 copy was RENAMED to `a3_serial_run`, and
the recovery-era pointer `a3_serial_dir.txt` names that physical recovery path.
`raw_transport`'s A1 receipt audit rebuilds the expected receipt FROM the run
directory, so a run presented under a renamed physical path can never match its
own recorded `run_id`, `receipts` and `invocations` - which is exactly the
`A3 evidence is not proved` refusal the RED trace produced.

Nothing is invented. The historical logical directory name is READ from the
run's own recovered receipt (`run_id`, corroborated by the logical
`runs/<run_id>/launch/...` path inside its recorded `invocations`), so the
restored pointer value is derived from the evidence rather than asserted.
Bytes are copied unchanged and re-hashed; the projection only restores the
historical NAME and LOCATION.
"""
import hashlib
import io
import json
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
R70 = R + "/a4_recovery/regen_1570"
T = R70 + "/targeted_1589"
UNIT = T + "/post_1500_exact_1626/out/a4_final_lock_1683"
EV = UNIT + "/evidence"
X = UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
LOGICAL_RUNS = S + "/bench_1306/.claude/plans/Drivers/experiments/runs"

A3_SRC = R70 + "/foundation/a3/bench/.claude/plans/Drivers/experiments/runs/a3_serial_run"
problems, placed = [], []


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src, dst, what):
    if not os.path.isfile(src):
        problems.append("MISSING source for %s: %s" % (what, src)); return
    h = fsha(src)
    if os.path.isfile(dst):
        if fsha(dst) == h:
            placed.append((os.path.relpath(dst, UNIT), h)); return
        problems.append("REFUSE differing byte at %s (%s)" % (dst, what)); return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != h:
        problems.append("REFUSE copy mismatch %s" % dst); return
    placed.append((os.path.relpath(dst, UNIT), h))


# ---- derive the historical logical name from the run's own receipt ---------
rec = json.load(io.open(A3_SRC + "/receipt.json", encoding="utf-8"))
run_id = rec.get("run_id")
if not run_id:
    print("MISSING run_id in the A3 receipt"); sys.exit(1)
inv = rec.get("invocations") or []
corroborated = any(("/runs/" + run_id + "/") in (i.get("scriptPath") or "") for i in inv)
if not corroborated:
    problems.append("run_id %r is not corroborated by any recorded invocation path" % run_id)

# ---- project the A3 run under its historical logical name ------------------
dst_run = X + "/runs/" + run_id
for dp, dn, fn in os.walk(A3_SRC):
    dn.sort()
    for f in sorted(fn):
        s = os.path.join(dp, f)
        if os.path.islink(s) or not os.path.isfile(s):
            continue
        place(s, os.path.join(dst_run, os.path.relpath(s, A3_SRC)), "a3 run")

# ---- restore the pointer to the historical logical path -------------------
ptr = EV + "/a3_serial_dir.txt"
want = LOGICAL_RUNS + "/" + run_id + "\n"
prev = io.open(ptr, encoding="utf-8").read() if os.path.isfile(ptr) else ""
if prev != want:
    io.open(ptr, "w", encoding="utf-8").write(want)
placed.append(("evidence/a3_serial_dir.txt", fsha(ptr)))

# ---- the plain corrected inventory the primary path also opens ------------
place(R70 + "/foundation/a3/bench/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json",
      X + "/one_item_benchmark_inventory.json", "plain inventory")

man = UNIT + "/manifest/PROJECTION_STAGE3.tsv"
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\n")
    for rel, h in sorted(placed):
        fh.write("%s\t%s\n" % (rel, h))

print("historical A3 run_id      : %s" % run_id)
print("corroborated by invocation: %s" % corroborated)
print("pointer now names         : %s" % want.strip().replace(S, "S"))
print("previous pointer value    : %s" % (prev.strip() or "(none)"))
print("files placed              : %d" % len(placed))
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:15]:
        print("   " + p)
    sys.exit(1)
print("STAGE3 OK")
