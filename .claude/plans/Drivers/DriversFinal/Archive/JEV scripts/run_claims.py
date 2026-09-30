"""Run the claim checker (JEV.md §6.5) over the frozen claim items, two runs each, saving the full probabilities.
Usage: python3 run_claims.py --pilot   (6 items, prints one raw answer)   |   python3 run_claims.py   (everything)"""
import json, sys, collections, time
sys.path.insert(0, ".")
import prompts_v3 as P
from claim_prompts import CHECK
from concurrent.futures import ThreadPoolExecutor

V2 = "--v2" in sys.argv
items = json.load(open("items_claims_v2.json")) if V2 else json.load(open("items_claims.json")) + json.load(open("items_claims_real.json"))
PILOT = "--pilot" in sys.argv
if PILOT:
    items = [i for i in items if i["id"].startswith("FT|DEV-00")][:6] + [i for i in items if i["id"].startswith("RM|")][:2]
jobs = [(x, r) for x in items for r in ((0,) if PILOT else (0, 1))]

def one(a):
    x, r = a
    assert isinstance(x["state"], dict) and "quote" in x["state"] and "claim" in x["state"]   # never send a label
    return x["id"], r, P.call(x["state"], CHECK)

t0 = time.time()
with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
out = collections.defaultdict(dict); err = tok = 0
for i, r, res in R:
    if "error" in res: err += 1; print("ERR", i, res["error"][:120]); continue
    tok += res["usage"]["input_tokens"]; a = res["answers"]["verdict"]
    out[i][f"r{r}"] = dict(choice=a["choice"], conf=a["confidence"], p=a["probabilities"])
if PILOT:
    print(json.dumps(R[0][2], indent=1)[:900])
    for x in items:
        a = out[x["id"]]["r0"]; print(f"{x['id']:22s} true={x['L_true']!s:5s} -> {a['choice']:13s} conf {a['conf']:.2f} | {x['state']['claim'][:70]}")
else:
    json.dump(out, open("results_claims_v2.json" if V2 else "results_claims.json", "w"), indent=1)
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s tokens {tok} cost ${tok*0.042/1e6:.3f}")
