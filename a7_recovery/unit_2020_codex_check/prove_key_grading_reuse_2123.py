"""Freeze the existing key-dependent grading inputs before any key correction.

This is a no-call diagnostic, not a replacement consumer or a new key. It
reconstructs every original G1 event prompt, validates the saved G2/G3 through
their existing consumer, and records the exact event boundaries needed to
decide reuse after an independently signed key correction exists.
"""
import os
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_meaning_format_2105 as FORMAT

G, B = E.G, E.B
HERE = Path(__file__).resolve().parent


def prove(producer, _inputs):
    baseline_path = Path(os.environ['A7_BASELINE_PATH'])
    assert G._sha_file(str(baseline_path)) == os.environ['A7_BASELINE_SHA256']
    baseline = G._read(str(baseline_path))
    assert baseline['producer'] == producer
    assert baseline['g1'] == E.g1
    gold, identity = G.live_key()
    assert identity == baseline['key_identity']
    root, candidate, lanes = B._lifecycle(E.g1)
    assert candidate['producer_identity'] == producer
    assert candidate['materialization']['key_identity'] == identity

    items, _legs, _totals, _meta, problems = G.questions(producer)
    assert not problems, problems
    by_qid = {row['question_id']: row for row in items}
    assert len(by_qid) == len(items) == candidate['questions']
    bindings = {row['question_id']: row for row in candidate['question_bindings']}
    assert set(by_qid) == set(bindings)
    groups = G.event_groups(items)
    seen, event_rows = set(), []
    for batch in candidate['batch_rows']:
        current = [by_qid[qid] for qid in batch['question_ids']]
        group = (current[0]['leg'], current[0]['source_id'])
        assert current == groups[group]
        assert group not in seen
        seen.add(group)
        packet = G.event_packet(current)
        prompt = Path(E.g1['candidate_dir']) / batch['prompt_path']
        assert prompt.read_text() == packet['prompt']
        assert G._sha_file(str(prompt)) == batch['prompt_sha256']
        assert batch['produced_idxs'] == packet['produced_idxs']
        assert batch['source_ids'] == [group[1]] * len(current)
        for item in current:
            qid = item['question_id']
            assert bindings[qid] == {
                'question_id': qid,
                'internal_key': G.internal_key(*group, item['gold_idx']),
                'leg': group[0], 'source_id': group[1],
                'gold_idx': item['gold_idx'], 'batch_id': batch['batch_id'],
                'candidates': packet['produced_idxs'],
            }
        selected = [row for row in root['rows'] if row['batch_id'] == batch['batch_id']]
        assert len(selected) == len(G.GRADER_LANES)
        event_rows.append({
            'leg': group[0], 'source_id': group[1],
            'batch_id': batch['batch_id'], 'prompt_sha256': batch['prompt_sha256'],
            'question_ids': batch['question_ids'], 'produced_idxs': packet['produced_idxs'],
            'lanes': {row['lane_id']: {
                'selected_attempt': lanes[row['lane_id']]['selected'],
                'attempts': lanes[row['lane_id']]['attempts'],
            } for row in selected},
        })
    assert seen == set(groups)

    prep_path = os.environ['A7_VERIFY_G23_PREPARATION']
    assert G._sha_file(prep_path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
    prep = G._read(prep_path)
    required = {}
    for kind, source in prep['candidates'].items():
        doc, _ = G.load_frozen(str(Path(source['path']).parent), source['sha256'])
        required[kind] = doc['population']
    memo, verdict_counts = {}, {}
    with FORMAT.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
        for leg in sorted(prep['findings']):
            meaning, extras = B._verdict_maps_from(
                leg, baseline['sources'], producer, required, E.g1, memo)
            verdict_counts[leg] = {'meaning_with_any_established_fields': len(meaning),
                                   'agreed_extra_verdicts': len(extras)}
    assert len(memo) == len(required)
    assert G._sha_file(str(baseline_path)) == os.environ['A7_BASELINE_SHA256']
    report = {
        'scope': 'Original-context evidence for later reuse; NOT a new-key handoff or score',
        'caller_sha256': G._sha_file(__file__), 'baseline_sha256': os.environ['A7_BASELINE_SHA256'],
        'producer_identity': producer, 'key_identity': identity, 'g1': E.g1,
        'g23_sources': baseline['sources'], 'required_population': required,
        'key_event_hashes': {sid: G._sha(G._plain(rows)) for sid, rows in gold.items()},
        'g1_event_inputs': event_rows, 'g1_questions': len(items),
        'g1_events': len(event_rows), 'g23_verdict_counts': verdict_counts,
        'new_model_calls': 0,
        'remaining': 'Only a new independently signed key can establish the actual changed '
                     'population. Do not relabel old roots or transfer a verdict by index alone.',
    }
    G._write_new(str(E.out / 'KEY_GRADING_REUSE_BASE.json'), G._pretty(report) + '\n')
    print('VERIFIED ORIGINAL INPUTS', len(items), len(event_rows), verdict_counts, flush=True)


E.with_prepared_inputs(prove)
