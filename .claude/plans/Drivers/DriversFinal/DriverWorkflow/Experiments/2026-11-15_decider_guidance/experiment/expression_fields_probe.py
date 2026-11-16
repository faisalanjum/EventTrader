"""Replace per-endpoint field targets with source spans established by model-selected bounds.
Exact same occurrence grouping is not final fact deduplication; preserve all anchor aliases.
"""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'literal_numeric_fields_request.json').read_text())
b=json.loads((T.R/'B_result.json').read_text())
bounds=json.loads((T.R/'numeric_bounds_shared_result.json').read_text())['response']['answers']
byid={c['tag']:c for c in b['candidates']}; ps={p['id']:p['text'] for p in T.source['passages']}
spans={}
for c in r['targets']:
 keys=[bounds[c['tag']+'_'+side]['choice'] for side in ['lower','upper']]
 if not all(k in byid for k in keys):continue
 cs=[byid[k] for k in keys]
 assert len({x['passage'] for x in cs})==1
 start=min(x['start'] for x in cs);end=max(x['end'] for x in cs);pid=cs[0]['passage']
 key=(pid,start,end)
 if key not in spans:
  first=min(cs,key=lambda x:x['start'])
  spans[key]={'tag':'F'+str(len(spans)),'passage':pid,'start':start,'end':end,'text':ps[pid][start:end],'aliases':[],'insert_at':first['tag']}
 spans[key]['aliases'].append(c['tag'])
state=r['state'];questions={}
first=r['targets'][0]['tag']; templates={k[len(first)+1:]:q for k,q in r['questions'].items() if k.startswith(first+'_')}
for c in spans.values():
 marker='['+c['insert_at']+']';assert state.count(marker)==1
 state=state.replace(marker,'['+c['tag']+'] '+marker,1)
 for f,q in templates.items():
  questions[c['tag']+'_'+f]={**q,'instructions':f'For the exact source occurrence {c["text"]!r} at [{c["tag"]}], answer {f} using FIELD_RULES.'}
T.run('expression_fields',state,questions,targets=list(spans.values()),note='Same field definitions/options as literal_numeric_fields; model-selected numeric boundaries define exact candidate source spans. Exact duplicate span questions grouped, original anchor aliases preserved. Not final record merging; several forecasts must still be identified or held. No gold measures, units, periods or other expected fields supplied.')
