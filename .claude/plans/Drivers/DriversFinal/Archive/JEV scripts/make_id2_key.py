"""Big identity test, stage C (JEV.md §6.8c): merge two independent Sonnet labelings (A = original side order, B = sides swapped and order reversed) into the frozen key.
Keep a pair only when both gave the same S or D. The difference kind used for strata is labeler A's. Usage: python3 make_id2_key.py"""
import json, glob, hashlib, collections
D = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
def load(tag):
    out = {}
    for f in sorted(glob.glob(f"{D}/id2_labels_{tag}_*.json")):
        for r in json.load(open(f)): out[r["id"]] = r
    return out
A, B = load("A"), load("B"); G = json.load(open("id2_pairs_groups.json")); ids = sorted(G)
print("labeled:", len(A), len(B), "of", len(ids), "| missing A", [i for i in ids if i not in A][:5], "missing B", [i for i in ids if i not in B][:5])
both = [i for i in ids if i in A and i in B]
agree = [i for i in both if A[i]["label"] == B[i]["label"]]
print("agree on label", len(agree), "of", len(both), "| A labels", collections.Counter(A[i]["label"] for i in both), "| B labels", collections.Counter(B[i]["label"] for i in both))
keep = {i: A[i]["label"] for i in agree if A[i]["label"] in ("S", "D")}
kind = {i: (A[i]["kind"] if A[i]["label"] == "D" else "same") for i in keep}
print("kept", len(keep), collections.Counter(keep.values()), "| unresolved", len(both) - len(keep), "(a U from either labeler, or S vs D)")
print("D kinds (labeler A):", collections.Counter(kind[i] for i in keep if keep[i] == "D"))
print("kept by stratum:", collections.Counter((G[i]["stratum"].split("/")[0], keep[i]) for i in keep))
sd = [i for i in both if {A[i]["label"], B[i]["label"]} == {"S", "D"}]
print("hard S-vs-D conflicts:", len(sd))
blob = json.dumps(keep, sort_keys=True); h = hashlib.sha256(blob.encode()).hexdigest()[:16]
json.dump({"hash": h, "rule": "kept only pairs where two independent Sonnet labelers (A original order, B sides swapped) gave the same S or D", "labels": keep, "kind": kind,
           "unresolved": {i: [A[i]["label"], B[i]["label"], A[i]["why"], B[i]["why"]] for i in both if i not in keep}}, open("id2_key.json", "w"), indent=1)
print("key hash", h)
