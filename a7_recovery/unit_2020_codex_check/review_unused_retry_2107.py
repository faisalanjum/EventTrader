"""Read-only counterexample to Core2107's unverified closure candidate."""
import copy
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, run, candidate, launch = (ctx[k] for k in ('G', 'run_dir', 'cand', 'launch'))
sys.path.insert(0, str(HERE.parent / 'unit_2106_unused_retry'))
import a7_unused_retry_closure_2106 as CL

assert G._sha_file(CL.__file__) == 'e8c2cd1d3a70eec6a695c8be8a75a9415bd7a936af8e52b9fcb3da3c8192bc36'
old = G._read(str(HERE / 'codex_formatreal2105_a/RECOVERY.json'))
fake = copy.deepcopy(old)
fake['code_sha256'] = os.environ['A7_FORMAT_CODE_SHA256']
fake['readings'] = [{'lane_id': 'G2-001/G1a', 'segment': 999,
                    'answer': {'not_an_answer': True},
                    'audit': {'recovered': False, 'raw_sha256': '0' * 64}}]
evidence, problems = CL.inspect(
    str(Path(G.__file__).parent), candidate, run, 5, launch['root_sha256'],
    'b04fe0d4668b9be916a855a6146b1dcfbd83b920e221d124afff7fd8d67b80b2',
    launch['workflow_gate_sha256'],
    '/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl',
    fake, os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256'])
assert evidence is not None and not problems, (evidence, problems)
assert evidence['recovered_prior_segment'] == {'G2-001/G1a': 999}
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'COUNTEREXAMPLE.json'), G._pretty({
    'scope': 'read-only proof of unsafe closure inspection; no closure applied',
    'candidate_code_sha256': G._sha_file(CL.__file__),
    'fabricated_report': fake, 'incorrectly_accepted_evidence': evidence,
    'actual_model_calls': 0, 'real_run_writes': 0}) + '\n')
print('PROVED: closure inspector accepted nonexistent prior segment999 and a made-up answer', flush=True)
