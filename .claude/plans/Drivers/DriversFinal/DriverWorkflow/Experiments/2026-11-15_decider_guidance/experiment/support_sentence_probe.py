"""Test source-sentence support association, not final condition-field writing.
All guidance sentences selected by the frozen broad screen are examined; no keyword gate.
"""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115');import main_path_trial as T
b=json.loads((T.R/'B_result.json').read_text()); screen=json.loads((T.R/'shared_all_guidance_screen_result.json').read_text()); fields=json.loads((T.R/'expression_fields_request.json').read_text())
targets=[c for c in fields['targets'] if c['tag'] in ['F0','F1','F2','F3']]
ss=[s for s in b['sentences'] if screen['response']['answers'][s['tag']]['noul']>=.5]
rule=('SUPPORT_TASK: Does the specified sentence state an assumption, exclusion or dependency that qualifies the exact target forecast? Include expressly applicable shared guidance assumptions and measurement exclusions. A causal explanation, an actual result, a different forecast or a bare amount does not by itself establish such a qualification. Use the complete call to resolve scope and references; do not infer a condition merely because it is economically related. This identifies supporting evidence only. It does not label every matched word as a stored condition: assumptions and measurement qualifiers have different fields under the rules.\n\n')
state=rule+b['state']
for c in targets:state=state.replace('['+c['insert_at']+']','['+c['tag']+'] ['+c['insert_at']+']',1)
q={f'{c["tag"]}_{s["tag"]}':{'type':'noul','instructions':f'Does sentence [{s["tag"]}] meet SUPPORT_TASK for {c["text"]!r} at [{c["tag"]}]?'} for c in targets for s in ss}
# Written from the exact source and rules before running, not from model answers.
# Ambiguous relationship/scope cases remain unadjudicated rather than forced to a convenient key.
unadjudicated={'S69','S116','S123','S172','S175'}
ref=[]
for c in targets:
 for s in ss:
  label=None if s['tag'] in unadjudicated else (s['tag'] in {'S70','S71'} or (c['tag'] in {'F2','F3'} and s['tag'] in {'S16','S74'}))
  ref.append({'target':c['tag'],'sentence':s['tag'],'expected':label,'source_text':s['text'],'note':'Scope/qualification interpretation requires review; do not score as known truth.' if label is None else 'Source explicitly states a shared annual-guidance assumption or an EPS-only exclusion.' if label else 'No expressly applicable assumption/exclusion/dependency for this forecast; another amount, cause, result or forecast is not one by itself.'})
T.save('support_sentence_reference',{'rows':ref,'scope':'Four numeric annual forecasts; all 27 broad-screen sentences. Partial independent relation key, not complete records or complete transcript truth. No graph-policy change.'})
T.run('support_sentence',state,q,targets=targets,sentences=ss,note='Replaces a broad condition-presence/copy attempt with explicit source-sentence association for this diagnostic. No known measure names or expected labels in input; whole call visible. Tests shared/far evidence without approving a storage-policy change. Exact relation/key limitations saved separately.')
