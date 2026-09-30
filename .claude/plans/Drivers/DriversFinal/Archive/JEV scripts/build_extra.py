import json,glob,re,random,collections,sys
sys.path.insert(0,'.')
from jevlib import *
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
h1=json.load(open('h1_raw.json')); X=[]
# ---- dividend declarations split into two claims (amount -> per-share driver, metric; decision -> dividend driver, action_event)
def ws(s): return r"\s+".join(re.escape(w) for w in s.split())
DIV={1:("a regular quarterly cash dividend of $0.18 per share of CMC common stock", r"cash\s+dividend"),
     35:("a quarterly cash dividend of $0.27 per share", r"cash\s+dividend"),
     43:("a regular quarterly cash dividend of $0.16 per share of CMC common stock", r"cash\s+dividend"),
     59:("a quarterly dividend of $0.18 per share of CMC common stock", r"quarterly\s+dividend")}
for idx,(amt,endpat) in DIV.items():
    o=h1[idx]; q=o['text'][o['s']:o['e']]
    m=re.search(ws(amt),q); assert m,(idx,'amount')
    e=re.search(endpat,q); assert e,(idx,'decision')
    tag=f"H1-{idx:03d}" if idx<40 else f"H5G-{idx}"
    a=(o['s']+m.start(),o['s']+m.end()); b=(o['s'],o['s']+e.end())
    X.append(dict(id=f"DIV-{tag}-amount",set='DIV',key='metric',note='amount claim under the per-share driver',state=build_state(o['text'],a[0],a[1],o['src_type'],o['part'],'dividend per share')))
    X.append(dict(id=f"DIV-{tag}-decision",set='DIV',key='action_event',note='declaring decision under the dividend driver',state=build_state(o['text'],b[0],b[1],o['src_type'],o['part'],'dividend')))
# ---- H6M: 40 more unused earlier-model metric facts (fresh; nothing tuned on them)
used=[re.sub(r"\s+"," ",x['state']['quote']) for f in ('items_final.json','fixtures_h5.json','fixtures_v3.json','fixtures_h3.json','fixtures_h4.json') for x in json.load(open(f))]
allrows=collections.defaultdict(set); info={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): allrows[(d.get('source_id'),it['quote'])].add(x['fact_type']); info[(d.get('source_id'),it['quote'])]=(x.get('part_ref'),it['driver_name'])
pool=[(s,q) for (s,q),ts in sorted(allrows.items()) if len(ts)==1 and next(iter(ts)) in('metric','action_event') and not any(re.sub(r"\s+"," ",q) in u or u in re.sub(r"\s+"," ",q) for u in used)]
tp={k:next(iter(allrows[k])) for k in pool}
print("unused pool",collections.Counter(tp.values()))
random.seed(71); random.shuffle(pool); srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
n=0
for src,q in pool:
    part,name=info[(src,q)]; st,parts=load(src); m=find_quote(parts[part],q)
    if not m: continue
    X.append(dict(id=f"H6-{n:03d}",set='H6',key=tp[(src,q)],note='earlier-model label',state=build_state(parts[part],m[0],m[1],st,part,re.sub(r"_(guidance|surprise)$","",name)))); n+=1
    if n>=40: break
print(collections.Counter((x['set'],x['key']) for x in X))
json.dump(X,open('items_extra.json','w'),indent=1)
for x in X:
    if x['set']=='DIV': print(x['id'],'|',x['state']['driver_name'],'|',x['state']['quote'][:150])
