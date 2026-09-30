import json,collections
fin={x['id']:x for x in json.load(open('items_final.json'))}; ext={x['id']:x for x in json.load(open('items_extra.json'))}
RA=json.load(open('results_rekey.json')); RE=json.load(open('results_extra.json')); R5=json.load(open('results_v5.json'))
def res(i,v):
    for R in (RA,RE,R5):
        if i in R and v in R[i]: return R[i][v]
items={**fin,**ext}
NEW=['H2-024','H5M-037','H1-028','H1-029','H5G-56','H2-039','H2-043','H1-035','H5G-43','H5G-59','H5M-016','H5M-026','H1-013a','H5G-60a','H5G-70b','H5M-004','H5M-027']
UND={'H5G-60b','H5G-70a','H6-033'}                                   # no key
def ok(i,v): return res(i,v)['choice']==items[i]['key']
groups={'earlier 363 decided':[i for i in fin if fin[i]['key']!='undecided'],
        '  of which newly ruled (17)':NEW,
        '  of which everything else (346)':[i for i in fin if fin[i]['key']!='undecided' and i not in NEW],
        'fresh H6 (39; 1 undecided set aside)':[i for i in ext if ext[i]['set']=='H6' and i not in UND],
        'dividend split claims (8)':[i for i in ext if ext[i]['set']=='DIV']}
print(f"{'':40s}"+"".join(f"{v:>10s}" for v in ('V0#0','V2a#0','V2b#0','V4#0','V4#1','V5#0','V5#1')))
for g,ids in groups.items():
    print(f"{g:40s}"+"".join(f"{sum(ok(i,v) for i in ids):>6d}/{len(ids):<3d}" if res(ids[0],v) else f"{'-':>10s}" for v in ('V0#0','V2a#0','V2b#0','V4#0','V4#1','V5#0','V5#1')))
allid=groups['earlier 363 decided']+groups['fresh H6 (39; 1 undecided set aside)']+groups['dividend split claims (8)']
print(f"{'ALL decided ('+str(len(allid))+')':40s}"+"".join(f"{sum(ok(i,v) for i in allid):>6d}/{len(allid):<3d}" for v in ('V0#0','V2a#0','V2b#0','V4#0','V5#0','V5#1')[:0]) )
for v in ('V0#0','V2a#0','V2b#0','V4#0','V5#0','V5#1'):
    print(f"  {v}: {sum(ok(i,v) for i in allid)}/{len(allid)} = {100*sum(ok(i,v) for i in allid)/len(allid):.1f}%")
d=[i for i in list(fin)+list(ext) if res(i,'V5#0')['choice']!=res(i,'V5#1')['choice']]; print("V5 two identical runs differ on:",d)
fx=[i for i in allid if not ok(i,'V4#0') and ok(i,'V5#0')]; br=[i for i in allid if ok(i,'V4#0') and not ok(i,'V5#0')]
print("V5 vs V4: fixed",fx,"| broken",br)
print("\nV5 errors (id key answer conf):")
for i in allid:
    if not ok(i,'V5#0'): print(f"  {i:22s} key={items[i]['key'][:4]} V5={res(i,'V5#0')['choice'][:4]}({res(i,'V5#0')['conf']:.2f}) V4={res(i,'V4#0')['choice'][:4]}({res(i,'V4#0')['conf']:.2f})  {items[i]['state']['quote'][:70]!r}")
wrong=[(i,res(i,'V5#0')['conf']) for i in allid if not ok(i,'V5#0')]
for t in (0.6,0.75,0.9):
    fl=[i for i in allid if res(i,'V5#0')['conf']<t]; c=sum(1 for i in fl if not ok(i,'V5#0'))
    print(f"  V5 conf<{t}: flags {len(fl)}/{len(allid)} ({100*len(fl)/len(allid):.0f}%), errors caught {c}/{len(wrong)}")
