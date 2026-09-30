"""Tag recall test runner (JEV.md §9). Sends the five Noul tags in ONE request per unit, for every variant (P plain, C criteria, S structured, and B0 = the old
`sweep_corpus.SET_B` for reference), on the positives (items_tags_pos.json) and the labeled background sample (tag_sample.json + tag_labels.json). Stores the raw
probabilities so any flag rule can be tuned offline (composite-scoring pattern). Usage: run_tags.py --pilot | run_tags.py  (env: needs the venv for sweep_corpus)"""
import json, sys, time, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from sweep_corpus import SET_B
import tag_prompts as T
from concurrent.futures import ThreadPoolExecutor
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
assert not T.validate(), T.validate()
VARS = {"P": T.variant("P"), "C": T.variant("C"), "S": T.variant("S"), "B0": SET_B}
pos = json.load(open("items_tags_pos.json"))
bg = json.load(open(f"{SCRATCH}/tag_sample.json")); lab = json.load(open("tag_labels.json"))["labels"]
items = [dict(id=p["id"], kind="pos", type=p["type"], set=p["set"], state=p["state"]) for p in pos] + \
        [dict(id=b["id"], kind="bg", type=lab[b["id"]], set=b["group"], state=b["state"]) for b in bg]
PILOT = "--pilot" in sys.argv
if PILOT:
    pick = []
    for t in ("metric", "metric", "guidance", "action_event", "surprise", "not_surprise"): pick.append(next(i for i in items if i["kind"] == "pos" and i["type"] == t and i not in pick))
    pick += [i for i in items if i["kind"] == "bg" and i["type"] == "F"][:2] + [i for i in items if i["kind"] == "bg" and i["type"] == "N"][:2]
    items = pick
def one(a):
    it, v = a; st = it["state"]
    assert set(st) == {"where_it_appears", "text_before_quote", "quote", "text_after_quote"}, set(st)          # no driver, no label field ever reaches Jev
    r = P.call(st, VARS[v])
    if "error" in r: return it["id"], v, None, None
    return it["id"], v, {q: (a["noul"] if a["type"] == "noul" else a["choice"]) for q, a in r["answers"].items()}, r["usage"]["input_tokens"]
jobs = [(it, v) for it in items for v in VARS]
t0 = time.time()
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, jobs))
out = collections.defaultdict(dict); tok = collections.Counter(); n = collections.Counter(); err = 0
for i, v, a, t in R:
    if a is None: err += 1; continue
    out[i][v] = a; tok[v] += t; n[v] += 1
print(f"jobs {len(jobs)} errors {err} time {time.time()-t0:.0f}s | mean input tokens per call: " + ", ".join(f"{v} {tok[v]/n[v]:.0f}" for v in VARS) + f" | cost ${sum(tok.values())*0.042/1e6:.3f}")
if PILOT:
    I = {i["id"]: i for i in items}
    for iid, d in out.items():
        it = I[iid]; print(f"\n[{iid}] label={it['type']} | {it['state']['quote'][:110]!r}")
        for v in ("P", "C", "S"): print(f"   {v}: " + "  ".join(f"{q[:14]}={d[v][q]:.2f}" for q in T.ORDER))
        print("   B0: " + "  ".join(f"{q}={d['B0'][q] if isinstance(d['B0'][q], str) else round(d['B0'][q],2)}" for q in d["B0"]))
else:
    json.dump(out, open("results_tags.json", "w")); json.dump({i["id"]: dict(kind=i["kind"], type=i["type"], set=i["set"]) for i in items}, open("results_tags_meta.json", "w"))
