"""Check one rule-specific choice in the existing full-call field batch.
No selected evidence is supplied. Preserve all raw choices; score the narrow
3.33 absence rule separately from full records and from other disagreements.
"""
import json
import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/faisal/EventMarketDB')
from config import local_llm as L

ROOT = pathlib.Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'quote_fields'
request = json.loads((OUT / 'whole_call_request.json').read_text())
targets = json.loads((ROOT / 'main_path/expression_fields_request.json').read_text())['targets']
base = json.loads((ROOT / 'main_path/B_result.json').read_text())
controls = [c for c in base['candidates'] if c['tag'] in ['V7', 'V10']]
options = {
    'year_earlier': 'This is percentage growth explicitly compared with the same period one year earlier.',
    'previous_period': 'This is percentage growth explicitly compared with the immediately preceding comparable period.',
    'two_bases': 'Distinct year-earlier and sequential growth bases are explicitly stated; both need preserving.',
    'other_stated': 'This is percentage growth with a different explicitly stated comparison, not year-earlier or sequential.',
    'not_stated': 'This is percentage growth, but the source does not establish its comparison basis. A target fiscal year alone does not establish one.',
    'not_growth_percentage': 'The target is not a percentage-growth amount. A money amount, percentage level, or stated points/basis-points amount is not one.',
    'unclear': 'The source does not establish whether this is percentage growth or which potentially relevant comparison applies.'}
request['state'] = ('GROWTH_BASIS_TASK: Classify the exact target occurrence. Use only comparison wording '
                    'applying to that occurrence, never a different amount or financial convention.\n'
                    + json.dumps(options) + '\n' + request['state'])
for target in targets + controls:
    request['questions'][target['tag'] + '_basis_evidence'] = {
        'type': 'choice',
        'instructions': f'For {target["text"]!r} at [{target["tag"]}] in SOURCE, which GROWTH_BASIS_TASK option is supported?',
        'criteria': {k: None for k in options}}
expected = json.loads((OUT / 'reference.json').read_text())['expected']
basis_expected = {tag + '_basis_evidence': value for tag, value in {
    'F0': 'not_growth_percentage', 'F1': 'not_stated', 'F2': 'not_growth_percentage',
    'F3': 'not_stated', 'F4': 'not_growth_percentage', 'F5': 'not_growth_percentage',
    'V7': 'year_earlier', 'V10': 'year_earlier'}.items()}
(OUT / 'basis_check_request.json').write_text(json.dumps(request, indent=2))
(OUT / 'basis_check_reference.json').write_text(json.dumps({'fields': expected, 'basis': basis_expected}, indent=2))
t = time.perf_counter()
try:
    result = {'response': L.decide(**request, timeout=1800)}
except Exception as error:
    result = {'error': str(error)}
result.update(seconds=time.perf_counter() - t, finished_at=datetime.now(ZoneInfo('America/Toronto')).isoformat())
(OUT / 'basis_check_result.json').write_text(json.dumps(result, indent=2))
rows = []
normalized = []
if 'response' in result:
    answers = result['response']['answers']
    for qid, value in {**expected, **basis_expected}.items():
        a = answers[qid]
        rows.append({'id': qid, 'expected': value, 'actual': a['choice'],
                     'correct': value == a['choice'], 'p': a['probabilities'][a['choice']]})
    for qid, value in expected.items():
        observed = answers[qid]['choice']
        new = observed
        reason = None
        if qid.endswith('_unit_scale') and observed in ['percent_yoy', 'percent_sequential']:
            basis = answers[qid.split('_', 1)[0] + '_basis_evidence']['choice']
            if basis in ['not_stated', 'other_stated']:
                new, reason = 'unknown', '3.33: no supported yearly/sequential growth basis'
            elif basis in ['unclear', 'two_bases', 'not_growth_percentage']:
                new, reason = 'unresolved', 'Conflicting or unseparated meanings; no forced unit'
        normalized.append({'id': qid, 'expected': value, 'raw': observed,
                           'after_absence_rule': new, 'correct': value == new, 'reason': reason})
score = {'raw_correct': sum(r['correct'] for r in rows), 'raw_total': len(rows), 'raw_rows': rows,
         'field_correct_after_absence_rule': sum(r['correct'] for r in normalized),
         'field_total': len(normalized), 'field_rows': normalized,
         'seconds': result['seconds'], 'usage': result.get('response', {}).get('usage'),
         'error': result.get('error'),
         'limits': 'Diagnostic of existing fields and one explicit policy judgment. Not a production normalizer or complete records; all other conflicts remain unproved.'}
(OUT / 'basis_check_scored.json').write_text(json.dumps(score, indent=2))
print(json.dumps({k: v for k, v in score.items() if not k.endswith('_rows')}, indent=2), flush=True)
for row in rows:
    if not row['correct']:
        print(json.dumps(row), flush=True)
with (ROOT / 'progress.md').open('a') as f:
    f.write('\nTest: Integrate an explicit growth-basis choice into the same full-call choice batch: six field targets plus two real positive controls, no reviewed excerpts supplied.\n')
    f.write(f'Result: {score["raw_correct"]}/{score["raw_total"]} raw choices; '
            f'{score["field_correct_after_absence_rule"]}/{score["field_total"]} original fields after the narrow 3.33 absence rule; '
            f'{score["seconds"]:.2f}s; {score["usage"]}; error={score["error"]}. Not full records.\n')
    f.write('Next: Inspect failures and total stage cost before retaining an extra judgment; do not turn prototype conflict handling into a production normalizer.\n')
