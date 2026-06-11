#!/usr/bin/env python3
"""
Decision-④ A/B differ (pure code, ZERO meaning judgment).

Turns the three arms into the §8R gate numbers:

  lost-merge rate = Arm-2 (solo) SAME among the batched-DIFFERENT/UNCLEAR stratum
                    = how often judging a pair ALONE flips a batched "keep separate" to SAME.
  noise floor     = Arm-3 solo-vs-solo flip-to-SAME on the 40 noise pairs
                    = how often a REPEATED solo judgment alone flips a not-SAME pair to SAME
                      (the judge's own irreducible coin-flip — no batching involved).
  position-in-batch SAME-rate analysis = the anchoring smoking gun: if Arm-2 SAMEs cluster in
                    pairs that sat LATE in their batch, anchoring is suppressing late merges.

Gate (§8R): lost-merge rate <= noise floor -> GO. Batching adds no merge loss beyond the
judge's own noise. We also report a one-sided binomial p (is the excess significant?) and a
Wilson CI, plus a DEGENERATE-FLOOR guard (§5 K1): a 40-pair floor that happens to be 0 can't
license anything, so we fall back to a rule-of-three upper bound and flag for the human.

Misses are the RECOVERABLE under-merge direction (unlinked pairs are re-suggested every future
sweep); the permanent 1-2% production canary remains mandatory regardless of verdict.
"""
import argparse
import json
import math
from pathlib import Path

SAME = "SAME"
NOT_SAME = ("DIFFERENT", "UNCLEAR")


def verdict_map(blob):
    return {r.get("idx"): r.get("verdict") for r in (blob.get("reviews") or [])}


def binom_sf_ge(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p). Exact (n is small)."""
    if n <= 0:
        return 1.0
    if k <= 0:
        return 1.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def wilson_upper(k, n, z=1.96):
    """Upper bound of the Wilson score interval for a proportion k/n."""
    if n == 0:
        return 1.0
    phat = k / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (centre + margin) / denom


def lost_merge(stratum_idx, arm2):
    """Arm-2 solo SAME among the batched-not-SAME stratum."""
    v2 = verdict_map(arm2)
    judged = [i for i in stratum_idx if i in v2]
    same = [i for i in judged if v2[i] == SAME]
    n = len(judged)
    return {
        "n_stratum": len(stratum_idx),
        "n_judged": n,
        "lost": len(same),
        "lost_idx": same,
        "rate": (len(same) / n) if n else 0.0,
        "wilson_upper95": wilson_upper(len(same), n) if n else 1.0,
    }


def noise_floor(noise_idx, arm3a, arm3b):
    """Solo-vs-solo flip-to-SAME on the noise pairs, pooled over both directions
    (a as base/b as repeat AND b as base/a as repeat). All noise pairs are batched-not-SAME,
    so the matched comparison to lost-merge is 'a not-SAME solo verdict flips to SAME on a
    repeat solo roll'."""
    va, vb = verdict_map(arm3a), verdict_map(arm3b)
    both = [i for i in noise_idx if i in va and i in vb]
    disagree = [i for i in both if va[i] != vb[i]]

    to_same = 0       # base not-SAME -> repeat SAME, pooled both directions
    base_notsame = 0  # base verdict was not-SAME (the trials that COULD flip to SAME)
    for i in both:
        if va[i] in NOT_SAME:
            base_notsame += 1
            if vb[i] == SAME:
                to_same += 1
        if vb[i] in NOT_SAME:
            base_notsame += 1
            if va[i] == SAME:
                to_same += 1
    same_a = sum(1 for i in both if va[i] == SAME)
    same_b = sum(1 for i in both if vb[i] == SAME)
    n = len(both)
    return {
        "n_noise": len(noise_idx),
        "n_both_judged": n,
        "disagree": len(disagree),
        "disagree_idx": disagree,
        "disagreement_rate": (len(disagree) / n) if n else 0.0,
        "to_same": to_same,
        "base_notsame_trials": base_notsame,
        "floor_rate": (to_same / base_notsame) if base_notsame else 0.0,
        "solo_same_rate": ((same_a + same_b) / (2 * n)) if n else 0.0,
        "degenerate": base_notsame < 10 or to_same == 0,
        "rule_of_three_upper95": (3.0 / base_notsame) if base_notsame else 1.0,
    }


