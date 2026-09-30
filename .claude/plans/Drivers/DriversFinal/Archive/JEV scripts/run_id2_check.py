"""Big identity test, stage D (JEV.md §6.8c): run the step-5 identity check on all 640 pairs (2 variants x 2 runs). Settings FROZEN BEFORE THE RUN (chosen on the 55-pair dev set, which is not part of this test):
primary = V2 (four one-check questions, id_prompts.py), a pair merges only if every question >= 0.7; secondary reported = V2 >= 0.5, V1 >= 0.5, V1 >= 0.7. Prompt wording = rule 2.40 only.
Usage: python3 run_id2_check.py  (needs id2_key.json; ~ $0.12)"""
import json, sys, collections, time
sys.path.insert(0, ".")
import prompts_v3 as P
from id_prompts import VARS
from concurrent.futures import ThreadPoolExecutor
assert json.load(open("id2_key.json"))["hash"] == "e005c5a366d3cc78"; B = {p["id"]: p for p in json.load(open("id2_pairs_blind.json"))}
jobs = [(i, v, r) for i in B for v in VARS for r in (0, 1)]
def one(a):
    i, v, r = a; p = B[i]; st = {"existing": p["existing"], "newcomer": p["newcomer"]}
    assert set(st["existing"]) == {"name", "type", "where_it_appears", "text_before_quote", "quote"}
    return i, v, r, P.call(st, VARS[v])
t0 = time.time()
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, jobs))
out = []; err = 0
for i, v, r, res in R:
    if "error" in res: err += 1; print("ERR", i, v, res["error"][:100]); continue
    out.append(dict(id=i, v=v, run=r, p={q: a["noul"] for q, a in res["answers"].items()}, tokens=res["usage"]["input_tokens"]))
json.dump(out, open("results_id2.json", "w"))
tok = collections.Counter(); n = collections.Counter()
for o in out: tok[o["v"]] += o["tokens"]; n[o["v"]] += 1
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s | " + " | ".join(f"{v}: {n[v]} calls, {tok[v]/n[v]:.0f} tok/call" for v in n) + f" | cost ${sum(tok.values())*0.042/1e6:.4f}")
