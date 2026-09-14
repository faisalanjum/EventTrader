"""Real saved-judgment connection and exact corrective G2 preparation; no calls.

The current full population is the already verified, frozen native result.
Its context/G1 and the original G2 run are proved again by their existing
owners. This is a base-consumer proof, NOT the corrected score.
"""
import copy
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
for rel in ('unit_2118_correction_native', 'unit_2143_source_authority'):
    sys.path.insert(0, str(A7 / rel))
from build_candidate_2148 import E
import a7_g2_key_reuse_2159 as REUSE
import a7_grading_script_binding_2156 as TRANSPORT
import a7_correction_candidate_2118 as PREPARE
import a7_grading_input_correction_2114 as V

G, B, GR = E.G, E.B, E.GR
plan_path, plan_sha = os.environ['A7_G2_KEY_REUSE_PLAN'], os.environ['A7_G2_KEY_REUSE_PLAN_SHA256']
assert G._sha_file(plan_path) == plan_sha
plan = G._read(plan_path)
selection = REUSE.derive(plan['selection']['path'], plan['selection']['sha256'])
current = G._read(plan['current_preparation']['path'])
old = G._read(plan['original_proof']['path'])
approval_path = os.environ['A7_CURRENT_G23_INPUT']
assert G._sha_file(approval_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
approved = G._read(approval_path)
assert approved['g1'] == current['g1']


def prove(producer, inputs, g1):
    root, _candidate, lanes = B._lifecycle(g1)
    missing = [r['lane_id'] for r in root['rows'] if lanes[r['lane_id']]['selected'] is None]
    assert len(lanes) == approved['expected_total_lanes']
    assert missing == approved['expected_exhausted_invalid_lanes']
    required = {}
    for kind, ref in current['candidates'].items():
        doc, _ = G.load_frozen(str(Path(ref['path']).parent), ref['sha256'])
        required[kind] = doc['population']
    rows = []
    for leg in sorted({t['group'].split('|', 1)[0] for t in selection['current_tasks'].values()}):
        meanings, extras = B.official_verdict_maps(leg, old['g23_sources'], producer, required, g1)
        assert not extras, 'original extras must not supply new-context credit'
        expected_keys = set()
        for qid, old_id in sorted(selection['carry'].items()):
            task = selection['current_tasks'][qid]
            group_leg, sid = task['group'].split('|', 1)
            if leg != group_leg:
                continue
            key = (sid, task['pair'][0])
            expected_keys.add(key)
            rows.append(dict(question_id=qid, original_question_id=old_id, group=task['group'],
                             current_pair=task['pair'], original_pair=selection['original_tasks'][old_id]['pair'],
                             established=meanings.get(key), has_established_fields=key in meanings))
        assert not (set(meanings) - expected_keys)
    assert len(rows) == len(selection['carry'])
    print('Native original G2 -> current-key consumer proved:', len(rows),
          'selected tasks;', sum(r['has_established_fields'] for r in rows),
          'with any established fields. Preparing only corrections.', flush=True)

    _legs, _totals, _meta, arms, gold, problems = G.inventory(producer)
    assert not problems, problems
    path, sha, doc, version = PREPARE.prepare(
        str(E.out / 'G2'), 'G2', required['G2'], selection['correction_population'],
        gold, arms, producer, inputs, g1, current['key_identity'])
    frozen, _ = G.load_frozen(str(Path(path).parent), sha)
    assert frozen['input_correction_sha256'] == version == G._sha_file(V.__file__)
    assert G._plain(frozen['population']) == G._plain(selection['correction_population'])
    with PREPARE.versioned_candidate(version):
        assert G._plain(frozen) == G._plain(GR.kind_candidate('G2', doc, doc['batching']['rows'], current['key_identity']))
    asked, scripts = set(), []
    prompts = {}
    for batch in frozen['batch_rows']:
        text = (Path(path).parent / batch['prompt_path']).read_text(encoding='utf-8')
        assert G._sha(text) == batch['prompt_sha256']
        assert text.startswith(V.meaning_rules())
        prompts[batch['batch_id']] = text
        import json
        for event in json.loads(text.split('[EVENT]\n', 1)[1])['events']:
            for question in event['questions']:
                qid = question['question_id']
                assert qid not in asked and qid not in selection['carry']
                expected = copy.deepcopy(selection['current_tasks'][qid]['question'])
                expected['produced_record'] = V.record_view(expected['produced_record'])
                assert G._plain(question) == G._plain(expected)
                assert G._plain(event['event_context']) == G._plain(selection['current_tasks'][qid]['context'])
                asked.add(qid)
    assert asked | set(selection['carry']) == set(selection['current_tasks'])
    launches = G.launchers(frozen['batch_rows'])
    for ordinal, row in enumerate(launches):
        call = dict(row, ordinal=ordinal, prompt=prompts[row['batch_id']])
        for attempt in range(1, G.MAX_ATTEMPTS + 1):
            size = len(G._bound_script([call], {'candidate_sha256': sha}, '0'*64, attempt).encode('utf-8'))
            assert size <= GR.W.SCRIPT_BYTE_LIMIT
            scripts.append(size)
    report = dict(scope='REAL original G2 native proof, current-key/G1 consumer, and corrected G2 inputs; NOT a final score or call approval',
                  plan_path=plan_path, plan_sha256=plan_sha, caller_sha256=G._sha_file(__file__),
                  producer=producer, g1=g1, key_identity=G.live_key()[1],
                  required_population=required, native_carry=rows,
                  current_question_count=len(selection['current_tasks']), carry_count=len(rows),
                  correction_count=len(asked), correction_population=selection['correction_population'],
                  corrected_candidate=dict(path=path, sha256=sha), input_correction_sha256=version,
                  batches=len(frozen['batch_rows']), primary_call_ceiling=len(launches),
                  invalid_only_retry_ceiling=len(launches)*(G.MAX_ATTEMPTS-1),
                  bound_script_checks=len(scripts), maximum_bound_script_bytes=max(scripts),
                  g1_total=len(lanes), g1_exhausted_invalid=missing, new_model_calls=0)
    G._write_new(str(E.out/'G2_REUSE_AND_CORRECTION_2159.json'), G._pretty(report)+'\n')
    print('Corrected G2 preparation:', len(asked), 'questions;', len(frozen['batch_rows']),
          'batches;', len(launches), 'primary lanes;', max(scripts), 'max script bytes.', flush=True)
    return report


with TRANSPORT.scope(approved['script_binding'], approved['g1']['pins']):
    REUSE.evaluate(E, plan_path, plan_sha, prove)
assert G._sha_file(approval_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
print('Native G2 reuse and corrective preparation complete; no model call.', flush=True)
