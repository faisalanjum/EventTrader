#!/usr/bin/env python3
"""EXP-0 post-run diagnostic (why the gate failed) + finalize manifest/budget/status (0 LLM). args: RUNDIR KEY"""
import json
import sys

sys.path.insert(0, "harness")
import key_lint as K

RUNDIR, KEY = sys.argv[1], sys.argv[2]
EXP = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments"
recs = {r["pair_id"]: r for _l, r in K.load_records(KEY)}
gold_same = [pid for pid, r in recs.items() if r["gold"] == "SAME"]
arms = ["g_sonnet_a", "g_sonnet_b", "g_opus"]
V = {a: {v["pair_id"]: v for v in json.load(open(RUNDIR + "/verdicts." + a + ".json"))["verdicts"]} for a in arms}
rows = []
for pid in gold_same:
    ver = {a: V[a][pid]["verdict"] for a in arms}
    nd = sum(1 for a in arms if ver[a] == "DIFFERENT")
    rows.append((pid, bool(recs[pid].get("hard")), nd, ver))
by_all = sorted([r for r in rows if r[2] == 3], key=lambda x: x[0])
by_any = [r for r in rows if r[2] >= 1]
easy_refused = [r for r in by_any if not r[1]]
print("DIAG gold_SAME %d | refused_by_all3 %d | refused_by>=1 %d | hard_among_refused %d | EASY_among_refused %d"
      % (len(gold_same), len(by_all), len(by_any), sum(1 for r in by_any if r[1]), len(easy_refused)))
print("--- SYSTEMATIC (all 3 arms refused) ---")
for pid, hard, nd, ver in by_all:
    print("  ", pid, "hard=%s" % hard, recs[pid]["side_a"]["name"], "<->", recs[pid]["side_b"]["name"])
print("--- EASY (non-hard) SAME refused by any arm (would be a real grader problem) ---")
for pid, hard, nd, ver in easy_refused:
    print("  ", pid, "n_diff=%d" % nd, recs[pid]["side_a"]["name"], "<->", recs[pid]["side_b"]["name"])
print("--- sample Opus reasons on systematic refusals ---")
for pid, hard, nd, ver in by_all[:5]:
    print("  ", pid, repr(V["g_opus"][pid].get("reason"))[:180])

# --- finalize ---
scores = json.load(open(RUNDIR + "/scores.json"))
mf = RUNDIR + "/manifest.json"
m = json.load(open(mf))
m["status"] = "scored_gate_FAIL"
m["pre_call_confirmations"]["6_outputs_plan"]["saved"] = True
m["result"] = {"gate_pass": scores["gate"]["pass"], "grader_tier": scores["metrics"]["grader_tier"],
               "per_arm": {a: {k: scores["per_arm"][a][k] for k in ("wrong_same", "false_refusal", "false_refusal_rate", "invalid", "pass")} for a in arms},
               "diagnostic": {"gold_same": len(gold_same), "refused_by_all3": len(by_all), "refused_by_any": len(by_any),
                              "easy_same_refused": len(easy_refused), "verdicts_hash_verified": True}}
m["counts"]["made_calls"] = sum(scores["per_arm"][a]["n"] for a in arms) + len(arms)
json.dump(m, open(mf, "w"), indent=2, sort_keys=True)

bp = EXP + "/BUDGET.json"
try:
    bud = json.load(open(bp))
except Exception:
    bud = {"global_cap": 4000, "abort_at": 6000, "entries": [], "totals": {"all": 0, "strong_tier": 0}}
bud.setdefault("entries", [])
bud.setdefault("totals", {"all": 0, "strong_tier": 0})
if not any(e.get("pkg") == "EXP-0" and e.get("run_id") == m["run_id"] for e in bud["entries"]):
    bud["entries"].append({"pkg": "EXP-0", "run_id": m["run_id"], "strong_grader_calls": 480, "record_clerk_calls": 3,
                           "preflight_probe_calls": 3, "by_model": {"claude-sonnet-5": 320, "claude-opus-4-8": 163},
                           "invalid": 0, "gate": "FAIL", "subagent_tokens_approx": 15580676})
    bud["totals"]["strong_tier"] = bud["totals"].get("strong_tier", 0) + 480
    bud["totals"]["all"] = bud["totals"].get("all", 0) + 486
json.dump(bud, open(bp, "w"), indent=2, sort_keys=True)

with open(EXP + "/WORKORDER_STATUS.md", "a") as fh:
    fh.write("\n- %s EXP-0 RAN (K-pairs.v1.1 sha 400f4dd9). 480 grader calls + 3 record, 0 invalid, files hash-verified. "
             "GATE=FAIL tier=none: wrong_same 0/110 on ALL arms (zero over-merge); false_refusal FAILS the <=10%% bar "
             "(sonnet_a 21/50, sonnet_b 24/50, opus 8/50) -> graders over-SPLIT true synonyms. STOP: no qualified grader "
             "tier <= Opus; all downstream graded scoring blocked pending Fable failure-action / O10 decision.\n" % m["run_id"])
print("FINALIZED: status scored_gate_FAIL; made_calls", m["counts"]["made_calls"])
