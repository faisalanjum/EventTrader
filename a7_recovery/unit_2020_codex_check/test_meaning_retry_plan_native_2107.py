"""Prove retry filtering from saved native TEST evidence, with no new calls."""
import os
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, R = ctx['G'], ctx['R']
import a7_g1_complete_v2 as C
import audit_worker_access as AUD
import meaning_retry_plan_2107 as M

path = HERE / 'codex_formatnative2105_c/SCORING_CONNECTION.json'
assert G._sha_file(str(path)) == 'be7ddc2123c5722c8fd9c8272c8afc24636e220606119b1cc4448c8a7fba8c06'
proof = G._read(str(path))
source = proof['sources']['G2']
run, root_sha = source['run_dir'], source['root_sha256']
root = G.load_root(run, root_sha)
candidate = root['candidate_dir']
identity = proof['completion']['run_identity']
before = C.run_digest(run)
assert before == (identity['run_digest'], identity['run_files'])
doc, _ = G.load_frozen(candidate, root['candidate_sha256'])
bad_lane = doc['batch_rows'][3]['batch_id'] + '/' + G.GRADER_LANES[0]
projects = str(Path(run).parent / 'projects')
with R._using(AUD, PROJECTS_ROOT=projects):
    first = M.plan(candidate, run, 1, root_sha, G._sha_file(G.receipt_path(run, 1)),
                   os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256'])
    assert first['retry_lanes'] == [bad_lane], first
    assert len(first['recovered']) == len(root['rows']) - 1
    assert not any(row['audit']['original_valid'] for row in first['readings'])
    assert any(value is False for row in first['readings'] if row['answer'] is not None
               for verdict in row['answer'].values() for value in verdict.values())
    assert any(value is None for row in first['readings'] if row['answer'] is not None
               for verdict in row['answer'].values() for value in verdict.values())
    # The filter does NOT grant a launch. This fixture has already consumed
    # that remaining retry; the original publisher must still refuse it.
    publication, problems = G.publish_run(candidate, run, root_sha, first['retry_lanes'], attempt=2)
    assert publication is None and any('already reserved' in p for p in problems)
    second = M.plan(candidate, run, 2, root_sha, G._sha_file(G.receipt_path(run, 2)),
                    os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256'])
    assert not second['retry_lanes'] and second['unusable'] == [bad_lane]
    for field in ('root', 'receipt', 'code', 'rule'):
        values = [root_sha, G._sha_file(G.receipt_path(run, 1)),
                  os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']]
        values[('root', 'receipt', 'code', 'rule').index(field)] = '0' * 64
        try:
            M.plan(candidate, run, 1, *values)
        except ValueError:
            pass
        else:
            raise AssertionError('wrong %s pin did not refuse' % field)
assert C.run_digest(run) == before
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'RETRY_PLAN_PROOF.json'), G._pretty({
    'scope': 'native TEST evidence; no launch or real collection mutation',
    'owner_sha256': G._sha_file(M.__file__), 'first': first, 'second': second,
    'new_model_calls': 0, 'run_unchanged': True,
    'original_publisher_refuses_consumed_retry': True}) + '\n')
print('VERIFIED:139 recovered readings never repeated; one genuine invalid remains; original publisher owns eligibility', flush=True)
