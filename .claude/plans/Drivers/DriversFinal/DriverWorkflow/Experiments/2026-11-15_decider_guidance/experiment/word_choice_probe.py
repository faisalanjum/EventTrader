import json,pathlib,sys,time,re,hashlib
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
raw=json.loads((R/'unseen_sentence_requests.json').read_text())
# Target positions are diagnostic fixtures, not run-time routing rules; no expected field text enters requests.
targets={'MU':['S0051','S0085','S0131'],'FDX':['S0168','S0157','S0025'],'OLLI':['S0086','S0106','S0053']}
requests=[]
fields={'measure':'the wording naming the financial or operating measure or business quantity forecast or qualified by management in this sentence', 'value':'the stated forecast value or expectation, including words establishing its direction, approximation or bounds, but excluding the measure name and target-period wording'}
for r in raw:
 state=r['state'];marks=[];qs={};pieces={}
 for s in r['sentences']:
  if s['tag'] not in targets[r['name']]:continue
  base=state.index('['+s['tag']+'] ')+len(s['tag'])+3
  assert state[base:base+len(s['text'])]==s['text']
  words=[]
  for i,m in enumerate(re.finditer(r'\S+',s['text'])):
   wid=f'{s["tag"]}W{i:03d}'
   words.append({'id':wid,'text':m.group(),'start':base+m.start(),'end':base+m.end()})
   marks.append((base+m.start(),wid))
  assert len(words)+4<=255
  pieces[s['tag']]={'sentence':s['text'],'words':words}
  criteria={w['id']:w['text'] for w in words}
  criteria.update({'elsewhere':'Required wording is elsewhere in the transcript, not in this sentence.','several':'There are several distinct eligible forecasts/expressions; no single answer covers them.','none':'No eligible management guidance or no such field is stated.','unclear':'The field or its boundaries cannot be established from the source.'})
  for field,desc in fields.items():
   for bound in ['first','last']:
    qs[f'{s["tag"]}_{field}_{bound}']={'type':'choice','instructions':f'For sentence [{s["tag"]}], select the {bound} source word of {desc}. Use the full call to resolve meaning. Select a word ID only if this is one clear, contiguous expression; otherwise select the applicable special option. Do not guess or repair the source.','criteria':criteria}
 for pos,tag in sorted(marks,reverse=True):state=state[:pos]+f'[{tag}] '+state[pos:]
 requests.append({'name':r['name'],'state':state,'questions':qs,'pieces':pieces})
(R/'word_choice_requests.json').write_text(json.dumps(requests,indent=2))
out=[]
for q in requests:
 t=time.perf_counter()
 try:r={**q,'response':L.decide(q['state'],q['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**q,'error':str(e),'seconds':time.perf_counter()-t}
 ans=r.get('response',{}).get('answers',{});result=[]
 for tag,p in q['pieces'].items():
  for field in fields:
   a=ans.get(f'{tag}_{field}_first',{});b=ans.get(f'{tag}_{field}_last',{});words={w['id']:w for w in p['words']};first=a.get('choice');last=b.get('choice')
   entry={'sentence':tag,'field':field,'first':first,'last':last,'first_p':a.get('probabilities',{}).get(first),'last_p':b.get('probabilities',{}).get(last)}
   if first in words and last in words and words[first]['start']<=words[last]['start']:
    base=p['words'][0]['start'];entry['span']=p['sentence'][words[first]['start']-base:words[last]['end']-base]
   result.append(entry)
 r['decoded']=result;out.append(r);(R/'word_choice_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'decoded':result,'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
