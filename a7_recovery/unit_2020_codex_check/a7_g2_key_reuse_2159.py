"""Bind independently selected unchanged G2 tasks across a corrected key.

This checks identities, not meaning. The reviewer selects affected tasks;
the existing native reader supplies judgments and the existing revision
owner applies new ones. Original evidence and question ids remain unchanged.
"""
import collections
import copy
import json
from pathlib import Path

import a7_g1_build as G
import a7_g23_build as B
import a7_grading_input_correction_2114 as V
import a4_review_composite as R
import a7_g1_complete_v2 as C
import a7_g1_key_reuse_2152 as REUSE
import a7_meaning_format_2105 as FORMAT


def _pin(ref):
    if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
            or G._sha_file(ref['path']) != ref['sha256']):
        raise ValueError('unapproved G2 reuse file')


def _tasks(ref, pins):
    _pin(ref)
    path = Path(ref['path'])
    if path.name != G.CANDIDATE_NAME:
        raise ValueError('G2 reuse must name the native candidate')
    doc, _ = G.load_frozen(str(path.parent), ref['sha256'])
    if doc.get('task_kind') != 'G2' or not isinstance(doc.get('population'), dict):
        raise ValueError('G2 reuse requires a G2 population')
    tasks = {}
    for group, pairs in doc['population'].items():
        leg, sid = group.split('|', 1)
        for pair in pairs:
            if (not isinstance(pair, list) or len(pair) != 2
                    or any(type(i) is not int or i < 0 for i in pair)):
                raise ValueError('invalid G2 reuse pair')
            qid = B.meaning_question_id(leg, sid, *pair)
            if qid in tasks:
                raise ValueError('repeated G2 reuse question')
            tasks[qid] = dict(group=group, pair=pair)
    seen = set()
    for row in doc['batch_rows']:
        prompt = path.parent / row['prompt_path']
        pin = dict(path=str(prompt), sha256=row['prompt_sha256'])
        _pin(pin)
        pins.append(pin)
        rules, body = prompt.read_text(encoding='utf-8').split('[EVENT]\n', 1)
        asked = []
        for event in json.loads(body)['events']:
            for question in event['questions']:
                qid = question['question_id']
                if qid not in tasks or qid in seen:
                    raise ValueError('G2 prompt population differs or repeats')
                seen.add(qid)
                asked.append(qid)
                task = tasks[qid]
                task.update(question=question, context=event['event_context'], rules=rules)
                # The same produced occurrence, complete record, source card,
                # source context and served rules. Only an opaque id may move.
                task['identity'] = G._plain([
                    task['group'], task['pair'][1], rules, event['event_context'],
                    {k: v for k, v in question.items() if k != 'question_id'}])
        if asked != row['question_ids']:
            raise ValueError('G2 batch question identities changed')
    if seen != set(tasks) or doc['questions'] != len(tasks):
        raise ValueError('G2 prompt population is incomplete')
    pins.append(ref)
    return doc, tasks


def derive(selection_path, expected_sha256):
    """Return exact old/new bindings, never caller-supplied grading judgments."""
    pins = [dict(path=str(selection_path), sha256=expected_sha256)]
    _pin(pins[0])
    selected = G._read(str(selection_path))
    fields = {'schema', 'reviewer_session', 'review', 'renderer',
              'original_candidate', 'current_candidate', 'rows'}
    if (not isinstance(selected, dict) or set(selected) != fields
            or selected['schema'] != 'a7-g2-reuse-selection/v1'
            or not isinstance(selected['reviewer_session'], str)
            or not selected['reviewer_session'].strip()):
        raise ValueError('invalid G2 reuse selection')
    pins.extend([selected['review'], selected['renderer']])
    for ref in pins:
        _pin(ref)
    if Path(selected['renderer']['path']).resolve() != Path(V.__file__).resolve():
        raise ValueError('G2 reuse names a different display owner')
    old_doc, old = _tasks(selected['original_candidate'], pins)
    current_doc, current = _tasks(selected['current_candidate'], pins)
    by_view = collections.defaultdict(list)
    for qid, task in old.items():
        by_view[task['identity']].append(qid)
    carry, correction, seen = {}, {}, set()
    for row in selected['rows']:
        if (not isinstance(row, dict)
                or set(row) != {'question_id', 'decision', 'reason'}
                or row['question_id'] not in current or row['question_id'] in seen
                or row['decision'] not in ('carry', 'correct')
                or not isinstance(row['reason'], str) or not row['reason'].strip()):
            raise ValueError('invalid or repeated G2 reuse disposition')
        qid = row['question_id']
        seen.add(qid)
        task = current[qid]
        if row['decision'] == 'correct':
            correction.setdefault(task['group'], []).append(task['pair'])
            continue
        matches = by_view[task['identity']]
        if len(matches) != 1:
            raise ValueError('G2 reuse has no unique unchanged task: ' + qid)
        record = task['question']['produced_record']
        if V.record_view(record) != record:
            raise ValueError('G2 reuse changed display: ' + qid)
        carry[qid] = matches[0]
    if seen != set(current) or len(set(carry.values())) != len(carry):
        raise ValueError('G2 reuse dispositions do not partition unique tasks')
    for ref in pins:
        _pin(ref)
    return dict(carry=carry, correction_population={k: sorted(v) for k, v in sorted(correction.items())},
                current_tasks=current, original_tasks=old, pins=pins,
                current_candidate=current_doc, original_candidate=old_doc)


