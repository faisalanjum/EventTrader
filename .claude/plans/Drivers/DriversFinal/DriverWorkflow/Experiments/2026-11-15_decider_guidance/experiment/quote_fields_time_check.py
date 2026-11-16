"""One generic clarification of duration versus instant, with boundary controls.
All prior 42 fields remain in the request to detect changes from shared state.
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
real_only = '--real-only' in sys.argv
name = 'time_real' if real_only else 'time_check'
request = json.loads((OUT / 'request.json').read_text())
reference = json.loads((OUT / 'reference.json').read_text())
prefix, encoded = request['state'].rsplit('\nQUOTES:\n', 1)
quotes = json.loads(encoded)
definitions = {
    'duration': 'The quantity describes performance, activity or change over an interval of time.',
    'instant': 'The quantity describes a balance, stock or other snapshot at one point in time.',
    'unclear': 'The evidence does not establish which meaning applies.'}
prefix += ('\nTIME_TYPE_DEFINITION: Classify the meaning of the measured quantity, not when the forecast '
           'was announced. A fiscal-year label can describe either annual activity or a year-end snapshot. '
           'Choose from these meanings: ' + json.dumps(definitions))

# Paired, manually specified semantic controls. These are test evidence, not source claims.
controls = [
    ('cash_flow', 'We expect cash generated during fiscal 2026 to be [TARGET] $50 million.', 'duration'),
    ('cash_balance', 'We expect cash on hand at May 31, 2026, to be [TARGET] $50 million.', 'instant'),
    ('openings', 'We expect to open [TARGET] 100 stores during fiscal 2026.', 'duration'),
    ('stores', 'We expect to have [TARGET] 100 stores operating at the end of fiscal 2026.', 'instant'),
    ('growth', 'We expect revenue in fiscal 2026 to grow by [TARGET] 5%.', 'duration'),
    ('unspecified', 'We expect the measure to be [TARGET] $50 million.', 'unclear')]
if real_only:
    controls = []
expected = dict(reference['expected'])
for name, text, answer in controls:
    tag = 'CONTROL_' + name
    quotes[tag] = {'evidence_in_source_order': [{'text': text}],
                   'provenance': 'Controlled semantic test, not a published company statement.'}
    request['questions'][tag + '_time_type'] = {
        'type': 'choice',
        'instructions': f'For [TARGET] in QUOTES.{tag}, answer time_type using TIME_TYPE_DEFINITION.',
        'criteria': {k: None for k in definitions}}
    expected[tag + '_time_type'] = answer
for qid, question in request['questions'].items():
    if qid.endswith('_time_type') and not qid.startswith('CONTROL_'):
        question['instructions'] = question['instructions'].replace('using FIELD_RULES.', 'using TIME_TYPE_DEFINITION.')
request['state'] = prefix + '\nQUOTES:\n' + json.dumps(quotes, ensure_ascii=False)
(OUT / (name + '_request.json')).write_text(json.dumps(request, indent=2))
(OUT / (name + '_reference.json')).write_text(json.dumps({'expected': expected, 'controls': controls}, indent=2))
t = time.perf_counter()
try:
    result = {'response': L.decide(**request, timeout=1800)}
except Exception as error:
    result = {'error': str(error)}
result.update(seconds=time.perf_counter() - t, finished_at=datetime.now(ZoneInfo('America/Toronto')).isoformat())
(OUT / (name + '_result.json')).write_text(json.dumps(result, indent=2))
rows = []
if 'response' in result:
    for qid, expected_value in expected.items():
        actual = result['response']['answers'][qid]
        rows.append({'id': qid, 'expected': expected_value, 'actual': actual['choice'],
                     'correct': expected_value == actual['choice'],
                     'p': actual['probabilities'][actual['choice']]})
score = {'correct': sum(r['correct'] for r in rows), 'total': len(rows), 'rows': rows,
         'seconds': result['seconds'], 'usage': result.get('response', {}).get('usage'),
         'error': result.get('error'),
         'limits': f'42 prior development-field controls plus {len(controls)} semantic controls; reviewed evidence, no automatic record score.'}
(OUT / (name + '_scored.json')).write_text(json.dumps(score, indent=2))
print(json.dumps({k: v for k, v in score.items() if k != 'rows'}, indent=2), flush=True)
for row in rows:
    if not row['correct']:
        print(json.dumps(row), flush=True)
with (ROOT / 'progress.md').open('a') as f:
    f.write(f'\nTest: Clarify duration versus instant by quantity meaning; retain all 42 prior field questions with {len(controls)} additional paired/negative semantic controls.\n')
    f.write(f'Result: {score["correct"]}/{score["total"]} field choices; {score["seconds"]:.2f}s; '
            f'{score["usage"]}; error={score["error"]}. This is not complete extraction.\n')
    f.write('Next: Keep only a measured generic wording improvement; check other fields and do not infer full-record readiness.\n')
