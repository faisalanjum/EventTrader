"""Workflow steps 3 and 6 on the 50 fresh facts (JEV.md §6.8). Frozen keys: wf_keys.json (hash 3577655d6f3c241a). Nothing is tuned; every prompt is an existing one:
step 3 = V6 fact-type Choice (variants.v6, Appendix A.1) on the 42 keyed facts, 2 runs; step 6 = metric-state Choice (card_prompts.STATE) 2 runs, and the
claim checker (claim_prompts.CHECK + state_claim) on the true state and all 4 wrong states, 1 run. Usage: python3 run_wf_steps.py  (~ $0.02)"""
import json, sys, time, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from variants import VARS
from card_prompts import STATE
from claim_prompts import CHECK, STATES, state_claim
from concurrent.futures import ThreadPoolExecutor
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
H = {h["id"]: h["state"] for h in json.load(open(f"{SCRATCH}/tag_holdout.json"))}; KEYS = json.load(open("wf_keys.json")); assert KEYS["hash"] == "3577655d6f3c241a"
K = KEYS["keys"]; V6 = {"fact_type": VARS["V6"]()}
def st(i, **extra):
    s = H[i]; d = {"where_it_appears": s["where_it_appears"], "driver_name": K[i]["name"], "text_before_quote": s["text_before_quote"], "quote": s["quote"], "text_after_quote": s["text_after_quote"]}
    d.update(extra); return d
jobs = []
for i, k in K.items():
    if k["type"] != "U":
        for r in (0, 1): jobs.append(("type", i, r, None, st(i), V6))
    if k["state"]:
        for r in (0, 1): jobs.append(("state", i, r, None, st(i), STATE))
        for s in STATES: jobs.append(("claim", i, 0, s, st(i, claim=state_claim(K[i]["name"], s)), CHECK))
def one(j):
    task, i, r, s, state, q = j; res = P.call(state, q); return task, i, r, s, res
t0 = time.time()
with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
out = []; err = 0
for task, i, r, s, res in R:
    if "error" in res: err += 1; print("ERR", task, i, res["error"][:100]); continue
    a = list(res["answers"].values())[0]
    out.append(dict(task=task, id=i, run=r, claimed=s, choice=a["choice"], conf=a["confidence"], p=a["probabilities"], tokens=res["usage"]["input_tokens"]))
json.dump(out, open("results_wf.json", "w"))
tok = collections.Counter(); n = collections.Counter()
for o in out: tok[o["task"]] += o["tokens"]; n[o["task"]] += 1
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s | " + " | ".join(f"{t}: {n[t]} calls, {tok[t]/n[t]:.0f} tok/call" for t in n) + f" | cost ${sum(tok.values())*0.042/1e6:.4f}")
