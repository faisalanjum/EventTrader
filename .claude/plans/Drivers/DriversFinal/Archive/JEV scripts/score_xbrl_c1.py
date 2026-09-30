"""Score XBRL concept-link test C1 (JEV.md §6.9): arms A0 (Jev pick), A1 (pick + Jev verify >= 0.5), B0 / B1 = the same plus the guards and vetoes of xbrl_checks.py (fresh code from rules 6.4/6.6).
Outcome per cell vs the two-labeler key: CORRECT (= key), ACCEPTABLE (a listed alternate), MISSED (none where the key has a concept), CORRECT_NONE, WRONG (another concept, or any concept where the key is none).
Usage: python3 score_xbrl_c1.py"""
import json, collections, sys
sys.path.insert(0, ".")
from xbrl_checks import guard, veto
M = json.load(open("c1_menus.json")); CO = M["companies"]; K = json.load(open("xbrl_c1_key.json")); KEY = K["key"]; ALT = K["alts"]
R = {(r["company"], r["name"]): r for r in json.load(open("results_xbrl_c1.json"))}
CON = {t: {c["q"]: c for c in v["concepts"]} for t, v in CO.items()}
def arms(t, n, r):
    a0 = r["pick"]; a1 = a0 if (a0 and r["verify_p"] is not None and r["verify_p"] >= 0.5) else None
    def code(p):
        if p is None: return None, None
        g = guard(n)
        if g: return None, g
        v = veto(n, CON[t][p]); return (None, v) if v else (p, None)
    b0, w0 = code(a0); b1, w1 = code(a1)
    return {"A0": a0, "A1": a1, "B0": b0, "B1": b1}, {"B0": w0, "B1": w1}
def outcome(link, t, n):
    k = KEY[f"{t}|{n}"]; alts = ALT[f"{t}|{n}"]
    if k is None: return "CORRECT_NONE" if link is None else "WRONG"
    if link == k: return "CORRECT"
    if link is None: return "MISSED"
    return "ACCEPTABLE" if link in alts else "WRONG"
cells = [c for c in KEY.keys()]; T = collections.defaultdict(collections.Counter); OUT = {}
for c in cells:
    t, n = c.split("|"); l, why = arms(t, n, R[(t, n)]); OUT[c] = (l, why)
    for a, link in l.items(): T[a][outcome(link, t, n)] += 1
kc = sum(1 for c in cells if KEY[c]); kn = len(cells) - kc
print(f"cells scored {len(cells)} (key = a concept: {kc}, key = none: {kn}); 9 unresolved cells left out\n")
print(f"{'arm':4s} {'WRONG':>6s} {'of which leaks':>15s} {'CORRECT':>8s} {'ACCEPT.':>8s} {'MISSED':>7s} {'CORR_NONE':>10s} | links kept right (of {kc})")
def leaks(a): return sum(1 for c in cells if KEY[c] is None and OUT[c][0][a] is not None)
for a, lab in (("A0", "A0  Jev pick only"), ("A1", "A1  + Jev verify"), ("B0", "B0  A0 + code checks"), ("B1", "B1  A1 + code checks")):
    o = T[a]; print(f"{a:4s} {o['WRONG']:6d} {leaks(a):15d} {o['CORRECT']:8d} {o['ACCEPTABLE']:8d} {o['MISSED']:7d} {o['CORRECT_NONE']:10d} | {o['CORRECT']+o['ACCEPTABLE']} ({100*(o['CORRECT']+o['ACCEPTABLE'])/kc:.1f}%)   [{lab}]")
print("\nWhat the code checks did (B vs A):")
for a, b in (("A0", "B0"), ("A1", "B1")):
    fixed = [c for c in cells if outcome(OUT[c][0][a], *c.split("|")) == "WRONG" and outcome(OUT[c][0][b], *c.split("|")) != "WRONG"]
    blocked = [c for c in cells if outcome(OUT[c][0][a], *c.split("|")) in ("CORRECT", "ACCEPTABLE") and outcome(OUT[c][0][b], *c.split("|")) == "MISSED"]
    newwrong = [c for c in cells if outcome(OUT[c][0][a], *c.split("|")) != "WRONG" and outcome(OUT[c][0][b], *c.split("|")) == "WRONG"]
    print(f"  {a}->{b}: wrong links removed {len(fixed)} | correct links wrongly blocked {len(blocked)} | new wrong {len(newwrong)}")
    print("     blocked correct:", collections.Counter(OUT[c][1][b].split(':')[0] if OUT[c][1][b] else '?' for c in blocked), "| removed wrong by code:", collections.Counter((OUT[c][1][b] or '?').split(':')[0] for c in fixed))
print("\nBy name (WRONG A0 / A1 / B1 ; key concept cells: right A0 / A1 / B1):")
names = M["names"]
for n in names:
    cs = [c for c in cells if c.split("|")[1] == n]; kk = [c for c in cs if KEY[c]]
    w = [sum(outcome(OUT[c][0][a], *c.split("|")) == "WRONG" for c in cs) for a in ("A0", "A1", "B1")]
    r = [sum(outcome(OUT[c][0][a], *c.split("|")) in ("CORRECT", "ACCEPTABLE") for c in kk) for a in ("A0", "A1", "B1")]
    print(f"  {n:45s} wrong {w[0]:2d}/{w[1]:2d}/{w[2]:2d}   right {r[0]:2d}/{r[1]:2d}/{r[2]:2d} of {len(kk):2d}" + ("   [guard name]" if guard(n) else ""))
print("\nEVERY WRONG link (A1 or B1), for the audit: company | name | Jev link | key | verify p")
seen = set()
for c in cells:
    t, n = c.split("|")
    for a in ("A1", "B1"):
        if outcome(OUT[c][0][a], t, n) == "WRONG" and (c, OUT[c][0][a]) not in seen:
            seen.add((c, OUT[c][0][a])); lk = OUT[c][0][a]; print(f"  [{a}] {t} | {n} | {lk} [{CON[t][lk]['label']}] | key {KEY[c]} | p={R[(t,n)]['verify_p']}")
print("\nTokens per cell:", round(sum(r['tokens'] for r in R.values())/len(R)), "| $ per cell", round(sum(r['tokens'] for r in R.values())/len(R)*0.042/1e6, 5))
