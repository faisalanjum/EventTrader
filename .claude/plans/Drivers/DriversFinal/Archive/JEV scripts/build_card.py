"""Answer keys = the earlier model's labels in experiments/runs/kf-* (silver, not truth). A fact counts as 'agreed' when every run that produced it gave the same label."""
import json,glob,re,collections,sys
sys.path.insert(0,'.')
from jevlib import build_state,find_quote
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
agg=collections.OrderedDict()
for f in sorted(glob.glob(f"{RUNS}/kf-*/*.raw.json")):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}; q=it.get('quote')
        if not q: continue
        k=(d.get('source_id'),q,it.get('driver_name'))
        a=agg.setdefault(k,dict(src=d.get('source_id'),quote=q,name=re.sub(r"_(guidance|surprise)$","",it.get('driver_name') or ''),part=x.get('part_ref'),ft=set(),state=[],lvl=[],chg=[],tt=[],runs=set()))
        a['ft'].add(x['fact_type']); a['runs'].add(f)
        a['state'].append(it.get('driver_state'))
        a['lvl'].append(it.get('level_unit') if it.get('level_low') is not None else None)
        a['chg'].append(it.get('change_unit') if it.get('change_value') is not None else None)
        a['tt'].append(it.get('time_type'))
srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
def lab(v):
    v=[x for x in v if x is not None]
    return (v[0],len(set(v))==1) if v else (None,False)
items=[]; lost=0
for k,a in agg.items():
    st,parts=load(a['src']); text=parts.get(a['part'])
    m=find_quote(text,a['quote']) if text else None
    if not m: lost+=1; continue
    state=build_state(text,m[0],m[1],st,a['part'],a['name'])
    row=dict(id=f"F{len(items):04d}",src=a['src'],fact_type=next(iter(a['ft'])) if len(a['ft'])==1 else 'mixed',runs=len(a['runs']),state=state)
    for f in ('state','lvl','chg','tt'):
        v,agreed=lab(a[f]); row['L_'+f]=v; row['L_'+f+'_agreed']=agreed
    assert isinstance(row['state'],dict) and 'quote' in row['state']          # the input must stay an input
    items.append(row)
json.dump(items,open('card_items.json','w'),indent=1)
print("unique facts",len(items),"| quote not found in source:",lost)
print("metric facts with a state:",sum(1 for x in items if x['fact_type']=='metric' and x['L_state'] is not None))
print("with a level unit:",sum(1 for x in items if x['L_lvl']),"| with a change unit:",sum(1 for x in items if x['L_chg']),"| with time_type:",sum(1 for x in items if x['L_tt']))
for f in ('state','lvl','chg','tt'):
    print(f,"agreed across runs:",sum(1 for x in items if x['L_'+f] is not None and x['L_'+f+'_agreed']),"of",sum(1 for x in items if x['L_'+f] is not None))
