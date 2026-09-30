"""Second look at the tag test (JEV.md §9): compare the variants at MATCHED recall, and try flag rules that combine the five probabilities offline
(composite scoring: the weights live in code, no new Jev call). Also lists the non-facts each variant flags. Usage: python3 score_tags2.py"""
import json, collections, math
R = json.load(open("results_tags.json")); M = json.load(open("results_tags_meta.json")); lab = json.load(open("tag_labels.json"))["labels"]
TY = ["states_metric", "states_guidance", "states_surprise", "states_action_event"]
stats = json.load(open("sweep_units_stats.json")); W = collections.defaultdict(float)
for s in stats:
    if s["group"] != "news titles": W[s["group"]] += s["est_calls"]
Wt = sum(W.values())
pos = [i for i, m in M.items() if m["kind"] == "pos" and m["type"] in ("metric", "guidance", "action_event", "surprise", "mixed")]
bg = [i for i, m in M.items() if m["kind"] == "bg"]; bgF = [i for i in bg if M[i]["type"] == "F"]; bgN = [i for i in bg if M[i]["type"] == "N"]
def score(v, i, how):
    d = R[i][v]; m = max(d[q] for q in TY); bp = d["is_boilerplate"]
    if how == "max": return m
    if how == "noisy-or": return 1 - math.prod(1 - d[q] for q in TY)
    if how.startswith("max-bp"): w = float(how[6:]); return m - w * bp
    if how == "max*(1-bp)": return m * (1 - bp)
def corpus_share(v, how, t):
    return sum(w * sum(score(v, i, how) >= t for i in bg if M[i]["set"] == g) / 15 for g, w in W.items()) / Wt
GRID = [x / 100 for x in range(0, 101)]
print("== matched recall on the 762 known facts: the highest threshold that still reaches the target; then what it costs in flags")
print(f"{'variant / rule':22s} " + " | ".join(f"recall >= {r}%" .ljust(38) for r in (99.5, 99, 98, 97)))
for v in ("P", "C", "S"):
    for how in ("max", "noisy-or", "max-bp0.5", "max-bp1.0", "max*(1-bp)"):
        cells = []
        for target in (99.5, 99, 98, 97):
            best = None
            for t in GRID:
                rec = 100 * sum(score(v, i, how) >= t for i in pos) / len(pos)
                if rec >= target: best = t
            if best is None: cells.append("-".ljust(38)); continue
            rec = 100 * sum(score(v, i, how) >= best for i in pos) / len(pos); fn = sum(score(v, i, how) >= best for i in bgN); ff = sum(score(v, i, how) >= best for i in bgF)
            cells.append(f"t={best:.2f} rec {rec:4.1f} FP {fn:2d}/80 F {ff}/28 corp {100*corpus_share(v, how, best):2.0f}%".ljust(38))
        print(f"{v} {how:19s} " + " | ".join(cells))
    print()
print("== non-facts (blind label N) flagged at t=0.5 by P, R1 (any type tag >= 0.5)")
S_ = {b["id"]: b for b in json.load(open("/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad/tag_sample.json"))}
for i in bgN:
    d = R[i]["P"]
    if max(d[q] for q in TY) >= 0.5:
        print(f"  {i[2:20]:18s} " + " ".join(f"{q[7:12]}={d[q]:.2f}" for q in TY) + f" bp={d['is_boilerplate']:.2f} | {S_[i]['state']['quote'][:120]!r}")
