"""One bounded test of source sentence selection before short extractive QA.
No known measure names or expected sentence IDs enter the request.
"""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115');import main_path_trial as T
b=json.loads((T.R/'B_result.json').read_text())
screen=json.loads((T.R/'shared_all_guidance_screen_result.json').read_text())
f=json.loads((T.R/'expression_fields_request.json').read_text())['targets']
aliases={v for x in f for v in x['aliases']}
targets=list(f)+[c for c in b['candidates'] if c['tag'] not in aliases and screen['response']['answers'][c['tag']]['choice'] in ['current','qualification','unclear']]
# Previously discussed worded qualifier, selected by the frozen all-guidance screen.
word=next(s for s in b['sentences'] if s['tag']=='S212')
assert screen['response']['answers']['S212']['noul']>=.5
targets.append(word)
state='MEASURE_POINTER_RULE (task instruction): Select the source sentence that explicitly names the financial or operating measure for the exact target occurrence. Resolve references with the whole call. A number, unit, date, pronoun or vague reference alone is not a measure name. Analyst wording may be used only when management clearly confirms the claim. A different business segment\'s measure is not interchangeable. This selects evidence, not a canonical name or a final fact.\n\n'+b['state']
for x in f:state=state.replace('['+x['insert_at']+']','['+x['tag']+'] ['+x['insert_at']+']',1)
q={}
for c in targets:
 ss=[s for s in b['sentences'] if (s['passage'].startswith('PR') if c['passage'].startswith('PR') else s['passage']==c['passage'])]
 options={s['tag']:None for s in ss}
 options.update({'none':'No source wording establishes the measure.','elsewhere':'The naming sentence is outside these options.','several':'Several naming sentences are required; one is not enough.','unclear':'The source does not settle which measure belongs to this occurrence.'})
 assert len(options)<=255
 q[c['tag']]={'type':'choice','instructions':f'Which sentence explicitly names the measure for {c["text"]!r} at [{c["tag"]}], under MEASURE_POINTER_RULE?','criteria':options}
T.run('measure_pointer',state,q,targets=targets,note='Frozen all-guidance numeric work candidates; six existing identical-bound expressions replace their duplicate endpoints, keeping aliases. All other retained numeric candidates included, plus previously retained worded S212. Source-only sentence menus, no metric names. Full call visible; complete prepared remarks or complete local exchange supplies options. New mechanism test, not another broad Locate wording repair.')