def position_analysis(rows, stratum_idx, arm2):
    """Arm-2 SAME-rate bucketed by where the pair sat in its batch. The anchoring smoking gun:
    late-position pairs flipping to SAME more than early-position pairs."""
    v2 = verdict_map(arm2)
    by_idx = {r["idx"]: r for r in rows}
    buckets = {"early": {"n": 0, "same": 0}, "late": {"n": 0, "same": 0}}
    per_pos = {}
    for i in stratum_idx:
        r = by_idx.get(i)
        if r is None or i not in v2:
            continue
        pos, bsize = r.get("position", 0), r.get("batch_size", 1) or 1
        is_same = 1 if v2[i] == SAME else 0
        half = "late" if pos >= math.ceil(bsize / 2) else "early"
        buckets[half]["n"] += 1
        buckets[half]["same"] += is_same
        pp = per_pos.setdefault(pos, {"n": 0, "same": 0})
        pp["n"] += 1
        pp["same"] += is_same
    for half in buckets.values():
        half["same_rate"] = (half["same"] / half["n"]) if half["n"] else 0.0
    for pp in per_pos.values():
        pp["same_rate"] = (pp["same"] / pp["n"]) if pp["n"] else 0.0
    gradient = buckets["late"]["same_rate"] - buckets["early"]["same_rate"]
    return {"buckets": buckets,
            "per_position": {str(k): per_pos[k] for k in sorted(per_pos)},
            "late_minus_early_same_rate": gradient}


def diff_arms(stratum_blob, arm2, arm3a, arm3b):
    stratum_idx = stratum_blob.get("stratum_idx") or []
    noise_idx = stratum_blob.get("noise_idx") or []
    rows = stratum_blob.get("rows") or []

    lm = lost_merge(stratum_idx, arm2)
    nf = noise_floor(noise_idx, arm3a, arm3b)
    pos = position_analysis(rows, stratum_idx, arm2)

    # one-sided test: under H0 the batched lane loses merges at the judge's own noise rate;
    # is the observed lost count significantly ABOVE that?
    p_excess = binom_sf_ge(lm["lost"], lm["n_judged"], nf["floor_rate"]) if lm["n_judged"] else 1.0

    floor = nf["floor_rate"]
    passes_point = lm["rate"] <= floor
    significant_excess = p_excess < 0.05
    if nf["degenerate"]:
        # §5 K1 degenerate-floor rule: a 0/too-thin floor licenses nothing on its own.
        # Require the lost-merge UPPER bound to sit under the rule-of-three noise ceiling.
        passes = lm["wilson_upper95"] <= nf["rule_of_three_upper95"]
        basis = "degenerate-floor: lost wilson_upper95 <= noise rule_of_three_upper95"
    else:
        passes = passes_point and not significant_excess
        basis = "lost-merge rate <= noise floor AND no significant one-sided excess"

    smoking_gun = pos["late_minus_early_same_rate"] > 0 and pos["buckets"]["late"]["n"] >= 5

    verdict = "GO" if passes else "NO-GO"
    flags = []
    if nf["degenerate"]:
        flags.append("DEGENERATE_NOISE_FLOOR — 40-pair floor too thin/zero; verdict uses "
                     "rule-of-three ceiling; treat as provisional, human review advised")
    if smoking_gun:
        flags.append(f"LATE-POSITION ANCHORING SIGNAL — late SAME-rate exceeds early by "
                     f"{pos['late_minus_early_same_rate']:+.3f}; inspect position buckets")
    if lm["n_judged"] != lm["n_stratum"]:
        flags.append(f"ARM-2 COVERAGE GAP — {lm['n_stratum'] - lm['n_judged']} stratum pair(s) "
                     f"missing an Arm-2 verdict")

    return {
        "verdict": verdict,
        "basis": basis,
        "gate": {
            "lost_merge_rate": round(lm["rate"], 4),
            "noise_floor_rate": round(floor, 4),
            "lost_merge_le_noise_floor": passes_point,
            "one_sided_binom_p_excess": round(p_excess, 4),
            "significant_excess": significant_excess,
        },
        "lost_merge": lm,
        "noise": nf,
        "position": pos,
        "flags": flags,
        "limitations": [
            "leaf/company-profile evidence only — fold repair stays off (separate K2 gate)",
            "misses are the RECOVERABLE under-merge direction (re-suggested every future sweep)",
            "statistical bound, not literal certainty — permanent 1-2% production canary remains mandatory",
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Decision-④ A/B differ (§8R)")
    ap.add_argument("run_dir")
    ap.add_argument("--stratum", default="ab_stratum.json")
    ap.add_argument("--arm2", default="ab_arm2_review.json")
    ap.add_argument("--arm3a", default="ab_arm3a.json")
    ap.add_argument("--arm3b", default="ab_arm3b.json")
    ap.add_argument("--out", default="ab_differ_report.json")
    a = ap.parse_args(argv)
    run = Path(a.run_dir)
    rep = diff_arms(
        json.load(open(run / a.stratum)),
        json.load(open(run / a.arm2)),
        json.load(open(run / a.arm3a)),
        json.load(open(run / a.arm3b)),
    )
    if a.out:
        from assemble_catalog import serialize
        (run / a.out).write_text(serialize(rep))
    print(json.dumps(rep, sort_keys=True, indent=1))


if __name__ == "__main__":
    main()
