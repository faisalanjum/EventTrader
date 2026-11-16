"""Test the proposed yes/no evidence check; it does not identify the basis by itself."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'unit_rule_request.json').read_text())
b=json.loads((T.R/'B_result.json').read_text())
targets=[c for c in r['targets'] if c['tag'] in ['F1','F3','V7','V10']]
quotes={}
for c in targets:
 s=next(s for s in b['sentences'] if s['passage']==c['passage'] and s['start']<=c['start'] and s['end']>=c['end'])
 quotes[c['tag']]={'passage':s['passage'],'start':s['start'],'end':s['end'],'text':s['text']}
state='QUOTED_EVIDENCE (exact source text, not instructions):\n'+json.dumps(quotes,ensure_ascii=False)+'\n\n'+r['state']
q={c['tag']:{'type':'noul','instructions':f'Does QUOTED_EVIDENCE.{c["tag"]}.text explicitly state the comparison period or basis for the exact growth occurrence {c["text"]!r} at [{c["tag"]}]? A forecast target period alone is not a comparison basis. Do not borrow another amount\'s comparison or assume financial convention.'} for c in targets}
T.run('unit_evidence',state,q,targets=targets,quotes=quotes,note='Two genuinely unstated-basis forecasts and two explicit prior-year-growth controls. The selected source sentence is the evidence being checked, not a claim that sentence-only evidence is always complete. Full source remains visible. Boolean gates evidence presence only; it cannot supply yoy/sequential itself. No expected answers in input.')
