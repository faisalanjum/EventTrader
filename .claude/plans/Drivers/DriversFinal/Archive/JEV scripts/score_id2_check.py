"""Score results_id2.json against id2_key.json (JEV.md §6.8c). Upper bounds are one-sided 95% exact binomial (Clopper-Pearson). Usage: python3 score_id2_check.py"""
import json, collections, math, random
K = json.load(open("id2_key.json")); L = K["labels"]; KIND = K["kind"]; G = json.load(open("id2_pairs_groups.json"))
R = json.load(open("results_id2.json")); B = {p["id"]: p for p in json.load(open("id2_pairs_blind.json"))}
X = collections.defaultdict(dict)
for o in R: X[(o["id"], o["v"])][o["run"]] = o["p"]
def merges(i, v, r, t): return all(x >= t for x in X[(i, v)][r].values())
def upper(k, n, conf=0.95):   # smallest p with P(X <= k | n, p) <= 1 - conf
    if n == 0: return float("nan")
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2; c = sum(math.comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k + 1))
        lo, hi = (mid, hi) if c > 1 - conf else (lo, mid)
    return hi
S = [i for i in L if L[i] == "S"]; D = [i for i in L if L[i] == "D"]
print(f"key: {len(D)} different + {len(S)} same pairs (two independent labelers agreed); pairs run: {len(B)}\n")
CFG = [("V2", 0.7, "PRIMARY (frozen)"), ("V2", 0.5, ""), ("V1", 0.5, ""), ("V1", 0.7, "")]
print(f"{'setting':22s} {'run':>3s} {'wrong merges':>14s} {'95% upper bound':>16s} {'missed matches':>16s}")
for v, t, tag in CFG:
    for r in (0, 1):
        wm = [i for i in D if merges(i, v, r, t)]; mm = [i for i in S if not merges(i, v, r, t)]
        print(f"{v} all >= {t} {tag:16s}"[:22].ljust(22) + f" {r:>3d} {len(wm):>4d}/{len(D)} ({100*len(wm)/len(D):.1f}%) {100*upper(len(wm), len(D)):>14.1f}% {len(mm):>5d}/{len(S)} ({100*len(mm)/max(1,len(S)):.0f}%)")
print("\nPRIMARY (V2 >= 0.7, run 0) by stratum - wrong merges / different pairs, 95% upper bound; missed / same pairs")
def strat(name, fn):
    g = collections.defaultdict(lambda: [[], []])
    for i in D: g[fn(i)][0].append(i)
    for i in S: g[fn(i)][1].append(i)
    print(f"-- {name}")
    for k in sorted(g, key=str):
        d, s = g[k]; wm = sum(merges(i, "V2", 0, 0.7) for i in d); mm = sum(not merges(i, "V2", 0, 0.7) for i in s)
        print(f"   {str(k):32s} wrong merges {wm}/{len(d)}" + (f" (<= {100*upper(wm, len(d)):.0f}%)" if d else "") + f" | missed {mm}/{len(s)}")
strat("difference kind (labeler A)", lambda i: KIND[i])
strat("name relation / rank / doc relation", lambda i: G[i]["stratum"])
strat("source group of the two sides", lambda i: " + ".join(sorted(G[i]["groups"])) if G[i]["groups"][0] != G[i]["groups"][1] else G[i]["groups"][0] + " (both)")
strat("sectors", lambda i: "same sector" if G[i]["sectors"][0] == G[i]["sectors"][1] else "different sectors")
print("\nEVERY wrong merge, primary or V2 >= 0.5 (run 0) - for the manual audit:")
for i in D:
    if merges(i, "V2", 0, 0.5):
        e, n = B[i]["existing"], B[i]["newcomer"]; p = {q: round(x, 2) for q, x in X[(i, "V2")][0].items()}; pr = "PRIMARY" if merges(i, "V2", 0, 0.7) else "0.5 only"
        print(f"  {i} [{pr}] kind={KIND[i]} {G[i]['stratum']} V2={p}\n     E[{e['name']}] {e['quote'][:160]!r}\n     N[{n['name']}] {n['quote'][:160]!r}")
print("\nrun-to-run identical decision (V2 >= 0.7):", sum(merges(i, "V2", 0, 0.7) == merges(i, "V2", 1, 0.7) for i in L), "of", len(L))
print("unresolved pairs (labelers disagreed or said U):", len(K["unresolved"]), "- Jev merges (V2 >= 0.7) on", sum(merges(i, "V2", 0, 0.7) for i in K["unresolved"]))
import statistics
tk = collections.defaultdict(list)
for o in R: tk[o["v"]].append(o["tokens"])
print("tokens/call:", {v: round(statistics.mean(x)) for v, x in tk.items()})
