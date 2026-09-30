"""Build the baseline / horizon / slice-kind test sets. Labels are fixed BEFORE any Jev call: kf-run labels (silver), older GuidanceUpdate period_scope (silver),
and my mapping of the frozen surprise labels to baselines (rule 3.52). Every label lives in L_key; the input stays in state (asserted)."""
import json,glob,re,random,collections,sys,hashlib
sys.path.insert(0,'.')
from jevlib import build_state,find_quote
from neo4j import GraphDatabase
EV="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS="/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
random.seed(44); items=[]
def add(task,key,state,note,src=''):
    assert isinstance(state,dict) and 'quote' in state
    items.append(dict(id=f"{task[:2].upper()}{len(items):04d}",task=task,L_key=key,state=state,note=note,src=src))
# ---------- kf runs (baseline + slice kind)
agg=collections.OrderedDict()
for f in sorted(glob.glob(f"{RUNS}/kf-*/*.raw.json")):
    try: d=json.load(open(f))
    except: continue
    if not isinstance(d,dict): continue
    for x in d.get('facts') or []:
        it=x.get('item') or {}; q=it.get('quote')
        if not q: continue
        k=(d.get('source_id'),q,it.get('driver_name'))
        a=agg.setdefault(k,dict(src=d.get('source_id'),quote=q,name=re.sub(r"_(guidance|surprise)$","",it.get('driver_name') or ''),part=x.get('part_ref'),ft=x['fact_type'],base=[],slices=set(),lvl=it.get('level_low') is not None,chg=it.get('change_value') is not None))
        a['base'].append(it.get('comparison_baseline'))
        for sp in it.get('slice_parts') or []: a['slices'].add(str(sp))
srcs={}
def load(s):
    if s not in srcs:
        d=json.load(open(f"{EV}/{s}.json")); srcs[s]=(d['source_type'],{p['part']:p['content'] for p in d['text_parts']})
    return srcs[s]
def st_of(a):
    st,parts=load(a['src']); text=parts.get(a['part']); m=find_quote(text,a['quote']) if text else None
    return build_state(text,m[0],m[1],st,a['part'],a['name']) if m else None
base_none=[]
for k,a in agg.items():
    labs=[b for b in a['base'] if b];
    if labs and len(set(labs))==1:
        s=st_of(a)
        if s: add('baseline',labs[0],s,'kf label',a['src'])
    elif not labs and a['ft']=='metric' and (a['lvl'] or a['chg']): base_none.append(a)
random.shuffle(base_none)
for a in base_none[:70]:
    s=st_of(a)
    if s: add('baseline','none',s,'kf: no baseline extracted (may hide a stated comparison)',a['src'])
# slice kinds: one item per (fact, slice); skip xbrl-axis 'unknown' (value is a hex axis id, not text)
for k,a in agg.items():
    for sp in sorted(a['slices']):
        kind,_,val=sp.partition(':')
        if kind in ('segment','product','geography','customer','channel','entity_ownership') and val:
            s=st_of(a)
            if s: s=dict(s); s['slice_value']=val.replace('_',' '); add('slice',kind,s,'kf label',a['src'])
# ---------- baseline from my frozen surprise labels (rule 3.52): kind -> baseline; controls mapped below
S=json.load(open('surprise_items.json')); C=json.load(open('surprise_candidates.json'))
CTRL={38:'previous_guidance',67:'previous_guidance',69:'previous_guidance',70:'previous_guidance',71:'previous_guidance',72:'prior_year',73:'prior_year',75:'prior_year',76:'prior_year',77:'prior_year',
      55:'none',56:'none',58:'none',61:'none',62:'none',63:'none'}
CTRL_SPAN={("Sees Capital Expenditures Of Approximately $800M",27):'none',("Now Sees A Low-Single-Digit Increase In Organic Revenue (Prior ~4% Organic)",19):'previous_guidance',
           ("Raises Guidance As AI Demand Soars",22):'previous_guidance',("which is $16.7 million better than Q3 of 2022",48):'prior_year',("operating expenses, which were down 19% year-over-year to $555 million",49):'prior_year',
           ("Announces $1 Billion Buyback",22):'none'}
for x in S:
    if not x['scored']: continue
    q=x['state']['quote']
    if x['key']=='surprise': key={'actual_vs_consensus':'consensus','guidance_vs_consensus':'consensus','actual_vs_guidance':'previous_guidance'}[x['kind']]
    elif (q,x['cand']) in CTRL_SPAN: key=CTRL_SPAN[(q,x['cand'])]
    elif x['cand'] in CTRL and q==C[x['cand']]['quote']: key=CTRL[x['cand']]
    else: continue
    add('baseline',key,x['state'],'frozen surprise/control set (rule 3.52)',x['id'])
# ---------- horizon from the older GuidanceUpdate period_scope (silver)
env=dict(l.strip().split("=",1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=",l))
drv=GraphDatabase.driver(env["NEO4J_URI"],auth=(env["NEO4J_USERNAME"],env["NEO4J_PASSWORD"].strip("'\"")))
WHERE={'PR':'earnings press release','Q&A':'answer to an analyst question on an earnings call','8-K':'current report (8-K)','10-Q':'quarterly report (10-Q)','10-K':'annual report (10-K)'}
def hstate(quote,label):
    m=re.match(r"^\[([^\]]{1,10})\]\s*",quote); tag=m.group(1) if m else ''; q=quote[m.end():] if m else quote
    return dict(where_it_appears=WHERE.get(tag,'company statement'),driver_name=(label or 'guidance').replace('_',' '),text_before_quote='',quote=q.strip(),text_after_quote='')
with drv.session(default_access_mode="READ") as s:
    for scope,n,lab in (('short_term',25,'short_term'),('medium_term',25,'medium_term'),('long_term',25,'long_term'),('undefined',25,'undefined'),('annual',20,'stated_window'),('quarter',20,'stated_window'),('half',8,'stated_window')):
        rows=s.run("MATCH (g:GuidanceUpdate) WHERE g.period_scope=$p AND size(g.quote)>40 AND size(g.quote)<500 RETURN g.quote AS q, g.label AS l LIMIT 400",p=scope).data()
        random.shuffle(rows)
        for r in rows[:n]: add('horizon',lab,hstate(r['q'],r['l']),f'GuidanceUpdate period_scope={scope}',scope)
json.dump(items,open('items_more.json','w'),indent=1)
h=hashlib.sha256(json.dumps([[x['id'],x['task'],x['L_key']] for x in items]).encode()).hexdigest()[:16]
print("labels frozen before any Jev call, hash",h)
for t in ('baseline','horizon','slice'):
    print(t,len([x for x in items if x['task']==t]),dict(collections.Counter(x['L_key'] for x in items if x['task']==t)))
