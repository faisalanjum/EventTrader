import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from more_prompts import BASELINE,HORIZON,SLICE
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('items_more.json')); Q={'baseline':BASELINE,'horizon':HORIZON,'slice':SLICE}
jobs=[(x,r) for x in items for r in (0,1)]
def one(a):
    x,r=a; assert isinstance(x['state'],dict) and 'quote' in x['state']; return x['id'],r,P.call(x['state'],Q[x['task']])
t0=time.time()
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0; tok=0
for i,r,res in R:
    if 'error' in res: err+=1; continue
    tok+=res['usage']['input_tokens']; a=list(res['answers'].values())[0]; out[i][f"r{r}"]=dict(choice=a['choice'],conf=a['confidence'])
json.dump(out,open('results_more.json','w'),indent=1); print(f"calls {len(jobs)} errors {err} time {time.time()-t0:.0f}s tokens {tok} cost ${tok*0.042/1e6:.3f}")
