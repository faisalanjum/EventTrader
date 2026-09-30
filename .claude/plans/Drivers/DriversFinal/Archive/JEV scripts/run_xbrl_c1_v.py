"""XBRL concept-link test C1, prompt variants for Jev (JEV.md §6.9). Same procedure as run_xbrl_c1.py (chunks of 200 + none, final pick, verify); only the `read` text differs:
 P0 = rule 6.5 only (the first run).  P1 = P0 + the SAME rule text the two labelers were given (6.4 never-link list, 6.6 fixed conventions).
 P2 = P1 + naming equivalents (revenue lines, capex, total debt, cost of revenue): NEW clause written after seeing the DEV misses, so only the fresh TEST companies are a fair score.
P3 runs on SET = testdefs (c1_test_menus_defs.json). Usage: run_xbrl_c1_v.py VARIANT SET [--pilot TICKER,TICKER] [--dump]   (SET = dev -> c1_menus.json, test -> c1_test_menus.json)"""
import json, sys, time, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from concurrent.futures import ThreadPoolExecutor
P0 = ("Same metric only: cost of revenue is not revenue, a subtotal is not its total, basic is not diluted. Refuse anything related-but-different: GAAP versus non-GAAP, gross versus net, "
      "subtotal versus total, the wrong statement, or a breakdown instead of the consolidated line. When two concepts are equally exact, choose either. When unsure, choose none.")
RULES = ("Never link (choose none): events and macro causes (resignation, buyback, oil price, interest rates, tariffs, weather); ratios, derived and growth figures (margins, growth, return on invested capital, "
         "EBITDA, free cash flow, per-square-foot, mix); non-GAAP or adjusted figures. Tax rates are real GAAP line items and may link. "
         "Fixed conventions: a point-in-time share count must be an instant concept, not a period average; a bare \"earnings per share\" or share count means diluted, never the basic line; "
         "a per-share metric never maps to a total-dollar line; these pairs are always different: SG&A versus general and administrative; SG&A versus selling and marketing; "
         "operating expenses versus SG&A; total debt versus notes payable.")
VOCAB = ("Naming equivalents: \"net sales\", \"total revenue\" and \"revenue\" all mean the company's consolidated revenue line (the taxonomy usually calls it Revenues or Revenue from Contract with Customer); "
         "\"capital expenditures\" means payments to acquire property, plant and equipment or productive assets; \"total debt\" means the company's total debt line, which may be labeled long-term debt including "
         "current maturities or debt and lease obligations; \"cost of revenue\" means cost of goods and services sold.")
READ = {"P0": P0, "P1": P0 + " " + RULES, "P2": P0 + " " + RULES + " " + VOCAB, "P3": P0 + " " + RULES}   # P3 = P1 wording + concept definitions and the company's own labels in each option (no hand-written hints)
def what(c):
    w = f"{c['label']}; {c['pt']}; {c['bal'] or 'no balance'}; {c['ct'].split(':')[-1]}"
    if c.get('also'): w += ". The company also calls it: " + "; ".join(c['also'])
    if c.get('doc'): w += ". Definition: " + c['doc']
    return w
def pick_q(chunk, read):
    crit = {c["q"]: {"what": what(c)} for c in chunk}; crit["none"] = {"what": "No concept in the list is exactly this metric."}
    return {"pick": {"type": "choice", "instructions": {"question": "Which one concept in the list is exactly the metric `metric`? Choose none if no concept in the list is exactly this metric.", "read": read}, "criteria": crit}}
def verify_q(read):
    return {"verify": {"type": "noul", "instructions": {"question": "Is the concept `concept` exactly the metric `metric`?", "read": read},
        "criteria": {"true": {"what": "It is exactly this metric: the same measure, at the consolidated level."},
                     "false": {"what": "It is a related but different measure (a component, a subtotal or total, adjusted or non-GAAP, gross or net, basic or diluted, a different statement, or a breakdown), or a different metric."}}}}
def call(state, q):
    for _ in range(2):
        r = P.call(state, q)
        if "error" not in r: return r
    return r
def cell(a):
    CO, read, t, name = a; cs = CO[t]["concepts"]; toks = 0; picks = []
    for i in range(0, len(cs), 200):
        r = call({"metric": name}, pick_q(cs[i:i + 200], read))
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; x = r["answers"]["pick"]; picks.append((x["choice"], round(x["confidence"], 3)))
    win = [p for p, _ in picks if p != "none"]; final = None; fconf = None
    if len(set(win)) == 1: final = win[0]
    elif len(set(win)) >= 2:
        cw = [c for c in cs if c["q"] in set(win)]; r = call({"metric": name}, pick_q(cw, read))
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; x = r["answers"]["pick"]; final = None if x["choice"] == "none" else x["choice"]; fconf = round(x["confidence"], 3)
    v = None
    if final:
        c = next(c for c in cs if c["q"] == final); r = call({"metric": name, "concept": f"{c['label']} [{c['q']}]; {c['pt']}; {c['bal'] or 'no balance'}; {c['ct'].split(':')[-1]}"}, verify_q(read))
        if "error" in r: return dict(company=t, name=name, error=r["error"][:120])
        toks += r["usage"]["input_tokens"]; v = round(r["answers"]["verify"]["noul"], 3)
    return dict(company=t, name=name, chunk_picks=picks, pick=final, final_conf=fconf, verify_p=v, tokens=toks)
if __name__ == "__main__":
    var, sset = sys.argv[1], sys.argv[2]; M = json.load(open({"dev": "c1_menus.json", "test": "c1_test_menus.json", "testdefs": "c1_test_menus_defs.json"}[sset])); CO = M["companies"]; NAMES = M["names"]
    ts = list(CO)
    if "--pilot" in sys.argv: ts = sys.argv[sys.argv.index("--pilot") + 1].split(",")
    if "--dump" in sys.argv:
        t, n = ts[0], "capital expenditures"; q = pick_q(CO[t]["concepts"][:200], READ[var])
        s = json.dumps({"state": {"metric": n}, "model": "jev-1.13.0", "questions": q}, ensure_ascii=False); crit = q["pick"]["criteria"]; ks = list(crit)
        print(f"variant {var} | company {t} | menu {len(CO[t]['concepts'])} concepts | first chunk options {len(ks)-1} + none | request chars {len(s)}")
        print("QUESTION:", q["pick"]["instructions"]["question"]); print("READ:", q["pick"]["instructions"]["read"]); print("first options:", [(k, crit[k]['what']) for k in ks[:3]]); print("last options:", [(k, crit[k]['what']) for k in ks[-3:]])
        sys.exit()
    jobs = [(CO, READ[var], t, n) for t in ts for n in NAMES]; t0 = time.time()
    with ThreadPoolExecutor(12) as ex: R = list(ex.map(cell, jobs))
    err = [r for r in R if "error" in r]; out = f"results_xbrl_c1_{var}_{sset}{'_pilot' if '--pilot' in sys.argv else ''}.json"; json.dump(R, open(out, "w"))
    print(f"{out}: cells {len(R)} errors {len(err)} time {time.time()-t0:.0f}s cost ${sum(r.get('tokens',0) for r in R)*0.042/1e6:.3f} | picked {sum(1 for r in R if r.get('pick'))} none {sum(1 for r in R if 'pick' in r and not r['pick'])}")
