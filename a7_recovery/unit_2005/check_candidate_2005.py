"""Source-only artifact-builder regression using preserved, labelled TEST keys."""
import collections
import hashlib
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_source_candidate as SC
CL, C = SC.CL, SC.C
base = Path(CL.PKG_DIR).parent
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
original_bindings = C.ordinary_bindings
results = []

def check(name, ok):
    results.append({'check': name, 'ok': bool(ok)})
    assert ok, name

for case, names in (
    ('primary', ('review_codex_final2002_qualified', 'closure_pkg_codex_final2002_qualified',
                 'final_codex_final2002_qualified', 'final_pkg_codex_final2002_qualified')),
    ('child', ('retry_review_codex_lifecycle2002_qualified', 'retry_pkg_codex_lifecycle2002_qualified',
               'retry_final_codex_lifecycle2002_qualified', 'retry_final_pkg_codex_lifecycle2002_qualified')),
):
    review, review_package, key_run, key_package = (str(base / n) for n in names)
    bound = CL.SK.bound(key_run, key_package)
    offered = {f: getattr(bound, f) for f in ('package', 'evidence', 'hr', 'events', 'hr_package')}
    ordinary = out / (case + '_bound.json')
    CL.RT.write_new(str(ordinary), json.dumps(offered))
    C.ORDINARY = str(ordinary)
    dest = out / case
    with SC.candidate_scope(review, review_package, key_run, key_package):
        hashes, full_counts, counts, manifest = C.build(str(dest))
        check(case + ': candidate re-derives exactly', C.verify(str(dest)) == [])
        ident = json.loads((dest / 'key_identity.json').read_text())
        expected_runs = []
        before = CL.K.ledger_before()
        for primary in (CL.INITIAL_RUN, review, key_run):
            for attempt in (primary, os.path.join(primary, 'retry')):
                rp = Path(attempt) / CL.K.RECEIPT_NAME
                if rp.is_file():
                    expected_runs.append(attempt)
                    before += len(json.loads(rp.read_text())['allowed'])
        check(case + ': every actual run bound once, no fake history',
              ident['runs'] == expected_runs and len(set(ident['runs'])) == len(expected_runs)
              and all(Path(r).is_dir() for r in ident['runs']))
        check(case + ': actual calls counted once', manifest['budget']['before'] == before)
        check(case + ': full live row population', counts['rows_accounted'] == len(CL.SK.inventory()))
        check(case + ': every artifact binding is exact', all(
            hashlib.sha256(Path(v['path']).read_bytes()).hexdigest() == v['sha256']
            for v in ident['bindings'].values()))
        check(case + ': all initial/review/final receipts and closeouts included', all(
            any(v['path'] == str(Path(r) / filename) for v in ident['bindings'].values())
            for r in expected_runs for filename in (CL.K.RECEIPT_NAME, CL.K.FINALIZATION_NAME)))
        prompt = (dest / 'signer/signer_prompt.txt').read_text()
        check(case + ': existing signer parser/launcher, one primary call',
              manifest['budget']['primaries'] == 1 and manifest['prompt_sha256'] == CL.K._sha(prompt)
              and json.dumps(prompt) in (dest / 'signer/final_sign.attempt1.js').read_text())
        # A downstream reader uses the original exact Decimal materializer,
        # inside this same context; it never substitutes a display JSON key.
        import a7_g1_build as G
        import build_a5_exp5_kit as A5
        saved_dir, saved_bound = A5.APPROVED_KEY_DIR, G._approved_bound
        A5.APPROVED_KEY_DIR = 'TEST binding behavior only; no real approval'
        G._approved_bound = lambda: bound
        try:
            key, sidecar = G.gold_by_event()
            expected, expected_sidecar, bad = CL.SK.materialize(CL.F.signing_gate(key_run, bound)['shards'])
            check(case + ': actual grader materializer agrees', not bad and key == expected and sidecar == expected_sidecar)
        finally:
            A5.APPROVED_KEY_DIR, G._approved_bound = saved_dir, saved_bound
    check(case + ': scope restores the historical binding owner', C.ordinary_bindings is original_bindings)
    try:
        with SC.candidate_scope(review, review_package, key_run + '_wrong', key_package):
            raise AssertionError('wrong offered run was accepted')
    except ValueError as exc:
        check(case + ': wrong offered run refuses', 'exact source-only key' in str(exc))
    check(case + ': refusal restores the historical binding owner', C.ordinary_bindings is original_bindings)
    try:
        with SC.candidate_scope(review + '_missing', review_package, key_run, key_package):
            raise AssertionError('missing review was accepted')
    except (ValueError, FileNotFoundError):
        check(case + ': absent required review refuses', True)
    check(case + ': failed precondition changes no binding owner', C.ordinary_bindings is original_bindings)

# The extracted default retains all historical bindings, including the
# mandatory phase-one record; a missing historical record is NOT waived.
legacy = out / 'legacy'
for directory in ('package', 'evidence', 'events', 'hr'):
    (legacy / directory).mkdir(parents=True)
    filename = C.F.MANIFEST_NAME if directory == 'package' else C.K.FINALIZATION_NAME
    CL.RT.write_new(str(legacy / directory / filename), '{"TEST": "' + directory + '"}')
for use_hr in (False, True):
    bound = C.F.Bound(package=str(legacy / 'package'), evidence=str(legacy / 'evidence'),
                      events=str(legacy / 'events'), hr=str(legacy / 'hr') if use_hr else None, fix=None)
    runs, bindings = C.ordinary_bindings(bound)
    check('legacy: exact original binding order, hr=' + str(use_hr), list(bindings) ==
          ['final_package', 'phase1_finalization', 'event_finalization'] + (['hard_review_finalization'] if use_hr else []))
    check('legacy: mandatory evidence hash retained, hr=' + str(use_hr),
          bindings['phase1_finalization']['sha256'] == hashlib.sha256((legacy / 'evidence' / C.K.FINALIZATION_NAME).read_bytes()).hexdigest())
    bound = bound._replace(evidence=str(legacy / 'missing'))
    try:
        C.ordinary_bindings(bound)
        raise AssertionError('a missing historical phase was silently dropped')
    except FileNotFoundError:
        check('legacy: missing phase still refuses, hr=' + str(use_hr), True)
print(json.dumps({'kind': 'SYNTHETIC ONLY; no real key signature or approval',
                  'model_calls': 0, 'checks': results, 'passed': len(results),
                  'test_output': str(out)}, indent=1))
