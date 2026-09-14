# -*- coding: utf-8 -*-
"""The question-scoped correction, end to end, on the REAL lifecycle.

The real original FULL population is consumed first, every time. Then the new
seam prepares a correction candidate whose whole population is an approved
subset carrying its input version, that candidate is driven through the SAME
`freeze_root -> publish_run -> preflight -> save_results -> finalize_segment`
facilities and completed by the real `a7_g1_complete_v2`, and the frozen
revision boundary combines it through the REAL `official_verdict_maps`.

No double stands in for the consumer, the evidence loader, the completion, the
matcher, the route or the scorer. The ONE substitution is the lifecycle test's
own `_candidate` helper - which only chooses WHICH candidate directory
`_drive` opens - so the lifecycle is reused instead of copied. Every reply is
an explicit TEST fixture with its own expected value, never a claim about a
real answer.
"""
import collections
import contextlib
import copy
import io
import json
import os
import sys

import pytest

SERVED = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SERVED)

import a7_g1_build as G                      # noqa: E402
import a7_g23_build as B                     # noqa: E402
import a7_g23_run as R                       # noqa: E402
import a7_grading_revision_2115 as REV       # noqa: E402
import a7_grading_input_correction_2114 as V  # noqa: E402
import a7_correction_candidate_2118 as PREP  # noqa: E402
import test_a7_g23_lifecycle_1464 as LC      # noqa: E402
from test_a7_g23_lifecycle_1464 import _current_candidate  # noqa: F401,E402
from test_a7_input_binding import run, inputs, g1          # noqa: F401,E402

KIND = 'G2'
FLIPPED = 'driver_state'


@contextlib.contextmanager
def _driving(out, sha, doc):
    original = LC._candidate
    LC._candidate = lambda _tmp, _kind: (out, sha, doc)
    try:
        yield
    finally:
        LC._candidate = original


def _reply(flip=None, omit=(), null=None, kind=KIND, bucket=None):
    """An explicit TEST reply. `flip` turns one field false, `null` leaves ONE
    aspect unanswered while still supplying the others, `omit` drops whole
    questions, and `bucket` names the G3 answer."""
    def build(_lane_id, question_ids):
        rows = []
        for qid in question_ids:
            if qid in omit:
                continue
            if kind == 'G3':
                rows.append({'question_id': qid,
                             'bucket': bucket or B.extras_buckets()[0]})
                continue
            verdicts = {f: True for f in B.meaning_fields()}
            if flip:
                verdicts[flip] = False
            if null:
                verdicts[null] = None
            rows.append({'question_id': qid, 'verdicts': verdicts})
        return json.dumps(rows)
    return build


@pytest.fixture
def base(tmp_path, monkeypatch, inputs):
    """The REAL original full-population run, consumed before any correction."""
    got = LC._drive(tmp_path / 'full', KIND, monkeypatch=monkeypatch)
    assert got['problems'] == [], got['problems'][:2]
    sha, result = LC._completed(got)
    assert result['credited'], 'the original lifecycle credited nothing'
    required = LC._required_populations()
    leg = sorted(required[KIND])[0].split('|', 1)[0]
    source = LC._source(got, KIND, sha)
    maps = B.official_verdict_maps(leg, source, LC.RUN, required,
                                   LC._approved_g1())
    assert maps[0], 'the real consumer derived no base meaning map'
    assert all(v[FLIPPED] is True for v in maps[0].values())
    _legs, _t, _m, arms, gold, problems = G.inventory(LC.RUN)
    assert not problems, problems[:2]
    return {'got': got, 'source': source, 'required': required, 'leg': leg,
            'maps': maps, 'tmp': tmp_path, 'monkeypatch': monkeypatch,
            'inputs': inputs, 'arms': arms, 'gold': gold}


def _matched(base):
    """THE matched-pair inventory: the full G2 population, unchanged.

    `a7_g23_run.populations` builds g2 from `B.matched_pairs`, so the G2
    population IS the final matched-pair inventory. Nothing is recomputed here.
    """
    return copy.deepcopy(LC._required_populations()['G2'])

def _subset_of(base):
    """ONE group of the real full population, declared independently."""
    full = base['required'][KIND]
    assert len(full) > 1, 'the TEST population is too small to subset'
    key = sorted(full)[0]
    return key, {key: copy.deepcopy(full[key])}


