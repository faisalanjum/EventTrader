"""Fresh hold-out check of the tag screen (JEV.md §6.6). Labels were made by Claude before any call and frozen (tag_holdout_labels.json). The rules below were
fixed BEFORE the run and were never tuned on these units. Usage: /home/faisal/EventMarketDB/venv/bin/python3 run_tags_holdout.py"""
import json, sys, math, collections
sys.path.insert(0, ".")
import prompts_v3 as P, tag_prompts as T
from sweep_corpus import SET_B
from concurrent.futures import ThreadPoolExecutor
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
H = json.load(open(f"{SCRATCH}/tag_holdout.json")); LAB = json.load(open("tag_holdout_labels.json"))["labels"]
VARS = {"P": T.variant("P"), "C": T.variant("C"), "S": T.variant("S"), "B0": SET_B}
def one(a):
    h, v = a; st = h["state"]; assert set(st) == {"where_it_appears", "text_before_quote", "quote", "text_after_quote"}
    r = P.call(st, VARS[v]); return h["id"], v, {q: (x["noul"] if x["type"] == "noul" else x["choice"]) for q, x in r["answers"].items()}, r["usage"]["input_tokens"]
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, [(h, v) for h in H for v in VARS]))
res = collections.defaultdict(dict); tok = collections.Counter()
for i, v, a, t in R: res[i][v] = a; tok[v] += t
json.dump(res, open("results_tags_holdout.json", "w"))
print(f"calls {len(R)} cost ${sum(tok.values())*0.042/1e6:.3f}")
TY = T.TYPE_TAGS; G = collections.defaultdict(list)
for h in H: G[h["group"]].append(h["id"])
stats = json.load(open("sweep_units_stats.json")); W = collections.defaultdict(float)
for s in stats:
    if s["group"] != "news titles": W[s["group"]] += s["est_calls"]
Wt = sum(W.values())
def mx(v, i): return max(res[i][v][q] for q in TY)
RULES = [  # (name, variant, function) -- fixed in advance
 ("old set B0: is_fact >= 0.5 or kind != none", "B0", lambda i: res[i]["B0"]["is_fact"] >= 0.5 or res[i]["B0"]["kind"] != "none"),
 ("P plain, any fact tag >= 0.70   <- the owner's 70%", "P", lambda i: mx("P", i) >= 0.70),
 ("P plain, any fact tag >= 0.85", "P", lambda i: mx("P", i) >= 0.85),
 ("P, max tag - 0.5 x boilerplate >= 0.41 (loose)", "P", lambda i: mx("P", i) - 0.5 * res[i]["P"]["is_boilerplate"] >= 0.41),
 ("P, max tag - 0.5 x boilerplate >= 0.55 (strict)", "P", lambda i: mx("P", i) - 0.5 * res[i]["P"]["is_boilerplate"] >= 0.55),
 ("S structured, any fact tag >= 0.70", "S", lambda i: mx("S", i) >= 0.70),
 ("S, max tag - 1.0 x boilerplate >= 0.26", "S", lambda i: mx("S", i) - res[i]["S"]["is_boilerplate"] >= 0.26),
]
F = [i for i in LAB if LAB[i] == "F"]; N = [i for i in LAB if LAB[i] == "N"]; U = [i for i in LAB if LAB[i] == "U"]
def wilson(k, n):
    z = 1.96; ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n); a = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)); return (c - a) / d, (c + a) / d
print(f"\nfresh units: {len(H)} = {len(F)} facts, {len(N)} non-facts, {len(U)} unclear (30 per source group)")
print(f"{'rule (fixed before the run)':52s} {'facts caught':>22s} {'non-facts flagged':>19s} {'unclear':>8s} {'corpus flagged':>15s}")
for name, v, fn in RULES:
    a = sum(fn(i) for i in F); n = sum(fn(i) for i in N); u = sum(fn(i) for i in U); lo, hi = wilson(a, len(F))
    corp = sum(W[g] * sum(fn(i) for i in G[g]) / len(G[g]) for g in W) / Wt
    print(f"{name:52s} {a:2d}/{len(F)} = {100*a/len(F):4.0f}% [{100*lo:.0f}-{100*hi:.0f}] {n:5d}/{len(N)} ({100*n/len(N):3.0f}%) {u:5d}/{len(U)} {100*corp:12.0f}%")
print("\nfacts MISSED by the 70% rule (P), with their tag values:")
S_ = {h["id"]: h for h in H}
for i in F:
    if not RULES[1][2](i):
        d = res[i]["P"]; print(f"  [{i}] " + " ".join(f"{q[7:12]}={d[q]:.2f}" for q in TY) + f" bp={d['is_boilerplate']:.2f} | {S_[i]['state']['quote'][:140]!r}")
