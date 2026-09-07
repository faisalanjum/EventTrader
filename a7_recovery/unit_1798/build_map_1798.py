# -*- coding: utf-8 -*-
"""This unit's bind map, derived from the PUBLISHED unit_1792 candidate map.

Nothing is copied: the harness, coordinator, workflow view and the finished
candidate run are all bound BY REFERENCE from the published checkpoint, and the
only writable rows are this unit's own logs and its own new run directory.
The finished candidate run is demoted to read-only - it is published evidence.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
SRC = R + "/a7_recovery/unit_1792/a7_map_1792_candidate.tsv"
UNIT = os.path.dirname(os.path.abspath(__file__))
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

READONLY_NOW = R + "/a7_recovery/unit_1792/out/candidate_run_1794"
LOGS = "/tmp/a7_logs_1781"
rows, demoted = [], []
for ln in io.open(SRC, encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg == LOGS:
        src, mode = UNIT + "/logs", "rw"
        os.makedirs(src, exist_ok=True)
        sha = boundary.source_sha(src)
    elif mode == "rw" and src == READONLY_NOW:
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    elif mode == "rw":
        # every other writable row in the source map belongs to the published
        # unit_1792; this unit reads them and writes nothing back
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))
#: the SAME logical run identity, backed by THIS unit's own fresh output
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
RUN_LOGICAL = S + "/g1_precall_run_1525"
SEG4 = R + "/a7_recovery/unit_1781/out/proposed_run/grade_batch.seg04.js"
variant = sys.argv[1] if len(sys.argv) > 1 else ""
if variant:
    src = UNIT + "/out/run_1798"
    os.makedirs(src, exist_ok=True)
    rows = [r for r in rows if not r.startswith(RUN_LOGICAL + "\t")]
    rows.append("\t".join([RUN_LOGICAL, src, boundary.source_sha(src), "rw"]))
if variant == "intake":
    # the scoped read-only override, mounted LAST: segment 4's intake must
    # resolve to the exact immutable script the native call executed
    rows.append("\t".join([RUN_LOGICAL + "/grade_batch.seg04.js", SEG4,
                            boundary.source_sha(SEG4), "ro"]))
out = UNIT + ("/a7_map_1798_%s.tsv" % variant if variant else "/a7_map_1798.tsv")
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("rows %d, demoted to read-only %d, writable %d -> %s"
      % (len(rows), len(demoted),
         sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw"), out))