def _correct(base, subset, reply, name, kind=KIND):
    """Prepare, drive and complete ONE correction run. -> (source, pin, doc)."""
    out = str(base['tmp'] / (name + '_cand'))
    os.makedirs(out)
    path, sha, doc, pin = PREP.prepare(
        out, kind, LC._required_populations()[kind], subset, base['gold'],
        base['arms'], LC.RUN, base['inputs'], LC._approved_g1(),
        G.live_key()[1], matched_pairs=_matched(base) if kind == 'G3' else None)
    written = G._read(path)
    with _driving(out, sha, written):
        got = LC._drive(base['tmp'] / name, kind, reply_for=reply,
                        monkeypatch=base['monkeypatch'])
    assert got['problems'] == [], got['problems'][:2]
    completion, _result = LC._completed(got)
    return LC._source(got, kind, completion), pin, written


def _plan(base, handle, subset, pin, path, base_sources=None, kind=KIND,
          **override):
    plan = {'schema': 'a7-grading-revision/v1',
            'code_sha256': G._sha_file(REV.__file__),
            'producer_identity': LC.RUN,
            'g1_identity': B.g1_identity(LC._approved_g1()),
            'required_population': base['required'],
            'base_sources': base_sources or base['source'],
            'corrections': {kind: {
                'source': handle[kind], 'population': subset,
                'input_correction_sha256': pin,
                'reason': 'native correction-candidate proof, TEST evidence'}}}
    plan['corrections'][kind].update(override)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(plan, fh)
    return path, G._sha_file(path)


def _revised(base, plan_path, plan_sha):
    with REV.scope(plan_path, plan_sha):
        return B.official_verdict_maps(base['leg'], base['source'], LC.RUN,
                                       base['required'], LC._approved_g1())


# ------------------------------------------------------------- the seam ------
def test_the_prepared_candidate_is_the_subset_and_names_its_input_version(base):
    key, subset = _subset_of(base)
    out = str(base['tmp'] / 'seam_cand')
    os.makedirs(out)
    path, sha, doc, pin = PREP.prepare(
        out, KIND, base['required'][KIND], subset, base['gold'], base['arms'],
        LC.RUN, base['inputs'], LC._approved_g1(), G.live_key()[1])
    written = G._read(path)
    assert G._sha_file(path) == sha
    assert written['task_kind'] == KIND
    assert G._plain(written['population']) == G._plain(subset)
    assert G._plain(written['population']) != G._plain(base['required'][KIND])
    assert written['input_correction_sha256'] == pin == G._sha_file(V.__file__)
    assert written['population_counts']['questions'] == len(subset[key])
    asked = [q for row in written['batch_rows'] for q in row['question_ids']]
    assert asked and len(asked) == len(set(asked))
    assert written['questions'] == len(asked)
    assert R.kind_candidate.__name__ == 'kind_candidate', 'writer not restored'
    # the OLD candidate is untouched by any of this
    assert 'input_correction_sha256' not in base['got']['doc']


@pytest.mark.parametrize('bad', ['empty', 'unknown_group', 'extra_question',
                                 'repeated_question'])
def test_an_unapproved_subset_refuses_with_a_valid_control(base, bad):
    key, subset = _subset_of(base)
    PREP.approved_subset(base['required'][KIND], subset)      # the control
    full = base['required'][KIND]
    other = sorted(full)[1]
    broken = {'empty': {},
              'unknown_group': {'P9|no-such-source': copy.deepcopy(full[key])},
              'extra_question': {key: list(full[key]) + [[99, 99]]},
              'repeated_question': {key: list(full[key]) + list(full[key])}}[bad]
    with pytest.raises(ValueError):
        PREP.approved_subset(full, broken)
    assert other in full


# --------------------------------------------------- the revision consumer ---
def test_a_corrected_judgment_replaces_only_its_own_questions(base):
    key, subset = _subset_of(base)
    source, pin, _doc = _correct(base, subset, _reply(flip=FLIPPED), 'flip')
    path, sha = _plan(base, source, subset, pin,
                      str(base['tmp'] / 'plan_flip.json'))
    meaning, extras = _revised(base, path, sha)

    sid = key.split('|', 1)[1]
    corrected = {k for k in meaning if k[0] == sid}
    assert corrected, 'nothing was corrected'
    for k in corrected:
        assert meaning[k][FLIPPED] is False, k
    for k, verdict in base['maps'][0].items():
        if k not in corrected:
            assert meaning[k] == verdict, k
    assert extras == base['maps'][1], 'the other kind changed'
    assert set(meaning) == set(base['maps'][0])
    assert B.official_verdict_maps(base['leg'], base['source'], LC.RUN,
                                   base['required'],
                                   LC._approved_g1()) == base['maps']


