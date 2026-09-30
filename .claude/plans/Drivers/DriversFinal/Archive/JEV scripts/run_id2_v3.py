"""EXPLORATORY (JEV.md §6.8c): the two reworded variants V3 (four checks) and V4 (one question) on all 640 pairs, 2 runs each. DEV = BP000-BP319 (may be read to see misses), TEST = BP320-BP639 (fresh: never looked at
for wording). Cutoffs 0.5 and 0.7 fixed in advance. Usage: python3 run_id2_v3.py  (~ $0.1)"""
import json, sys, collections, time
sys.path.insert(0, ".")
import prompts_v3 as P
from id_prompts import VARS
from concurrent.futures import ThreadPoolExecutor
B = {p["id"]: p for p in json.load(open("id2_pairs_blind.json"))}
jobs = [(i, v, r) for i in B for v in ("V3", "V4") for r in (0, 1)]
def one(a):
    i, v, r = a; p = B[i]; return i, v, r, P.call({"existing": p["existing"], "newcomer": p["newcomer"]}, VARS[v])
t0 = time.time()
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, jobs))
out = []; err = 0
for i, v, r, res in R:
    if "error" in res: err += 1; continue
    out.append(dict(id=i, v=v, run=r, p={q: a["noul"] for q, a in res["answers"].items()}, tokens=res["usage"]["input_tokens"]))
json.dump(out, open("results_id2_v3.json", "w"))
tok = collections.Counter(); n = collections.Counter()
for o in out: tok[o["v"]] += o["tokens"]; n[o["v"]] += 1
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s | " + " | ".join(f"{v}: {n[v]} calls, {tok[v]/n[v]:.0f} tok/call" for v in n) + f" | cost ${sum(tok.values())*0.042/1e6:.4f}")
