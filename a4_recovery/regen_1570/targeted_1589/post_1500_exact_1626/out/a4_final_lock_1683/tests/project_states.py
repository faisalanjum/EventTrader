# -*- coding: utf-8 -*-
"""Durable projection, stage 2 (Codex SEQ 1695 item 2): the complete union of
receipt-named official states and their transcripts, plus the corrected
inventory.

The needed set is DERIVED FROM THE RUNTIME TRACE the real owners produced
(manifest/RED_PRIMARY_PATH.json), never hand-listed: every workflow state the
owners actually asked for and did not find is projected from a named durable
store, with its transcript directory. Each byte is re-hashed after copying;
a missing, duplicate, or mismatched required byte refuses.
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
X = UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments"

# Named durable stores, most specific first. The OFFICIAL store is last: it is
# the record `audit_worker_access._official_location` itself names, and it is
# consulted only for a receipt-named state no recovery store carries. Whatever
# it supplies is copied INTO the durable unit and it is the unit's copy that the
# namespace binds, so the reconstruction still never reads live bytes at run time.
LIVE = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB"
        "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
STATE_STORES = [R70 + "/foundation/a3/evidence/workflow_states",
                R + "/a3_recovery/regen_1541/evidence/workflow_states",
                LIVE + "/workflows"]
TRANSCRIPT_STORES = [R70 + "/foundation/a3/evidence/subagent_records",
                     R + "/a3_recovery/regen_1541/evidence/subagent_records",
                     LIVE + "/subagents/workflows"]

problems, placed = [], []


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def place(src, dst, what):
    if not os.path.isfile(src):
        problems.append("MISSING source for %s: %s" % (what, src))
        return
    h = fsha(src)
    if os.path.isfile(dst):
        if fsha(dst) == h:
            placed.append((os.path.relpath(dst, UNIT), h, src))
            return
        problems.append("REFUSE differing byte at %s (%s)" % (dst, what))
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != h:
        problems.append("REFUSE copy mismatch %s" % dst)
        return
    placed.append((os.path.relpath(dst, UNIT), h, src))


def find_first(stores, rel):
    for s in stores:
        c = os.path.join(s, rel)
        if os.path.exists(c):
            return c
    return None


# ---- derive the needed workflow set from the real owners' trace ------------
trace = json.load(io.open(UNIT + "/manifest/RED_PRIMARY_PATH.json", encoding="utf-8"))
wanted = []
for row in trace["missing_project_paths"]:
    p = row["path"]
    if "/workflows/" in p and p.endswith(".json"):
        wanted.append(os.path.basename(p)[:-5])
wanted = sorted(set(wanted))

for wf in wanted:
    src = find_first(STATE_STORES, wf + ".json")
    if src is None:
        problems.append("MISSING durable state for %s in any named store" % wf)
        continue
    place(src, os.path.join(SESS, "workflows", wf + ".json"), "state %s" % wf)
    tdir = find_first(TRANSCRIPT_STORES, wf)
    if tdir is None or not os.path.isdir(tdir):
        problems.append("MISSING durable transcripts for %s" % wf)
        continue
    for f in sorted(os.listdir(tdir)):
        s = os.path.join(tdir, f)
        if os.path.isfile(s):
            place(s, os.path.join(SESS, "subagents", "workflows", wf, f),
                  "transcript %s/%s" % (wf, f))

# ---- the corrected inventory the primary path opens -----------------------
place(T + "/phase1_targeted_1488/inputs/one_item_benchmark_inventory.v2_1487.json",
      X + "/one_item_benchmark_inventory.v2_1487.json", "corrected inventory")

man = UNIT + "/manifest/PROJECTION_STAGE2.tsv"
with io.open(man, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\tdurable_source\n")
    for rel, h, src in sorted(placed):
        fh.write("%s\t%s\t%s\n" % (rel, h, src.replace(R + "/", "")))

print("workflows requested by the owners : %d" % len(wanted))
print("files placed                      : %d" % len(placed))
print("session store states now          : %d"
      % len([f for f in os.listdir(os.path.join(SESS, "workflows")) if f.endswith(".json")]))
print("manifest                          : manifest/PROJECTION_STAGE2.tsv")
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:20]:
        print("   " + p)
    sys.exit(1)
print("STAGE2 OK")
