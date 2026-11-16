import json,pathlib,sys,time,hashlib,os
R=pathlib.Path('/tmp/decider_claude_review_20261115')
sys.path[:0]=['/home/faisal/EventMarketDB',str(R/'vendor')]
from config import local_llm as L
import pysbd
seg=pysbd.Segmenter(language='en',clean=False,char_span=True)
raw=json.loads((R/'unseen_components.json').read_text())
old=json.loads((R/'unseen_word_requests.json').read_text())
definition="Guidance is a specific financial or operating forecast, target or outlook stated or clearly confirmed by company management. Include numerical and meaningful qualitative forecasts, reaffirmations, withdrawals, and qualifications that change a forecast's meaning. Exclude actual results, merely recalled old forecasts, analyst-only estimates, vague optimism and boilerplate. A hypothetical illustration is not a committed forecast. Resolve references using the entire call; do not invent missing facts."
reqs=[]
for d in raw:
 ps=[z for p in d['snapshot']['prepared'] for z in json.loads(p['content'])]
 passages=[{'text':z,'prepared':True} for z in ps]
 passages.extend({'text':'\n'.join(e['text'] for e in json.loads(q['exchanges'])),'prepared':False} for q in sorted(d['snapshot']['qa'],key=lambda q:int(q['sequence'])))
 sentences=[]; rendered=[]
 for pi,p in enumerate(passages):
  text=p['text']; spans=seg.segment(text);last=0;body=[]
  for sp in spans:
   assert text[sp.start:sp.end]==sp.sent and sp.start>=last and not text[last:sp.start].strip()
   tag=f'S{len(sentences):04d}'
   sentences.append({'tag':tag,'passage':pi,'text':sp.sent,'start_in_passage':sp.start,'end_in_passage':sp.end,'prepared':p['prepared']})
   body.extend([text[last:sp.start],f'[{tag}] ',sp.sent]);last=sp.end
  assert not text[last:].strip()
  body.append(text[last:]);rendered.append(f'[P{pi:03d}] '+''.join(body))
 state=definition+'\n\n'+'\n\n'.join(rendered)
 questions={s['tag']:{'type':'noul','instructions':f"Under the supplied definition, does sentence [{s['tag']}] state or qualify management guidance elsewhere in this transcript? Use the whole call to resolve references; an analyst's question needs management confirmation."} for s in sentences if s['prepared']}
 controls=next(r['positive_controls'] for r in old if r['name']==d['selection']['ticker']+'_forecast_wording')
 matched=[]
 for c in controls:
  hits=[s for s in sentences if s['prepared'] and c['text'] in s['text']]
  assert len(hits)==1,(c,hits)
  matched.append({'text':c['text'],'tag':hits[0]['tag']})
 reqs.append({'name':d['selection']['ticker'],'state':state,'questions':questions,'sentences':sentences,'positive_controls':matched})
(R/'unseen_sentence_requests.json').write_text(json.dumps(reqs,indent=2))
(R/'unseen_sentence_prompt_fingerprint.json').write_text(json.dumps({'definition':definition,'question_template':"Under the supplied definition, does sentence [S] state or qualify management guidance elsewhere in this transcript? Use the whole call to resolve references; an analyst's question needs management confirmation.",'package':'pysbd==0.3.4','mode':'isolated'},indent=2))
# Do not run concurrent inference with the preceding diagnostic.
while True:
 try:os.kill(2914283,0)
 except ProcessLookupError:break
 time.sleep(2)
out=[]
for q in reqs:
 t=time.perf_counter()
 try:r={**q,'response':L.decide(q['state'],q['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-t}
 except Exception as e:r={**q,'error':str(e),'seconds':time.perf_counter()-t}
 ans=r.get('response',{}).get('answers',{})
 r['positive_control_results']=[{**c,'p':ans.get(c['tag'],{}).get('noul')} for c in q['positive_controls']]
 out.append(r);(R/'unseen_sentence_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':q['name'],'questions':len(q['questions']),'seconds':round(r['seconds'],2),'controls':r['positive_control_results'],'flagged_at_half':sum(a.get('noul',0)>=.5 for a in ans.values()),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