def test_an_unresolved_replacement_cannot_inherit_the_superseded_credit(base):
    key, subset = _subset_of(base)
    sid = key.split('|', 1)[1]
    superseded = {k for k in base['maps'][0] if k[0] == sid}
    assert superseded, 'the subset credits nothing to supersede'

    # the correction run answers NOTHING for its own questions, so the
    # replacement is unresolved and the old credit has nothing to inherit from
    out = str(base['tmp'] / 'unres_cand')
    os.makedirs(out)
    path2, sha2, doc2, pin2 = PREP.prepare(
        out, KIND, base['required'][KIND], subset, base['gold'], base['arms'],
        LC.RUN, base['inputs'], LC._approved_g1(), G.live_key()[1])
    written = G._read(path2)
    every = [q for row in written['batch_rows'] for q in row['question_ids']]
    with _driving(out, sha2, written):
        got = LC._drive(base['tmp'] / 'unres', KIND,
                        reply_for=_reply(omit=set(every)),
                        monkeypatch=base['monkeypatch'])
    completion, _r = LC._completed(got)
    source2 = LC._source(got, KIND, completion)
    plan_path, plan_sha = _plan(base, source2, subset, pin2,
                                str(base['tmp'] / 'plan_unres.json'))
    meaning, _extras = _revised(base, plan_path, plan_sha)
    for k in superseded:
        assert k not in meaning, 'superseded credit was inherited: %r' % (k,)
    for k, verdict in base['maps'][0].items():
        if k not in superseded:
            assert meaning[k] == verdict, k


@pytest.mark.parametrize('tamper', ['population', 'version', 'completion'])
def test_a_tampered_correction_refuses_with_a_valid_control(base, tamper):
    key, subset = _subset_of(base)
    source, pin, _doc = _correct(base, subset, _reply(flip=FLIPPED), 'tamper')
    good_path, good_sha = _plan(base, source, subset, pin,
                                str(base['tmp'] / 'plan_good.json'))
    assert _revised(base, good_path, good_sha)[0], 'the control failed'

    full = base['required'][KIND]
    override = {
        'population': {'population': {sorted(full)[1]: copy.deepcopy(
            full[sorted(full)[1]])}},
        'version': {'input_correction_sha256': G._sha('not-the-renderer')},
        'completion': {'source': dict(source[KIND],
                                      completion_sha256=G._sha('not-it'))},
    }[tamper]
    bad_path, bad_sha = _plan(base, source, subset, pin,
                              str(base['tmp'] / ('plan_%s.json' % tamper)),
                              **override)
    with pytest.raises(ValueError):
        _revised(base, bad_path, bad_sha)
    assert B._verdict_maps_from.__name__ == '_verdict_maps_from', 'not restored'


# ------------------------------------------------- the actual scorer, real ---
@pytest.fixture
def both(base):
    """The G3 half of the same real original run, so the official scorer has
    the whole handle set it requires."""
    got = LC._drive(base['tmp'] / 'full_g3', 'G3',
                    monkeypatch=base['monkeypatch'])
    assert got['problems'] == [], got['problems'][:2]
    sha, result = LC._completed(got)
    assert result['credited'], 'the G3 lifecycle credited nothing'
    sources = dict(base['source'])
    sources.update(LC._source(got, 'G3', sha))
    return {'sources': sources, 'g3': got}


def _score(base, both, name):
    return B.score_leg_official(base['leg'], LC.RUN, both['sources'],
                                str(base['tmp'] / name), LC._approved_g1())


def test_a_corrected_judgment_changes_only_its_own_scorer_result(base, both):
    """The REAL official scorer, before and after, with nothing replaced."""
    before = _score(base, both, 'score_before')
    key, subset = _subset_of(base)
    source, pin, _doc = _correct(base, subset, _reply(flip=FLIPPED), 'score')
    path, sha = _plan(base, source, subset, pin,
                      str(base['tmp'] / 'plan_score.json'),
                      base_sources=both['sources'])
    with REV.scope(path, sha):
        after = _score(base, both, 'score_after')

    changed = [k for k in sorted(set(before) | set(after))
               if G._plain(before.get(k)) != G._plain(after.get(k))]
    assert changed, 'the corrected judgment changed no scorer result at all'
    # THE EXACT RESULT of flipping driver_state, named before the run: the
    # state accuracy moves and the matching, extras and park facts cannot.
    assert 'state_acc' in changed, changed
    for k in ('extras', 'gold_n', 'matched', 'would_park'):
        assert k in before and k in after, k
        assert G._plain(before[k]) == G._plain(after[k]), k
    # and the untouched scorer is restored
    assert G._plain(_score(base, both, 'score_restored')) == G._plain(before)


