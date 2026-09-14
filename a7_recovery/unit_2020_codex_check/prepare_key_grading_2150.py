"""Form a new saved-answer evaluation and measure actual new-key G1 inputs.

No model calls or verdict transfer. The original G1 is first proved in its
own context. Existing A6/PR, materializer, reference and question owners then
read the newly signed key. A changed row is a finding to resolve, not automatic
permission to repeat a call whose complete model-facing input is unchanged.
"""
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2143_source_authority'))
from build_candidate_2148 import E
import a7_current_key_context_2148 as CURRENT
import a7_signed_key_input_2149 as INPUT
import build_a5_exp5_kit as A5
import a7_reference_inventory as RI

G, K, B, R = E.G, E.K, E.B, E.R


def compare_events(old, new):
    """Compare complete event input and row binding; ignore packaging number."""
    shared = set(old) & set(new)
    same = {k for k in shared if all(old[k][f] == new[k][f]
                                    for f in ('prompt', 'items', 'full_positions'))}
    return {name: [list(k) for k in sorted(keys)] for name, keys in (
        ('unchanged', same), ('changed', shared - same),
        ('added', set(new) - set(old)), ('removed', set(old) - set(new)))}


def event_inputs(producer, candidate, key):
    items, _legs, _totals, _meta, bad = G.questions(producer)
    assert not bad, bad
    assert len(items) == candidate['questions']
    groups = G.event_groups(items)
    batches = {tuple(row['question_ids']): row for row in candidate['batch_rows']}
    assert len(batches) == len(candidate['batch_rows']) == len(groups)
    result = {}
    for ident, group in groups.items():
        batch = batches[tuple(i['question_id'] for i in group)]
        packet = G.event_packet(group)
        assert G._sha(packet['prompt']) == batch['prompt_sha256']
        assert packet['produced_idxs'] == batch['produced_idxs']
        full = G.accepted_positions(key[ident[1]])
        result[ident] = {'batch_id': batch['batch_id'], 'items': group,
                         'full_positions': [full[i['gold_idx']] for i in group],
                         'prompt': packet['prompt']}
    return result


