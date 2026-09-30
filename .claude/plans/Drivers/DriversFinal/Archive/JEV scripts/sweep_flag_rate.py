"""How many sentences would the cheap tags pass on? (JEV.md §9.1 task 9). Runs the 5 short tags (SET_B) on ~60 sampled units per source group and
reports the share flagged: is_fact >= 0.5 OR kind != none. The tag wording is untested for accuracy, so this is an indication, not a measurement of recall.
Usage: /home/faisal/EventMarketDB/venv/bin/python3 sweep_flag_rate.py  (needs sweep_units_sample.pkl and sweep_units_stats.json)"""
import json, sys, pickle, random, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from sweep_corpus import SET_B, make_state, WHERE, PKL
from concurrent.futures import ThreadPoolExecutor
random.seed(31)
out = pickle.load(open(PKL, "rb")); stats = json.load(open("sweep_units_stats.json"))
groups = collections.defaultdict(list)
for st, recs in out: groups[st["group"]].append((st, recs))
jobs = []
for g, lst in groups.items():
    if g == "news titles": continue
    w = [s["est_calls"] for s, _ in lst]; pool = [[(r["units"], i) for r in recs for i in range(len(r["units"]))] for _, recs in lst]
    for _ in range(60):
        si = random.choices(range(len(lst)), weights=w)[0]; units, i = random.choice(pool[si]); jobs.append((g, make_state(units, i, WHERE[g])))
def one(j):
    g, st = j; r = P.call(st, SET_B); a = r["answers"]
    return g, a["is_fact"]["noul"], a["kind"]["choice"], a["has_number"]["noul"], r["usage"]["input_tokens"]
with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
calls = collections.defaultdict(float)
for s in stats: calls[s["group"]] += s["est_calls"]
res = collections.defaultdict(list)
for g, isf, kind, num, tok in R: res[g].append((isf >= 0.5 or kind != "none", isf >= 0.5, kind != "none", num >= 0.5))
print(f"{'group':24s} {'calls M':>8s} {'flagged (is_fact or kind)':>26s} {'is_fact':>8s} {'kind!=none':>11s} {'has number':>11s}")
tot = fl = 0
for g, rows in res.items():
    n = len(rows); f = [sum(r[i] for r in rows) / n for i in range(4)]
    print(f"{g:24s} {calls[g]/1e6:8.2f} {100*f[0]:25.0f}% {100*f[1]:7.0f}% {100*f[2]:10.0f}% {100*f[3]:10.0f}%")
    tot += calls[g]; fl += calls[g] * f[0]
f = fl / tot
print(f"\nweighted share flagged (all groups except headlines): {100*f:.0f}%   | tokens spent on this check: {sum(r[4] for r in R):,} = ${sum(r[4] for r in R)*0.042/1e6:.3f}")
B, A, both = 1570, 4510, 5190
print(f"\ncost of the whole corpus (33.1M units), using the measured tokens per call:\n  tags only ........................................ ${B:,}\n  full card on everything, one call ................ ${A:,}\n  ALL ten questions in one call (fan-out) .......... ~${both:,}\n  two stages: tags, then full card on the flagged .. ${B + f*A:,.0f}   (flagged share {100*f:.0f}%)")
print(f"  break-even: two stages beat card-only while fewer than {100*(A-B)/A:.0f}% are flagged, and beat fan-out of all ten while fewer than {100*(both-B)/A:.0f}%")