def test_the_seam_handles_G3_and_the_other_leg_keeps_its_base_evidence(base, both):
    """G3 through the same seam, and a leg the correction never named."""
    full3 = LC._required_populations()['G3']
    key3 = sorted(full3)[0]
    subset3 = {key3: copy.deepcopy(full3[key3])}
    out = str(base['tmp'] / 'g3_cand')
    os.makedirs(out)
    path, sha, doc, pin = PREP.prepare(
        out, 'G3', full3, subset3, base['gold'], base['arms'], LC.RUN,
        base['inputs'], LC._approved_g1(), G.live_key()[1],
        matched_pairs=_matched(base))
    written = G._read(path)
    assert written['task_kind'] == 'G3'
    assert G._plain(written['population']) == G._plain(subset3)
    assert written['input_correction_sha256'] == pin

    other = [k.split('|', 1)[0] for k in sorted(full3)
             if k.split('|', 1)[0] != key3.split('|', 1)[0]]
    assert other, 'the TEST population has only one leg'
    base_other = B.official_verdict_maps(other[0], both['sources'], LC.RUN,
                                         LC._required_populations(),
                                         LC._approved_g1())
    key, subset = _subset_of(base)
    source, pin2, _d = _correct(base, subset, _reply(flip=FLIPPED), 'otherleg')
    plan_path, plan_sha = _plan(base, source, subset, pin2,
                                str(base['tmp'] / 'plan_other.json'),
                                base_sources=both['sources'])
    with REV.scope(plan_path, plan_sha):
        after_other = B.official_verdict_maps(other[0], both['sources'], LC.RUN,
                                              LC._required_populations(),
                                              LC._approved_g1())
    assert G._plain(after_other) == G._plain(base_other), (
        'a leg the correction never named changed')


def test_a_tampered_root_refuses_with_a_valid_control(base):
    key, subset = _subset_of(base)
    source, pin, _doc = _correct(base, subset, _reply(flip=FLIPPED), 'root')
    good, good_sha = _plan(base, source, subset, pin,
                           str(base['tmp'] / 'plan_root_ok.json'))
    assert _revised(base, good, good_sha)[0], 'the control failed'
    bad, bad_sha = _plan(base, source, subset, pin,
                         str(base['tmp'] / 'plan_root_bad.json'),
                         source=dict(source[KIND],
                                     root_sha256=G._sha('not-the-root')))
    with pytest.raises(ValueError):
        _revised(base, bad, bad_sha)


# ------------------------------------------- the gaps Codex SEQ 2118 named ---
def test_a_corrected_G3_bucket_changes_only_its_own_result(base, both):
    """G3 all the way through: prepare, drive, complete, revise, score."""
    full3 = LC._required_populations()['G3']
    key3 = sorted(full3)[0]
    subset3 = {key3: copy.deepcopy(full3[key3])}
    buckets = B.extras_buckets()
    chosen = buckets[1]
    assert chosen != buckets[0], 'the fixture reply must change the bucket'

    before_maps = B.official_verdict_maps(base['leg'], both['sources'], LC.RUN,
                                          LC._required_populations(),
                                          LC._approved_g1())
    assert before_maps[1], 'no base extras map to correct'
    assert set(before_maps[1].values()) == {buckets[0]}

    before_score = _score(base, both, 'g3_score_before')
    source, pin, _doc = _correct(base, subset3, _reply(kind='G3', bucket=chosen),
                                 'g3full', kind='G3')
    path, sha = _plan(base, source, subset3, pin,
                      str(base['tmp'] / 'plan_g3.json'),
                      base_sources=both['sources'], kind='G3')
    with REV.scope(path, sha):
        meaning, extras = B.official_verdict_maps(
            base['leg'], both['sources'], LC.RUN,
            LC._required_populations(), LC._approved_g1())
        after_score = _score(base, both, 'g3_score_after')

    sid = key3.split('|', 1)[1]
    corrected = {k for k in extras if k[0] == sid}
    assert corrected, 'nothing was corrected on the G3 side'
    for k in corrected:
        assert extras[k] == chosen, (k, extras[k])
    for k, bucket in before_maps[1].items():
        if k not in corrected:
            assert extras[k] == bucket, k
    assert meaning == before_maps[0], 'the meaning side changed'
    changed = [k for k in sorted(set(before_score) | set(after_score))
               if G._plain(before_score.get(k)) != G._plain(after_score.get(k))]
    assert 'extras' in changed, changed
    assert G._plain(before_score['gold_n']) == G._plain(after_score['gold_n'])


