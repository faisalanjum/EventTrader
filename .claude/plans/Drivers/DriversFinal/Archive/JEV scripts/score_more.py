import json,collections
items={x['id']:x for x in json.load(open('items_more.json'))}; R=json.load(open('results_more.json'))
for t in ('baseline','horizon','slice'):
    I=[i for i,x in items.items() if x['task']==t]
    ok=lambda r,S=I: sum(R[i][r]['choice']==items[i]['L_key'] for i in S)
    d=[i for i in I if R[i]['r0']['choice']!=R[i]['r1']['choice']]
    print(f"\n=== {t}: n={len(I)} run1 {ok('r0')} ({100*ok('r0')/len(I):.1f}%) run2 {ok('r1')} ({100*ok('r1')/len(I):.1f}%) | two identical runs differ on {len(d)}")
    for lab in sorted({items[i]['L_key'] for i in I}):
        S=[i for i in I if items[i]['L_key']==lab]; w=collections.Counter(R[i]['r0']['choice'] for i in S if R[i]['r0']['choice']!=lab)
        print(f"   {lab:19s} {sum(R[i]['r0']['choice']==lab for i in S)}/{len(S)}  picked instead: {dict(w)}")
    wrong=[i for i in I if R[i]['r0']['choice']!=items[i]['L_key']]
    for c in (0.6,0.8,0.9):
        fl=[i for i in I if R[i]['r0']['conf']<c]; print(f"   conf<{c}: flags {len(fl)}/{len(I)} ({100*len(fl)/len(I):.0f}%), catches {sum(1 for i in fl if i in wrong)}/{len(wrong)} misses")
json.dump({t:[i for i,x in items.items() if x['task']==t and R[i]['r0']['choice']!=x['L_key']] for t in ('baseline','horizon','slice')},open('more_misses.json','w'))
print({t:len(v) for t,v in json.load(open('more_misses.json')).items()})
