"""Focused source-view regressions; no model calls or original evidence edits."""
import copy
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

A7 = Path(__file__).resolve().parents[1]
for relative in ('grader_20260909/harness_g1v3', 'unit_2008/harness_g1v3',
                 'unit_2006/harness_g1v3'):
    sys.path.insert(0, str(A7 / relative))

import a7_g1_build as G
import a7_g23_build as OLD
import a7_grading_input_correction_2114 as SUBJECT


def token(qname, member):
    return 'unknown:xbrlaxis_' + qname.encode('utf-8').hex() + '__' + member


@pytest.fixture
def source(monkeypatch):
    raw_token = token('custom:CustomerChannelAxis', 'new_channel')
    raw = {
        'source_id': 'unfamiliar-source', 'event_date': '2026-02-15',
        'fye_month': 8,
        'text_parts': [{'part': 'body', 'content':
                        'The new channel reported five units. Footnote: the count excludes trials.'}],
        'menu_tokens': [raw_token, 'geography:north'],
    }
    context = OLD.event_context(raw)
    assert context['menu'] == ['unknown:custom:CustomerChannelAxis__new_channel',
                               'geography:north']
    run, inputs = {'identity': 'fixture-run'}, {'identity': 'fixture-inputs'}

    def verified(got_inputs, sid, got_run):
        assert (got_inputs, sid, got_run) == (inputs, raw['source_id'], run)
        return copy.deepcopy(context)

    monkeypatch.setattr(OLD, 'verified_event_context', verified)
    monkeypatch.setattr(OLD, 'reference_card', lambda f, sid, i, run:
                        {'quote': f['item']['quote'], 'reference_name': 'raw source claim',
                         'values': [5]})
    monkeypatch.setattr(OLD, 'GRADING_SCORER', None)
    monkeypatch.setattr(OLD, 'GRADING_SCORER_PROVENANCE', None)
    path = str(A7 / 'unit_2008/harness_g1v3/scorers/score_exp5_current.py')
    OLD.bind_grading_scorer(path, G._sha_file(path))
    fact = {'fact_type': 'metric', 'per_x': None, 'part_ref': 'body',
            'occurrence_in_part': None,
            'item': {'driver_name': 'unit_count', 'quote': 'The new channel reported five units.',
                     'slice_parts': [raw_token], 'driver_state': 'reported'},
            'du_worthy': True, 'gold_extra': {'must_never_be_shown': True}}
    return raw, run, inputs, fact


def test_meaning_record_uses_the_same_readable_population_as_its_menu(source):
    raw, run, inputs, fact = source
    before = copy.deepcopy(fact)
    packet = SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                    [fact], [fact], run, inputs=inputs)
    shown = packet['questions'][0]['produced_record']
    assert shown['item']['slice_parts'] == packet['event_context']['menu'][:1]
    assert shown['item']['quote'] == fact['item']['quote']
    assert 'gold_extra' not in shown and 'du_worthy' not in shown
    assert fact == before
    body = json.loads(packet['prompt'].split('[EVENT]\n', 1)[1])
    assert body['questions'] == packet['questions']


def test_extras_packet_and_batch_keep_the_verified_source_context(source):
    raw, run, inputs, fact = source
    other = copy.deepcopy(fact)
    other['item']['quote'] = 'The count excludes trials.'
    before = copy.deepcopy([fact, other])
    packet = SUBJECT.extras_packet(
        'P2', raw['source_id'], [0], [fact, other], [(0, fact)], run,
        inputs=inputs,
        # the OTHER row is the matched one, so it stays a comparison record
        matched_pairs={'P2|' + raw['source_id']: [[0, 1]]})
    expected = {k: v for k, v in OLD.event_context(raw).items() if k != '_source_id'}
    assert packet['event_context'] == expected
    assert packet['questions'][0]['produced_record']['item']['slice_parts'] == expected['menu'][:1]
    assert packet['other_records'][0]['produced_record']['item']['slice_parts'] == expected['menu'][:1]
    batch = SUBJECT.batch_packet('G3', [packet])
    body = json.loads(batch['prompt'].split('[EVENT]\n', 1)[1])
    assert body['events'][0]['event_context'] == expected
    assert body['events'][0]['questions'] == packet['questions']
    assert '_source_id' not in body['events'][0]['event_context']
    assert [fact, other] == before