def test_a_partially_unresolved_reply_cannot_regain_the_superseded_aspects(base):
    """One aspect null, the others still supplied - a LAWFUL partial answer."""
    key, subset = _subset_of(base)
    source, pin, _doc = _correct(
        base, subset, _reply(flip=FLIPPED, null='favorability'), 'partial')
    path, sha = _plan(base, source, subset, pin,
                      str(base['tmp'] / 'plan_partial.json'))
    meaning, _extras = _revised(base, path, sha)

    sid = key.split('|', 1)[1]
    corrected = {k for k in meaning if k[0] == sid}
    assert corrected, 'nothing was corrected'
    for k in corrected:
        # the aspect the correction answered stands
        assert meaning[k][FLIPPED] is False, k
        # the aspect it left unresolved did NOT come back from the old answer
        assert base['maps'][0][k]['favorability'] is True
        assert meaning[k].get('favorability') is not True, (
            'a superseded aspect regained its old credit')
    for k, verdict in base['maps'][0].items():
        if k not in corrected:
            assert meaning[k] == verdict, k


def test_question_scoped_preservation_in_the_actual_population(base):
    """What the ACTUAL fixture population supports, measured not assumed."""
    full = base['required'][KIND]
    sources = collections.Counter(k.split('|', 1)[1] for k in full)
    per_group = collections.Counter(len(v) for v in full.values())
    shape = {'groups': len(full), 'sources': len(sources),
             'questions_per_group': dict(per_group)}

    # ONE source is shared by several groups here, so the within-source case
    # available is a group of that source left uncorrected.
    key, subset = _subset_of(base)
    sid = key.split('|', 1)[1]
    siblings = [k for k in full if k.split('|', 1)[1] == sid and k != key]
    assert siblings, ('the population offers no second group on the same '
                      'source: %r' % (shape,))
    source, pin, _doc = _correct(base, subset, _reply(flip=FLIPPED), 'within')
    path, sha = _plan(base, source, subset, pin,
                      str(base['tmp'] / 'plan_within.json'))
    meaning, _extras = _revised(base, path, sha)
    corrected = {k for k in meaning if meaning[k][FLIPPED] is False}
    assert corrected, 'nothing was corrected'
    # every base key the correction did not name keeps its own verdict, and
    # the uncorrected groups of the SAME source are among them
    for k, verdict in base['maps'][0].items():
        if k not in corrected:
            assert meaning[k] == verdict, k

    # MULTIPLE FITTED BATCHES: only where the population needs them.
    biggest = max(len(v) for v in full.values())
    rows = G._read(str(base['tmp'] / 'within_cand' /
                       G.CANDIDATE_NAME))['batch_rows']
    assert rows, 'the subset fitted no call'
    if biggest > B.MAX_ITEMS_PER_CALL:
        assert len(rows) > 1, (biggest, len(rows))
    else:
        assert len(rows) == 1, (biggest, len(rows), B.MAX_ITEMS_PER_CALL)
    print('POPULATION_SHAPE ' + json.dumps(
        dict(shape, max_items_per_call=B.MAX_ITEMS_PER_CALL,
             fitted_batches=len(rows))))


# ----------- the shape Codex SEQ 2119 named: many questions in ONE group -----
def _bigger_group(base, kind=KIND):
    """An independently specified LARGER TEST population, from evidence that
    already exists: this event carries two accepted gold rows and two produced
    facts per leg, so every (gold, produced) pair of that one group is a
    renderable question. Nothing is invented and no real evidence is altered.
    """
    full = base['required'][kind]
    group = sorted(full)[0]
    leg, sid = group.split('|', 1)
    golds = G.accepted_positions(base['gold'][sid])
    produced = list(range(len(base['arms'][leg][sid]['facts'])))
    # ONE PAIRING PER GOLD ROW. The owner refuses a population that pairs a
    # gold row twice - the verdict would be ambiguous - so the larger TEST
    # population is the bijection this event's own evidence already supports.
    pairs = [[g, p] for g, p in zip(golds, produced)]
    assert len(pairs) > 1, ('this fixture cannot show the shape: %d pair(s)'
                            % len(pairs))
    return group, {group: pairs}


def _original_candidate(base, out, population, kind=KIND):
    """The ORIGINAL writer over that population - no correction stamp.

    The same owners the runner uses: B.pack_batches, R._g2_packet_for and
    R._rows_and_prompts for the real fitting, then R.write_kind.
    """
    rows, prompts, _of = R._rows_and_prompts(
        kind, B.pack_batches(population),
        lambda _bid, batch: R._g2_packet_for(base['gold'], base['arms'], batch,
                                             LC.RUN, base['inputs']))
    counts = {'questions': sum(len(v) for v in population.values()),
              'batches': len(rows),
              'largest_batch': max(r['items'] for r in rows)}
    doc = {'producer_identity': LC.RUN,
           'g1_identity': B.g1_identity(LC._approved_g1()),
           'g2_pairs': population, 'g3_idxs': {},
           'g2': counts, 'g3': None,
           'batching': {'rows': rows}}
    os.makedirs(out)
    path, sha = R.write_kind(out, kind, doc, prompts, G.live_key()[1])
    return path, sha, G._read(path), rows


