import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
sources={x['id']:x for x in json.loads((R/'sources.json').read_text())}
prior={x['name']:x for x in json.loads((R/'candidate_results.json').read_text())}
pay=sources['PAYX_2025-12-19T09.30']
prs={p['id']:p for p in pay['passages']}
tests=[
 {'name':'paychex_full_broad_alone','state':prior['paychex_prepared']['state'],'questions':{'values':{'type':'locate','instructions':'Numbers, amounts, percentages and numeric ranges'}}},
 {'name':'paychex_cfo_broad_pair','state':'[PR003] '+prs['PR003']['text'],'questions':prior['paychex_prepared']['questions']},
 {'name':'paychex_full_concrete_types','state':prior['paychex_prepared']['state'],'questions':{k:{'type':'locate','instructions':v} for k,v in [('percent','Percentages'),('money','Monetary amounts'),('bare','Numbers without an explicit unit'),('words','Qualitative forecasts, reaffirmations, withdrawals and forecast qualifications')]}},
 {'name':'erp_generic_wording','state':prior['erp']['state'],'questions':{'values':{'type':'locate','instructions':'Numbers, amounts, percentages and numeric ranges'},'wording':{'type':'locate','instructions':'Qualitative forecasts, reaffirmations, withdrawals and forecast qualifications'}}},
]
(R/'locate_followup_requests.json').write_text(json.dumps(tests,indent=2))
results=[]
for c in tests:
 t=time.perf_counter()
 try: result={**c,'response':L.decide(c['state'],c['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e: result={**c,'error':str(e),'seconds':time.perf_counter()-t}
 results.append(result);(R/'locate_followup_results.json').write_text(json.dumps(results,indent=2))
 print(json.dumps({'name':c['name'],'seconds':round(result['seconds'],2),'answers':result.get('response',{}).get('answers'),'usage':result.get('response',{}).get('usage'),'error':result.get('error')}),flush=True)
