"""Reviewer source-reading annotations. Not derived from the evaluated Decider outputs."""
import json,pathlib,hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
R=pathlib.Path('/tmp/decider_claude_review_20261115')
s=next(x for x in json.loads((R/'sources.json').read_text()) if x['id']=='CTAS_2025-09-24T10.00')
ps={p['id']:p['text'] for p in s['passages']}; starts={};off=0
for p in s['passages']:starts[p['id']]=off;off+=len(p['text'])+2
assert '\n\n'.join(p['text'] for p in s['passages'])==s['text']
def span(p,text,role):
 assert ps[p].count(text)==1,(p,text,ps[p].count(text))
 a=ps[p].index(text);b=a+len(text)
 assert s['text'][starts[p]+a:starts[p]+b]==text
 return {'passage':p,'start':a,'end':b,'global_start':starts[p]+a,'global_end':starts[p]+b,'text':text,'role':role}
def between(p,first,last,role):
 assert ps[p].count(first)==1 and ps[p].count(last)==1
 a=ps[p].index(first);b=ps[p].index(last)+len(last);assert a<b
 return span(p,ps[p][a:b],role)
lead=span('PR002','Reflecting our strong first quarter performance, we are raising our fiscal 2026 financial guidance.','target period and stated movement; causal introductory words remain source evidence')
revenue=span('PR002','We expect our revenue to be in the range of $11.06 billion to $11.18 billion, a total growth rate of 7%, to 8.1%.','two distinct forecast quantities')
eps=span('PR002','We expect diluted EPS to be in the range of $4.74 to $4.86, a growth rate of 7.7% to 10.5%.','two distinct forecast quantities; diluted measurement qualifier')
assumptions=between('PR004','Earlier, Todd provided our updated guidance for the remainder of the year.','And finally, our guide does not include any future share buybacks or significant economic disruptions or downturns.','shared guidance assumptions and separately forecast interest/tax amounts; applicability is field-specific')
employment=between('QA006','But we\'re not forecasting for that,','without, you know, the employment picture being, you know, real favorable.','guidance does not assume a substantially more favorable employment environment')
tariff=span('QA009','And I\'d just like to remind you that our guide contemplates the current environment for tariffs as well.','stated tariff environment incorporated in guidance')
claims=[]
def add(i,meaning,evidence,expected,unresolved=(),status='confirmed_claim'):
 claims.append({'id':i,'meaning':meaning,'status':status,'evidence':evidence,'expected_source_fields':expected,'unresolved_fields_or_policy':list(unresolved),'continuous_quote_interval':{'start':min(x['global_start'] for x in evidence),'end':max(x['global_end'] for x in evidence)},'complete_record_gold':not bool(unresolved)})
