import json,pathlib,sys,time
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
s=next(x for x in json.loads((R/'sources.json').read_text()) if x['id']=='CTAS_2026-03-25T10.00')
prior=json.loads((R/'source_names_choices_results.json').read_text())
values=next(x for x in json.loads((R/'tagged_requests.json').read_text()) if x['name']=='cintas_tagged_fields')['occurrences']
marks=list(values);groups={};i=0
for pid,tag in [('QA016','V001'),('QA022','V002')]:
 p=next(x for x in s['passages'] if x['id']==pid)
 base=s['text'].index(p['text'])
 r=next(x for x in prior if x['name']=='source_names_'+pid)
 groups[tag]=[]
 for sp in r['response']['answers']['names']['spans']:
  # All returned name spans precede the inserted V tag in these test passages.
  a,b=base+sp['start'],base+sp['end']
  assert s['text'][a:b]==sp['text']
  i+=1;m={'tag':f'M{i:03d}','start':a,'end':b,'text':sp['text']}
  marks.append(m);groups[tag].append(m)
state=s['text']
for m in sorted(marks,key=lambda x:(x['start'],x['tag']),reverse=True):
 state=state[:m['start']]+f"[{m['tag']}] "+state[m['start']:]
questions={}
for v in values:
 criteria={m['tag']:f"The occurrence [{m['tag']}] of '{m['text']}' in this transcript." for m in groups[v['tag']]}
 criteria.update({'several':'Several distinct measures are forecast by this expression.','none':'None of these occurrences names the applicable measure.','unclear':'The measure or its scope cannot be established.'})
 questions[v['tag']+'_choose']={'type':'choice','instructions':f"Which tagged occurrence identifies what is being forecast or qualified by [{v['tag']}]? Match the actual measure and business scope using the full transcript. A number, unit or period alone does not identify a measure. Analyst wording is usable only when management supports that meaning.",'criteria':criteria}
 for m in groups[v['tag']]:
  questions[v['tag']+'_'+m['tag']]={'type':'noul','instructions':f"Does the occurrence [{m['tag']}] identify what is being measured, and does [{v['tag']}] forecast or qualify that same measure for the same business scope, as management states or clearly confirms? Answer no if [{m['tag']}] only gives a number, unit or period, or concerns a different business scope. Use the whole transcript as context."}
req={'state':state,'questions':questions,'marks':marks}
(R/'measure_occurrences_request.json').write_text(json.dumps(req,indent=2))
t=time.perf_counter()
try:r={**req,'response':L.decide(state,questions,mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
except Exception as e:r={**req,'error':str(e),'seconds':time.perf_counter()-t}
(R/'measure_occurrences_results.json').write_text(json.dumps(r,indent=2))
print(json.dumps({'seconds':r['seconds'],'answers':r.get('response',{}).get('answers'),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
