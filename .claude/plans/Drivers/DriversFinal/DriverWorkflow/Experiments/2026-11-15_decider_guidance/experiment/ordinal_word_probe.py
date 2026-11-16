import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
r=next(x for x in json.loads((R/'word_choice_requests.json').read_text()) if x['name']=='OLLI')
counts=json.loads((R/'count_probe_result.json').read_text())['response']['answers']
fields={'measure':'the wording naming the financial or operating measure or business quantity for this forecast','value':'the stated forecast value or expectation, including direction, approximation and bounds, but excluding the measure name and target-period wording'}
qs={};selected={}
for tag in ['S0086','S0106']:
 n=int(counts[tag]['choice']);p=r['pieces'][tag];selected[tag]={'count':n,'count_p':counts[tag]['probabilities'][str(n)]}
 criteria={w['id']:w['text'] for w in p['words']}
 criteria.update({'elsewhere':'The required wording is elsewhere in the call, not in this sentence.','unclear':'Cannot identify this forecast or its field reliably.','none':'This forecast or field is not stated.'})
 for i in range(1,n+1):
  for field,desc in fields.items():
   for bound in ['first','last']:
    qs[f'{tag}_F{i}_{field}_{bound}']={'type':'choice','instructions':f'For forecast {i} of the {n} distinct current management forecasts in sentence [{tag}], ordered by their first appearance, select the {bound} source word of {desc}. Use the whole call to resolve meaning. Point to one contiguous source expression; otherwise select the applicable special option. Do not guess or repair the source.','criteria':criteria}
req={'state':r['state'],'questions':qs,'pieces':r['pieces'],'counts':selected,'note':'Diagnostic continuation on model counts, including uncertain counts. These are not accepted records.'}
(R/'ordinal_word_request.json').write_text(json.dumps(req,indent=2))
t=time.perf_counter()
try:out={**req,'response':L.decide(req['state'],qs,mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
except Exception as e:out={**req,'error':str(e),'seconds':time.perf_counter()-t}
ans=out.get('response',{}).get('answers',{});decoded=[]
for tag,c in selected.items():
 p=r['pieces'][tag];words={w['id']:w for w in p['words']}
 import re
 base=p['words'][0]['start']-re.search(r'\S+',p['sentence']).start()
 for i in range(1,c['count']+1):
  row={'sentence':tag,'ordinal':i,'count_p':c['count_p']}
  for field in fields:
   a=ans.get(f'{tag}_F{i}_{field}_first',{});b=ans.get(f'{tag}_F{i}_{field}_last',{});first=a.get('choice');last=b.get('choice')
   value={'first':first,'last':last,'first_p':a.get('probabilities',{}).get(first),'last_p':b.get('probabilities',{}).get(last)}
   if first in words and last in words and words[first]['start']<=words[last]['start']:
    value['span']=p['sentence'][words[first]['start']-base:words[last]['end']-base]
   row[field]=value
  decoded.append(row)
out['decoded']=decoded;(R/'ordinal_word_result.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'seconds':out['seconds'],'decoded':decoded,'usage':out.get('response',{}).get('usage'),'error':out.get('error')}),flush=True)
