"""Score results_id.json against the frozen key (JEV.md §6.8b). A pair merges only if every question of the variant is >= t. Usage: python3 score_id_check.py"""
import json, collections, statistics
K = json.load(open("id_key.json"))["labels"]; R = json.load(open("results_id.json")); G = json.load(open("id_pairs_groups.json"))
B = {p["id"]: p for p in json.load(open("id_pairs_blind.json"))}; Sn = json.load(open("id_labels_sonnet.json"))
X = collections.defaultdict(dict)
for o in R: X[(o["id"], o["v"])][o["run"]] = o["p"]
def merges(i, v, r, t): return all(x >= t for x in X[(i, v)][r].values())
S = [i for i in K if K[i] == "S"]; D = [i for i in K if K[i] == "D"]
pct = lambda a, b: f"{a}/{b} ({100*a/b:.0f}%)"
print(f"key: {len(S)} same, {len(D)} different (unanimous)\n")
print(f"{'variant, cutoff':22s} {'run':>3s} {'wrong merges (dangerous)':>26s} {'missed matches':>18s}")
for v in ("V1", "V2"):
    for t in (0.5, 0.7):
        for r in (0, 1):
            wm = [i for i in D if merges(i, v, r, t)]; mm = [i for i in S if not merges(i, v, r, t)]
            print(f"{v} all >= {t:<10} {r:>3d} {pct(len(wm), len(D)):>26s} {pct(len(mm), len(S)):>18s}")
print("\nEVERY wrong merge (D pair that Jev would merge), run 0:")
for v, t in (("V1", 0.5), ("V2", 0.5), ("V1", 0.7), ("V2", 0.7)):
    for i in D:
        if merges(i, v, 0, t):
            e, n = B[i]["existing"], B[i]["newcomer"]; p = {q: round(x, 2) for q, x in X[(i, v)][0].items()}
            print(f"  [{v} >= {t}] {i} ({G[i]['group']}) {p}\n     E[{e['name']}] {e['quote'][:110]!r}\n     N[{n['name']}] {n['quote'][:110]!r}")
print("\nMissed matches (S pair Jev would keep separate), V2 >= 0.5, run 0:")
for i in S:
    if not merges(i, "V2", 0, 0.5): print("  ", i, {q: round(x, 2) for q, x in X[(i, "V2")][0].items()}, "| V1", round(X[(i, "V1")][0]["same_driver"], 2), "|", B[i]["existing"]["name"], "~", B[i]["newcomer"]["name"])
print("\nWhich V2 question blocks the D pairs (run 0, cutoff 0.5) - count of D pairs each question alone would block:", {q: sum(X[(i, 'V2')][0][q] < 0.5 for i in D) for q in ("same_object", "same_scope", "same_mechanism", "coherent")})
print("...and how many S pairs each would wrongly block:", {q: sum(X[(i, 'V2')][0][q] < 0.5 for i in S) for q in ("same_object", "same_scope", "same_mechanism", "coherent")})
print("\nrun-to-run: same V1/V2 decision on both runs at 0.5:", {v: sum(merges(i, v, 0, 0.5) == merges(i, v, 1, 0.5) for i in K) for v in ("V1", "V2")}, "of", len(K))
print("\nThe 11 pairs the labelers could not agree on (information only; Jev's answers, run 0):")
for i in sorted(set(B) - set(K)):
    print(f"  {i} V1={X[(i,'V1')][0]['same_driver']:.2f} V2min={min(X[(i,'V2')][0].values()):.2f} | Sonnet: {Sn[i]['label']} {Sn[i]['why']}")
tk = collections.defaultdict(list)
for o in R: tk[o["v"]].append(o["tokens"])
print("\ntokens/call:", {v: round(statistics.mean(x)) for v, x in tk.items()}, "| $ per pair-call:", {v: round(statistics.mean(x) * 0.042 / 1e6, 6) for v, x in tk.items()})
