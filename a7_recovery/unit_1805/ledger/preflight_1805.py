# -*- coding: utf-8 -*-
"""G.preflight for segment 6 against the EXTERNAL pinned root and receipt."""
import collections, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
CAND, RUN, OUT = S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525", "/tmp/a7_logs_1781"
DURABLE = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1803/"
           "out/run_1803/grade_batch.seg06.js")
ROOT = "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0"
RECEIPT = "2b0e8a4153a2d32461f5630a7821e6d29bbb831a82a7f8859ac7f212b50677fb"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402
packet, problems = G.preflight(CAND, RUN, 6, ROOT, RECEIPT)
logical = packet["scriptPath"] if packet else None
same = bool(logical) and os.path.isfile(DURABLE) and os.path.samefile(logical, DURABLE)
doc = collections.OrderedDict([
    ("pinned_root", ROOT), ("pinned_receipt", RECEIPT),
    ("problems", problems), ("zero_problems", not problems),
    ("logical_script_path", logical), ("durable_script_path", DURABLE),
    ("paths_differ", logical != DURABLE), ("same_regular_file", same),
    ("args_rows", len(packet["args"]) if packet else None),
    ("first_lane", packet["args"][0]["lane_id"] if packet else None),
    ("last_lane", packet["args"][-1]["lane_id"] if packet else None)])
io.open(OUT + "/PREFLIGHT_1805.json", "w", encoding="utf-8").write(
    json.dumps(doc, indent=1) + "\n")
print("  problems: %s" % (problems or "none"))
print("  SAME FILE as the durable script: %s (paths differ: %s)" % (same, doc["paths_differ"]))
print("  args rows %s  %s .. %s" % (doc["args_rows"], doc["first_lane"], doc["last_lane"]))
sys.exit(0 if (not problems and same) else 1)
