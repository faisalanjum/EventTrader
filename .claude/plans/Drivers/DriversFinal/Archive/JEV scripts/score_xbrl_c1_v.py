"""XBRL test C1, prompt variants (JEV.md §6.9): Jev P0/P1/P2 and Haiku on the DEV set (24 companies, used to write the hints) and the fresh TEST set (12 companies, key made after the hints were fixed).
Each model alone (pick; pick+verify) and with the code checks of xbrl_checks.py. Usage: python3 score_xbrl_c1_v.py dev|test"""
import json, glob, collections, sys, os
sys.path.insert(0, ".")
from xbrl_checks import guard, veto
S = sys.argv[1]; D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
M = json.load(open("c1_menus.json" if S == "dev" else "c1_test_menus.json")); NAMES = M["names"]; CO = M["companies"]
K = json.load(open("xbrl_c1_key.json" if S == "dev" else "xbrl_c1_test_key.json")); KEY = K["key"]; ALT = K["alts"]
CON = {t: {c["q"]: c for c in v["concepts"]} for t, v in CO.items()}
def load_jev(v):
    f = "results_xbrl_c1.json" if (S == "dev" and v == "P0") else ("results_xbrl_c1_P3_testdefs.json" if v == "P3" else f"results_xbrl_c1_{v}_{S}.json")
    return {f"{r['company']}|{r['name']}": r for r in json.load(open(f))}
VARS = ("P0", "P1", "P2") + (("P3",) if (S == "test" and os.path.exists("results_xbrl_c1_P3_testdefs.json")) else ())
J = {v: load_jev(v) for v in VARS}
# Haiku: dev picks/verify are merged in the repo; test picks/verify come from the scratchpad
if S == "dev": HP = json.load(open("results_xbrl_c1_haiku_pick.json")); HV = json.load(open("results_xbrl_c1_haiku_verify.json"))
else:
    HP = {}; HV = {}
    for t, v in CO.items():
        p = f"{D}/c1t_hk_pick_{t}.json"
        if not os.path.exists(p): continue
        valid = {c["q"] for c in v["concepts"]}
        for r in json.load(open(p)): HP[f"{t}|{r['name']}"] = r["qname"] if r.get("qname") in valid else None
        q = f"{D}/c1t_hk_verres_{t}.json"
        if os.path.exists(q):
            for r in json.load(open(q)): HV[f"{t}|{r['name']}"] = bool(r["real"])
HAVE_H = len(HP) == len(NAMES) * len(CO)
LP = {}; LV = {}
if S == "test":
    for t, v in CO.items():
        valid = {c["q"] for c in v["concepts"]}; p = f"{D}/c1t_luna_pick_{t}.json"; q = f"{D}/c1t_luna_verres_{t}.json"
        if os.path.exists(p):
            for r in json.load(open(p)): LP[f"{t}|{r['name']}"] = r.get("qname") if r.get("qname") in valid else None
        if os.path.exists(q):
            for r in json.load(open(q)): LV[f"{t}|{r['name']}"] = bool(r["real"])
HAVE_L = len(LP) == len(NAMES) * len(CO)
def code(c, p):
    t, n = c.split("|")
    if p is None: return None
    if guard(n): return None
    return None if veto(n, CON[t][p]) else p
def outcome(link, c, pl=False):
    t, n = c.split("|"); k = KEY[c]
    if k is None: return "CORRECT_NONE" if link is None else "WRONG"
    if link == k: return "CORRECT"
    if link is None: return "MISSED"
    return "ACCEPTABLE" if (link in ALT[c] or (pl and n == "net income" and link == "us-gaap:ProfitLoss")) else "WRONG"
cells = list(KEY); kc = sum(1 for c in cells if KEY[c]); A = {}
for v in VARS:
    A[f"{v} pick"] = {c: J[v][tuple(c.split("|")) and c].get("pick") for c in cells}
    A[f"{v} +verify"] = {c: (A[f"{v} pick"][c] if (A[f"{v} pick"][c] and (J[v][c]["verify_p"] or 0) >= 0.5) else None) for c in cells}
    A[f"{v} +code"] = {c: code(c, A[f"{v} pick"][c]) for c in cells}; A[f"{v} +verify+code"] = {c: code(c, A[f"{v} +verify"][c]) for c in cells}
if HAVE_H:
    A["Haiku pick"] = {c: HP.get(c) for c in cells}
    if len(HV) >= sum(1 for x in HP.values() if x):
        A["Haiku +verify"] = {c: (HP[c] if (HP.get(c) and HV.get(c, False)) else None) for c in cells}
        A["Haiku +code"] = {c: code(c, HP.get(c)) for c in cells}; A["Haiku +verify+code"] = {c: code(c, A["Haiku +verify"][c]) for c in cells}
    else: A["Haiku +code"] = {c: code(c, HP.get(c)) for c in cells}
