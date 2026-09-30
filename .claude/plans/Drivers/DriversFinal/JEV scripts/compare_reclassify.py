"""Comparator (JEV.md §6.5): instead of asking "does the quote support this label?", re-classify the fact with the V6 fact-type prompt and
flag the claim when V6's answer differs from the claimed type. No new Jev calls: uses results_real_reader.json (V6 and QC4 answers on every
decided fact, one run) and the v2 claim-checker results. DEV is left out of the fair comparison because V6 was tuned on it."""
import json, collections
A = json.load(open("items_claims_v2.json")); R2 = json.load(open("results_claims_v2.json")); RR = json.load(open("results_real_reader.json"))
def base(i): return i["id"].split("|")[1]
def isdev(i): return base(i).startswith("DEV-")
def v6(i): return RR[base(i)]["V6"]["choice"]
def flag_claim(i): return R2[i["id"]]["r0"]["choice"] != "supports"
def flag_reclass(i): return v6(i) != i["L_claimed"]
def pct(a, n): return f"{a:3d}/{n:3d} ({100*a/n:5.1f}%)"
for name, sel in (("fresh sets (not DEV)", lambda i: not isdev(i)), ("DEV (V6 tuned here, optimistic)", isdev)):
    right = [i for i in A if i["id"].startswith("FT|") and i["L_true"] and sel(i)]
    wrong = [i for i in A if i["id"].startswith("FT|") and not i["L_true"] and sel(i)]
    print(f"== {name}")
    print(f"   planted wrong labels flagged:   claim checker v2 {pct(sum(map(flag_claim, wrong)), len(wrong))}   re-classify {pct(sum(map(flag_reclass, wrong)), len(wrong))}")
    print(f"   right labels wrongly flagged:   claim checker v2 {pct(sum(map(flag_claim, right)), len(right))}   re-classify {pct(sum(map(flag_reclass, right)), len(right))}")
real = [i for i in A if i["id"].startswith("RM|")]
print("== real mistakes (32; made by QC4 and/or V6)")
for tag in ("QC4", "V6", "QC4+V6"):
    rows = [i for i in real if i["L_kind"].endswith("[" + tag + "]")]
    print(f"   [{tag}]   n={len(rows):2d}  claim checker v2 flags {sum(map(flag_claim, rows))}   re-classify with V6 flags {sum(map(flag_reclass, rows))}")
