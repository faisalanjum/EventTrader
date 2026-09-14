"""Exercise corrected inputs on the real, verified A7 population; zero AI calls.

This prepares evidence for review, not launch permission or a corrected score.
Original key, producer, G1 and G2/G3 completions remain unchanged.
"""
import os
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_grading_input_correction_2114 as V

G, B, GR = E.G, E.B, E.GR
HERE = Path(__file__).resolve().parent
TRACE_SHA = '0b4a3f624a4024fb071fff1740f04b186027b2c91bcade2aaba4ce6bb05f7ee4'


def prove(producer, inputs):
    trace_path = HERE / 'codex_scoretrace2112_a/SCORER_TRACE.json'
    assert G._sha_file(str(trace_path)) == TRACE_SHA
    trace = G._read(str(trace_path))
    prep_path = os.environ['A7_VERIFY_G23_PREPARATION']
    assert G._sha_file(prep_path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
    prep = G._read(prep_path)
    _legs, _totals, meta, arms, gold, problems = G.inventory(producer)
    assert not problems, problems
    for leg, recorded in trace['records'].items():
        assert G._plain(arms[leg]) == G._plain(recorded['inputs']['arm_by_event']), leg
        assert G._plain(gold) == G._plain(recorded['inputs']['gold_by_event']), leg
    report = {
        'scope': 'Real source-bound corrected input and transport-fit proof; no launch or score',
        'producer': producer, 'key_identity': prep['key_identity'],
        'trace_sha256': TRACE_SHA, 'caller_sha256': G._sha_file(__file__),
        'input_correction_sha256': G._sha_file(V.__file__),
        'source_manifest_sha256': inputs['manifest_sha256'],
        'new_model_calls': 0, 'kinds': {},
        'owners': G.owner_hashes(),
        'batch_owner_sha256': G._sha_file(GR.__file__),
        'transport_gate_sha256': G._sha_file(GR.W.__file__),
    }
    before = G.owner_hashes()
    # THE MATCHED-PAIR INVENTORY, from the frozen G2 candidate's own population.
    # `a7_g23_run.populations` builds that population with `B.matched_pairs`, so
    # it IS the final inventory; a G3 duplicate can only be a duplicate OF one
    # of these (exp5_scoring_spec_v3.md section 5). Nothing is recomputed.
    g2_source = prep['candidates']['G2']
    g2_frozen, _g2sha = G.load_frozen(str(Path(g2_source['path']).parent),
                                      g2_source['sha256'])
    matched_pairs = g2_frozen['population']
    #: made explicit for exactly the asked G3 groups, at the same owner the
    #: preparation seam uses; the sparse canonical population is unchanged.
    g3_source = prep['candidates']['G3']
    g3_frozen, _g3sha = G.load_frozen(str(Path(g3_source['path']).parent),
                                      g3_source['sha256'])
    matched_view = V.matched_inventory(matched_pairs, g3_frozen['population'])
    for kind in ('G2', 'G3'):
        source = prep['candidates'][kind]
        old, _sha = G.load_frozen(str(Path(source['path']).parent), source['sha256'])
        packets, identities = {}, {}
        for key, positions in old['population'].items():
            leg, sid = key.split('|', 1)
            facts = arms[leg][sid]['facts']
            for position in positions:
                if kind == 'G2':
                    packet = V.meaning_packet(leg, sid, [position], gold[sid], facts,
                                               producer, inputs=inputs)
                else:
                    cards = [(i, gold[sid][i]) for i in G.accepted_positions(gold[sid])]
                    packet = V.extras_packet(leg, sid, [position], facts, cards,
                                              producer, inputs=inputs,
                                              matched_pairs=matched_view)
                assert len(packet['question_ids']) == 1
                qid = packet['question_ids'][0]
                assert qid not in packets
                packets[qid] = packet
                identities[qid] = (key, position)
        rows, asked = [], []
        by_identity = {G._plain(identities[q]): packet for q, packet in packets.items()}
        batches = [[identities[q] for q in batch['question_ids']]
                   for batch in old['batch_rows']]
        def build_packet(_batch_id, batch):
            return V.batch_packet(kind, [by_identity[G._plain(row)] for row in batch])
        fitted, prompts, question_batches = GR._rows_and_prompts(kind, batches, build_packet)
        for batch in fitted:
            text = prompts[batch['batch_id']]
            path = E.out / (batch['batch_id'] + '.prompt.txt')
            G._write_new(str(path), text)
            assert G._sha_file(str(path)) == batch['prompt_sha256']
            asked += batch['question_ids']
            rows.append({'batch_id': batch['batch_id'], 'path': str(path),
                         'sha256': batch['prompt_sha256'],
                         'bytes': len(text.encode('utf-8')),
                         'question_ids': batch['question_ids']})
        # Independently inspect the real publisher's fully rendered scripts
        # for every emitted lane; the same gate also bounds every retry.
        launches = G.launchers(fitted)
        script_sizes = []
        for ordinal, call in enumerate(launches):
            call = dict(call, ordinal=ordinal, prompt=prompts[call['batch_id']])
            for attempt in range(1, G.MAX_ATTEMPTS + 1):
                script = G._bound_script([call], {'candidate_sha256': '0' * 64},
                                          '0' * 64, attempt)
                size = len(script.encode('utf-8'))
                assert size <= GR.W.SCRIPT_BYTE_LIMIT, (call['lane_id'], attempt, size)
                script_sizes.append(size)
        assert len(asked) == len(set(asked)) and set(asked) == set(packets)
        assert set(question_batches) == set(packets)
        report['kinds'][kind] = {'original_candidate_sha256': source['sha256'],
                                 'questions': len(asked), 'batches': len(rows),
                                 'maximum_prompt_bytes': max(r['bytes'] for r in rows),
                                 'bound_scripts_checked': len(script_sizes),
                                 'maximum_bound_script_bytes': max(script_sizes),
                                 'script_byte_limit': GR.W.SCRIPT_BYTE_LIMIT,
                                 'rows': rows}
        assert G._sha_file(source['path']) == source['sha256']
    assert G.owner_hashes() == before
    assert G._sha_file(str(trace_path)) == TRACE_SHA
    assert G._sha_file(prep_path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
    G._write_new(str(E.out / 'GRADING_INPUT_PROOF.json'), G._pretty(report) + '\n')
    print('SAVED CORRECTED INPUT PROOF', {
        k: {f: v[f] for f in ('questions', 'batches', 'maximum_prompt_bytes')}
        for k, v in report['kinds'].items()}, flush=True)
    return report


E.with_prepared_inputs(prove)
