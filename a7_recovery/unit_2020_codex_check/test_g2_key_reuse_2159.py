"""Full task identity first; native consumer proof is a separate real run."""
import copy
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import types

import pytest

A7 = Path(__file__).resolve().parents[1]
for relative in ('grader_20260909/harness_g1v3', 'unit_2008/harness_g1v3',
                 'unit_2006/harness_g1v3', 'unit_2009/owner'):
    sys.path.insert(0, str(A7 / relative))

import a7_g1_build as G
import a7_g23_build as B
import a7_grading_input_correction_2114 as V
import a7_g2_key_reuse_2159 as SUBJECT


@pytest.fixture
def selected(tmp_path):
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
        return {'path': str(path), 'sha256': G._sha_file(str(path))}

    fact = {'fact_type': 'metric', 'item': {
        'driver_name': 'unfamiliar_quantity', 'driver_state': 'reported',
        'slice_parts': [], 'quote': 'The amount was five.'}}
    card = {'quote': fact['item']['quote'], 'reference_name': 'the amount',
            'values': [5]}
    context = {'fye_month': 8, 'menu': [], 'text': 'The amount was five.'}

    def candidate(name, population):
        rows, events = [], []
        for group, pairs in population.items():
            leg, sid = group.split('|')
            for gi, pi in pairs:
                qid = B.meaning_question_id(leg, sid, gi, pi)
                q = {'question_id': qid, 'produced_record': copy.deepcopy(fact),
                     'reference_card': copy.deepcopy(card)}
                events.append({'event': 'E%d' % len(events),
                               'event_context': copy.deepcopy(context), 'questions': [q]})
        body = {'events': events}
        prompt = tmp_path / name / 'prompt.txt'
        prompt.parent.mkdir()
        prompt.write_text('original rules\n[EVENT]\n' + json.dumps(body), encoding='utf-8')
        rows.append({'batch_id': 'G2-000', 'question_ids': [
            q['question_id'] for e in events for q in e['questions']],
                     'prompt_path': prompt.name, 'prompt_sha256': G._sha_file(str(prompt))})
        doc = {'task_kind': 'G2', 'questions': len(events), 'population': population,
               'batch_rows': rows, 'producer_identity': {'id': name}}
        ref = write(prompt.parent / G.CANDIDATE_NAME, doc)
        return {'ref': ref, 'doc': doc, 'body': body, 'prompt': prompt}

    old = candidate('old', {'P1|source-z': [[1, 7], [2, 9]], 'P2|other': [[3, 4]]})
    current = candidate('current', {'P1|source-z': [[5, 7], [2, 9], [8, 12]],
                                    'P2|other': [[3, 4]]})
    ids = [q['question_id'] for e in current['body']['events'] for q in e['questions']]
    review = tmp_path / 'review.md'
    review.write_text('Independent task-materiality decision, not a verdict.')
    selection = {
        'schema': 'a7-g2-reuse-selection/v1', 'reviewer_session': 'independent-reviewer',
        'review': {'path': str(review), 'sha256': G._sha_file(str(review))},
        'renderer': {'path': V.__file__, 'sha256': G._sha_file(V.__file__)},
        'original_candidate': old['ref'], 'current_candidate': current['ref'],
        'rows': [{'question_id': q, 'decision': 'correct' if n == 2 else 'carry',
                  'reason': 'independently reviewed task'} for n, q in enumerate(ids)]}
    path = tmp_path / 'selection.json'

    def save():
        for src in (old, current):
            src['prompt'].write_text('original rules\n[EVENT]\n' + json.dumps(src['body']))
            src['doc']['batch_rows'][0]['prompt_sha256'] = G._sha_file(str(src['prompt']))
            src['ref'].update(write(Path(src['ref']['path']), src['doc']))
        write(path, selection)
        return str(path), G._sha_file(str(path))

    return dict(old=old, current=current, selection=selection, save=save,
                ids=ids, path=path, review=review)