def evaluate(E, plan_path, expected_sha256, action):
    """Prove old G2 natively, enter the current key, then use its consumer.

    This is a BASE input, not a completed grading run: every selected correction
    still needs the existing revision owner. No original G3 credit is carried.
    The public entry receives frozen file handles, never a map of judgments.
    """
    plan_ref = dict(path=str(plan_path), sha256=expected_sha256)
    _pin(plan_ref)
    plan = G._read(str(plan_path))
    fields = {'schema', 'code_sha256', 'selection', 'original_proof',
              'current_preparation', 'g1_reuse_report', 'format'}
    if (not isinstance(plan, dict) or set(plan) != fields
            or plan['schema'] != 'a7-g2-key-reuse/v1'):
        raise ValueError('invalid G2 key-reuse plan')
    pins = [plan_ref, dict(path=__file__, sha256=plan['code_sha256'])]
    pins.extend(plan[k] for k in ('original_proof', 'current_preparation', 'g1_reuse_report'))
    for ref in pins:
        _pin(ref)
    selection = derive(plan['selection']['path'], plan['selection']['sha256'])
    pins.extend(selection['pins'])
    old = G._read(plan['original_proof']['path'])
    current = G._read(plan['current_preparation']['path'])
    required = {}
    for kind, ref in current['candidates'].items():
        _pin(ref)
        doc, _ = G.load_frozen(str(Path(ref['path']).parent), ref['sha256'])
        if doc['task_kind'] != kind:
            raise ValueError('current grading kind changed')
        required[kind] = doc['population']
        if kind == 'G2' and doc != selection['current_candidate']:
            raise ValueError('current G2 candidate differs from the reuse selection')
        pins.append(ref)
    if set(required) != {'G2', 'G3'}:
        raise ValueError('current grading population is incomplete')

    def same(actual, expected, label):
        if G._plain(actual) != G._plain(expected):
            raise ValueError('G2 key reuse changed ' + label)

    original, prepared = B._verdict_maps_from, E.with_prepared_inputs
    native_maps, native_memo = {}, {}
    source = old['g23_sources']['G2']
    memo_key = ('G2', source['run_dir'], source['root_sha256'], source['completion_sha256'])

    def prove_then(enter_current):
        def prove(producer, inputs):
            same(producer, old['producer_identity'], 'original producer')
            same(E.g1, old['g1'], 'original G1')
            same(G.live_key()[1], old['key_identity'], 'original key')
            # Only G2 is reused. Its WHOLE original run/completion/population
            # is mandatory; repeating old G3 verification would supply no data.
            with FORMAT.scope(plan['format']['code_sha256'], plan['format']['rule_sha256']):
                for leg in sorted({k.split('|', 1)[0] for k in required['G2']}):
                    native_maps[leg] = original(leg, {'G2': source}, producer,
                                                old['required_population'], E.g1, native_memo)[0]
            same(native_memo[memo_key][0], selection['original_candidate'], 'original native candidate')
            return enter_current(producer, inputs)
        return prepared(prove)

    def under_current(producer, inputs, g1):
        same(producer, current['producer'], 'current producer')
        same(g1, current['g1'], 'current G1')
        same(G.live_key()[1], current['key_identity'], 'current key')

        def carried(leg, sources, got_producer, want, got_g1, memo):
            if G._plain(sources) != G._plain(old['g23_sources']):
                # Corrective runs still go through the one native verifier.
                return original(leg, sources, got_producer, want, got_g1, memo)
            same(got_producer, producer, 'consumer producer')
            same(got_g1, g1, 'consumer G1')
            same(want, required, 'consumer full population')
            same(G.live_key()[1], current['key_identity'], 'consumer key')
            result = {}
            for new_id, old_id in selection['carry'].items():
                new, previous = selection['current_tasks'][new_id], selection['original_tasks'][old_id]
                group_leg, sid = new['group'].split('|', 1)
                if group_leg != leg:
                    continue
                old_index, new_index = (sid, previous['pair'][0]), (sid, new['pair'][0])
                if old_index in native_maps[leg]:
                    if new_index in result:
                        raise ValueError('G2 reuse repeats a current gold row')
                    result[new_index] = copy.deepcopy(native_maps[leg][old_index])
            return result, {}  # all original G3 judgments remain excluded

        with R._using(B, _verdict_maps_from=carried):
            result = action(producer, inputs, g1)
        same(G.live_key()[1], current['key_identity'], 'current key at exit')
        return result

    try:
        with R._using(E, with_prepared_inputs=prove_then):
            return REUSE.evaluate(E, plan['g1_reuse_report']['path'], current['g1'], under_current)
    finally:
        for ref in pins:
            _pin(ref)
        if memo_key in native_memo:
            identity = native_memo[memo_key][1]['run_identity']
            if C.run_digest(source['run_dir']) != (identity['run_digest'], identity['run_files']):
                raise ValueError('original G2 evidence changed during evaluation')
