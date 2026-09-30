import json,glob,re,random,collections,sys
sys.path.insert(0,'.')
from jevlib import *
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"
RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
srcs={}
def load(src):
    if src not in srcs:
        d=json.load(open(f"{EV}/{src}.json")); srcs[src]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[src]
def mk(setname,i,src,part,quote,name,key,note=""):
    st,parts=load(src); text=parts[part]; m=find_quote(text,quote)
    if not m: return None
    s,e=m
    return dict(set=setname,id=f"{setname}-{i:03d}",src=src,key=key,note=note,state=build_state(text,s,e,st,part,name))
# ---- DEV (same 115 facts as before; key = label, except the 31 disputed items where key = my ruling)
old=json.load(open('fixtures.json')); ver=json.load(open('adjudication_verdicts.json')); idx={d['n']:d['id'] for d in json.load(open('adj_index.json'))}
ruling={idx[int(n)]:v for n,v in ver.items()}
oldn={x['id']:x for x in old}
# need part & name: recover from runs
meta={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): meta.setdefault((d.get('source_id'),it['quote']),(x.get('part_ref'),it.get('driver_name'),x['fact_type']))
dev=[]
for o in old:
    part,name,_=meta[(o['src'],o['quote'])]
    name=re.sub(r"_(guidance|surprise)$","",name)
    r=ruling.get(o['id'])
    key=o['label'] if not r else (r['ruling'] if r['ruling'] else 'unclear')
    if r and r['category']=='label wrong': key=r['ruling']
    x=mk('DEV',o['id'],o['src'],part,o['quote'],name,key,note=(r['category'] if r else 'label'))
    if x: dev.append(x)
print("DEV",len(dev),collections.Counter(x['key'] for x in dev))
# ---- H1 (guidance-source pool, other companies; MY labels made blind before any Jev call)
h1raw=json.load(open('h1_raw.json'))[:40]
H1_UNCLEAR={1:'dividend declaration vs per-share level',13:'past actual + forward expectation in one quote',28:'fixed assumed non-GAAP tax rate: policy vs projection',29:'same as 28',35:'dividend approval vs per-share level'}
h1=[]
for i,o in enumerate(h1raw):
    name=o['gid'].split(':')[2]
    st=build_state(o['text'],o['s'],o['e'],o['src_type'],o['part'],name)
    key='unclear' if i in H1_UNCLEAR else 'guidance'
    h1.append(dict(set='H1',id=f"H1-{i:03d}",src=o['rid'],key=key,note=H1_UNCLEAR.get(i,'blind label by Claude'),state=st))
print("H1",len(h1),collections.Counter(x['key'] for x in h1))
# ---- H2: fresh earlier-model facts not in DEV (no overlapping quote), consistent label, metric/action only
devq=[re.sub(r"\s+"," ",o['quote']) for o in old]
seen=collections.defaultdict(list)
for (src,q),(part,name,t) in meta.items(): pass
allrows=collections.defaultdict(set); info={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): allrows[(d.get('source_id'),it['quote'])].add(x['fact_type']); info[(d.get('source_id'),it['quote'])]=(x.get('part_ref'),it['driver_name'])
cand=[]
for (src,q),ts in sorted(allrows.items()):
    if len(ts)!=1: continue
    t=next(iter(ts))
    if t not in('metric','action_event'): continue
    nq=re.sub(r"\s+"," ",q)
    if any(nq in d or d in nq for d in devq): continue
    cand.append((t,src,q))
random.seed(11); by=collections.defaultdict(list)
for c in cand: by[c[0]].append(c)
h2=[]; n=0
for t,k in (('metric',30),('action_event',30)):
    random.shuffle(by[t])
    for _,src,q in by[t]:
        part,name=info[(src,q)]; x=mk('H2',n,src,part,q,re.sub(r"_(guidance|surprise)$","",name),t,note='earlier-model label')
        if x: h2.append(x); n+=1
        if sum(1 for y in h2 if y['key']==t)>=k: break
print("H2",len(h2),collections.Counter(x['key'] for x in h2))
allf=dev+h1+h2
json.dump(allf,open('fixtures_v3.json','w'),indent=1)
print("total",len(allf))