def test_exact_task_can_move_gold_index_without_reasking(selected):
    got = SUBJECT.derive(*selected['save']())
    new = selected['ids'][0]
    old = B.meaning_question_id('P1', 'source-z', 1, 7)
    assert got['carry'][new] == old
    assert len(got['carry']) == 3
    assert got['correction_population'] == {'P1|source-z': [[8, 12]]}
    assert got['current_tasks'][new]['pair'] == [5, 7]
    assert got['original_tasks'][old]['pair'] == [1, 7]


@pytest.mark.parametrize('part', ['quote', 'reference', 'source_context'])
def test_changed_task_cannot_carry_even_with_newly_supplied_file_hashes(selected, part):
    test_exact_task_can_move_gold_index_without_reasking(selected)
    event = selected['current']['body']['events'][0]
    q = event['questions'][0]
    if part == 'quote':
        q['produced_record']['item']['quote'] = 'The amount was six.'
    elif part == 'reference':
        q['reference_card']['values'] = [6]
    else:
        event['event_context']['fye_month'] = 9
    with pytest.raises(ValueError, match='unchanged task'):
        SUBJECT.derive(*selected['save']())


def test_changed_display_cannot_be_declared_unchanged(selected):
    test_exact_task_can_move_gold_index_without_reasking(selected)
    token = 'unknown:xbrlaxis_' + 'custom:RegionAxis'.encode().hex() + '__zone'
    for src in (selected['old'], selected['current']):
        src['body']['events'][0]['questions'][0]['produced_record']['item']['slice_parts'] = [token]
    with pytest.raises(ValueError, match='display'):
        SUBJECT.derive(*selected['save']())


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'unknown', 'unknown_decision', 'blank_reason'])
def test_every_current_question_has_exactly_one_reasoned_disposition(selected, change):
    test_exact_task_can_move_gold_index_without_reasking(selected)
    rows = selected['selection']['rows']
    if change == 'missing':
        rows.pop()
    elif change == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
    elif change == 'unknown':
        rows[0]['question_id'] = 'unasked'
    elif change == 'unknown_decision':
        rows[0]['decision'] = 'maybe'
    else:
        rows[0]['reason'] = ' '
    with pytest.raises(ValueError):
        SUBJECT.derive(*selected['save']())


def test_two_original_claims_with_identical_views_are_not_arbitrarily_selected(selected):
    test_exact_task_can_move_gold_index_without_reasking(selected)
    src = selected['old']
    src['doc']['population']['P1|source-z'].append([6, 7])
    extra = copy.deepcopy(src['body']['events'][0])
    extra['questions'][0]['question_id'] = B.meaning_question_id('P1', 'source-z', 6, 7)
    src['body']['events'].append(extra)
    src['doc']['questions'] += 1
    src['doc']['batch_rows'][0]['question_ids'].append(extra['questions'][0]['question_id'])
    with pytest.raises(ValueError, match='unique unchanged task'):
        SUBJECT.derive(*selected['save']())


@pytest.mark.parametrize('part', ['prompt', 'candidate', 'review', 'selection'])
def test_stale_pinned_bytes_refuse(selected, part):
    path, pin = selected['save']()
    SUBJECT.derive(path, pin)
    target = {'prompt': selected['old']['prompt'],
              'candidate': Path(selected['old']['ref']['path']),
              'review': selected['review'], 'selection': Path(path)}[part]
    target.write_text(target.read_text() + ' ')
    with pytest.raises(ValueError):
        SUBJECT.derive(path, pin)


def test_prompt_population_is_bound_not_assumed_from_count(selected):
    test_exact_task_can_move_gold_index_without_reasking(selected)
    selected['current']['body']['events'][0]['questions'][0]['question_id'] = selected['ids'][1]
    with pytest.raises(ValueError):
        SUBJECT.derive(*selected['save']())


