#!/usr/bin/env python3
"""EXP-0 contested-pair evidence assembler for Fable re-adjudication (READ-ONLY, 0 LLM). args: RUNDIR KEY SIDECAR"""
import json
import os
import sys

sys.path.insert(0, "harness")
import key_lint as K

RUNDIR, KEY, SIDECAR = sys.argv[1], sys.argv[2], sys.argv[3]
recs = {r["pair_id"]: r for _l, r in K.load_records(KEY)}
side = {}
if os.path.exists(SIDECAR):
    for l in open(SIDECAR, encoding="utf-8"):
        l = l.strip()
        if l:
            s = json.loads(l); side[s["pair_id"]] = s
arms = ["g_sonnet_a", "g_sonnet_b", "g_opus"]
V = {a: {v["pair_id"]: v for v in json.load(open(RUNDIR + "/verdicts." + a + ".json"))["verdicts"]} for a in arms}
gold_same = [pid for pid, r in recs.items() if r["gold"] == "SAME"]

contested = []
for pid in gold_same:
    ver = {a: V[a][pid]["verdict"] for a in arms}
    refusers = [a for a in arms if ver[a] == "DIFFERENT"]
    if not refusers:
        continue
    r = recs[pid]
    contested.append({
        "pair_id": pid, "hard": bool(r.get("hard")),
        "refused_by": [a.replace("g_", "") for a in refusers],
        "refused_by_all3": len(refusers) == 3, "refused_by_opus": "g_opus" in refusers, "n_refused": len(refusers),
        "side_a": {"name": r["side_a"]["name"], "quotes": r["side_a"]["quotes"]},
        "side_b": {"name": r["side_b"]["name"], "quotes": r["side_b"]["quotes"]},
        "gold": "SAME", "gold_rationale": r.get("gold_rationale"),
        "fable_sidecar": side.get(pid, {}).get("fable"),
        "graders": {a.replace("g_", ""): {"verdict": ver[a], "reason": V[a][pid].get("reason"),
                                          "cited_a": V[a][pid].get("cited_a"), "cited_b": V[a][pid].get("cited_b")} for a in arms},
    })
contested.sort(key=lambda c: (-c["n_refused"], c["pair_id"]))

sa_ref = [c["pair_id"] for c in contested if "sonnet_a" in c["refused_by"]]
sb_ref = [c["pair_id"] for c in contested if "sonnet_b" in c["refused_by"]]
op_ref = [c["pair_id"] for c in contested if "opus" in c["refused_by"]]


def min_flips_tier(refsets, bar=5):
    rem = [set(rs) for rs in refsets]
    pids = set().union(*[set(rs) for rs in refsets])
    cnt = 0
    while any(len(r) > bar for r in rem):
        best, cov = None, -1
        for p in pids:
            c = sum(1 for r in rem if p in r and len(r) > bar)
            if c > cov:
                cov, best = c, p
        if best is None or cov <= 0:
            break
        for r in rem:
            r.discard(best)
        pids.discard(best); cnt += 1
    return cnt


out = {
    "run_id": RUNDIR.rstrip("/").split("/")[-1], "key": "K-pairs.v1.1.jsonl (sha 400f4dd9)", "gate": "FAIL (no tier qualifies)",
    "invariants": {"wrong_same_per_arm_over_110": {a.replace("g_", ""): 0 for a in arms},
                   "wrong_same_note": "0/110 for EVERY arm -- zero over-merge (the dangerous error never happened)",
                   "invalid_per_arm": {a.replace("g_", ""): 0 for a in arms}},
    "false_refusal_over_50": {"sonnet_a": len(sa_ref), "sonnet_b": len(sb_ref), "opus": len(op_ref), "bar": "<=5 (10% of 50)"},
    "gold_same_total": len(gold_same), "contested_count": len(contested),
    "hard_among_contested": sum(1 for c in contested if c["hard"]), "refused_by_all3": sum(1 for c in contested if c["refused_by_all3"]),
    "pass_analysis": {"opus_min_SAME_to_DIFFERENT_flips_to_pass": max(0, len(op_ref) - 5), "opus_refused_pids": sorted(op_ref),
                      "sonnet_tier_min_flips_to_pass": min_flips_tier([set(sa_ref), set(sb_ref)]),
                      "note": "A 'flip' = a gold-SAME pair whose label moves to DIFFERENT, making the refusal correct (removes it from false_refusal and adds no wrong_same for the arm that refused it). Opus flips come from its own 8-refused set; the Sonnet tier requires BOTH instances <=5."},
    "execution_note_for_O10": "EXP-0 graders ran under DEFAULT Claude Code workflow thinking settings; NO explicit thinking-effort / reasoning-budget was set for Sonnet or Opus (agent() called with model + schema only, no effort option). Flag for O10 reproducibility review -- a different reasoning budget could shift verdicts.",
    "contested": contested,
}
json.dump(out, open(RUNDIR + "/contested_evidence.json", "w"), indent=2, sort_keys=True)

print("CONTESTED %d of %d gold-SAME | hard %d | refused_by_all3 %d" % (len(contested), len(gold_same), out["hard_among_contested"], out["refused_by_all3"]))
print("false_refusal: sonnet_a %d  sonnet_b %d  opus %d  (bar<=5)" % (len(sa_ref), len(sb_ref), len(op_ref)))
print("MIN FLIPS to pass: opus %d | sonnet_tier %d" % (out["pass_analysis"]["opus_min_SAME_to_DIFFERENT_flips_to_pass"], out["pass_analysis"]["sonnet_tier_min_flips_to_pass"]))
for c in contested:
    print("\n%s hard=%s n=%d by=%s" % (c["pair_id"], c["hard"], c["n_refused"], ",".join(c["refused_by"])))
    print("  A %s :: %s" % (c["side_a"]["name"], " || ".join(c["side_a"]["quotes"])))
    print("  B %s :: %s" % (c["side_b"]["name"], " || ".join(c["side_b"]["quotes"])))
    print("  GOLD: %s" % c["gold_rationale"])
    for a in ("sonnet_a", "sonnet_b", "opus"):
        g = c["graders"][a]
        print("  %-9s %s -- %s" % (a, g["verdict"], (g["reason"] or "")[:210]))
