"""Final caller ordering and accounting; native evidence proof stays separate."""
import copy
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path

import pytest

from test_corrected_score_2162 import caller, SUBJECT


@pytest.fixture
def later(caller, monkeypatch):
    ref = {'path': 'later-pinned-revision', 'sha256': 'b' * 64}
    handle = ('later-run', 'later-root', 'later-completion')
    plan = {'base_sources': caller['revision']['base_sources'], 'corrections': {
        'G2': {'source': dict(zip(('run_dir', 'root_sha256', 'completion_sha256'), handle)),
               'input_correction_sha256': 'c' * 64}}}
    original_read = SUBJECT.G._read
    monkeypatch.setattr(SUBJECT.G, '_read', lambda path:
                        copy.deepcopy(plan) if path == ref['path'] else original_read(path))
    seen = []

    @contextmanager
    def chain_scope(refs, owner_pin):
        assert refs == [caller['revision_ref'], ref]
        assert owner_pin == 'chain-owner-pin'
        seen.append(copy.deepcopy(refs))
        with caller['scope']('chain'):
            yield

    # Explicit caller-boundary spy: the real chain/evidence owner is tested
    # separately, not replaced in the native lifecycle checks.
    monkeypatch.setattr(SUBJECT, 'CHAIN', SimpleNamespace(scope=chain_scope), raising=False)
    caller['revision_mode'][0] = 'chain'
    caller['load_sources'].append(handle)

    def run():
        return caller['run'](later_revisions=[ref], chain_sha256='chain-owner-pin')

    return dict(run=run, ref=ref, plan=plan, seen=seen, caller=caller)


def test_final_caller_applies_old_then_new_and_records_every_completion(later):
    got = later['run']()
    assert got['revision_sequence'] == [later['caller']['revision_ref'], later['ref']]
    assert got['correction_chain_sha256'] == 'chain-owner-pin'
    assert got['correction_completion_load_count'] == 3
    assert got['route_count'] == 3 and got['new_model_calls'] == 0
    assert len(later['seen']) == 1
    assert all(value is False for value in got['decisions'].values())
    assert not later['caller']['active']


@pytest.mark.parametrize('failure', ['missing', 'duplicate', 'wrong_root', 'wrong_completion'])
def test_later_completion_accounting_cannot_be_skipped_or_swapped(later, failure):
    test_final_caller_applies_old_then_new_and_records_every_completion(later)
    caller = later['caller']
    caller['fresh_output']()
    loads = caller['load_sources']
    if failure == 'missing':
        loads.pop()
    elif failure == 'duplicate':
        loads.append(loads[-1])
    else:
        row = list(loads[-1])
        row[1 if failure == 'wrong_root' else 2] = 'another-pinned-identity'
        loads[-1] = tuple(row)
    with pytest.raises((ValueError, AssertionError)):
        later['run']()
    assert not caller['path'].exists() and not caller['active']
    assert (SUBJECT.B._score_leg_bound, SUBJECT.B._verdict_maps_from,
            SUBJECT.B.route_for, SUBJECT.C.load_g23) == caller['owners']


@pytest.mark.parametrize('options', [
    {'later_revisions': [], 'chain_sha256': 'unused-owner-pin'},
    {'later_revisions': [{'path': 'later', 'sha256': 'b' * 64}]},
    {'later_revisions': 'not-a-reference-list', 'chain_sha256': 'pin'},
])
def test_caller_refuses_an_incomplete_chain_configuration(caller, options):
    from test_corrected_score_2162 import test_caller_uses_official_tier_once_and_keeps_false_partial_findings
    test_caller_uses_official_tier_once_and_keeps_false_partial_findings(caller)
    caller['fresh_output']()
    with pytest.raises(ValueError):
        caller['run'](**options)
    assert not caller['path'].exists() and not caller['active']


@pytest.mark.parametrize('before,after,swapped', [
    ('copy.deepcopy([revision_ref] + later_revisions)',
     'copy.deepcopy(later_revisions)', False),
    ('copy.deepcopy([revision_ref] + later_revisions)',
     'copy.deepcopy(later_revisions + [revision_ref])', False),
    ('assert set(loads) == expected_loads and len(loads) == len(expected_loads)',
     'assert len(loads) == len(expected_loads)', True),
])
def test_actual_caller_mutants_cannot_drop_order_or_identity(later, monkeypatch,
                                                          before, after, swapped):
    test_final_caller_applies_old_then_new_and_records_every_completion(later)
    caller = later['caller']
    caller['fresh_output']()
    source = Path(SUBJECT.__file__).read_text()
    assert source.count(before) == 1
    namespace = dict(vars(SUBJECT))
    exec(compile(source.replace(before, after, 1), SUBJECT.__file__, 'exec'), namespace)
    # Keep the same explicit caller-boundary spy after imports in the mutant.
    namespace['CHAIN'] = SUBJECT.CHAIN
    namespace['validate_revision'] = SUBJECT.validate_revision
    monkeypatch.setattr(SUBJECT, 'run', namespace['run'])
    if swapped:
        handle = list(caller['load_sources'][-1])
        handle[1] = 'wrong-root-with-the-same-count'
        caller['load_sources'][-1] = tuple(handle)
        # The weakened equality guard demonstrably saves the wrong report;
        # the actual negative-test assertion must catch that acceptance.
        with pytest.raises(pytest.fail.Exception):
            with pytest.raises((ValueError, AssertionError)):
                later['run']()
    else:
        with pytest.raises((ValueError, AssertionError)):
            later['run']()
