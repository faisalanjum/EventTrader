#!/usr/bin/env python3
"""Score the matcher (concept_linker.link, faithful) vs INDEPENDENT non-LLM ground truth, across
ALL companies + all 4 fact_types. Precision uses CONFIRMED-WRONG (cross-family or structural
contradiction — no LLM). Out-of-GT-family-but-plausible = REVIEW (possible GT gap). Stability =
flip rate across runs. Usage: python score_revalidation.py [run1 run2 run3]
"""
import json, sys, pathlib, collections

CLRV = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")
runs = sys.argv[1:] or ["run1"]

def localname(qn): return qn.split(":",1)[1] if ":" in qn else qn

def load_runs():
    """run -> {ticker -> {slug -> {qname, real}}}"""
    out = {}
    for rn in runs:
        d = {}
        for f in (CLRV/rn).glob("*.json"):
            try: arr = json.loads(f.read_text())
            except Exception: continue
            d[f.stem] = {r["slug"]: r for r in arr if isinstance(r, dict) and r.get("slug")}
        out[rn] = d
    return out

def final_link(rec, menu_qset):
    """Exact concept_linker.link final logic: pick if (real and pick in menu) else None."""
    if not rec: return None
    q = rec.get("qname")
    if not q or not rec.get("real"): return None
    return q if q in menu_qset else None

