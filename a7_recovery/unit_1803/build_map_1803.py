# -*- coding: utf-8 -*-
"""This unit's bind map, derived from the committed unit_1798 candidate map.

Everything published is bound read-only BY REFERENCE. The only writable rows
are this unit's own mutable run and its logs. Two scoped read-only overrides,
mounted last, make each segment's logical script resolve to the EXACT durable
file that actually executed rather than to a same-byte copy.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
A = R + "/a7_recovery"
SRC = A + "/unit_1798/a7_map_1798_candidate.tsv"
UNIT = os.path.dirname(os.path.abspath(__file__))
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
        "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
RUN_LOGICAL = S + "/g1_precall_run_1525"
LOGS = "/tmp/a7_logs_1781"
NEW_RID = "wf_feabb3a2-628"
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

#: the executed scripts, by segment: each logical path must resolve to these
EXECUTED = {
    4: A + "/unit_1781/out/proposed_run/grade_batch.seg04.js",
    5: A + "/unit_1798/out/run_1798/grade_batch.seg05.js",
}
rows, demoted = [], []
for ln in io.open(SRC, encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg == LOGS:
        src = UNIT + "/logs"
        os.makedirs(src, exist_ok=True)
        rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))
        continue
    if lg == RUN_LOGICAL:
        src = UNIT + "/out/run_1803"
        rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))
        continue
    if lg == SESS + "/workflows":
        src = UNIT + "/view/workflows"
    if lg == SESS + "/subagents/workflows":
        # the SAME assembly, composed for this unit: the published 624 runs plus
        # the verified new one. A child mountpoint cannot be created inside a
        # read-only parent bind, so the new run is exposed HERE, not by an extra
        # row - and the two existing child overrides still apply on top.
        src = UNIT + "/view/subagent_runs"
    if mode == "rw":
        demoted.append(lg)
    mode, sha = "ro", boundary.source_sha(src)
    rows.append("\t".join([lg, src, sha, mode]))

#: mounted LAST: the exact executed scripts, over this unit's mutable run
for n, src in sorted(EXECUTED.items()):
    rows.append("\t".join([RUN_LOGICAL + "/grade_batch.seg%02d.js" % n, src,
                           boundary.source_sha(src), "ro"]))
out = UNIT + "/a7_map_1803.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("rows %d, demoted to read-only %d, writable %d, scoped overrides %d -> %s"
      % (len(rows), len(demoted),
         sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw"), len(EXECUTED), out))
