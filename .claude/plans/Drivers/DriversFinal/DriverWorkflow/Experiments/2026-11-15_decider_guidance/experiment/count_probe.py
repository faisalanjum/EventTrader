import json,pathlib,sys,re,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
r=next(x for x in json.loads((R/'unseen_sentence_requests.json').read_text()) if x['name']=='OLLI')
qs={}
for s in r['sentences']:
 if s['tag'] not in ['S0053','S0086','S0099','S0106']:continue
 n=min(252,len(re.findall(r'\S+',s['text'])))
 options={str(i):None for i in range(n+1)}
 options.update({'more':f'More than {n} distinct forecasts.','unclear':'The eligible forecasts or their number cannot be established from the source.'})
 qs[s['tag']]={'type':'choice','instructions':f'How many distinct current management forecasts does [{s["tag"]}] state or qualify? Count one per measure, subject/business scope, target period and scenario. A numeric range is one forecast; different periods or measures are separate. Do not count actuals, earlier forecasts, restated duplicates, mere causes or unsupported analyst estimates. An assumption is separately counted only when management forecasts its own measure. Resolve references using the whole call; do not guess.','criteria':options}
req={'state':r['state'],'questions':qs}
(R/'count_probe_request.json').write_text(json.dumps(req,indent=2))
t=time.perf_counter()
try:out={**req,'response':L.decide(req['state'],req['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
except Exception as e:out={**req,'error':str(e),'seconds':time.perf_counter()-t}
(R/'count_probe_result.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'seconds':out['seconds'],'answers':{k:{'choice':a['choice'],'p':a['probabilities'].get(a['choice'])} for k,a in out.get('response',{}).get('answers',{}).items()},'error':out.get('error')}),flush=True)
