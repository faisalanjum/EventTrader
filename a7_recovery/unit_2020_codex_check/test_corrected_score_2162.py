"""The final caller must use every approved correction, not a partial base.

These focused configuration checks reuse the existing task/context fixtures;
the actual native scoring proof is separate and requires completed AI results.
"""
import copy
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_g2_key_reuse_2159 import selected, connection  # shared fixtures
import a7_g1_build as G
import a7_g23_build as B
import a7_grading_revision_2115 as REV
import a7_grading_input_correction_2114 as V
import score_corrected_grading_2162 as SUBJECT


@pytest.fixture
def revisions(connection, tmp_path):
    connection['run']()
    reuse_path = tmp_path / 'bridge.json'
    reuse_ref = {'path': str(reuse_path), 'sha256': G._sha_file(str(reuse_path))}
    current = connection['current']
    revision = {
        'schema': 'a7-grading-revision/v1',
        'code_sha256': G._sha_file(REV.__file__),
        'producer_identity': current['producer'],
        'g1_identity': B.g1_identity(current['g1']),
        'required_population': connection['population'],
        'base_sources': connection['sources'],
        'corrections': {
            kind: {'source': {'run_dir': kind, 'root_sha256': 'root',
                              'completion_sha256': 'completion'},
                   'population': population,
                   'input_correction_sha256': G._sha_file(V.__file__),
                   'reason': 'independently proved changed grading task'}
            for kind, population in {
                'G2': {'P1|source-z': [[8, 12]]},
                'G3': connection['population']['G3']}.items()}}
    path = tmp_path / 'revision.json'

    def run():
        path.write_text(json.dumps(revision))
        ref = {'path': str(path), 'sha256': G._sha_file(str(path))}
        return SUBJECT.validate_revision(reuse_ref, ref)

    return revision, run


def test_exact_approved_corrections_are_ready_for_the_existing_native_consumer(revisions):
    revision, run = revisions
    assert run() == revision


@pytest.mark.parametrize('change', ['missing_kind', 'missing_question', 'extra_question',
                                  'wrong_partner', 'wrong_input_version'])
