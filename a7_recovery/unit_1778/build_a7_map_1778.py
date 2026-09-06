# -*- coding: utf-8 -*-
"""The G1 restoration bind map (Codex SEQ 1778).

Derived from the PUBLISHED unit_1773 map, which Codex verified. Every source
that unit carries is now published, so all of them are read-only here; the old
unit is never written to and never modified. The only additions are the G1 view,
the original coordinator, the candidate at its ORIGINAL logical path, and this
unit's own fresh writable output.
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
OLD = R + "/a7_recovery/unit_1773"
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
UNIT = os.path.dirname(os.path.abspath(__file__))
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
        "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

RO = {X + "/harness_g1v3": UNIT + "/view/harness_g1v3",
      SESS + "/workflows": UNIT + "/view/workflows",
      SESS + "/subagents/workflows": UNIT + "/view/subagent_runs",
      # the ORIGINAL coordinator, recovered byte-exact from its own records
      S + "/g1_run_1525.py": UNIT + "/view/scratchpad/g1_run_1525.py",
      # the PUBLISHED candidate, at its original logical candidate path
      S + "/g1_precall_cand_1525": OLD + "/out/candidate_a",
      # the PUBLISHED completed producer run, read-only
      S + "/a6_a5run_1515": OLD + "/out/producer_run"}
#: this unit's own writable output - the run under restoration, and its logs
RW = {S + "/g1_precall_run_1525": UNIT + "/out/g1_precall_run_1525",
      "/tmp/a7_logs_1778": UNIT + "/logs"}

rows, demoted, replaced = [], [], []
for ln in io.open(OLD + "/a7_map_1773.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg in RO or lg in RW:
        replaced.append(lg)
        continue
    if mode == "rw":
        # every unit_1773 output is published now: read-only here
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))

for lg, src in sorted(RO.items()):
    if not os.path.exists(src):
        raise SystemExit("REFUSED: missing read-only source at %s" % src)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
for lg, src in sorted(RW.items()):
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))

out = UNIT + "/a7_map_1778.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
n_rw = sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")
print("published unit_1773 outputs demoted to read-only: %d" % len(demoted))
for d in demoted:
    print("   ", d.replace(S, "S"))
print("rows replaced by a G1 binding: %d" % len(replaced))
for d in replaced:
    print("   ", d.replace(S, "S").replace(SESS, "SESS"))
print("writable (all unit_1778-only): %d" % n_rw)
for lg in sorted(RW):
    print("   ", lg.replace(S, "S"))
print("map rows: %d -> %s" % (len(rows), out))
