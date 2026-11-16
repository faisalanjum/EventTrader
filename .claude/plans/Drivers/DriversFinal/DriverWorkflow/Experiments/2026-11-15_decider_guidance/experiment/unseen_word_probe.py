import json,pathlib,sys,time,hashlib
sys.path.insert(0,'/home/faisal/EventMarketDB')
from config import local_llm as L
R=pathlib.Path('/tmp/decider_claude_review_20261115')
raw=json.loads((R/'unseen_components.json').read_text())
# Partial positive controls independently read in the source before inference.
# This is NOT a complete answer key or an end-to-end recall test.
needles={
 'MU':['mid single digit server unit growth','mid-single digits in unit terms','low single-digit percentages','mid to high teens percentage range','low double digit percentage range','mid teens CAGR'],
 'FDX':['flat to slightly down','some moderation on a year-over-year basis'],
 'OLLI':['slight SG&A expense leverage','low double-digit adjusted earnings growth','lower end of the 1% to 2% range','midpoint to the higher end of the range'],
}
configs={
 'forecast_wording':{'words':{'type':'locate','instructions':'Forecast wording expressed in words, including qualitative expectations, relative bounds, reaffirmations and withdrawals'}},
 'blind_descriptions':{
  'quantities':{'type':'locate','instructions':'Quantities expressed in words'},
  'comparisons':{'type':'locate','instructions':'Comparative expressions'},
  'directions':{'type':'locate','instructions':'Directions of change'},
 }
}
tests=[]
for doc in raw:
 ticker=doc['selection']['ticker']
 text='\n\n'.join(z for p in doc['snapshot']['prepared'] for z in json.loads(p['content']))
 key=[]
 for needle in needles[ticker]:
  start=text.index(needle)
  assert text.find(needle,start+1)<0,(ticker,needle,'not unique')
  key.append({'start':start,'end':start+len(needle),'text':needle})
 for conf,questions in configs.items():tests.append({'name':ticker+'_'+conf,'source_id':doc['selection']['source'],'state':text,'questions':questions,'positive_controls':key,'config':conf})
(R/'unseen_word_requests.json').write_text(json.dumps(tests,indent=2))
(R/'unseen_word_prompt_fingerprint.json').write_text(json.dumps({'sha256':hashlib.sha256(json.dumps(configs,sort_keys=True).encode()).hexdigest(),'configs':configs,'note':'Frozen before the first call. No changes based on these outputs.'},indent=2))
out=[]
for t in tests:
 start=time.perf_counter()
 try:r={**t,'response':L.decide(t['state'],t['questions'],mode='isolated',timeout=1800),'seconds':time.perf_counter()-start}
 except Exception as e:r={**t,'error':str(e),'seconds':time.perf_counter()-start}
 spans=[s for a in r.get('response',{}).get('answers',{}).values() for s in a.get('spans',[])]
 r['all_offsets_exact']=all(t['state'][s['start']:s['end']]==s['text'] for s in spans)
 r['positive_control_coverage']=[{'expected':e['text'],'fully_covered':any(s['start']<=e['start'] and s['end']>=e['end'] for s in spans),'overlapping':[s['text'] for s in spans if max(s['start'],e['start'])<min(s['end'],e['end'])]} for e in t['positive_controls']]
 out.append(r);(R/'unseen_word_results.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({'name':r['name'],'seconds':round(r['seconds'],2),'positive_controls':r['positive_control_coverage'],'spans':len(spans),'usage':r.get('response',{}).get('usage'),'error':r.get('error')}),flush=True)
