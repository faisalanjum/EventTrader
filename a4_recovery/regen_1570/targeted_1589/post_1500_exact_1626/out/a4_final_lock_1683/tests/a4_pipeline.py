# -*- coding: utf-8 -*-
"""Run the saved A4 final-lock operations in their recorded order (Codex SEQ 1725).

Each step is one of the unit's own already-approved reconstruct scripts, executed
unchanged; the order is the order their own names record. The whole pipeline runs in
ONE namespace because the steps hand each other artifacts through the historical /tmp
paths, and every artifact that survives is preserved durably at the end.

The first failing step stops the run with its own output, so a later step can never
be reached on a broken input.
"""
import hashlib, io, os, shutil, subprocess, sys, time

UNIT = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
        "/post_1500_exact_1626/out/a4_final_lock_1683")
KEEP = os.environ["KEEP_DIR"]
#: the recorded order of the saved operations, read from their own names
#: the review receipt is an INPUT to the budget receipt - the numbers are the
#: reviewer's message ids, not the order the operations run in
#: the budget receipt reads the round-1 review receipt, and the 1502 review is the
#: later correction package input - both exist, in that order
ORDER = ["review_receipt_1501", "budget_receipt_1501", "review_receipt_1502", "prepare_round1", "record_round1_states", "finalize_round1", "bind_1504", "ledger_check", "review_receipt_1505",
         "build_package", "prepare_1506", "record_round1_states",
         "finalize_round1", "bind_1506", "review_receipt_1507", "review_receipt_1508",
         "budget_receipt_1508", "build_package", "prepare_1509", "record_round1_states",
         "finalize_round1", "evidence_1509", "bind_1509", "ledger_check", "build_final_candidate", "harvest_final_sign_run",
         "check_final_key_candidate", "build_final_key_lock_run", "verify_checkpoint"]
only = [s for s in (os.environ.get("A4_STEPS") or "").split(",") if s]
# A stage a later round repeats appears more than once in ORDER, so a filtered run
# cannot be a subset of ORDER without picking one of those positions for it. It runs
# exactly the stages named, in the order they are named; the full run is ORDER itself.
unknown = [s for s in only if s not in ORDER]
if unknown:
    raise SystemExit("REFUSE: not stages of this pipeline: %s" % unknown)
STEPS = only or ORDER
PY3 = "/home/faisal/EventMarketDB/venv/bin/python3"
sha = lambda b: hashlib.sha256(b).hexdigest()

failed = None
for name in STEPS:
    t0 = time.time()
    p = subprocess.run([PY3, "-B", UNIT + "/reconstruct/" + name + ".py"],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    print("%s %-28s rc=%s  %.1fs" % ("ok  " if p.returncode == 0 else "BAD ", name,
                                     p.returncode, time.time() - t0), flush=True)
    print(out.rstrip()[-4000:], flush=True)
    if p.returncode:
        # THE STAGES THAT DID SUCCEED KEEP THEIR OUTPUTS. The namespace holds nothing, so
        # discarding them here would force a completed prerequisite to be recomputed for
        # the next attempt, which is exactly what must not happen.
        failed = name
        break

os.makedirs(KEEP, exist_ok=True)
kept = []
#: the receipts an operation writes beside the bench live under the scratch root, and
#: they are inputs to the next stage exactly as the /tmp artifacts are
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
for dp, _dn, fn in list(os.walk("/tmp")) + [(S, [], sorted(os.listdir(S)))]:
    if dp.startswith("/tmp/claude-1000") and dp != S:
        continue
    for f in sorted(fn):
        s = os.path.join(dp, f)
        if not os.path.isfile(s):
            continue
        rel = os.path.relpath(s, S if dp == S else "/tmp")
        # A STAGE'S OUTPUT IS NOT ALWAYS NAMED AFTER ITS DOOR. The binding and its
        # pointer sit at the scratch root under their own names, and a prefix filter
        # dropped them, so the successful writes were lost with the namespace. Everything
        # the scratch root itself holds is kept; under /tmp the run directories still are.
        if dp != S and not rel.startswith("a7_") and not rel.startswith("a4_"):
            continue
        rel = ("scratch/" + rel) if dp == S else rel
        d = os.path.join(KEEP, rel.replace("/", "__"))
        try:
            shutil.copyfile(s, d)
        except OSError:
            continue
        kept.append((os.path.basename(d), sha(io.open(d, "rb").read()), os.path.getsize(d)))
with io.open(os.path.join(KEEP, "ARTIFACTS.tsv"), "w", encoding="utf-8") as fh:
    fh.write("file\tsha256\tbytes\n")
    for n, h, b in sorted(kept):
        fh.write("%s\t%s\t%d\n" % (n, h, b))
        print("kept %-52s %s %9d B" % (n, h[:16], b))
print("PRESERVED %d artifacts" % len(kept))
if failed:
    print("REFUSED: step %s failed" % failed)
    sys.exit(2)
