"""Items for the tag recall test (JEV.md §9). POSITIVES = every known fact we have a decided/agreed type for (fact-type decided set + fact-card set), de-duplicated
by quote, state WITHOUT driver_name (a sweep does not know the driver). BACKGROUND = random corpus units drawn like the sweep estimate (stratified by source group),
which I label by reading them BEFORE any Jev call (F = states a fact the Driver system could store, N = boilerplate/heading/cross-reference/etc., U = unclear).
Usage: /home/faisal/EventMarketDB/venv/bin/python3 build_tag_items.py   -> items_tags_pos.json (repo) + tag_sample.json (scratchpad, has filing text)"""
import json, re, sys, random, pickle, collections
sys.path.insert(0, ".")
from sweep_corpus import make_state, WHERE, PKL
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
def norm(t): return re.sub(r"\s+", " ", t).strip().lower()
pos, seen = [], set()
for x in json.load(open("items_final.json")) + json.load(open("items_extra.json")):
    if x["key"] == "undecided": continue
    q = norm(x["state"]["quote"])
    if q in seen: continue
    seen.add(q); st = {k: v for k, v in x["state"].items() if k != "driver_name"}
    pos.append(dict(id="P|" + x["id"], set=x["set"], type=x["key"], state=st))
for x in json.load(open("card_items.json")):
    q = norm(x["state"]["quote"])
    if q in seen: continue
    seen.add(q); st = {k: v for k, v in x["state"].items() if k != "driver_name"}
    pos.append(dict(id="P|" + x["id"], set="card", type=x["fact_type"], state=st))
# surprise test items (Claude's labels, frozen before that run, hash b43d406630dce0a8): 42 surprise claims = positives for the surprise tag;
# the 23 look-alike controls (guidance movements, comparisons with last year, "consensus" in another sense) = hard negatives for it. 10 unclear ones are left out.
for x in json.load(open("surprise_items.json")):
    if not x["scored"]: continue
    q = norm(x["state"]["quote"])
    if q in seen: continue
    seen.add(q); st = {k: v for k, v in x["state"].items() if k != "driver_name"}
    pos.append(dict(id="P|" + x["id"], set="surprise-test", type=x["key"], state=st))
for p in pos: assert "quote" in p["state"] and "driver_name" not in p["state"]
json.dump(pos, open("items_tags_pos.json", "w"), indent=1)
print("positives:", len(pos), collections.Counter(p["type"] for p in pos), "| sets:", collections.Counter(p["set"] for p in pos))

random.seed(77)
out = pickle.load(open(PKL, "rb")); groups = collections.defaultdict(list)
for st, recs in out: groups[st["group"]].append((st, recs))
sample = []
for g, lst in groups.items():
    if g == "news titles": continue
    w = [s["est_calls"] for s, _ in lst]; pool = [[(r["units"], i) for r in recs for i in range(len(r["units"]))] for _, recs in lst]
    for k in range(15):
        si = random.choices(range(len(lst)), weights=w)[0]; units, i = random.choice(pool[si])
        st = make_state(units, i, WHERE[g]); sample.append(dict(id=f"B|{g}|{k:02d}", group=g, state=st))
json.dump(sample, open(f"{SCRATCH}/tag_sample.json", "w"), indent=1)
print("background sample:", len(sample))