def test_final_score_cannot_silently_omit_or_expand_the_reviewed_changes(revisions, change):
    revision, run = revisions
    test_exact_approved_corrections_are_ready_for_the_existing_native_consumer(revisions)
    if change == 'missing_kind':
        revision['corrections'].pop('G3')
    elif change == 'missing_question':
        revision['corrections']['G2']['population'] = {}
    elif change == 'extra_question':
        revision['corrections']['G2']['population']['P1|source-z'].append([2, 9])
    elif change == 'wrong_partner':
        revision['corrections']['G2']['population']['P1|source-z'][0][1] = 9
    else:
        revision['corrections']['G3']['input_correction_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        run()


@pytest.fixture
def caller(monkeypatch, tmp_path):
    """Caller-boundary doubles, not proof of native evidence or scoring rules."""
    import build_a5_exp5_kit as A5
    active = []
    producer, g1 = {'producer': 'current'}, {'pins': {'g1': 'current'}}
    sources = {'G2': {'run_dir': 'old-g2'}, 'G3': {'run_dir': 'old-g3'}}
    load_sources = [('new-g2', 'root-g2', 'completion-g2'),
                    ('new-g3', 'root-g3', 'completion-g3')]
    revision = {'base_sources': sources, 'corrections': {
        kind: {'source': dict(zip(('run_dir', 'root_sha256', 'completion_sha256'), handle))}
        for kind, handle in zip(('G2', 'G3'), load_sources)}}
    key = {'source-z': [{'du_worthy': True}]}
    ref = {'path': 'pinned-handle', 'sha256': 'a' * 64}
    mode = [None]
    monkeypatch.setattr(SUBJECT, 'validate_revision', lambda *_: revision)
    monkeypatch.setattr(SUBJECT.REUSE, '_pin', lambda r: None)
    format_pins = {'code_sha256': 'format-code', 'rule_sha256': 'format-rule'}
    monkeypatch.setattr(G, '_read', lambda path: {
        'script_binding': 'script-binding', 'g1': g1, 'format': format_pins})
    monkeypatch.setattr(G, 'live_key', lambda: (key, {'accepted_rows': 1}))
    monkeypatch.setattr(A5, 'ACTIVE_ARM_IDS', ['original-a', 'original-b'])
    legs = list(A5.ACTIVE_ARM_IDS) + [G.LEG_UNION]

    @contextmanager
    def scoped(name, *_):
        active.append(name)
        try:
            yield
        finally:
            assert active.pop() == name

    monkeypatch.setattr(SUBJECT.TRANSPORT, 'scope', lambda *a: scoped('transport', *a))
    monkeypatch.setattr(SUBJECT.REV, 'scope', lambda *a: scoped('revision', *a))
    monkeypatch.setattr(SUBJECT.DUP, 'scope', lambda *a: scoped('counter', *a))

    def format_scope(code_pin, rule_pin):
        assert (code_pin, rule_pin) == ('format-code', 'format-rule')
        return scoped('format')

    monkeypatch.setattr(SUBJECT.REUSE.FORMAT, 'scope', format_scope)

    def reuse(E, path, sha, action):
        assert active == ['transport'] and (path, sha) == (ref['path'], ref['sha256'])
        result = action(producer, {'verified': 'inputs'}, g1)
        assert active == ['transport']
        return result

    monkeypatch.setattr(SUBJECT.REUSE, 'evaluate', reuse)
    monkeypatch.setattr(B, '_scorer', lambda: SimpleNamespace())
    monkeypatch.setattr(B, 'route_for', lambda *a: None)
    monkeypatch.setattr(SUBJECT.C, 'load_g23', lambda *a: None)
    meanings = {('source-z', 0): {'driver_state': False}}
    extras = {('source-z', 2): 'unsupported'}
    monkeypatch.setattr(B, '_verdict_maps_from', lambda *a: (meanings, extras))

    def bound(bundle, leg, p, source, g):
        assert p == producer and g == g1 and source == sources
        B._verdict_maps_from(leg, source, p, {}, g, {})
        if mode[0] == 'double_judgment':
            B._verdict_maps_from(leg, source, p, {}, g, {})
        return {'gold_n': 0 if mode[0] == 'wrong_denominator' else 1, 'PASS': False}

    monkeypatch.setattr(B, '_score_leg_bound', bound)

    revision_mode = ['revision']

    def tier(p, by_leg, audit_root, g):
        assert active == ['transport', 'format', revision_mode[0], 'counter']
        assert p == producer and g == g1 and set(by_leg) == set(legs)
        for run_dir, root_sha, completion_sha in load_sources:
            SUBJECT.C.load_g23(run_dir + '-candidate', completion_sha, root_sha, run_dir)
        route = {'source-z': {'result': {'outcomes': []}, 'index_map': {('fact', 0): 0}}}
        bundle = {'arms': {leg: {'source-z': {'facts': [{'original': True}]}}
                           for leg in legs},
                  'derived': {'event_meta': {'source-z': {'event_date': '2026-01-01'}},
                              'resolutions': {leg: {('source-z', 0): 0} for leg in legs},
                              'routes': {leg: route for leg in legs}}}
        got = {}
        for leg in legs:
            B.route_for({'source-z': {}}, str(Path(audit_root) / leg))
            if mode[0] == 'double_route':
                B.route_for({'source-z': {}}, str(Path(audit_root) / leg))
            if mode[0] == 'missing_leg' and leg == legs[-1]:
                continue
            got[leg] = B._score_leg_bound(bundle, leg, p, by_leg[leg], g)
        return {leg: False for leg in A5.ACTIVE_ARM_IDS}, got

    monkeypatch.setattr(B, 'official_tier_decision', tier)
    E = SimpleNamespace(out=tmp_path, launch={'owners': {'grading_scorer': 'scorer-pin'}})
    original_owners = (B._score_leg_bound, B._verdict_maps_from, B.route_for, SUBJECT.C.load_g23)

    def run(**kwargs):
        return SUBJECT.run(E, ref, ref, ref, 'counter-pin', **kwargs)

    result = dict(run=run, mode=mode, path=tmp_path / 'A7_CORRECTED_SCORE.json',
                  active=active, owners=original_owners, meanings=meanings,
                  revision=revision, revision_ref=ref, load_sources=load_sources,
                  revision_mode=revision_mode, scope=scoped)

    def fresh_output():
        E.out = tmp_path / 'negative'
        E.out.mkdir()
        result['path'] = E.out / 'A7_CORRECTED_SCORE.json'

    result['fresh_output'] = fresh_output
    return result


def test_caller_uses_official_tier_once_and_keeps_false_partial_findings(caller):
    got = caller['run']()
    assert got['route_count'] == 3 and got['correction_completion_load_count'] == 2
    assert got['new_model_calls'] == 0 and all(x is False for x in got['decisions'].values())
    for row in got['cases'].values():
        assert row['meanings'] == [{'key': ['source-z', 0], 'value': {'driver_state': False}}]
        assert row['extras'] == [{'key': ['source-z', 2], 'value': 'unsupported'}]
        assert row['route']['source-z']['index_map'] == [{'key': ['fact', 0], 'value': 0}]
    assert caller['path'].exists() and not caller['active']
    assert (B._score_leg_bound, B._verdict_maps_from, B.route_for, SUBJECT.C.load_g23) == caller['owners']
    got['cases']['original-a']['meanings'][0]['value']['driver_state'] = True
    assert caller['meanings'][('source-z', 0)]['driver_state'] is False


@pytest.mark.parametrize('failure', ['double_route', 'double_judgment', 'missing_leg', 'wrong_denominator'])
def test_caller_does_not_save_a_score_with_an_incomplete_or_repeated_derivation(caller, failure):
    test_caller_uses_official_tier_once_and_keeps_false_partial_findings(caller)
    caller['fresh_output']()
    caller['mode'][0] = failure
    with pytest.raises((ValueError, AssertionError)):
        caller['run']()
    assert not caller['path'].exists() and not caller['active']
    assert (B._score_leg_bound, B._verdict_maps_from, B.route_for, SUBJECT.C.load_g23) == caller['owners']