@pytest.fixture
def connection(selected, monkeypatch, tmp_path):
    """Boundary doubles only; the real saved-run consumer is checked separately."""
    import a7_g1_complete_v2 as C
    import a7_g1_key_reuse_2152 as REUSE
    import a7_meaning_format_2105 as FORMAT

    selection_path, selection_pin = selected['save']()
    old_producer = selected['old']['doc']['producer_identity']
    producer = selected['current']['doc']['producer_identity']
    old_g1, g1 = {'pins': {'identity': 'old'}}, {'pins': {'identity': 'current'}}
    old_key, key = {'key': 'old'}, {'key': 'current'}
    old_pop = {'G2': selected['old']['doc']['population'], 'G3': {'P1|source-z': [15]}}
    population = {'G2': selected['current']['doc']['population'], 'G3': {'P1|source-z': [16]}}
    sources = {kind: dict(run_dir=kind, root_sha256=kind+'root', completion_sha256=kind+'done')
               for kind in old_pop}
    key_now, calls, maps = [old_key], [], {
        'P1': ({('source-z', 1): {'driver_state': True},
                ('source-z', 2): {'record_matches_source': False}},
               {('source-z', 15): 'duplicate'}),
        'P2': ({}, {})}

    def write(name, doc):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        return dict(path=str(path), sha256=G._sha_file(str(path)))

    old = dict(producer_identity=old_producer, key_identity=old_key, g1=old_g1,
               g23_sources=sources, required_population=old_pop)
    candidate3 = dict(task_kind='G3', producer_identity=producer, g1_identity=g1['pins'],
                      population=population['G3'])
    g3ref = write('current-g3/'+G.CANDIDATE_NAME, candidate3)
    current = dict(producer=producer, g1=g1, key_identity=key,
                   candidates={'G2': selected['current']['ref'], 'G3': g3ref})
    report = write('g1-report.json', {'scope': 'fixture'})
    plan = dict(schema='a7-g2-key-reuse/v1', code_sha256=G._sha_file(SUBJECT.__file__),
                selection=dict(path=selection_path, sha256=selection_pin),
                original_proof=write('old.json', old),
                current_preparation=write('current.json', current),
                g1_reuse_report=report,
                format={'code_sha256': G._sha_file(FORMAT.__file__),
                        'rule_sha256': G._sha_file(str(FORMAT.RULE_FILE))})

    def prepared(action):
        key_now[0] = old_key
        return action(old_producer, {'source': 'verified'})

    E = SimpleNamespace(g1=old_g1, with_prepared_inputs=prepared)

    def evaluate(got_e, got_report, got_g1, action):
        assert got_e is E and got_report == report['path'] and got_g1 == g1
        def checked(got_producer, inputs):
            assert got_producer == old_producer and key_now[0] == old_key
            key_now[0] = key
            return action(producer, inputs, g1)
        return E.with_prepared_inputs(checked)

    def native(leg, got_sources, got_producer, required, got_g1, memo):
        if got_sources != {'G2': sources['G2']}:
            calls.append(('fresh', leg))
            result = [{}, {}]
            for kind, src in got_sources.items():
                if 'root_sha256' in src:
                    memo[(kind, src['run_dir'], src['root_sha256'], src['completion_sha256'])] = (
                        {'input_correction_sha256': 'b'*64, 'matched_population': population['G2']}, {})
                result[kind == 'G3'] = ({('source-z', 8): {'driver_state': False}}
                                        if kind == 'G2' else {('source-z', 16): 'unsupported'})
            return tuple(result)
        assert key_now[0] == old_key and got_producer == old_producer
        assert required == old_pop and got_g1 == old_g1
        calls.append(('original', leg))
        for kind, src in got_sources.items():
            candidate = (selected['old']['doc'] if kind == 'G2' else
                         dict(task_kind='G3', population=old_pop['G3']))
            memo[(kind, src['run_dir'], src['root_sha256'], src['completion_sha256'])] = (
                copy.deepcopy(candidate), {'run_identity': {'run_digest': kind+'digest', 'run_files': 2}})
        return copy.deepcopy(maps[leg])

    @contextmanager
    def format_scope(expected_code_sha256, expected_rule_sha256):
        assert expected_code_sha256 == plan['format']['code_sha256']
        assert expected_rule_sha256 == plan['format']['rule_sha256']
        yield

    monkeypatch.setattr(REUSE, 'evaluate', evaluate)
    monkeypatch.setattr(FORMAT, 'scope', format_scope)
    monkeypatch.setattr(G, 'live_key', lambda: ({}, key_now[0]))
    monkeypatch.setattr(B, '_verdict_maps_from', native)
    monkeypatch.setattr(C, 'run_digest', lambda path: (path+'digest', 2))

    def run(action=None):
        ref = write('bridge.json', plan)
        if action is None:
            action = lambda p, _i, g: {leg: B.official_verdict_maps(leg, sources, p, population, g)
                                      for leg in ('P1', 'P2')}
        return SUBJECT.evaluate(E, ref['path'], ref['sha256'], action)

    return dict(run=run, E=E, plan=plan, prepared=prepared, native=native, calls=calls,
                maps=maps, population=population, sources=sources, key_now=key_now,
                selected=selected, old=old, current=current)


