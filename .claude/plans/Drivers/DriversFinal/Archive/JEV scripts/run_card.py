import json,sys,collections,time
sys.path.insert(0,'.')
import prompts_v3 as P
from card_prompts import STATE,UNIT_LEVEL,UNIT_CHANGE,TIMETYPE
from concurrent.futures import ThreadPoolExecutor
items=json.load(open('card_items.json'))
MSTATES={'increased','decreased','mixed','unchanged','persists','reported','unknown'}
UNITS={'usd','m_usd','percent','percent_yoy','percent_sequential','percent_points','basis_points','count','x','unknown'}
T={'state':(STATE,lambda x:x['fact_type']=='metric' and x['L_state'] in MSTATES,'state'),
   'unit_level':(UNIT_LEVEL,lambda x:x['L_lvl'] in UNITS,'lvl'),
   'unit_change':(UNIT_CHANGE,lambda x:x['L_chg'] in UNITS,'chg'),
   'time_type':(TIMETYPE,lambda x:x['L_tt'] in ('duration','instant'),'tt')}
jobs=[(x,t,r) for t,(qs,sel,_) in T.items() for x in items if sel(x) for r in (0,1)]
print({t:sum(1 for x in items if sel(x)) for t,(qs,sel,_) in T.items()},"jobs",len(jobs))
def one(a):
    x,t,r=a; assert isinstance(x['state'],dict) and 'quote' in x['state']; return x['id'],f"{t}#{r}",P.call(x['state'],T[t][0])
t0=time.time()
with ThreadPoolExecutor(8) as ex: R=list(ex.map(one,jobs))
out=collections.defaultdict(dict); err=0; tok=0
for i,k,r in R:
    if 'error' in r: err+=1; continue
    tok+=r['usage']['input_tokens']; a=list(r['answers'].values())[0]
    out[i][k]=dict(choice=a['choice'],conf=a['confidence'],p=a['probabilities'])
json.dump(out,open('results_card.json','w'),indent=1)
print(f"errors {err} time {time.time()-t0:.0f}s tokens {tok} cost ${tok*0.042/1e6:.3f}")
