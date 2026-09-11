"""Read-only native/transcript proof for the original A3 answer population."""
import collections
import json
import os
import sys

sys.path.insert(0, '/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1997/owner')
import a4_source_key as SK
K, RT = SK.K, SK.RT
primary, retry = K.a3_run_dirs()
audit = K.AUD.audit(os.path.join(primary, K.RECEIPT_NAME))
full = K.a3_evidence()
receipt = K._load(os.path.join(primary, K.RECEIPT_NAME))
fin = K._load(os.path.join(primary, K.FINALIZATION_NAME))
returned = RT.a1_readable_rows(receipt['states'])
raw_problems = RT.a1_raw_binding_problems(primary, returned, fin['attempt'])
print(json.dumps({
    'kind': 'READ-ONLY original-answer native proof; no grading or model call',
    'primary': primary, 'scheduled': len(receipt['allowed']),
    'native_states': len(receipt['states']), 'native_returned_rows': len(returned),
    'proved_answers': len(full['answers']), 'audit_problems': audit['problems'],
    'outcomes': dict(collections.Counter(row[1] for row in audit['outcomes'])),
    'complete_primary_retry_problems': full['problems'],
    'raw_binding_problems': raw_problems, 'source_binding': full['binding'],
    'answer_hashes': [{'packet_id': k[0], 'lane_id': k[1], 'sha256': K._sha(v)}
                      for k, v in sorted(full['answers'].items())],
}, indent=1))
raise SystemExit(0 if not (audit['problems'] or full['problems'] or raw_problems) else 3)
