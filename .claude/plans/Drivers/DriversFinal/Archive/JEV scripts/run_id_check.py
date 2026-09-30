"""Run the step-5 identity check (JEV.md §6.8b) on the frozen unanimous pairs (id_key.json). 2 runs per variant. Usage: python3 run_id_check.py  (~ $0.02)"""
import json, sys, collections, time
sys.path.insert(0, ".")
import prompts_v3 as P
from id_prompts import VARS
from concurrent.futures import ThreadPoolExecutor
KEY = json.load(open("id_key.json")); B = {p["id"]: p for p in json.load(open("id_pairs_blind.json"))}
assert KEY["hash"] == "26c1c07869dbc51c"
jobs = [(i, v, r) for i in B for v in VARS for r in (0, 1)]   # all 66 pairs run; only the 55 keyed pairs are scored, the 11 dropped ones are shown for information
def one(a):
    i, v, r = a; p = B[i]; st = {"existing": p["existing"], "newcomer": p["newcomer"]}
    assert set(st["existing"]) == {"name", "type", "where_it_appears", "text_before_quote", "quote"}   # never send a label
    return i, v, r, P.call(st, VARS[v])
t0 = time.time()
with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
out = []; err = 0
for i, v, r, res in R:
    if "error" in res: err += 1; print("ERR", i, v, res["error"][:100]); continue
    out.append(dict(id=i, v=v, run=r, p={q: a["noul"] for q, a in res["answers"].items()}, tokens=res["usage"]["input_tokens"]))
json.dump(out, open("results_id.json", "w"))
tok = collections.Counter(); n = collections.Counter()
for o in out: tok[o["v"]] += o["tokens"]; n[o["v"]] += 1
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s | " + " | ".join(f"{v}: {n[v]} calls, {tok[v]/n[v]:.0f} tok/call" for v in n) + f" | cost ${sum(tok.values())*0.042/1e6:.4f}")