common={'subject':'Cintas Corporation','period_text':'fiscal 2026','period_scope':'annual','driver_state':'raised','company_confirmed':True,'time_type':'duration'}
shared=[lead,assumptions,employment,tariff]
shared_open=['Adjudicate applicability of shared employment/tariff/financial assumptions to each specific quantity; do not paste every shared clause into conditions indiscriminately.','Verify and pin subject fiscal-calendar evidence before date normalization.']
add('SEP01','Annual revenue level',[revenue]+shared,{**common,'value_shape':'closed_range','level_low':'11060','level_high':'11180','level_unit':'m_usd','source_unit_scale':'billions of dollars','measurement_words':[]},shared_open)
add('SEP02','Annual revenue growth',[revenue]+shared,{**common,'value_shape':'closed_range','level_low':'7','level_high':'8.1','level_unit':'unknown','comparison_basis':'not established for this growth figure','measurement_words':['growth rate']},shared_open+['Keep growth meaning distinct from the revenue level; no default yearly basis from the fiscal-year label.'])
add('SEP03','Annual diluted earnings per share level',[eps]+shared,{**common,'value_shape':'closed_range','level_low':'4.74','level_high':'4.86','level_unit':'usd','measurement_words':['diluted']},shared_open)
add('SEP04','Annual diluted earnings per share growth',[eps]+shared,{**common,'value_shape':'closed_range','level_low':'7.7','level_high':'10.5','level_unit':'unknown','comparison_basis':'not established for this growth figure','measurement_words':['diluted','growth rate']},shared_open+['Growth is a guidance value, not the size of a revision.'])
add('SEP05','Annual net interest expense',[assumptions],{'subject':'Cintas Corporation','period_text':'fiscal 2026','period_scope':'annual','value_shape':'point','level_low':'97.0','level_high':'97.0','level_unit':'m_usd','measurement_words':['approximately'],'driver_state':'unknown','company_confirmed':True,'time_type':'duration'},['Pin fiscal-calendar evidence.','Do not automatically turn every other number in the same assumption sentence into a condition of this forecast.'])
add('SEP06','Annual effective tax rate',[assumptions],{'subject':'Cintas Corporation','period_text':'fiscal 2026','period_scope':'annual','value_shape':'point','level_low':'20.0','level_high':'20.0','level_unit':'percent','comparison_text':'which is the same compared to our fiscal 2025','driver_state':'unknown','company_confirmed':True,'time_type':'duration'},['Pin fiscal-calendar evidence.','Adjudicate exact comparison-field encoding of the stated same-as-prior-year rate; do not invent an earlier-forecast comparison.'])
inc=between('QA008','And then also the incrementals are right where we like them to be at that stated 25 to 35% range.','But being able to make those investments while improving margins at the exact same time, it\'s real strength of our business.','current incremental-margin range, implied margin expansion and investment context')
add('SEP07','Current incremental-margin target',[between('QA008','Joshua Chan [1461]:','And then also the incrementals are right where we like them to be at that stated 25 to 35% range.', 'EPS-guidance question and management scope'),inc],{'value_shape':'closed_range','level_low':'25','level_high':'35','level_unit':'percent','measure_text':'incrementals','company_confirmed':True},['Resolve the precise margin definition from permitted evidence; do not silently supply operating or EBITDA.','Resolve annual versus remaining-quarter scope and whether the source states reaffirmation.'])
add('SEP08','Implied margin expansion',[inc],{'value_text':'it also implies margin expansion within there as well','company_confirmed':True},['Resolve which margin and target period; distinguish this source claim from the related incremental-margin target.'])
remaining=between('QA008','Joshua Chan [1461]:','Q2 through 4 implied guide also increases at all points within the range.','analyst identifies EPS; management separately raises the remaining-quarter guide')
add('SEP09','EPS guidance for Q2–Q4 is raised',[remaining],{'measure_semantics':'earnings per share','period_text':'Q2 through 4','driver_state':'raised','company_confirmed':True,'new_numeric_level_stated':False,'source_value_or_state_wording':'Q2 through 4 implied guide also increases at all points within the range.'},['Normalize the Q2–Q4 duration using verified fiscal metadata.','Determine state-only versus value_text encoding under the current contract; absence of a new amount must not itself discard a permitted state-only guidance claim.'])
raised_growth=between('QA002','George Tong [844]:','the opening guide at all points within the range.','question names revenue and EPS; management raises an unnamed implied growth guide for Q2–Q4')
add('SEP10','Unnamed implied growth for Q2–Q4 higher than opening guide',[raised_growth],{'period_text':'queues two through four','driver_state':'raised','value_text':'higher than the opening guide at all points within the range','company_confirmed':True},['Determine whether the claim concerns revenue, EPS, both, or overlaps SEP09; do not force one metric or duplicate it.'],status='claim_requires_association')
firstaid=between('QA017','Faiza Aoui [2291]:','as a low double-digit growth business for us moving forward.','analyst identifies first-aid top-line growth and 3–5-year horizon; management confirms worded target')
add('SEP11','First-aid revenue growth outlook',[firstaid],{'subject':'Cintas Corporation','business_scope_text':'first aid business','value_text':'low double-digit','numeric_value_fields':None,'growth_basis':'not explicitly established','company_confirmed':True,'period_text':['over the next three to five years','moving forward']},['Resolve an admissible period without inventing an endpoint; source duration range and management long-term investment context need careful separation.','Do not convert low double-digit into a numeric range or default a yearly comparison basis.'])
fa_margin=between('QA018','Faiza Aoui [2402]:','But we like where it is and in the future as well.','question asks incremental margins; answer discusses gross margin and future leverage without a sudden pop')
add('SEP12','First-aid margin outlook/leverage',[fa_margin],{'company_confirmed':True,'quoted_current_level_is_not_new_forecast':'56.8%','future_wording':'I wouldn\'t be thinking of it as – oh, geez, you know, the first aid margin is going to pop after a certain timing.'},['Determine whether this is sufficiently specific guidance and which margin it concerns; do not promote the current 56.8% gross margin to a future point.'],status='borderline_claim')
sga=between('QA023','Tony Kaplan [3105]:','ramp up or ramp down from there from that perspective.','analyst asks all-other SG&A through fiscal year; management predicts no ramp from present investment level')
add('SEP13','SG&A investment level does not ramp up or down',[sga],{'value_text':'I don\'t think you\'ll see a ramp up or ramp down from there from that perspective.','company_confirmed':True,'period_text':'throughout the year / this fiscal year'},['Resolve all-other versus total-company scope, and absolute investment level versus expense ratio.','Do not borrow the later actual 27.5% as the forecast.'])
sga_future=span('QA023','but we think we\'re in a good spot from an SG&A investment and plan to get leverage on that over time.','future leverage statement; not the preceding reported expense ratio')
add('SEP14','SG&A leverage over time',[sga_future],{'company_confirmed':True,'period_text':'over time'},['Decide whether this is specific financial guidance or general investment intent and resolve scope/measure.'],status='borderline_claim')
capex=between('QA026','From a CapEx standpoint,','where we plan to be moving forward.','management confirms standing percentage target; no target fiscal year or denominator is stated here')
add('SEP15','Standing CapEx percentage target',[capex],{'value_shape':'point','level_low':'4','level_high':'4','level_unit':'percent','driver_state':'reaffirmed','period_text':'moving forward','company_confirmed':True},['Do not invent revenue as denominator; identify what permitted current/prior evidence would establish it.','The source does not explicitly assign this to FY2026; apply the stated-horizon rules, not the call year.'])
coverage=[]
roles={
 'PR000':'Operator introduction; no forecast.', 'PR001':'Participants and forward-looking disclaimer; no specific forecast.',
 'PR002':'SEP01–04, period and movement; reported results are negative controls.',
 'PR003':'Actual segment results and business example; no separate specific forecast.',
 'PR004':'SEP05–06 and shared assumptions for annual guidance; actual results/capital allocation are not new guidance.',
 'PR005':'General confidence and investment intent; no separate specific financial target.',
 'PR006':'Call procedure only.','PR007':'Call procedure only.',
 'QA000':'Future investment plans and generic ability to grow; not a specific forecast level. Mixed speaker text must not be inferred from stored label alone.',
 'QA001':'Current selling environment/results, not a specific future forecast.',
 'QA002':'SEP10, remaining-quarter growth guide; metric association unresolved.',
 'QA003':'Current business drivers and generic growth confidence; employment context, no exact separate forecast.',
 'QA004':'Observed early-quarter demand, not a new full-period forecast.',
 'QA005':'Customer example and strategy; no separate guidance target.',
 'QA006':'Employment assumption supporting guidance; inventory/use-of-capital discussion is current explanation, not a stated amount forecast.',
 'QA007':'Current vertical/customer behavior.',
 'QA008':'SEP07–09; current range and remaining-quarter guidance, with possible scope/meaning ambiguities.',
 'QA009':'Tariff environment included in guide; supplier statistics are actuals, not forecasts.',
 'QA010':'Current sales-cycle observation and general investment intent.',
 'QA011':'Actual first-aid margins and investment timing; general positive outlook.',
 'QA012':'Analyst proposes higher investment; management describes timing/ongoing investment, not a clear quantified or specific level forecast.',
 'QA013':'Competitive strategy/TAM and current customer counts, not company financial forecasts.',
 'QA014':'Actual all-other margins and planned investment activity.',
 'QA015':'Uniform-direct strategic context, current revenue share and general lumpiness; no specific future level.',
 'QA016':'M&A opportunity/strategy, explicitly difficult to predict; no specific forecast.',
 'QA017':'SEP11, first-aid worded growth target and horizon.',
 'QA018':'SEP12, potential margin/leverage outlook; actual 56.8% is not a future point.',
 'QA019':'Acquisition strategy and historical cadence, no specific financial/operating target.',
 'QA020':'Technology investment plans, not specific forecast amounts/levels.',
 'QA021':'Strategy, current counts and possible acquisitions; no specific company forecast.',
 'QA022':'Current visa-policy impact observations; no future impact forecast.',
 'QA023':'SEP13–14; stable SG&A investment and possible leverage outlook, with actual ratio controls.',
 'QA024':'Actual growth and counterfactual Q1 9% calculation; not future guidance.',
 'QA025':'Current M&A prices/strategy and uncertainty; no specific financial forecast.',
 'QA026':'SEP15, standing CapEx target.',
 'QA027':'Next reporting date; an event schedule, not financial guidance.'}
