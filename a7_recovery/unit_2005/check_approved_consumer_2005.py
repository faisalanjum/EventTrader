"""TEST ONLY: actual approved-key pins, inventory and runtime key consumers.

This tests the key handoff. It does not prepare an EXP-5 run, transform a saved
answer, sign a real key, decide meaning or claim a completed A5/A6 evaluation.
"""
import decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT / 'TEST_codex_signed2005_a/TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT / 'owner'))
import a4_source_candidate as SC
CL, C = SC.CL, SC.C
import build_a5_exp5_kit as A5
import a7_g1_build as G
import a7_key_correction as KC

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
checks = []


def check(name, ok):
    checks.append({'check': name, 'ok': bool(ok)})
    assert ok, name


def decimals(value):
    if isinstance(value, decimal.Decimal):
        return 1
    if isinstance(value, dict):
        return sum(decimals(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(decimals(v) for v in value)
    return 0


with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    lock = A5.a4_lock()
    check('approval comes from frozen external pins',
          A5.A4_LOCK_SHA == saved['lock_sha256']
          and A5.A4_LOCK_RECEIPT_SHA == saved['receipt_sha256'])
    check('exact sealed source inventory follows the full hash chain',
          not A5.approved_inventory_problems()
          and A5.approved_inventory()[0] == CL.SK.plan()['inventory_sha256'])
    bound = G._approved_bound()
    check('ordinary binding is the exact independently pinned settlement',
          bound == CL.SK.bound(saved['key_run'], saved['key_package']))
    key, sidecar = G.gold_by_event()
    current, identity = KC.current_key()
    check('actual grader and current-key consumer agree without historical corrections',
          current == key and identity['acted_rows'] == 0
          and identity['approved_lock_sha256'] == A5.A4_LOCK_SHA)
    check('runtime key keeps exact Decimal values', decimals(key) > 0)
    check('sealed facts and observed reader facts reconcile',
          sum(f.get('du_worthy') is True for rows in key.values() for f in rows)
          == lock['counts']['du_worthy_facts'] == identity['accepted_rows'])

    # The existing denominator consumer takes a reader plan. Exercise that
    # schema from the original frozen population and lane schedule. This is
    # a TEST input, not a newly published evaluation plan or response adapter.
    original = CL.SK.plan()
    arms = sorted({lane['lane_id'].rsplit('/', 1)[1]
                   for packet in original['packets'] for lane in packet['lanes']})
    plan = {'n_events': len(original['events']),
            'n_packets': len(original['packets']), 'arms': arms}
    required = G._required(plan)
    check('denominator includes every original event/item/arm, not returned answers',
          required == {'events': original['n_events'], 'packets': original['n_packets'],
                       'answers': original['n_calls'],
                       'accepted_gold': lock['counts']['du_worthy_facts']})
    check('empty source events remain in the denominator',
          required['events'] > len(key)
          and required['events'] - len(key) == len(original['events']) - len(CL.SK.tasks()))
    unfamiliar = {'n_events': 2, 'n_packets': 7, 'arms': ['left', 'middle', 'right']}
    check('unfamiliar supported plan is not replaced by historical totals',
          G._required(unfamiliar) == {'events': 2, 'packets': 7, 'answers': 21,
                                     'accepted_gold': lock['counts']['du_worthy_facts']})

    # Coherently tamper the offered TEST lock AND receipt, while leaving the
    # external approval pins intact. No original or frozen artifact changes.
    offered = out / 'coherently_changed_TEST_offer'
    shutil.copytree(saved['candidate'], offered)
    changed = json.loads((offered / 'a4_final_key_lock.json').read_text())
    changed['counts']['du_worthy_facts'] += 1
    CL.RT._atomic_json(str(offered / 'a4_final_key_lock.json'), changed)
    rec = json.loads((offered / 'a4_final_key_lock_receipt.json').read_text())
    rec['lock_sha256'] = CL.INV.sha_file(str(offered / 'a4_final_key_lock.json'))
    CL.RT._atomic_json(str(offered / 'a4_final_key_lock_receipt.json'), rec)
    with patch.object(A5, 'A4_LOCK_PATH', str(offered / 'a4_final_key_lock.json')):
        try:
            A5.a4_lock()
            raise AssertionError('a coherently re-bound unapproved TEST key passed')
        except ValueError as exc:
            check('coherent unapproved replacement refuses', 'not the pinned' in str(exc))
    check('original approved positive still passes after tamper test', A5.a4_lock() == lock)

CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'SYNTHETIC key handoff only; no real signature or A5/A6 freeze',
    'model_calls': 0, 'passed': len(checks), 'checks': checks,
    'required': required, 'key_events': len(key), 'decimal_values': decimals(key),
    'key_identity': identity, 'run_binding_sha256': CL.INV.sha_file(os.environ['A7_RUN_BINDING']),
}, indent=1))
print('TEST APPROVED CONSUMER', len(checks), 'checks passed; zero calls;', required)