def _finish_remaining_segments(base, got, doc, reply=None, kind=KIND):
    """Every batch AFTER the first, through the same five owner entries.

    `_drive` publishes one lane slice, which is exactly one batch, so a
    multi-batch candidate needs one more segment per remaining batch. This
    calls `publish_run`, `preflight`, `save_results`, `_record_state` and
    `finalize_segment` once per segment - the very calls `_drive` makes and
    the very ones the resume test makes - and merges each segment's rulings
    into the run's own. It is not a second lifecycle and it invents nothing.
    """
    out, run, root_sha = got['out'], got['run'], got['root_sha']
    rows = G.load_root(run, root_sha)['rows']
    width = len(G.GRADER_LANES)
    for start in range(width, len(rows), width):
        lanes = [r['lane_id'] for r in rows[start:start + width]]
        identity, problems = G.publish_run(out, run, root_sha, lanes)
        assert problems == [], problems[:3]
        n, receipt_sha = identity['segment'], identity['receipt_sha256']
        packet, problems = G.preflight(out, run, n, root_sha, receipt_sha)
        assert problems == [], problems[:3]
        receipt = G.load_receipt(run, n)
        results = []
        for arg in packet['args']:
            qids = G.binding_and_parser(kind)[0](doc, arg['batch_id'])['question_ids']
            text = (reply(arg['lane_id'], qids) if reply
                    else LC._lawful_reply(kind, qids))
            row = collections.OrderedDict((f, arg.get(f)) for f in G.RESULT_BINDING)
            row['invocation_sha256'] = receipt['invocation_sha256']
            row['text'], row['error'] = text, None
            results.append(row)
        _accounting, problems = G.save_results(run, n, results, root_sha,
                                               receipt_sha)
        assert problems == [], problems[:3]
        LC._record_state(base['tmp'], base['monkeypatch'], run, n, root_sha,
                         receipt_sha)
        _final, rulings, problems = G.finalize_segment(out, run, n, root_sha,
                                                       receipt_sha)
        assert problems == [], problems[:3]
        got['rulings'].update(rulings)
    return got

