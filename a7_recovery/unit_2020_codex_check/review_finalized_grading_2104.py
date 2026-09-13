"""Read-only native/parser replay of externally pinned finalized segments.

Other segments may still be collecting. No whole-run completion or A7 score
is claimed here, and no candidate, collection record or model call is changed.
The existing operator establishes the exact owners and preflight context.
"""
import json
import os
import runpy
from pathlib import Path

assert os.environ['A7_GRADING_COMMAND'] == 'preflight'
HERE = Path(__file__).resolve().parent
context = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G = context['G']
run, candidate, launch = (context[k] for k in ('run_dir', 'cand', 'launch'))
pins = json.loads(os.environ['A7_REVIEW_FINALIZED_SEGMENTS'])
assert pins and len({p['segment'] for p in pins}) == len(pins)
doc, _ = G.load_frozen(candidate, launch['candidate_sha256'])
binding, parser = G.binding_and_parser(G.task_kind(doc))
reviewed = []
for pin in pins:
    n = pin['segment']
    final_path = G.finalization_path(run, n)
    assert G.segment_state(run, n) == 'finalized'
    assert G._sha_file(final_path) == pin['finalization_sha256']
    assert G._sha_file(G.receipt_path(run, n)) == pin['receipt_sha256']
    final = G._read(final_path)
    assert final['root_sha256'] == launch['root_sha256']
    assert final['receipt_sha256'] == pin['receipt_sha256']
    assert final['accounting_sha256'] == G._sha_file(G.accounting_path(run, n))
    _packet, bad = G.preflight(candidate, run, n, launch['root_sha256'], pin['receipt_sha256'])
    assert not bad, bad
    bad, native = G.audit_official_state(run, n, launch['root_sha256'], pin['receipt_sha256'])
    assert not bad, bad
    saved, bad = G.whole_answers(run, n)
    assert not bad and saved == native, bad
    expected = {r['lane_id']: r for r in G.load_receipt(run, n)['rows']}
    assert set(native) <= set(expected)
    validity = dict(final['validity'])
    rows = []
    for lane, text in native.items():
        answer, bad = parser(text, binding(doc, expected[lane]['batch_id']))
        assert (not bad) == validity[lane], (lane, bad)
        rows.append({'lane': lane, 'whole_sha256': G._sha(text),
                     'valid': not bad, 'problems': bad, 'answer': answer})
    assert G._sha_file(final_path) == pin['finalization_sha256']
    reviewed.append(dict(pin, ledger=final['ledger'], rows=rows,
                         uncalled=final['uncalled'], retry=final['retry']))
out = HERE / os.environ['A7_TAG']
out.mkdir()
result = {'scope': 'finalized-segment native and parser replay; not semantic adjudication or an A7 score',
          'launch_sha256': G._sha_file(os.environ['A7_GRADING_LAUNCH']),
          'kind': G.task_kind(doc), 'segments': reviewed, 'new_model_calls': 0}
G._write_new(str(out / 'REVIEW.json'), G._pretty(result) + '\n')
print('REVIEW_SAVED', str(out / 'REVIEW.json'), 'segments', len(reviewed), flush=True)
