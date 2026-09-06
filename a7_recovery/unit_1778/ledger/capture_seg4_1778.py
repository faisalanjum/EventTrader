# -*- coding: utf-8 -*-
"""Capture the prepared segment-4 artefacts durably, without launching anything."""
import hashlib, io, json, os, shutil
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
RUN = S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1778/seg4_prepared"
os.makedirs(OUT, exist_ok=True)
rec = {}
for src, name in ((S + "/g1_args_seg04.json", "g1_args_seg04.json"),
                  (RUN + "/grade_batch.seg04.js", "grade_batch.seg04.js"),
                  (RUN + "/receipt.seg04.json", "receipt.seg04.json"),
                  (RUN + "/reservation.seg04.json", "reservation.seg04.json")):
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(OUT, name))
        b = io.open(src, "rb").read()
        rec[name] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
# the args file lives in the ephemeral namespace tmpfs, so it is re-derived
# through the SAME owner call prepare used - no launch, no new decision
import sys
sys.path.insert(0, S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3")
sys.path.insert(0, "/home/faisal/EventMarketDB")
import a7_g1_build as G
rsha = G._sha_file(G.root_path(RUN))
receipt_sha = G._sha_file(os.path.join(RUN, "receipt.seg04.json"))
packet, problems = G.preflight(S + "/g1_precall_cand_1525", RUN, 4, rsha, receipt_sha)
if problems:
    raise SystemExit("REFUSED preflight: %s" % problems[:3])
args = packet["args"]
io.open(os.path.join(OUT, "g1_args_seg04.json"), "w", encoding="utf-8").write(
    json.dumps(args))
rec["root_sha256"] = rsha
rec["receipt_seg04_sha256"] = receipt_sha
rec["script_path"] = packet["scriptPath"]
rec["args_rows"] = len(args)
rec["args_lanes"] = sorted({a["lane_id"] for a in args})
io.open("/tmp/a7_logs_1778/SEG4_PREPARED.json", "w", encoding="utf-8").write(
    json.dumps(rec, indent=1) + "\n")
for k, v in rec.items():
    print("  %-26s %s" % (k, v if not isinstance(v, list) else "%d lanes" % len(v)))
