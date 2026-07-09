#!/usr/bin/env python3
"""EXP-0: assemble the 3-arm BLIND projection for the embedded-pairs grader run (0 LLM, no Neo4j).
Emits [{arm, model, n, page_h32, pairs:[blind]}] where pairs come from key_lint.project_blind (gold/family/
provenance/rival already stripped). page_h32 lets the workflow self-verify embedding integrity."""
import json
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/harness")
import key_lint as KL

KEY = sys.argv[1]
OUT = sys.argv[2]
ARMDEFS = [("g_sonnet_a", "sonnet"), ("g_sonnet_b", "sonnet"), ("g_opus", "opus")]
out = []
for arm, model in ARMDEFS:
    pairs, ph = KL.project_blind(KEY, arm)
    out.append({"arm": arm, "model": model, "n": len(pairs), "page_h32": ph, "pairs": pairs})
json.dump(out, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)
print("ASSEMBLED", [(o["arm"], o["n"], o["page_h32"]) for o in out], file=sys.stderr)
