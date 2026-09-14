"""Actual completed-round proof; expected raw hashes come from a separate run.

No model calls or receipt edits. Each case starts in its own native process.
The warm-context case intentionally changes only the declared input after a
valid read inside one operation; stale acceptance must not hide that change.
"""
import importlib.util
import os
import sys
from pathlib import Path

import prepare_g23_partial_2097 as E

OWNER = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(OWNER) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location('round_owner_2134', OWNER)
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)
E.X = X
CASE = os.environ['A7_CASE']
EXPECTED = E.A7 / 'unit_2020_codex_check/codex_cold2131_b/COLD_SEVEN_BOUNDARY.json'
assert E.G._sha_file(str(EXPECTED)) == '4347ec1aa50f22f506183b757edef996b067acbe0c7ee71aad9726ec3eee6c1b'


def run(_producer, _inputs):
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2132_history_input'):
        sys.path.insert(0, str(E.A7 / rel))
    import a4_source_taskv2 as V2
    import a7_source_context_2127 as V3
    import a7_round_binding_2128 as B
    import a4_v6_history_input_2132 as H

    assert E.G._sha_file(H.__file__) == '48abdac2893f39ea311f0754fb40091a17bae4fecba5217753602d33bdf54341'
    renderer = str(E.A7 / 'unit_2127_source_context/a7_source_context_2127.py')
    ri = H.round_input(E.G._sha_file, renderer,
                      '002001473da073b21dfa6e5db7aed620d0da7da96d787a5127b292e7014d7c33')
    expected = E.K._load(str(EXPECTED))
    done = expected['run']
    assert E.G._sha_file(os.path.join(done, E.K.RECEIPT_NAME)) == expected['receipt_sha256']
    assert E.G._sha_file(os.path.join(done, E.K.FINALIZATION_NAME)) == expected['finalization_sha256']
    b = B.binding(E, X)
    # This is the older key needed to derive the completed round's findings,
    # NOT a positive read of the seven results being tested.
    old = B.current_key(E, X, b)
    assert not old[3] and len(old[1]) == 33, old[3]
    findings = B.round_findings(E, b, old[1])
    prior = b.prior + ((b.predecessor, b.predecessor_findings),)

    def clarified(bnd, keys):
        with E.R._using(V2, served_prefix=V3.served_prefix):
            return X.C2065.closeout_prefix(bnd, keys)

    def key(declared):
        if CASE.startswith('root_'):
            return X.first_round_key(
                b.bound, done, findings, E.source_inputs, prior,
                signatures=b.signatures,
                prefixes={r: clarified for r in declared})
        return H.first_round_key(E, X, b.bound, done, findings,
                                 E.source_inputs, prior, signatures=b.signatures,
                                 carrier=V2, inputs=declared)

    def check():
        got = key({done: ri})
        raw_hashes = {sid: E.K._sha(raw) for sid, raw in got[1].items()}
        assert not got[3] and raw_hashes == expected['raw_hashes'], got[3]
        result = {'case': CASE, 'positive_sources': len(raw_hashes),
                  'external_expected_sha256': E.G._sha_file(str(EXPECTED)),
                  'raw_hashes': raw_hashes, 'model_calls': 0}
        if CASE in ('core_warm_missing', 'root_warm_missing', 'root_flow'):
            try:
                key({})
            except ValueError as exc:
                result['missing_input_refusal'] = str(exc)
                assert 'receipt.prompts' in str(exc), str(exc)
            else:
                raise AssertionError('missing declared input accepted from the warm cache')
        else:
            assert CASE in ('core_cold', 'root_cold'), CASE
        if CASE == 'root_flow':
            again = key({done: ri})
            assert {sid: E.K._sha(raw) for sid, raw in again[1].items()} == raw_hashes
            next_dir = str(E.A7 / 'unit_2020_codex_check' /
                           os.environ['A7_TAG'] / 'unlaunched_test_next_round')
            next_bound = X.bind(b.bound, next_dir)
            next_findings = B.round_findings(E, b, got[1])
            with X.successor_scope(
                    next_bound, next_findings, done, findings, E.source_inputs,
                    prior, signatures=b.signatures,
                    prefixes={done: clarified, next_dir: clarified}):
                result['next_round_ledger_before'] = E.F.v6_budget(next_bound)['before']
                assert result['next_round_ledger_before'] == 677
                prepared = E.F.prepare_v6(next_dir, next_bound)
                assert prepared['ok'], prepared
                result['unlaunched_test_scripts'] = len(prepared['invocations'])
                assert result['unlaunched_test_scripts'] == len(findings)
            chain = list(prior) + [(done, findings)]
            prompts = {}
            for i, (run_dir, run_findings) in enumerate(chain):
                recorded = E.K._load(os.path.join(run_dir, E.K.RECEIPT_NAME))['prompts']
                prior_i = tuple(chain[:i])
                allowed = {r for r, _ in prior_i} | {run_dir}
                sigs = {r: p for r, p in b.signatures.items() if r in allowed}
                with X.first_round_scope(
                        b.bound, run_dir, run_findings, E.source_inputs, prior_i,
                        signatures=sigs, prefixes={done: clarified} if run_dir == done else {}):
                    derived = {label: E.K._sha(E.F.v6_prompt(X.first_bound(b.bound, run_dir), label))
                               for label in recorded}
                assert derived == recorded, run_dir
                prompts[run_dir] = len(recorded)
            assert len(prompts) == 5 and sum(prompts.values()) == 19, prompts
            result['historical_prompts'] = prompts
        return result

    # Clear the operation-scoped caches only at this new operation boundary,
    # never between its correctly-declared and incorrectly-declared reads.
    with E.R._using(E.F, _OP_DEPTH=[0]):
        result = E.F._operation(check)()
    result.update(caller_sha256=E.G._sha_file(__file__),
                  owner_sha256=E.G._sha_file(OWNER),
                  candidate_sha256=E.G._sha_file(H.__file__))
    out = E.A7 / 'unit_2020_codex_check' / os.environ['A7_TAG']
    E.G._write_new(str(out / 'COLD_HISTORY.json'), E.G._pretty(result) + '\n')
    print('COLD_HISTORY', E.G._pretty(result), flush=True)


E.with_prepared_inputs(run)
