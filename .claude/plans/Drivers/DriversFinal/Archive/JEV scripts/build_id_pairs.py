"""Step 5 (identity check) small pair test (JEV.md §6.8b). Builds ~54 candidate pairs of real metric facts MECHANICALLY (seeded, no hand picking), so the author does not shape difficulty:
 A exact  = same normalized driver name, different quote (mostly the same measure);  B look-alike = names share a content word but differ (mostly different measures);
 C synonym = names equal only after abbreviation expansion (asm, capex, eps ...);   D random = no shared content word (easy negatives).
Writes id_pairs_blind.json (what labelers and Jev see: names, evidence, random left/right order, NO group) and id_pairs_groups.json (group tags, hidden from labelers).
Pool = the 504 named metric facts we already have (American and Delta filings only: two companies, so the sample is airline-heavy). Usage: python3 build_id_pairs.py"""
import json, re, random, collections, hashlib
C = json.load(open("card_items.json")); F = json.load(open("items_final.json"))
pool = {}
for i in C:
    if i["fact_type"] == "metric": pool.setdefault(i["state"]["quote"], dict(id=i["id"], src=i["src"][:10], st=i["state"]))
for i in F:
    if i["key"] == "metric": pool.setdefault(i["state"]["quote"], dict(id="F" + i["id"], src="final", st=i["state"]))
P = [p for p in pool.values() if 30 <= len(p["st"]["quote"]) <= 500]
ABBR = {"asm": "available seat mile", "asms": "available seat mile", "capex": "capital expenditure", "eps": "earnings per share", "rasm": "revenue per available seat mile",
        "prasm": "passenger revenue per available seat mile", "trasm": "total revenue per available seat mile", "casm": "cost per available seat mile", "rpm": "revenue passenger mile"}
STOP = {"of", "and", "the", "a", "in", "for", "to", "on", "per", "by", "with", "from"}
def norm(n):
    t = re.sub(r"[^a-z0-9 ]", " ", n.lower()).split(); t = [ABBR.get(w, w) for w in t]
    return " ".join(" ".join(t).split())
def stem(w): return w[:-1] if w.endswith("s") and len(w) > 4 else w
def words(n): return {stem(w) for w in norm(n).split() if w not in STOP and len(w) >= 4}
def raw_key(n): return " ".join(re.sub(r"[^a-z0-9 ]", " ", n.lower()).split())
rng = random.Random(5)
by = collections.defaultdict(list)
for p in P: by[" ".join(stem(w) for w in norm(p["st"]["driver_name"]).split())].append(p)
used = collections.Counter(); pairs = []
def take(a, b, g):
    if a is b or a["st"]["quote"] == b["st"]["quote"] or used[a["id"]] >= 1 or used[b["id"]] >= 1: return False
    used[a["id"]] += 1; used[b["id"]] += 1; pairs.append((g, a, b)); return True
# A exact: same normalized name AND same raw spelling
ex = [(a, b) for k, v in by.items() for i, a in enumerate(v) for b in v[i + 1:] if raw_key(a["st"]["driver_name"]) == raw_key(b["st"]["driver_name"])]
rng.shuffle(ex); n = 0
for a, b in ex:
    if n < 16 and take(a, b, "A_exact"): n += 1
# C synonym: equal after abbreviation expansion, different raw spelling
sy = [(a, b) for k, v in by.items() for i, a in enumerate(v) for b in v[i + 1:] if raw_key(a["st"]["driver_name"]) != raw_key(b["st"]["driver_name"])]
rng.shuffle(sy); n = 0
for a, b in sy:
    if n < 8 and take(a, b, "C_synonym"): n += 1
# B look-alike: share a content word, names differ after normalization
keys = list(by); lk = []
for i, k1 in enumerate(keys):
    for k2 in keys[i + 1:]:
        if words(k1) & words(k2): lk.append((rng.choice(by[k1]), rng.choice(by[k2])))
rng.shuffle(lk); n = 0
for a, b in lk:
    if n < 24 and take(a, b, "B_lookalike"): n += 1
# D random: no shared content word
n = 0
for _ in range(2000):
    a, b = rng.sample(P, 2)
    if not (words(a["st"]["driver_name"]) & words(b["st"]["driver_name"])) and n < 6 and take(a, b, "D_random"): n += 1
rng.shuffle(pairs)
def side(p): s = p["st"]; return {"name": s["driver_name"], "type": "metric", "where_it_appears": s["where_it_appears"], "text_before_quote": s["text_before_quote"][-300:], "quote": s["quote"]}
blind, groups = [], {}
for j, (g, a, b) in enumerate(pairs):
    if rng.random() < 0.5: a, b = b, a
    pid = f"IP{j:02d}"; blind.append({"id": pid, "existing": side(a), "newcomer": side(b)}); groups[pid] = {"group": g, "src": [a["src"], b["src"]], "ids": [a["id"], b["id"]]}
# E same-number: same filer, different quote, a distinctive number (thousands with a comma, or a decimal, 4+ characters) appears in both quotes, names differ or not: mostly the same measure
# reported twice (10-Q text vs press release table). Added AFTER the first 52 pairs were shuffled, with its own seed, so those 52 are unchanged.
NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+")
def nums(q): return {m for m in NUM.findall(q) if len(m) >= 4}
rng2 = random.Random(11); cand = []
for i, a in enumerate(P):
    for b in P[i + 1:]:
        if a["src"] == b["src"] and a["src"] != "final" and a["st"]["where_it_appears"] != b["st"]["where_it_appears"] and nums(a["st"]["quote"]) & nums(b["st"]["quote"]) and used[a["id"]] == 0 and used[b["id"]] == 0: cand.append((a, b))
rng2.shuffle(cand); n = 0; E = []
for a, b in cand:
    if n < 14 and used[a["id"]] == 0 and used[b["id"]] == 0 and a["st"]["quote"] != b["st"]["quote"]:
        used[a["id"]] += 1; used[b["id"]] += 1; n += 1; E.append(("E_samenumber", a, b))
for g, a, b in E:
    if rng2.random() < 0.5: a, b = b, a
    pid = f"IP{len(blind):02d}"; blind.append({"id": pid, "existing": side(a), "newcomer": side(b)}); groups[pid] = {"group": g, "src": [a["src"], b["src"]], "ids": [a["id"], b["id"]]}
json.dump(blind, open("id_pairs_blind.json", "w"), indent=1); json.dump(groups, open("id_pairs_groups.json", "w"), indent=1)
print(len(blind), collections.Counter(g["group"] for g in groups.values()), "| hash", hashlib.sha256(json.dumps(blind, sort_keys=True).encode()).hexdigest()[:16])
