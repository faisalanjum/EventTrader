#!/usr/bin/env python3
"""EXP-0 scorer + gate (0 LLM, no network). WorkOrder section 4 EXP-0.

Reads the three arm verdict files (verdicts.g_sonnet_a.json / _b / g_opus.json) from a run dir, joins to the
LOCKED K-pairs.v1 gold, RE-VERIFIES the key sha (section 1.4), computes per-arm wrong_same / false_refusal /
invalid_rate + a per-family table + the sonnet shared_miss, and applies the gate:

  EXISTS tier T: for every instance g in T: wrong_same(g)==0 AND false_refusal(g)<=0.10 AND invalid_rate(g)<=0.02
  (sonnet tier = BOTH instances g_sonnet_a & g_sonnet_b ; opus tier = g_opus alone.)

Writes scores.json + decision.json. Never edits the key. O10 blindness discounts are Fable's (left null)."""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # harness/
import key_lint

ARMS = ["g_sonnet_a", "g_sonnet_b", "g_opus"]
VALID = ("SAME", "DIFFERENT")


def sha256_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_verdicts(path):
    if not os.path.exists(path):
        return None
    blob = json.load(open(path, encoding="utf-8"))
    rows = blob.get("verdicts") if isinstance(blob, dict) else blob
    out = {}
    for r in (rows or []):
        v = r.get("verdict")
        out[r.get("pair_id")] = v if v in VALID else None
    return out


def score_arm(gold, verd):
    n = len(gold)
    invalid = wrong_same = false_refusal = 0
    fam = {}
    for pid, g in gold.items():
        v = verd.get(pid) if verd else None
        f = fam.setdefault(g["family"], {"n": 0, "wrong_same": 0, "false_refusal": 0, "invalid": 0})
        f["n"] += 1
        if v not in VALID:
            invalid += 1; f["invalid"] += 1; continue
        if g["gold"] == "DIFFERENT" and v == "SAME":
            wrong_same += 1; f["wrong_same"] += 1
        if g["gold"] == "SAME" and v == "DIFFERENT":
            false_refusal += 1; f["false_refusal"] += 1
    n_diff = sum(1 for g in gold.values() if g["gold"] == "DIFFERENT")
    n_same = sum(1 for g in gold.values() if g["gold"] == "SAME")
    fr_rate = (false_refusal / n_same) if n_same else 0.0
    inv_rate = (invalid / n) if n else 0.0
    return {"n": n, "wrong_same": wrong_same, "wrong_same_denom": n_diff,
            "false_refusal": false_refusal, "false_refusal_denom": n_same, "false_refusal_rate": round(fr_rate, 6),
            "invalid": invalid, "invalid_rate": round(inv_rate, 6),
            "pass": bool(wrong_same == 0 and fr_rate <= 0.10 and inv_rate <= 0.02), "by_family": fam}


def main(argv=None):
    ap = argparse.ArgumentParser(description="EXP-0 scorer + gate (0 LLM)")
    ap.add_argument("--run", required=True, help="exp0_graders/runs/<utc> dir with verdicts.<arm>.json")
    ap.add_argument("--key", required=True)
    ap.add_argument("--lock", required=True)
    ap.add_argument("--protocol", default=None)
    a = ap.parse_args(argv)

    lock = json.load(open(a.lock, encoding="utf-8"))
    key_sha_verified = (sha256_file(a.key) == lock.get("sha256"))
    if a.protocol and key_sha_verified:
        key_sha_verified = (sha256_file(a.protocol) == lock.get("protocol_sha256"))

    recs = key_lint.load_records(a.key)
    gold = {r["pair_id"]: {"gold": r["gold"], "family": r["family"]} for _ln, r in recs}

    per_arm, present = {}, {}
    for arm in ARMS:
        v = load_verdicts(os.path.join(a.run, "verdicts.%s.json" % arm))
        present[arm] = v is not None
        per_arm[arm] = score_arm(gold, v or {})

    va = load_verdicts(os.path.join(a.run, "verdicts.g_sonnet_a.json")) or {}
    vb = load_verdicts(os.path.join(a.run, "verdicts.g_sonnet_b.json")) or {}
    shared_miss = {}
    for pid, g in gold.items():
        if g["gold"] == "DIFFERENT" and va.get(pid) == "SAME" and vb.get(pid) == "SAME":
            shared_miss[g["family"]] = shared_miss.get(g["family"], 0) + 1

    sonnet_pass = present["g_sonnet_a"] and present["g_sonnet_b"] and per_arm["g_sonnet_a"]["pass"] and per_arm["g_sonnet_b"]["pass"]
    opus_pass = present["g_opus"] and per_arm["g_opus"]["pass"]
    grader_tier = "sonnet" if sonnet_pass else ("opus" if opus_pass else "none")
    gate_pass = grader_tier != "none"

    n_diff = sum(1 for g in gold.values() if g["gold"] == "DIFFERENT")
    ub = {}
    if gate_pass and n_diff:
        ub["wrong_same_ub95_rule_of_three"] = "<=3/%d = %.4f" % (n_diff, 3.0 / n_diff)

    scores = {"exp_id": "EXP-0", "run_id": os.path.basename(a.run.rstrip("/")), "key_sha_verified": key_sha_verified,
              "gate": {"expr": "EXISTS tier T: forall g in T: wrong_same==0 && false_refusal<=0.10 && invalid_rate<=0.02",
                       "pass": bool(gate_pass and key_sha_verified)},
              "metrics": {"grader_tier": grader_tier, "sonnet_tier_pass": sonnet_pass, "opus_tier_pass": opus_pass, "arms_present": present},
              "per_arm": per_arm, "shared_miss_by_family": shared_miss,
              "denominators": {"n_records": len(gold), "n_DIFFERENT": n_diff,
                               "n_SAME": sum(1 for g in gold.values() if g["gold"] == "SAME")},
              "upper_bounds": ub, "exhibit_refs": []}
    outcome = "ABORTED" if not key_sha_verified else ("PASS" if gate_pass else "FAIL")
    decision = {"exp_id": "EXP-0", "outcome": outcome, "adopted": {"grader_tier": grader_tier},
                "failure_attribution": ([] if (gate_pass and key_sha_verified) else
                                        [{"cause": ("rules" if not key_sha_verified else "tiering"),
                                          "evidence": ("key sha re-verify failed" if not key_sha_verified else
                                                       "no tier meets wrong_same==0 & false_refusal<=0.10 & invalid_rate<=0.02")}]),
                "shared_miss_flags": shared_miss, "blindness_discounts": None, "fable_signoff": None}
    json.dump(scores, open(os.path.join(a.run, "scores.json"), "w"), indent=2, sort_keys=True)
    json.dump(decision, open(os.path.join(a.run, "decision.json"), "w"), indent=2, sort_keys=True)
    print("GATE", "PASS" if scores["gate"]["pass"] else outcome, "| tier", grader_tier, "| key_sha_verified", key_sha_verified)
    for arm in ARMS:
        p = per_arm[arm]
        print("  %-12s present=%s pass=%s wrong_same=%d/%d false_refusal=%d/%d inv=%.3f" %
              (arm, present[arm], p["pass"], p["wrong_same"], p["wrong_same_denom"], p["false_refusal"], p["false_refusal_denom"], p["invalid_rate"]))
    if shared_miss:
        print("  SHARED_MISS", json.dumps(shared_miss, sort_keys=True))
    print("WROTE scores.json + decision.json")


if __name__ == "__main__":
    main()