@pytest.mark.parametrize('corrected', ['some', 'all'])
def test_many_questions_in_one_group_across_several_fitted_batches(base, corrected):
    """A leg/source group holding several questions, each in its own fitted
    batch. `some` proves the unselected question keeps its verdict; `all`
    proves a correction that itself spans every fitted batch."""
    group, bigger = _bigger_group(base)
    leg = group.split('|', 1)[0]
    required = {KIND: bigger}

    # THE ORIGINAL run over the larger population, consumed first
    path, sha, doc, rows = _original_candidate(
        base, str(base['tmp'] / 'big_cand'), bigger)
    assert len(rows) > 1, 'the larger population fitted only one call'
    with _driving(str(base['tmp'] / 'big_cand'), sha, doc):
        got = LC._drive(base['tmp'] / 'big', KIND, monkeypatch=base['monkeypatch'])
    assert got['problems'] == [], got['problems'][:2]
    _finish_remaining_segments(base, got, doc)
    completion, result = LC._completed(got)
    asked = [q for row in doc['batch_rows'] for q in row['question_ids']]
    assert len(result['credited']) == len(asked), (
        'not every fitted batch was finalized and consumed',
        len(result['credited']), len(asked))
    source = LC._source(got, KIND, completion)
    before, _e = B.official_verdict_maps(leg, source, LC.RUN, required,
                                         LC._approved_g1())
    assert len(before) == len(bigger[group]), (len(before), len(bigger[group]))
    assert all(v[FLIPPED] is True for v in before.values())

    # CORRECT ONLY SOME OF THEM, spanning more than one fitted batch
    chosen = bigger[group][:1] if corrected == 'some' else list(bigger[group])
    kept = [p for p in bigger[group] if p not in chosen]
    assert chosen, 'nothing was selected'
    assert bool(kept) == (corrected == 'some'), (corrected, kept)
    subset = {group: copy.deepcopy(chosen)}
    out = str(base['tmp'] / 'big_corr_cand')
    os.makedirs(out)
    cpath, csha, cdoc, pin = PREP.prepare(
        out, KIND, bigger, subset, base['gold'], base['arms'], LC.RUN,
        base['inputs'], LC._approved_g1(), G.live_key()[1])
    cwritten = G._read(cpath)
    assert len(cwritten['batch_rows']) == len(chosen), (
        'one fitted batch per selected question', len(cwritten['batch_rows']))
    if corrected == 'all':
        assert len(cwritten['batch_rows']) > 1, (
            'the correction must span several fitted batches here')
    flip = _reply(flip=FLIPPED)
    with _driving(out, csha, cwritten):
        cgot = LC._drive(base['tmp'] / 'big_corr', KIND, reply_for=flip,
                         monkeypatch=base['monkeypatch'])
    assert cgot['problems'] == [], cgot['problems'][:2]
    _finish_remaining_segments(base, cgot, cwritten, reply=flip)
    ccompletion, cresult = LC._completed(cgot)
    casked = [q for row in cwritten['batch_rows'] for q in row['question_ids']]
    assert len(cresult['credited']) == len(casked), (
        'a correction batch was not finalized', len(cresult['credited']),
        len(casked))
    csource = LC._source(cgot, KIND, ccompletion)

    plan = {'schema': 'a7-grading-revision/v1',
            'code_sha256': G._sha_file(REV.__file__),
            'producer_identity': LC.RUN,
            'g1_identity': B.g1_identity(LC._approved_g1()),
            'required_population': required, 'base_sources': source,
            'corrections': {KIND: {
                'source': csource[KIND], 'population': subset,
                'input_correction_sha256': pin,
                'reason': 'many questions in one group, only some corrected'}}}
    plan_path = str(base['tmp'] / 'plan_big.json')
    with open(plan_path, 'w', encoding='utf-8') as fh:
        json.dump(plan, fh)
    with REV.scope(plan_path, G._sha_file(plan_path)):
        after, _ex = B.official_verdict_maps(leg, source, LC.RUN, required,
                                             LC._approved_g1())

    changed = {k for k, v in after.items() if v[FLIPPED] is False}
    assert len(changed) == len(chosen), (len(changed), len(chosen))
    for k, verdict in before.items():
        if k not in changed:
            assert after[k] == verdict, (
                'an unselected question of the SAME group changed', k)
    assert len(after) == len(before)
    print('BIG_SHAPE ' + json.dumps({
        'case': corrected, 'group': group, 'questions': len(bigger[group]),
        'base_batches': len(rows), 'base_credited': len(result['credited']),
        'corrected': len(chosen), 'kept': len(kept),
        'correction_batches': len(cwritten['batch_rows']),
        'correction_credited': len(cresult['credited'])}))


# ------------- the G3 duplicate prerequisite: matched comparators only -------
def _g3_question(base):
    """One real G3 question and the matched pool its event actually has."""
    full3 = LC._required_populations()['G3']
    group = sorted(full3)[0]
    asked = full3[group][:1]
    matched = _matched(base)
    pool = sorted({p for _g, p in matched.get(group, [])} - set(asked))
    return group, {group: copy.deepcopy(asked)}, matched, pool


def test_g3_comparison_records_are_only_this_events_matched_records(base):
    """The pool is the matched produced rows, and nothing else this event holds."""
    group, subset, matched, pool = _g3_question(base)
    leg, sid = group.split('|', 1)
    every = len(base['arms'][leg][sid]['facts'])
    assert every > len(pool), (
        'this event offers no unmatched record, so nothing would be excluded')

    out = str(base['tmp'] / 'g3_pool_cand')
    os.makedirs(out)
    path, sha, doc, pin = PREP.prepare(
        out, 'G3', LC._required_populations()['G3'], subset, base['gold'],
        base['arms'], LC.RUN, base['inputs'], LC._approved_g1(),
        G.live_key()[1], matched_pairs=matched)
    written = G._read(path)
    assert G._plain(written['matched_population']) == G._plain(matched)

    body = json.loads((io.open(os.path.join(out, written['batch_rows'][0]['prompt_path']),
                               encoding='utf-8').read()).split('[EVENT]\n', 1)[1])
    others = body['events'][0]['other_records']
    assert len(others) == len(pool), (len(others), pool, every)
    assert [row['other'] for row in others] == ['O%d' % (n + 1)
                                                for n in range(len(others))]
    # every reviewed card and the whole source are still there
    assert body['events'][0]['reference_cards']
    assert body['events'][0]['event_context']['text_parts']
    assert len(body['events'][0]['questions']) == len(subset[group])


