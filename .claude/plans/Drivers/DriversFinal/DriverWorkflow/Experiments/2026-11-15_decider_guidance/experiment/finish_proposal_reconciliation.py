"""Normalize actual selected numeric slots and preserve all remaining gaps.
This combines saved stages; it is neither new inference nor automatic acceptance.
"""
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, '/tmp/decider_claude_review_20261115')
from proposal_numbers import normalize, printed_decimal

ROOT = pathlib.Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'assembled_proposals'
initial = json.loads((OUT / 'reconciled.json').read_text())
fields = json.loads((ROOT / 'prepared_record/label_check_result.json').read_text())['response']['answers']
copies = json.loads((ROOT / 'prepared_record/selected_copy_mapped.json').read_text())
source = json.loads((ROOT / 'prepared_record/source_map.json').read_text())
periods = json.loads((ROOT / 'main_path/C_choices_request.json').read_text())['period_menu']
rows = []
for old in initial['proposals']:
    tag = old['target']
    answers = {k[len(tag) + 1:]: a for k, a in fields.items()
               if k.startswith(tag + '_') and a['type'] == 'choice'}
    values = {k: a['choice'] for k, a in answers.items()}
    unit = values['unit_scale']
    if unit in ['percent_yoy', 'percent_sequential'] and values['basis_evidence'] == 'not_stated':
        unit = 'unknown'
    amount = {}
    for side, token in old['printed_endpoints'].items():
        value, canonical_unit = normalize(token['text'], unit, values['sign'])
        amount[side] = value
    amount.update(unit=canonical_unit, shape=values['form'], meaning=values['amount_meaning'])
    # These six actual expressions use equal points or increasing closed ranges.
    # Other shapes are not silently coerced by this diagnostic.
    from decimal import Decimal
    if values['form'] == 'point':
        assert amount['lower'] == amount['upper']
    elif values['form'] == 'range':
        assert Decimal(amount['lower']) < Decimal(amount['upper'])
    else:
        raise ValueError('Unimplemented diagnostic shape: ' + values['form'])
    dates = periods[values['period']].split(' through ')
    assert len(dates) == 2
    assert date.fromisoformat(dates[0]) <= date.fromisoformat(dates[1])
    modifiers = copies[tag + '_modifiers']
    conditions = copies[tag + '_conditions']
    assert all(x['contiguous_source'] for x in modifiers + conditions)
    for x in modifiers + conditions:
        assert x['source_text'] == source['prepared_quote'][x['source_start']:x['source_end']]
    rows.append({'target': tag, 'source_id': initial['source'],
        'status': 'requires_independent_semantic_review', 'runtime_accepted': False,
        'raw_measure_wording': old['raw_measure_wording'],
        'subject_scope': values['subject_scope'], 'amount': amount,
        'period': {'label': values['period'], 'inclusive_start': dates[0], 'inclusive_end': dates[1],
                   'time_type': values['time_type'], 'calendar_scope': 'Previously verified fixture calendar; not a general calendar implementation.'},
        'movement': 'unknown' if values['movement'] == 'not_stated' else values['movement'],
        'comparison_baseline': values['comparison_baseline'],
        'comparison_numbers': None,
        'tags_from_copies': ['_'.join(re.findall(r'\w+', x['source_text'].lower())) for x in modifiers],
        'modifier_evidence': modifiers, 'conditions': conditions,
        'quote_reference': 'complete_prepared_quote', 'raw_answers': answers,
        'source_bounds': old['printed_endpoints'],
        'limits': 'Raw source measure, not a final Driver name/ID. Comparison numbers were not extracted; baseline-only is lawful when no number is stated. Full proposals require source review.'})

inputs = ['assembled_proposals/reconciled.json', 'prepared_record/label_check_request.json',
          'prepared_record/label_check_result.json', 'prepared_record/selected_copy_request.json',
          'prepared_record/selected_copy_result.json', 'main_path/C_choices_request.json', 'proposal_numbers.py']
artifact = {'source': initial['source'], 'source_text_sha256': initial['source_text_sha256'],
            'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
            'complete_prepared_quote': source['prepared_quote'], 'proposals': rows,
            'runtime_accepted': 0, 'claim': 'Six normalized diagnostic proposals assembled from actual measured stages, not a coherent end-to-end run or a source-wide recall result.'}
(OUT / 'normalized.json').write_text(json.dumps(artifact, indent=2, ensure_ascii=False))

# Account for the entire observed six-source literal domain. A parseable year
# is still only a token; this check does not decide what is a forecast.
inventory = []
for snapshot in json.loads((ROOT / 'sources.json').read_text()):
    for match in re.finditer(r'\S+', snapshot['text']):
        if not any(c.isdecimal() for c in match[0]):
            continue
        try:
            value = str(printed_decimal(match[0]))
            status, reason = 'lexically_parseable', None
        except ValueError as error:
            value, status, reason = None, 'unsupported_literal', str(error)
        inventory.append({'source': snapshot['id'], 'start': match.start(), 'end': match.end(),
                          'text': match[0], 'outcome': status, 'value': value, 'reason': reason})
census = {'tokens': len(inventory), 'outcomes': dict(Counter(x['outcome'] for x in inventory)),
          'rows': inventory, 'scope': 'All digit-bearing tokens in the six frozen source snapshots, including dates and speaker labels. No financial eligibility or corpus-wide parser-coverage claim.'}
(OUT / 'number_spelling_audit.json').write_text(json.dumps(census, indent=2))
print(json.dumps({k: v for k, v in census.items() if k != 'rows'}))
for row in rows:
    print(row['target'], row['amount'], row['tags_from_copies'], row['comparison_baseline'])
with (ROOT / 'progress.md').open('a') as f:
    f.write('\nTest: Normalize all six actual numeric proposals with native strict Babel parsing and the existing exact-scaling helper; check source copies and all observed six-source digit tokens.\n')
    f.write(f'Result: Six exact numeric proposals; {len(inventory)} observed tokens accounted for: {census["outcomes"]}. Wrapper tests passed after the initial missing-helper failure. Semantic acceptance remains unset.\n')
    f.write('Next: Complete the source-based proposal review and record copying gaps; no parser expansion or further copy repair loop.\n')
