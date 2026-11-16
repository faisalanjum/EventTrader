"""Mechanical scoring and exact-source reconstruction, not a semantic judge."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'prepared_record'
prefix = sys.argv[1] + '_' if len(sys.argv) > 1 else ''
request = json.loads((OUT / (prefix + 'request.json')).read_text())
result = json.loads((OUT / (prefix + 'result.json')).read_text())
reference = json.loads((OUT / 'reference.json').read_text())
source = json.loads((OUT / 'source_map.json').read_text())
answers = result['response']['answers']
assert set(answers) == set(request['questions'])
rows = []
for qid, expected in reference['expected_choices'].items():
    a = answers[qid]
    observed = a['choice']
    after = observed
    if qid.endswith('_unit_scale') and observed in ['percent_yoy', 'percent_sequential']:
        basis = answers[qid.split('_', 1)[0] + '_basis_evidence']['choice']
        if basis == 'not_stated':
            after = 'unknown'
    rows.append({'id': qid, 'expected': expected, 'raw': observed,
                 'after_3_33_absence_rule': after, 'raw_correct': observed == expected,
                 'correct_after_rule': after == expected,
                 'probability': a['probabilities'][observed]})
mapped = {}
for qid, question in request['questions'].items():
    if question['type'] != 'locate':
        continue
    copies = []
    for span in answers[qid]['spans']:
        assert request['state'][span['start']:span['end']] == span['text']
        positions = [i for i in source['mapping'][span['start']:span['end']] if i is not None]
        if not positions:
            copies.append({'returned': span, 'error': 'not_source_evidence'})
            continue
        assert positions == sorted(positions)
        a, z = min(positions), max(positions) + 1
        copies.append({'returned': span, 'source_start': a, 'source_end': z,
                       'source_text': source['prepared_quote'][a:z],
                       'unmapped_characters': sum(x is None for x in source['mapping'][span['start']:span['end']])})
    mapped[qid] = copies
proposals = json.loads((ROOT / 'assembled_proposals/reconciled.json').read_text())['proposals']
for proposal in proposals:
    tag = proposal['target']
    proposal['field_choices'] = {k[len(tag) + 1:]: a for k, a in answers.items()
                                 if k.startswith(tag + '_') and a['type'] == 'choice'}
    proposal.pop('proposed_fields')
    proposal['continuous_quote'] = {'source_start': 0, 'source_end': len(source['prepared_quote']),
                                    'text': source['prepared_quote']}
    proposal['modifier_copies'] = mapped[tag + '_modifiers']
    proposal['condition_copies'] = mapped[tag + '_conditions']
    proposal['outcome'] = 'requires_source_semantic_review'
    proposal['limits'] = 'New field/copy run; earlier model-selected discovery/bounds/measures retained. Full record correctness unproved.'
summary = {'choice_count': len(rows), 'raw_correct': sum(r['raw_correct'] for r in rows),
           'correct_after_absence_rule': sum(r['correct_after_rule'] for r in rows),
           'copy_questions': len(mapped), 'copy_spans': sum(len(v) for v in mapped.values()),
           'invalid_copy_spans': sum('error' in x for v in mapped.values() for x in v),
           'seconds': result['seconds'], 'usage': result['response'].get('usage'),
           'model': result['response'].get('model'),
           'complete_record_score': None}
artifact = {'summary': summary, 'choice_rows': rows, 'copies': mapped, 'proposals': proposals,
            'request_sha256': hashlib.sha256((OUT / (prefix + 'request.json')).read_bytes()).hexdigest(),
            'source_text_sha256': source['source_text_sha256'],
            'note': 'Exact copies and correct choices do not establish complete records. Conditions and modifiers require independent source review.'}
(OUT / (prefix + 'review.json')).write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
print(json.dumps(summary, indent=2))
for row in rows:
    if not row['correct_after_rule']:
        print(json.dumps(row))
for qid, spans in mapped.items():
    print(qid, json.dumps([{'text': s.get('source_text'), 'error': s.get('error'),
                           'score': s['returned']['score']} for s in spans], ensure_ascii=False))
with (ROOT / 'progress.md').open('a') as f:
    f.write(f'\nTest: Reconstruct {prefix or "original "}complete-prepared-block field outputs and compare choices with the frozen six-target reference.\n')
    f.write(f'Result: {summary["raw_correct"]}/{summary["choice_count"]} raw choices; {summary["correct_after_absence_rule"]} after the existing absence rule; {summary["copy_spans"]} copied spans, {summary["invalid_copy_spans"]} outside source. Full-record semantic review pending.\n')
    f.write('Next: Review all copied conditions/qualifiers and whole proposals; field counts are not a readiness score.\n')
