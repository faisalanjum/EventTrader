import json,glob,re,random,collections,sys
sys.path.insert(0,'.')
from jevlib import *
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
# ---- H5G: 35 unused pool facts, labeled by Claude BEFORE any Jev call (advice principles applied)
UNCLEAR={43:'dividend declaration under per-share driver',59:'dividend declaration under per-share driver',60:'completed action + expected completion in one quote',70:'became subject + expected impact in one quote'}
METRIC={51:'committed amount as of date',56:'method in use (advice group 7)'}
h=json.load(open('h1_raw.json')); H=[]
for i in range(40,75):
    o=h[i]; st=build_state(o['text'],o['s'],o['e'],o['src_type'],o['part'],o['gid'].split(':')[2])
    key='unclear' if i in UNCLEAR else 'metric' if i in METRIC else 'guidance'
    H.append(dict(id=f"H5G-{i}",set='H5G',key=key,note=UNCLEAR.get(i) or METRIC.get(i) or 'blind label',state=st))
# ---- H5M / H5A: unused earlier-model facts (metric / action), no overlap with anything used so far
used=[re.sub(r"\s+"," ",x['state']['quote']) for f in ('fixtures_v3.json','fixtures_h3.json','fixtures_h4.json','redo_items.json') for x in json.load(open(f))]
allrows=collections.defaultdict(set); info={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): allrows[(d.get('source_id'),it['quote'])].add(x['fact_type']); info[(d.get('source_id'),it['quote'])]=(x.get('part_ref'),it['driver_name'])
pool=collections.defaultdict(list)
for (src,q),ts in sorted(allrows.items()):
    if len(ts)!=1: continue
    t=next(iter(ts)); nq=re.sub(r"\s+"," ",q)
    if t in('metric','action_event') and not any(nq in u or u in nq for u in used): pool[t].append((src,q))
print("unused pool:",{k:len(v) for k,v in pool.items()})
random.seed(53); srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
for t,tag,k in (('metric','H5M',40),('action_event','H5A',30)):
    random.shuffle(pool[t]); n=0
    for src,q in pool[t]:
        part,name=info[(src,q)]; st,parts=load(src); m=find_quote(parts[part],q)
        if not m: continue
        H.append(dict(id=f"{tag}-{n:03d}",set=tag,key=t,note='earlier-model label',state=build_state(parts[part],m[0],m[1],st,part,re.sub(r"_(guidance|surprise)$","",name)))); n+=1
        if n>=k: break
print({t:sum(1 for x in H if x['set']==t) for t in ('H5G','H5M','H5A')}, "keys:",collections.Counter(x['key'] for x in H))
json.dump(H,open('fixtures_h5.json','w'),indent=1)
