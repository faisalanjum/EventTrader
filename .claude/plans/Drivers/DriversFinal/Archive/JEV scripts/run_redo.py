import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS,QM
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('redo_items.json')); PRICE=0.042/1e6
tok=collections.Counter()
def one(args):
    x,name,rep=args
    qs=QM if name=='QM' else {"fact_type":VARS[name]()}
    r=P.call(x['state'],qs)
    return (x['id'],name,rep,r)
jobs=[(x,n,0) for x in items for n in ('V0','V1','V2a','V2b','QM')]+[(x,n,1) for x in items for n in ('V2a','V2b')]
t=time.time()
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0
for i,n,rep,r in R:
    if 'error' in r: err+=1; continue
    tok[n]+=r['usage']['input_tokens']
    a=r['answers']
    out[i][f"{n}#{rep}"]=(dict(choice=a['fact_type']['choice'],conf=a['fact_type']['confidence'],p=a['fact_type']['probabilities']) if n!='QM' else dict(mixed=a['mixed_claims']['noul']))
json.dump(out,open('results_redo.json','w'),indent=1)
print(f"calls {len(jobs)} errors {err} time {time.time()-t:.0f}s  input tokens {dict(tok)}  cost ${sum(tok.values())*PRICE:.3f}")
