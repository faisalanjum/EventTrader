import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
source=next(s for s in json.loads((R/'sources.json').read_text()) if s['id']=='CTAS_2026-03-25T10.00')
original=next(x for x in json.loads((R/'tagged_requests.json').read_text()) if x['name']=='cintas_tagged_fields')
tests=[]
for pid,tag,needle in [('QA016','V001','7.6'),('QA022','V002','something less than that')]:
 state=next(p['text'] for p in source['passages'] if p['id']==pid)
 state=state.replace(needle,f'[{tag}] '+needle)
 questions={k:v for k,v in original['questions'].items() if k.startswith(tag+'_') and v['type']=='locate'}
 tests.append({'name':pid,'state':state,'questions':questions})
(R/'passage_fields_requests.json').write_text(json.dumps(tests,indent=2))
out=[]
for test in tests:
 t=time.perf_counter()
 try:r={**test,'response':L.decide(test['state'],test['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**test,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'passage_fields_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
