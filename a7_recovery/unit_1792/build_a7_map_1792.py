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
OLD = R + "/a7_recovery/unit_1781"
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
          UNIT + "/out/private_agents/wf_85692dcf-0e8",
      # the resumed batch's own transcripts, from the PUBLISHED unit_1786
      # capture rather than the live session, so the candidate is reproducible
      # from frozen bytes and the live directory is never reached
      SESS + "/subagents/workflows/wf_41b934cf-f76":
          UNIT + "/out/private_agents/wf_41b934cf-f76"}

rows, demoted = [], []
for ln in io.open(OLD + "/a7_map_1781.tsv", encoding="utf-8").read().splitlines():
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
#: the SAME logical run identity, backed by a DIFFERENT durable output. The
#: candidate needs a fresh one because a root is frozen once and this one
#: carries each lane's expected input.
TARGET = {"proposed": "proposed_run", "candidate": "candidate_run_1794",
          "candidate_intake": "candidate_run_1794"}
variant = sys.argv[1] if len(sys.argv) > 1 else ""
if variant in TARGET:
    rows = [r for r in rows if not r.startswith(S + "/g1_precall_run_1525\t")]
    src = UNIT + "/out/" + TARGET[variant]
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([S + "/g1_precall_run_1525", src,
                           boundary.source_sha(src), "rw"]))
elif variant:
    raise SystemExit("REFUSED: unknown variant %r (known: %s)"
                     % (variant, ", ".join(sorted(TARGET))))
if variant == "candidate_intake":
    # A SCOPED OVERRIDE, mounted last and read-only over the run this unit
    # writes: the segment-4 intake must resolve to the EXACT immutable file the
    # native call actually executed, not to a byte-identical copy of it. The
    # boundary mounts rows in file order and supports exactly this. Nothing is
    # written to it and no file on disk is moved or relinked.
    src = OLD + "/out/proposed_run/grade_batch.seg04.js"
    rows.append("\t".join([S + "/g1_precall_run_1525/grade_batch.seg04.js",
                           src, boundary.source_sha(src), "ro"]))
out = UNIT + ("/a7_map_1792_%s.tsv" % variant if variant else "/a7_map_1792.tsv")
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
n_rw = sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")
print("published unit_1778 outputs demoted to read-only: %d" % len(demoted))
print("writable (all unit_1792-only): %d" % n_rw)
for lg in sorted(RW):
    print("   ", lg.replace(S, "S").replace(SESS, "SESS"))
print("map rows: %d -> %s" % (len(rows), out))
