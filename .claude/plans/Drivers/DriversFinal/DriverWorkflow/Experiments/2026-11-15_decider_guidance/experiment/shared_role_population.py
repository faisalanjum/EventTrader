"""All numeric seeds from the fixed development call's retained passages; no answer key input."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'B_result.json').read_text())
roles=next(q['criteria'] for q in r['questions'].values() if q['type']=='choice')
state='NUMERIC_ROLES (task definitions, not source evidence):\n'+json.dumps(roles,ensure_ascii=False)+'\n\n'+r['state']
questions={c['tag']:{'type':'choice','instructions':f'What is the role of the exact source occurrence {c["text"]!r} at [{c["tag"]}] under NUMERIC_ROLES? Use the whole call.','criteria':{k:None for k in roles}} for c in r['candidates']}
T.run('shared_role_population',state,questions,candidates=r['candidates'],note='All 120 numeric seeds in all ten retained passages; no subset chosen by expected values. Shared role definitions and literal-plus-ID questions. Numeric seeds are not complete records; no worded-fact recall claim.')
