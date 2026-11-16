import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
req=json.loads((R/'measure_occurrences_request.json').read_text())
ss=json.loads((R/'sources.json').read_text())
s=next(x for x in ss if x['id']=='CTAS_2026-03-25T10.00')
out=[]
for pid in ['QA016','QA022']:
 p=next(x for x in s['passages'] if x['id']==pid)
 a=s['text'].index(p['text']);b=a+len(p['text']);marks=[m for m in req['marks'] if a<=m['start']<b]
 state=p['text']
 for m in sorted(marks,key=lambda x:(x['start'],x['tag']),reverse=True):
  z=m['start']-a;state=state[:z]+f"[{m['tag']}] "+state[z:]
 questions={m['tag']:{'type':'noul','instructions':f"Does the source phrase at [{m['tag']}] name a financial or operating measure or business quantity, rather than merely state a number, unit, date or period? The phrase may include an amount, but it must also identify what is being measured."} for m in marks if m['tag'].startswith('M')}
 test={'name':pid,'state':state,'questions':questions}
 (R/(pid+'_measure_kind_request.json')).write_text(json.dumps(test,indent=2))
 t=time.perf_counter()
 try:r={**test,'response':L.decide(state,questions,mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**test,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'measure_kind_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':pid,'seconds':r['seconds'],'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
