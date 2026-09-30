import json,sys,collections
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('items_extra.json'))
def one(a):
    x,n,rep=a; return x['id'],n,rep,P.call(x['state'],{"fact_type":VARS[n]()})
jobs=[(x,n,r) for x in items for n,r in (('V0',0),('V2a',0),('V2b',0),('V4',0),('V4',1))]
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0
for i,n,rep,r in R:
    if 'error' in r: err+=1; continue
    a=r['answers']['fact_type']; out[i][f"{n}#{rep}"]=dict(choice=a['choice'],conf=a['confidence'])
json.dump(out,open('results_extra.json','w'),indent=1); print("calls",len(jobs),"errors",err)
its={x['id']:x for x in items}
print("\nDIVIDEND claims split (key -> answer(conf)):")
for i,x in its.items():
    if x['set']!='DIV': continue
    print(f"  {i:24s} [{x['key'][:4]}] "+"  ".join(f"{v[:-2]}={out[i][v]['choice'][:4]}({out[i][v]['conf']:.2f})" for v in ('V0#0','V2a#0','V2b#0','V4#0','V4#1')))
h6=[i for i,x in its.items() if x['set']=='H6']
print("\nFRESH H6 (40 metric facts, earlier-model labels):")
for v in ('V0#0','V2a#0','V2b#0','V4#0','V4#1'):
    w=[i for i in h6 if out[i][v]['choice']!=its[i]['key']]; print(f"  {v:6s} {len(h6)-len(w)}/{len(h6)}  wrong: {w}")
