"""One frozen common-path field pass. Ambiguity stays unresolved; no repair loop."""
import json,pathlib,sys,time
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
R=T.R
b=json.loads((R/'B_result.json').read_text())
sel=json.loads((R/'B_selection.json').read_text())
# Model output alone selects these inputs; no expected names/values are read.
cs=[]
for c in sel['numeric']:
 a=c['answer'];p=a['probabilities'][a['choice']]
 if a['choice'] in ['current','qualification'] and p>=.5:cs.append({**c,'kind':'numeric','selection_p':p})
for c in sel['worded']:
 if c['p']>=.5:cs.append({**c,'kind':'worded','selection_p':c['p']})
T.save('C_targets',cs)
periods={}
from datetime import date
# This fixture has verified ordinary month-end fiscal periods; this is not a generic week-calendar resolver.
for fy in [2025,2026,2027]:
 periods[f'FY{fy}']=f'{fy-1}-06-01 through {fy}-05-31'
 for label,start,end in [('Q1',f'{fy-1}-06-01',f'{fy-1}-08-31'),('Q2',f'{fy-1}-09-01',f'{fy-1}-11-30'),('Q3',f'{fy-1}-12-01',f'{fy}-02-28'),('Q4',f'{fy}-03-01',f'{fy}-05-31'),('H1',f'{fy-1}-06-01',f'{fy-1}-11-30'),('H2',f'{fy-1}-12-01',f'{fy}-05-31')]:
  periods[f'{label}_FY{fy}']=start+' through '+end
periods.update({k:k.replace('_',' ') for k in ['short_term','medium_term','long_term','undefined_horizon','other_stated','several','unclear']})
units={
 'usd':'US dollars per share or other single unit; scale 1.',
 'usd_cents':'US cents per share or other single unit; convert once to dollars, factor .01.',
 'm_usd_from_dollars':'Company money total printed in dollars; convert to millions, factor .000001.',
 'm_usd_from_thousands':'Company money total printed in thousands; convert to millions, factor .001.',
 'm_usd_from_millions':'Company money total printed in millions; factor 1.',
 'm_usd_from_billions':'Company money total printed in billions; convert to millions, factor 1000.',
 'percent':'Percentage level; scale 1.',
 'percent_yoy':'Percentage growth/change explicitly vs the same period a year earlier; scale 1.',
 'percent_sequential':'Percentage growth/change explicitly vs the previous comparable period; scale 1.',
 'percent_points':'Percentage-point amount; scale 1.',
 'basis_points':'Basis-point amount; scale 1.',
 'count':'Count, scale 1.','count_thousand':'Count in thousands.','count_million':'Count in millions.','count_billion':'Count in billions.',
 'x':'A multiple, scale 1.',
 'other_stated':'Another source-supported currency, physical/time unit or scale; needs its exact evidence and official registry mapping.',
 'numberless':'No amount or evidenced growth-basis unit.',
 'unknown':'Unit, growth basis or scale cannot be established.',
 'several':'The target contains several different amounts/units.'}
menus={
 'form':{'point':'One current forecast point.','range':'One current forecast with a lower and upper endpoint.','floor':'One current lower bound.','ceiling':'One current upper bound.','words':'One meaningful current forecast expressed in words.','revision':'Only an explicitly stated size of a forecast revision.','qualification':'Only a condition, comparison or qualification on another forecast.','reaffirmation':'A reaffirmation without restated values.','withdrawal':'A withdrawal.','centre_tolerance':'Centre and tolerance, not endpoints.','several':'Several distinct forecasts; do not collapse them.','none':'No eligible management forecast or qualifier.','unclear':'Cannot establish the meaning.'},
 'subject_scope':{'source_company_total':'Whole call company.','source_company_part':'A stated business, product, geography or other part of the call company.','other_subject':'A different source-identified company or subject.','shared':'A genuinely shared measure, with no single company subject.','unclear':'The subject/scope is not established.'},
 'period':{k:None for k in periods},
 'unit_scale':{k:None for k in units},
 'sign':{'positive':'The forecast amount increases or is positive in the measured quantity.','negative':'The forecast amount reduces or is negative in the measured quantity.','zero':'Explicit zero.','not_numeric':'No single numeric amount.','several':'Different signs/amounts.','unclear':'The sign is not established.'},
 'movement':{k:None for k in ['introduced','raised','lowered','reaffirmed','withdrawn','not_stated','unclear']},
 'time_type':{k:None for k in ['duration','instant','unclear']}}
