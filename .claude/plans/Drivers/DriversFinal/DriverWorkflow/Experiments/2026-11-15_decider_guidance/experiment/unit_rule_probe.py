"""One direct test of the explicit rulebook growth-basis rule, with real positive controls."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'expression_fields_request.json').read_text())
b=json.loads((T.R/'B_result.json').read_text())
controls=[c for c in b['candidates'] if c['tag'] in ['V7','V10','V4','V5','V77','V78']]
# Values are source-only fixtures; expected units live in a separate scoring file.
targets=r['targets']+controls
state=('UNIT_RULE_3_33 (task rule): For growth, use percent_yoy or percent_sequential only when the quote establishes the comparison basis for THIS amount. An annual target period alone does not establish it. Without that evidence choose unknown. Never use plain percent for growth. A percentage LEVEL remains percent. Points or basis points take precedence over year-over-year/sequential wording. Do not borrow another figure\'s comparison basis.\n\n'+r['state'])
criteria=r['questions']['F0_unit_scale']['criteria'];qs={c['tag']:{'type':'choice','instructions':f'For the exact source occurrence {c["text"]!r} at [{c["tag"]}], choose unit_scale using FIELD_RULES and UNIT_RULE_3_33.','criteria':criteria} for c in targets}
T.run('unit_rule',state,qs,targets=targets,note='Clarifies the existing rule 3.33, not a new rule or company heuristic. Includes all six established numeric expression targets and six real source unit controls (explicit yearly growth, percentage levels and basis points). No expected units in input. Different grouping from previous field run; not an isolated causal comparison.')
