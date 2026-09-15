"""Apply ordered, pinned corrections through the unchanged revision owner.

Each revision still validates the whole base and its own native completion.
Only its internal correction read reaches the original evidence consumer:
an earlier revision must not mistake that approved subset for a full run.
No verdict, matching rule, source fact or completion is created here.
"""
import copy
from contextlib import ExitStack, contextmanager

import a7_grading_revision_2115 as REV

G, B = REV.G, REV.B
REVISION_SHA256 = 'dd708431e2a106c4f711b89dfe8b9918a52ddf4f8616f5fefb94fa742783de76'


def _consumer_for(plan, prior, native):
    def consume(leg, sources, producer, required, g1, memo):
        same = lambda a, b: G._plain(a) == G._plain(b)
        if (same(sources, plan['base_sources'])
                and same(required, plan['required_population'])):
            return prior(leg, sources, producer, required, g1, memo)
        for kind, correction in plan['corrections'].items():
            if (same(sources, {kind: correction['source']})
                    and same(required, {kind: correction['population']})):
                return native(leg, sources, producer, required, g1, memo)
        raise ValueError('a revision requested evidence outside its approved plan')
    return consume


@contextmanager
def scope(revisions, expected_code_sha256):
    """Later approved revisions replace only their own questions, in order."""
    if (not isinstance(revisions, list) or not revisions
            or any(not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
                   for ref in revisions)):
        raise ValueError('a correction chain requires pinned revision references')
    refs = copy.deepcopy(revisions)
    if len({ref['sha256'] for ref in refs}) != len(refs):
        raise ValueError('a correction chain repeats a revision')

    def verify():
        if (G._sha_file(__file__) != expected_code_sha256
                or G._sha_file(REV.__file__) != REVISION_SHA256):
            raise ValueError('unapproved correction-chain owner')
        for ref in refs:
            if G._sha_file(ref['path']) != ref['sha256']:
                raise ValueError('unapproved correction-chain revision')

    verify()
    native = B._verdict_maps_from
    try:
        with ExitStack() as scopes:
            for ref in refs:
                plan = G._read(ref['path'])
                # The unchanged owner checks the complete plan and every
                # producer/key/population/version/root/completion binding.
                prior = B._verdict_maps_from
                scopes.callback(setattr, B, '_verdict_maps_from', prior)
                B._verdict_maps_from = _consumer_for(plan, prior, native)
                scopes.enter_context(REV.scope(ref['path'], ref['sha256']))
            yield
    finally:
        verify()