if HAVE_L:
    A["Luna pick"] = {c: LP.get(c) for c in cells}
    if len(LV) >= sum(1 for x in LP.values() if x):
        A["Luna +verify"] = {c: (LP[c] if (LP.get(c) and LV.get(c, False)) else None) for c in cells}
        A["Luna +code"] = {c: code(c, LP.get(c)) for c in cells}; A["Luna +verify+code"] = {c: code(c, A["Luna +verify"][c]) for c in cells}
    else: A["Luna +code"] = {c: code(c, LP.get(c)) for c in cells}
    HV_L = True
if S == "test":  # Luna at lower reasoning effort: picks only
    for eff in ("low", "medium", "high"):
        E = {}
        for t, v in CO.items():
            valid = {c["q"] for c in v["concepts"]}; p = f"{D}/c1t_luna{eff}_pick_{t}.json"
            if os.path.exists(p):
                for r in json.load(open(p)): E[f"{t}|{r['name']}"] = r.get("qname") if r.get("qname") in valid else None
        if len(E) == len(NAMES) * len(CO): A[f"Luna {eff} pick"] = {c: E.get(c) for c in cells}; A[f"Luna {eff} +code"] = {c: code(c, E.get(c)) for c in cells}
if S == "test":  # local Qwen3.8 (exams/jev_replication/xbrl_results): picks only
    QD = "/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/exams/jev_replication/xbrl_results"; E = {}
    for t, v in CO.items():
        valid = {c["q"] for c in v["concepts"]}; p = f"{QD}/c1t_qwen_pick_{t}.json"
        if os.path.exists(p):
            for r in json.load(open(p)): E[f"{t}|{r['name']}"] = r.get("qname") if r.get("qname") in valid else None
    if len(E) == len(NAMES) * len(CO): A["Qwen pick"] = {c: E.get(c) for c in cells}; A["Qwen +code"] = {c: code(c, E.get(c)) for c in cells}
    elif E: print(f"(Qwen: only {len(E)} of {len(NAMES) * len(CO)} cells present, arm not scored)")
print(f"SET {S}: {len(cells)} cells scored (key = a concept {kc}, none {len(cells)-kc}); unresolved left out: {len(K['unresolved'])}\n")
print(f"{'arm':22s} {'wrong':>5s} {'(ProfitLoss ok)':>15s} {'leaks':>5s} {'right':>6s} {'missed':>6s}   links kept right (of {kc})")
for a, m in A.items():
    o = collections.Counter(outcome(m[c], c) for c in cells); o2 = collections.Counter(outcome(m[c], c, True) for c in cells); r = o["CORRECT"] + o["ACCEPTABLE"]
    print(f"{a:22s} {o['WRONG']:5d} {o2['WRONG']:15d} {sum(1 for c in cells if KEY[c] is None and m[c] is not None):5d} {r:6d} {o['MISSED']:6d}   {100*r/kc:5.1f}%")
print("\nPer name, links kept right (of key-concept cells): " + " / ".join(VARS) + (" / Haiku" if HAVE_H else "") + (" / Luna" if HAVE_L else ""))
for n in NAMES:
    cs = [c for c in cells if c.split("|")[1] == n]; kk = [c for c in cs if KEY[c]]
    if not kk and not any(A["P2 pick"][c] for c in cs): continue
    arms = [f"{v} pick" for v in VARS] + (["Haiku pick"] if HAVE_H else []) + (["Luna pick"] if HAVE_L else [])
    r = [sum(outcome(A[a][c], c) in ("CORRECT", "ACCEPTABLE") for c in kk) for a in arms]; w = [sum(outcome(A[a][c], c) == "WRONG" for c in cs) for a in arms]
    print(f"  {n:45s} {'/'.join(f'{x:2d}' for x in r)} of {len(kk):2d}   wrong {'/'.join(str(x) for x in w)}")
print("\nEVERY wrong link of P2 pick and Haiku pick: company | name | link | key")
for a in ("P2 pick", "P3 pick", "Haiku pick", "Luna pick", "Luna high pick", "Luna medium pick", "Luna low pick", "Qwen pick"):
    if a not in A: continue
    for c in cells:
        lk = A[a][c]
        if outcome(lk, c) == "WRONG": t, n = c.split("|"); print(f"  [{a}] {t} | {n} | {lk} [{CON[t][lk]['label']}] | key {KEY[c]}")
