"""Read-only accounting of the frozen experiment; no inference or baseline edits."""
import collections, hashlib, json, pathlib
root=pathlib.Path('/tmp/decider_claude_review_20261115');r=root/'main_path'
names=['A_result.json','B_result.json','B_selection.json','C_targets.json','C_copy_targets.json','C_choices_result.json','E_proposals.json']
d={n:json.loads((r/n).read_text()) for n in names}
b=d['B_result.json'];selected=d['B_selection.json'];c={x['tag']:x for x in d['C_targets.json']}
cp={x['tag'] for x in d['C_copy_targets.json']};e={x['tag']:x for x in d['E_proposals.json']['proposals']}
assert set(c)==set(e)
bs={x['tag'] for values in selected.values() for x in values}
rows=[]
for kind,items in [('numeric',b['candidates']),('sentence',b['sentences'])]:
 for x in items:
  tag=x['tag'];a=b['response']['answers'][tag]
  row=dict(tag=tag,kind=kind,passage=x['passage'],text=x['text'],raw_answer=a)
  if tag in e:
   row.update(outcome=e[tag]['status'],reasons=e[tag]['reasons'],copied=tag in cp)
  elif tag not in bs:
   row.update(outcome='not_selected_by_B',reasons=['numeric_role_not_current_qualification_unclear' if kind=='numeric' else 'sentence_probability_below_0.25'])
  elif kind=='numeric':
   row.update(outcome='not_advanced_to_C',reasons=['unclear_numeric_role' if a['choice']=='unclear' else 'selected_numeric_role_probability_below_0.5'])
  else:
   row.update(outcome='not_advanced_to_C',reasons=['sentence_probability_0.25_to_below_0.5'])
  rows.append(row)
assert len(rows)==len({x['tag'] for x in rows})==len(b['questions'])
summary=dict(targets=len(rows),outcomes=dict(collections.Counter(x['outcome'] for x in rows)),
 not_advanced_reasons=dict(collections.Counter(y for x in rows if x['outcome']=='not_advanced_to_C' for y in x['reasons'])),
 no_copy_but_recorded=[dict(tag=t,form=e[t]['choices']['form']['choice'],outcome=e[t]['status']) for t in c if t not in cp])
out=dict(summary=summary,rows=rows,inputs_sha256={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names},
 note='Reconstructed diagnostic routing, not a production outcome writer or semantic correctness judgment. C form skips were retained by E; earlier threshold removals lacked a consolidated outcome/reason. Raw responses were preserved.')
(root/'final_review_item8_audit.json').write_text(json.dumps(out,indent=2)+'\n')
with (root/'progress.md').open('a') as f:f.write('\nTest: Independently audit final-review item 8 against frozen B/C/E code and all 333 source targets.\nResult: '+json.dumps(summary)+'. No new model calls or baseline changes; this is accounting, not extraction recall.\nNext: Accept explicit outcomes for earlier filtering, but correct the claim that several/form rejects vanish: E already records all C targets.\n')
print(json.dumps(summary,indent=2))
