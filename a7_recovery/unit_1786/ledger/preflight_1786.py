# -*- coding: utf-8 -*-
"""The read-only pre-call verification (Codex SEQ 1786). No call is made."""
import hashlib, io, json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
CAND = S + "/g1_precall_cand_1525"
RUN = S + "/g1_precall_run_1525"
DURABLE = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1781/"
           "out/proposed_run/grade_batch.seg04.js")
OUT = "/tmp/a7_logs_1786"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
#: EXTERNALLY supplied by Codex 1786 - not read back as their own expectation
ROOT = "cb161efeab864d109d47e9134012132ba0cda1a21673dcca0758dcceb3c9b9fb"
RECEIPT = "208b1dd490058224d2566a95c3f9b5f7ce6751c8afc1cbc41ca64dbeb7e5e5a3"
SCRIPT = "36c3e792270693b1a1749ee63ab3ce2efb0e26fbd5767978de8903c2ec7a1757"
ARGS = "3d0a7d57a8196e22842046b9eadbe2cfb044d434ae2aee48c54a393f36433a52"
ENVELOPE = "59525cdb10f82c95431e98344ad68f93dc1f969bef71e34d1c53ab8db0fa152c"
import a7_g1_build as G                                          # noqa: E402
C = []


def ck(name, got, want):
    C.append((name, got == want, str(got)[:70]))
    print("  %-5s %-22s %s" % ("ok" if got == want else "BAD", name, str(got)[:66]))


packet, problems = G.preflight(CAND, RUN, 4, ROOT, RECEIPT)
ck("preflight_problems", problems, [])
if problems:
    sys.exit(1)
ck("script_sha", G._sha_file(packet["scriptPath"]), SCRIPT)
ck("script_bytes", os.path.getsize(packet["scriptPath"]), 520690)
args = packet["args"]
ck("args_type", type(args).__name__, "list")
ck("args_rows", len(args), 34)
ck("args_sha", hashlib.sha256(json.dumps(args, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest(), ARGS)
lanes = [a["lane_id"] for a in args]
ck("first_lane", lanes[0], "G1-041/G1a")
ck("last_lane", lanes[-1], "G1-057/G1b")
ck("unique_lanes", len(set(lanes)), 34)
# the packet carries no hidden keys beyond the published arg schema
keys = {k for a in args for k in a}
ck("arg_keys", sorted(keys), sorted({"agentType", "attempt", "batch_id",
    "candidate_sha256", "disallowedTools", "effort", "lane_id",
    "max_output_tokens", "model", "ordinal", "prompt_sha256", "runtime_model_id"}))
env = {"args": args, "resumeFromRunId": "wf_41b934cf-f76", "scriptPath": DURABLE}
blob = json.dumps(env, sort_keys=True, separators=(",", ":")).encode()
ck("envelope_sha", hashlib.sha256(blob).hexdigest(), ENVELOPE)
ck("envelope_bytes", len(blob), 13440)
# THE REAL same-file check: the logical path in here IS the durable file
same = os.path.exists(DURABLE) and os.path.samefile(packet["scriptPath"], DURABLE)
ck("logical_is_durable_same_file", same, True)
ck("paths_actually_differ", packet["scriptPath"] != DURABLE, True)
os.makedirs(OUT, exist_ok=True)
io.open(OUT + "/PRECALL_IDENTITIES.json", "w", encoding="utf-8").write(json.dumps(
    {"root_sha256": ROOT, "receipt_seg04_sha256": RECEIPT, "script_sha256": SCRIPT,
     "args_canonical_sha256": ARGS, "envelope_sha256": ENVELOPE,
     "envelope_bytes": 13440, "lanes": lanes,
     "logical_script_path": packet["scriptPath"], "durable_script_path": DURABLE,
     "same_file": same, "checks": [{"name": n, "ok": k} for n, k, _g in C]},
    indent=1) + "\n")
bad = [n for n, k, _g in C if not k]
print("\n%d checks, %d bad %s" % (len(C), len(bad), bad or ""))
sys.exit(1 if bad else 0)
