import json,collections
old={x['id']:x for x in json.load(open('redo_items.json'))}; h5={x['id']:x for x in json.load(open('fixtures_h5.json'))}
R3=json.load(open('results_v3run.json')); R2=json.load(open('results_redo.json'))
DISPUTED={'H1-013a','H1-035','H2-024','H2-039','H2-043'}
print("=== FRESH SET H5 (untouched by any tuning; guidance pool labeled by Claude before any Jev call)")
dec=[i for i,x in h5.items() if x['key']!='unclear']
print(f"decided {len(dec)} (4 unclear set aside) | guidance {sum(1 for i in dec if h5[i]['key']=='guidance')} metric {sum(1 for i in dec if h5[i]['key']=='metric')}")
for v in ('V0#0','V2a#0','V2b#0','V2b#1','V3#0','V3#1'):
    if v not in R3[dec[0]]: continue
    wrong=[i for i in dec if R3[i][v]['choice']!=h5[i]['key']]
    print(f"  {v:6s} {len(dec)-len(wrong)}/{len(dec)} = {100*(len(dec)-len(wrong))/len(dec):5.1f}%  wrong: {wrong}")
print("\n=== ALL 288 earlier items, V3 vs V2b (5 disputed set aside)")
ids=[i for i in old if i not in DISPUTED]
def res(i,v): return (R3[i][v] if v.startswith('V3') and v in R3.get(i,{}) else R2[i].get(v))['choice']
for v in ('V2b#0','V3#0','V3#1'):
    wrong=[i for i in ids if res(i,v)!=old[i]['key']]
    print(f"  {v}: {len(ids)-len(wrong)}/{len(ids)} = {100*(len(ids)-len(wrong))/len(ids):.1f}%  wrong: {wrong}")
d=[i for i in old if R3[i]['V3#0']['choice']!=R3[i]['V3#1']['choice']]; print("  V3 two identical runs differ on:",d)
print("\ndisputed items under V3:")
for i in sorted(DISPUTED): print(f"  {i}: key(advice/inferred)={old[i]['key']}  V3={R3[i]['V3#0']['choice']}({R3[i]['V3#0']['conf']:.2f})  V2b={R2[i]['V2b#0']['choice']}({R2[i]['V2b#0']['conf']:.2f})")
json.dump({i:dict(h5[i],R=R3[i]) for i in h5},open('h5_results.json','w'))
