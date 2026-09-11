"""The saved-answer entry must use the existing proved-trace warm path.

Cold use proves native evidence in full. Warm use checks the external freeze
and whole-run bytes without repeating the complete workflow audit per card.
No AI calls, no invented success, no original file mutation.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT.parent / 'unit_2005/TEST_codex_signed2005_a/TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT.parent / 'unit_2005/owner'))
import a4_source_candidate as SC
CL = SC.CL
import a6_launch_freeze as A6
import a7_prepared_run as PR
import a7_g1_build as G
import a7_g1_complete_v2 as CV

if globals().get('remove_warm_guard'):
    PR.current_era = lambda identity: identity

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    primary, _ = CL.K.a3_run_dirs()
    frozen = A6.reuse_freeze(primary, os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME))
    rendered = A6.render(frozen)
    pin = hashlib.sha256(rendered.encode()).hexdigest()
    CL.RT.write_new(str(out / A6.REUSE_FREEZE_NAME), rendered)
    run = PR.reuse(str(out), pin)
    assert G.materialize(run)[2] == []
    start = time.monotonic()
    with patch.object(CL.K, 'a3_evidence', wraps=CL.K.a3_evidence) as audit:
        assert G.run_of(run) == primary
    elapsed = time.monotonic() - start
    print(json.dumps({'warm_seconds': elapsed, 'full_audits_per_warm_call': audit.call_count}), flush=True)
    assert audit.call_count == 0, 'a warmed source card repeats the entire original workflow audit'
    for owner, attr, replacement in (
            (PR, '_sha', lambda _p: '0' * 64),
            (CV, 'run_digest', lambda _p: ('0' * 64, run['executed']['run_files']))):
        with patch.object(owner, attr, side_effect=replacement):
            try:
                G.run_of(run)
            except ValueError:
                pass
            else:
                raise AssertionError('warm drift was accepted: ' + attr)
        assert G.run_of(run) == primary
    G._MATERIALIZED.clear()
    with patch.object(CL.K, 'a3_evidence', wraps=CL.K.a3_evidence) as audit:
        assert G.run_of(run) == primary
    assert audit.call_count > 0, 'a cold run skipped the full native proof'
print('warm audit is reused, both drift classes refuse, restored positives and cold proof pass')
