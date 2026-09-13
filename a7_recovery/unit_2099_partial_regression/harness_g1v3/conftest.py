"""ONE clearly named fixture for the HISTORICAL structural proofs.

Codex SEQ 1473 ruled option (b): every production/live A7 entry requires
`a7_prepared_run.current`, so a run prepared for an earlier contract era is
refused. The only executed producer run is v1-era - the current-v3 run is
pre-call and holds no answers - so the full-population structural proofs would
have no evidence at all.

This relaxes `PR.current_era`, THE single era gate (`PR.current` = load + that
gate, and a warm trace asks the same gate; Codex SEQ 1489 item D), for the
duration of a test that has explicitly asked for it. It is test-only: there is
no runtime flag, no public history API, no adapter and no second rule engine,
and every other check - the exact identity comparison, the receipt and
finalization validators, the caches - still runs unchanged.

WHEN THE FRESH V3 PRODUCER RUN EXISTS, the same proofs must pass WITHOUT this
fixture before EXP-5 can pass.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


@pytest.fixture(scope="module")
def historical_v1_evidence():
    """Let the live era gate accept the paid v1 run, for THIS module only.

    Module-scoped because several of these proofs build their expensive
    evidence in module-scoped fixtures of their own, which are created outside
    any function-scoped patch - so a function-scoped relaxation would not be in
    force when the evidence is built.
    """
    import a7_prepared_run as PR
    with pytest.MonkeyPatch.context() as m:
        # ONE substitution is enough because `PR.load` fulfils its documented
        # any-era contract and the ledger owns no era rule; `PR.current_era`
        # is the single live gate that `PR.current` and a warm trace both ask
        # (Codex SEQ 1475; SEQ 1489 item D).
        # ONLY this one substitution. Also patching `require_current_era`
        # globally weakened the ledger's era check and contradicted this
        # fixture's own description (Codex SEQ 1474 item 1).
        m.setattr(PR, "current_era", lambda identity: identity)
        yield "historical: the paid v1 run, not current-era evidence"


# --------------------------------------------------------------------------
# THE CURRENT GRADING SCORER, supplied the way the production caller supplies
# it (Codex SEQ 1851). `a7_g23_build` deliberately refuses to render or score
# until a scorer is bound BY FILE AND HASH, so a suite that never binds one
# fails with "no current grading scorer is bound" rather than testing
# behaviour. This binds the same scorer the native entry binds; it relaxes
# nothing - the mismatch refusal is proved separately by its own mutation.
@pytest.fixture(autouse=True, scope="session")
def _bound_grading_scorer():
    import hashlib
    import a7_g23_build as B
    # the CURRENT grading scorer, kept beside the ERA scorer under its own
    # name: a6_launch_freeze hashes "score_exp5.py" into the producer era
    # freeze, so the era file must stay exactly what the era pinned.
    path = os.path.join(_HERE, "scorers", "score_exp5_current.py")
    if not os.path.isfile(path):
        return
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    B.bind_grading_scorer(path, digest)
