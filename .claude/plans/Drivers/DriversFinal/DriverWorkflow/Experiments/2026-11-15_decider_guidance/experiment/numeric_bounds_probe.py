"""Code already owns exact numeric occurrences: choose their roles; do not ask Locate to recopy them."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
R=T.R
b=json.loads((R/'B_result.json').read_text())
controls=json.loads((R/'binding_literal_tag_result.json').read_text())['candidates']
qs={}
for c in controls:
 opts={x['tag']:f"{x['text']!r} in [{x['passage']}]" for x in b['candidates'] if x['passage']==c['passage']}
 opts.update({'no_current_forecast':'This occurrence is only an actual, earlier forecast, date, identifier or unconfirmed estimate, not a current management forecast amount.', 'no_stated_bound':'This forecast has no explicitly stated bound on this side.','elsewhere':'The required amount is elsewhere in the source, outside these options.','several':'Several distinct forecasts are inseparable here.','unclear':'The source does not establish the requested bound.'})
 assert len(opts)<=255
 ref=f"the exact source occurrence {c['text']!r} at [{c['tag']}]"
 for side in ['lower','upper']:
  qs[c['tag']+'_'+side]={'type':'choice','instructions':f'For the current management forecast containing {ref}, select its {side} value. A point forecast uses the same occurrence for both values; a closed range uses its two stated endpoints; a one-sided bound leaves the other side unstated. Resolve using the whole call. If this occurrence is not a current forecast amount, choose no_current_forecast; never substitute another forecast or calculate an unstated amount.','criteria':opts}
ans=T.run('numeric_bounds',b['state'],qs,targets=controls,note='All 25 prior controls including negatives; candidate menus contain every numeric occurrence in the complete local passage, not just forecast positives. No expected bounds or names in input.')
rows=[]
for c in controls:
 row={k:c[k] for k in ['tag','text','passage']}
 for side in ['lower','upper']:
  a=ans[c['tag']+'_'+side];row[side]={'choice':a['choice'],'p':a['probabilities'][a['choice']]}
 rows.append(row)
T.save('numeric_bounds_summary',rows)
print(json.dumps(rows,indent=2),flush=True)