def test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection):
    got = connection['run']()
    assert got == {'P1': ({('source-z', 5): {'driver_state': True},
                           ('source-z', 2): {'record_matches_source': False}}, {}),
                   'P2': ({}, {})}
    assert connection['calls'] == [('original', 'P1'), ('original', 'P2')]
    assert B._verdict_maps_from is connection['native']
    assert connection['E'].with_prepared_inputs is connection['prepared']
    got['P1'][0][('source-z', 5)]['driver_state'] = None
    assert connection['maps']['P1'][0][('source-z', 1)]['driver_state'] is True


@pytest.mark.parametrize('part', ['producer', 'g1', 'population', 'key'])
def test_current_consumer_identity_drift_refuses(connection, part):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    def action(producer, _inputs, g1):
        required = copy.deepcopy(connection['population'])
        if part == 'producer': producer = {'id': 'wrong'}
        if part == 'g1': g1 = {'pins': {'identity': 'wrong'}}
        if part == 'population': required['G2']['P1|source-z'][0][1] += 1
        if part == 'key': connection['key_now'][0] = {'key': 'wrong'}
        return B.official_verdict_maps('P1', connection['sources'], producer, required, g1)
    with pytest.raises(ValueError):
        connection['run'](action)
    assert B._verdict_maps_from is connection['native']


def test_native_refusal_is_not_replaced_with_saved_summary(connection, monkeypatch):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    def refused(*args):
        raise ValueError('native whole completion does not rederive')
    monkeypatch.setattr(B, '_verdict_maps_from', refused)
    with pytest.raises(ValueError, match='whole completion'):
        connection['run']()
    assert B._verdict_maps_from is refused
    assert connection['E'].with_prepared_inputs is connection['prepared']


def test_fresh_corrective_sources_still_use_existing_native_owner(connection):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    got = connection['run'](lambda p, _i, g: B.official_verdict_maps(
        'P1', {'G2': {'run_dir': 'new-correction'}}, p, {'G2': {'P1|source-z': [[8, 12]]}}, g))
    assert got == ({('source-z', 8): {'driver_state': False}}, {})
    assert connection['calls'][-1] == ('fresh', 'P1')


@pytest.mark.parametrize('field', ['schema', 'code_sha256'])
def test_bridge_schema_and_owner_are_frozen(connection, field):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    connection['plan'][field] = 'wrong'
    with pytest.raises(ValueError):
        connection['run']()


def test_native_run_changed_during_current_evaluation_refuses(connection, monkeypatch):
    import a7_g1_complete_v2 as C
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    def action(p, _i, g):
        result = B.official_verdict_maps('P1', connection['sources'], p, connection['population'], g)
        monkeypatch.setattr(C, 'run_digest', lambda path: ('changed', 2))
        return result
    with pytest.raises(ValueError, match='evidence changed'):
        connection['run'](action)


