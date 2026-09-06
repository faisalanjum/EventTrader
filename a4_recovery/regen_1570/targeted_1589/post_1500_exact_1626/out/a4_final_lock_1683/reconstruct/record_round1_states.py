# -*- coding: utf-8 -*-
"""Record the saved official states into the round-1 correction run (Codex SEQ 1732).

This is the step the existing seam skipped. Nothing is chosen here: the run's own receipt
says which labels it scheduled, each saved workflow state says which label it answers
through the owner's own label reader, and the owner's own recorder appends it. A state
that answers no scheduled label is not recorded, and a label with no state stays missing
so finalization can report it rather than have it hidden.
"""
import collections, hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_key as K                                    # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402

#: which correction round this stage serves; the door and the run directory are the
#: owner's own constants for it, never named here
ROUND = os.environ.get("A4_ROUND", "1")
DOOR = getattr(FT, "CORR_DOOR" if ROUND == "1" else "CORR%s_DOOR" % ROUND)
RUN = {"1": "/tmp/a4_final_targeted_corr_run_1504",
       "2": "/tmp/a4_final_targeted_corr2_run_1506",
       "3": "/tmp/a4_final_targeted_corr3_run_1509"}[ROUND]
PROJ = "/home/faisal/.claude/projects"
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
allowed = [r if isinstance(r, str) else r.get("label")
           for r in (receipt.get("allowed") or [])]
allowed = [a for a in allowed if a]
print("scheduled labels:", allowed, flush=True)
print("already recorded:", len(receipt.get("states") or []), flush=True)

found = collections.OrderedDict()
for dp, _dn, fn in os.walk(PROJ):
    if os.path.basename(dp) != "workflows":
        continue
    for f in sorted(fn):
        if not f.endswith(".json"):
            continue
        p = os.path.join(dp, f)
        try:
            doc = json.loads(io.open(p, encoding="utf-8").read())
            label = K._state_label(doc)
        except Exception:
            continue
        if label not in allowed:
            continue
        # THE LABEL IS NOT THE BINDING. Several rounds answer the same key, so a state is
        # this round's only when it RAN THIS RUN'S OWN LAUNCHER - the same check the
        # owner's proof makes. The run's pinned script decides, not the name.
        want = os.path.join(RUN, "scripts", label + ".attempt1.js")
        if not os.path.isfile(want):
            continue
        if doc.get("script") != io.open(want, encoding="utf-8").read():
            continue
        if label in found:
            sys.exit("REFUSE: two saved states ran %s's pinned launcher" % label)
        found[label] = p

print("states located: %d of %d" % (len(found), len(allowed)), flush=True)
# THE RECEIPT'S OWN SCHEDULED ORDER, NOT THE ORDER THE FILES WERE FOUND IN. Walking the
# session store yields the states in filename order, and appending them that way changes
# the receipt identity and every binding that reads it. The run already states the order
# its calls were scheduled in, so that is the order they are recorded in.
for label in allowed:
    if label not in found:
        continue
    p = found[label]
    problems = K.record_state(RUN, p)
    print("  %-22s %s  %s" % (label, sha(p)[:16], problems or "recorded"), flush=True)

missing = [a for a in allowed if a not in found]
if missing:
    print("NO SAVED STATE FOR: %s" % missing, flush=True)
    sys.exit(6)
print("receipt states now:",
      len(K._load(os.path.join(RUN, K.RECEIPT_NAME)).get("states") or []), flush=True)
print("RECORD_ROUND1_OK", flush=True)
