"""Test remaining typed fields on actual role-positive numeric occurrences; no expected fields supplied."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'C_choices_request.json').read_text())
b=json.loads((T.R/'binding_literal_tag_result.json').read_text())
targets=[c for c in b['candidates'] if b['response']['answers'][c['tag']]['choice']=='current' and b['response']['answers'][c['tag']]['probabilities']['current']>=.5]
first=r['targets'][0]['tag'];field_rules={};qs={}
for qid,q in r['questions'].items():
 if qid.startswith(first+'_'):
  field=qid[len(first)+1:]
  field_rules[field]={'instructions':q['instructions'].replace('For the source target ['+first+'], ','').replace('['+first+']','the target'), 'type':q['type']}
  if q['type']=='choice':field_rules[field]['criteria']=q['criteria']
state='FIELD_RULES (task instructions, not source evidence):\n'+json.dumps(field_rules,ensure_ascii=False)+'\n\n'+r['state']
for c in targets:
 for f,q in field_rules.items():
  v={'type':q['type'],'instructions':f'For the exact source occurrence {c["text"]!r} at [{c["tag"]}], answer {f} using FIELD_RULES.'}
  if q['type']=='choice':v['criteria']={k:None for k in q['criteria']}
  qs[c['tag']+'_'+f]=v
T.run('literal_numeric_fields',state,qs,targets=targets,note='All ten actual current-amount outputs of binding_literal_tag, selected without answer key; represents six numeric forecasts, not ten records. Original field definitions/options retained once in shared state; exact target text and ID in each question. No field values or expected measure names in input.')
