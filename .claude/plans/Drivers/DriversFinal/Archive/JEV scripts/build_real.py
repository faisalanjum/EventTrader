"""Real mistakes for the claim checker (JEV.md §6.5). Step 1: run two fact-type prompts we already have (round 1's QC4 and the
recommended V6) once on every decided fact. Step 2: every answer that differs from the decided key is a REAL model mistake; the
claim "this fact is <that wrong type>" becomes a wrong claim. Caveat: the mistakes come from Jev itself, so the checker is
asked to catch its own kind of error (harder than catching another model's).
Usage: python3 build_real.py   -> results_real_reader.json, items_claims_real.json (hash printed; freeze before any checker call)"""
import json, sys, hashlib, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from claim_prompts import TYPES, type_claim
from concurrent.futures import ThreadPoolExecutor

fin = [x for x in json.load(open("items_final.json")) + json.load(open("items_extra.json")) if x["key"] in TYPES]
PROMPTS = {"QC4": json.load(open("QC4.json"))["fact_type"], "V6": json.load(open("V6.json"))}
jobs = [(x, n) for x in fin for n in PROMPTS]

def one(a):
    x, n = a
    assert isinstance(x["state"], dict) and "quote" in x["state"]
    return x["id"], n, P.call(x["state"], {"fact_type": PROMPTS[n]})

with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
out = collections.defaultdict(dict); err = tok = 0
for i, n, r in R:
    if "error" in r: err += 1; continue
    tok += r["usage"]["input_tokens"]; a = r["answers"]["fact_type"]
    out[i][n] = dict(choice=a["choice"], conf=a["confidence"])
json.dump(out, open("results_real_reader.json", "w"), indent=1)
print(f"reader calls {len(jobs)} errors {err} cost ${tok*0.042/1e6:.3f}")

items = []
for x in fin:
    wrong = collections.defaultdict(list)
    for n in PROMPTS:
        c = out.get(x["id"], {}).get(n, {}).get("choice")
        if c and c != x["key"]: wrong[c].append(n)
    for w, ns in wrong.items():
        st = dict(x["state"]); st["claim"] = type_claim(st["driver_name"], w)
        assert "quote" in st and "claim" in st
        items.append(dict(id=f"RM|{x['id']}|{w}", state=st, L_true=False, L_task="type", L_claimed=w, L_key=x["key"],
                          L_kind=f"real {x['key']}->{w} [{'+'.join(ns)}]"))
json.dump(items, open("items_claims_real.json", "w"), indent=1)
blob = json.dumps([[i["id"], i["state"]["claim"], i["L_true"]] for i in items], sort_keys=True)
print("real mistakes", len(items), "| hash", hashlib.sha256(blob.encode()).hexdigest()[:16])
print(collections.Counter(i["L_kind"] for i in items).most_common(20))