def connect(original, _original_inputs):
    # This reuses the full original lifecycle owner, including both native
    # lanes and the explicit partial-event accounting. No identity is relabelled.
    _old_root, old_candidate, _old_lanes = B._lifecycle(E.g1)
    old_key, old_identity = G.live_key()
    assert old_candidate['producer_identity'] == original
    assert old_candidate['materialization']['key_identity'] == old_identity
    old_events = event_inputs(original, old_candidate, old_key)
    old_arms, old_meta, bad = G.materialize(original)
    assert not bad, bad
    evaluation = K._load(str(Path(E.prep['evaluation']) / E.A6.REUSE_FREEZE_NAME))
    preparation = os.environ['A7_CURRENT_KEY_PREPARATION']
    prep_pin = os.environ['A7_CURRENT_KEY_PREPARATION_SHA256']
    signed_path = os.environ['A7_CURRENT_SIGNED_KEY']
    signed_pin = os.environ['A7_CURRENT_SIGNED_KEY_SHA256']

    with CURRENT.current_key(E, preparation, prep_pin) as (_C, bound, prepared), \
            INPUT.approved_inputs(E, A5, signed_path, signed_pin) as signed:
        assert signed['preparation'] == preparation
        assert signed['preparation_sha256'] == prep_pin
        assert signed['ordinary'] == prepared['ordinary']
        assert G._approved_bound() == bound
        fresh = E.A6.reuse_freeze(original['run_dir'], evaluation['initial_key_manifest'])
        out = E.out / 'evaluation'
        out.mkdir()
        freeze_path = out / E.A6.REUSE_FREEZE_NAME
        G._write_new(str(freeze_path), E.A6.render(fresh) + '\n')
        freeze_pin = G._sha_file(str(freeze_path))
        producer = E.PR.reuse(str(out), freeze_pin)
        changed_identity = {k for k in set(original) | set(producer)
                            if original.get(k) != producer.get(k)}
        assert changed_identity == {'a4_lock_sha256', 'a4_lock_receipt_sha256',
                                    'evaluation_dir', 'a6_freeze_sha256'}, changed_identity
        assert producer['a4_lock_sha256'] == signed['lock_sha256']
        assert producer['a4_lock_receipt_sha256'] == signed['receipt_sha256']
        assert fresh['database_writes'] == fresh['armed_grader_calls'] == 0
        assert fresh['activated'] is False
        print('New evaluation proved; original answers/launch/finalization unchanged', flush=True)

        key, identity = G.live_key()
        assert identity['approved_lock_sha256'] == signed['lock_sha256']
        assert identity['accepted_rows'] == signed['counts']['du_worthy_facts']
        assert identity['events'] == signed['counts']['events_accounted']
        arms, meta, bad = G.materialize(producer)
        assert not bad, bad
        assert arms == old_arms
        assert meta['trace'] == old_meta['trace']
        assert meta['answers'] == old_meta['answers'] == producer['scheduled_calls']
        assert meta['key_identity'] == identity != old_identity

        reference_path = E.out / 'reference_inventory.json'
        reference = RI.expected_document(producer)
        reference_pin = RI.write(reference, str(reference_path))
        with R._using(RI, INVENTORY_PATH=str(reference_path)):
            reference_rows = RI.validate(run=producer)
            assert len(reference_rows) == identity['accepted_rows']
            path, bad = G.write(str(E.out / 'g1_candidate'), producer)
            assert not bad, bad
            candidate = K._load(path)
            assert candidate['materialization']['key_identity'] == identity
            new_events = event_inputs(producer, candidate, key)
            for row in candidate['batch_rows']:
                prompt = Path(path).parent / row['prompt_path']
                assert G._sha_file(str(prompt)) == row['prompt_sha256']
            comparison = compare_events(old_events, new_events)
            report = {
                'scope': 'Real corrected-key saved evaluation and G1 preparation; '
                         'NO new model call, reused verdict or corrected score',
                'caller_sha256': G._sha_file(__file__),
                'context_sha256': G._sha_file(CURRENT.__file__),
                'input_owner_sha256': G._sha_file(INPUT.__file__),
                'signed_key_report': signed_path, 'signed_key_report_sha256': signed_pin,
                'original_producer': original, 'producer': producer,
                'original_g1': E.g1, 'key_identity': identity,
                'evaluation': str(out), 'evaluation_sha256': freeze_pin,
                'reference_inventory': str(reference_path),
                'reference_inventory_sha256': reference_pin,
                'g1_candidate': path, 'g1_candidate_sha256': G._sha_file(path),
                'changed_identity_fields': sorted(changed_identity),
                'unchanged_answer_trace_sha256': G._sha(G._plain(meta['trace'])),
                'saved_answers': meta['answers'], 'scheduled_events': meta['events'],
                'key_events': identity['events'], 'key_facts': identity['accepted_rows'],
                'original_questions': old_candidate['questions'],
                'current_questions': candidate['questions'],
                'event_comparison': comparison,
                'event_counts': {k: len(v) for k, v in comparison.items()},
                'original_events': [dict(v, leg=k[0], source_id=k[1])
                                    for k, v in sorted(old_events.items())],
                'current_events': [dict(v, leg=k[0], source_id=k[1])
                                   for k, v in sorted(new_events.items())],
                'new_model_calls': 0,
            }
            G._write_new(str(E.out / 'KEY_GRADING_INPUTS.json'), G._pretty(report) + '\n')
            print('Actual current G1 questions:', candidate['questions'],
                  'event comparison:', report['event_counts'], flush=True)
    assert G.live_key()[1] == old_identity
    assert G._sha_file(signed_path) == signed_pin
    return report


if __name__ == '__main__':
    E.with_prepared_inputs(connect)
