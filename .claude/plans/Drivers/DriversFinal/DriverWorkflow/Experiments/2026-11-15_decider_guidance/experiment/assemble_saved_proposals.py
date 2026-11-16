"""Reconcile existing experiment outputs, without inference or answer-key input.

This is a mixed-configuration diagnostic, not a replay of one frozen pipeline.
It deliberately retains missing fields instead of inventing complete records.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'assembled_proposals'
OUT.mkdir(exist_ok=True)
inputs = {}


def read(relative):
    path = ROOT / relative
    raw = path.read_bytes()
    inputs[relative] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


source_id = read('main_path/expression_fields_request.json')['source']
# The source file also contains legacy rows. Only source text/metadata are used.
snapshot = next(s for s in read('sources.json') if s['id'] == source_id)
source = {k: snapshot[k] for k in ['id', 'meta', 'passages', 'text']}
assert source['text'] == '\n\n'.join(p['text'] for p in source['passages'])
passages = {p['id']: p for p in source['passages']}
offsets = {}
offset = 0
for passage in source['passages']:
    offsets[passage['id']] = offset
    offset += len(passage['text']) + 2


def location(passage, start, end):
    text = passages[passage]['text'][start:end]
    a, z = offsets[passage] + start, offsets[passage] + end
    assert text == source['text'][a:z] and 0 <= start < end <= len(passages[passage]['text'])
    return {'passage': passage, 'start': start, 'end': end,
            'source_start': a, 'source_end': z, 'text': text}


base = read('main_path/B_result.json')
candidates = {c['tag']: c for c in base['candidates']}
sentences = {s['tag']: s for s in base['sentences']}
targets = read('main_path/expression_fields_request.json')['targets']
bounds = read('main_path/numeric_bounds_shared_result.json')['response']['answers']
measures = {m['target']['tag']: m for m in read('main_path/measure_local_summary.json')}
pointer = read('main_path/measure_pointer_result.json')
support = read('main_path/support_sentence_result.json')
fields_request = read('quote_fields/basis_check_request.json')
fields = read('quote_fields/basis_check_result.json')['response']['answers']
assert 'QUOTED_EVIDENCE' not in fields_request['state']
rows = []
for target in targets:
    tag = target['tag']
    anchor = location(target['passage'], target['start'], target['end'])
    assert anchor['text'] == target['text']
    own = next(s for s in sentences.values() if s['passage'] == target['passage']
               and s['start'] <= target['start'] < s['end'])
    selected = {own['tag']: 'contains forecast amount'}
    m = measures[tag]
    if m['selected'] in sentences:
        selected[m['selected']] = 'model-selected measure sentence'
    measure_spans = []
    for span in m.get('spans', []):
        if 'source_passage' not in span:
            continue
        proof = location(span['source_passage'], span['source_start'], span['source_end'])
        assert proof['text'] == span['text']
        measure_spans.append({**proof, 'score': span['score']})
    support_choices = []
    for qid, answer in support['response']['answers'].items():
        if qid.startswith(tag + '_'):
            sid = qid.split('_', 1)[1]
            support_choices.append({'sentence': sid, 'probability': answer['noul']})
            if answer['noul'] >= .5:
                selected[sid] = 'model-selected support; not automatically a condition'
    evidence = []
    for sid, reason in selected.items():
        s = sentences[sid]
        evidence.append({**location(s['passage'], s['start'], s['end']),
                         'sentence': sid, 'selected_because': reason})
    evidence.sort(key=lambda x: x['source_start'])
    lo = min(x['source_start'] for x in evidence)
    hi = max(x['source_end'] for x in evidence)
    quote = {'source_start': lo, 'source_end': hi, 'text': source['text'][lo:hi]}
    # Preserve every model-selected endpoint and its probability. Repeated
    # aliases must agree; do not infer a range just because two numbers exist.
    endpoints = {}
    for side in ['lower', 'upper']:
        answers = {alias: bounds[alias + '_' + side] for alias in target['aliases']}
        chosen = {a['choice'] for a in answers.values()}
        assert len(chosen) == 1
        token = candidates[next(iter(chosen))]
        endpoints[side] = {**location(token['passage'], token['start'], token['end']),
                           'token': token['tag'], 'answers': answers}
    answers = {qid[len(tag) + 1:]: answer for qid, answer in fields.items()
               if qid.startswith(tag + '_')}
    values = {name: answer['choice'] for name, answer in answers.items()}
    unit = values['unit_scale']
    applied = None
    if unit in ['percent_yoy', 'percent_sequential'] and values['basis_evidence'] == 'not_stated':
        unit, applied = 'unknown', '3.33: no evidenced growth comparison basis'
    rows.append({
        'target': tag, 'source_id': source_id,
        'outcome': 'partial_proposal_for_review', 'accepted': False,
        'anchor': anchor, 'aliases': target['aliases'],
        'raw_measure_wording': measure_spans,
        'measure_pointer_answer': pointer['response']['answers'][tag],
        'printed_endpoints': endpoints,
        'field_choices': answers,
        'proposed_fields': {**values, 'unit_scale_after_rule': unit,
                            'unit_rule_applied': applied},
        'selected_evidence': evidence, 'continuous_quote': quote,
        'support_choices': support_choices,
        'missing_assembly_steps': [
            'Separate copied measure wording from complete measure/change meaning and qualifiers.',
            'Separate assumptions, measurement exclusions and comparisons; support selection alone does not do this.',
            'Verify every field against the assembled quote, including omitted lead-ins.',
            'Exact numeric/unit normalization and fiscal-date resolution are not performed by this reconciliation.',
        ],
        'limits': 'Mixed saved configurations; only six prior field targets. No new recall or end-to-end score.'})

output = {'source': source_id,
          'source_text_sha256': hashlib.sha256(source['text'].encode()).hexdigest(),
          'input_sha256': inputs, 'proposals': rows,
          'counts': {'proposals': len(rows), 'complete_accepted': 0,
                     'partial': len(rows)},
          'scope': 'Actual saved outputs assembled without reference labels or legacy rows as field inputs. Not one coherent production run.'}
(OUT / 'reconciled.json').write_text(json.dumps(output, indent=2, ensure_ascii=False))
lines = ['# Saved-output reconciliation', '',
         'Current rulebook governs. This combines measured components from different requests; it is not a new end-to-end run. No accepted complete records are claimed.', '',
         '| Target | Raw measure wording | Printed expression | Shape / period / unit choice | Selected evidence |',
         '| --- | --- | --- | --- | --- |']
for row in rows:
    v = row['proposed_fields']
    lines.append('| ' + ' | '.join([row['target'],
        '; '.join(s['text'] for s in row['raw_measure_wording']), row['anchor']['text'],
        f"{v['form']} / {v['period']} / {v['unit_scale_after_rule']}",
        ', '.join(e['sentence'] for e in row['selected_evidence'])]) + ' |')
lines.extend(['', 'Full exact quotes, positions, all probabilities and input hashes are in `reconciled.json`.',
              'Missing: complete amount meaning and qualifiers; correct separation of conditions/exclusions/comparisons; proof for every field in the assembled quote; final numeric and fiscal-date normalization.',
              'A copied phrase can correctly identify a measure without being a final Driver name. No catalogue matching, graph IDs or database writes belong to this diagnostic.'])
(OUT / 'README.md').write_text('\n'.join(lines) + '\n')
with (ROOT / 'progress.md').open('a') as f:
    f.write('\nTest: Assemble six prior field targets from actual saved numeric bounds, measure pointers/copies, support associations and whole-call choices; verify all source locations.\n')
    f.write('Result: Six partial proposals with exact quotes and input hashes; zero complete accepts claimed. Mixed configurations are explicit; no reference labels or legacy rows supplied as fields.\n')
    f.write('Next: Audit actual assembled records under the current rulebook, distinguishing missing meaning from deferred canonical naming and redundant copying.\n')
print(json.dumps(output['counts']))
