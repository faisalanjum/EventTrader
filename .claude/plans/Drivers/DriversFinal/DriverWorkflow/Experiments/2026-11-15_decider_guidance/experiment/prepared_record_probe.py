"""One complete source block instead of a new evidence-selection repair layer.

Six previously discovered numeric expressions, not full-call discovery. Existing
field questions are retained, with required amount meaning, comparison baseline,
modifiers and conditions. No measure-copy repair, reference names or writer.
"""
import hashlib
import json
import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/faisal/EventMarketDB')
from config import local_llm as L

ROOT = pathlib.Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'prepared_record'
OUT.mkdir(exist_ok=True)


def load(name):
    return json.loads((ROOT / name).read_text())


def save(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def prepare():
    prior = load('quote_fields/basis_check_request.json')
    targets = load('main_path/expression_fields_request.json')['targets']
    source_id = load('main_path/expression_fields_request.json')['source']
    source = next(s for s in load('sources.json') if s['id'] == source_id)
    prepared = [p for p in source['passages'] if p['kind'] == 'prepared']
    quote = '\n\n'.join(p['text'] for p in prepared)
    # This fixture has contiguous ordered prepared blocks. Never stitch a
    # discontinuous selection and present it as a continuous source quote.
    assert source['text'].startswith(quote)
    source_prefix = prior['state'].split('SOURCE:\n', 1)[0]
    metadata = prior['state'].split('SOURCE:\n', 1)[1].split('[PR000]', 1)[0]
    rendered, mapping = [], []
    original_offset = 0
    for p in prepared:
        text = p['text']
        positions = list(range(original_offset, original_offset + len(text)))
        for target in sorted((c for c in targets if c['passage'] == p['id']),
                             key=lambda c: c['start'], reverse=True):
            label = '[' + target['tag'] + '] '
            assert p['text'][target['start']:target['end']] == target['text']
            text = text[:target['start']] + label + text[target['start']:]
            positions[target['start']:target['start']] = [None] * len(label)
        prefix = '[' + p['id'] + '] '
        if rendered:
            mapping.extend([None, None])
        rendered.append(prefix + text)
        mapping.extend([None] * len(prefix) + positions)
        original_offset += len(p['text']) + 2
    meanings = {
        'level': 'The amount is the forecast level of the measure, including a rate level.',
        'measure_change': 'The amount is forecast growth or a change in the underlying measure, not a revision of the guidance itself.',
        'guidance_revision': 'The amount states how much the company revised its own previous forecast.',
        'reference_only': 'Only a comparison, prior forecast, actual, or other supporting number; not the current forecast value.',
        'several': 'Several of these meanings apply to distinct claims; do not collapse them.',
        'unclear': 'The source does not establish what the amount represents.'}
    baselines = {
        'consensus': 'An explicitly stated comparison with analysts, the Street or market expectations.',
        'prior_year': 'An explicitly stated comparison with the prior year or the same period one year earlier.',
        'sequential_period': 'An explicitly stated comparison with the immediately preceding period.',
        'previous_guidance': 'An explicitly stated comparison with the company\'s own earlier guidance or target.',
        'none': 'No eligible explicit comparison baseline. A target year alone is not a comparison.',
        'unclear': 'A comparison is potentially relevant but its type or applicability is unclear.'}
    rules = ('REMAINING_FIELDS: Preserve the exact target meaning, not another amount nearby. '
             'A forecast of a change is its value; only the forecast\'s own revision is a guidance revision (4.6). '
             'MEANING_OPTIONS=' + json.dumps(meanings) + '\n'
             'COMPARISON_OPTIONS=' + json.dumps(baselines) + '\n'
             'A baseline may be stated without a comparison number; never invent one (3.49). '
             'Use only the headline comparison; prior-year wins a tie with sequential (3.52). '
             'MODIFIERS are exact meaning-changing words: measurement basis, approximation/strict bounds, '
             'or words establishing forecast growth/change. Do not copy the measure, value, period or unit '
             'as a modifier when it only supplies those fields. Keep source wording; no inferred modifier. '
             'CONDITIONS are expressly applicable forecast assumptions, dependencies and exclusions; '
             'not a cause, actual result, bare forecast amount, or guidance movement. A measurement '
             'definition stays in the evidence; it is not automatically an assumption (4.8).\n')
    prefix = rules + source_prefix + 'SOURCE:\n' + metadata
    state = prefix + '\n\n'.join(rendered)
    mapping = [None] * len(prefix) + mapping
    assert len(mapping) == len(state)
    questions = {k: v for k, v in prior['questions'].items() if k.startswith('F')}
    for target in targets:
        tag = target['tag']
        address = f'For {target["text"]!r} at [{tag}] in SOURCE'
        questions[tag + '_amount_meaning'] = {
            'type': 'choice', 'instructions': address + ', choose MEANING_OPTIONS.',
            'criteria': {k: None for k in meanings}}
        questions[tag + '_comparison_baseline'] = {
            'type': 'choice', 'instructions': address + ', choose COMPARISON_OPTIONS.',
            'criteria': {k: None for k in baselines}}
        questions[tag + '_modifiers'] = {
            'type': 'locate', 'instructions': address + ', locate its MODIFIERS under REMAINING_FIELDS.'}
        questions[tag + '_conditions'] = {
            'type': 'locate', 'instructions': address + ', locate its CONDITIONS under REMAINING_FIELDS.'}
    save('request', {'state': state, 'questions': questions, 'mode': 'isolated'})
    save('source_map', {'source_id': source_id, 'source_text_sha256': hashlib.sha256(source['text'].encode()).hexdigest(),
                        'prepared_quote': quote, 'mapping': mapping, 'targets': targets})
    # Kept separate from model input. This is a six-target field reference,
    # not a complete independently adjudicated transcript answer key.
    reference = load('quote_fields/reference.json')['expected']
    for target in targets:
        tag = target['tag']
        reference[tag + '_amount_meaning'] = 'measure_change' if tag in ['F1', 'F3'] else 'level'
        reference[tag + '_comparison_baseline'] = 'prior_year' if tag == 'F5' else 'none'
    reference.update({k: v for k, v in load('quote_fields/basis_check_reference.json')['basis'].items() if k.startswith('F')})
    save('reference', {'expected_choices': reference,
        'modifier_requirements': {'F0': [], 'F1': ['growth meaning'],
            'F2': ['adjusted diluted'], 'F3': ['adjusted diluted', 'growth meaning'],
            'F4': ['approximately'], 'F5': []},
        'condition_review': 'Check source assumptions and measurement exclusions separately; support association is not an exhaustive or adjudicated condition key.',
        'scope': 'Discovery and measure identity are not retested. Copying and whole-proposal correctness require source review after choices.'})
    print(json.dumps({'questions': len(questions), 'source_characters': len(quote), 'state_characters': len(state)}))


def run():
    request = json.loads((OUT / 'request.json').read_text())
    t = time.perf_counter()
    try:
        result = {'response': L.decide(**request, timeout=1800)}
    except Exception as error:
        result = {'error': str(error)}
    result.update(seconds=time.perf_counter() - t,
                  finished_at=datetime.now(ZoneInfo('America/Toronto')).isoformat())
    save('result', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'response'}), flush=True)
    with (ROOT / 'progress.md').open('a') as f:
        f.write('\nTest: Complete prepared-section evidence, six saved numeric targets; existing fields plus amount meaning, baseline, modifiers and assumptions. No new discovery or measure repair.\n')
        f.write(f'Result: {result["seconds"]:.2f}s; {result.get("response", {}).get("usage")}; error={result.get("error")}. Semantic review pending; not a complete extraction pass.\n')
        f.write('Next: Map returned copies to source and review complete target meanings; keep failures explicit instead of adding repair layers.\n')


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
