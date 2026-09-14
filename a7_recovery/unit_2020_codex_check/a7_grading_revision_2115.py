"""Question-scoped revisions after the original whole-run evidence checks.

No calls, invented verdicts, scoring rules or edits to old evidence. The
existing consumer validates every original and correction completion. This
boundary checks the approved replacement population and combines only those
verified maps. An unresolved new answer removes old credit, never inherits it.
"""
import copy
from contextlib import contextmanager

import a7_g1_build as G
import a7_g23_build as B


def _same(actual, expected, label):
    if G._plain(actual) != G._plain(expected):
        raise ValueError('grading revision changed ' + label)


def _targets(kind, population, required, leg):
    """A nonempty exact subset of the consumer's own full population."""
    if not isinstance(population, dict) or not population:
        raise ValueError('grading revision has no affected population')
    targets = set()
    for group, rows in population.items():
        if group not in required or not isinstance(rows, list) or not rows:
            raise ValueError('grading revision has an unknown or empty group')
        frozen = {G._plain(row) for row in required[group]}
        seen = set()
        for row in rows:
            key = G._plain(row)
            if key not in frozen or key in seen:
                raise ValueError('grading revision has a different or repeated question')
            seen.add(key)
            group_leg, sid = group.split('|', 1)
            if group_leg == leg:
                targets.add((sid, row[0] if kind == 'G2' else row))
    return targets


@contextmanager
def scope(plan_path, expected_sha256):
    """Use one reviewed plan; restore the existing consumer even on refusal.

    The plan pins the full original identity/population and one new completed
    run per affected kind. The candidate's exact subset, new input version,
    root and completion must all agree. There is no caller-supplied verdict.
    """
    def verify():
        if G._sha_file(plan_path) != expected_sha256:
            raise ValueError('unapproved grading revision plan')
        if G._sha_file(__file__) != plan['code_sha256']:
            raise ValueError('unapproved grading revision code')

    if G._sha_file(plan_path) != expected_sha256:
        raise ValueError('unapproved grading revision plan')
    plan = G._read(plan_path)
    fields = {'schema', 'code_sha256', 'producer_identity', 'g1_identity',
              'required_population', 'base_sources', 'corrections'}
    if (not isinstance(plan, dict) or set(plan) != fields
            or plan['schema'] != 'a7-grading-revision/v1'):
        raise ValueError('invalid grading revision plan')
    corrections = plan['corrections']
    if (not isinstance(corrections, dict)
            or set(corrections) - {'G2', 'G3'}):
        raise ValueError('invalid grading revision kinds')
    verify()
    original = B._verdict_maps_from

    def revised(leg, sources, producer, required, g1, memo):
        verify()
        _same(producer, plan['producer_identity'], 'producer identity')
        _same(B.g1_identity(g1), plan['g1_identity'], 'G1 identity')
        _same(required, plan['required_population'], 'full required population')
        _same(sources, plan['base_sources'], 'original source handles')
        # The old full-population door remains mandatory. Its saved runs,
        # native attempts and completions are validated before any replacement.
        result = list(copy.deepcopy(original(leg, sources, producer, required, g1, memo)))
        for kind, correction in sorted(corrections.items()):
            fields = {'source', 'population', 'input_correction_sha256', 'reason'}
            if (not isinstance(correction, dict) or set(correction) != fields
                    or not isinstance(correction['reason'], str)
                    or not correction['reason'].strip()):
                raise ValueError('invalid grading revision descriptor')
            pin = correction['input_correction_sha256']
            if (not isinstance(pin, str) or len(pin) != 64
                    or any(c not in '0123456789abcdef' for c in pin)):
                raise ValueError('invalid grading revision input hash')
            if kind not in sources or kind not in required:
                raise ValueError('grading revision has no original kind')
            src, population = correction['source'], correction['population']
            targets = _targets(kind, population, required[kind], leg)
            # This is the SAME evidence/re-derivation door, applied to the
            # independently approved subset proved against the full population.
            changed = original(leg, {kind: src}, producer, {kind: population}, g1, memo)
            # Reuse its verified candidate, not a second root/completion loader.
            candidate, _ = memo[(kind, src['run_dir'], src['root_sha256'],
                                 src['completion_sha256'])]
            _same(candidate.get('input_correction_sha256'),
                  correction['input_correction_sha256'], 'correction input version')
            if kind == 'G3':
                # THE COMPARISON POOL IS CHECKED, NOT TRUSTED. A G3 duplicate is
                # a duplicate OF A MATCHED FACT, so the candidate must name the
                # matched-pair inventory it drew its comparison records from,
                # and it must be the very G2 population this scoring already
                # requires - not a caller's or a candidate's own claim.
                if 'G2' not in required:
                    raise ValueError('grading revision has no G2 population to '
                                     'check the G3 comparators against')
                _same(candidate.get('matched_population'), required['G2'],
                      'G3 matched comparison population')
            index = 0 if kind == 'G2' else 1
            if set(changed[index]) - targets or changed[1 - index]:
                raise ValueError('grading revision returned an unrequested judgment')
            for key in targets:
                result[index].pop(key, None)
            result[index].update(changed[index])
        verify()
        return tuple(result)

    try:
        B._verdict_maps_from = revised
        yield
    finally:
        B._verdict_maps_from = original
        verify()
