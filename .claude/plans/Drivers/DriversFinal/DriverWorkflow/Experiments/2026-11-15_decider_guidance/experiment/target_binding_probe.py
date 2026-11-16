"""Matched requests: tag alone vs literal + tag. Separate calls avoid indirect cross-question leakage."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
b=json.loads((T.R/'B_result.json').read_text())
cs=[c for c in b['candidates'] if c['passage']=='PR002' or c['tag'] in ['V58','V59','V60','V61']]
answers={}
for arm in ['tag_only','literal_tag']:
 q={}
 for c in cs:
  original=b['questions'][c['tag']]
  q[c['tag']]=original if arm=='tag_only' else {**original,'instructions':f"What role does the exact source occurrence {c['text']!r} immediately following [{c['tag']}] have under the guidance definition? Resolve meaning using the entire call."}
 answers[arm]=T.run('binding_'+arm,b['state'],q,candidates=cs,note='Same source, candidate set, order, options and runtime; separate requests differ only in target wording. Development controls, not a whole-call benchmark.')
rows=[]
for c in cs:
 row={'tag':c['tag'],'text':c['text'],'passage':c['passage']}
 for arm in ['tag_only','literal_tag']:
  a=answers[arm][c['tag']];row[arm]={'choice':a['choice'],'p':a['probabilities'][a['choice']]}
 rows.append(row)
T.save('binding_pair_summary',rows)
print(json.dumps(rows,indent=2),flush=True)
