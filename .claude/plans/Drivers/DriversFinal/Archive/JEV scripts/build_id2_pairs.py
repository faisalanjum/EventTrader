"""Big identity test, stage B (JEV.md §6.8c): from the named facts build ~640 candidate pairs of look-alikes, stratified, written in blind chunks of 80 for two labelers.
Look-alike = TF-IDF cosine (name x3 + quote) top-4 neighbours within the same type (what a code shortlist would show), plus every same-name pair across documents.
Strata: same name / different name x neighbour rank 1 / 2-4 x same document / different documents; picked round-robin over (source group, source group) buckets.
Usage: python3 build_id2_pairs.py   (reads id2_named_*.json written by the naming helpers)"""
import json, re, math, random, glob, collections, hashlib
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
U = {p["id"]: p for p in json.load(open(f"{SCRATCH}/id2_pool_units.json"))}
named = {}
for f in sorted(glob.glob(f"{SCRATCH}/id2_named_*.json")):
    for r in json.load(open(f)): named[r["id"]] = r
facts = [dict(U[i], **{"name": r["name"].strip().lower(), "type": r["type"]}) for i, r in named.items() if r.get("is_fact") and r.get("type") in ("metric", "guidance") and r.get("name")]
print("named", len(named), "| facts", collections.Counter(bool(r.get("is_fact")) for r in named.values()), "| kept metric/guidance", len(facts), collections.Counter(f["type"] for f in facts))
STOP = set("the a an of and to in for on by with from is are was were be as at that this it its our we us or which".split())
def toks(t): return [w for w in re.findall(r"[a-z][a-z0-9]{2,}", t.lower()) if w not in STOP]
docs = [toks(f["name"]) * 3 + toks(f["state"]["quote"]) for f in facts]
df = collections.Counter(w for d in docs for w in set(d)); N = len(docs)
def vec(d):
    c = collections.Counter(d); v = {w: (1 + math.log(n)) * math.log(N / df[w]) for w, n in c.items()}; nm = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / nm for w, x in v.items()}
V = [vec(d) for d in docs]
def cos(a, b): return sum(x * b[w] for w, x in a.items() if w in b)
cand = {}
for i, f in enumerate(facts):
    sims = sorted(((cos(V[i], V[j]), j) for j, g in enumerate(facts) if j != i and g["type"] == f["type"] and g["state"]["quote"] != f["state"]["quote"]), reverse=True)[:4]
    for rank, (s, j) in enumerate(sims, 1):
        k = tuple(sorted((i, j))); cand.setdefault(k, dict(rank=rank, sim=s))
        cand[k]["rank"] = min(cand[k]["rank"], rank)
byname = collections.defaultdict(list)
for i, f in enumerate(facts): byname[f["name"]].append(i)
for n, ix in byname.items():
    for a in range(len(ix)):
        for b in range(a + 1, len(ix)):
            if facts[ix[a]]["type"] == facts[ix[b]]["type"] and facts[ix[a]]["state"]["quote"] != facts[ix[b]]["state"]["quote"]: cand.setdefault(tuple(sorted((ix[a], ix[b]))), dict(rank=0, sim=cos(V[ix[a]], V[ix[b]])))
def stratum(k, c):
    a, b = facts[k[0]], facts[k[1]]
    return ("same_name" if a["name"] == b["name"] else "diff_name", "rank1" if c["rank"] <= 1 else "rank2_4", "same_doc" if a["doc"] == b["doc"] else "diff_doc")
rng = random.Random(77); pools = collections.defaultdict(list)
for k, c in cand.items(): pools[stratum(k, c)].append(k)
print("candidate pairs", len(cand), {"/".join(s): len(v) for s, v in sorted(pools.items())})
QUOTA = {"same_name": 170, "diff_name": 470}   # same-name pairs are the dangerous slice; different-name split rank1 : rank2-4 = 55 : 45
picked = []
for nm, q in QUOTA.items():
    ss = [s for s in pools if s[0] == nm]
    # round-robin over source-group buckets inside each stratum so no source dominates
    buckets = collections.defaultdict(list)
    for s in ss:
        for k in pools[s]: buckets[(s, facts[k[0]]["group"], facts[k[1]]["group"])].append(k)
    for b in buckets.values(): rng.shuffle(b)
    keys = list(buckets); rng.shuffle(keys); got = []
    weight = {s: (0.55 if s[1] == "rank1" else 0.45) if nm == "diff_name" else 1 / max(1, len(ss)) for s in ss}
    cap = {s: int(q * weight[s] / sum(weight.values() if False else [weight[t] for t in ss]) + 0.999) for s in ss}
    cnt = collections.Counter(); progress = True
    while len(got) < q and progress:
        progress = False
        for b in keys:
            if buckets[b] and cnt[b[0]] < cap[b[0]] and len(got) < q: got.append(buckets[b].pop()); cnt[b[0]] += 1; progress = True
    for s in ss:   # fill any shortfall from the remaining pairs of the other strata
        pass
    picked += got
if len(picked) < sum(QUOTA.values()):
    left = [k for k in cand if k not in set(picked)]; rng.shuffle(left); picked += left[:sum(QUOTA.values()) - len(picked)]
rng.shuffle(picked)
def side(f): s = f["state"]; return {"name": f["name"], "type": f["type"], "where_it_appears": s["where_it_appears"], "text_before_quote": s["text_before_quote"][-250:], "quote": s["quote"][:500]}
blind, hidden = [], {}
for j, k in enumerate(picked):
    a, b = (facts[k[0]], facts[k[1]]) if rng.random() < 0.5 else (facts[k[1]], facts[k[0]])
    pid = f"BP{j:03d}"; blind.append({"id": pid, "existing": side(a), "newcomer": side(b)})
    hidden[pid] = dict(stratum="/".join(stratum(k, cand[k])), sim=round(cand[k]["sim"], 3), groups=[a["group"], b["group"]], sectors=[a["sector"], b["sector"]], tickers=[a["ticker"], b["ticker"]], ids=[a["id"], b["id"]])
json.dump(blind, open("id2_pairs_blind.json", "w")); json.dump(hidden, open("id2_pairs_groups.json", "w"), indent=1)
for c in range(0, len(blind), 80):
    ch = blind[c:c + 80]; json.dump(ch, open(f"{SCRATCH}/id2_lab_A_{c//80:02d}.json", "w"))
    json.dump([{"id": p["id"], "existing": p["newcomer"], "newcomer": p["existing"]} for p in reversed(ch)], open(f"{SCRATCH}/id2_lab_B_{c//80:02d}.json", "w"))   # B: sides swapped, order reversed
print("pairs", len(blind), collections.Counter(h["stratum"].split("/")[0] for h in hidden.values()), "chunks", (len(blind) + 79) // 80,
      "| sectors in pairs", len({s for h in hidden.values() for s in h["sectors"]}), "| hash", hashlib.sha256(json.dumps(blind, sort_keys=True).encode()).hexdigest()[:16])
