"""Haiku arm of XBRL test C1: merge the Haiku pick answers (picks must be exact menu qnames; anything else counts as none) into results_xbrl_c1_haiku_pick.json and write the verify inputs
(one file per company with the proposed links). Usage: python3 build_hk_verify.py"""
import json, glob
D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
M = json.load(open("c1_menus.json")); NAMES = M["names"]; out = {}; bad = []
for t, v in M["companies"].items():
    try: rows = json.load(open(f"{D}/c1_hk_pick_{t}.json"))
    except Exception as e: print("MISSING", t, e); continue
    valid = {c["q"]: c for c in v["concepts"]}; got = {r["name"]: r.get("qname") for r in rows}
    if set(got) != set(NAMES): print("names mismatch", t, len(got), set(NAMES) - set(got))
    props = []
    for n in NAMES:
        q = got.get(n)
        if q is not None and q not in valid: bad.append((t, n, q)); q = None
        out[f"{t}|{n}"] = q
        if q: props.append({"name": n, "qname": q, "label": valid[q]["label"]})
    json.dump({"company": t, "proposals": props}, open(f"{D}/c1_hk_ver_{t}.json", "w"))
json.dump(out, open("results_xbrl_c1_haiku_pick.json", "w"))
print("cells", len(out), "| picked a concept", sum(1 for x in out.values() if x), "| none", sum(1 for x in out.values() if not x), "| invalid qnames treated as none:", len(bad), bad[:3])
