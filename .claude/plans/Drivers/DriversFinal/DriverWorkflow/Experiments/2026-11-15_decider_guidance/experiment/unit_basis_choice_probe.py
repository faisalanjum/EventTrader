"""Matched bounded comparison: evidence presence + basis in one choice, same source state."""
import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'unit_evidence_request.json').read_text())
criteria={
 'year_earlier':'The quote explicitly compares this growth with the same period a year earlier.',
 'previous_period':'The quote explicitly compares this growth with the immediately preceding comparable period (sequential).',
 'two_bases':'This exact expression explicitly gives distinct year-earlier and sequential comparisons; both need preserving.',
 'other_stated':'A different comparison is explicitly stated; it cannot be relabelled year-earlier or sequential.',
 'not_stated':'The quote does not establish a comparison basis for this exact growth occurrence. A forecast target year or period alone does not establish one.',
 'unclear':'Potential comparison wording is present, but the quote does not settle which growth occurrence or basis it applies to.'}
q={c['tag']:{'type':'choice','instructions':f'Which comparison basis does QUOTED_EVIDENCE.{c["tag"]}.text explicitly establish for the exact growth occurrence {c["text"]!r} at [{c["tag"]}]? Do not borrow another amount\'s comparison or assume financial convention.','criteria':criteria} for c in r['targets']}
T.save('unit_basis_choice_reference',{'F1':'not_stated','F3':'not_stated','V7':'year_earlier','V10':'year_earlier'})
T.run('unit_basis_choice',r['state'],q,targets=r['targets'],quotes=r['quotes'],note='Same state and four target quotes as evidence-presence test; one choice combines presence and basis identity. Native type/options only. No expected answers in model state. Whole call remains visible. Full quote construction and scope not proved by this fixture.')
