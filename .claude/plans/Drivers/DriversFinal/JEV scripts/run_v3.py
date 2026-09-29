import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from variants import VARS
from concurrent.futures import ThreadPoolExecutor
old=json.load(open('redo_items.json')); h5=json.load(open('fixtures_h5.json')); PRICE=0.042/1e6
tok=collections.Counter()
def one(a):
    x,name,rep=a
    r=P.call(x['state'],{"fact_type":VARS[name]()}); return x['id'],name,rep,r
jobs=[(x,n,0) for x in h5 for n in ('V0','V2a','V2b','V3')]+[(x,n,1) for x in h5 for n in ('V2b','V3')]
jobs+=[(x,'V3',0) for x in old]+[(x,'V3',1) for x in old]
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0
for i,n,rep,r in R:
    if 'error' in r: err+=1; continue
    tok[n]+=r['usage']['input_tokens']; a=r['answers']['fact_type']
    out[i][f"{n}#{rep}"]=dict(choice=a['choice'],conf=a['confidence'],p=a['probabilities'])
json.dump(out,open('results_v3run.json','w'),indent=1)
print(f"calls {len(jobs)} errors {err} input tokens {dict(tok)} cost ${sum(tok.values())*PRICE:.3f}")
