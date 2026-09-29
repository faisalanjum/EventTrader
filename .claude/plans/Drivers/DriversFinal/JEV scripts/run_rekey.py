import json,sys,collections,time,copy
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('items_final.json')); PRICE=0.042/1e6
def state_for(x,name):
    s=dict(x['state'])
    if name=='V2bN': s.pop('driver_name',None)
    return s
def one(a):
    x,name,rep=a
    return x['id'],name,rep,P.call(state_for(x,name),{"fact_type":VARS[name]()})
jobs=[(x,n,r) for x in items for n,r in (('V0',0),('V2a',0),('V2b',0),('V2b',1),('V4',0),('V4',1),('V2bN',0))]
t=time.time()
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0; tok=collections.Counter()
for i,n,rep,r in R:
    if 'error' in r: err+=1; continue
    tok[n]+=r['usage']['input_tokens']; a=r['answers']['fact_type']
    out[i][f"{n}#{rep}"]=dict(choice=a['choice'],conf=a['confidence'],p=a['probabilities'])
json.dump(out,open('results_rekey.json','w'),indent=1)
print(f"calls {len(jobs)} errors {err} time {time.time()-t:.0f}s tokens {dict(tok)} cost ${sum(tok.values())*PRICE:.3f}")
