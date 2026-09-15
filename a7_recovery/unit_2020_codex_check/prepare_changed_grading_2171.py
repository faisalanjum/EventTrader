"""Invoke the existing preparer for an approved changed-question subset.

No new rule, packet renderer, batcher, model call or score. Reuse the verified
full population under its exact producer/key/G1 identity. Compare every new
question's evidence with the saved prior question; only instructions change.
"""
import copy
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
for rel in ('unit_2118_correction_native', 'unit_2143_source_authority',
            'unit_2159_current_g3'):
    sys.path.insert(0, str(A7 / rel))
from build_candidate_2148 import E
import a7_g1_key_reuse_2152 as REUSE
import a7_grading_script_binding_2156 as TRANSPORT
import a7_correction_candidate_2118 as PREP
import a7_grading_contract_2168 as V
import g3_checks_2159 as CHECK

G, B, GR = E.G, E.B, E.GR


def pinned(ref):
    assert G._sha_file(ref['path']) == ref['sha256'], ref['path']
    return G._read(ref['path'])


selection_ref = {'path': os.environ['A7_CHANGED_GRADING_SELECTION'],
                 'sha256': os.environ['A7_CHANGED_GRADING_SELECTION_SHA256']}
approval_ref = {'path': os.environ['A7_CURRENT_G23_INPUT'],
                'sha256': os.environ['A7_CURRENT_G23_INPUT_SHA256']}
selection, approved = pinned(selection_ref), pinned(approval_ref)
assert selection['input_correction_sha256'] == G._sha_file(V.__file__)
base = pinned(selection['base_preparation'])
full_ref = {'path': base['full_candidate'], 'sha256': base['full_candidate_sha256']}
full = pinned(full_ref)
assert set(selection['populations']) == set(selection['baseline_candidates'])
assert set(selection['populations']) == set(selection['question_ids'])
assert set(selection['populations']) <= {'G2', 'G3'}
for ref in selection['reviews']:
    assert G._sha_file(ref['path']) == ref['sha256'], ref['path']


