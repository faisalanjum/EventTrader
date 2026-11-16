import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
sys.path.insert(0,'/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts')
from config import local_llm as L
from fiscal_math import _compute_fiscal_dates
R=pathlib.Path('/tmp/decider_claude_review_20261115')
sources={x['id']:x for x in json.loads((R/'sources.json').read_text())}
cs=sources['CTAS_2026-03-25T10.00']
tagged=next(x for x in json.loads((R/'tagged_requests.json').read_text()) if x['name']=='cintas_tagged_fields')
passages=json.loads((R/'passage_fields_requests.json').read_text())
out=[]
def run(name,state,questions,extra=None):
 req={'name':name,'state':state,'questions':questions,**(extra or {})}
 (R/(name+'_request.json')).write_text(json.dumps(req,indent=2))
 t=time.perf_counter()
 try:r={**req,'response':L.decide(state,questions,mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**req,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'source_names_choices_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':name,'seconds':round(r['seconds'],2),'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
 return r

names={}
for p in passages:
 r=run('source_names_'+p['name'],p['state'],{'names':{'type':'locate','instructions':'Financial or operating measures'}})
 names[p['name']]=r.get('response',{}).get('answers',{}).get('names',{}).get('spans',[])

# Calendar-only metadata, verified independently from the pre-call SEC filing index.
# This is a fixed-month calendar test, not validation of a 52/53-week resolver.
periods={}
for fy in [2025,2026,2027]:
 for q in ['Q1','Q2','Q3','Q4','FY']:
  a,b=_compute_fiscal_dates(5,fy,q);periods[f'{q}_{fy}']=f'{q} FY{fy}: {a} through {b}, inclusive.'
 for half,qa,qb in [('H1','Q1','Q2'),('H2','Q3','Q4')]:
  a,_=_compute_fiscal_dates(5,fy,qa);_,b=_compute_fiscal_dates(5,fy,qb)
  periods[f'{half}_{fy}']=f'{half} FY{fy}: {a} through {b}, inclusive.'
periods.update({'short_term':'Explicit short-term horizon, no exact dates.','medium_term':'Explicit medium-term horizon, no exact dates.','long_term':'Explicit long-term horizon, no exact dates.','undefined_horizon':'Explicit ongoing or going-forward horizon, no exact dates.','other_stated':'Another stated period or date range.','several':'Several separate target periods apply.','unclear':'The target period cannot be established.'})
units={'usd':'US dollars per unit, including per-share amounts.','m_usd':'Aggregate US-dollar amount, stored in millions after exact rescaling.','percent':'A percentage level, such as a margin or tax rate.','percent_yoy':'Percentage growth or change versus the same period a year earlier.','percent_sequential':'Percentage growth or change versus the previous comparable period.','percent_points':'Percentage-point change.','basis_points':'Basis-point amount.','count':'Count of things.','x':'A multiple.','other_currency':'Another source-supported currency.','other_registry_unit':'Another source-supported physical or time unit.','unknown':'The unit or growth basis is not established by the source.'}
qs={}
for v in tagged['occurrences']:
 tag=v['tag'];target=f"the occurrence '{v['text']}' immediately following [{tag}]"
 qs[tag+'_period']={'type':'choice','instructions':f'What is the target period of {target}? Use the whole call and its fiscal context; distinguish the forecast period from comparisons and publication dates.','criteria':periods}
 qs[tag+'_unit']={'type':'choice','instructions':f'What unit does {target} use? Resolve references from the whole call. Do not infer units or the growth comparison basis from a metric name alone.','criteria':units}
 qs[tag+'_scale']={'type':'choice','instructions':f'What multiplier applies to the printed numeric quantity referenced by {target}, before conversion to its stored unit? Follow only source-supported scale wording.','criteria':{'one':'1; number as printed, including percent or basis-point units.','thousand':'1000.','million':'1000000.','billion':'1000000000.','other_stated':'A different stated scale.','unclear':'Scale cannot be established.'}}
 qs[tag+'_condition']={'type':'noul','instructions':f'Does management explicitly attach an assumption, exclusion or dependency to {target}, including a clearly applicable shared qualification elsewhere in this call? Do not count generic forward-looking boilerplate or a mere comparison with past results.'}
 pid='QA016' if tag=='V001' else 'QA022'
 spans=names[pid]
 if spans:
  criteria={f'M{i}':s['text'] for i,s in enumerate(spans)}
  criteria.update({'several':'Several of the listed measures.','none':'No listed measure fits.','unclear':'Cannot establish the measure from this source.'})
  qs[tag+'_source_measure']={'type':'choice','instructions':f'Which source wording names the measure forecast or qualified by {target}? Analyst wording counts only when management supports that meaning. This is source wording, not an existing Driver catalog.','criteria':criteria}
  for i,s in enumerate(spans):
   qs[tag+f'_association_{i}']={'type':'noul','instructions':f"Does {target} forecast or qualify '{s['text']}' as management states or clearly confirms in this transcript? Use the full context, not shared words or nearby placement alone."}
header='Company: Cintas. Call: 2026-03-25, fiscal Q3 FY2026. Verified ordinary month-end fiscal calendar: year ends May 31.\n\n'
run('full_call_choices',header+tagged['state'],qs,{'calendar_source':'https://www.sec.gov/Archives/edgar/data/723254/000072325426000002/0000723254-26-000002-index.htm','calendar_source_published':'2026-01-07','calendar_scope':'Ordinary month-end fiscal calendar only; existing helper does not support 52/53-week calendars.'})
