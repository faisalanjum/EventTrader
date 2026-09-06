# -*- coding: utf-8 -*-
"""Durable projection: the COMPLETE union of receipt-named official states and
their transcripts (Codex SEQ 1695 item 2), derived in one pass.

Every projected run receipt (and its retry receipt) NAMES the official state of
each call it made. Reading those receipts gives the complete union directly,
instead of discovering one more state per execution pass.

Recovery stores are preferred; the official store that
`audit_worker_access._official_location` itself names is the last resort for a
receipt-named state no recovery store carries. Everything accepted is copied
INTO the durable unit and re-hashed, and it is the unit's copy the namespace
binds, so the reconstruction never reads live bytes at run time.
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
SESS = (UNIT + "/session_store/projects/-home-faisal-EventMarketDB"
               "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
# Every projected run: the pre-targeted history inside the bench, AND the three
# reconstructed targeted-phase logical run directories. Both carry receipts that
# name official states, so both must be read or that phase's states go missing.
RUN_ROOTS = [UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments/runs",
             UNIT + "/runs"]
LIVE = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB"
        "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")

STATE_STORES = [R70 + "/foundation/a3/evidence/workflow_states",
                R + "/a3_recovery/regen_1541/evidence/workflow_states",
                LIVE + "/workflows"]
TRANSCRIPT_STORES = [R70 + "/foundation/a3/evidence/subagent_records",
                     R + "/a3_recovery/regen_1541/evidence/subagent_records",
                     LIVE + "/subagents/workflows"]

problems, placed, from_official = [], [], 0


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src, dst):
    global from_official
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
    if src.startswith(LIVE):
        from_official += 1


# ---- the complete union, read from every projected run receipt ------------
wanted = set()
receipts = 0
walked = []
for root in RUN_ROOTS:
    if os.path.isdir(root):
        # followlinks: a projected run may be a POINTER to evidence already
        # proved elsewhere in the recovery worktree, and its receipt names
        # states just like a copied one - not descending would silently drop
        # that whole run's states from the union.
        walked.extend(os.walk(root, followlinks=True))
for dp, _dn, fn in walked:
    if "receipt.json" not in fn:
        continue
    receipts += 1
    try:
        rec = json.load(io.open(os.path.join(dp, "receipt.json"), encoding="utf-8"))
    except Exception as exc:                             # noqa: BLE001
        problems.append("unreadable receipt %s: %s" % (dp, exc))
        continue
    for s in rec.get("states") or []:
        if isinstance(s, str) and s.endswith(".json"):
            wanted.add(os.path.basename(s)[:-5])

for wf in sorted(wanted):
    src = next((os.path.join(s, wf + ".json") for s in STATE_STORES
                if os.path.isfile(os.path.join(s, wf + ".json"))), None)
    if src is None:
        problems.append("MISSING receipt-named state %s in every named store" % wf)
        continue
    place(src, os.path.join(SESS, "workflows", wf + ".json"))
    tdir = next((os.path.join(s, wf) for s in TRANSCRIPT_STORES
                 if os.path.isdir(os.path.join(s, wf))), None)
    if tdir is None:
        problems.append("MISSING transcripts for receipt-named state %s" % wf)
        continue
    for f in sorted(os.listdir(tdir)):
        s = os.path.join(tdir, f)
        if os.path.isfile(s):
            place(s, os.path.join(SESS, "subagents", "workflows", wf, f))

man = UNIT + "/manifest/SESSION_UNION.tsv"
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\tsource\n")
    for rel, h, src in sorted(placed):
        fh.write("%s\t%s\t%s\n" % (rel, h, src.replace(R + "/", "")))

have = len([f for f in os.listdir(os.path.join(SESS, "workflows")) if f.endswith(".json")])
print("run receipts read            : %d" % receipts)
print("receipt-named states (union) : %d" % len(wanted))
print("files placed this pass       : %d  (from official store: %d)" % (len(placed), from_official))
print("session store states now     : %d" % have)
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:15]:
        print("   " + p)
    sys.exit(1)
print("SESSION UNION OK")
