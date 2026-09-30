"""XBRL concept-link test C1, FRESH TEST set key (copy of make_xbrl_c1_key.py with test file names). Original: XBRL concept-link test C1, key: two blind Sonnet labelers (A alphabetical, B reversed order) each picked the concept (or none) for every (company, name); the key keeps a cell only when both gave the SAME pick
(or both none). Alternates listed by either labeler count as acceptable. Usage: python3 make_xbrl_c1_key.py"""
import json, glob, hashlib, collections
D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
M = json.load(open("c1_test_menus.json")); NAMES = M["names"]; CO = M["companies"]
def load(tag):
    out = {}
    for f in sorted(glob.glob(f"{D}/c1t_labels_{tag}_*.json")):
        for r in json.load(open(f)): out[(r["company"], r["name"])] = r
    return out
A, B = load("A"), load("B"); cells = [(t, n) for t in CO for n in NAMES]
print("labeled A", len(A), "B", len(B), "of", len(cells), "| missing A", [c for c in cells if c not in A][:4], "B", [c for c in cells if c not in B][:4])
valid = lambda t, q: q is None or q in {c["q"] for c in CO[t]["concepts"]}
bad = [(c, w, r[c]["pick"]) for w, r in (("A", A), ("B", B)) for c in cells if c in r and not valid(c[0], r[c]["pick"])]
print("picks not in the company's list:", len(bad), bad[:4])
key, alts, unres = {}, {}, {}
for c in cells:
    if c not in A or c not in B: unres[c] = "missing"; continue
    a, b = A[c]["pick"], B[c]["pick"]
    if a == b and valid(c[0], a): key[c] = a; alts[c] = sorted(set((A[c].get("alts") or []) + (B[c].get("alts") or [])) - {a})
    else: unres[c] = (a, b)
print("agree", len(key), "of", len(cells), f"({100*len(key)/len(cells):.0f}%) | unresolved", len(unres), "| key = a concept:", sum(1 for v in key.values() if v), "| key = none:", sum(1 for v in key.values() if v is None))
by = collections.Counter(c[1] for c in unres); print("unresolved by name:", by.most_common(10))
blob = json.dumps({f"{t}|{n}": v for (t, n), v in sorted(key.items())}, sort_keys=True); h = hashlib.sha256(blob.encode()).hexdigest()[:16]
json.dump({"hash": h, "key": {f"{t}|{n}": v for (t, n), v in key.items()}, "alts": {f"{t}|{n}": v for (t, n), v in alts.items()},
           "unresolved": {f"{t}|{n}": v for (t, n), v in unres.items()}}, open("xbrl_c1_test_key.json", "w"), indent=1); print("key hash", h)
json.dump({"A": [A[c] for c in cells if c in A], "B": [B[c] for c in cells if c in B]}, open("xbrl_c1_test_labels.json", "w"))
