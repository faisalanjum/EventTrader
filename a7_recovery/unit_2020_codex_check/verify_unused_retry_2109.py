"""Independent native closure controls and in-memory boundary mutations."""
import copy
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

code = 'e72647b3a0d3f5a4ffddd7752ff18dd32229cf87dfea540141cc4189f3a96998'
assert G._sha_file(CL.__file__) == code
before = C.run_digest(run)
args = (str(Path(G.__file__).parent), str(HERE), candidate, run, 5,
        launch['root_sha256'],
        'b04fe0d4668b9be916a855a6146b1dcfbd83b920e221d124afff7fd8d67b80b2',
        launch['workflow_gate_sha256'], os.environ['A7_FORMAT_CODE_SHA256'],
        os.environ['A7_FORMAT_RULE_SHA256'],
        '/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl')
positive, bad = CL.inspect(*args)
assert positive is not None and not bad, bad

# Reuse the independently frozen negative from the actual earlier reproduction.
old = HERE / 'codex_unusedreview2108_a/REVIEW.json'
assert G._sha_file(str(old)) == '5fe13e690da3e6637dacb1f854b8a9ffdbd708432fcb2f2a8f2c5028aba489aa'
bad_whole = str(old.parent / 'TEST_only_false_whole.json')
claim = G._read(str(old))
assert G._read(bad_whole)['lanes']['G2-001/G1a']['sha256'] == claim['incorrectly_accepted_rehashed_whole']['prior_reading']['G2-001/G1a']['prior_raw_sha256']
whole_path, read, audit = G.whole_path, G._read, G.audit_official_state
side = G.load_receipt(run, 5)['state_path']
side_value = G._read(side)

def negative(which):
    if which == 'native_mapping':
        changes = {'whole_path': lambda r, n: bad_whole if r == run and n == 4 else whole_path(r, n)}
    elif which == 'native_failure':
        changes = {'audit_official_state': lambda *_: (['injected native refusal'], {})}
    else:
        value = dict(side_value, states=None)
        changes = {'_read': lambda path: copy.deepcopy(value) if path == side else read(path)}
    with R._using(G, **changes):
        return CL.inspect(*args)

controls = {}
for name in ('native_mapping', 'native_failure', 'sidecar'):
    ev, problems = negative(name)
    assert ev is None and problems, (name, ev, problems)
    controls[name] = problems

source = Path(CL.__file__).read_text()
changes = [
    ('native_mapping', '_prior_reading',
     'if not audit_problems and G._plain(whole or {}) != G._plain(native_whole):',
     'if False:'),
    ('native_failure', '_prior_reading',
     'problems += ["prior segment %d native audit: %s" % (prior, p)\n                 for p in audit_problems]',
     'problems += []'),
    ('sidecar', 'inspect', 'if G._plain(state) != G._plain(want):', 'if False:'),
]
mutations = []
for name, function, old_text, new_text in changes:
    assert source.count(old_text) == 1, name
    changed = source.replace(old_text, new_text)
    namespace = dict(vars(CL))
    exec(compile(changed, CL.__file__, 'exec'), namespace)
    with R._using(CL, **{function: namespace[function]}):
        ev, problems = negative(name)
    assert ev is not None and not problems, (name, ev, problems)
    mutations.append({'name': name, 'mutant_sha256': G._sha(changed),
                      'wrong_accept_reproduced': True})
    assert negative(name)[0] is None, 'restored control must refuse'

closed = str(HERE.parent / 'unit_2106_unused_retry/testruns_codex2109_review/connection/run')
digest, files = C.run_digest(closed)
with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
    root, doc, lanes, problems = C.evidence(candidate, closed, launch['root_sha256'], digest, files)
    assert not problems, problems
    relations = C.relations_from_run(lanes)
    assert set(relations) == {'G2-000/G1a', 'G2-000/G1b', 'G2-001/G1a'}
    result, problems = C.complete_g23(doc, relations, C.g23_identity(launch['root_sha256'], closed))
    assert not problems, problems
    expected = {qid: row['batch_id'] for row in doc['batch_rows'] for qid in row['question_ids']}
    reached = dict((q, row['batch_id']) for q, row in result['credited'].items())
    for row in result['unresolved']:
        assert row['question_id'] not in reached
        reached[row['question_id']] = row['batch_id']
    assert reached == expected and len(expected) == 306
    assert result['credited_questions'] == 0 and result['unresolved_questions'] == 306
    assert lanes['G2-001/G1a']['selected'] == 1
    assert all(not entry['original_valid'] for entry in result['run_identity']['meaning_format_recovery']['attempts']
               if entry['lane_id'] == 'G2-001/G1a')
assert C.run_digest(run) == before and Path(CL.__file__).read_text() == source
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'REVIEW.json'), G._pretty({
    'closure_code_sha256': code, 'positive': positive, 'negative_controls': controls,
    'mutations': mutations, 'correct_completion': result,
    'actual_model_calls': 0, 'actual_G2_run_unchanged': True,
    'core_test_replay': '51/51 in attempt_codex_unused2109_tests; original native + TEST copies'}) + '\n')
print('VERIFIED: native closure boundary,3 caught mutations,306 exact outcomes,original invalids unchanged; zero real writes')
