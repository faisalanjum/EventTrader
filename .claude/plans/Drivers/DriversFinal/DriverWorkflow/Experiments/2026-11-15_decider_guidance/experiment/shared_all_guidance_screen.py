"""One sentence question for all guidance; no numeric-only exclusion or new repair call."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'shared_role_population_request.json').read_text())
b=json.loads((T.R/'B_result.json').read_text())
state=('SENTENCE_TASK (task definition, not source evidence): Decide whether the specified sentence states, reaffirms, withdraws or qualifies management guidance under the supplied definition, whether numeric or expressed in words. Use the whole call to resolve references and management confirmation.\n\n'+r['state'])
q=dict(r['questions'])
for s in b['sentences']:
 q[s['tag']]={'type':'noul','instructions':f'Does sentence [{s["tag"]}] meet SENTENCE_TASK?'}
T.run('shared_all_guidance_screen',state,q,candidates=b['candidates'],sentences=b['sentences'],note='Same complete call and all 120 numeric role questions as shared_role_population, plus one broad guidance/qualification noul for each of the 213 sentences in retained passages. Exact grouping changed and must be re-scored. No hidden answer key in inputs; positive sentence is coverage evidence, not a record or a contradiction with every negative number role.')
