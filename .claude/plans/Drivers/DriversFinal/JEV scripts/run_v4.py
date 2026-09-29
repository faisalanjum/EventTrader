import json,glob,re,random,collections,sys,copy
sys.path.insert(0,'.')
from jevlib import *
import prompts_v3 as P
from concurrent.futures import ThreadPoolExecutor
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
QC4=copy.deepcopy(P.QC); c=QC4['fact_type']['criteria']
c['metric']['what']+=" A figure that a company reports for each period (revenue, an expense, income, a cash flow, a balance) is such a variable, even when the sentence describes it with a verb like recorded, increased or decreased."
c['action_event']['not_for']="A standing variable or condition, or a forecast. A figure reported for each period is not an action_event just because the sentence uses a verb like recorded or increased."
json.dump(QC4,open('QC4.json','w'),indent=1)
# ---- H4: fresh metric facts untouched by any tuning (excludes DEV, H1, H2, H3)
used=[re.sub(r"\s+"," ",f['state']['quote']) for f in json.load(open('fixtures_v3.json'))+json.load(open('fixtures_h3.json'))]
allrows=collections.defaultdict(set); info={}
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}
        if it.get('quote'): allrows[(d.get('source_id'),it['quote'])].add(x['fact_type']); info[(d.get('source_id'),it['quote'])]=(x.get('part_ref'),it['driver_name'])
pool=[(s,q) for (s,q),ts in sorted(allrows.items()) if ts=={'metric'} and not any(re.sub(r"\s+"," ",q) in u or u in re.sub(r"\s+"," ",q) for u in used)]
random.seed(31); random.shuffle(pool); srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
h4=[]
for src,q in pool:
    part,name=info[(src,q)]; st,parts=load(src); m=find_quote(parts[part],q)
    if not m: continue
    h4.append(dict(set='H4',id=f"H4-{len(h4):03d}",src=src,key='metric',note='earlier-model label',state=build_state(parts[part],m[0],m[1],st,part,re.sub(r"_(guidance|surprise)$","",name))))
    if len(h4)>=40: break
json.dump(h4,open('fixtures_h4.json','w'),indent=1)
allf=json.load(open('fixtures_v3.json'))+json.load(open('fixtures_h3.json'))+h4
def two(f): return P.call(f['state'],P.QC),P.call(f['state'],QC4)
with ThreadPoolExecutor(8) as ex: R=list(ex.map(two,allf))
out=[]
for f,(a,b) in zip(allf,R):
    if 'error' in a or 'error' in b: print('ERR',f['id']); continue
    x,y=a['answers']['fact_type'],b['answers']['fact_type']
    out.append(dict(id=f['id'],set=f['set'],key=f['key'],note=f['note'],quote=f['state']['quote'],name=f['state']['driver_name'],C=x['choice'],C_conf=x['confidence'],C4=y['choice'],C4_conf=y['confidence'],C4_p=y['probabilities']))
json.dump(out,open('results_v4.json','w'),indent=1); print("scored",len(out))
