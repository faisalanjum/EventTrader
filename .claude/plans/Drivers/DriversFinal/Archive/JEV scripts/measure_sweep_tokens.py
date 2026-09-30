"""Measure the real input tokens of a "5 questions per sentence" call (JEV.md §9.1 task 9, the whole-corpus sweep estimate).
A: the five fact-card questions we actually tested (fact type V6, state, unit of the value, span vs moment, baseline), with driver_name.
B: five short tagging questions (four yes/no + one short Choice), no driver_name (a sweep does not know the driver yet).
Each question alone and all five together, on 40 decided facts (the state = sentence + context, as in every test). ~$0.02.
Usage: python3 measure_sweep_tokens.py  -> results_sweep_tokens.json + a summary"""
import json, sys, random, statistics
sys.path.insert(0, ".")
import prompts_v3 as P
from card_prompts import STATE, UNIT_LEVEL, TIMETYPE
from more_prompts import BASELINE
from concurrent.futures import ThreadPoolExecutor

V6 = {"fact_type": json.load(open("V6.json"))}
A = {"fact_type": V6["fact_type"], **STATE, **UNIT_LEVEL, **TIMETYPE, **BASELINE}
READ = "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see what `quote` refers to."
def yn(q, yes, no): return {"type": "noul", "instructions": {"question": q, "read": READ}, "criteria": {"true": {"what": yes}, "false": {"what": no}}}
B = {
 "is_fact": yn("Does `quote` state a fact about the company?", "It states something that is true or planned for the company.", "It is boilerplate, a disclaimer, a heading or a bare mention."),
 "is_forecast": yn("Does `quote` give the company's own forecast or outlook?", "The company itself says what it expects or targets.", "It reports what happened, or the forecast is someone else's."),
 "vs_expectation": yn("Does `quote` compare a result or forecast with an outside expectation such as the consensus?", "It compares with analysts or another outside party.", "No such comparison."),
 "has_number": yn("Does `quote` state a number or an amount?", "It gives a number, an amount or a percentage.", "It gives none."),
 "kind": {"type": "choice", "instructions": {"question": "Which kind of fact does `quote` state?", "read": READ}, "criteria": {
   "metric": {"what": "A standing level that can be read again."}, "guidance": {"what": "The company's own forecast."},
   "surprise": {"what": "A result compared with an outside expectation."}, "action_event": {"what": "A one-time happening."}, "none": {"what": "No fact."}}},
}
fin = [x for x in json.load(open("items_final.json")) if x["key"] != "undecided"]
random.seed(7); S = random.sample(fin, 40)

def sset(name, qs, drop_driver):
    jobs = []
    for x in S:
        st = dict(x["state"])
        if drop_driver: st.pop("driver_name", None)
        assert "quote" in st
        for k in qs: jobs.append((name, k, x["id"], st, {k: qs[k]}))
        jobs.append((name, "ALL5", x["id"], st, qs))
    return jobs
jobs = sset("A", A, False) + sset("B", B, True)
def one(j):
    name, k, i, st, qs = j; r = P.call(st, qs)
    return name, k, i, r["usage"]["input_tokens"] if "usage" in r else None
with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
tok = {}
for name, k, i, t in R:
    if t is not None: tok.setdefault((name, k), []).append(t)
out = {f"{n}|{k}": statistics.mean(v) for (n, k), v in tok.items()}
json.dump(out, open("results_sweep_tokens.json", "w"), indent=1)
for name in ("A", "B"):
    print(f"\n== {name}: mean input tokens per call (40 facts)")
    for (n, k), v in tok.items():
        if n == name: print(f"   {k:16s} {statistics.mean(v):7.0f}")
print(f"\nmeasurement cost ${sum(sum(v) for v in tok.values())*0.042/1e6:.3f}")