@pytest.mark.parametrize('shape', ['sparse', 'explicit_empty'])
def test_a_group_with_no_matched_pair_gets_an_explicitly_empty_pool(base, shape):
    """The reproduced case: no matched fact in the event, so no comparator.

    `sparse` is the shape the REAL frozen inventory has - a7_g23_run.populations
    writes g2[group] only `if rows`, so an unmatched group is ABSENT, not an
    empty list. `explicit_empty` is the same group carried as []. Positive
    control first: with the event's real matched pair the pool is NOT empty.
    """
    group, subset, matched, pool = _g3_question(base)
    assert pool, 'the control needs a real matched comparator'
    leg, sid = group.split('|', 1)

    empty = copy.deepcopy(matched)
    if shape == 'sparse':
        empty.pop(group)                   # exactly as the live inventory is
    else:
        empty[group] = []
    out = str(base['tmp'] / 'g3_empty_cand')
    out = out + '_' + shape
    os.makedirs(out)
    path, _sha, _doc, _pin = PREP.prepare(
        out, 'G3', LC._required_populations()['G3'], subset, base['gold'],
        base['arms'], LC.RUN, base['inputs'], LC._approved_g1(),
        G.live_key()[1], matched_pairs=empty)
    written = G._read(path)
    body = json.loads((io.open(os.path.join(out, written['batch_rows'][0]['prompt_path']),
                               encoding='utf-8').read()).split('[EVENT]\n', 1)[1])
    assert body['events'][0]['other_records'] == [], body['events'][0]['other_records']
    assert body['events'][0]['questions'], 'the question itself must survive'
    assert body['events'][0]['reference_cards'], 'the cards must survive'


@pytest.mark.parametrize('fault', ['absent', 'wrong_event', 'unknown_index',
                                   'repeated_index'])
def test_a_broken_matched_inventory_refuses_with_a_valid_control(base, fault):
    group, subset, matched, _pool = _g3_question(base)
    leg, sid = group.split('|', 1)
    V.eligible_comparators(matched, leg, sid,
                           base['arms'][leg][sid]['facts'])      # the control
    every = len(base['arms'][leg][sid]['facts'])
    broken = copy.deepcopy(matched)
    if fault == 'absent':
        broken = None
    elif fault == 'wrong_event':
        broken.pop(group)
    elif fault == 'unknown_index':
        broken[group] = [[0, every + 5]]
    else:
        broken[group] = [[0, 0], [1, 0]]
    with pytest.raises(ValueError):
        V.eligible_comparators(broken, leg, sid,
                               base['arms'][leg][sid]['facts'])


def test_the_bound_matched_population_is_checked_by_the_consumer(base, both):
    """It reaches the real consumer, and a candidate bound to a DIFFERENT
    inventory refuses - the consumer checks the binding, it does not trust it.
    """
    group, subset, matched, _pool = _g3_question(base)

    # the control: bound to the population this scoring requires
    source, pin, _doc = _correct(base, subset, _reply(kind='G3'), 'g3bind',
                                 kind='G3')
    path, sha = _plan(base, source, subset, pin,
                      str(base['tmp'] / 'plan_g3bind.json'),
                      base_sources=both['sources'], kind='G3')
    with REV.scope(path, sha):
        _meaning, extras = B.official_verdict_maps(
            base['leg'], both['sources'], LC.RUN,
            LC._required_populations(), LC._approved_g1())
    assert extras, 'the G3 correction produced no map'

    # the same shape, bound to a DIFFERENT inventory: lawful on its face, and
    # not the population this scoring already derived
    other = copy.deepcopy(matched)
    other.pop(sorted(k for k in other if k != group)[0])
    out = str(base['tmp'] / 'g3bad_cand')
    os.makedirs(out)
    bpath, bsha, bdoc, bpin = PREP.prepare(
        out, 'G3', LC._required_populations()['G3'], subset, base['gold'],
        base['arms'], LC.RUN, base['inputs'], LC._approved_g1(),
        G.live_key()[1], matched_pairs=other)
    bwritten = G._read(bpath)
    assert G._plain(bwritten['matched_population']) != G._plain(matched)
    with _driving(out, bsha, bwritten):
        bgot = LC._drive(base['tmp'] / 'g3bad', 'G3',
                         reply_for=_reply(kind='G3'),
                         monkeypatch=base['monkeypatch'])
    assert bgot['problems'] == [], bgot['problems'][:2]
    bcompletion, _r = LC._completed(bgot)
    bsource = LC._source(bgot, 'G3', bcompletion)
    bplan, bplan_sha = _plan(base, bsource, subset, bpin,
                             str(base['tmp'] / 'plan_g3bad.json'),
                             base_sources=both['sources'], kind='G3')
    with REV.scope(bplan, bplan_sha):
        with pytest.raises(ValueError) as exc:
            B.official_verdict_maps(base['leg'], both['sources'], LC.RUN,
                                    LC._required_populations(),
                                    LC._approved_g1())
    assert 'matched comparison population' in str(exc.value), str(exc.value)
