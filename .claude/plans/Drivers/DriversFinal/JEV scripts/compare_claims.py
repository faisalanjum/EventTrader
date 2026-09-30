"""v1 vs v2 claim wording on the fact-type items (JEV.md §6.5). DEV = the set whose v1 misses I read to write v2 (so v2 is tuned on it);
every other set is a fresh check for v2. Usage: python3 compare_claims.py"""
import json, collections
A = json.load(open("items_claims.json")) + json.load(open("items_claims_real.json"))
R1 = json.load(open("results_claims.json")); R2 = json.load(open("results_claims_v2.json"))
T = [i for i in A if i["L_task"] == "type"]
def part(i): return "real" if i["id"].startswith("RM|") else ("DEV(tuned)" if "|DEV-" in i["id"] else "fresh")
def sup(R, i, r="r0"): return R[i["id"]][r]["choice"] == "supports"
def line(name, rows):
    n = len(rows)
    if not n: return
    c1 = sum(not sup(R1, i) for i in rows); c2 = sum(not sup(R2, i) for i in rows)
    print(f"  {name:30s} n={n:3d}  v1 flagged {c1:3d} ({100*c1/n:5.1f}%)   v2 flagged {c2:3d} ({100*c2/n:5.1f}%)")
for p in ("DEV(tuned)", "fresh", "real"):
    print(f"== WRONG claims, {p}"); W = [i for i in T if not i["L_true"] and part(i) == p]
    line("all", W)
    if p != "real":
        for k in sorted({i["L_kind"] for i in W}): line(k, [i for i in W if i["L_kind"] == k])
print("== RIGHT claims (should pass)")
for p in ("DEV(tuned)", "fresh"):
    Rr = [i for i in T if i["L_true"] and part(i) == p]; n = len(Rr)
    print(f"  {p:12s} n={n}  v1 passed {sum(sup(R1,i) for i in Rr)}   v2 passed {sum(sup(R2,i) for i in Rr)}")
print("== fresh sets, wrong claims flagged by set (v1 -> v2)")
by = collections.defaultdict(list)
for i in T:
    if not i["L_true"] and part(i) == "fresh": by[i["id"].split("|")[1].split("-")[0]].append(i)
for s, rows in sorted(by.items()): print(f"  {s:4s} n={len(rows):3d}  v1 {sum(not sup(R1,i) for i in rows):3d}  v2 {sum(not sup(R2,i) for i in rows):3d}")
