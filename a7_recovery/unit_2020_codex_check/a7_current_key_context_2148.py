"""One input boundary for the corrected key's lock and grading consumer.

The existing owners still reconstruct and validate all history and meaning.
This supplies their recorded inputs, including an older signature's own
ordinary binding while a newer key is being read. No model call or writer.
"""
from contextlib import contextmanager
from pathlib import Path
import sys


@contextmanager
def historical_inputs(R, C, X, signature_inputs):
    """Keep the existing signature verifier; select only its proved input."""
    original = X.signature_accounting

    def historical_signature(candidate_dir):
        if candidate_dir not in signature_inputs:
            raise ValueError('no proved ordinary binding for this historical signature')
        with R._using(C, ORDINARY=signature_inputs[candidate_dir]):
            return original(candidate_dir)

    with R._using(X, signature_accounting=historical_signature):
        yield


@contextmanager
def current_key(E, preparation_path, expected_sha256):
    """Enter only after E has proved the original producer/key context.

    The external pin approves the completed preparation, not a newly read
    candidate. Its existing source binding reconstructs this round and every
    historical round; its ordinary decoder is the candidate owner's.
    """
    G, K, X, R = E.G, E.K, E.X, E.R
    if G._sha_file(str(preparation_path)) != expected_sha256:
        raise ValueError('unapproved current-key preparation')
    prepared = K._load(str(preparation_path))
    if G._sha_file(X.__file__) != prepared['round_owner_sha256']:
        raise ValueError('the current-key history owner changed')
    for rel in ('unit_2136_source_questions', 'unit_2143_source_authority'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_authority_2143 as V
    import a7_round_binding_2136 as B2136
    import a7_round_binding_2143 as B
    import build_final_key_candidate as C

    def intact():
        for name, digest in prepared['candidate_files'].items():
            if G._sha_file(str(Path(prepared['candidate']) / name)) != digest:
                raise ValueError('the prepared candidate changed: ' + name)
        if G._sha_file(prepared['ordinary']) != prepared['ordinary_sha256']:
            raise ValueError('the prepared ordinary binding changed')

    intact()
    bb = B.binding(E, X, B2136, V)
    _shards, raws, _origins, bad = B.current_key(E, X, bb)
    if bad:
        raise ValueError('the proved predecessor no longer reads: %s' % bad[:2])
    findings = B.round_findings(E, bb, raws)
    # Decode the exact complete Bound with its existing owner; no field list
    # or reconstruction of a fact is duplicated here.
    with R._using(C, ORDINARY=prepared['ordinary']):
        bound = C._ordinary_bound()
    packet = bound.decision_correction_v6
    if (not packet or bound != X.bind(bb.bound, packet)
            or set(findings) != set(prepared['replaced_sources'])):
        raise ValueError('the current round does not match its preparation')
    signature_inputs = prepared['historical_signature_inputs']
    original_inputs = {E.result['notes']['candidate']: E.result['notes']['ordinary']}
    if (signature_inputs != original_inputs
            or set(bb.signatures.values()) != set(signature_inputs)):
        raise ValueError('the historical signature input map is not the proved one')
    try:
        with historical_inputs(R, C, X, signature_inputs), \
                B.scope(E, X, bb, bound, findings, V), \
                R._using(C, ORDINARY=prepared['ordinary']):
            yield C, bound, prepared
    finally:
        intact()
