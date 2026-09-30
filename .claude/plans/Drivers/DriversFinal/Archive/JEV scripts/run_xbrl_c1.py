"""XBRL concept-link test C1 (JEV.md §6.9), Jev arms: for every (company, metric name) cell, pick from the company's real concept list. The list is cut into chunks of 200 concepts + "none" (Choice limit 255),
each chunk answers separately; if 2+ chunks name a concept, one final Choice among those winners + none; then a Jev VERIFY (Noul). No guards and no code checks here: those are applied in the scorer (arm B).
Prompt wording = rule 6.5 (same metric only; related-but-different refused). Usage: /home/faisal/EventMarketDB/venv/bin/python3 run_xbrl_c1.py  (~$0.5)"""
import json, sys, time, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from concurrent.futures import ThreadPoolExecutor
D = json.load(open("c1_menus.json")); NAMES = D["names"]; CO = D["companies"]
READ = ("Same metric only: cost of revenue is not revenue, a subtotal is not its total, basic is not diluted. Refuse anything related-but-different: GAAP versus non-GAAP, gross versus net, "
        "subtotal versus total, the wrong statement, or a breakdown instead of the consolidated line. When two concepts are equally exact, choose either. When unsure, choose none.")
def what(c): return f"{c['label']}; {c['pt']}; {c['bal'] or 'no balance'}; {c['ct'].split(':')[-1]}"
def pick_q(chunk):
    crit = {c["q"]: {"what": what(c)} for c in chunk}; crit["none"] = {"what": "No concept in the list is exactly this metric."}
    return {"pick": {"type": "choice", "instructions": {"question": "Which one concept in the list is exactly the metric `metric`? Choose none if no concept in the list is exactly this metric.", "read": READ}, "criteria": crit}}
VERIFY = {"verify": {"type": "noul", "instructions": {"question": "Is the concept `concept` exactly the metric `metric`?", "read": READ},
    "criteria": {"true": {"what": "It is exactly this metric: the same measure, at the consolidated level."},
                 "false": {"what": "It is a related but different measure (a component, a subtotal or total, adjusted or non-GAAP, gross or net, basic or diluted, a different statement, or a breakdown), or a different metric."}}}}
def call(state, q):
    for _ in range(2):
        r = P.call(state, q)
        if "error" not in r: return r
    return r
def cell(a):
    t, name = a; cs = CO[t]["concepts"]; toks = 0; picks = []
    for i in range(0, len(cs), 200):
        r = call({"metric": name}, pick_q(cs[i:i + 200]))
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; x = r["answers"]["pick"]; picks.append((x["choice"], round(x["confidence"], 3)))
    win = [p for p, _ in picks if p != "none"]; final = None; fconf = None
    if len(set(win)) == 1: final = win[0]
    elif len(set(win)) >= 2:
        cw = [c for c in cs if c["q"] in set(win)]; r = call({"metric": name}, pick_q(cw))
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; x = r["answers"]["pick"]; final = None if x["choice"] == "none" else x["choice"]; fconf = round(x["confidence"], 3)
    v = None
    if final:
        c = next(c for c in cs if c["q"] == final); r = call({"metric": name, "concept": f"{c['label']} [{c['q']}]; {c['pt']}; {c['bal'] or 'no balance'}; {c['ct'].split(':')[-1]}"}, VERIFY)
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; v = round(r["answers"]["verify"]["noul"], 3)
    return dict(company=t, name=name, chunk_picks=picks, pick=final, final_conf=fconf, verify_p=v, tokens=toks)
if __name__ == "__main__":
    jobs = [(t, n) for t in CO for n in NAMES]; t0 = time.time()
    with ThreadPoolExecutor(12) as ex: R = list(ex.map(cell, jobs))
    err = [r for r in R if "error" in r]; json.dump(R, open("results_xbrl_c1.json", "w"))
    print(f"cells {len(R)} errors {len(err)} time {time.time()-t0:.0f}s tokens {sum(r.get('tokens',0) for r in R)} cost ${sum(r.get('tokens',0) for r in R)*0.042/1e6:.3f}")
    print("picked a concept:", sum(1 for r in R if r.get('pick')), "| none:", sum(1 for r in R if 'pick' in r and not r['pick']))
