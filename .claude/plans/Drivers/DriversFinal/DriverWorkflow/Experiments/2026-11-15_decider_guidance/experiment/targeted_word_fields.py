import json,pathlib,sys,time,os
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
requests=[]
for r in json.loads((R/'unseen_sentence_requests.json').read_text()):
 first_qa=min(s['passage'] for s in r['sentences'] if not s['prepared'])
 state=r['state'].split(f'[P{first_qa:03d}]',1)[0]
 tags=list(dict.fromkeys(c['tag'] for c in r['positive_controls']))
 qs={}
 for tag in tags:
  qs[tag+'_measures']={'type':'locate','instructions':f'For [{tag}], copy the source wording naming the financial or operating measure or business quantity it refers to. Copy what is measured, not a bare amount, unit, date or period. Include antecedent wording when the target uses a reference.'}
  qs[tag+'_expressions']={'type':'locate','instructions':f'For [{tag}], copy the distinct forecast expressions stated or qualified here, including applicable values, limiting words and references. Keep different expressions separate.'}
 requests.append({'name':r['name'],'state':state,'questions':qs,'controls':r['positive_controls']})
(R/'targeted_word_field_requests.json').write_text(json.dumps(requests,indent=2))
while True:
 try:os.kill(2920975,0)
 except ProcessLookupError:break
 time.sleep(2)
out=[]
for q in requests:
 t=time.perf_counter()
 try:r={**q,'response':L.decide(q['state'],q['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**q,'error':str(e),'seconds':time.perf_counter()-t}
 out.append(r);(R/'targeted_word_field_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'answers':{k:[{'text':s['text'],'score':s['score']} for s in a.get('spans',[])] for k,a in r.get('response',{}).get('answers',{}).items()},'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
