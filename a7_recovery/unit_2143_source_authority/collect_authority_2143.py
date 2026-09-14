# -*- coding: utf-8 -*-
"""Collect this prepared source round through the unchanged collection owner.

Run through the frozen native command. Explicit report/hash/state inputs name
the packet; an empty state list is a missing answer, never a completed review.
This entry starts no model and makes no semantic or retry decision.
"""
import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path


def collect(E, report_path, expected_sha256, states):
    for rel in ('unit_2136_source_questions', 'unit_2143_source_authority'):
        sys.path.insert(0, str(E.A7 / rel))
    import collect_questions_2136 as C
    import a7_round_binding_2136 as B2136
    import a7_round_binding_2143 as B
    import a7_source_authority_2143 as V
    return C.collect(E, E.X, B, B2136, V, report_path, expected_sha256, states)


def main():
    report = os.environ['A7_COLLECT_REPORT']
    report_sha256 = os.environ['A7_COLLECT_REPORT_SHA256']
    states = json.loads(os.environ['A7_COLLECT_STATES'])
    tag = os.environ['A7_TAG']
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                           / 'unit_2020_codex_check'))
    import prepare_g23_partial_2097 as E
    candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
    if E.G._sha_file(candidate) != os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']:
        raise ValueError('the round-input owner is not the pinned candidate')
    spec = importlib.util.spec_from_file_location(
        'round_owner_2143', candidate,
        loader=SourceFileLoader('round_owner_2143', candidate))
    E.X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E.X)

    def run(_producer, _inputs):
        out = E.A7 / 'unit_2143_source_authority' / tag
        out.mkdir(parents=True)
        record = collect(E, report, report_sha256, states)
        E.G._write_new(str(out / 'COLLECTION_2143.json'),
                       E.G._pretty(record) + '\n')
        print('COLLECTION_2143', json.dumps({
            'phase_complete': record['finalization']['phase_complete'],
            'ledger': record['finalization']['ledger'],
            'retry': record['finalization']['retry']}), flush=True)
        return record

    E.with_prepared_inputs(run)


if __name__ == '__main__':
    main()