def main():
    gt = json.loads((CLRV/"probe_gt.json").read_text())
    local2metric = {k: set(v) for k, v in json.loads((CLRV/"local2metric.json").read_text()).items()}
    meta = {r["ticker"]: r for r in json.loads((CLRV/"company_meta.json").read_text())}
    menus = {}
    struct = {}
    for f in (CLRV/"menus").glob("*.json"):
        rows = json.loads(f.read_text())
        menus[f.stem] = {r["qname"] for r in rows}
        struct[f.stem] = {r["qname"]: r for r in rows}
    runsd = load_runs()
    main_run = runs[0]
    R = runsd[main_run]
    COMPLETED = set(R.keys())   # only score companies that actually produced matcher output
    print(f"(scoring {len(COMPLETED)} completed companies of {len(menus)})")

    # CANON expected structure via gt cell
    def classify(t, slug, cell):
        """Return (bucket, detail). bucket in CORRECT_LINK, WRONG, REVIEW, RECALL_MISS, CORRECT_ABSTAIN, LEAK."""
        qset = menus.get(t, set())
        if cell["guarded"]:
            fl = None                                  # guarded → abstain (no LLM), faithful
        else:
            fl = final_link(R.get(t, {}).get(slug), qset)
        if cell["gt_type"] == "link":
            fam = set(cell["gt_family"])
            if fl is None: return "RECALL_MISS", None
            if fl in fam: return "CORRECT_LINK", None
            # not a GT family member — is it CONFIRMED-WRONG?
            ln = localname(fl); base = cell["base"]
            mets = local2metric.get(ln, set())
            if mets and base not in mets:
                return "WRONG", f"cross-family:{ln}->{sorted(mets)}"
            # structural contradiction?
            srow = struct.get(t, {}).get(fl, {})
            eb, ep = cell.get("exp_balance"), cell.get("exp_ptype")
            if eb and srow.get("balance") and srow["balance"] != eb:
                return "WRONG", f"balance {srow['balance']}!={eb}:{ln}"
            if ep and srow.get("period_type") and srow["period_type"] != ep:
                return "WRONG", f"ptype {srow['period_type']}!={ep}:{ln}"
            return "REVIEW", f"out-of-family:{ln}"
        else:  # gt_type == abstain
            if fl is None: return "CORRECT_ABSTAIN", None
            ln = localname(fl); base = cell["base"]
            mets = local2metric.get(ln, set())
            # linking a real concept to a conceptless/absent metric = leak (precision fail)
            return "LEAK", f"{ln}"

    by_cat = collections.defaultdict(collections.Counter)
    fails = {"WRONG": [], "LEAK": [], "REVIEW": []}
    for key, cell in gt.items():
        t, slug = key.split("|", 1)
        if t not in menus or t not in COMPLETED: continue
        bucket, detail = classify(t, slug, cell)
        ft = {"core":"metric","variant":"guidance/surprise","ratio":"conceptless_ratio",
              "event":"conceptless_event(action)","macro":"conceptless_macro",
              "nongaap":"conceptless_nongaap","kpi":"conceptless_kpi"}[cell["cat"]]
        by_cat[ft][bucket] += 1
        if bucket in fails: fails[bucket].append((t, slug, detail))

    print(f"=== RE-VALIDATION (main run={main_run}, {len(menus)} companies) ===\n")
    for ft, c in by_cat.items():
        tot = sum(c.values())
        print(f"[{ft}] n={tot}")
        for b in ["CORRECT_LINK","RECALL_MISS","WRONG","REVIEW","CORRECT_ABSTAIN","LEAK"]:
            if c[b]: print(f"    {b}: {c[b]}")
        # metric-type precision: emitted = CORRECT_LINK+WRONG+REVIEW(+LEAK for abstain cats)
        if c["CORRECT_LINK"] or c["WRONG"] or c["REVIEW"]:
            emit = c["CORRECT_LINK"]+c["WRONG"]+c["REVIEW"]
            print(f"    precision(confirmed-correct/(emitted excl review)) = "
                  f"{c['CORRECT_LINK']}/{c['CORRECT_LINK']+c['WRONG']} "
                  f"= {c['CORRECT_LINK']/max(c['CORRECT_LINK']+c['WRONG'],1):.3%}  (REVIEW={c['REVIEW']})")
            if c["CORRECT_LINK"]+c["RECALL_MISS"]:
                print(f"    recall = {c['CORRECT_LINK']}/{c['CORRECT_LINK']+c['RECALL_MISS']} "
                      f"= {c['CORRECT_LINK']/(c['CORRECT_LINK']+c['RECALL_MISS']):.1%}")
        if c["CORRECT_ABSTAIN"] or c["LEAK"]:
            ab = c["CORRECT_ABSTAIN"]+c["LEAK"]
            print(f"    abstention = {c['CORRECT_ABSTAIN']}/{ab} = {c['CORRECT_ABSTAIN']/max(ab,1):.3%}  (LEAK={c['LEAK']})")
        print()

    # totals
    tot_wrong = sum(len(v) for k,v in fails.items() if k=="WRONG")
    tot_leak = len(fails["LEAK"]); tot_review = len(fails["REVIEW"])
    print(f"TOTAL confirmed-WRONG links: {tot_wrong}")
    print(f"TOTAL abstention LEAKS: {tot_leak}")
    print(f"TOTAL REVIEW (out-of-GT-family, needs adjudication): {tot_review}")
    (CLRV/"score_main.json").write_text(json.dumps(
        {"by_cat":{k:dict(v) for k,v in by_cat.items()}, "fails":fails}))

    # stability across runs (only if >1 run present)
    present = [rn for rn in runs if runsd[rn]]
    if len(present) >= 2:
        flips = 0; cells = 0
        for key, cell in gt.items():
            if cell["guarded"]: continue
            t, slug = key.split("|",1)
            if t not in menus: continue
            outs = []
            for rn in present:
                fl = final_link(runsd[rn].get(t,{}).get(slug), menus[t])
                outs.append(fl)
            cells += 1
            if len(set(outs)) > 1: flips += 1
        print(f"\nSTABILITY ({len(present)} runs): {cells} non-guarded cells, "
              f"flip rate = {flips/max(cells,1):.2%} ({flips} flipped)")

    # stratum split (precision/recall on metric-type, guidance vs non-guidance)
    print("\n=== stratum: guidance vs non-guidance (metric+variant link cells) ===")
    for label, pred in [("guidance", lambda t: meta.get(t,{}).get("n_guidance",0)>0),
                        ("non-guidance", lambda t: meta.get(t,{}).get("n_guidance",0)==0)]:
        cl=w=rv=rm=0
        for key,cell in gt.items():
            if cell["cat"] not in ("core","variant") or cell["gt_type"]!="link": continue
            t,slug=key.split("|",1)
            if t not in menus or t not in COMPLETED or not pred(t): continue
            b,_=classify(t,slug,cell)
            cl+=b=="CORRECT_LINK"; w+=b=="WRONG"; rv+=b=="REVIEW"; rm+=b=="RECALL_MISS"
        print(f"  {label}: correct={cl} wrong={w} review={rv} miss={rm} "
              f"precision={cl/max(cl+w,1):.2%} recall={cl/max(cl+rm,1):.1%}")

if __name__ == "__main__":
    main()
