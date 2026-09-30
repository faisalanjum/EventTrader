import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('items_final.json'))+json.load(open('items_extra.json'))
def one(a):
    x,n,rep=a; return x['id'],n,rep,P.call(x['state'],{"fact_type":VARS[n]()})
jobs=[(x,'V5',r) for x in items for r in (0,1)]
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0; tok=0
for i,n,rep,r in R:
    if 'error' in r: err+=1; continue
    tok+=r['usage']['input_tokens']; a=r['answers']['fact_type']; out[i][f"{n}#{rep}"]=dict(choice=a['choice'],conf=a['confidence'])
json.dump(out,open('results_v5.json','w'),indent=1); print("calls",len(jobs),"errors",err,"tokens",tok,"cost $%.3f"%(tok*0.042/1e6))
