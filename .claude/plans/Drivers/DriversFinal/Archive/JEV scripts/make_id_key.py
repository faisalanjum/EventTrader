"""Merge the two independent labelings into the frozen key (JEV.md §6.8b): keep a pair only when Claude and the Sonnet helper gave the same S or D; everything else is dropped and listed.
Usage: python3 make_id_key.py  (reads id_labels_claude.json, id_labels_sonnet.json; writes id_key.json)"""
import json, hashlib, collections
A = json.load(open("id_labels_claude.json"))["labels"]; Sn = json.load(open("id_labels_sonnet.json")); G = json.load(open("id_pairs_groups.json"))
S = {k: v["label"] for k, v in Sn.items()}; assert set(S) == set(A) and len(A) == 66
keep = {i: A[i] for i in A if A[i] in "SD" and A[i] == S[i]}
drop = {i: (A[i], S[i]) for i in A if i not in keep}
print("agreement on all 66:", sum(A[i] == S[i] for i in A), "| kept", len(keep), collections.Counter(keep.values()), "| dropped", len(drop))
print("kept by pair group:", collections.Counter((G[i]["group"], keep[i]) for i in keep))
for i, (a, s) in sorted(drop.items()): print(f"  dropped {i} ({G[i]['group']}): Claude={a} Sonnet={s} | {Sn[i]['why']}")
blob = json.dumps(keep, sort_keys=True); h = hashlib.sha256(blob.encode()).hexdigest()[:16]
json.dump({"hash": h, "rule": "kept only pairs where Claude and the Sonnet helper independently gave the same S or D", "labels": keep}, open("id_key.json", "w"), indent=1); print("key hash", h)
