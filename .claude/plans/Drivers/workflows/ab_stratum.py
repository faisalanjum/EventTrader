#!/usr/bin/env python3
"""
Decision-④ A/B stratum selector (pure code, ZERO meaning judgment).

Picks the ~N MARGINAL batched-DIFFERENT/UNCLEAR pairs from Arm-1's repair_review.json —
the pairs where batch anchoring could most plausibly HIDE a lost merge — and a deterministic
40-pair noise subset for Arm-3. Ranking is by the three §8R anchoring-exposure signals:

  1. shared-full-name adjacency  — duplicate-hub DEGREE of the pair's two records (how many
                                   OTHER candidate pairs touch record a or b). High degree =
                                   dense duplicate neighbourhood = the §2 same-name streaks
                                   where a real missed merge most plausibly hides.
  2. late position-in-batch      — how late the pair sat inside its batch file (the order the
                                   proposer judge actually consumed). Later = more pairs seen
                                   first = more anchoring exposure. Fraction in [0,1].
  3. reason score                — strength of the deterministic suggestion = number of shared
                                   name tokens (token_overlap:a,b,c -> 3). All candidates here
                                   are token_overlap (no embeddings), so the flat _reason_score
                                   in repair_duplicates.py is useless; shared-token COUNT is the
                                   finer, faithful signal.

Each signal is turned into an average-rank PERCENTILE in [0,1] over the eligible pool; the
composite is their equal-weight mean. The stratum first takes the top raw-signal tails
(adjacency, late position, reason score), then fills remaining slots by composite; the noise
subset is spread across the final stratum ranks. Pure, totally deterministic, no randomness.

Inputs (run_dir): repair_candidates.json (frozen), repair_plan.json (batch positions),
                  repair_review.json (Arm-1 verdicts).
Output: <run_dir>/ab_stratum.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from assemble_catalog import serialize
from fold_catalogs import norm

NOT_SAME = ("DIFFERENT", "UNCLEAR")


def shared_token_count(reason):
    """token_overlap:beef,price[+embedding:..] -> 2 ; embedding-only -> 0."""
    r = str(reason or "")
    if "token_overlap:" not in r:
        return 0
    body = r.split("token_overlap:", 1)[1].split("+", 1)[0]
    return len([t for t in body.split(",") if t.strip()])


def degree(cands):
    """How many candidate pairs touch each (normalised) record name."""
    deg = Counter()
    for c in cands:
        deg[norm(c.get("a"))] += 1
        deg[norm(c.get("b"))] += 1
    return deg


def positions(plan):
    """idx -> (batch_id, position_in_batch, batch_size) from the pinned plan."""
    out = {}
    for b in plan.get("batches") or []:
        idxs = b.get("idx") or []
        for pos, i in enumerate(idxs):
            out[i] = (b.get("id"), pos, len(idxs))
    return out


def percentile_ranks(pairs):
    """pairs: list of (key, value). Returns {key: pr in [0,1]} by AVERAGE rank (ties share
    the mean rank). Highest value -> ~1.0, lowest -> 0.0. Deterministic."""
    n = len(pairs)
    if n == 0:
        return {}
    if n == 1:
        return {pairs[0][0]: 1.0}
    order = sorted(range(n), key=lambda i: pairs[i][1])
    pr = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pairs[order[j + 1]][1] == pairs[order[i]][1]:
            j += 1
        avg_rank = (i + j) / 2.0           # 0-based average rank for this tie group
        for k in range(i, j + 1):
            pr[pairs[order[k]][0]] = avg_rank / (n - 1)
        i = j + 1
    return pr


def build_rows(cands, plan, review):
    """One row per ELIGIBLE candidate, with all three raw signals + their percentile ranks +
    the composite. Sorted most-anchoring-suspicious first.

    ELIGIBLE = the batched lane kept the pair separate AND never gave it an isolated look:
    final verdict DIFFERENT/UNCLEAR with NO `confirmed` flag. A confirm-flipped row
    (proposer SAME -> blind isolated confirm DIFFERENT, marked confirmed:true) already had its
    isolated judgment, so anchoring could not have hidden a merge there — it is NOT a hunting
    ground and would only dilute the stratum / waste Arm-2 budget."""
    row_by_idx = {r.get("idx"): r for r in (review.get("reviews") or [])}
    pos = positions(plan)
    deg = degree(cands)

    eligible = []
    for idx, c in enumerate(cands):
        rr = row_by_idx.get(idx)
        v = rr.get("verdict") if rr else None
        if v not in NOT_SAME:
            continue                       # SAME (or unjudged) -> not a lost-merge hunting ground
        if rr.get("confirmed") is True:
            continue                       # confirm-flipped: already isolated; anchoring didn't hide it
        bid, p, bsize = pos.get(idx, (None, 0, 1))
        eligible.append({
            "idx": idx, "a": c.get("a"), "b": c.get("b"),
            "batched_verdict": v,
            "reason": c.get("reason"),
            "n_companies": c.get("n_companies"),
            "reason_score": shared_token_count(c.get("reason")),
            "adjacency": deg[norm(c.get("a"))] + deg[norm(c.get("b"))],
            "position": p,
            "position_frac": (p / (bsize - 1)) if bsize > 1 else 0.0,
            "batch_size": bsize,
            "batch_id": bid,
        })

    pr_adj = percentile_ranks([(r["idx"], r["adjacency"]) for r in eligible])
    pr_pos = percentile_ranks([(r["idx"], r["position_frac"]) for r in eligible])
    pr_rsn = percentile_ranks([(r["idx"], r["reason_score"]) for r in eligible])
    for r in eligible:
        r["pr_adjacency"] = pr_adj.get(r["idx"], 0.0)
        r["pr_position"] = pr_pos.get(r["idx"], 0.0)
        r["pr_reason"] = pr_rsn.get(r["idx"], 0.0)
        r["composite"] = (r["pr_adjacency"] + r["pr_position"] + r["pr_reason"]) / 3.0

    # deterministic order: composite desc, then each raw signal desc, then idx asc
    eligible.sort(key=lambda r: (-r["composite"], -r["adjacency"], -r["position_frac"],
                                 -r["reason_score"], r["idx"]))
    return eligible


# raw-signal field -> short label used in admitted_by / admit_counts
SIGNAL_FIELDS = [("adjacency", "adjacency"), ("position_frac", "position"),
                 ("reason_score", "reason")]


def _top_by(rows, field, k):
    """Top-k idx by one RAW signal desc; ties -> composite desc, then idx asc."""
    return [r["idx"] for r in
            sorted(rows, key=lambda r: (-r[field], -r["composite"], r["idx"]))[:k]]


def select_indices(rows, n_stratum=100, n_noise=40, per_signal=25):
    """Pick the stratum + the noise subset (owner-pinned design 2026-06-11).

    Stratum = UNION of the top-`per_signal` pairs by EACH raw signal — so the single most
    extreme pair for every separate failure type is guaranteed in (a plain composite average
    can drop a pair that is #1 on one signal but middling overall — exactly the pair Arm 2
    must test) — then FILL to n_stratum by composite. Each pair is tagged `admitted_by`
    (which signal(s) admitted it; composite-fill pairs = ["composite"]).

    Noise = the 40 pairs spread EVENLY across the composite-ranked stratum
    (rank round(j*(k-1)/(m-1)), j=0..m-1) — NOT the top-40, which would over-sample the most
    flip-prone pairs and inflate the noise floor, making the GO test too easy.

    Returns (ranked_idx [composite desc], noise_idx, {idx: sorted admitted_by labels})."""
    by_composite = sorted(rows, key=lambda r: (-r["composite"], r["idx"]))
    admitted = {}
    for field, label in SIGNAL_FIELDS:
        for idx in _top_by(rows, field, per_signal):
            admitted.setdefault(idx, set()).add(label)

    selected = [r["idx"] for r in by_composite if r["idx"] in admitted]   # extremes, composite order
    if len(selected) > n_stratum:
        selected = selected[:n_stratum]      # only if misconfigured (len(SIGNALS)*per_signal > n)
    else:
        have = set(selected)
        for r in by_composite:               # fill remaining slots by composite
            if len(selected) >= n_stratum:
                break
            if r["idx"] not in have:
                selected.append(r["idx"])
                admitted.setdefault(r["idx"], set()).add("composite")
                have.add(r["idx"])

    have = set(selected)
    ranked = [r["idx"] for r in by_composite if r["idx"] in have]   # composite desc = rank order
    k = len(ranked)
    m = min(n_noise, k)
    if m <= 0:
        noise_idx = []
    elif m == 1:
        noise_idx = [ranked[0]]
    else:
        ranks = sorted({round(j * (k - 1) / (m - 1)) for j in range(m)})
        noise_idx = [ranked[p] for p in ranks]
    return ranked, noise_idx, {i: sorted(admitted.get(i, [])) for i in ranked}


def select_stratum(run_dir, n_stratum=100, n_noise=40, per_signal=25, out="ab_stratum.json"):
    run = Path(run_dir)
    cands = json.load(open(run / "repair_candidates.json")).get("candidates") or []
    plan = json.load(open(run / "repair_plan.json"))
    review = json.load(open(run / "repair_review.json"))

    rows = build_rows(cands, plan, review)
    reviews = review.get("reviews") or []
    n_confirm_flipped = sum(1 for r in reviews
                            if r.get("verdict") in NOT_SAME and r.get("confirmed") is True)

    ranked, noise_idx, admitted_by = select_indices(rows, n_stratum, n_noise, per_signal)
    rank_of = {idx: p for p, idx in enumerate(ranked)}
    sset, nset = set(ranked), set(noise_idx)
    for r in rows:
        in_s = r["idx"] in sset
        r["in_stratum"] = in_s
        r["in_noise"] = r["idx"] in nset
        r["admitted_by"] = admitted_by.get(r["idx"], []) if in_s else []
        r["rank"] = rank_of.get(r["idx"]) if in_s else None

    admit_counts = Counter()
    for i in ranked:
        for lab in admitted_by[i]:
            admit_counts[lab] += 1

    blob = {
        "run_id": run.name,
        "n_candidates": len(cands),
        "n_eligible": len(rows),
        "n_confirm_flipped_excluded": n_confirm_flipped,
        "per_signal": per_signal,
        "n_stratum": len(ranked),
        "n_noise": len(noise_idx),
        "admit_counts": dict(admit_counts),
        "stratum_idx": ranked,
        "noise_idx": noise_idx,
        "rows": rows,
    }
    if out:
        (run / out).write_text(serialize(blob))
    return blob


def main(argv=None):
    ap = argparse.ArgumentParser(description="Decision-④ A/B stratum selector (§8R)")
    ap.add_argument("run_dir")
    ap.add_argument("--n-stratum", type=int, default=100)
    ap.add_argument("--n-noise", type=int, default=40)
    ap.add_argument("--per-signal", type=int, default=25)
    ap.add_argument("--out", default="ab_stratum.json")
    a = ap.parse_args(argv)
    blob = select_stratum(a.run_dir, a.n_stratum, a.n_noise, a.per_signal, a.out)
    print(json.dumps({k: v for k, v in blob.items() if k != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
