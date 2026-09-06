# -*- coding: utf-8 -*-
"""The G1 correction bind map (Codex SEQ 1781), derived from the PUBLISHED
unit_1778 map. Every published source stays read-only; the only writable rows
are this unit's own private view and output.

The workflow-state directory is writable HERE because the cached-row fixture
must be presented at the runtime's own official location for the audit's
location check to apply at all - so this unit gets its OWN copy of that view,
and the published one is never touched.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
OLD = R + "/a7_recovery/unit_1778"
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
      S + "/g1_run_1525.py": UNIT + "/view/scratchpad/g1_run_1525.py"}
RW = {SESS + "/workflows": UNIT + "/view/workflows",
      S + "/g1_precall_run_1525": UNIT + "/out/g1_precall_run_1525",
      "/tmp/a7_logs_1781": UNIT + "/logs",
      # ONE run's agent directory, privately writable, so the metadata and
      # transcript negatives can corrupt a COPY - never the published evidence
      SESS + "/subagents/workflows/wf_85692dcf-0e8":
          UNIT + "/out/private_agents/wf_85692dcf-0e8"}

rows, demoted = [], []
for ln in io.open(OLD + "/a7_map_1778.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg in RO or lg in RW:
        continue
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))
for lg, src in sorted(RO.items()):
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
for lg, src in sorted(RW.items()):
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))
variant = len(sys.argv) > 1 and sys.argv[1] == "proposed"
if variant:
    # the SAME logical run identity, backed by a NEW durable physical output
    rows = [r for r in rows if not r.startswith(S + "/g1_precall_run_1525\t")]
    src = UNIT + "/out/proposed_run"
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([S + "/g1_precall_run_1525", src,
                           boundary.source_sha(src), "rw"]))
out = UNIT + ("/a7_map_1781_proposed.tsv" if variant else "/a7_map_1781.tsv")
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
n_rw = sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")
print("published unit_1778 outputs demoted to read-only: %d" % len(demoted))
print("writable (all unit_1781-only): %d" % n_rw)
for lg in sorted(RW):
    print("   ", lg.replace(S, "S").replace(SESS, "SESS"))
print("map rows: %d -> %s" % (len(rows), out))