instructions={
 'form':'What is the role and form of the current forecast expression, keeping separate measures/periods separate?',
 'subject_scope':'Whose measure and business scope is this?',
 'period':'Which target period is established? Use the subject\'s calendar; never force an unavailable period or use a comparison period.',
 'unit_scale':'Which source-supported unit and scale applies? A bare $/cents defaults to US dollars unless contradicted. Do not infer a growth basis, unit or scale from the metric name or magnitude.',
 'sign':'What sign does this forecast amount have in the measured quantity? Respect meaning, not only a printed minus.',
 'movement':'What guidance movement does management explicitly state? Never calculate a revision from earlier values.',
 'time_type':'Does the forecast measure a duration or a single instant? Do not default.'}
state=b['state']+'\n\nPERIOD OPTIONS (calendar metadata, not quote text):\n'+json.dumps(periods)+'\nUNIT/SCALE OPTIONS:\n'+json.dumps(units)
questions={}
for c in cs:
 v=c['tag']
 for k,m in menus.items():questions[v+'_'+k]={'type':'choice','instructions':f'For the source target [{v}], '+instructions[k],'criteria':m}
 for k,desc in {'conditions':'any applicable assumption, exclusion, dependency or qualification that changes the forecast meaning, including a shared statement elsewhere in this call; exclude generic boilerplate and mere causes','comparison_revision':'any explicitly stated earlier-forecast comparison or size of revision; exclude values only obtainable by arithmetic'}.items():
  questions[v+'_'+k]={'type':'noul','instructions':f'Does management explicitly attach {desc} to [{v}]?'}
ans=T.run('C_choices',state,questions,targets=cs,period_menu=periods,unit_menu=units)
# Copy only positive eligible targets, using full prepared remarks or the complete Q&A.
cs=[c for c in cs if ans[c['tag']+'_form']['choice'] not in ['none','unclear','several']]
T.save('C_copy_targets',cs)
starts=[]
for p in T.source['passages']:
 marker='['+p['id']+'] '
 start=b['state'].index(marker)
 starts.append((start,p))
contexts={}
for i,(start,p) in enumerate(starts):
 end=starts[i+1][0] if i+1<len(starts) else len(b['state'])
 contexts[p['id']]=b['state'][start:end]
prepared='\n\n'.join(contexts[p['id']] for p in T.source['passages'] if p['kind']=='prepared')
groups={}
for c in cs:
 p=next(x for x in T.source['passages'] if x['id']==c['passage'])
 key='prepared' if p['kind']=='prepared' else p['id']
 groups.setdefault(key,[]).append(c)
raw={}
for key,targets in groups.items():
 local=T.DEFINITION+'\n\n'+(prepared if key=='prepared' else contexts[key])
 qs={}
 for c in targets:
  v=c['tag']
  fields={
   'measure':f'Source wording naming the financial or operating measure for [{v}], including its measurement and business-scope qualifiers. Follow references to the antecedent, including confirmed analyst wording. Do not return a bare amount, unit or date as its name.',
   'value':f'Current management forecast amount, range or expectation for [{v}], including limiting words. Keep other measures, actuals and earlier forecasts separate, except when the current wording refers to them.',
   'context':f'Source wording giving the target period, unit and scale applying to [{v}]. Copy only evidence for this forecast.'}
  for k,label in fields.items():qs[v+'_'+k]={'type':'locate','instructions':label}
 a=T.run('C_copy_'+key,local,qs,targets=targets)
 for q,x in a.items():
  for s in x['spans']:assert local[s['start']:s['end']]==s['text']
 raw[key]={'state':local,'answers':a}
T.save('C_copied',raw)
# Optional full-call copying only for a positive presence judgment. No retries after empty copying.
qs={}
for c in cs:
 v=c['tag']
 for k,desc in {'conditions':'every applicable assumption, exclusion, dependency or qualification that changes this forecast\'s meaning; include shared guidance assumptions when they apply, not generic boilerplate or causes','comparison_revision':'any explicitly stated comparison/revision amount, its unit and baseline; exclude derived values'}.items():
  if ans[v+'_'+k]['noul']>=.5:qs[v+'_'+k]={'type':'locate','instructions':f'For [{v}], copy {desc}. Select only source wording that supports this specific forecast.'}
if qs:
 a=T.run('D_optional',b['state'],qs,targets=cs)
 for x in a.values():
  for s in x['spans']:assert b['state'][s['start']:s['end']]==s['text']
print(json.dumps({'finished_targets':len(cs),'note':'No retries, model-written records, canonical naming or database writes. Assembly is a separate deterministic inspection.'}),flush=True)
