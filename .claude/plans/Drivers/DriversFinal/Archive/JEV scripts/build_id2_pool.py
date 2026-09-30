"""Big identity test, stage A (JEV.md §6.8c): a FRESH multi-industry pool of real units. Draws ~520 units per source group (7 groups, 4 per document at most, documents uniform)
from the two stage-1 document samples, excluding every unit used in an earlier test; looks up each document's company sector in Neo4j; runs the plain tag screen (loose rule, fixed in
the tag test: max fact tag - 0.5 x is_boilerplate >= 0.41); writes the flagged units in chunks of 100 for the Sonnet naming helpers.
Usage: /home/faisal/EventMarketDB/venv/bin/python3 build_id2_pool.py"""
import json, re, sys, random, pickle, collections
sys.path.insert(0, ".")
import prompts_v3 as P, tag_prompts as T
from sweep_corpus import make_state, WHERE, PKL, PKL_PARA, connect
from concurrent.futures import ThreadPoolExecutor
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
norm = lambda t: re.sub(r"\s+", " ", t).strip().lower()
used = {norm(b["state"]["quote"]) for b in json.load(open(f"{SCRATCH}/tag_sample.json"))} | {norm(h["state"]["quote"]) for h in json.load(open(f"{SCRATCH}/tag_holdout.json"))}
used |= {norm(p["state"]["quote"]) for p in json.load(open("items_tags_pos.json"))}
for f in ("card_items.json", "items_final.json", "items_more.json", "items_extra.json"): used |= {norm(p["state"]["quote"]) for p in json.load(open(f))}
GROUPS = ["prose sections", "FS sections", "press release exhibits", "filing text only", "prepared remarks", "Q&A", "news bodies"]
docs = collections.defaultdict(dict)
for pk in (PKL, PKL_PARA):
    for st, recs in pickle.load(open(pk, "rb")):
        if st["group"] in GROUPS:
            for r in recs: docs[st["group"]].setdefault(r["id"], r["units"])
rng = random.Random(4242); pool = []
for g in GROUPS:
    ids = list(docs[g]); rng.shuffle(ids); per_doc = collections.Counter(); k = 0
    for _ in range(60000):
        if k >= 520: break
        d = rng.choice(ids)
        if per_doc[d] >= 4: continue
        units = docs[g][d]; i = rng.randrange(len(units)); u = units[i]
        if not (40 <= len(u) <= 700) or norm(u) in used: continue
        used.add(norm(u)); per_doc[d] += 1
        pool.append(dict(id=f"N|{g}|{k:03d}", group=g, doc=d, state=make_state(units, i, WHERE[g]))); k += 1
print("drawn", len(pool), collections.Counter(p["group"] for p in pool))
drv = connect(); sec = {}; dset = {p["doc"] for p in pool}
with drv.session() as s:   # batched lookups (a per-document variable-length path took ~5 s each)
    csec = {r["t"]: r["sec"] for r in s.run("MATCH (c:Company) RETURN c.ticker AS t, c.sector AS sec").data()}
    tick = {d: d.split("_")[0] for d in dset if re.match(r"^[A-Z.\-]{1,6}_\d{4}-", d)}   # transcripts carry the ticker in the id
    accs = {d: d.split("_")[0] for d in dset if re.match(r"^\d{10}-\d\d-\d{6}_", d)}
    amap = {r["a"]: r["t"] for r in s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company) WHERE r.accessionNo IN $a RETURN r.accessionNo AS a, c.ticker AS t", a=list(set(accs.values()))).data()}
    for d, a in accs.items():
        if a in amap: tick[d] = amap[a]
    news = [d for d in dset if d.startswith("bzNews_")]
    for r in s.run("UNWIND $n AS i MATCH (x:News {id:i})-[]-(c:Company) RETURN i, collect(DISTINCT c.ticker)[0] AS t", n=news).data(): tick[r["i"]] = r["t"]
for d in dset: sec[d] = (tick.get(d), csec.get(tick.get(d)))
for p in pool: p["ticker"], p["sector"] = sec[p["doc"]]
print("docs", len(dset), "with company", sum(1 for d in dset if sec[d][0]), flush=True)
print("sectors:", collections.Counter(p["sector"] for p in pool).most_common(12), "| tickers", len({p["ticker"] for p in pool}))
VAR = T.variant("P"); TY = T.TYPE_TAGS
def one(p): r = P.call(p["state"], VAR); return p["id"], {q: (x["noul"] if x["type"] == "noul" else x["choice"]) for q, x in r["answers"].items()}, r["usage"]["input_tokens"]
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, pool))
tags = {i: a for i, a, _ in R}; print("tag cost $%.3f" % (sum(t for *_, t in R) * 0.042 / 1e6))
flag = [p for p in pool if max(tags[p["id"]][q] for q in TY) - 0.5 * tags[p["id"]]["is_boilerplate"] >= 0.41]
print("flagged", len(flag), "of", len(pool), collections.Counter(p["group"] for p in flag))
json.dump(pool, open(f"{SCRATCH}/id2_pool_units.json", "w")); json.dump(tags, open(f"{SCRATCH}/id2_pool_tags.json", "w"))
json.dump([p["id"] for p in flag], open("id2_flagged_ids.json", "w"))
rng.shuffle(flag)
for c in range(0, len(flag), 100):
    items = [dict(id=p["id"], where=p["state"]["where_it_appears"], before=p["state"]["text_before_quote"][-250:], quote=p["state"]["quote"], after=p["state"]["text_after_quote"][:100]) for p in flag[c:c + 100]]
    json.dump(items, open(f"{SCRATCH}/id2_name_in_{c//100:02d}.json", "w"), indent=1)
print("chunks", (len(flag) + 99) // 100)
