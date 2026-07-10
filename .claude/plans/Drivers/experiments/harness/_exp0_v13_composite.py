#!/usr/bin/env python3
"""EXP-0 v1.3 COMPOSITE scorer + recorder (0 LLM). Fable O10-2 ruling.
Composite = run-2 judgments on the 159 UNCHANGED records + 3 fresh kp_0022(v1.3) judgments, scored vs the v1.3 key.
args: RUNDIR KEY RUN2 RET   (RET = the 3-call workflow return JSON, uploaded)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, "harness")
import key_lint as K  # noqa

RUNDIR, KEY, RUN2, RET = sys.argv[1:5]
EXP = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments"
PY = "/home/faisal/EventMarketDB/venv/bin/python3"
ARMS = ["g_sonnet_a", "g_sonnet_b", "g_opus"]


def find_key(o, k):
    if isinstance(o, str):
        s = o.strip()
        if s and s[0] in "[{":
            try:
                return find_key(json.loads(s), k)
            except Exception:
                return None
        return None
    if isinstance(o, dict):
        if k in o:
            return o[k]
        for v in o.values():
            r = find_key(v, k)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find_key(v, k)
            if r is not None:
                return r
    return None


kp = find_key(json.load(open(RET)), "kp_0022_v13")
if not kp or not all(a in kp and kp[a] for a in ARMS):
    print("ABORT: could not find all 3 kp_0022_v13 verdicts in RET", file=sys.stderr)
    sys.exit(3)
os.makedirs(RUNDIR, exist_ok=True)
json.dump({"kp_0022_v13": kp}, open(RUNDIR + "/kp0022_v13_verdicts.json", "w"), indent=2, sort_keys=True)

# ---- build composite verdict files: run-2's 160 with kp_0022 replaced by the fresh v1.3 verdict ----
for a in ARMS:
    b = json.load(open(RUN2 + "/verdicts." + a + ".json"))
    v = kp[a]
    for x in b["verdicts"]:
        if x["pair_id"] == "kp_0022":
            x["verdict"] = v["verdict"]; x["cited_a"] = v.get("cited_a"); x["cited_b"] = v.get("cited_b")
            x["reason"] = "[kp_0022 v1.3 fresh] " + (v.get("reason") or "")
    b["run_id"] = os.path.basename(RUNDIR.rstrip("/"))
    b["composite"] = "run-2 (v1.2) 159 unchanged + kp_0022(v1.3) fresh"
    b["invalid"] = sum(1 for x in b["verdicts"] if x["verdict"] not in ("SAME", "DIFFERENT"))
    b["judged"] = 160 - b["invalid"]
    b["counts"] = {"SAME": sum(1 for x in b["verdicts"] if x["verdict"] == "SAME"),
                   "DIFFERENT": sum(1 for x in b["verdicts"] if x["verdict"] == "DIFFERENT"), "INVALID": b["invalid"]}
    json.dump(b, open(RUNDIR + "/verdicts." + a + ".json", "w"), separators=(",", ":"))

# ---- score the composite vs the v1.3 key ----
r = subprocess.run([PY, "harness/scorers/score_exp0.py", "--run", RUNDIR, "--key", KEY,
                    "--lock", "keys/K-pairs/K-pairs.v1.3.lock.json", "--protocol", "keys/K-pairs/protocol.md"],
                   cwd=EXP, capture_output=True, text=True)
print(r.stdout.strip())
if r.stderr.strip():
    print("SCORER_STDERR", r.stderr.strip()[:400])
scores = json.load(open(RUNDIR + "/scores.json"))
pa = scores["per_arm"]

# ---- pre-registered composite outcome ----
kp_verdicts = {a: kp[a]["verdict"] for a in ARMS}
all_diff = all(kp_verdicts[a] == "DIFFERENT" for a in ARMS)
sonnet_pass = pa["g_sonnet_a"]["pass"] and pa["g_sonnet_b"]["pass"]
if all_diff and sonnet_pass:
    outcome = "RATIFY_SONNET_TIER"
elif not all_diff:
    outcome = "STOP_kp0022_SAME_by_" + ",".join(a for a in ARMS if kp_verdicts[a] == "SAME")
else:
    outcome = "STOP_sonnet_tier_failed_other"

# ---- wm exhibits for the two run-2 wrong-SAMEs (key_erratum) ----
exdir = EXP + "/exhibits"
os.makedirs(exdir, exist_ok=True)
run2_kp = {}
for a in ARMS:
    b = json.load(open(RUN2 + "/verdicts." + a + ".json"))
    run2_kp[a] = next((x for x in b["verdicts"] if x["pair_id"] == "kp_0022"), None)
wrong_same_arms = [a for a in ("g_sonnet_b", "g_opus") if run2_kp[a] and run2_kp[a]["verdict"] == "SAME"]
wm_ids = []
for i, a in enumerate(wrong_same_arms, 1):
    wmid = "wm_exp0_%04d" % i
    wm_ids.append(wmid)
    json.dump({"id": wmid, "exp_id": "EXP-0", "arm": a, "case_ref": "kp_0022 (v1.2 defective item; re-anchored in v1.3)",
               "family": "deferred_recognized", "target_visible": False,
               "model_output": {"verdict": "SAME", "cited_a": run2_kp[a].get("cited_a"), "cited_b": run2_kp[a].get("cited_b"), "reason": run2_kp[a].get("reason")},
               "gold": {"gold": "DIFFERENT", "note": "deferred liability (obligation) vs recognized income"},
               "fable_review": {"verdict": "key_erratum", "note": "Fair reading of a DEFECTIVE item: the v1.2 quote emphasized the recognition PATTERN (amortize/ratable) and hid the deferred-liability nature, so the arm's SAME was reasonable. Fixed in v1.3 (side_a re-anchored to 'sit as an obligation'). Run-2 scores.json is NEVER retro-edited; this exhibit excuses the miss."}},
              open(exdir + "/" + wmid + ".json", "w"), indent=2, sort_keys=True)

# ---- O10 memo: Sonnet B's one false_refusal pair + reason ----
sb = json.load(open(RUN2 + "/verdicts.g_sonnet_b.json"))
gold = {rr["pair_id"]: rr for _l, rr in K.load_records(KEY)}
sb_fr = [x for x in sb["verdicts"] if gold.get(x["pair_id"], {}).get("gold") == "SAME" and x["verdict"] == "DIFFERENT"]
o10_memo = {"sonnet_b_false_refusal": [{"pair_id": x["pair_id"], "family": gold[x["pair_id"]]["family"],
                                        "side_a": gold[x["pair_id"]]["side_a"]["name"], "side_b": gold[x["pair_id"]]["side_b"]["name"],
                                        "verdict": x["verdict"], "reason": x.get("reason")} for x in sb_fr],
            "note": "Sonnet B's single false-refusal in run-2 (within the <=10% bar: 1/50=0.02). Recorded per Fable for the O10 memo."}
json.dump(o10_memo, open(RUNDIR + "/o10_memo.json", "w"), indent=2, sort_keys=True)

# ---- augment decision.json ----
dec = json.load(open(RUNDIR + "/decision.json"))
dec["composite"] = {"basis": "run-2 (v1.2) 159 unchanged verdicts + 3 fresh kp_0022(v1.3) judgments, scored vs v1.3 key",
                    "kp_0022_v13_verdicts": kp_verdicts, "all_three_DIFFERENT": all_diff,
                    "outcome_v13": outcome, "sonnet_tier_pass": sonnet_pass,
                    "wm_exhibits_key_erratum": wm_ids, "o10_memo_ref": "o10_memo.json", "fable_signoff": None}
json.dump(dec, open(RUNDIR + "/decision.json", "w"), indent=2, sort_keys=True)

# ---- budget ----
bp = EXP + "/BUDGET.json"
bud = json.load(open(bp)); bud.setdefault("entries", []); bud.setdefault("totals", {"all": 0, "strong_tier": 0})
if not any(e.get("run_id") == os.path.basename(RUNDIR.rstrip("/")) for e in bud["entries"]):
    bud["entries"].append({"pkg": "EXP-0-v1.3-composite", "run_id": os.path.basename(RUNDIR.rstrip("/")), "effort": "high",
                           "fresh_calls": 3, "by_model": {"claude-sonnet-5": 2, "claude-opus-4-8": 1},
                           "composite": "477 run-2 reused + 3 fresh", "outcome": outcome})
    bud["totals"]["all"] = bud["totals"].get("all", 0) + 3
json.dump(bud, open(bp, "w"), indent=2, sort_keys=True)

print("KP_0022_V13", json.dumps(kp_verdicts, sort_keys=True))
print("ALL_DIFFERENT", all_diff, "| SONNET_TIER_PASS", sonnet_pass)
print("PER_ARM", json.dumps({a: {"ws": pa[a]["wrong_same"], "fr": pa[a]["false_refusal"], "inv": pa[a]["invalid"], "pass": pa[a]["pass"]} for a in ARMS}, sort_keys=True))
print("OUTCOME", outcome, "| wm_exhibits", wm_ids, "| o10_memo sonnet_b_fr", [x["pair_id"] for x in o10_memo["sonnet_b_false_refusal"]])
