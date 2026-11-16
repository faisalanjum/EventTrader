import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
raw=json.loads((R/'word_choice_requests.json').read_text())
requests=[]
for r in raw:
 if r['name'] not in ['FDX','OLLI']:continue
 qs={}
 for tag,p in r['pieces'].items():
  for w in p['words']:
   qs[w['id']]={'type':'noul','instructions':f'Does word [{w["id"]}] begin a distinct current management forecast value or expectation in sentence [{tag}]? A value can be a number or words. Include its leading approximation, direction or bound wording; exclude the measure name, target period, actual results and merely recalled forecasts. Use the whole call for meaning.'}
 requests.append({'name':r['name'],'state':r['state'],'questions':qs,'pieces':r['pieces']})
(R/'word_start_requests.json').write_text(json.dumps(requests,indent=2))
out=[]
for q in requests:
 t=time.perf_counter()
 try:r={**q,'response':L.decide(q['state'],q['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**q,'error':str(e),'seconds':time.perf_counter()-t}
 ans=r.get('response',{}).get('answers',{});starts=[]
 for tag,p in q['pieces'].items():
  for w in p['words']:
   score=ans.get(w['id'],{}).get('noul',0)
   if score>=.25:starts.append({'sentence':tag,'word':w['text'],'id':w['id'],'p':score})
 r['starts_at_quarter']=starts;out.append(r);(R/'word_start_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'questions':len(q['questions']),'seconds':round(r['seconds'],2),'starts':starts,'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
