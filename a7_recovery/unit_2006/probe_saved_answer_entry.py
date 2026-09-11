"""Read-only preflight of the unchanged A3 answers at the actual A7 entry.

No answers or old plans are copied/changed, no model is called, and no real
approval is asserted. The offered key is the explicitly TEST-signed handoff.
"""
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT.parent / 'unit_2005/TEST_codex_signed2005_a/TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT.parent / 'unit_2005/owner'))
import a4_source_candidate as SC
CL = SC.CL
import a7_prepared_run as PR
import raw_transport as RT

primary, retry = CL.K.a3_run_dirs()
plan = RT.a1_plan_for_run(primary)
receipt = CL.K._load(os.path.join(primary, CL.K.RECEIPT_NAME))
fin = CL.K._load(os.path.join(primary, RT.FINALIZATION_NAME))
result = {
    'kind': 'READ-ONLY saved-answer entry preflight, TEST key only',
    'model_calls': 0, 'primary': primary,
    'original_plan_sha256': CL.INV.sha_file(CL.SK.PLAN_PATH),
    'receipt_sha256': CL.INV.sha_file(os.path.join(primary, CL.K.RECEIPT_NAME)),
    'finalization_sha256': CL.INV.sha_file(os.path.join(primary, RT.FINALIZATION_NAME)),
    'events': plan['n_events'], 'packets': plan['n_packets'],
    'scheduled': len(receipt['allowed']), 'ledger': fin['ledger'],
    'contract_problems': RT.a1_run_contract_problems(receipt, primary, plan),
    'finalization_problems': RT.a1_finalization_problems(fin, plan, primary, 1),
    'original_plan_has_arms': 'arms' in plan,
    'original_has_a5_plan_directory': os.path.isdir(os.path.join(primary, PR.PLAN_DIRNAME)),
}
with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    try:
        identity = PR.load(primary)
    except Exception as exc:
        result['current_A7_entry'] = {'state': 'refused', 'reason': '%s: %s' % (type(exc).__name__, exc)}
    else:
        result['current_A7_entry'] = {'state': 'accepted', 'identity': identity}
print(json.dumps(result, indent=1))
