import json, re, pathlib, collections
CLRV = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")
def ln(q): return q.split(":",1)[1] if q and ":" in q else q
gt = json.loads((CLRV/"probe_gt.json").read_text())
l2m = {k:set(v) for k,v in json.loads((CLRV/"local2metric.json").read_text()).items()}
struct = {}; menus = {}
for f in (CLRV/"menus").glob("*.json"):
    rows = json.loads(f.read_text()); menus[f.stem] = {r["qname"] for r in rows}
    struct[f.stem] = {r["qname"]:r for r in rows}

# --- minimal deterministic backstop: 2 rules, no per-metric curation ---
INSTANT_STOCK = re.compile(r"shares_outstanding|shares_issued")   # point-in-time share counts
def backstop_veto(t, slug, qname):
    row = struct.get(t,{}).get(qname,{})
    pt = row.get("period_type")
    if INSTANT_STOCK.search(slug) and pt == "duration":           # A: stock metric got a flow concept
        return "A_period_type"
    if slug in ("eps","share_count","shares") and "Basic" in (ln(qname) or ""):  # B: bare eps→Basic (conv=diluted)
        return "B_basic_diluted"
    return None

def fl(rec, qs):
    q = rec.get("qname") if rec else None
    return q if (q and rec.get("real") and q in qs) else None

def score(run, apply_backstop):
    R = {f.stem:{r["slug"]:r for r in json.loads(f.read_text()) if r.get("slug")} for f in (CLRV/run).glob("*.json")}
    COMP = set(R)
    correct=wrong=vetoed_correct=vetoed_wrong=0
    for k,c in gt.items():
        if c["cat"] not in ("core","variant") or c["gt_type"]!="link": continue
        t,slug=k.split("|",1)
        if t not in COMP or t not in menus: continue
        q = fl(R.get(t,{}).get(slug,{}), menus[t])
        if q is None: continue
        is_correct = q in set(c["gt_family"])
        is_wrong = (not is_correct) and (ln(q) in l2m and c["base"] not in l2m[ln(q)])
        if apply_backstop and backstop_veto(t,slug,q):
            if is_correct: vetoed_correct+=1   # MUST be 0 (safety)
            elif is_wrong: vetoed_wrong+=1
            continue
        correct += is_correct; wrong += is_wrong
    return correct,wrong,vetoed_correct,vetoed_wrong

for run in ["run1","run_haiku"]:
    c0,w0,_,_ = score(run, False)
    c1,w1,vc,vw = score(run, True)
    name = "OPUS(run1)" if run=="run1" else "HAIKU"
    print(f"{name:12s}  baseline: correct={c0} wrong={w0}  |  +backstop: correct={c1} wrong={w1}  "
          f"(vetoed {vw} wrong, {vc} correct[MUST=0])")
