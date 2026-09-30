"""Fresh hold-out for the tag screen (JEV.md §6.6). 240 random corpus units (30 per source group) drawn from the SECOND stage-1 sample (sweep_para_sample.pkl,
different random documents than the first sample behind tag_sample.json), excluding any unit already used. Labeled F/N/U by Claude BEFORE any Jev call, then frozen.
No cutoff or weight was ever tuned on these. Usage: /home/faisal/EventMarketDB/venv/bin/python3 build_tag_holdout.py"""
import json, re, sys, random, pickle, collections
sys.path.insert(0, ".")
from sweep_corpus import make_state, WHERE, PKL_PARA
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
norm = lambda t: re.sub(r"\s+", " ", t).strip().lower()
used = {norm(b["state"]["quote"]) for b in json.load(open(f"{SCRATCH}/tag_sample.json"))}
used |= {norm(p["state"]["quote"]) for p in json.load(open("items_tags_pos.json"))}
random.seed(2027)
out = pickle.load(open(PKL_PARA, "rb")); groups = collections.defaultdict(list)
for st, recs in out: groups[st["group"]].append((st, recs))
sample = []
for g, lst in groups.items():
    if g == "news titles": continue
    w = [s["est_calls"] for s, _ in lst]; pool = [[(r["units"], i) for r in recs for i in range(len(r["units"]))] for _, recs in lst]
    k = 0
    while k < 30:
        si = random.choices(range(len(lst)), weights=w)[0]; units, i = random.choice(pool[si])
        if norm(units[i]) in used: continue
        used.add(norm(units[i])); sample.append(dict(id=f"H|{g}|{k:02d}", group=g, state=make_state(units, i, WHERE[g]))); k += 1
json.dump(sample, open(f"{SCRATCH}/tag_holdout.json", "w"), indent=1)
clip = lambda t, n: (" ".join(t.split())[:n - 1] + "…") if len(" ".join(t.split())) > n else " ".join(t.split())
for i, s in enumerate(sample):
    st = s["state"]; print(f"{i:3d} [{s['group'][:10]}] {clip(st['quote'], 210)} ||…{clip(st['text_before_quote'][-70:], 70)}")
