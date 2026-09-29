import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS
from surprise_prompts import S2,S3
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('surprise_items.json'))
def call_one(a):
    x,task,rep=a
    if task in ('V0','V6'): qs={"fact_type":VARS[task]()}
    elif task=='S2': qs=S2
    else: qs=S3
    return x['id'],f"{task}#{rep}",P.call(x['state'],qs)
jobs=[(x,t,r) for x in items for t,r in (('V0',0),('V6',0),('V6',1),('S2',0))]
jobs+=[(x,'S3',0) for x in items if x['key']=='surprise']
t0=time.time()
with ThreadPoolExecutor(8) as ex: R=list(ex.map(call_one,jobs))
out=collections.defaultdict(dict); err=0; tok=0
for i,k,r in R:
    if 'error' in r: err+=1; continue
    tok+=r['usage']['input_tokens']; a=list(r['answers'].values())[0]
    out[i][k]=dict(choice=a['choice'],conf=a['confidence'],p=a['probabilities'])
json.dump(out,open('results_surprise.json','w'),indent=1)
print(f"calls {len(jobs)} errors {err} time {time.time()-t0:.0f}s tokens {tok} cost ${tok*0.042/1e6:.3f}")
