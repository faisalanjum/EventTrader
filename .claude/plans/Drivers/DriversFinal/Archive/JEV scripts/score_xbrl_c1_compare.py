"""XBRL test C1: Jev vs Haiku on the same 696 cells, same key, each alone and with the code checks of xbrl_checks.py. Haiku = production PICK/VERIFY prompt text from concept_linker.py, one Haiku helper
per company (menu lines "qname|label"); Jev = the Choice/Noul prompts of run_xbrl_c1.py. Usage: python3 score_xbrl_c1_compare.py"""
import json, glob, collections, sys
sys.path.insert(0, ".")
from xbrl_checks import guard, veto
D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
M = json.load(open("c1_menus.json")); CO = M["companies"]; NAMES = M["names"]; K = json.load(open("xbrl_c1_key.json")); KEY = K["key"]; ALT = K["alts"]
CON = {t: {c["q"]: c for c in v["concepts"]} for t, v in CO.items()}
J = {(r["company"], r["name"]): r for r in json.load(open("results_xbrl_c1.json"))}
HP = json.load(open("results_xbrl_c1_haiku_pick.json"))
HV = {}
for f in sorted(glob.glob(f"{D}/c1_hk_verres_*.json")):
    t = f.split("verres_")[1][:-5]
    for r in json.load(open(f)): HV[f"{t}|{r['name']}"] = bool(r["real"])
json.dump(HV, open("results_xbrl_c1_haiku_verify.json", "w"))
def code(t, n, p):
    if p is None: return None, None
    g = guard(n)
    if g: return None, g
    v = veto(n, CON[t][p]); return (None, v) if v else (p, None)
def arms(c):
    t, n = c.split("|"); r = J[(t, n)]
    j0 = r["pick"]; j1 = j0 if (j0 and (r["verify_p"] or 0) >= 0.5) else None
    h0 = HP[c]; h1 = h0 if (h0 and HV.get(c, False)) else None
    a = {"J0": j0, "J1": j1, "H0": h0, "H1": h1}; w = {}
    for k in ("J0", "J1", "H0", "H1"): a["B" + k], w["B" + k] = code(t, n, a[k])
    return a, w
def outcome(link, c, profitloss_ok=False):
    t, n = c.split("|"); k = KEY[c]
    if k is None: return "CORRECT_NONE" if link is None else "WRONG"
    if link == k: return "CORRECT"
    if link is None: return "MISSED"
    if link in ALT[c] or (profitloss_ok and n == "net income" and link == "us-gaap:ProfitLoss"): return "ACCEPTABLE"
    return "WRONG"
cells = list(KEY); OUT = {c: arms(c) for c in cells}; kc = sum(1 for c in cells if KEY[c])
LAB = [("J0", "Jev pick only"), ("J1", "Jev pick + Jev verify"), ("BJ0", "Jev pick + code checks"), ("BJ1", "Jev pick + verify + code"),
       ("H0", "Haiku pick only"), ("H1", "Haiku pick + Haiku verify"), ("BH0", "Haiku pick + code checks"), ("BH1", "Haiku pick + verify + code")]
print(f"{len(cells)} cells scored (key = a concept {kc}, none {len(cells)-kc}); Haiku verify answers: {len(HV)}\n")
print(f"{'arm':4s} {'wrong':>5s} {'(if ProfitLoss ok)':>19s} {'leaks':>5s} {'right':>6s} {'missed':>6s} | links kept right (of {kc})    label")
for a, lab in LAB:
    o = collections.Counter(outcome(OUT[c][0][a], c) for c in cells); o2 = collections.Counter(outcome(OUT[c][0][a], c, True) for c in cells)
    leaks = sum(1 for c in cells if KEY[c] is None and OUT[c][0][a] is not None); right = o["CORRECT"] + o["ACCEPTABLE"]
    print(f"{a:4s} {o['WRONG']:5d} {o2['WRONG']:19d} {leaks:5d} {right:6d} {o['MISSED']:6d} | {100*right/kc:5.1f}%   {lab}")
print("\nCode checks on each model (alone -> with code): wrong removed / correct wrongly blocked")
for a, b in (("J0", "BJ0"), ("J1", "BJ1"), ("H0", "BH0"), ("H1", "BH1")):
    fixed = [c for c in cells if outcome(OUT[c][0][a], c) == "WRONG" and outcome(OUT[c][0][b], c) != "WRONG"]
    blocked = [c for c in cells if outcome(OUT[c][0][a], c) in ("CORRECT", "ACCEPTABLE") and outcome(OUT[c][0][b], c) == "MISSED"]
    print(f"  {a}->{b}: removed {len(fixed)} wrong ({collections.Counter((OUT[c][1][b] or '?').split(':')[0] for c in fixed)}), blocked {len(blocked)} correct")
print("\nPer name: right (of key-concept cells) J0 / H0 / BH1, and wrong J0 / H0 / BH1:")
for n in NAMES:
    cs = [c for c in cells if c.split("|")[1] == n]; kk = [c for c in cs if KEY[c]]
    r = [sum(outcome(OUT[c][0][a], c) in ("CORRECT", "ACCEPTABLE") for c in kk) for a in ("J0", "H0", "BH1")]; w = [sum(outcome(OUT[c][0][a], c) == "WRONG" for c in cs) for a in ("J0", "H0", "BH1")]
    print(f"  {n:45s} right {r[0]:2d}/{r[1]:2d}/{r[2]:2d} of {len(kk):2d}   wrong {w[0]:2d}/{w[1]:2d}/{w[2]:2d}")
print("\nEVERY Haiku wrong link (H0 or H1): company | name | Haiku link | key | verify said real")
seen = set()
for c in cells:
    t, n = c.split("|")
    for a in ("H0", "H1"):
        lk = OUT[c][0][a]
        if outcome(lk, c) == "WRONG" and (c, lk) not in seen:
            seen.add((c, lk)); print(f"  [{a}] {t} | {n} | {lk} [{CON[t][lk]['label']}] | key {KEY[c]} | verify {HV.get(c)} | code veto: {OUT[c][1].get('BH0')}")
both = sum(1 for c in cells if OUT[c][0]["J0"] == OUT[c][0]["H0"]); print(f"\nJev pick == Haiku pick in {both} of {len(cells)} cells")
