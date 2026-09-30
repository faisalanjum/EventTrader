import json,re,sys,collections,os
sys.path.insert(0,'.')
from concurrent.futures import ThreadPoolExecutor
import prompts_v3 as P, old_prompts as O
OUT=os.path.dirname(os.path.abspath(__file__)); PRICE=0.042/1e6
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"
fx=json.load(open('fixtures_v3.json')); oldfx={x['id']:x for x in json.load(open('fixtures.json'))}
# old-style input (flattened, 400 chars before, no text after) for the DEV control
norm=lambda t:re.sub(r"\s+"," ",t); _c={}
def old_state(f):
    o=oldfx[int(f['id'].split('-')[1])]
    if o['src'] not in _c: _c[o['src']]=norm(" ".join(p['content'] for p in json.load(open(f"{EV}/{o['src']}.json"))['text_parts']))
    T=_c[o['src']]; q=norm(o['quote']); i=T.find(q)
    if i<0: i=T.find(q[:60])
    return dict(quote=o['quote'],section=o['section'],driver_name=o['name'],text_just_before_quote=T[max(0,i-400):i].strip())
def as_new_fields(s): return dict(where_it_appears=s['section'],driver_name=s['driver_name'],text_before_quote=s['text_just_before_quote'],quote=s['quote'],text_after_quote="")
def run(name,items,qs_a,qs_b,comp_b,state_fn):
    def two(f):
        st=state_fn(f); return P.call(st,qs_a),P.call(st,qs_b)
    with ThreadPoolExecutor(8) as ex: R=list(ex.map(two,items))
    out=[];tok=0;err=0
    for f,(a,b) in zip(items,R):
        if 'error' in a or 'error' in b: err+=1; continue
        tok+=a['usage']['input_tokens']+b['usage']['input_tokens']
        ans=a['answers']['fact_type']; pb=comp_b(b['answers'])
        out.append(dict(id=f['id'],set=f['set'],key=f['key'],note=f['note'],quote=f['state']['quote'],name=f['state']['driver_name'],
             one=ans['choice'],one_conf=ans['confidence'],one_p=ans['probabilities'],
             steps=pb[0] if isinstance(pb,tuple) else pb,steps_unc=pb[1] if isinstance(pb,tuple) else False,
             steps_raw={k:(round(v['noul'],3) if 'noul' in v else v['choice']) for k,v in b['answers'].items()}))
    print(f"{name}: scored {len(out)} errors {err} input tokens {tok} cost ${tok*PRICE:.4f}"); return out
dev=[f for f in fx if f['set']=='DEV']
EXP={}
EXP['new_prompts_new_input']=run('new prompts + new input (ALL sets)',fx,P.QC,P.QD,P.compose_d,lambda f:f['state'])
EXP['old_prompts_new_input']=run('old prompts + new input (DEV)',dev,O.QA,O.QB,O.compose_b,lambda f:f['state'])
EXP['new_prompts_old_input']=run('new prompts + old input (DEV)',dev,P.QC,P.QD,P.compose_d,lambda f:as_new_fields(old_state(f)))
json.dump(EXP,open('results_all.json','w'),indent=1)
