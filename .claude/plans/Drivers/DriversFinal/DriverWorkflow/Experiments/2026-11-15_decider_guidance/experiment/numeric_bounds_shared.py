"""Matched controls; put repeated task/option definitions once in state. No answer key input."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'numeric_bounds_request.json').read_text())
special={k:v for k,v in next(iter(r['questions'].values()))['criteria'].items() if not (k.startswith('V') and k[1:].isdigit())}
rule=('For the current management forecast containing the target, select the requested lower or upper value. '
'A point forecast uses the same occurrence for both values; a closed range uses its two stated endpoints; '
'a one-sided bound leaves the other side unstated. Resolve using the whole call. '
'If this occurrence is not a current forecast amount, choose no_current_forecast; '
'never substitute another forecast or calculate an unstated amount.')
state='BOUND_SELECTION_RULES (task instructions, not source evidence):\n'+rule+'\nAlternative meanings:\n'+json.dumps(special,ensure_ascii=False)+'\n\n'+r['state']
q={}
for c in r['targets']:
 for side in ['lower','upper']:
  k=c['tag']+'_'+side
  q[k]={'type':'choice','instructions':f'For the exact source occurrence {c["text"]!r} at [{c["tag"]}], select its {side} value under BOUND_SELECTION_RULES.','criteria':{k:None for k in r['questions'][k]['criteria']}}
T.run('numeric_bounds_shared',state,q,targets=r['targets'],note='Same 25 controls, exact options/order, and rules as numeric_bounds; repeated task and special-option definitions appear once in state; numeric source text is already tagged. Questions retain exact target literal and visible ID. No expected answers in input.')
