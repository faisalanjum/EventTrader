"""Two real saved TEST correction runs through one unchanged scorer."""
import copy

import a7_grading_revision_chain_2169 as CHAIN
from test_grading_contract_native_2169 import *
from test_grading_contract_native_2169 import _current_candidate


def ref(pair):
    return {'path': pair[0], 'sha256': pair[1]}


def test_two_real_correction_rounds_change_only_their_own_scores(base, both):
    before = NATIVE._score(base, both, 'two_before')
    _group, subset = NATIVE._subset_of(base)
    source, pin, _doc = NATIVE._correct(
        base, subset, NATIVE._reply(flip=NATIVE.FLIPPED), 'first_round')
    first = NATIVE._plan(base, source, subset, pin,
                          str(base['tmp'] / 'first_round.json'),
                          base_sources=both['sources'])
    full = NATIVE.LC._required_populations()['G3']
    group = sorted(full)[0]
    subset3 = {group: copy.deepcopy(full[group])}
    chosen = NATIVE.B.extras_buckets()[1]
    source3, pin3, _doc = NATIVE._correct(
        base, subset3, NATIVE._reply(kind='G3', bucket=chosen), 'second_round', kind='G3')
    second = NATIVE._plan(base, source3, subset3, pin3,
                           str(base['tmp'] / 'second_round.json'),
                           base_sources=both['sources'], kind='G3')
    with CHAIN.scope([ref(first), ref(second)], NATIVE.G._sha_file(CHAIN.__file__)):
        after = NATIVE._score(base, both, 'two_after')
    assert before['state_acc'] != after['state_acc']
    assert NATIVE.G._plain(before['extras']) != NATIVE.G._plain(after['extras'])
    for field in ('gold_n', 'matched', 'would_park'):
        assert NATIVE.G._plain(before[field]) == NATIVE.G._plain(after[field])
    assert NATIVE.G._plain(NATIVE._score(base, both, 'two_restored')) == NATIVE.G._plain(before)


def test_later_real_partial_correction_cannot_recover_an_old_aspect(base):
    group, subset = NATIVE._subset_of(base)
    source, pin, _doc = NATIVE._correct(
        base, subset, NATIVE._reply(flip=NATIVE.FLIPPED), 'earlier')
    first = NATIVE._plan(base, source, subset, pin, str(base['tmp'] / 'earlier.json'))
    source2, pin2, _doc = NATIVE._correct(
        base, subset, NATIVE._reply(null=NATIVE.FLIPPED), 'later')
    second = NATIVE._plan(base, source2, subset, pin2, str(base['tmp'] / 'later.json'))
    sid = group.split('|', 1)[1]
    with CHAIN.scope([ref(first), ref(second)], NATIVE.G._sha_file(CHAIN.__file__)):
        meaning, extras = NATIVE.B.official_verdict_maps(
            base['leg'], base['source'], NATIVE.LC.RUN,
            base['required'], NATIVE.LC._approved_g1())
    for key, value in base['maps'][0].items():
        if key[0] == sid:
            assert meaning[key].get(NATIVE.FLIPPED) is None
        else:
            assert meaning[key] == value
    assert extras == base['maps'][1]