assert set(roles)==set(ps)
for p in s['passages']:coverage.append({'passage':p['id'],'read_in_full':True,'disposition':roles[p['id']],'sha256':hashlib.sha256(p['text'].encode()).hexdigest()})
out={'source_id':s['id'],'source_text_sha256':hashlib.sha256(s['text'].encode()).hexdigest(),'snapshot_sha256':s['snapshot_sha256'],'annotated_at':datetime.now(ZoneInfo('America/Toronto')).isoformat(),'method':'Full prepared remarks and every Q&A passage read directly by the root agent for this pass. No legacy records or draft-inventory labels consulted during this reading. Prior conversation exposure exists: this is NOT a blinded or independently double-reviewed gold key. Root-agent source annotations are separate from evaluated Decider outputs.','record_policy':'../record_policy.md','status':'source-claim inventory with exact evidence; adjudication and full normalized field key remain incomplete','claims':claims,'passage_coverage':coverage}
f=R/'reference_key/CTAS_2025-09-24T10.00.json';f.write_text(json.dumps(out,indent=2,ensure_ascii=False))
for c in claims:
 for e in c['evidence']:assert s['text'][e['global_start']:e['global_end']]==e['text']
print(json.dumps({'source':s['id'],'passages_read':len(coverage),'claim_entries':len(claims),'source_spans':sum(len(c['evidence']) for c in claims),'status':out['status']},indent=2))
with (R/'progress.md').open('a') as f:
 f.write('\nTest: Source-only annotation pass on all 36 prepared/Q&A passages of CTAS 2025-09-24; exact evidence intervals checked mechanically.\n')
 f.write('Result: 15 claim/interpretation entries with passage coverage and source-backed fields; this includes ambiguities, not 15 certified records. No model calls, blind-pass claim or complete gold-key claim.\n')
 f.write('Next: Compare the independent source reading with the supplied draft/legacy records, expose disagreements, then continue the remaining five source reads before new model tuning.\n')