def test_actual_revision_owner_adds_only_corrected_tasks_to_the_carried_base(connection, tmp_path):
    import a7_grading_revision_2115 as REV
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    def action(p, _i, g):
        plan = dict(schema='a7-grading-revision/v1', code_sha256=G._sha_file(REV.__file__),
                    producer_identity=p, g1_identity=B.g1_identity(g),
                    required_population=connection['population'], base_sources=connection['sources'],
                    corrections={kind: dict(source=dict(run_dir='new-'+kind, root_sha256=kind+'root',
                                                        completion_sha256=kind+'complete'),
                                             population=population, input_correction_sha256='b'*64,
                                             reason='changed task inputs') for kind, population in {
                        'G2': {'P1|source-z': [[8, 12]]}, 'G3': connection['population']['G3']}.items()})
        path = tmp_path/'revision.json'
        path.write_text(json.dumps(plan))
        with REV.scope(str(path), G._sha_file(str(path))):
            return B.official_verdict_maps('P1', connection['sources'], p, connection['population'], g)
    got = connection['run'](action)
    assert got == ({('source-z', 5): {'driver_state': True},
                    ('source-z', 2): {'record_matches_source': False},
                    ('source-z', 8): {'driver_state': False}},
                   {('source-z', 16): 'unsupported'})
    assert connection['calls'][-2:] == [('fresh', 'P1'), ('fresh', 'P1')]


def test_native_candidate_must_equal_the_selected_original(connection):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    connection['selected']['old']['doc']['producer_identity'] = {'id': 'changed'}
    with pytest.raises(ValueError, match='original native candidate'):
        connection['run']()


def test_selection_edit_during_evaluation_is_not_hidden(connection):
    test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection)
    def action(p, i, g):
        path = connection['selected']['path']
        path.write_text(path.read_text()+' ')
        return {}
    with pytest.raises(ValueError, match='unapproved'):
        connection['run'](action)


@pytest.mark.parametrize('old,new,check,argument', [
    ("task['group'], task['pair'][1], rules, event['event_context'],",
     "task['group'], task['pair'][1], rules, {},",
     'test_changed_task_cannot_carry_even_with_newly_supplied_file_hashes', 'source_context'),
    ("or G._sha_file(ref['path']) != ref['sha256']", 'or False',
     'test_stale_pinned_bytes_refuse', 'review'),
])
def test_task_guard_mutations_fail_the_same_positive_control(selected, monkeypatch, old, new, check, argument):
    run = globals()[check]
    frozen = copy.deepcopy((selected['old']['body'], selected['current']['body']))
    review = selected['review'].read_bytes()
    run(selected, argument)
    selected['old']['body'], selected['current']['body'] = frozen
    selected['review'].write_bytes(review)
    text = Path(SUBJECT.__file__).read_text()
    assert text.count(old) == 1
    mutant = types.ModuleType('mutated_g2_key_reuse')
    mutant.__file__ = SUBJECT.__file__
    exec(compile(text.replace(old, new), mutant.__file__, 'exec'), mutant.__dict__)
    monkeypatch.setattr(sys.modules[__name__], 'SUBJECT', mutant)
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        run(selected, argument)


@pytest.mark.parametrize('old,new,part', [
    ("(sid, previous['pair'][0]), (sid, new['pair'][0])",
     "(sid, new['pair'][0]), (sid, new['pair'][0])", None),
    ("copy.deepcopy(native_maps[leg][old_index])",
     "dict(copy.deepcopy(native_maps[leg][old_index]), invented_aspect=True)", None),
    ("same(want, required, 'consumer full population')", 'pass', 'population'),
    ('return result, {}  # all original G3 judgments remain excluded',
     "return result, {('source-z', 15): 'duplicate'}", None),
])
def test_native_connection_mutations_fail_with_positive_control(connection, monkeypatch, old, new, part):
    check = (lambda: test_current_consumer_identity_drift_refuses(connection, part)) if part else (
        lambda: test_public_bridge_enters_both_contexts_and_preserves_partial_and_missing(connection))
    check()
    connection['calls'].clear()
    text = Path(SUBJECT.__file__).read_text()
    assert text.count(old) == 1
    mutant = types.ModuleType('mutated_g2_key_reuse')
    mutant.__file__ = SUBJECT.__file__
    exec(compile(text.replace(old, new), mutant.__file__, 'exec'), mutant.__dict__)
    monkeypatch.setattr(sys.modules[__name__], 'SUBJECT', mutant)
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        check()
