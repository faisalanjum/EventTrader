import json,collections
A=json.load(open('ablate_results.json')); keys=A['items']; R=A['R']
ids=list(keys)
V2B=json.load(open('results_redo.json')); H5=json.load(open('results_v3run.json'))
def base(i,v):
    r=V2B.get(i,{}).get(v) or H5.get(i,{}).get(v); return r['choice'] if r else None
print(f"{'prompt':32s} correct/350   changes vs V2b (fixed | broken)")
def wrong_v2b(i): return base(i,'V2b#0')!=keys[i]
print(f"{'V2b (all clauses)':32s} {sum(not wrong_v2b(i) for i in ids)}/{len(ids)}")
for n in next(iter(R.values())):
    ok=sum(R[i][n]['choice']==keys[i] for i in ids)
    fixed=[i for i in ids if wrong_v2b(i) and R[i][n]['choice']==keys[i]]
    broke=[i for i in ids if not wrong_v2b(i) and R[i][n]['choice']!=keys[i]]
    print(f"{'V2b minus '+n:32s} {ok}/{len(ids)}    fixed {len(fixed)} {fixed} | broken {len(broke)} {broke}")
# V0 baseline on the same keys (V0 exists for redo items and H5)
v0=[i for i in ids if base(i,'V0#0')]
print("\nV0 (last round's prompt) on the same items:",sum(base(i,'V0#0')==keys[i] for i in v0),"/",len(v0))