@pytest.mark.parametrize('qname,member', [
    ('custom:DifferentAxis', 'unfamiliar_member'), ('ex:ÉlémentAxis', 'canal'),
])
def test_unfamiliar_canonical_axes_and_off_menu_text_are_lossless(source, qname, member):
    _raw, _run, _inputs, fact = source
    fact = copy.deepcopy(fact)
    picks = [token(qname, member), 'geography:north', 'unknown:an unfamiliar source span',
             'unknown:xbrlaxis_zz__broken', 'unknown:xbrlaxis_ff__bad_utf8']
    fact['item']['slice_parts'] = picks
    fact['item']['level_low'] = {'value': '1.000000000000000000001',
                                 'scale_multiplier': 1000, 'unit_scale_evidence': 'thousand'}
    before = copy.deepcopy(fact)
    shown = SUBJECT.record_view(fact)
    assert shown['item']['slice_parts'] == ['unknown:' + qname + '__' + member] + picks[1:]
    assert shown['item']['level_low'] == before['item']['level_low']
    assert fact == before


def test_a_complete_zero_match_inventory_is_not_missing_evidence(source):
    raw, run, inputs, fact = source
    group = 'P1|' + raw['source_id']
    asked = {group: [0]}

    def packet(canonical):
        return SUBJECT.extras_packet(
            'P1', raw['source_id'], [0], [fact, copy.deepcopy(fact)], [(0, fact)],
            run, inputs=inputs,
            matched_pairs=SUBJECT.matched_inventory(canonical, asked))

    control = packet({group: [[0, 1]]})
    assert len(control['other_records']) == 1
    # Explicit zero and the canonical sparse representation mean the same
    # thing, even when no other event happened to produce a matched pair.
    for canonical in ({group: []}, {}):
        empty = packet(canonical)
        assert empty['other_records'] == []
        for field in ('questions', 'reference_cards', 'event_context'):
            assert empty[field] == control[field]
    for absent in (None, [], ''):
        with pytest.raises(ValueError):
            SUBJECT.matched_inventory(absent, asked)


def test_all_saved_facts_change_only_the_24_proved_display_occurrences():
    root = Path(__file__).parent / 'codex_scoretrace2112_a'
    data = (root / 'SCORER_TRACE.json').read_bytes()
    assert hashlib.sha256(data).hexdigest() == '0b4a3f624a4024fb071fff1740f04b186027b2c91bcade2aaba4ce6bb05f7ee4'
    evidence = (root / 'DISPLAY_GAP_2113.json').read_bytes()
    assert hashlib.sha256(evidence).hexdigest() == '4d2594c7d655aa258718bdbe3af9793f8a3f297d77fea2be9163204ca5ca55d9'
    mapping = {r['raw']: r['shown'] for r in json.loads(evidence)['rows']}
    # Independent representation check, not the decoder being called by the fix.
    for raw, shown in mapping.items():
        encoded, member = raw.removeprefix('unknown:xbrlaxis_').split('__', 1)
        assert shown == 'unknown:' + bytes.fromhex(encoded).decode('utf-8') + '__' + member
    total = changed = 0
    for leg in json.loads(data)['records'].values():
        for answer in leg['inputs']['arm_by_event'].values():
            for fact in answer['facts']:
                total += 1
                before = copy.deepcopy(fact)
                expected = copy.deepcopy(G._display(fact))
                picks = expected['item']['slice_parts']
                changed += sum(p in mapping for p in picks)
                expected['item']['slice_parts'] = [mapping.get(p, p) for p in picks]
                assert SUBJECT.record_view(fact) == expected
                assert fact == before
    assert (total, changed) == (560, 24)


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_missing_or_cross_event_context_refuses_with_a_valid_control(source, monkeypatch, kind):
    raw, run, inputs, fact = source

    def build(given):
        if kind == 'G2':
            return SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                          [fact], [fact], run, inputs=given)
        return SUBJECT.extras_packet(
            'P1', raw['source_id'], [0], [fact], [(0, fact)], run,
            inputs=given, matched_pairs={'P1|' + raw['source_id']: []})

    assert build(inputs)['event_context']['event_date'] == raw['event_date']
    with pytest.raises(ValueError, match='verified source inputs'):
        build(None)
    valid = OLD.verified_event_context

    def wrong(*args):
        return dict(valid(*args), _source_id='another-event')

    monkeypatch.setattr(OLD, 'verified_event_context', wrong)
    with pytest.raises(ValueError, match='different source|context came from'):
        build(inputs)
    monkeypatch.setattr(OLD, 'verified_event_context', valid)
    assert build(inputs)['event_context']['fye_month'] == raw['fye_month']


def test_batch_rejects_an_old_or_different_correction_version(source):
    raw, run, inputs, fact = source
    good = SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                  [fact], [fact], run, inputs=inputs)
    assert SUBJECT.batch_packet('G2', [good])['question_ids'] == good['question_ids']
    for value in (None, '0' * 64):
        stale = dict(good)
        if value is None:
            stale.pop('input_correction_sha256')
        else:
            stale['input_correction_sha256'] = value
        with pytest.raises(ValueError, match='correction version'):
            SUBJECT.batch_packet('G2', [stale])


