import json,collections
items={x['id']:x for x in json.load(open('items_final.json'))}; R=json.load(open('results_rekey.json'))
dec=[i for i,x in items.items() if x['key']!='undecided']
NEW=['H2-024','H5M-037','H1-028','H1-029','H5G-56','H2-039','H2-043','H1-035','H5G-43','H5G-59','H5M-016','H5M-026','H1-013a','H5G-60a','H5G-70b','H5M-004','H5M-027']
rest=[i for i in dec if i not in NEW]
def ok(i,v): return R[i][v]['choice']==items[i]['key']
print(f"decided items {len(dec)}; newly ruled {len(NEW)}; everything else {len(rest)}")
print(f"{'prompt':8s} | newly ruled ({len(NEW)}) | everything else ({len(rest)}) | all decided ({len(dec)})")
for v in ('V0#0','V2a#0','V2b#0','V2b#1','V4#0','V4#1','V2bN#0'):
    a=sum(ok(i,v) for i in NEW); b=sum(ok(i,v) for i in rest); c=a+b
    print(f"{v:8s} | {a:2d}/{len(NEW)} {100*a/len(NEW):5.1f}%      | {b:3d}/{len(rest)} {100*b/len(rest):5.1f}%        | {c:3d}/{len(dec)} {100*c/len(dec):5.1f}%")
for v in ('V2b','V4'):
    d=[i for i in items if R[i][v+'#0']['choice']!=R[i][v+'#1']['choice']]; print(f"stability {v}: two identical runs differ on {len(d)}: {d}")
print("\nnewly ruled items — answer(conf) per prompt:  [key]")
for i in NEW:
    print(f"  {i:8s} [{items[i]['key'][:4]}] "+"  ".join(f"{v[:-2]}={R[i][v]['choice'][:4]}({R[i][v]['conf']:.2f})" for v in ('V0#0','V2a#0','V2b#0','V4#0','V2bN#0'))+f"   | {items[i]['note'][:60]}")
print("\nundecided claims (no key):",[(i,R[i]['V2b#0']['choice'][:4],round(R[i]['V2b#0']['conf'],2),R[i]['V4#0']['choice'][:4],round(R[i]['V4#0']['conf'],2)) for i in items if items[i]['key']=='undecided'])
# name dependence: V2b (name in state) vs V2bN (name hidden)
diff=[i for i in items if R[i]['V2b#0']['choice']!=R[i]['V2bN#0']['choice']]
print(f"\nname dependence: hiding the driver name changes {len(diff)} of {len(items)} answers")
for i in diff: print(f"  {i:9s} key={items[i]['key'][:4]} with name={R[i]['V2b#0']['choice'][:4]}({R[i]['V2b#0']['conf']:.2f})  without={R[i]['V2bN#0']['choice'][:4]}({R[i]['V2bN#0']['conf']:.2f})  driver={items[i]['state']['driver_name']!r}")
# regressions / gains V4 vs V2b on all decided
fx=[i for i in dec if not ok(i,'V2b#0') and ok(i,'V4#0')]; br=[i for i in dec if ok(i,'V2b#0') and not ok(i,'V4#0')]
print("\nV4 vs V2b: fixed",fx,"| broken",br)
print("V4 errors:",[(i,R[i]['V4#0']['choice'][:4],round(R[i]['V4#0']['conf'],2)) for i in dec if not ok(i,'V4#0')])
print("V2b errors:",[(i,R[i]['V2b#0']['choice'][:4],round(R[i]['V2b#0']['conf'],2)) for i in dec if not ok(i,'V2b#0')])
