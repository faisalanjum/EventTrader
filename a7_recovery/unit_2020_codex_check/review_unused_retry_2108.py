"""Read-only independent reproduction of Core2108's remaining boundary gap."""
import copy
import json
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, R, run, candidate, launch = (ctx[k] for k in ('G', 'R', 'run_dir', 'cand', 'launch'))
sys.path.insert(0, str(HERE.parent / 'unit_2106_unused_retry'))
import a7_unused_retry_closure_2106 as CL
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F

assert G._sha_file(CL.__file__) == '5504673f343816821f49764189e3b833695da7d542ee7d262a8633e43451521a'
out = HERE / os.environ['A7_TAG']
out.mkdir()
before = C.run_digest(run)
args = (str(Path(G.__file__).parent), str(HERE), candidate, run, 5,
        launch['root_sha256'],
        'b04fe0d4668b9be916a855a6146b1dcfbd83b920e221d124afff7fd8d67b80b2',
        launch['workflow_gate_sha256'], os.environ['A7_FORMAT_CODE_SHA256'],
        os.environ['A7_FORMAT_RULE_SHA256'],
        '/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl')
positive, problems = CL.inspect(*args)
assert positive is not None and not problems, problems

# Corrupt only a copied whole record, including its self-hash. The real
# native transcript is unchanged, so a native-evidence comparison must fail.
original_path = G.whole_path
whole = copy.deepcopy(G._read(original_path(run, 4)))
row = whole['lanes']['G2-001/G1a']
raw = row['text']
assert '"true"' in raw
row['text'] = raw.replace('"true"', '"false"', 1)
assert row['text'] != raw
row['sha256'], row['chars'] = G._sha(row['text']), len(row['text'])
fake = str(out / 'TEST_only_false_whole.json')
G._write_new(fake, G._pretty(whole) + '\n')
with R._using(G, whole_path=lambda r, n: fake if r == run and n == 4 else original_path(r, n)):
    accepted, problems = CL.inspect(*args)
assert accepted is not None and not problems, problems
assert accepted['prior_reading']['G2-001/G1a']['prior_raw_sha256'] != positive['prior_reading']['G2-001/G1a']['prior_raw_sha256']

# The reported completion crash is a caller-shape error: the existing owner
# consumes relations, not the evidence owner's per-lane wrapper dictionaries.
closed = str(HERE.parent / 'unit_2106_unused_retry/testruns/connection/run')
digest, files = C.run_digest(closed)
with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
    root, doc, lanes, problems = C.evidence(candidate, closed, launch['root_sha256'], digest, files)
    assert not problems, problems
    completion, problems = C.complete_g23(doc, C.relations_from_run(lanes), C.g23_identity(launch['root_sha256'], closed))
assert completion is not None
assert C.run_digest(run) == before
G._write_new(str(out / 'REVIEW.json'), G._pretty({
    'code_sha256': G._sha_file(CL.__file__), 'positive': positive,
    'incorrectly_accepted_rehashed_whole': accepted,
    'correct_completion_call': 'C.complete_g23(doc, C.relations_from_run(lanes), identity)',
    'completion': completion, 'completion_problems': problems,
    'actual_model_calls': 0, 'real_run_unchanged': True}) + '\n')
print('PROVED: rehashed false whole accepted without native comparison; correct relation caller completes', flush=True)
