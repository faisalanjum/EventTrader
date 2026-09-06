# -*- coding: utf-8 -*-
"""The A7 bind map: the ACCEPTED A6 map, with A7's own view and outputs.

Codex SEQ 1773. Every read-only input the A6 map proved is preserved untouched.
A6's three writable output mounts are its own finished artefacts, and A7 reads
none of them, so they are OMITTED rather than carried in. The only changes are:

  * the logical harness directory -> the smallest A7 view, copied from the
    accepted A6 harness (a file cannot be bound into a read-only directory
    mount, so one directory is the smallest workable unit)
  * the logical workflow store -> the accepted session store PLUS the 36
    preserved producer records, which that store does not carry; the receipt
    the producer recorded names those exact absolute paths
  * the logical completed run -> A7's own fresh reconstruction, writable
  * the published A5 prelaunch fixture stays a DISTINCT read-only input

No published source is ever remapped writable, and no historical path is
created on the host: the tmpfs and binds exist only inside the namespace.
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
A6 = R + "/a6_recovery/unit_1765"
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
UNIT = os.path.dirname(os.path.abspath(__file__))
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
        "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
WF = SESS + "/workflows"
#: the child transcripts are the only place an agent's completion is provable,
#: and the accepted snapshot predates this run, so its own 36 are added beside
#: the snapshot's - never instead of them
SUB = SESS + "/subagents/workflows"
sys.path.insert(0, L + "/launcher")
import boundary                                              # noqa: E402

RO = {X + "/harness_g1v3": UNIT + "/view/harness_g1v3",
      WF: UNIT + "/view/workflows",
      SUB: UNIT + "/view/subagent_runs",
      # the published prelaunch fixture, kept as its own read-only input so the
      # proof can compare the reconstruction against it without touching it
      "/tmp/a7_prelaunch_1773/a6_a5run_1515": R + "/a5_recovery/unit_1758/out/a6_a5run_1515",
      # the existing producer reports, used ONLY as the index naming which
      # recorded states belong to THIS run - the store holds other runs whose
      # launch args are identical, so args alone cannot identify them
      "/tmp/a7_producer_reports_1773": UNIT + "/evidence/reports"}
#: the logical completed run is A7's own reconstruction, and A7's fresh logs
RW = {S + "/a6_a5run_1515": UNIT + "/out/producer_run",
      "/tmp/a7_candidate_a_1773": UNIT + "/out/candidate_a",
      "/tmp/a7_candidate_b_1773": UNIT + "/out/candidate_b",
      "/tmp/a7_logs_1773": UNIT + "/logs"}

rows, omitted, replaced = [], [], []
for ln in io.open(A6 + "/a6_map_1765.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg in RO or lg in RW:
        replaced.append(lg)
        continue
    if mode == "rw":
        omitted.append(lg)          # A6's own outputs; A7 reads none of them
        continue
    rows.append("\t".join([lg, src, sha, mode]))

for lg, src in sorted(RO.items()):
    if not os.path.exists(src):
        raise SystemExit("REFUSED: missing A7 view source at %s" % src)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
for lg, src in sorted(RW.items()):
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))

out = UNIT + "/a7_map_1773.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("A6 output mounts omitted (unused by A7): %d" % len(omitted))
for d in omitted:
    print("   ", d)
print("A6 rows replaced by an A7 binding: %d" % len(replaced))
for d in replaced:
    print("   ", d.replace(S, "S").replace(SUB, "SUB").replace(WF, "WF"))
n_rw = sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")
print("A7 writable (all A7-only): %d" % n_rw)
for lg in sorted(RW):
    print("   ", lg.replace(S, "S"))
print("map rows: %d (%d writable) -> %s" % (len(rows), n_rw, out))
