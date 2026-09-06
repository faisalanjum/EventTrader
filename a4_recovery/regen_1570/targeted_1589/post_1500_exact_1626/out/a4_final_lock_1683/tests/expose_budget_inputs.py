# -*- coding: utf-8 -*-
"""Expose the three recovered budget inputs to the A4 pipeline (Codex SEQ 1725).

Read-only, at their historical logical paths, and nothing else: the G23 bench is not
transplanted and no era owner is touched. The event-run view is COMPOSED rather than
edited - the accepted prior-call view keeps its exact files, and a separate view holds
those same bytes plus the accepted root - so exposing the root cannot alter evidence
that is already verified.
"""
import hashlib, io, os, shutil

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
U = P + "/budget_inputs_1720"
V = UNIT + "/views"
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

PLACE = [("a7_g1_event_run4/root.json", U + "/out_g1/tmp__a7_g1_event_run4__root.json",
          "b491596136682a696876844bedd656c5cc71ff73b323f1be87d307514df3cf81"),
         ("a7_g2_candidate/a7_g1_candidate.json",
          U + "/out_g23/tmp__a7_g2_candidate__a7_g1_candidate.json",
          "21ae14e50050780e6dcac5451c72a4ed5d96b283d38f6f8cd78de2dccc180d19"),
         ("a7_g3_candidate/a7_g1_candidate.json",
          U + "/out_g23/tmp__a7_g3_candidate__a7_g1_candidate.json",
          "53a60ec15228c685b27da89b0bf4ff6c86ece4c78dbe3b9fff127f1040ae0c3a")]

shutil.rmtree(V, ignore_errors=True)
# the accepted prior-call view, byte for byte, so the composed view hides nothing
shutil.copytree(UNIT + "/runs/a7_g1_event_run4", V + "/a7_g1_event_run4")
rows = []
for rel, src, pin in PLACE:
    if fsha(src) != pin:
        raise SystemExit("REFUSE: %s is not at its verified identity" % src)
    dst = os.path.join(V, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != pin:
        raise SystemExit("REFUSE: %s did not survive the copy" % rel)
    rows.append(("/tmp/" + rel, pin, os.path.getsize(dst)))

kept = sorted(os.listdir(UNIT + "/runs/a7_g1_event_run4"))
mine = sorted(os.listdir(V + "/a7_g1_event_run4"))
if mine != sorted(kept + ["root.json"]):
    raise SystemExit("REFUSE: the composed view is not the accepted view plus the root")

with io.open(UNIT + "/manifest/BUDGET_INPUTS_EXPOSED.tsv", "w", encoding="utf-8") as fh:
    fh.write("logical\tsha256\tbytes\n")
    for r in rows:
        fh.write("%s\t%s\t%d\n" % r)
        print("%-46s %s %8d B" % (r[0], r[1][:16], r[2]))
print("composed event view: %d files (%d accepted + the root)" % (len(mine), len(kept)))
