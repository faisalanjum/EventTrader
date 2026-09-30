import json,glob,re,random,collections,sys
sys.path.insert(0,'.')
from jevlib import *
import prompts_v3 as P
from concurrent.futures import ThreadPoolExecutor
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
fx=json.load(open('fixtures_v3.json')); used=[re.sub(r"\s+"," ",f['state']['quote']) for f in fx]
allrows=collections.defaultdict(set); info={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): allrows[(d.get('source_id'),it['quote'])].add(x['fact_type']); info[(d.get('source_id'),it['quote'])]=(x.get('part_ref'),it['driver_name'])
by=collections.defaultdict(list)
for (src,q),ts in sorted(allrows.items()):
    if len(ts)!=1: continue
    t=next(iter(ts)); nq=re.sub(r"\s+"," ",q)
    if t in('metric','action_event') and not any(nq in u or u in nq for u in used): by[t].append((src,q))
print({k:len(v) for k,v in by.items()})
random.seed(23); srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
h3=[];n=0
for t,k in (('metric',30),('action_event',30)):
    random.shuffle(by[t]); c=0
    for src,q in by[t]:
        part,name=info[(src,q)]; st,parts=load(src); m=find_quote(parts[part],q)
        if not m: continue
        h3.append(dict(set='H3',id=f"H3-{n:03d}",src=src,key=t,note='earlier-model label',state=build_state(parts[part],m[0],m[1],st,part,re.sub(r"_(guidance|surprise)$","",name)))); n+=1; c+=1
        if c>=k: break
print("H3",len(h3),collections.Counter(x['key'] for x in h3))
json.dump(h3,open('fixtures_h3.json','w'),indent=1)
def two(f): return P.call(f['state'],P.QC),P.call(f['state'],P.QD)
with ThreadPoolExecutor(8) as ex: R=list(ex.map(two,h3))
out=[]
for f,(a,b) in zip(h3,R):
    if 'error' in a or 'error' in b: continue
    ans=a['answers']['fact_type']; pb=P.compose_d(b['answers'])
    out.append(dict(id=f['id'],set='H3',key=f['key'],note=f['note'],quote=f['state']['quote'],name=f['state']['driver_name'],one=ans['choice'],one_conf=ans['confidence'],one_p=ans['probabilities'],steps=pb[0],steps_unc=pb[1],steps_raw={k:round(v['noul'],3) for k,v in b['answers'].items()}))
json.dump(out,open('results_h3.json','w'),indent=1)
for p in ('one','steps'):
    for t in ('metric','action_event'):
        s=[r for r in out if r['key']==t]; print(p,t,sum(r[p]==t for r in s),'/',len(s),' picked instead:',dict(collections.Counter(r[p] for r in s if r[p]!=t)))
