"""Score the claim checker (JEV.md §6.5). A claim PASSES when Jev answers `supports`; anything else is a FLAG.
RIGHT claims should pass (a flag = a good fact wrongly flagged); WRONG claims should be flagged (a pass = an escape).
Usage: python3 score_claims.py            summary
       python3 score_claims.py --misses   also print every false flag and every escape with context, for reading"""
import json, sys, collections

V2 = "--v2" in sys.argv
items = json.load(open("items_claims_v2.json")) if V2 else json.load(open("items_claims.json")) + json.load(open("items_claims_real.json"))
R = json.load(open("results_claims_v2.json" if V2 else "results_claims.json"))
X = {i["id"]: i for i in items}
def grp(i): return "real" if i["id"].startswith("RM|") else i["L_task"]
def ps(i, r="r0"): return R[i["id"]][r]["p"]["supports"]
def passed(i, r="r0"): return R[i["id"]][r]["choice"] == "supports"
def pct(a, b): return f"{a}/{b} ({100*a/b:.1f}%)" if b else "0/0"

print("=== summary (run 1; run 2 in brackets)")
for g in ("type", "state", "real"):
    right = [i for i in items if grp(i) == g and i["L_true"]]; wrong = [i for i in items if grp(i) == g and not i["L_true"]]
    if not right and not wrong: continue
    if right: print(f"{g:6s} RIGHT passed  {pct(sum(passed(i) for i in right), len(right))}  [{sum(passed(i,'r1') for i in right)}]   false flags {len(right)-sum(passed(i) for i in right)}")
    ca = collections.Counter(R[i["id"]]["r0"]["choice"] for i in wrong)
    print(f"{g:6s} WRONG flagged {pct(sum(not passed(i) for i in wrong), len(wrong))}  [{sum(not passed(i,'r1') for i in wrong)}]   escapes {sum(passed(i) for i in wrong)}   (answers: {dict(ca)})")
flips = sum(R[i["id"]]["r0"]["choice"] != R[i["id"]]["r1"]["choice"] for i in items)
print(f"run-to-run: answer changed on {flips} of {len(items)} items")

print("\n=== wrong claims flagged, by kind of swap (run 1)")
K = collections.defaultdict(lambda: [0, 0])
for i in items:
    if i["L_true"]: continue
    k = i["L_kind"] if grp(i) != "real" else "real: " + i["L_kind"].split()[1]
    K[(grp(i), k)][1] += 1; K[(grp(i), k)][0] += (not passed(i))
for (g, k), (a, b) in sorted(K.items(), key=lambda t: (t[0][0], -t[1][1])): print(f"  {g:6s} {k:34s} {pct(a, b)}")

print("\n=== right claims passed, by label (run 1)")
K = collections.defaultdict(lambda: [0, 0])
for i in items:
    if i["L_true"]: K[(grp(i), i["L_key"])][1] += 1; K[(grp(i), i["L_key"])][0] += passed(i)
for (g, k), (a, b) in sorted(K.items()): print(f"  {g:6s} {k:14s} {pct(a, b)}")

print("\n=== if a claim had to reach P(supports) >= bar to pass (run 1) -- measurement only, no bar is proposed")
print("  bar    | type: right pass / wrong pass | state: right pass / wrong pass | real: wrong pass")
for b in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
    row = []
    for g in ("type", "state"):
        if not [i for i in items if grp(i) == g]: row.append("n/a"); continue
        right = [i for i in items if grp(i) == g and i["L_true"]]; wrong = [i for i in items if grp(i) == g and not i["L_true"]]
        row.append(f"{100*sum(ps(i) >= b for i in right)/len(right):5.1f}% / {100*sum(ps(i) >= b for i in wrong)/len(wrong):5.1f}%")
    real = [i for i in items if grp(i) == "real"]
    print(f"  {b:.2f}   | {row[0]:>22s}        | {row[1]:>22s}         | {100*sum(ps(i) >= b for i in real)/len(real):5.1f}%")

if "--misses" in sys.argv:
    def show(i):
        s = i["state"]; print(f"\n[{i['id']}] {i['L_kind']} | P(supports) {ps(i):.2f} answers r0={R[i['id']]['r0']['choice']} r1={R[i['id']]['r1']['choice']}")
        print("  claim :", s["claim"][:160]); print("  where :", s["where_it_appears"], "| driver:", s["driver_name"])
        print("  before:", s["text_before_quote"][-200:].replace("\n", " ")); print("  QUOTE :", s["quote"][:320].replace("\n", " ")); print("  after :", s["text_after_quote"][:140].replace("\n", " "))
    ONLY = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")), None)   # e.g. --only=state or --only=type,real
    SET = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--set=")), None)                 # e.g. --set=DEV (id contains |DEV-)
    ok = lambda i: (ONLY is None or grp(i) in ONLY) and (SET is None or f"|{SET}" in i["id"])
    print("\n\n######## FALSE FLAGS (right claim, not passed in run 1)")
    for i in items:
        if i["L_true"] and not passed(i) and ok(i): show(i)
    print("\n\n######## ESCAPES (wrong claim passed in run 1)")
    for i in items:
        if not i["L_true"] and passed(i) and ok(i): show(i)