def test_rules_and_parser_keep_all_three_literal_results_without_examples(source):
    rules = SUBJECT.meaning_rules()
    output = rules.split('[OUTPUT]\n', 1)[1].split(G.BOUNDARY, 1)[0]
    assert '<true | false | null>' not in output
    assert 'unquoted JSON true, false, or null, never a string' in output
    assert "against the company's own prior guide, not projected business growth" in rules
    assert 'Direction follows the signed numerical axis' in rules
    fields = OLD.meaning_fields()
    for value in (True, False, None):
        row = {'question_id': 'new-id', 'verdicts': dict.fromkeys(fields, value)}
        parsed, problems = OLD.read_meaning_reply(json.dumps([row]), {'question_ids': ['new-id']})
        assert not problems and parsed == {'new-id': row['verdicts']}
    assert 'full verified source' in SUBJECT.extras_rules()


def test_frozen_packet_owners_stay_unchanged():
    assert G._sha_file(G.__file__) == '5523c5b6b8fdc4701730c21e5022693eab0a7f8384c81efdcddf4539e5cf1439'
    assert G._sha_file(OLD.__file__) == '3ca73c35163fdb3c39623711b78e9f0ea3a0c6ed30fdcec943d57ca1deaac79e'


def test_omitted_default_population_is_preserved_without_inventing_fields(source):
    fact = copy.deepcopy(source[3])
    del fact['item']['slice_parts']
    before = copy.deepcopy(fact)
    assert SUBJECT.record_view(fact) == G._display(before)
    assert fact == before


@pytest.mark.parametrize('state,quote', [
    ('introduced', 'The company issued its first outlook for fiscal 2028.'),
    ('withdrawn', 'The company withdrew its outlook for fiscal 2028.'),
])
def test_assembled_guidance_instructions_do_not_require_a_prior_guide_for_every_state(
        source, monkeypatch, state, quote):
    raw, run, inputs, fact = source
    fact = copy.deepcopy(fact)
    fact['fact_type'] = 'guidance'
    fact['item']['driver_state'] = state
    fact['item']['quote'] = quote
    raw = copy.deepcopy(raw)
    raw['text_parts'] = [{'part': 'body', 'content': quote}]
    monkeypatch.setattr(OLD, 'verified_event_context', lambda *args: OLD.event_context(raw))
    packet = SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                    [fact], [fact], run, inputs=inputs)
    rules, body = packet['prompt'].split('[EVENT]\n', 1)
    assert ('source-stated introduction, revision, reaffirmation or withdrawal'
            in rules)
    assert 'movement means a revision' not in rules
    shown = json.loads(body)['questions'][0]['produced_record']
    assert shown['item']['driver_state'] == state
    assert shown['item']['quote'] == quote


@pytest.mark.parametrize('text', ['', 'anchor anchor'])
def test_changed_instruction_anchor_refuses_instead_of_guessing(text):
    assert SUBJECT._replace_once('prefix anchor suffix', 'anchor', 'new') == 'prefix new suffix'
    with pytest.raises(ValueError, match='instruction changed'):
        SUBJECT._replace_once(text, 'anchor', 'new')


@pytest.mark.parametrize('old,new,check_name', [
    ('parts[i] = display[0]', 'parts[i] = token',
     'test_meaning_record_uses_the_same_readable_population_as_its_menu'),
    ("if context.pop('_source_id', None) != source_id:",
     "if context.pop('_source_id', None) is None:",
     'test_cross_event_extras_mutation_control'),
    ("packet.get('input_correction_sha256') != expected", 'False',
     'test_batch_rejects_an_old_or_different_correction_version'),
    ("'event_context': OLD._required_context(packet, n),",
     "'event_context': {},",
     'test_extras_packet_and_batch_keep_the_verified_source_context'),
])
def test_meaningful_mutations_are_detected_with_positive_controls(source, monkeypatch, old, new, check_name):
    check = globals()[check_name]
    if check_name == 'test_cross_event_extras_mutation_control':
        check(source, monkeypatch)
    else:
        check(source)
    text = Path(SUBJECT.__file__).read_text()
    assert text.count(old) == 1
    changed = types.ModuleType('test_mutated_grading_input')
    changed.__file__ = SUBJECT.__file__
    exec(compile(text.replace(old, new), changed.__file__, 'exec'), changed.__dict__)
    monkeypatch.setattr(sys.modules[__name__], 'SUBJECT', changed)
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        if check_name == 'test_cross_event_extras_mutation_control':
            check(source, monkeypatch)
        else:
            check(source)


def test_cross_event_extras_mutation_control(source, monkeypatch):
    test_missing_or_cross_event_context_refuses_with_a_valid_control(source, monkeypatch, 'G3')
