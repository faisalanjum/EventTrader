"""EXPLORATORY scoring of the reworded variants (JEV.md §6.8c), DEV and TEST halves separately. Usage: python3 score_id2_v3.py"""
import json, collections, math
K = json.load(open("id2_key.json")); L = K["labels"]; KIND = K["kind"]; B = {p["id"]: p for p in json.load(open("id2_pairs_blind.json"))}
R = json.load(open("results_id2_v3.json")) + json.load(open("results_id2.json"))
X = collections.defaultdict(dict)
for o in R: X[(o["id"], o["v"])][o["run"]] = o["p"]
def merges(i, v, r, t): return all(x >= t for x in X[(i, v)][r].values())
def upper(k, n):
    if n == 0: return float("nan")
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2; c = sum(math.comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k + 1)); lo, hi = (mid, hi) if c > 0.05 else (lo, mid)
    return hi
half = lambda i: "DEV" if int(i[2:]) < 320 else "TEST"
for h in ("DEV", "TEST", "ALL"):
    S = [i for i in L if L[i] == "S" and (h == "ALL" or half(i) == h)]; D = [i for i in L if L[i] == "D" and (h == "ALL" or half(i) == h)]
    hard = [i for i in D if KIND[i] != "unrelated"]
    print(f"\n== {h}: {len(D)} different ({len(hard)} hard = not 'unrelated') + {len(S)} same")
    print(f"{'setting':18s} {'run':>3s} {'wrong merges':>15s} {'upper':>6s} {'wrong (hard)':>13s} {'missed matches':>16s}")
    for v in ("V1", "V2", "V3", "V4"):
        for t in (0.5, 0.7):
            for r in (0, 1):
                wm = [i for i in D if merges(i, v, r, t)]; wh = [i for i in hard if merges(i, v, r, t)]; mm = [i for i in S if not merges(i, v, r, t)]
                print(f"{v} all >= {t}".ljust(18) + f" {r:>3d} {len(wm):>4d}/{len(D)} ({100*len(wm)/len(D):.1f}%) {100*upper(len(wm), len(D)):>5.1f}% {len(wh):>5d}/{len(hard)}  {len(mm):>5d}/{len(S)} ({100*len(mm)/max(1,len(S)):.0f}%)")
print("\nEVERY wrong merge by V3 or V4 (run 0 or 1, cutoff 0.5) - for the audit:")
seen = set()
for v in ("V3", "V4"):
    for i in L:
        if L[i] == "D" and (i, v) not in seen and any(merges(i, v, r, 0.5) for r in (0, 1)):
            seen.add((i, v)); e, n = B[i]["existing"], B[i]["newcomer"]
            print(f"  [{v}] {i} ({half(i)}) kind={KIND[i]} p={[ {q: round(x, 2) for q, x in X[(i, v)][r].items()} for r in (0, 1)]}\n     E[{e['name']}] {e['quote'][:150]!r}\n     N[{n['name']}] {n['quote'][:150]!r}")
