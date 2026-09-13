"""Recover the four independently pinned real G2 replies; no run/score write."""
import json
import os
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, run, candidate, launch = (ctx[k] for k in ('G', 'run_dir', 'cand', 'launch'))
import a7_meaning_format_2105 as F

assert G._sha_file(F.__file__) == os.environ['A7_FORMAT_CODE_SHA256']
assert G._sha_file(str(F.RULE_FILE)) == os.environ['A7_FORMAT_RULE_SHA256']
prior_path = HERE / 'codex_g2seg1to4review2105_a/REVIEW.json'
assert G._sha_file(str(prior_path)) == '3785da62ce266c1a8f60ca022d6c01d28cb35b4b75c2d0ccf3e00c66aa597b73'
prior = G._read(str(prior_path))
assert prior['kind'] == 'G2' and prior['launch_sha256'] == G._sha_file(os.environ['A7_GRADING_LAUNCH'])
doc, _ = G.load_frozen(candidate, launch['candidate_sha256'])
binding, parser = G.binding_and_parser('G2')
results = []
for pin in prior['segments']:
    n = pin['segment']
    assert G._sha_file(G.finalization_path(run, n)) == pin['finalization_sha256']
    assert G._sha_file(G.receipt_path(run, n)) == pin['receipt_sha256']
    whole, bad = G.whole_answers(run, n)
    assert not bad
    rows = {r['lane_id']: r for r in G.load_receipt(run, n)['rows']}
    for previous in pin['rows']:
        lane, raw = previous['lane'], whole[previous['lane']]
        assert G._sha(raw) == previous['whole_sha256']
        packet = binding(doc, rows[lane]['batch_id'])
        answer, bad, audit = F.read(raw, packet)
        assert audit['original_valid'] is previous['valid']
        assert audit['original_problems'] == previous['problems']
        assert not bad
        # Independent literal interpretation by the JSON standard library,
        # not the recovery's lookup or a verdict manufactured by its parser.
        plain = raw.strip()
        if plain.startswith('```'):
            plain = '\n'.join(plain.splitlines()[1:-1])
        expected = {}
        for entry in json.loads(plain):
            expected[entry['question_id']] = {
                field: json.loads(value) if isinstance(value, str) else value
                for field, value in entry['verdicts'].items()}
        assert answer == expected
        assert parser(raw, packet)[1] == previous['problems']
        results.append({'segment': n, 'lane_id': lane, 'audit': audit, 'answer': answer})
assert len(results) == 4
assert sum(row['audit']['recovered'] for row in results) == 3
assert sum(row['audit']['original_valid'] for row in results) == 1
assert G._sha_file(F.__file__) == os.environ['A7_FORMAT_CODE_SHA256']
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'RECOVERY.json'), G._pretty({
    'scope': 'real saved reply format recovery only; no completion or A7 score',
    'code_sha256': os.environ['A7_FORMAT_CODE_SHA256'],
    'rule_sha256': os.environ['A7_FORMAT_RULE_SHA256'],
    'original_review_sha256': G._sha_file(str(prior_path)),
    'actual_model_calls': 0, 'readings': results}) + '\n')
print('VERIFIED four saved replies; three explicitly recovered; original failures unchanged', flush=True)