def prepare(producer, inputs, g1):
    assert producer == full['producer_identity'] == base['producer']
    assert g1 == base['g1'] == approved['g1']
    assert B.g1_identity(g1) == full['g1_identity']
    assert G.live_key()[1] == full['key_identity'] == base['key_identity']
    required = {'G2': full['g2_pairs'], 'G3': full['g3_idxs']}
    _legs, _totals, _meta, arms, gold, problems = G.inventory(producer)
    assert not problems, problems
    reports = {}
    for kind, subset in sorted(selection['populations'].items()):
        PREP.approved_subset(required[kind], subset)
        wanted = []
        for group, rows in sorted(subset.items()):
            leg, sid = group.split('|', 1)
            wanted.extend(B.meaning_question_id(leg, sid, *row) if kind == 'G2'
                          else B.extras_question_id(leg, sid, row) for row in rows)
        assert len(wanted) == len(set(wanted))
        assert sorted(wanted) == selection['question_ids'][kind]

        # Independent byte comparison with the old full-population questions.
        # G2's earlier display still contains menu tokens; its existing display
        # owner is the only allowed evidence-view transformation. Current G3
        # already has that view and its full matched comparator pool.
        previous_ref = selection['baseline_candidates'][kind]
        previous, _ = G.load_frozen(str(Path(previous_ref['path']).parent),
                                    previous_ref['sha256'])
        assert G._plain(previous['population']) == G._plain(required[kind])
        for field in ('producer_identity', 'g1_identity', 'key_identity'):
            assert G._plain(previous[field]) == G._plain(full[field])
        expected = {}
        for batch in previous['batch_rows']:
            text = (Path(previous_ref['path']).parent / batch['prompt_path']).read_text()
            assert G._sha(text) == batch['prompt_sha256']
            for event in CHECK.body_of(text)['events']:
                assert len(event['questions']) == 1
                qid = event['questions'][0]['question_id']
                assert qid not in expected
                event = copy.deepcopy(event)
                event.pop('event')
                if kind == 'G2':
                    question = event['questions'][0]
                    question['produced_record'] = V.record_view(question['produced_record'])
                expected[qid] = event
        assert set(wanted) <= set(expected)

        with E.R._using(PREP, V=V, CORRECTED_RULES={
                'G2': V.meaning_rules, 'G3': V.extras_rules}):
            path, sha, doc, version = PREP.prepare(
                str(E.out / kind), kind, required[kind], subset, gold, arms,
                producer, inputs, g1, full['key_identity'],
                matched_pairs=required['G2'] if kind == 'G3' else None)
            frozen, _ = G.load_frozen(str(Path(path).parent), sha)
            with PREP.versioned_candidate(version, required['G2'] if kind == 'G3' else None):
                rebuilt = GR.kind_candidate(kind, doc, doc['batching']['rows'], full['key_identity'])
            assert G._plain(frozen) == G._plain(rebuilt)
        assert version == selection['input_correction_sha256']
        assert G._plain(frozen['population']) == G._plain(subset)
        prompts, seen, script_sizes = {}, [], []
        rules = V.meaning_rules() if kind == 'G2' else V.extras_rules()
        for batch in frozen['batch_rows']:
            text = (Path(path).parent / batch['prompt_path']).read_text()
            assert G._sha(text) == batch['prompt_sha256'] and text.startswith(rules)
            prompts[batch['batch_id']] = text
            for event in CHECK.body_of(text)['events']:
                assert len(event['questions']) == 1
                qid = event['questions'][0]['question_id']
                event.pop('event')
                assert qid in wanted and G._plain(event) == G._plain(expected[qid]), qid
                seen.append(qid)
        assert sorted(seen) == sorted(wanted)
        launches = G.launchers(frozen['batch_rows'])
        for ordinal, row in enumerate(launches):
            call = dict(row, ordinal=ordinal, prompt=prompts[row['batch_id']])
            for attempt in range(1, G.MAX_ATTEMPTS + 1):
                size = len(G._bound_script([call], {'candidate_sha256': sha},
                                          '0' * 64, attempt).encode('utf-8'))
                assert size <= GR.W.SCRIPT_BYTE_LIMIT
                script_sizes.append(size)
        reports[kind] = dict(candidate={'path': path, 'sha256': sha},
                             questions=sorted(seen), population=subset,
                             input_correction_sha256=version,
                             batches=len(frozen['batch_rows']),
                             primary_call_ceiling=len(launches),
                             invalid_only_retry_ceiling=len(launches) * (G.MAX_ATTEMPTS - 1),
                             bound_scripts_checked=len(script_sizes),
                             maximum_bound_script_bytes=max(script_sizes))
    report = dict(scope='Verified changed-task preparation, NOT call approval or a score',
                  selection=selection_ref, current_input=approval_ref,
                  caller_sha256=G._sha_file(__file__), producer=producer, g1=g1,
                  key_identity=full['key_identity'], candidates=reports,
                  unchanged_question_evidence=True, model_calls=0)
    G._write_new(str(E.out / 'CHANGED_GRADING_PREPARATION_2171.json'), G._pretty(report) + '\n')
    print('CHANGED QUESTIONS PREPARED', G._plain({kind: {
        k: row[k] for k in ('batches', 'primary_call_ceiling',
                            'invalid_only_retry_ceiling', 'maximum_bound_script_bytes')}
        for kind, row in reports.items()}), flush=True)
    return report


with TRANSPORT.scope(approved['script_binding'], approved['g1']['pins']):
    REUSE.evaluate(E, approved['report'], approved['g1'], prepare)
for ref in [selection_ref, approval_ref, selection['base_preparation'], full_ref] + selection['reviews']:
    assert G._sha_file(ref['path']) == ref['sha256'], ref['path']
print('Completed with no AI call.', flush=True)
