import json,collections
items={x['id']:x for x in json.load(open('redo_items.json'))}; R=json.load(open('results_redo.json'))
redo=[i for i,x in items.items() if x['group']]; rest=[i for i in items if i not in set(redo)]
def acc(ids,v): 
    ok=sum(R[i][v]['choice']==items[i]['key'] for i in ids); return ok,len(ids)
print(f"{'variant':8s} | redo set (31 claims) | everything else ({len(rest)}) | ALL ({len(items)})")
for v in ('V0#0','V1#0','V2a#0','V2b#0','V2a#1','V2b#1'):
    a=acc(redo,v);b=acc(rest,v);c=acc(list(items),v)
    print(f"{v:8s} | {a[0]:2d}/{a[1]}  {100*a[0]/a[1]:5.1f}%       | {b[0]:3d}/{b[1]}  {100*b[0]/b[1]:5.1f}%      | {c[0]:3d}/{c[1]}  {100*c[0]/c[1]:5.1f}%")
# stability: same variant, second run
for v in ('V2a','V2b'):
    diff=[i for i in items if R[i][v+'#0']['choice']!=R[i][v+'#1']['choice']]
    mx=max(abs(R[i][v+'#0']['conf']-R[i][v+'#1']['conf']) for i in items)
    print(f"stability {v}: answers differing between two identical runs: {len(diff)}/{len(items)}; max confidence change {mx:.3f}")
print("\nby group (redo set) — correct/total:")
gs=sorted({items[i]['group'] for i in redo})
print(f"{'group':6s}"+"".join(f"{v:>8s}" for v in ('V0','V1','V2a','V2b')))
for g in gs:
    ids=[i for i in redo if items[i]['group']==g]
    print(f"{g:6s}"+"".join(f"{sum(R[i][v+'#0']['choice']==items[i]['key'] for i in ids):>5d}/{len(ids)}" for v in ('V0','V1','V2a','V2b')))
print("\nmixed-claim detector (probability of 'two claims'):")
mixed=[(R[i]['QM#0']['mixed'],i) for i in items]; mixed.sort(reverse=True)
for p,i in mixed[:12]: print(f"  {p:.2f} {i:9s} {items[i]['state']['quote'][:110]!r}")
print("  count >=0.5:",sum(p>=0.5 for p,_ in mixed),"of",len(mixed))
