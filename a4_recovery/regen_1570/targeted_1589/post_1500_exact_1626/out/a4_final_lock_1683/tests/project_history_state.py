# -*- coding: utf-8 -*-
"""Project one preserved run's official states + transcripts into the durable
session store, so the reconstruction reads them at the historical projects path
through a read-only bind (Codex SEQ 1698).

The preserved `inputs/history_store` is the source, and its own WORKFLOWS.tsv is
the inventory. That inventory has ONE accepted owner - `verify_inventory` in the
frozen `recover_hist_1632` adapter - and it is re-run here over the source bytes
before anything is copied, so no second set of rules is invented. Copies are
re-hashed; an existing differing byte is refused, never overwritten.

Usage: project_history_state.py <run_label>
"""
import importlib
import io
import os
import shutil
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
DEST = (UNIT + "/session_store/projects/-home-faisal-EventMarketDB"
               "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
STORE = (P + "/inputs/history_store/projects/-home-faisal-EventMarketDB"
             "/5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
TSV = P + "/inputs/history_store/WORKFLOWS.tsv"

os.environ.setdefault("PE_1626_HOME", P)
os.environ.setdefault("HIST_1632_OUT", P + "/out/history_1634/attempt2/A")
sys.path.insert(0, P)
PH = importlib.import_module("recover_hist_1632")          # the ONE inventory owner

label = sys.argv[1]
problems = list(PH.verify_inventory(STORE, TSV))
if problems:
    for p in problems[:10]:
        print("REFUSE inventory: " + p)
    sys.exit(1)

rows = PH.wf_rows(label)
if not rows:
    print("REFUSE: the inventory has no run labelled %r" % label)
    sys.exit(1)

placed = []


def place(src, dst):
    h = PH.fsha(src)
    if os.path.isfile(dst):
        if PH.fsha(dst) != h:
            print("REFUSE differing byte already at %s" % dst)
            sys.exit(1)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if PH.fsha(dst) != h:
        print("REFUSE copy mismatch %s" % dst)
        sys.exit(1)
    placed.append((os.path.relpath(dst, UNIT), h))


for r in rows:
    wf = r[1]
    place(STORE + "/workflows/%s.json" % wf, DEST + "/workflows/%s.json" % wf)
    tsrc = STORE + "/subagents/workflows/" + wf
    for f in sorted(os.listdir(tsrc)) if os.path.isdir(tsrc) else []:
        s = os.path.join(tsrc, f)
        if os.path.isfile(s):
            place(s, DEST + "/subagents/workflows/" + wf + "/" + f)
    # the inventory's own transcript binding, re-derived at the DESTINATION
    tdst = DEST + "/subagents/workflows/" + wf
    th, tn = PH.transcript_tree(wf, tdst)
    print("%s  state %s  transcripts %d" % (wf, PH.fsha(DEST + "/workflows/%s.json" % wf)[:16], tn))
    if (th, str(tn)) != (r[7], r[6]):
        print("REFUSE: projected transcript tree is not the inventory's")
        sys.exit(1)

with io.open(UNIT + "/manifest/HISTORY_STATES_%s.tsv" % label, "w", encoding="utf-8") as fh:
    fh.write("dest_rel\tsha256\n")
    for rel, h in sorted(placed):
        fh.write("%s\t%s\n" % (rel, h))
print("run %s: %d state(s), %d file(s) placed this pass" % (label, len(rows), len(placed)))
