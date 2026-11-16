"""Apply the same verified binding change to existing copy requests, with no other change."""
import json,re,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
R=T.R
cs={c['tag']:c for c in json.loads((R/'C_targets.json').read_text())}
for path in sorted(R.glob('C_copy_*_request.json')):
 d=json.loads(path.read_text())
 def bind(m):
  tag=m.group(1);c=cs[tag]
  return f"the source {'sentence' if c['kind']=='worded' else 'occurrence'} {c['text']!r} at [{tag}]"
 qs={k:{**q,'instructions':re.sub(r'\[([VS]\d+)\]',bind,q['instructions'])} for k,q in d['questions'].items()}
 name=path.name.removesuffix('_request.json')+'_literal'
 a=T.run(name,d['state'],qs,targets=d['targets'],note='Matched field-copying comparison: same context/options/grouping, only literal source text added beside target IDs.')
 print(json.dumps({'name':name,'nonempty':sum(bool(x['spans']) for x in a.values()),'questions':len(a),'fields':{k:[s['text'] for s in x['spans']] for k,x in a.items() if x['spans']}},ensure_ascii=False),flush=True)
