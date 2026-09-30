"""XBRL concept-link test C1, FRESH TEST set (12 companies not in the 24 of build_xbrl_c1.py, seed 32; 1 per sector + 1 extra Technology). Same code otherwise. Original docstring: XBRL concept-link test C1 (JEV.md §6.9), stage 1: sample companies and pull each one's concept list. No linker code: plain graph reads only.
24 companies: 2 per sector (11 sectors) + 2 extra from the two largest, seeded random, each with its LATEST 10-K that has tagged data. The list = the filing's
numeric concepts that have at least one fact with NO breakdown ("the company's consolidated numeric line items", rule 6.7); text blocks, booleans, strings and dates left out.
Also writes the blind labeler files (A: alphabetical, B: reversed) into the scratchpad. Usage: /home/faisal/EventMarketDB/venv/bin/python3 build_xbrl_c1.py"""
import json, random, sys, collections
sys.path.insert(0, ".")
from sweep_corpus import connect
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
# Metric names. CORE: most frequent line-item-like names in the Sonnet-named pool (id2_named.json) + the names in rules 6.5/6.6. GUARD: names the rules say never link (6.4).
CORE = ["total revenue", "net sales", "revenue", "net income", "earnings per share", "diluted earnings per share", "basic earnings per share", "cash and cash equivalents",
        "shares outstanding", "weighted average diluted shares outstanding", "total debt", "goodwill", "research and development expense", "operating income", "operating cash flow",
        "gross profit", "capital expenditures", "selling general and administrative expense", "general and administrative expense", "cost of revenue", "operating expenses",
        "dividend per share", "income tax expense"]
GUARD = ["free cash flow", "adjusted ebitda", "adjusted earnings per share", "gross margin", "revenue growth rate", "adjusted ebitda margin"]
NAMES = CORE + GUARD
EXCL = ("textBlock", "boolean", "string", "date", "Text", "anyURI", "gYear", "Uri")
drv = connect(); rng = random.Random(32)
with drv.session() as s:
    rows = s.run("MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report {formType:'10-K'})-[:HAS_XBRL]->(x:XBRLNode) RETURN c.ticker AS t, c.sector AS sec, r.id AS rid, r.periodOfReport AS per ORDER BY per DESC").data()
    latest = {}
    for r in rows: latest.setdefault(r["t"], r)
    bysec = collections.defaultdict(list)
    dev = set(json.load(open("c1_menus.json"))["companies"])
    for r in latest.values():
        if r["t"] not in dev: bysec[r["sec"]].append(r)
    pick = []
    for sec in sorted(bysec):
        lst = sorted(bysec[sec], key=lambda r: r["t"]); rng.shuffle(lst); pick += lst[:1] + (lst[1:2] if sec == "Technology" else [])
    out = {}
    for r in pick:
        m = s.run("""MATCH (rp:Report {id:$rid})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(c:Concept)
          OPTIONAL MATCH (f)-[:IN_CONTEXT]->(cx:Context)
          WITH c, f, cx WHERE (cx IS NULL OR size(coalesce(cx.dimension_u_ids, [])) = 0) AND c.period_type IN ['duration','instant']
          RETURN c.qname AS q, c.label AS label, c.period_type AS pt, c.balance AS bal, c.concept_type AS ct, count(f) AS usage""", rid=r["rid"]).data()
        m = [x for x in m if x["ct"] and not any(e in x["ct"] for e in EXCL)]
        m.sort(key=lambda x: x["q"]); out[r["t"]] = dict(rid=r["rid"], sector=r["sec"], period=r["per"], concepts=m)
json.dump(dict(names=NAMES, core=CORE, guard=GUARD, companies=out), open("c1_test_menus.json", "w"))
import pathlib
print("companies", len(out), "| menu sizes", sorted(len(v["concepts"]) for v in out.values()), "| sectors", collections.Counter(v["sector"] for v in out.values()))
def line(x): return f"{x['q']} | {x['label']} | {x['pt']} | {x['bal'] or '-'} | {x['ct'].split(':')[-1]}"
for t, v in out.items():
    cs = v["concepts"]
    json.dump(dict(names=NAMES, concepts=[line(x) for x in cs]), open(f"{SCRATCH}/c1t_lab_A_{t}.json", "w"))
    json.dump(dict(names=list(reversed(NAMES)), concepts=[line(x) for x in reversed(cs)]), open(f"{SCRATCH}/c1t_lab_B_{t}.json", "w"))
print("files written for", len(out), "companies x 2 labelers")
