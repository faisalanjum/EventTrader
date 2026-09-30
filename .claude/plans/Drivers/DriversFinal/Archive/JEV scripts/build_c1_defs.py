"""XBRL concept-link test C1, definitions variant (JEV.md §6.9/§6.10): add to every concept in c1_test_menus.json (a) the company's OWN other labels for it (labels from the filing's own label linkbase,
source_url on sec.gov/Archives/edgar, different from the standard label; up to 3) and (b) the published documentation text (first 40 words), both read from the definitions reader's output
(scripts/xbrl_metadata_pilot/evidence/c1_test/<accession>_result.json). Nothing is written by hand; missing text stays missing. Usage: python3 build_c1_defs.py"""
import json, re, collections
R = "/home/faisal/EventMarketDB/scripts/xbrl_metadata_pilot/evidence/c1_test"
M = json.load(open("c1_test_menus.json")); rep = {r["ticker"]: r["accession"] for r in json.load(open("/home/faisal/EventMarketDB/scripts/xbrl_metadata_pilot/reports_c1_test.json"))}
words = lambda t, n: " ".join(t.split()[:n]) + (" …" if len(t.split()) > n else "")
st = collections.Counter(); out = {}
for t, v in M["companies"].items():
    try: d = json.load(open(f"{R}/{rep[t]}_result.json"))
    except Exception as e: print("MISSING result", t, e); continue
    els = {e["qname"]: e for e in d["elements"]}; cs = []
    for c in v["concepts"]:
        e = els.get(c["q"]); c = dict(c)
        if not e: st["concept not in reader output"] += 1; cs.append(c); continue
        own = []
        for l in e.get("labels") or []:
            tx = (l.get("text") or "").strip()
            if "sec.gov/Archives/edgar" in (l.get("source_url") or "") and tx and tx.lower() != c["label"].lower() and tx not in own and len(tx) <= 90: own.append(tx)
        doc = " ".join((x.get("text") or "") for x in (e.get("documentation") or []) if isinstance(x, dict)).strip()
        c["also"] = own[:3]; c["doc"] = words(re.sub(r"\s+", " ", doc), 40) if doc else ""
        st["with doc"] += bool(c["doc"]); st["with own labels"] += bool(c["also"]); st["concepts"] += 1; cs.append(c)
    out[t] = dict(v, concepts=cs)
json.dump(dict(M, companies=out), open("c1_test_menus_defs.json", "w"))
print(dict(st), "| companies", len(out))
tok = sum(len(c.get("doc", "").split()) + sum(len(a.split()) for a in c.get("also", [])) for v in out.values() for c in v["concepts"]) / max(1, sum(len(v["concepts"]) for v in out.values()))
print("extra words per concept (avg):", round(tok, 1))
