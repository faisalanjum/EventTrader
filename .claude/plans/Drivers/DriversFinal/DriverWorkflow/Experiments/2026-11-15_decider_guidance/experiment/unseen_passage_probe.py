import json,pathlib,sys,time,hashlib
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
raw=json.loads((R/'unseen_components.json').read_text())
definition="Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and qualifications that change a forecast's meaning. Exclude actual results, merely recalled old forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts."
requests=[]
for d in raw:
 ps=[]
 for p in d['snapshot']['prepared']:
  ps.extend(json.loads(p['content']))
 passages=[{'tag':f'P{i:03d}','text':s,'prepared':True} for i,s in enumerate(ps)]
 for q in sorted(d['snapshot']['qa'],key=lambda q:int(q['sequence'])):
  passages.append({'tag':f'P{len(passages):03d}','text':'\n'.join(e['text'] for e in json.loads(q['exchanges'])),'prepared':False})
 state=definition+'\n\n'+'\n\n'.join('['+p['tag']+'] '+p['text'] for p in passages)
 questions={p['tag']:{'type':'noul','instructions':f"Under the supplied definition, does [{p['tag']}] state, reaffirm, withdraw or qualify management guidance? Use the whole transcript as context. An analyst's question alone is not management confirmation."} for p in passages}
 requests.append({'name':d['selection']['ticker']+'_passages','state':state,'questions':questions,'passages':passages})
 requests.append({'name':d['selection']['ticker']+'_source_measures','state':'\n\n'.join(ps),'questions':{'measures':{'type':'locate','instructions':'Financial or operating measures'}}})
(R/'unseen_passage_requests.json').write_text(json.dumps(requests,indent=2))
out=[]
for q in requests:
 t=time.perf_counter()
 try:r={**q,'response':L.decide(q['state'],q['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**q,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'unseen_passage_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
